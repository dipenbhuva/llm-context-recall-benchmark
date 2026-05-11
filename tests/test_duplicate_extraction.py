from __future__ import annotations

import subprocess
import sys


def run_extract(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "bench.py", "extract", *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_multi_file_extract_reports_duplicate_names() -> None:
    result = run_extract("--corpus", "multi_file_duplicates", "--all")

    assert result.returncode == 0
    assert "3 function(s) with" in result.stdout
    assert "skipped 1 duplicate function name(s)" in result.stdout
    assert "repeated_name" in result.stdout
    assert "kept=a.py" in result.stdout
    assert "skipped=b.py" in result.stdout


def test_multi_file_show_uses_first_duplicate_occurrence() -> None:
    result = run_extract("--corpus", "multi_file_duplicates", "--show", "repeated_name")

    assert result.returncode == 0
    assert "This first occurrence should be kept" in result.stdout
    assert "This duplicate occurrence should be skipped" not in result.stdout


def test_single_file_extract_has_no_duplicate_warning() -> None:
    result = run_extract("--corpus", "http_server", "--all")

    assert result.returncode == 0
    assert "duplicate function" not in result.stdout
