"""Compare two benchmark result JSON files for lab reports."""
from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ResultRow:
    key: str
    function: str
    passed: bool
    error: str | None
    primary_matched: int
    primary_total: int
    hallucinated: int
    bonus_matched: int
    latency_s: float


@dataclass(frozen=True)
class Aggregate:
    passed: int
    total: int
    errors: int
    primary_matched: int
    primary_total: int
    hallucinated: int
    bonus_matched: int
    average_latency_s: float


def load_result_file(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _row_key(row: dict[str, Any], index: int, counts: Counter[str], seen: dict[str, int]) -> str:
    function = str(row.get("function", f"result_{index}"))
    if counts[function] == 1:
        return function
    if row.get("case"):
        return f"{function}:{row['case']}"
    seen[function] += 1
    return f"{function}#{seen[function]}"


def index_results(data: dict[str, Any]) -> dict[str, ResultRow]:
    results = data.get("results") or []
    counts = Counter(str(row.get("function", f"result_{i}")) for i, row in enumerate(results))
    seen: dict[str, int] = defaultdict(int)
    indexed = {}
    for i, row in enumerate(results):
        key = _row_key(row, i, counts, seen)
        indexed[key] = ResultRow(
            key=key,
            function=str(row.get("function", key)),
            passed=bool(row.get("passed", False)),
            error=row.get("error"),
            primary_matched=int(row.get("primary_matched", 0) or 0),
            primary_total=int(row.get("primary_total", 0) or 0),
            hallucinated=int(row.get("hallucinated", 0) or 0),
            bonus_matched=int(row.get("bonus_matched", 0) or 0),
            latency_s=float(row.get("latency_s", 0.0) or 0.0),
        )
    return indexed


def aggregate(rows: list[ResultRow]) -> Aggregate:
    total = len(rows)
    return Aggregate(
        passed=sum(1 for row in rows if row.passed and row.error is None),
        total=total,
        errors=sum(1 for row in rows if row.error),
        primary_matched=sum(row.primary_matched for row in rows if row.error is None),
        primary_total=sum(row.primary_total for row in rows if row.error is None),
        hallucinated=sum(row.hallucinated for row in rows if row.error is None),
        bonus_matched=sum(row.bonus_matched for row in rows if row.error is None),
        average_latency_s=(
            sum(row.latency_s for row in rows) / total if total else 0.0
        ),
    )


def _strategy(data: dict[str, Any]) -> str:
    strategy = data.get("prompt_strategy") or {}
    order = strategy.get("prompt_order", "file-first")
    anchor = strategy.get("anchor_style", "function-name")
    signature = "+signature" if strategy.get("include_signature") else ""
    return f"{order}/{anchor}{signature}"


def _label(path: Path, data: dict[str, Any]) -> str:
    model = data.get("model", "unknown-model")
    return f"{path.name}  model={model}  prompt={_strategy(data)}"


def _signed(value: int | float, *, digits: int | None = None) -> str:
    if digits is None:
        return f"{value:+d}"
    return f"{value:+.{digits}f}"


def _metric_rows(a: Aggregate, b: Aggregate) -> list[tuple[str, str, str, str]]:
    return [
        (
            "Pass",
            f"{a.passed}/{a.total}",
            f"{b.passed}/{b.total}",
            _signed(b.passed - a.passed),
        ),
        (
            "Errors",
            str(a.errors),
            str(b.errors),
            _signed(b.errors - a.errors),
        ),
        (
            "Primary matched",
            f"{a.primary_matched}/{a.primary_total}",
            f"{b.primary_matched}/{b.primary_total}",
            _signed(b.primary_matched - a.primary_matched),
        ),
        (
            "Hallucinated lines",
            str(a.hallucinated),
            str(b.hallucinated),
            _signed(b.hallucinated - a.hallucinated),
        ),
        (
            "Bonus matched",
            str(a.bonus_matched),
            str(b.bonus_matched),
            _signed(b.bonus_matched - a.bonus_matched),
        ),
        (
            "Average latency",
            f"{a.average_latency_s:.2f}s",
            f"{b.average_latency_s:.2f}s",
            f"{b.average_latency_s - a.average_latency_s:+.2f}s",
        ),
    ]


def render_comparison(path_a: Path, data_a: dict[str, Any], path_b: Path, data_b: dict[str, Any]) -> str:
    rows_a = index_results(data_a)
    rows_b = index_results(data_b)
    common = sorted(set(rows_a) & set(rows_b))
    only_a = sorted(set(rows_a) - set(rows_b))
    only_b = sorted(set(rows_b) - set(rows_a))

    out = [
        "=== RESULT COMPARISON ===",
        f"A: {_label(path_a, data_a)}",
        f"B: {_label(path_b, data_b)}",
        f"Common functions: {len(common)}",
    ]
    if only_a:
        out.append(f"Only in A: {', '.join(only_a)}")
    if only_b:
        out.append(f"Only in B: {', '.join(only_b)}")
    if not common:
        out.append("No common functions to compare.")
        return "\n".join(out)

    common_a = [rows_a[key] for key in common]
    common_b = [rows_b[key] for key in common]
    agg_a = aggregate(common_a)
    agg_b = aggregate(common_b)

    out.extend([
        "",
        "Metric                  A              B              Delta",
        "------                  -              -              -----",
    ])
    for name, a_value, b_value, delta in _metric_rows(agg_a, agg_b):
        out.append(f"{name:<22}  {a_value:<13}  {b_value:<13}  {delta}")

    out.extend(["", "Per-function delta (B - A):"])
    for key in common:
        a = rows_a[key]
        b = rows_b[key]
        pass_change = f"{'yes' if a.passed else 'no'} -> {'yes' if b.passed else 'no'}"
        out.append(
            f"  {key:<32} "
            f"matched {a.primary_matched:>2} -> {b.primary_matched:>2} "
            f"({_signed(b.primary_matched - a.primary_matched)})  "
            f"halluc {a.hallucinated:>2} -> {b.hallucinated:>2} "
            f"({_signed(b.hallucinated - a.hallucinated)})  "
            f"pass {pass_change}"
        )
    return "\n".join(out)
