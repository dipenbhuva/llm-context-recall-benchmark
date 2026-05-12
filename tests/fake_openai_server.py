#!/usr/bin/env python3
"""Deterministic OpenAI-compatible test server for benchmark runtime checks."""
from __future__ import annotations

import argparse
import json
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any


class FakeOpenAIHandler(BaseHTTPRequestHandler):
    server: "FakeOpenAIServer"

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _write_json(self, status: int, payload: dict[str, Any]) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path == "/health":
            self._write_json(200, {"status": "ok"})
            return
        self._write_json(404, {"error": {"message": f"unknown path: {self.path}"}})

    def do_POST(self) -> None:
        if self.path != "/v1/chat/completions":
            self._write_json(404, {"error": {"message": f"unknown path: {self.path}"}})
            return

        length = int(self.headers.get("Content-Length", "0"))
        raw_body = self.rfile.read(length)
        try:
            request = json.loads(raw_body.decode("utf-8"))
        except json.JSONDecodeError as exc:
            self._write_json(400, {"error": {"message": f"invalid json: {exc}"}})
            return

        self.server.record_request(request)
        model = request.get("model", self.server.model)
        completion_tokens = len(self.server.response_text.split())
        self._write_json(
            self.server.response_status,
            {
                "id": "chatcmpl-fake",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": model,
                "choices": [
                    {
                        "index": 0,
                        "message": {
                            "role": "assistant",
                            "content": self.server.response_text,
                        },
                        "finish_reason": "stop",
                    }
                ],
                "usage": {
                    "prompt_tokens": 0,
                    "completion_tokens": completion_tokens,
                    "total_tokens": completion_tokens,
                },
            },
        )


class FakeOpenAIServer(ThreadingHTTPServer):
    def __init__(
        self,
        server_address: tuple[str, int],
        response_text: str,
        response_status: int,
        record_jsonl: Path | None,
        model: str,
    ) -> None:
        super().__init__(server_address, FakeOpenAIHandler)
        self.response_text = response_text
        self.response_status = response_status
        self.record_jsonl = record_jsonl
        self.model = model

    def record_request(self, request: dict[str, Any]) -> None:
        if self.record_jsonl is None:
            return
        with self.record_jsonl.open("a", encoding="utf-8") as f:
            f.write(json.dumps(request) + "\n")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    response = parser.add_mutually_exclusive_group(required=True)
    response.add_argument("--response-file", type=Path)
    response.add_argument("--response-text")
    parser.add_argument("--status", type=int, default=200, help="HTTP status for chat completions")
    parser.add_argument("--record-jsonl", type=Path, help="optional file to append raw requests")
    parser.add_argument("--model", default="fake-model")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    response_text = (
        args.response_file.read_text(encoding="utf-8")
        if args.response_file
        else args.response_text
    )
    server = FakeOpenAIServer(
        (args.host, args.port),
        response_text=response_text,
        response_status=args.status,
        record_jsonl=args.record_jsonl,
        model=args.model,
    )
    print(f"fake OpenAI server listening on http://{args.host}:{args.port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
