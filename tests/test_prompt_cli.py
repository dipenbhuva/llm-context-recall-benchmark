from __future__ import annotations

import subprocess
import sys


def run_prompt(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "bench.py", "prompt", *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_prompt_command_prints_exact_prompt_metadata() -> None:
    result = run_prompt("--corpus", "http_server", "--function", "run_cgi")

    assert result.returncode == 0
    assert result.stderr == ""
    assert "# function: run_cgi" in result.stdout
    assert "# prompt_chars:" in result.stdout
    assert "Task: reproduce verbatim" in result.stdout
    assert "def run_cgi(" in result.stdout
    assert "/no_think" in result.stdout


def test_prompt_command_supports_single_file_mode() -> None:
    result = run_prompt("--file", "fixtures/http_server.py", "--function", "send_head")

    assert result.returncode == 0
    assert "# function: send_head" in result.stdout
    assert "Task: reproduce verbatim" in result.stdout


def test_prompt_command_reports_missing_function() -> None:
    result = run_prompt("--corpus", "http_server", "--function", "nope")

    assert result.returncode == 1
    assert "function 'nope' not found" in result.stderr
