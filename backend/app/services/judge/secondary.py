"""Secondary LLM judge — the pluggable second opinion in the ensemble.

This is the "plug in another LLM" slot. It talks to any OpenAI-compatible
endpoint (OpenAI, another vLLM, a gateway, ...) configured via
`JUDGE_SECONDARY_*` settings, and grades on the same 1..5 absolute scale so its
vote can be averaged with Prometheus-2 to reduce single-judge subjectivity.

Falls back to a deterministic mock when `mock_judge` is on or no API key is set.
"""

from __future__ import annotations

from openai import AsyncOpenAI
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.core.exceptions import ExternalServiceError
from app.core.logging import get_logger
from app.services.judge.base import JudgeRequest, JudgeResult
from app.services.judge.prompts import (
    ABSOLUTE_SYSTEM_PROMPT,
    DEFAULT_RUBRIC,
    parse_absolute_output,
)

logger = get_logger(__name__)

# Permanent failures — retrying just burns time and API calls. A bad key or an
# empty billing balance won't fix itself across 3 attempts; fail fast and let the
# ensemble degrade to the surviving judge.
_PERMANENT_CODES = {"insufficient_quota", "invalid_api_key", "account_deactivated"}


def _is_transient(exc: BaseException) -> bool:
    if getattr(exc, "code", None) in _PERMANENT_CODES:
        return False
    try:
        from openai import AuthenticationError, PermissionDeniedError

        if isinstance(exc, (AuthenticationError, PermissionDeniedError)):
            return False
    except ImportError:
        pass
    return True

# Hold the second judge to the SAME hardened auditor standard as the primary
# (anti-hallucination + prompt-injection guard) so both votes are comparable and
# an independent model can't be talked out of its score by the agent's text.
_SYSTEM_PROMPT = ABSOLUTE_SYSTEM_PROMPT

_USER_TEMPLATE = """Evaluate the response to the instruction using the rubric.

###Instruction:
{instruction}

###Response:
{response}

###Reference Answer (ideal, scores 5):
{reference_answer}

###Rubric:
{rubric}

Reply in exactly this format:
"Feedback: <one or two sentences> [RESULT] <integer 1-5>"
"""


class SecondaryLLMJudge:
    """Generic OpenAI-compatible second-opinion judge."""

    def __init__(self) -> None:
        self.name = settings.judge_secondary_model
        self._client: AsyncOpenAI | None = None

    @property
    def client(self) -> AsyncOpenAI:
        if self._client is None:
            self._client = AsyncOpenAI(
                base_url=settings.judge_secondary_base_url,
                api_key=settings.judge_secondary_api_key or "EMPTY",
            )
        return self._client

    async def grade(self, request: JudgeRequest) -> JudgeResult:
        if settings.mock_judge or not settings.judge_secondary_api_key:
            return self._grade_mock(request)
        return await self._grade_llm(request)

    async def _grade_llm(self, request: JudgeRequest) -> JudgeResult:
        prompt = _USER_TEMPLATE.format(
            instruction=request.instruction,
            response=request.response or "(empty response)",
            reference_answer=request.reference_answer or "N/A",
            rubric=request.rubric or DEFAULT_RUBRIC,
        )
        try:
            completion = await self._call_llm(prompt)
        except Exception as exc:
            logger.error("judge.secondary_error", error=str(exc))
            raise ExternalServiceError(f"Secondary judge failed: {exc}") from exc

        content = completion.choices[0].message.content or ""
        score, feedback = parse_absolute_output(content)
        return JudgeResult(score=score, feedback=feedback)

    @retry(
        retry=retry_if_exception(_is_transient),  # skip retries on permanent errors
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def _call_llm(self, prompt: str):
        return await self.client.chat.completions.create(
            model=settings.judge_secondary_model,
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.0,
            max_tokens=512,
        )

    def _grade_mock(self, request: JudgeRequest) -> JudgeResult:
        """Slightly different heuristic than Prometheus so the ensemble shows
        realistic, non-identical votes in offline/demo mode."""
        resp = request.response.strip().lower()
        if not resp:
            return JudgeResult(1, "[mock-2] Empty response.")
        if "error" in resp or "traceback" in resp:
            return JudgeResult(2, "[mock-2] Detected an error in the output.")
        score = 4 if len(resp) > 40 else 3
        return JudgeResult(score, f"[mock-2] Acceptable but cautious (len={len(resp)}).")
