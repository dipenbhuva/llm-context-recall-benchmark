"""Classify benchmark result failures into a compact taxonomy."""
from __future__ import annotations

import json
from collections import Counter
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from .compare import ResultRow, index_results, load_result_file


@dataclass(frozen=True)
class Diagnosis:
    key: str
    function: str
    category: str
    reason: str
    primary_matched: int
    primary_total: int
    hallucinated: int
    passed: bool
    error: str | None

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def classify_row(row: ResultRow) -> Diagnosis:
    if row.error:
        category = "api_error"
        reason = "request failed or returned no usable content"
    elif row.primary_total <= 0:
        category = "invalid_score"
        reason = "primary_total is zero or missing"
    elif row.primary_matched == row.primary_total and row.hallucinated == 0:
        category = "perfect_recall"
        reason = "all primary lines matched with no hallucinations"
    elif row.passed and row.hallucinated > 0:
        category = "pass_with_hallucination"
        reason = "passed threshold but included non-source lines"
    elif row.passed:
        category = "partial_pass"
        reason = "passed threshold but missed at least one primary line"
    elif row.primary_matched == 0 and row.hallucinated == 0:
        category = "empty_or_no_recall"
        reason = "no primary lines matched"
    elif row.hallucinated == 0:
        category = "truncated_or_incomplete"
        reason = "some prefix/content matched but output stopped before threshold"
    else:
        category = "format_or_wrong_span"
        reason = "missed threshold and produced non-matching lines"

    return Diagnosis(
        key=row.key,
        function=row.function,
        category=category,
        reason=reason,
        primary_matched=row.primary_matched,
        primary_total=row.primary_total,
        hallucinated=row.hallucinated,
        passed=row.passed,
        error=row.error,
    )


def diagnose_result(data: dict[str, Any]) -> list[Diagnosis]:
    return [classify_row(row) for row in index_results(data).values()]


def render_diagnosis(path: Path, diagnoses: list[Diagnosis]) -> str:
    counts = Counter(item.category for item in diagnoses)
    lines = [
        "=== FAILURE DIAGNOSIS ===",
        f"source: {path}",
        f"functions: {len(diagnoses)}",
        "",
        "Category counts:",
    ]
    for category, count in sorted(counts.items()):
        lines.append(f"  {category:<28} {count}")

    lines.extend(["", "Examples:"])
    for item in diagnoses:
        lines.append(
            f"  {item.key:<32} {item.category:<28} "
            f"matched={item.primary_matched}/{item.primary_total} "
            f"hallucinated={item.hallucinated} passed={item.passed}"
        )
        lines.append(f"    {item.reason}")
    return "\n".join(lines)


def load_and_diagnose(path: Path) -> list[Diagnosis]:
    return diagnose_result(load_result_file(path))


def write_diagnosis_json(path: Path, diagnoses: list[Diagnosis]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps([item.as_dict() for item in diagnoses], indent=2),
        encoding="utf-8",
    )
