from __future__ import annotations

import subprocess
import sys
import json
from pathlib import Path


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


def prompt_body(output: str) -> str:
    return output.split("# --- prompt ---\n", 1)[1]


def test_prompt_command_supports_prompt_order_variants() -> None:
    file_first = run_prompt(
        "--corpus", "http_server", "--function", "run_cgi",
        "--prompt-order", "file-first",
    )
    task_first = run_prompt(
        "--corpus", "http_server", "--function", "run_cgi",
        "--prompt-order", "task-first",
    )

    assert file_first.returncode == 0
    assert task_first.returncode == 0
    assert "# prompt_order: file-first" in file_first.stdout
    assert "# prompt_order: task-first" in task_first.stdout
    assert prompt_body(file_first.stdout).startswith("# ======")
    assert prompt_body(task_first.stdout).startswith("Task: reproduce verbatim")
    assert "from the source below" in prompt_body(task_first.stdout)
    assert prompt_body(file_first.stdout) != prompt_body(task_first.stdout)


def test_prompt_command_supports_line_number_anchor() -> None:
    result = run_prompt(
        "--corpus", "http_server", "--function", "run_cgi",
        "--anchor-style", "line-number",
    )

    assert result.returncode == 0
    assert "# anchor_style: line-number" in result.stdout
    assert "starting at line 1076" in result.stdout


def test_run_dump_records_prompt_strategy(tmp_path: Path) -> None:
    dump_path = tmp_path / "strategy.json"
    result = subprocess.run(
        [
            sys.executable, "bench.py", "run",
            "--file", "fixtures/http_server.py",
            "--model", "fake-model",
            "--base-url", "http://127.0.0.1:9",
            "--function", "send_head",
            "--prompt-order", "task-first",
            "--anchor-style", "line-number",
            "--skip-preflight",
            "--fail-fast-after", "1",
            "--dump", str(dump_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert dump_path.is_file()
    data = json.loads(dump_path.read_text())
    assert data["prompt_strategy"] == {
        "prompt_order": "task-first",
        "anchor_style": "line-number",
        "include_signature": False,
    }
