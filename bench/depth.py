"""Analyze recall by source-file depth."""
from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .compare import ResultRow, index_results, load_result_file
from .extract import extract


@dataclass(frozen=True)
class DepthRow:
    key: str
    function: str
    source_file: str
    start_line: int | None
    total_lines: int | None
    depth_pct: float | None
    bucket: str
    primary_matched: int
    primary_total: int
    recall_pct: float
    hallucinated: int
    passed: bool
    error: str | None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DepthBucket:
    bucket: str
    functions: int
    passed: int
    errors: int
    primary_matched: int
    primary_total: int
    recall_pct: float
    hallucinated: int

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _resolve_source_file(raw: str) -> Path | None:
    path = Path(raw)
    if path.exists():
        return path
    repo_root = Path(__file__).resolve().parent.parent
    candidates = [
        repo_root / raw,
        repo_root / "fixtures" / path.name,
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return None


def _source_files(data: dict[str, Any]) -> list[Path]:
    raw_files = data.get("files") or ([data["source"]] if data.get("source") else [])
    files = []
    for raw in raw_files:
        resolved = _resolve_source_file(str(raw))
        if resolved is not None:
            files.append(resolved)
    return files


def _line_positions(data: dict[str, Any]) -> tuple[dict[str, tuple[str, int]], dict[str, int]]:
    positions: dict[str, tuple[str, int]] = {}
    total_lines: dict[str, int] = {}
    for path in _source_files(data):
        text = path.read_text(encoding="utf-8")
        total_lines[str(path)] = text.count("\n") + 1
        for target in extract(path):
            positions.setdefault(target.name, (str(path), target.start_line))
    return positions, total_lines


def _bucket(depth_pct: float | None) -> str:
    if depth_pct is None:
        return "unknown"
    if depth_pct < 33.333:
        return "early"
    if depth_pct < 66.667:
        return "middle"
    return "late"


def depth_rows(data: dict[str, Any]) -> list[DepthRow]:
    positions, total_lines = _line_positions(data)
    rows = []
    for row in index_results(data).values():
        source_file = ""
        start_line = None
        file_lines = None
        depth_pct = None
        if row.function in positions:
            source_file, start_line = positions[row.function]
            file_lines = total_lines.get(source_file)
            if file_lines:
                depth_pct = round(start_line / file_lines * 100, 2)
        recall = row.primary_matched / row.primary_total * 100 if row.primary_total else 0.0
        rows.append(
            DepthRow(
                key=row.key,
                function=row.function,
                source_file=source_file,
                start_line=start_line,
                total_lines=file_lines,
                depth_pct=depth_pct,
                bucket=_bucket(depth_pct),
                primary_matched=row.primary_matched,
                primary_total=row.primary_total,
                recall_pct=round(recall, 2),
                hallucinated=row.hallucinated,
                passed=row.passed,
                error=row.error,
            )
        )
    return rows


def depth_buckets(rows: list[DepthRow]) -> list[DepthBucket]:
    grouped: dict[str, list[DepthRow]] = defaultdict(list)
    for row in rows:
        grouped[row.bucket].append(row)
    order = {"early": 0, "middle": 1, "late": 2, "unknown": 3}
    buckets = []
    for bucket, items in sorted(grouped.items(), key=lambda item: order.get(item[0], 99)):
        real = [item for item in items if not item.error]
        matched = sum(item.primary_matched for item in real)
        total = sum(item.primary_total for item in real)
        recall = matched / total * 100 if total else 0.0
        buckets.append(
            DepthBucket(
                bucket=bucket,
                functions=len(items),
                passed=sum(1 for item in real if item.passed),
                errors=len(items) - len(real),
                primary_matched=matched,
                primary_total=total,
                recall_pct=round(recall, 2),
                hallucinated=sum(item.hallucinated for item in real),
            )
        )
    return buckets


def render_depth(path: Path, rows: list[DepthRow]) -> str:
    if not rows:
        return f"no result rows in {path}"
    lines = [
        "=== DEPTH ANALYSIS ===",
        f"source: {path}",
        "",
        "Bucket   Functions  Pass  Primary  Recall  Halluc.  Errors",
        "------   ---------  ----  -------  ------  -------  ------",
    ]
    for bucket in depth_buckets(rows):
        real_total = bucket.functions - bucket.errors
        lines.append(
            f"{bucket.bucket:<8} {bucket.functions:>9}  "
            f"{bucket.passed:>2}/{real_total:<2}  "
            f"{bucket.primary_matched:>3}/{bucket.primary_total:<3}  "
            f"{bucket.recall_pct:>5.1f}%  "
            f"{bucket.hallucinated:>7}  "
            f"{bucket.errors:>6}"
        )

    lines.extend(["", "Per-function:"])
    for row in sorted(rows, key=lambda item: (item.bucket, item.start_line or 10**9, item.key)):
        line = "?" if row.start_line is None else str(row.start_line)
        depth = "?" if row.depth_pct is None else f"{row.depth_pct:.1f}%"
        lines.append(
            f"  {row.key:<32} {row.bucket:<7} line={line:<5} depth={depth:<6} "
            f"matched={row.primary_matched}/{row.primary_total} "
            f"hallucinated={row.hallucinated} passed={row.passed}"
        )
    return "\n".join(lines)


def render_depth_json(rows: list[DepthRow]) -> str:
    return json.dumps({
        "buckets": [bucket.as_dict() for bucket in depth_buckets(rows)],
        "functions": [row.as_dict() for row in rows],
    }, indent=2) + "\n"


def load_depth_rows(path: Path) -> list[DepthRow]:
    return depth_rows(load_result_file(path))
