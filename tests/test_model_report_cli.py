from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def run_report(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "bench.py", "report", *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_report_command_writes_markdown_with_baseline(tmp_path: Path) -> None:
    out = tmp_path / "model-report.md"
    result = run_report(
        "fixtures/results/compare_candidate.json",
        "--baseline", "fixtures/results/compare_baseline.json",
        "--out", str(out),
    )

    assert result.returncode == 0
    assert f"Report written to {out}" in result.stdout
    text = out.read_text()
    assert "# Model Recall Report" in text
    assert "fixture-candidate" in text
    assert "Strict result contract: **PASS" in text
    assert "Primary lines matched | 38/40 (95.0%)" in text
    assert "Recommendation: **needs more evals**" in text
    assert "Baseline Comparison" in text
    assert "pass no -> yes" in text


def test_report_command_prints_markdown_to_stdout() -> None:
    result = run_report("fixtures/results/compare_candidate.json")

    assert result.returncode == 0
    assert result.stdout.startswith("# Model Recall Report")
    assert "Worst Failures" in result.stdout


def test_report_command_fails_for_strict_validation_errors() -> None:
    result = run_report("fixtures/results/send_head_fake_results.json")

    assert result.returncode == 1
    assert "strict validation failed" in result.stderr
    assert "# Model Recall Report" in result.stdout


def test_report_command_can_allow_invalid_legacy_result() -> None:
    result = run_report("fixtures/results/send_head_fake_results.json", "--allow-invalid")

    assert result.returncode == 0
    assert "Strict result contract: **FAIL" in result.stdout
