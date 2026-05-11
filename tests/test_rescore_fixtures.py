from __future__ import annotations

import subprocess
import sys


def run_rescore(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "bench.py", "rescore", *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_fake_response_fixture_rescores_without_model() -> None:
    result = run_rescore(
        "fixtures/results/send_head_fake_results.json",
        "--file", "fixtures/http_server.py",
    )

    assert result.returncode == 0
    assert "matched=20/20" in result.stdout
    assert "matched= 5/20" in result.stdout
    assert "hallucinated=2" in result.stdout
    assert "=== SUMMARY ===" in result.stdout


def test_fake_response_fixture_relax_indent_changes_score() -> None:
    strict = run_rescore(
        "fixtures/results/send_head_fake_results.json",
        "--file", "fixtures/http_server.py",
    )
    relaxed = run_rescore(
        "fixtures/results/send_head_fake_results.json",
        "--file", "fixtures/http_server.py",
        "--relax-indent",
    )

    assert strict.returncode == 0
    assert relaxed.returncode == 0
    assert "matched= 3/20" in strict.stdout
    assert "matched= 3/20" not in relaxed.stdout
    assert relaxed.stdout.count("matched=20/20") >= 2
    assert "scored with relax_indent=true" in relaxed.stdout
