"""Summarize benchmark result JSON files into table/CSV/JSON artifacts."""
from __future__ import annotations

import csv
import json
from dataclasses import asdict, dataclass
from io import StringIO
from pathlib import Path
from typing import Any

from .compare import aggregate, index_results, load_result_file


@dataclass(frozen=True)
class RunSummary:
    path: str
    model: str
    files: str
    prompt_strategy: str
    schema_version: str
    run_id: str
    functions: int
    passed: int
    errors: int
    primary_matched: int
    primary_total: int
    recall_pct: float
    hallucinated: int
    bonus_matched: int
    average_latency_s: float
    corpus_sha256: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def _files_label(data: dict[str, Any]) -> str:
    files = data.get("files") or ([data["source"]] if data.get("source") else [])
    if not files:
        return "unknown"
    if len(files) == 1:
        return str(files[0])
    return ";".join(str(file) for file in files)


def _strategy_label(data: dict[str, Any]) -> str:
    strategy = data.get("prompt_strategy") or {}
    order = strategy.get("prompt_order", "file-first")
    anchor = strategy.get("anchor_style", "function-name")
    signature = "+signature" if strategy.get("include_signature") else ""
    return f"{order}/{anchor}{signature}"


def result_paths(inputs: list[Path]) -> list[Path]:
    paths: list[Path] = []
    for item in inputs:
        if item.is_dir():
            paths.extend(sorted(item.glob("*.json")))
        else:
            paths.append(item)
    return paths


def summarize_result(path: Path, data: dict[str, Any]) -> RunSummary | None:
    if not data.get("results"):
        return None
    rows = list(index_results(data).values())
    agg = aggregate(rows)
    recall = agg.primary_matched / agg.primary_total * 100 if agg.primary_total else 0.0
    return RunSummary(
        path=str(path),
        model=str(data.get("model", "unknown")),
        files=_files_label(data),
        prompt_strategy=_strategy_label(data),
        schema_version=str(data.get("schema_version", "legacy")),
        run_id=str(data.get("run_id", "legacy")),
        functions=agg.total,
        passed=agg.passed,
        errors=agg.errors,
        primary_matched=agg.primary_matched,
        primary_total=agg.primary_total,
        recall_pct=round(recall, 2),
        hallucinated=agg.hallucinated,
        bonus_matched=agg.bonus_matched,
        average_latency_s=round(agg.average_latency_s, 3),
        corpus_sha256=str(data.get("corpus_sha256", "")),
    )


def load_summaries(paths: list[Path]) -> list[RunSummary]:
    summaries = []
    for path in result_paths(paths):
        summary = summarize_result(path, load_result_file(path))
        if summary is not None:
            summaries.append(summary)
    return summaries


def render_table(summaries: list[RunSummary]) -> str:
    if not summaries:
        return "no usable result JSON files"
    rows = [
        [
            Path(item.path).name,
            item.model,
            f"{item.passed}/{item.functions - item.errors}",
            f"{item.primary_matched}/{item.primary_total}",
            f"{item.recall_pct:.1f}%",
            str(item.hallucinated),
            str(item.errors),
            item.prompt_strategy,
        ]
        for item in summaries
    ]
    headers = [
        "Run",
        "Model",
        "Pass",
        "Primary",
        "Recall",
        "Halluc.",
        "Errors",
        "Prompt",
    ]
    widths = [
        max(len(headers[i]), *(len(row[i]) for row in rows))
        for i in range(len(headers))
    ]
    lines = [
        "  ".join(headers[i].ljust(widths[i]) for i in range(len(headers))),
        "  ".join("-" * widths[i] for i in range(len(headers))),
    ]
    for row in rows:
        lines.append("  ".join(row[i].ljust(widths[i]) for i in range(len(headers))))
    return "\n".join(lines)


def render_csv(summaries: list[RunSummary]) -> str:
    buffer = StringIO()
    writer = csv.DictWriter(buffer, fieldnames=list(RunSummary.__dataclass_fields__))
    writer.writeheader()
    for item in summaries:
        writer.writerow(item.as_dict())
    return buffer.getvalue()


def render_json(summaries: list[RunSummary]) -> str:
    return json.dumps([item.as_dict() for item in summaries], indent=2) + "\n"


def render_summaries(summaries: list[RunSummary], output_format: str) -> str:
    if output_format == "table":
        return render_table(summaries) + "\n"
    if output_format == "csv":
        return render_csv(summaries)
    if output_format == "json":
        return render_json(summaries)
    raise ValueError(f"unsupported summary format: {output_format}")
