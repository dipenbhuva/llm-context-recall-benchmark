from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def run_validate(*args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "bench.py", "validate", *args],
        capture_output=True,
        text=True,
        check=False,
    )


def test_validate_accepts_schema_v2_fixture_in_strict_mode() -> None:
    result = run_validate("fixtures/results/compare_candidate.json", "--strict")

    assert result.returncode == 0
    assert "PASS fixtures/results/compare_candidate.json" in result.stdout
    assert "0 errors, 0 warnings" in result.stdout


def test_validate_allows_legacy_fixture_with_warning() -> None:
    result = run_validate("fixtures/results/send_head_fake_results.json")

    assert result.returncode == 0
    assert "PASS fixtures/results/send_head_fake_results.json" in result.stdout
    assert "legacy result without schema_version" in result.stdout


def test_validate_rejects_legacy_fixture_in_strict_mode() -> None:
    result = run_validate("fixtures/results/send_head_fake_results.json", "--strict")

    assert result.returncode == 1
    assert "FAIL fixtures/results/send_head_fake_results.json" in result.stdout
    assert "strict mode requires schema version 2" in result.stdout


def test_validate_reports_malformed_result_json(tmp_path: Path) -> None:
    bad = tmp_path / "bad.json"
    bad.write_text(
        json.dumps({
            "model": "bad-fixture",
            "schema_version": 2,
            "results": [
                {
                    "function": "send_head",
                    "passed": "yes",
                    "primary_matched": 21,
                    "primary_total": 20,
                    "hallucinated": -1,
                    "bonus_matched": 0,
                }
            ],
        })
    )

    result = run_validate(str(bad), "--strict")

    assert result.returncode == 1
    assert "$.run_id" in result.stdout
    assert "$.results[0].passed" in result.stdout
    assert "cannot exceed primary_total" in result.stdout
    assert "must be non-negative" in result.stdout


def test_validate_can_emit_json(tmp_path: Path) -> None:
    out = tmp_path / "validation.json"
    result = run_validate("fixtures/results/send_head_fake_results.json", "--json", str(out))

    assert result.returncode == 0
    data = json.loads(out.read_text())
    assert data[0]["level"] == "warning"
    assert data[0]["path"] == "$.schema_version"
