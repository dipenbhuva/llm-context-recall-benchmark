from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def run_bundle(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "bench.py", "bundle", *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_bundle_command_creates_review_artifacts(tmp_path: Path) -> None:
    out_dir = tmp_path / "bundle"
    result = run_bundle(
        "fixtures/results/compare_candidate.json",
        "--baseline", "fixtures/results/compare_baseline.json",
        "--out-dir", str(out_dir),
    )

    assert result.returncode == 0
    assert f"Bundle written to {out_dir}" in result.stdout
    expected = {
        "candidate-result.json",
        "baseline-result.json",
        "validation.json",
        "diagnosis.json",
        "depth-analysis.json",
        "run-summary.csv",
        "model-report.md",
        "manifest.json",
    }
    assert expected == {path.name for path in out_dir.iterdir()}
    assert "fixture-candidate" in (out_dir / "model-report.md").read_text()
    assert "recall_pct" in (out_dir / "run-summary.csv").read_text()

    manifest = json.loads((out_dir / "manifest.json").read_text())
    assert manifest["candidate"] == "fixtures/results/compare_candidate.json"
    assert manifest["baseline"] == "fixtures/results/compare_baseline.json"
    assert set(manifest["artifacts"]) == expected - {"manifest.json"}


def test_bundle_command_supports_candidate_only(tmp_path: Path) -> None:
    out_dir = tmp_path / "bundle"
    result = run_bundle("fixtures/results/compare_candidate.json", "--out-dir", str(out_dir))

    assert result.returncode == 0
    assert not (out_dir / "baseline-result.json").exists()
    assert (out_dir / "model-report.md").is_file()
