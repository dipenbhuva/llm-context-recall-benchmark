from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def run_depth(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "bench.py", "depth", *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_depth_command_prints_bucket_summary() -> None:
    result = run_depth("fixtures/results/compare_candidate.json")

    assert result.returncode == 0
    assert "=== DEPTH ANALYSIS ===" in result.stdout
    assert "Bucket" in result.stdout
    assert "middle" in result.stdout
    assert "send_head" in result.stdout
    assert "list_directory" in result.stdout


def test_depth_command_writes_json(tmp_path: Path) -> None:
    out = tmp_path / "depth.json"
    result = run_depth("fixtures/results/compare_candidate.json", "--json", str(out))

    assert result.returncode == 0
    data = json.loads(out.read_text())
    assert data["buckets"][0]["bucket"] == "middle"
    assert data["buckets"][0]["functions"] == 2
    functions = {row["function"] for row in data["functions"]}
    assert functions == {"send_head", "list_directory"}


def test_depth_command_handles_missing_source(tmp_path: Path) -> None:
    dump = tmp_path / "missing-source.json"
    dump.write_text(
        json.dumps({
            "files": ["missing.py"],
            "model": "missing-source",
            "results": [
                {
                    "function": "target",
                    "passed": False,
                    "primary_matched": 0,
                    "primary_total": 20,
                    "hallucinated": 0,
                    "bonus_matched": 0,
                }
            ],
        })
    )

    result = run_depth(str(dump))

    assert result.returncode == 0
    assert "unknown" in result.stdout
    assert "target" in result.stdout
