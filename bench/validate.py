"""Validate benchmark result JSON contracts."""
from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


HEX_64 = re.compile(r"^[0-9a-f]{64}$")
PROMPT_ORDERS = {"file-first", "task-first"}
ANCHOR_STYLES = {"function-name", "line-number"}


@dataclass(frozen=True)
class ValidationIssue:
    level: str
    path: str
    message: str

    def as_dict(self) -> dict[str, str]:
        return asdict(self)


def load_result_file(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _issue(issues: list[ValidationIssue], level: str, path: str, message: str) -> None:
    issues.append(ValidationIssue(level=level, path=path, message=message))


def _type_name(value: Any) -> str:
    return type(value).__name__


def _require_type(
    issues: list[ValidationIssue],
    data: dict[str, Any],
    key: str,
    expected: type | tuple[type, ...],
    *,
    path: str = "$",
    required: bool = True,
) -> bool:
    if key not in data:
        if required:
            _issue(issues, "error", f"{path}.{key}", "missing required field")
        return False
    value = data[key]
    if not isinstance(value, expected):
        expected_name = (
            " or ".join(t.__name__ for t in expected)
            if isinstance(expected, tuple)
            else expected.__name__
        )
        _issue(
            issues,
            "error",
            f"{path}.{key}",
            f"expected {expected_name}, got {_type_name(value)}",
        )
        return False
    return True


def _require_int_metric(
    issues: list[ValidationIssue],
    row: dict[str, Any],
    key: str,
    *,
    path: str,
) -> None:
    if _require_type(issues, row, key, int, path=path):
        if row[key] < 0:
            _issue(issues, "error", f"{path}.{key}", "must be non-negative")


def _validate_created_at(issues: list[ValidationIssue], data: dict[str, Any]) -> None:
    value = data.get("created_at")
    if not isinstance(value, str):
        _issue(issues, "error", "$.created_at", "expected ISO-8601 string")
        return
    try:
        datetime.fromisoformat(value)
    except ValueError:
        _issue(issues, "error", "$.created_at", "must parse as ISO-8601 datetime")


def _validate_schema_v2(issues: list[ValidationIssue], data: dict[str, Any]) -> None:
    required = {
        "schema_version": int,
        "run_id": str,
        "created_at": str,
        "git_sha": (str, type(None)),
        "python_version": str,
        "corpus_sha256": str,
        "prompt_template_id": str,
        "sample_k": int,
        "sample_seed": int,
        "selected_functions": list,
        "prompt_strategy": dict,
    }
    for key, expected in required.items():
        _require_type(issues, data, key, expected)

    if data.get("schema_version") != 2:
        _issue(issues, "error", "$.schema_version", "expected schema version 2")
    if "created_at" in data:
        _validate_created_at(issues, data)
    corpus_sha = data.get("corpus_sha256")
    if isinstance(corpus_sha, str) and not HEX_64.match(corpus_sha):
        _issue(issues, "error", "$.corpus_sha256", "expected 64 lowercase hex characters")
    selected = data.get("selected_functions")
    if isinstance(selected, list) and not all(isinstance(x, str) for x in selected):
        _issue(issues, "error", "$.selected_functions", "expected list of strings")

    strategy = data.get("prompt_strategy")
    if isinstance(strategy, dict):
        if strategy.get("prompt_order") not in PROMPT_ORDERS:
            _issue(
                issues,
                "error",
                "$.prompt_strategy.prompt_order",
                f"expected one of {sorted(PROMPT_ORDERS)}",
            )
        if strategy.get("anchor_style") not in ANCHOR_STYLES:
            _issue(
                issues,
                "error",
                "$.prompt_strategy.anchor_style",
                f"expected one of {sorted(ANCHOR_STYLES)}",
            )
        _require_type(
            issues,
            strategy,
            "include_signature",
            bool,
            path="$.prompt_strategy",
        )


def _validate_results(issues: list[ValidationIssue], data: dict[str, Any]) -> None:
    if not _require_type(issues, data, "results", list):
        return
    results = data["results"]
    if not results:
        _issue(issues, "error", "$.results", "must contain at least one result")
        return

    for i, row in enumerate(results):
        path = f"$.results[{i}]"
        if not isinstance(row, dict):
            _issue(issues, "error", path, f"expected object, got {_type_name(row)}")
            continue
        _require_type(issues, row, "function", str, path=path)
        _require_type(issues, row, "passed", bool, path=path)
        _require_type(issues, row, "error", (str, type(None)), path=path, required=False)
        _require_int_metric(issues, row, "primary_matched", path=path)
        _require_int_metric(issues, row, "primary_total", path=path)
        _require_int_metric(issues, row, "hallucinated", path=path)
        _require_int_metric(issues, row, "bonus_matched", path=path)
        _require_type(issues, row, "latency_s", (int, float), path=path, required=False)
        _require_type(issues, row, "prompt_chars", int, path=path, required=False)
        _require_type(issues, row, "response", str, path=path, required=False)
        if (
            isinstance(row.get("primary_matched"), int)
            and isinstance(row.get("primary_total"), int)
            and row["primary_matched"] > row["primary_total"]
        ):
            _issue(
                issues,
                "error",
                f"{path}.primary_matched",
                "cannot exceed primary_total",
            )


def validate_result(data: dict[str, Any], *, strict: bool = False) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []
    if not isinstance(data, dict):
        return [ValidationIssue("error", "$", f"expected object, got {_type_name(data)}")]

    _require_type(issues, data, "model", str)
    _require_type(issues, data, "files", list, required=False)
    _require_type(issues, data, "base_url", str, required=False)
    _require_type(issues, data, "temperature", (int, float), required=False)
    _require_type(issues, data, "max_tokens", int, required=False)
    _require_type(issues, data, "relax_indent", bool, required=False)
    _validate_results(issues, data)

    schema_version = data.get("schema_version")
    if schema_version == 2:
        _validate_schema_v2(issues, data)
    elif strict:
        _issue(issues, "error", "$.schema_version", "strict mode requires schema version 2")
    else:
        _issue(issues, "warning", "$.schema_version", "legacy result without schema_version")

    files = data.get("files")
    if isinstance(files, list) and not all(isinstance(x, str) for x in files):
        _issue(issues, "error", "$.files", "expected list of strings")
    return issues


def render_validation(path: Path, issues: list[ValidationIssue]) -> str:
    errors = [issue for issue in issues if issue.level == "error"]
    warnings = [issue for issue in issues if issue.level == "warning"]
    status = "PASS" if not errors else "FAIL"
    lines = [f"{status} {path} ({len(errors)} errors, {len(warnings)} warnings)"]
    for issue in issues:
        lines.append(f"  {issue.level.upper():<7} {issue.path}: {issue.message}")
    return "\n".join(lines)
