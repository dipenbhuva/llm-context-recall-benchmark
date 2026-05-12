from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_runtime_check_runner_lists_checks() -> None:
    result = subprocess.run(
        [sys.executable, "scripts/run_lab_runtime_checks.py", "--list"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "PR-001-RT-03" in result.stdout
    assert "PR-011-RT-01" in result.stdout
    assert "PR-012-RT-01" in result.stdout
    assert "PR-015-RT-01" in result.stdout
    assert "PR-016-RT-01" in result.stdout


def test_runtime_check_runner_can_run_one_check(tmp_path: Path) -> None:
    report_path = tmp_path / "report.json"
    result = subprocess.run(
        [
            sys.executable,
            "scripts/run_lab_runtime_checks.py",
            "--work-dir", str(tmp_path),
            "--only", "PR-012-RT-01",
            "--json", str(report_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    assert "[PASS] PR-012-RT-01" in result.stdout
    data = json.loads(report_path.read_text())
    assert data[0]["check_id"] == "PR-012-RT-01"
    assert data[0]["status"] == "pass"
