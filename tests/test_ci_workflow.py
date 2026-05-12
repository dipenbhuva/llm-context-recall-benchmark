from __future__ import annotations

from pathlib import Path


def test_lab_runtime_workflow_runs_tests_and_runtime_checks() -> None:
    workflow = Path(".github/workflows/lab-runtime-checks.yml")
    text = workflow.read_text()

    assert "uv sync --dev --frozen" in text
    assert "uv run pytest" in text
    assert "scripts/run_lab_runtime_checks.py" in text
    assert "lab-runtime-report" in text
