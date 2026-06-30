"""Agent-under-test runner.

Given a task, the agent (an OpenAI-compatible chat endpoint) produces a solution.
For the MVP the agent is expected to return a Python program that prints its
answer; we extract the code so the sandbox can execute it.

Uses a deterministic mock when the agent has no API key configured AND no
default key is set, so the pipeline runs offline.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

from openai import AsyncOpenAI
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.core.exceptions import ExternalServiceError
from app.core.logging import get_logger

logger = get_logger(__name__)


def _is_transient(exc: BaseException) -> bool:
    """Don't burn retries on permanent failures (bad key / model). A dead or hung
    endpoint is bounded by the client timeout, so retrying a transient blip is fine
    but auth/not-found errors won't fix themselves."""
    try:
        from openai import AuthenticationError, NotFoundError, PermissionDeniedError

        if isinstance(exc, (AuthenticationError, PermissionDeniedError, NotFoundError)):
            return False
    except ImportError:
        pass
    return True

_DEFAULT_SYSTEM_PROMPT = (
    "You are a coding agent. Solve the user's task by writing a single, "
    "self-contained Python program that prints the final answer to stdout. "
    "Return only a Python code block."
)

_CODE_FENCE_RE = re.compile(r"```(?:python)?\s*(.*?)```", re.DOTALL | re.IGNORECASE)


@dataclass
class AgentOutput:
    raw: str  # full model message
    code: str  # extracted runnable code (falls back to raw)
    has_code: bool = False  # True only if a real ```code``` block was found


def _extract_code(text: str) -> tuple[str, bool]:
    """Return (code, has_code). has_code is True only when a fenced code block
    was actually present — so callers can tell a coding agent (returns code to
    run) apart from an answer agent (returns prose; nothing to execute)."""
    match = _CODE_FENCE_RE.search(text)
    if match:
        return match.group(1).strip(), True
    return text.strip(), False


class AgentRunner:
    def __init__(self, agent_config: dict[str, Any]) -> None:
        self.config = agent_config or {}

    def _resolve(self, key: str, default: str | None) -> str | None:
        return self.config.get(key) or default

    async def solve(self, prompt: str) -> AgentOutput:
        api_key = self._resolve("api_key", settings.agent_default_api_key)
        if not api_key:
            return self._solve_mock(prompt)
        return await self._solve_llm(prompt, api_key)

    @retry(
        retry=retry_if_exception(_is_transient),
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def _solve_llm(self, prompt: str, api_key: str) -> AgentOutput:
        client = AsyncOpenAI(
            base_url=self._resolve("base_url", settings.agent_default_base_url),
            api_key=api_key,
            timeout=settings.agent_request_timeout,  # bound a hung/misconfigured endpoint
            max_retries=0,  # tenacity owns retries (with our transient-only policy)
        )
        system_prompt = self._resolve("system_prompt", _DEFAULT_SYSTEM_PROMPT)
        try:
            completion = await client.chat.completions.create(
                model=self._resolve("model", settings.agent_default_model),
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,
            )
        except Exception as exc:
            logger.error("agent.llm_error", error=str(exc))
            raise ExternalServiceError(f"Agent request failed: {exc}") from exc

        raw = completion.choices[0].message.content or ""
        code, has_code = _extract_code(raw)
        return AgentOutput(raw=raw, code=code, has_code=has_code)

    def _solve_mock(self, prompt: str) -> AgentOutput:
        """Echo-style stub: a valid program that prints a canned answer."""
        logger.info("agent.mock_solve")
        snippet = prompt.strip().replace("\n", " ")[:80]
        code = f'print("Mock agent solution for task: {snippet!s}")'
        return AgentOutput(raw=f"```python\n{code}\n```", code=code, has_code=True)
