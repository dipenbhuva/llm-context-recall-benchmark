from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def test_visualize_generates_lab_summary(tmp_path: Path) -> None:
    out_dir = tmp_path / "charts"
    result = subprocess.run(
        [
            sys.executable,
            "analysis/visualize.py",
            "--results-dir", "fixtures/results",
            "--output-dir", str(out_dir),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0
    summary = out_dir / "http_server" / "summary.html"
    assert summary.is_file()
    html = summary.read_text()
    assert "Lab summary" in html
    assert "Worst Failure" in html
    assert "fake-responses" in html


def test_visualize_empty_results_dir_reports_clear_error(tmp_path: Path) -> None:
    results_dir = tmp_path / "empty-results"
    results_dir.mkdir()
    result = subprocess.run(
        [
            sys.executable,
            "analysis/visualize.py",
            "--results-dir", str(results_dir),
            "--output-dir", str(tmp_path / "charts"),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert "no usable result JSON files" in result.stdout
