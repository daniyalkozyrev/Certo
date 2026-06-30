"""Prometheus-2 judge backed by a self-hosted vLLM (OpenAI-compatible) endpoint.

A deterministic mock is used when `settings.mock_judge` is true, so the pipeline
runs without the GPU box being available.
"""

from __future__ import annotations

from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from app.core.config import settings
from app.core.exceptions import ExternalServiceError
from app.core.logging import get_logger
from app.services.judge.base import JudgeRequest, JudgeResult
from app.services.judge.prompts import (
    ABSOLUTE_SYSTEM_PROMPT,
    build_absolute_prompt,
    parse_absolute_output,
)

logger = get_logger(__name__)


class PrometheusJudge:
    """Absolute-grading judge using Prometheus-2 via vLLM."""

    name = "Prometheus-2"

    def __init__(self) -> None:
        self._client: AsyncOpenAI | None = None

    @property
    def client(self) -> AsyncOpenAI:
        if self._client is None:
            self._client = AsyncOpenAI(
                base_url=settings.judge_base_url,
                api_key=settings.judge_api_key,
            )
        return self._client

    async def grade(self, request: JudgeRequest) -> JudgeResult:
        if settings.mock_judge:
            return self._grade_mock(request)
        return await self._grade_vllm(request)

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=1, max=10),
        reraise=True,
    )
    async def _grade_vllm(self, request: JudgeRequest) -> JudgeResult:
        prompt = build_absolute_prompt(
            instruction=request.instruction,
            response=request.response,
            rubric=request.rubric,
            reference_answer=request.reference_answer,
        )
        try:
            completion = await self.client.chat.completions.create(
                model=settings.judge_model,
                messages=[
                    {"role": "system", "content": ABSOLUTE_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=1.0,
                max_tokens=1024,
            )
        except Exception as exc:  # network / server error
            logger.error("judge.vllm_error", error=str(exc))
            raise ExternalServiceError(f"Judge request failed: {exc}") from exc

        content = completion.choices[0].message.content or ""
        score, feedback = parse_absolute_output(content)
        return JudgeResult(score=score, feedback=feedback)

    def _grade_mock(self, request: JudgeRequest) -> JudgeResult:
        """Deterministic heuristic stub: rewards non-empty, error-free output."""
        resp = request.response.strip().lower()
        if not resp:
            return JudgeResult(1, "[mock] Empty response.")
        if "error" in resp or "traceback" in resp:
            return JudgeResult(2, "[mock] Response contains errors.")
        score = 5 if len(resp) > 20 else 4
        return JudgeResult(score, f"[mock] Looks reasonable (len={len(resp)}).")
