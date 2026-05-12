from __future__ import annotations

import json
import socket
import subprocess
import sys
import time
import urllib.request
from pathlib import Path


def free_port() -> int:
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


def wait_for_health(port: int) -> None:
    deadline = time.monotonic() + 5
    url = f"http://127.0.0.1:{port}/health"
    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=0.2) as response:
                if response.status == 200:
                    return
        except OSError:
            time.sleep(0.05)
    raise AssertionError("fake OpenAI server did not become healthy")


def test_fake_server_exercises_full_run_path(tmp_path: Path) -> None:
    port = free_port()
    dump_path = tmp_path / "fake-run.json"
    record_path = tmp_path / "requests.jsonl"
    server = subprocess.Popen(
        [
            sys.executable,
            "tests/fake_openai_server.py",
            "--port", str(port),
            "--response-file", "fixtures/responses/send_head_perfect.txt",
            "--record-jsonl", str(record_path),
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        wait_for_health(port)
        result = subprocess.run(
            [
                sys.executable, "bench.py", "run",
                "--file", "fixtures/http_server.py",
                "--model", "fake-model",
                "--base-url", f"http://127.0.0.1:{port}",
                "--function", "send_head",
                "--skip-preflight",
                "--dump", str(dump_path),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
    finally:
        server.terminate()
        server.wait(timeout=5)

    assert result.returncode == 0
    assert "=== send_head" in result.stdout
    assert "[PASS]" in result.stdout
    assert "matched=20/20" in result.stdout
    assert dump_path.is_file()

    data = json.loads(dump_path.read_text())
    assert data["model"] == "fake-model"
    assert data["base_url"] == f"http://127.0.0.1:{port}"
    assert data["results"][0]["passed"] is True
    assert data["results"][0]["primary_matched"] == 20

    requests = [json.loads(line) for line in record_path.read_text().splitlines()]
    assert len(requests) == 1
    assert requests[0]["model"] == "fake-model"
    assert requests[0]["stream"] is False
    assert requests[0]["messages"][0]["role"] == "user"
