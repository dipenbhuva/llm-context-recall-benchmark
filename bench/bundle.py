"""Create a reviewable artifact bundle from benchmark result JSON."""
from __future__ import annotations

import json
import shutil
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from .depth import load_depth_rows, render_depth_json
from .diagnose import load_and_diagnose
from .model_report import ReportPolicy, render_model_report
from .summary import load_summaries, render_csv
from .validate import load_result_file, validate_result


@dataclass(frozen=True)
class BundleManifest:
    created_at: str
    candidate: str
    baseline: str | None
    artifacts: list[str]

    def as_dict(self) -> dict:
        return asdict(self)


def create_bundle(
    candidate_path: Path,
    out_dir: Path,
    *,
    baseline_path: Path | None = None,
    policy: ReportPolicy | None = None,
) -> list[Path]:
    policy = policy or ReportPolicy()
    out_dir.mkdir(parents=True, exist_ok=True)

    candidate_data = load_result_file(candidate_path)
    baseline_data = load_result_file(baseline_path) if baseline_path is not None else None

    artifacts: list[Path] = []
    copied_candidate = out_dir / "candidate-result.json"
    shutil.copy2(candidate_path, copied_candidate)
    artifacts.append(copied_candidate)

    copied_baseline = None
    if baseline_path is not None:
        copied_baseline = out_dir / "baseline-result.json"
        shutil.copy2(baseline_path, copied_baseline)
        artifacts.append(copied_baseline)

    validation_path = out_dir / "validation.json"
    validation_path.write_text(
        json.dumps([issue.as_dict() for issue in validate_result(candidate_data, strict=True)], indent=2),
        encoding="utf-8",
    )
    artifacts.append(validation_path)

    diagnosis_path = out_dir / "diagnosis.json"
    diagnosis_path.write_text(
        json.dumps([item.as_dict() for item in load_and_diagnose(candidate_path)], indent=2),
        encoding="utf-8",
    )
    artifacts.append(diagnosis_path)

    depth_path = out_dir / "depth-analysis.json"
    depth_path.write_text(render_depth_json(load_depth_rows(candidate_path)), encoding="utf-8")
    artifacts.append(depth_path)

    summary_inputs = [candidate_path]
    if baseline_path is not None:
        summary_inputs.insert(0, baseline_path)
    summary_path = out_dir / "run-summary.csv"
    summary_path.write_text(render_csv(load_summaries(summary_inputs)), encoding="utf-8")
    artifacts.append(summary_path)

    report_path = out_dir / "model-report.md"
    report_path.write_text(
        render_model_report(
            candidate_path,
            candidate_data,
            baseline_path=baseline_path,
            baseline_data=baseline_data,
            policy=policy,
        ),
        encoding="utf-8",
    )
    artifacts.append(report_path)

    manifest = BundleManifest(
        created_at=datetime.now(timezone.utc).isoformat(),
        candidate=str(candidate_path),
        baseline=str(baseline_path) if baseline_path else None,
        artifacts=[path.name for path in artifacts],
    )
    manifest_path = out_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest.as_dict(), indent=2), encoding="utf-8")
    artifacts.append(manifest_path)
    return artifacts


def render_bundle_result(out_dir: Path, artifacts: list[Path]) -> str:
    lines = [f"Bundle written to {out_dir}", "Artifacts:"]
    lines.extend(f"  - {path.name}" for path in artifacts)
    return "\n".join(lines)
