from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def run_diagnose(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "bench.py", "diagnose", *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_diagnose_command_classifies_fake_responses() -> None:
    result = run_diagnose("fixtures/results/send_head_fake_results.json")

    assert result.returncode == 0
    assert "=== FAILURE DIAGNOSIS ===" in result.stdout
    assert "perfect_recall" in result.stdout
    assert "truncated_or_incomplete" in result.stdout
    assert "pass_with_hallucination" in result.stdout
    assert "format_or_wrong_span" in result.stdout
    assert "send_head:truncated" in result.stdout


def test_diagnose_command_writes_json(tmp_path: Path) -> None:
    out = tmp_path / "diagnosis.json"
    result = run_diagnose(
        "fixtures/results/send_head_fake_results.json",
        "--json", str(out),
    )

    assert result.returncode == 0
    data = json.loads(out.read_text())
    categories = {item["category"] for item in data}
    assert "perfect_recall" in categories
    assert "truncated_or_incomplete" in categories
    assert "pass_with_hallucination" in categories
    assert "format_or_wrong_span" in categories
