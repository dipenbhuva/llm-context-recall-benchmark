from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def run_compare(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "bench.py", "compare", *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_compare_command_reports_aggregate_and_function_deltas() -> None:
    result = run_compare(
        "fixtures/results/compare_baseline.json",
        "fixtures/results/compare_candidate.json",
    )

    assert result.returncode == 0
    assert "=== RESULT COMPARISON ===" in result.stdout
    assert "Common functions: 2" in result.stdout
    assert "Pass" in result.stdout
    assert "1/2" in result.stdout
    assert "2/2" in result.stdout
    assert "Primary matched" in result.stdout
    assert "35/40" in result.stdout
    assert "38/40" in result.stdout
    assert "+3" in result.stdout
    assert "send_head" in result.stdout
    assert "matched 15 -> 20 (+5)" in result.stdout
    assert "pass no -> yes" in result.stdout


def test_compare_command_reports_missing_functions(tmp_path: Path) -> None:
    left = tmp_path / "left.json"
    right = tmp_path / "right.json"
    left.write_text(
        """{
          "model": "left",
          "results": [
            {"function": "shared", "passed": true, "primary_matched": 20, "primary_total": 20},
            {"function": "only_left", "passed": true, "primary_matched": 20, "primary_total": 20}
          ]
        }"""
    )
    right.write_text(
        """{
          "model": "right",
          "results": [
            {"function": "shared", "passed": true, "primary_matched": 19, "primary_total": 20},
            {"function": "only_right", "passed": true, "primary_matched": 20, "primary_total": 20}
          ]
        }"""
    )

    result = run_compare(str(left), str(right))

    assert result.returncode == 0
    assert "Common functions: 1" in result.stdout
    assert "Only in A: only_left" in result.stdout
    assert "Only in B: only_right" in result.stdout


def test_compare_command_fails_when_no_functions_overlap(tmp_path: Path) -> None:
    left = tmp_path / "left.json"
    right = tmp_path / "right.json"
    left.write_text("""{"model": "left", "results": [{"function": "left_only"}]}""")
    right.write_text("""{"model": "right", "results": [{"function": "right_only"}]}""")

    result = run_compare(str(left), str(right))

    assert result.returncode == 1
    assert "No common functions to compare" in result.stdout
