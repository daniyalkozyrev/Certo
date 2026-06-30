"""Anthropic Claude judge — temporary primary grader while the Prometheus-2 GPU
box is not yet available.

Uses the official Anthropic SDK (Messages API, x-api-key auth). Grades on the
same 1..5 absolute scale as Prometheus-2 so it slots into the ensemble.

Falls back to a deterministic mock when `mock_judge` is on or no API key is set.

Model note: "Claude 3.5 Sonnet" (claude-3-5-sonnet-*) was retired on 2025-10-28
and now 404s; `claude-sonnet-4-6` is the documented drop-in successor.
"""

from __future__ import annotations

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

_USER_TEMPLATE = """Evaluate the response to the instruction using the score rubric.

###Instruction:
{instruction}

###Response to evaluate:
{response}

###Reference Answer (ideal, scores 5):
{reference_answer}

###Score Rubric:
{rubric}

Reply in exactly this format, nothing else:
"Feedback: <one or two sentences> [RESULT] <integer 1-5>"
"""


class AnthropicJudge:
    """LLM-as-a-Judge backed by Anthropic Claude (e.g. Sonnet 4.6)."""

    def __init__(self) -> None:
        self.name = settings.judge_anthropic_model
        self._client = None  # lazily created AsyncAnthropic

    @property
    def client(self):
        if self._client is None:
            from anthropic import AsyncAnthropic

            self._client = AsyncAnthropic(api_key=settings.judge_anthropic_api_key)
        return self._client

    async def grade(self, request: JudgeRequest) -> JudgeResult:
        if settings.mock_judge or not settings.judge_anthropic_api_key:
            return self._grade_mock(request)
        return await self._grade_claude(request)

    async def _grade_claude(self, request: JudgeRequest) -> JudgeResult:
        prompt = _USER_TEMPLATE.format(
            instruction=request.instruction,
            response=request.response or "(empty response)",
            reference_answer=request.reference_answer or "N/A",
            rubric=request.rubric or DEFAULT_RUBRIC,
        )
        try:
            message = await self.client.messages.create(
                model=settings.judge_anthropic_model,
                max_tokens=512,
                temperature=0,  # deterministic grading (allowed on Sonnet 4.6)
                system=ABSOLUTE_SYSTEM_PROMPT,
                messages=[{"role": "user", "content": prompt}],
            )
        except Exception as exc:  # network / auth / rate-limit
            logger.error("judge.anthropic_error", error=str(exc))
            raise ExternalServiceError(f"Anthropic judge failed: {exc}") from exc

        # content is a list of blocks; concatenate the text blocks.
        text = "".join(
            block.text for block in message.content if getattr(block, "type", None) == "text"
        )
        score, feedback = parse_absolute_output(text)
        return JudgeResult(score=score, feedback=feedback)

    def _grade_mock(self, request: JudgeRequest) -> JudgeResult:
        resp = request.response.strip().lower()
        if not resp:
            return JudgeResult(1, "[mock-claude] Empty response.")
        if "error" in resp or "traceback" in resp:
            return JudgeResult(2, "[mock-claude] Response contains errors.")
        score = 5 if len(resp) > 30 else 4
        return JudgeResult(score, f"[mock-claude] Looks correct (len={len(resp)}).")
