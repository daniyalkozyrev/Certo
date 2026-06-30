"""Agent Trajectory Logging — stream an agent's sandbox output into one transcript.

Instead of running the agent and grabbing stdout/stderr at the end, we attach
`on_stdout` / `on_stderr` callbacks to E2B's `sandbox.commands.run()` so every
line is captured live, timestamped and labelled, into a single ordered
transcript. That transcript is exactly what we hand to the LLM-as-a-Judge.

Verified against the installed E2B SDK:
    sandbox.commands.run(cmd, on_stdout: Callable[[str], None],
                              on_stderr: Callable[[str], None], timeout=..., ...)
The callbacks receive a plain `str` chunk; AsyncSandbox accepts sync callbacks.

Usage (FastAPI-friendly, async):
    run = await run_agent_with_transcript(
        cmd='python /home/user/agent/run.py "fix the failing test"',
        log_path="logs/run-123.log",
    )
    # run.transcript  -> feed to the judge; run.exit_code -> success/fail
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class TranscriptCollector:
    """Collects streamed stdout/stderr chunks into one ordered, line-clean log.

    E2B may deliver partial lines, so we buffer per stream and only emit a
    transcript line once a newline is seen (flushing any remainder at the end).
    """

    def __init__(self) -> None:
        self._t0 = time.monotonic()
        self.entries: list[str] = []
        self._buf: dict[str, str] = {"OUT": "", "ERR": ""}

    # ── callbacks handed to E2B ──────────────────────────────
    def on_stdout(self, data: str) -> None:
        self._feed("OUT", data)

    def on_stderr(self, data: str) -> None:
        self._feed("ERR", data)

    # ── internals ────────────────────────────────────────────
    def _feed(self, stream: str, data: str) -> None:
        self._buf[stream] += data
        # split keeps the trailing partial line as the new buffer
        *complete, self._buf[stream] = self._buf[stream].split("\n")
        for line in complete:
            self._emit(stream, line.rstrip("\r"))

    def _emit(self, stream: str, line: str) -> None:
        ts = time.monotonic() - self._t0
        self.entries.append(f"[{ts:7.2f}s] {stream} | {line}")

    def flush(self) -> None:
        """Emit any buffered partial lines (call once the command is done)."""
        for stream in ("OUT", "ERR"):
            remainder = self._buf[stream]
            if remainder:
                self._emit(stream, remainder.rstrip("\r"))
                self._buf[stream] = ""

    @property
    def transcript(self) -> str:
        return "\n".join(self.entries)

    def save(self, path: str | Path) -> Path:
        p = Path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(self.transcript, encoding="utf-8")
        return p


@dataclass
class AgentRun:
    transcript: str
    exit_code: int
    transcript_path: str | None = None
    lines: int = field(default=0)


async def run_agent_with_transcript(
    *,
    cmd: str,
    api_key: str | None = None,
    timeout: int = 600,
    envs: dict[str, str] | None = None,
    cwd: str | None = None,
    log_path: str | Path | None = None,
) -> AgentRun:
    """Run `cmd` (the command that launches the agent) in a fresh E2B sandbox,
    streaming every output line into a transcript.

    `cmd` is whatever starts your agent inside the sandbox — e.g. after you
    upload its files with `sandbox.files.write(...)`, something like
    `python /home/user/agent/run.py "<task>"`.
    """
    from e2b_code_interpreter import AsyncSandbox

    collector = TranscriptCollector()
    sandbox = await AsyncSandbox.create(api_key=api_key or settings.e2b_api_key, timeout=timeout)
    try:
        try:
            result = await sandbox.commands.run(
                cmd,
                on_stdout=collector.on_stdout,
                on_stderr=collector.on_stderr,
                envs=envs,
                cwd=cwd,
                timeout=timeout,
            )
            exit_code = result.exit_code
        except Exception as exc:
            # E2B raises CommandExitException on a non-zero exit — the callbacks
            # have already captured all output, we just record the failure.
            exit_code = getattr(exc, "exit_code", 1)
            collector.on_stderr(f"\n[process exited with code {exit_code}: {exc}]\n")
        finally:
            collector.flush()
    finally:
        await sandbox.kill()

    saved: str | None = None
    if log_path is not None:
        saved = str(collector.save(log_path))

    logger.info("agent.transcript_captured", lines=len(collector.entries), exit_code=exit_code)
    return AgentRun(
        transcript=collector.transcript,
        exit_code=exit_code,
        transcript_path=saved,
        lines=len(collector.entries),
    )
