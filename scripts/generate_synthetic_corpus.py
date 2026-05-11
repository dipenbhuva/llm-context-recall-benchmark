#!/usr/bin/env python3
"""Generate a deterministic Python corpus for recall-depth experiments."""
from __future__ import annotations

import argparse
import random
from pathlib import Path


def positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be positive")
    return parsed


def non_negative_int(value: str) -> int:
    parsed = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be non-negative")
    return parsed


def rate(value: str) -> float:
    parsed = float(value)
    if parsed < 0.0 or parsed > 1.0:
        raise argparse.ArgumentTypeError("must be between 0.0 and 1.0")
    return parsed


def function_body(
    *,
    index: int,
    body_lines: int,
    rng: random.Random,
    group_id: int | None = None,
    member_id: int | None = None,
    near_duplicate_rate: float = 0.0,
) -> list[str]:
    if group_id is None or member_id is None:
        marker = f"UNIQUE_MARKER_{index:04d}_{rng.randrange(16 ** 8):08x}"
        target_line = f"    target_index = {index}"
        bucket_line = f"    bucket = {index % 7}"
        doc = f'    """Synthetic target {index:04d}."""'
    else:
        marker = (
            f"UNIQUE_MARKER_GROUP_{group_id:03d}_MEMBER_{member_id:03d}_"
            f"{rng.randrange(16 ** 8):08x}"
        )
        target_line = f"    target_index = {group_id}"
        bucket_line = f"    bucket = {group_id % 7}"
        doc = f'    """Synthetic distractor group {group_id:03d}, member {member_id:03d}."""'
        group_line = f"    group_id = {group_id}"
    if group_id is None or member_id is None:
        group_line = None

    body = [line for line in [
        doc,
        f'    marker = "{marker}"',
        target_line,
        group_line,
        "    total = input_value",
        bucket_line,
    ] if line is not None]
    update_count = max(0, body_lines - len(body) - 1)
    shared_updates = int(update_count * near_duplicate_rate) if group_id is not None else 0
    updates_written = 0
    while len(body) < body_lines - 1:
        step = len(body)
        if group_id is not None and updates_written < shared_updates:
            update_value = f"group_id + {step}"
        else:
            update_value = f"target_index + {step}"
        body.append(
            f"    total = (total * 31 + {update_value}) % 1000003  # repeated recall update"
        )
        updates_written += 1
    body.append("    return marker, total, bucket")
    return body


def generate_source(
    *,
    functions: int,
    body_lines: int,
    filler_lines: int,
    seed: int,
    distractor_groups: int = 0,
    near_duplicate_rate: float = 0.0,
) -> str:
    if body_lines < 20:
        raise ValueError("body_lines must be at least 20 so every function is extractable")
    if distractor_groups < 0:
        raise ValueError("distractor_groups must be non-negative")

    rng = random.Random(seed)
    out = [
        '"""Generated synthetic corpus for context-recall labs."""',
        "",
        f"SYNTHETIC_SEED = {seed}",
        "",
    ]
    group_count = min(distractor_groups, functions)
    for i in range(functions):
        group_id = i % group_count if group_count else None
        member_id = i // group_count if group_count else None
        if group_id is None or member_id is None:
            function_name = f"target_{i:03d}"
        else:
            function_name = f"target_g{group_id:03d}_m{member_id:03d}"

        if filler_lines:
            out.append(f"# filler block before {function_name}")
            for j in range(filler_lines):
                out.append(f"FILLER_{i:03d}_{j:03d} = 'shared filler token {j % 11}'")
            out.append("")

        out.append(f"def {function_name}(input_value):")
        out.extend(
            function_body(
                index=i,
                body_lines=body_lines,
                rng=rng,
                group_id=group_id,
                member_id=member_id,
                near_duplicate_rate=near_duplicate_rate,
            )
        )
        out.append("")

    return "\n".join(out)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--functions", type=positive_int, default=32)
    parser.add_argument("--body-lines", type=positive_int, default=30)
    parser.add_argument("--filler-lines", type=non_negative_int, default=0)
    parser.add_argument("--distractor-groups", type=non_negative_int, default=0)
    parser.add_argument("--near-duplicate-rate", type=rate, default=0.0)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--out", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        source = generate_source(
            functions=args.functions,
            body_lines=args.body_lines,
            filler_lines=args.filler_lines,
            seed=args.seed,
            distractor_groups=args.distractor_groups,
            near_duplicate_rate=args.near_duplicate_rate,
        )
    except ValueError as exc:
        raise SystemExit(f"error: {exc}") from exc

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(source + "\n")
    print(
        f"wrote {args.functions} function(s), {args.body_lines} body lines each "
        f"to {args.out}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
