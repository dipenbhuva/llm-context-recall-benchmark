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


def function_body(index: int, body_lines: int, rng: random.Random) -> list[str]:
    marker = f"UNIQUE_MARKER_{index:04d}_{rng.randrange(16 ** 8):08x}"
    body = [
        f'    """Synthetic target {index:04d}."""',
        f'    marker = "{marker}"',
        f"    target_index = {index}",
        "    total = input_value",
        f"    bucket = {index % 7}",
    ]
    while len(body) < body_lines - 1:
        step = len(body)
        body.append(
            f"    total = (total * 31 + target_index + {step}) % 1000003  # repeated recall update"
        )
    body.append("    return marker, total, bucket")
    return body


def generate_source(
    *,
    functions: int,
    body_lines: int,
    filler_lines: int,
    seed: int,
) -> str:
    if body_lines < 20:
        raise ValueError("body_lines must be at least 20 so every function is extractable")

    rng = random.Random(seed)
    out = [
        '"""Generated synthetic corpus for context-recall labs."""',
        "",
        f"SYNTHETIC_SEED = {seed}",
        "",
    ]
    for i in range(functions):
        if filler_lines:
            out.append(f"# filler block before target_{i:03d}")
            for j in range(filler_lines):
                out.append(f"FILLER_{i:03d}_{j:03d} = 'shared filler token {j % 11}'")
            out.append("")

        out.append(f"def target_{i:03d}(input_value):")
        out.extend(function_body(i, body_lines, rng))
        out.append("")

    return "\n".join(out)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--functions", type=positive_int, default=32)
    parser.add_argument("--body-lines", type=positive_int, default=30)
    parser.add_argument("--filler-lines", type=non_negative_int, default=0)
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
