"""E2B sandbox: execute agent-produced code in isolation and collect output.

Two execution modes:

* `run_python(code)` — one-shot: spin up, run once, tear down. Used by the
  legacy one-shot agent.
* `open_session()` — a **persistent** sandbox the agent keeps using across many
  steps. State (variables, files, installed packages) survives between calls,
  so the agent can build up a solution incrementally — this is what lets an
  agent actually *live inside* the sandbox instead of firing one blind shot.

When `settings.mock_sandbox` is true (or no E2B key is configured) a local stub
runs instead, so the whole pipeline is testable without any external service.
The mock session keeps a persistent in-process namespace so multi-step state
still works offline (it is NOT a security boundary — dev only).
"""

from __future__ import annotations

import asyncio
import contextlib
import io
import sys
import traceback
from dataclasses import dataclass

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class SandboxResult:
    stdout: str
    stderr: str
    exit_code: int


# ── Persistent sessions ──────────────────────────────────────────────────


class SandboxSession:
    """A sandbox kept alive across multiple `run` calls (state persists)."""

    async def run(self, code: str, *, timeout: int = 60) -> SandboxResult:  # pragma: no cover - interface
        raise NotImplementedError

    async def close(self) -> None:  # pragma: no cover - interface
        raise NotImplementedError

    async def __aenter__(self) -> SandboxSession:
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.close()


class _E2BSession(SandboxSession):
    """One real E2B sandbox reused across steps. E2B runs a Jupyter-like kernel,
    so variables/files defined in an earlier `run` are visible in later ones."""

    def __init__(self) -> None:
        self._sandbox = None  # created lazily on first run

    async def run(self, code: str, *, timeout: int = 60) -> SandboxResult:
        def _exec() -> SandboxResult:
            from e2b_code_interpreter import Sandbox

            if self._sandbox is None:
                self._sandbox = Sandbox.create(api_key=settings.e2b_api_key)
            execution = self._sandbox.run_code(code, timeout=timeout)
            stdout = "".join(execution.logs.stdout)
            stderr = "".join(execution.logs.stderr)
            exit_code = 1 if execution.error else 0
            if execution.error:
                stderr = f"{stderr}\n{execution.error.name}: {execution.error.value}".strip()
            return SandboxResult(stdout=stdout, stderr=stderr, exit_code=exit_code)

        return await asyncio.to_thread(_exec)

    async def close(self) -> None:
        def _kill() -> None:
            if self._sandbox is not None:
                with contextlib.suppress(Exception):
                    self._sandbox.kill()
                self._sandbox = None

        await asyncio.to_thread(_kill)


class _MockSession(SandboxSession):
    """Offline session: exec each snippet into a persistent in-process namespace
    so cross-step state behaves like a real kernel. Dev only, not isolated."""

    def __init__(self) -> None:
        self._globals: dict = {"__name__": "__main__"}

    async def run(self, code: str, *, timeout: int = 60) -> SandboxResult:
        def _exec() -> SandboxResult:
            out, err = io.StringIO(), io.StringIO()
            try:
                with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
                    exec(compile(code, "<agent-step>", "exec"), self._globals)  # noqa: S102
                return SandboxResult(out.getvalue(), err.getvalue(), 0)
            except Exception:
                tb = traceback.format_exc()
                return SandboxResult(out.getvalue(), (err.getvalue() + tb).strip(), 1)

        try:
            return await asyncio.wait_for(asyncio.to_thread(_exec), timeout=timeout)
        except asyncio.TimeoutError:
            return SandboxResult("", "timeout", 124)

    async def close(self) -> None:
        self._globals.clear()


class SandboxRunner:
    """Runs Python code and returns stdout/stderr/exit_code."""

    def _use_mock(self) -> bool:
        return settings.mock_sandbox or not settings.e2b_api_key

    def open_session(self) -> SandboxSession:
        """A persistent sandbox the agent reuses across steps."""
        return _MockSession() if self._use_mock() else _E2BSession()

    async def run_python(self, code: str, *, timeout: int = 60) -> SandboxResult:
        """One-shot execution (spin up, run once, tear down)."""
        if self._use_mock():
            return await self._run_mock(code, timeout=timeout)
        return await self._run_e2b(code, timeout=timeout)

    # ── Real E2B execution (SDK v2.x) ────────────────────────
    async def _run_e2b(self, code: str, *, timeout: int) -> SandboxResult:
        from e2b_code_interpreter import Sandbox

        def _exec() -> SandboxResult:
            sandbox = Sandbox.create(api_key=settings.e2b_api_key)
            try:
                execution = sandbox.run_code(code, timeout=timeout)
                stdout = "".join(execution.logs.stdout)
                stderr = "".join(execution.logs.stderr)
                exit_code = 1 if execution.error else 0
                if execution.error:
                    stderr = f"{stderr}\n{execution.error.name}: {execution.error.value}".strip()
                return SandboxResult(stdout=stdout, stderr=stderr, exit_code=exit_code)
            finally:
                try:
                    sandbox.kill()
                except Exception:  # best-effort cleanup
                    pass

        # E2B SDK is sync; offload to a thread to avoid blocking the event loop.
        return await asyncio.to_thread(_exec)

    # ── Local mock execution ─────────────────────────────────
    async def _run_mock(self, code: str, *, timeout: int) -> SandboxResult:
        """Run the snippet in a subprocess (NOT a security boundary — dev only)."""
        logger.info("sandbox.mock_run")
        proc = await asyncio.create_subprocess_exec(
            sys.executable,
            "-c",
            code,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout_b, stderr_b = await asyncio.wait_for(
                proc.communicate(), timeout=timeout
            )
        except asyncio.TimeoutError:
            proc.kill()
            return SandboxResult(stdout="", stderr="timeout", exit_code=124)
        return SandboxResult(
            stdout=stdout_b.decode(errors="replace"),
            stderr=stderr_b.decode(errors="replace"),
            exit_code=proc.returncode if proc.returncode is not None else -1,
        )
