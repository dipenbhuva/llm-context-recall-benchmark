from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path


def run_summary(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "bench.py", "summarize", *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_summarize_command_prints_table() -> None:
    result = run_summary(
        "fixtures/results/compare_baseline.json",
        "fixtures/results/compare_candidate.json",
    )

    assert result.returncode == 0
    assert "fixture-baseline" in result.stdout
    assert "fixture-candidate" in result.stdout
    assert "35/40" in result.stdout
    assert "38/40" in result.stdout
    assert "95.0%" in result.stdout


def test_summarize_command_writes_csv(tmp_path: Path) -> None:
    out = tmp_path / "summary.csv"
    result = run_summary(
        "fixtures/results/compare_baseline.json",
        "fixtures/results/compare_candidate.json",
        "--format", "csv",
        "--out", str(out),
    )

    assert result.returncode == 0
    assert f"Summary written to {out}" in result.stdout
    rows = list(csv.DictReader(out.read_text().splitlines()))
    assert rows[0]["model"] == "fixture-baseline"
    assert rows[1]["model"] == "fixture-candidate"
    assert rows[1]["recall_pct"] == "95.0"


def test_summarize_command_writes_json_for_directory(tmp_path: Path) -> None:
    out = tmp_path / "summary.json"
    result = run_summary("fixtures/results", "--format", "json", "--out", str(out))

    assert result.returncode == 0
    data = json.loads(out.read_text())
    models = {row["model"] for row in data}
    assert "fixture-baseline" in models
    assert "fixture-candidate" in models
    assert "fake-responses" in models


def test_summarize_command_fails_for_empty_directory(tmp_path: Path) -> None:
    result = run_summary(str(tmp_path))

    assert result.returncode == 1
    assert "no usable result JSON files" in result.stdout
