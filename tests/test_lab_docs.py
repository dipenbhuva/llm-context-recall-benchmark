from __future__ import annotations

from pathlib import Path


REQUIRED_HEADINGS = [
    "## Objective",
    "## Concepts",
    "## Files to inspect",
    "## Commands to run",
    "## Expected output",
    "## Student task",
    "## Reflection questions",
    "## Verification checklist",
]


def lab_files() -> list[Path]:
    return sorted(Path("labs").glob("[0-9][0-9]_*.md"))


def test_lab_workbook_files_use_required_structure() -> None:
    paths = lab_files()

    assert len(paths) == 9
    for path in paths:
        text = path.read_text()
        for heading in REQUIRED_HEADINGS:
            assert heading in text, f"{path} missing {heading}"


def test_lab_workbook_uses_repo_commands() -> None:
    for path in lab_files():
        text = path.read_text()
        assert "bench.py" in text or "analysis/visualize.py" in text
