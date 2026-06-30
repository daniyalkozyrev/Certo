#!/usr/bin/env python3
"""
Hermes -> Certo adapter  (zero dependencies, stdlib only).

Makes the locally-installed **Hermes Agent** look like an OpenAI-compatible
chat endpoint, so Certo can evaluate it as a normal one-shot agent.

Flow:
    Certo  --POST /v1/chat/completions-->  this adapter
    adapter  --`hermes -z "<task>"`-->  Hermes (runs, returns final answer)
    adapter  --OpenAI-shaped JSON-->  Certo  (judge grades the answer)

We pass ONLY the user's task to Hermes (we ignore Certo's built-in "you are a
coding agent" system prompt) so Hermes answers the task as itself.

── Run it (in the SAME PowerShell where `hermes` works) ──────────────────────
    python C:\\Users\\user\\Desktop\\Certo\\adapters\\hermes_adapter.py

── Then in Certo -> New Evaluation -> Create new ────────────────────────────
    Type     = One-shot
    Base URL = http://localhost:8765/v1
    API key  = hermes          (any non-empty string; if empty, Certo uses a mock!)
    Model    = hermes          (just a label; Hermes uses its own configured model)
    Benchmark: pick a JUDGE-graded one (the judge reads Hermes's answer).
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HOST = "127.0.0.1"
PORT = 8765
HERMES = shutil.which("hermes") or "hermes"
TIMEOUT = 300  # seconds Hermes may spend per task

# --yolo prevents a headless run from hanging on an approval prompt.
# It also lets Hermes run commands without asking — remove it if you'd rather
# the agent never auto-run anything (at the risk of the run hanging).
EXTRA_ARGS = ["--yolo"]


def run_hermes(task: str) -> str:
    cmd = [HERMES, "-z", task, *EXTRA_ARGS]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=TIMEOUT,
        )
    except FileNotFoundError:
        return "[adapter] 'hermes' not found. Run this from the terminal where `hermes` works."
    except subprocess.TimeoutExpired:
        return f"[adapter] Hermes timed out after {TIMEOUT}s."
    out = (proc.stdout or "").strip()
    if not out:
        err = (proc.stderr or "").strip()
        return f"[adapter] Hermes produced no stdout. stderr:\n{err[:1000]}" if err else "[adapter] (empty)"
    return out


class Handler(BaseHTTPRequestHandler):
    def _json(self, code: int, payload: dict) -> None:
        body = json.dumps(payload).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        p = self.path.rstrip("/")
        if p in ("", "/v1", "/health"):
            self._json(200, {"status": "ok", "hermes": HERMES})
        elif p == "/v1/models":
            self._json(200, {"object": "list", "data": [{"id": "hermes", "object": "model"}]})
        else:
            self._json(404, {"error": "not found"})

    def do_POST(self) -> None:
        if not self.path.rstrip("/").endswith("/chat/completions"):
            self._json(404, {"error": "not found"})
            return
        length = int(self.headers.get("Content-Length", 0))
        try:
            body = json.loads(self.rfile.read(length) or b"{}")
        except json.JSONDecodeError:
            self._json(400, {"error": "invalid json"})
            return

        # The task is the last user message; ignore Certo's system prompt.
        task = ""
        for m in body.get("messages", []):
            if m.get("role") == "user" and m.get("content"):
                task = m["content"]
        print(f"[adapter] -> task: {task[:120]!r}", flush=True)
        answer = run_hermes(task)
        print(f"[adapter] <- answer: {answer[:120]!r}", flush=True)

        self._json(200, {
            "id": "chatcmpl-hermes",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": body.get("model", "hermes"),
            "choices": [{
                "index": 0,
                "message": {"role": "assistant", "content": answer},
                "finish_reason": "stop",
            }],
            "usage": {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
        })

    def log_message(self, *a) -> None:  # silence default request logging
        pass


if __name__ == "__main__":
    if shutil.which("hermes") is None:
        print(
            "WARNING: 'hermes' is not on PATH in this shell. Start this adapter from\n"
            "the same PowerShell where the `hermes` command works.",
            file=sys.stderr,
        )
    print(f"Hermes->Certo adapter listening on http://{HOST}:{PORT}/v1   (hermes={HERMES})")
    print("In Certo set Base URL = http://localhost:8765/v1  (API key = any non-empty string)")
    try:
        ThreadingHTTPServer((HOST, PORT), Handler).serve_forever()
    except KeyboardInterrupt:
        print("\nadapter stopped.")
