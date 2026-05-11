from __future__ import annotations

import hashlib
import subprocess
import sys
from pathlib import Path

from bench.extract import extract


def run_generator(out: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            "scripts/generate_synthetic_corpus.py",
            "--out",
            str(out),
            *args,
        ],
        capture_output=True,
        text=True,
        check=False,
    )


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_synthetic_generator_creates_extractable_functions(tmp_path: Path) -> None:
    out = tmp_path / "synth.py"
    result = run_generator(out, "--functions", "10", "--body-lines", "30", "--seed", "7")

    assert result.returncode == 0
    assert out.is_file()
    targets = extract(out)
    assert len(targets) == 10
    assert [t.name for t in targets] == [f"target_{i:03d}" for i in range(10)]
    assert all(len(t.body_lines) == 30 for t in targets)


def test_synthetic_generator_is_deterministic(tmp_path: Path) -> None:
    first = tmp_path / "first.py"
    second = tmp_path / "second.py"

    first_result = run_generator(first, "--functions", "10", "--body-lines", "30", "--seed", "7")
    second_result = run_generator(second, "--functions", "10", "--body-lines", "30", "--seed", "7")

    assert first_result.returncode == 0
    assert second_result.returncode == 0
    assert sha256(first) == sha256(second)


def test_synthetic_generator_rejects_unextractable_body_size(tmp_path: Path) -> None:
    out = tmp_path / "too_short.py"
    result = run_generator(out, "--functions", "1", "--body-lines", "19")

    assert result.returncode != 0
    assert "body_lines must be at least 20" in result.stderr


def test_synthetic_generator_creates_distractor_groups(tmp_path: Path) -> None:
    out = tmp_path / "distractors.py"
    result = run_generator(
        out,
        "--functions", "40",
        "--body-lines", "30",
        "--distractor-groups", "8",
        "--near-duplicate-rate", "0.8",
    )

    assert result.returncode == 0
    text = out.read_text()
    targets = extract(out)
    assert len(targets) == 40
    assert targets[0].name == "target_g000_m000"
    assert targets[8].name == "target_g000_m001"
    assert text.count("UNIQUE_MARKER_GROUP_") == 40
    assert "group_id = 0" in text


def test_synthetic_generator_rejects_invalid_near_duplicate_rate(tmp_path: Path) -> None:
    out = tmp_path / "invalid.py"
    result = run_generator(out, "--near-duplicate-rate", "1.5")

    assert result.returncode != 0
    assert "must be between 0.0 and 1.0" in result.stderr
