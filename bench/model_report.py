"""Generate Markdown model reports from benchmark result JSON."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .compare import aggregate, index_results, load_result_file, render_comparison
from .validate import validate_result


@dataclass(frozen=True)
class ReportPolicy:
    min_recall: float = 0.80
    max_hallucinated: int = 0
    max_errors: int = 0
    min_functions: int = 8


def _strategy(data: dict[str, Any]) -> str:
    strategy = data.get("prompt_strategy") or {}
    order = strategy.get("prompt_order", "file-first")
    anchor = strategy.get("anchor_style", "function-name")
    signature = "+signature" if strategy.get("include_signature") else ""
    return f"{order}/{anchor}{signature}"


def _corpus_label(data: dict[str, Any]) -> str:
    files = data.get("files") or ([data["source"]] if data.get("source") else [])
    if not files:
        return "unknown"
    if len(files) == 1:
        return str(files[0])
    return ", ".join(str(file) for file in files)


def _validation_summary(data: dict[str, Any]) -> tuple[str, list[str]]:
    issues = validate_result(data, strict=True)
    errors = [issue for issue in issues if issue.level == "error"]
    warnings = [issue for issue in issues if issue.level == "warning"]
    status = "PASS" if not errors else "FAIL"
    details = [
        f"{issue.level.upper()} {issue.path}: {issue.message}"
        for issue in issues
    ]
    return f"{status} ({len(errors)} errors, {len(warnings)} warnings)", details


def _recommendation(data: dict[str, Any], policy: ReportPolicy) -> tuple[str, list[str]]:
    rows = list(index_results(data).values())
    agg = aggregate(rows)
    recall = agg.primary_matched / agg.primary_total if agg.primary_total else 0.0
    blockers = []
    if agg.total < policy.min_functions:
        blockers.append(
            f"Only {agg.total} functions evaluated; minimum is {policy.min_functions}."
        )
    if recall < policy.min_recall:
        blockers.append(
            f"Recall {recall:.1%} is below required {policy.min_recall:.1%}."
        )
    if agg.hallucinated > policy.max_hallucinated:
        blockers.append(
            f"Hallucinated lines {agg.hallucinated} exceeds maximum {policy.max_hallucinated}."
        )
    if agg.errors > policy.max_errors:
        blockers.append(f"Errored calls {agg.errors} exceeds maximum {policy.max_errors}.")
    return ("deploy" if not blockers else "needs more evals", blockers)


def _worst_rows(data: dict[str, Any], limit: int = 5) -> list[tuple[str, str, int, bool]]:
    rows = list(index_results(data).values())
    rows.sort(
        key=lambda row: (
            row.error is None,
            row.primary_matched / row.primary_total if row.primary_total else 0.0,
            -row.hallucinated,
        )
    )
    return [
        (
            row.key,
            "ERROR" if row.error else f"{row.primary_matched}/{row.primary_total}",
            row.hallucinated,
            row.passed,
        )
        for row in rows[:limit]
    ]


def render_model_report(
    result_path: Path,
    result_data: dict[str, Any],
    *,
    baseline_path: Path | None = None,
    baseline_data: dict[str, Any] | None = None,
    policy: ReportPolicy | None = None,
) -> str:
    policy = policy or ReportPolicy()
    rows = list(index_results(result_data).values())
    agg = aggregate(rows)
    recall = agg.primary_matched / agg.primary_total if agg.primary_total else 0.0
    validation_status, validation_details = _validation_summary(result_data)
    recommendation, blockers = _recommendation(result_data, policy)

    lines = [
        "# Model Recall Report",
        "",
        f"Result file: `{result_path}`",
        "",
        "## Run Metadata",
        "",
        "| Field | Value |",
        "| --- | --- |",
        f"| Model | `{result_data.get('model', 'unknown')}` |",
        f"| Corpus files | `{_corpus_label(result_data)}` |",
        f"| Prompt strategy | `{_strategy(result_data)}` |",
        f"| Run ID | `{result_data.get('run_id', 'legacy')}` |",
        f"| Created at | `{result_data.get('created_at', 'unknown')}` |",
        f"| Corpus SHA-256 | `{result_data.get('corpus_sha256', 'unknown')}` |",
        "",
        "## Validation",
        "",
        f"Strict result contract: **{validation_status}**",
    ]
    if validation_details:
        lines.extend(["", "| Level | Path | Message |", "| --- | --- | --- |"])
        for detail in validation_details:
            level, rest = detail.split(" ", 1)
            path, message = rest.split(": ", 1)
            lines.append(f"| {level} | `{path}` | {message} |")

    lines.extend([
        "",
        "## Metrics",
        "",
        "| Metric | Value |",
        "| --- | --- |",
        f"| Pass count | {agg.passed}/{agg.total - agg.errors} |",
        f"| Errored calls | {agg.errors} |",
        f"| Primary lines matched | {agg.primary_matched}/{agg.primary_total} ({recall:.1%}) |",
        f"| Hallucinated lines | {agg.hallucinated} |",
        f"| Bonus lines matched | {agg.bonus_matched} |",
        f"| Average latency | {agg.average_latency_s:.2f}s |",
        "",
        "## Worst Failures",
        "",
        "| Function | Matched | Hallucinated | Passed |",
        "| --- | --- | --- | --- |",
    ])
    for function, matched, hallucinated, passed in _worst_rows(result_data):
        lines.append(f"| `{function}` | {matched} | {hallucinated} | {passed} |")

    lines.extend([
        "",
        "## Recommendation",
        "",
        f"Recommendation: **{recommendation}**",
    ])
    if blockers:
        lines.extend(["", "Blocking evidence:"])
        lines.extend(f"- {blocker}" for blocker in blockers)
    else:
        lines.append("")
        lines.append("No policy blockers were found for the configured thresholds.")

    if baseline_path is not None and baseline_data is not None:
        lines.extend([
            "",
            "## Baseline Comparison",
            "",
            "```text",
            render_comparison(baseline_path, baseline_data, result_path, result_data),
            "```",
        ])

    return "\n".join(lines) + "\n"
