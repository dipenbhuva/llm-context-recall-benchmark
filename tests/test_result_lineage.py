from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def run_error_dump(path: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable, "bench.py", "run",
            "--file", "fixtures/http_server.py",
            "--model", "fake-model",
            "--base-url", "http://127.0.0.1:9",
            "--function", "send_head",
            "--skip-preflight",
            "--fail-fast-after", "1",
            "--dump", str(path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )


def test_run_dump_includes_lineage_metadata(tmp_path: Path) -> None:
    dump_path = tmp_path / "lineage.json"
    result = run_error_dump(dump_path)

    assert result.returncode == 1
    data = json.loads(dump_path.read_text())
    assert data["schema_version"] == 2
    assert data["run_id"]
    assert data["created_at"]
    assert data["python_version"].startswith(f"{sys.version_info.major}.{sys.version_info.minor}")
    assert len(data["corpus_sha256"]) == 64
    assert data["prompt_template_id"] == "context-recall-v2"
    assert data["sample_k"] == 16
    assert data["sample_seed"] == 42
    assert data["selected_functions"] == ["send_head"]
    assert data["git_sha"] is None or len(data["git_sha"]) == 40


def test_corpus_checksum_is_stable_for_same_source(tmp_path: Path) -> None:
    first = tmp_path / "first.json"
    second = tmp_path / "second.json"

    assert run_error_dump(first).returncode == 1
    assert run_error_dump(second).returncode == 1

    first_data = json.loads(first.read_text())
    second_data = json.loads(second.read_text())
    assert first_data["corpus_sha256"] == second_data["corpus_sha256"]
    assert first_data["run_id"] != second_data["run_id"]
