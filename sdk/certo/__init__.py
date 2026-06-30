"""Certo SDK — instrument any agent in ~5 lines and stream its trajectory to Certo.

    import certo

    with certo.trace("Refactor the auth module", api_key=TOKEN) as t:
        t.log_span("llm", "planner", input=prompt, output=plan)
        result = run_tool()                       # or decorate it with @certo.tool
        t.finish(result)                          # -> Certo scores the trajectory

The agent runs wherever it lives; Certo just receives the trace and grades it.
Depends only on `httpx`.
"""

from __future__ import annotations

import functools
import time
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Callable, Iterator

import httpx

__all__ = ["trace", "tool", "Trace"]

_current: ContextVar["Trace | None"] = ContextVar("certo_current_trace", default=None)


class Trace:
    """Collects spans for one agent run and submits them to Certo on finish."""

    def __init__(
        self,
        task: str,
        *,
        api_key: str,
        base_url: str = "http://localhost:8000",
        name: str | None = None,
        agent_id: str | None = None,
        source: str = "sdk",
        expected_output: str | None = None,
        test_code: str | None = None,
        meta: dict[str, Any] | None = None,
    ) -> None:
        self.task = task
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.name = name
        self.agent_id = agent_id
        self.source = source
        self.expected_output = expected_output
        self.test_code = test_code
        self.meta = meta or {}
        self.spans: list[dict[str, Any]] = []
        self.final_output: str | None = None
        self.result: dict[str, Any] | None = None
        self._submitted = False

    def log_span(
        self,
        kind: str,
        name: str | None = None,
        *,
        input: Any = None,
        output: Any = None,
        error: str | None = None,
        tokens: int | None = None,
        latency_ms: int | None = None,
    ) -> None:
        """Record one step: kind = llm | tool | agent | observation | handoff."""
        self.spans.append({
            "kind": kind, "name": name, "input": input, "output": output,
            "error": error, "tokens": tokens, "latency_ms": latency_ms,
        })

    def finish(self, output: Any = None) -> dict[str, Any]:
        """Submit the trace to Certo. Returns the created trace ({id, status, ...})."""
        if self._submitted:
            return self.result or {}
        self.final_output = output if isinstance(output, str) or output is None else str(output)
        payload = {
            "task": self.task,
            "name": self.name,
            "agent_id": self.agent_id,
            "source": self.source,
            "final_output": self.final_output,
            "expected_output": self.expected_output,
            "test_code": self.test_code,
            "meta": self.meta,
            "spans": self.spans,
        }
        resp = httpx.post(
            f"{self.base_url}/api/v1/traces",
            json={k: v for k, v in payload.items() if v is not None or k in ("spans", "meta")},
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=60,
        )
        resp.raise_for_status()
        self.result = resp.json()
        self._submitted = True
        return self.result


@contextmanager
def trace(task: str, **kwargs: Any) -> Iterator[Trace]:
    """Context manager: opens a trace, sets it active (for @tool), submits on exit."""
    t = Trace(task, **kwargs)
    token = _current.set(t)
    try:
        yield t
    finally:
        _current.reset(token)
        if not t._submitted:
            t.finish(t.final_output)


def tool(_fn: Callable | None = None, *, name: str | None = None) -> Callable:
    """Decorator: auto-log a function call as a `tool` span on the active trace."""

    def decorate(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            t = _current.get()
            start = time.monotonic()
            err: str | None = None
            result: Any = None
            try:
                result = fn(*args, **kwargs)
                return result
            except Exception as exc:  # log the failure as a span, then re-raise
                err = f"{type(exc).__name__}: {exc}"
                raise
            finally:
                if t is not None:
                    t.log_span(
                        "tool",
                        name or fn.__name__,
                        input={"args": [str(a)[:500] for a in args], "kwargs": {k: str(v)[:500] for k, v in kwargs.items()}},
                        output=None if err else (result if isinstance(result, (str, int, float, bool, list, dict)) else str(result)),
                        error=err,
                        latency_ms=int((time.monotonic() - start) * 1000),
                    )

        return wrapper

    return decorate(_fn) if callable(_fn) else decorate
