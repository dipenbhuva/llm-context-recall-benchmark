#!/usr/bin/env python3
"""Run deterministic lab runtime checks from a checkout."""
from __future__ import annotations

import argparse
import json
import socket
import subprocess
import sys
import time
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


REPO_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_WORK_DIR = Path("/tmp/llm-context-recall-lab-checks")


@dataclass(frozen=True)
class CheckOutput:
    command: list[str]
    returncode: int
    stdout: str
    stderr: str
    artifacts: list[Path]


@dataclass(frozen=True)
class RuntimeCheck:
    check_id: str
    check_type: str
    description: str
    runner: Callable[[Path], CheckOutput]
    stdout_contains: tuple[str, ...] = ()
    required_artifacts: tuple[Path, ...] = ()


@dataclass(frozen=True)
class CheckResult:
    check_id: str
    check_type: str
    description: str
    command: str
    status: str
    seconds: float
    errors: list[str]
    artifacts: list[str]


def py_cmd(*args: str | Path) -> list[str]:
    return [sys.executable, *[str(arg) for arg in args]]


def command_runner(*args: str | Path, artifacts: list[Path] | None = None) -> Callable[[Path], CheckOutput]:
    command = py_cmd(*args)

    def run(_: Path) -> CheckOutput:
        result = subprocess.run(
            command,
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        return CheckOutput(
            command=command,
            returncode=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
            artifacts=artifacts or [],
        )

    return run


def synthetic_runner(work_dir: Path) -> CheckOutput:
    out_path = work_dir / "runtime_synthetic.py"
    command = py_cmd(
        "-c",
        (
            "import subprocess, sys; "
            f"out={str(out_path)!r}; "
            "subprocess.check_call([sys.executable, 'scripts/generate_synthetic_corpus.py', "
            "'--functions', '10', '--body-lines', '30', '--seed', '7', '--out', out]); "
            "subprocess.check_call([sys.executable, 'bench.py', 'extract', '--file', out, '--all'])"
        ),
    )
    result = subprocess.run(
        command,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    return CheckOutput(
        command=command,
        returncode=result.returncode,
        stdout=result.stdout,
        stderr=result.stderr,
        artifacts=[out_path],
    )


def _free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def _wait_for_health(port: int) -> None:
    deadline = time.monotonic() + 5
    url = f"http://127.0.0.1:{port}/health"
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=0.2) as response:
                if response.status == 200:
                    return
        except OSError:
            time.sleep(0.05)
    raise RuntimeError("fake OpenAI server did not become healthy")


def mock_llm_runner(work_dir: Path) -> CheckOutput:
    port = _free_port()
    dump_path = work_dir / "fake-run.json"
    record_path = work_dir / "fake-requests.jsonl"
    server_command = py_cmd(
        "tests/fake_openai_server.py",
        "--port", str(port),
        "--response-file", "fixtures/responses/send_head_perfect.txt",
        "--record-jsonl", record_path,
    )
    run_command = py_cmd(
        "bench.py", "run",
        "--file", "fixtures/http_server.py",
        "--model", "fake-model",
        "--base-url", f"http://127.0.0.1:{port}",
        "--function", "send_head",
        "--skip-preflight",
        "--dump", dump_path,
    )
    server = subprocess.Popen(
        server_command,
        cwd=REPO_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        _wait_for_health(port)
        result = subprocess.run(
            run_command,
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        return CheckOutput(
            command=run_command,
            returncode=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
            artifacts=[dump_path, record_path],
        )
    except Exception as exc:
        return CheckOutput(
            command=run_command,
            returncode=1,
            stdout="",
            stderr=str(exc),
            artifacts=[dump_path, record_path],
        )
    finally:
        server.terminate()
        server.wait(timeout=5)


def build_checks(work_dir: Path) -> list[RuntimeCheck]:
    charts_dir = work_dir / "charts"
    return [
        RuntimeCheck(
            "PR-001-RT-03",
            "ci",
            "Run no-LLM smoke test",
            command_runner("smoke_test.py"),
            stdout_contains=("all smoke checks passed",),
        ),
        RuntimeCheck(
            "PR-001-RT-04",
            "ci",
            "Extract all http_server targets",
            command_runner("bench.py", "extract", "--corpus", "http_server", "--all"),
            stdout_contains=("11 function(s)", "send_head", "run_cgi"),
        ),
        RuntimeCheck(
            "PR-002-RT-01",
            "ci",
            "Print exact prompt without a model call",
            command_runner("bench.py", "prompt", "--corpus", "http_server", "--function", "run_cgi"),
            stdout_contains=("# function: run_cgi", "Task: reproduce verbatim"),
        ),
        RuntimeCheck(
            "PR-004-RT-01",
            "local-no-llm",
            "Generate and extract a synthetic recall corpus",
            synthetic_runner,
            stdout_contains=("target_000", "target_009"),
        ),
        RuntimeCheck(
            "PR-006-RT-01",
            "ci",
            "Report duplicate function names",
            command_runner("bench.py", "extract", "--corpus", "multi_file_duplicates", "--all"),
            stdout_contains=("skipped", "repeated_name"),
        ),
        RuntimeCheck(
            "PR-007-RT-01",
            "ci",
            "Rescore fake responses without a model",
            command_runner(
                "bench.py", "rescore",
                "fixtures/results/send_head_fake_results.json",
                "--file", "fixtures/http_server.py",
            ),
            stdout_contains=("=== SUMMARY ===", "matched=20/20", "hallucinated=2"),
        ),
        RuntimeCheck(
            "PR-009-RT-02",
            "ci",
            "Generate lab dashboard pages from fixture results",
            command_runner(
                "analysis/visualize.py",
                "--results-dir", "fixtures/results",
                "--output-dir", charts_dir,
                artifacts=[charts_dir / "index.html", charts_dir / "http_server" / "summary.html"],
            ),
            stdout_contains=("Loaded", "http_server"),
            required_artifacts=(charts_dir / "index.html", charts_dir / "http_server" / "summary.html"),
        ),
        RuntimeCheck(
            "PR-011-RT-01",
            "mock-llm",
            "Run benchmark through deterministic fake OpenAI server",
            mock_llm_runner,
            stdout_contains=("[PASS]", "matched=20/20"),
        ),
        RuntimeCheck(
            "PR-012-RT-01",
            "ci",
            "Compare two fixture result dumps",
            command_runner(
                "bench.py", "compare",
                "fixtures/results/compare_baseline.json",
                "fixtures/results/compare_candidate.json",
            ),
            stdout_contains=("Primary matched", "send_head", "pass no -> yes"),
        ),
        RuntimeCheck(
            "PR-015-RT-01",
            "ci",
            "Strict-validate a schema-v2 result fixture",
            command_runner(
                "bench.py", "validate",
                "fixtures/results/compare_candidate.json",
                "--strict",
            ),
            stdout_contains=("PASS", "0 errors, 0 warnings"),
        ),
        RuntimeCheck(
            "PR-016-RT-01",
            "ci",
            "Generate a Markdown model report from fixture results",
            command_runner(
                "bench.py", "report",
                "fixtures/results/compare_candidate.json",
                "--baseline", "fixtures/results/compare_baseline.json",
                "--out", work_dir / "model-report.md",
                artifacts=[work_dir / "model-report.md"],
            ),
            stdout_contains=("Report written to",),
            required_artifacts=(work_dir / "model-report.md",),
        ),
        RuntimeCheck(
            "PR-017-RT-01",
            "ci",
            "Diagnose fake-response failure modes",
            command_runner(
                "bench.py", "diagnose",
                "fixtures/results/send_head_fake_results.json",
            ),
            stdout_contains=(
                "perfect_recall",
                "truncated_or_incomplete",
                "pass_with_hallucination",
                "format_or_wrong_span",
            ),
        ),
        RuntimeCheck(
            "PR-018-RT-01",
            "ci",
            "Export result summaries as CSV",
            command_runner(
                "bench.py", "summarize",
                "fixtures/results",
                "--format", "csv",
                "--out", work_dir / "run-summary.csv",
                artifacts=[work_dir / "run-summary.csv"],
            ),
            stdout_contains=("Summary written to",),
            required_artifacts=(work_dir / "run-summary.csv",),
        ),
        RuntimeCheck(
            "PR-019-RT-01",
            "ci",
            "Analyze recall by source depth",
            command_runner(
                "bench.py", "depth",
                "fixtures/results/compare_candidate.json",
                "--json", work_dir / "depth-analysis.json",
                artifacts=[work_dir / "depth-analysis.json"],
            ),
            stdout_contains=("DEPTH ANALYSIS", "middle", "send_head"),
            required_artifacts=(work_dir / "depth-analysis.json",),
        ),
    ]


def run_check(check: RuntimeCheck, work_dir: Path) -> CheckResult:
    start = time.monotonic()
    output = check.runner(work_dir)
    seconds = time.monotonic() - start
    errors = []
    if output.returncode != 0:
        errors.append(f"exit code {output.returncode}")
    for needle in check.stdout_contains:
        if needle not in output.stdout:
            errors.append(f"stdout missing {needle!r}")
    artifacts_to_check = list(dict.fromkeys([*check.required_artifacts, *output.artifacts]))
    for artifact in artifacts_to_check:
        if not artifact.exists():
            errors.append(f"missing artifact {artifact}")
    status = "pass" if not errors else "fail"
    return CheckResult(
        check_id=check.check_id,
        check_type=check.check_type,
        description=check.description,
        command=" ".join(output.command),
        status=status,
        seconds=seconds,
        errors=errors,
        artifacts=[str(p) for p in output.artifacts],
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work-dir", type=Path, default=DEFAULT_WORK_DIR)
    parser.add_argument("--only", action="append", default=[], help="run one check ID; repeatable")
    parser.add_argument("--skip-mock", action="store_true", help="skip mock-llm checks")
    parser.add_argument("--list", action="store_true", help="list available checks without running them")
    parser.add_argument("--json", type=Path, help="write a machine-readable result report")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    args.work_dir.mkdir(parents=True, exist_ok=True)
    checks = build_checks(args.work_dir)
    if args.skip_mock:
        checks = [check for check in checks if check.check_type != "mock-llm"]
    if args.only:
        selected = set(args.only)
        checks = [check for check in checks if check.check_id in selected]
        missing = selected - {check.check_id for check in checks}
        if missing:
            raise SystemExit(f"unknown check id(s): {', '.join(sorted(missing))}")

    if args.list:
        for check in checks:
            print(f"{check.check_id}\t{check.check_type}\t{check.description}")
        return 0

    results = []
    for check in checks:
        result = run_check(check, args.work_dir)
        results.append(result)
        print(f"[{result.status.upper()}] {result.check_id} {result.description} ({result.seconds:.2f}s)")
        for error in result.errors:
            print(f"  - {error}")

    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(
            json.dumps([result.__dict__ for result in results], indent=2),
            encoding="utf-8",
        )

    failed = [result for result in results if result.status != "pass"]
    print(f"\n{len(results) - len(failed)}/{len(results)} checks passed")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
