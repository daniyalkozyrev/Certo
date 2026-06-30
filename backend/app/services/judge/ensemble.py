"""Ensemble judge — combines multiple independent judges into one verdict.

Averaging an independent second opinion (and any future judges) reduces the
single-judge subjectivity of Prometheus-2 and surfaces disagreement.
"""

from __future__ import annotations

import asyncio

from app.core.config import settings
from app.core.logging import get_logger
from app.services.judge.base import (
    EnsembleResult,
    JudgeProvider,
    JudgeRequest,
    JudgeVote,
)
from app.services.judge.prometheus import PrometheusJudge
from app.services.judge.secondary import SecondaryLLMJudge

logger = get_logger(__name__)


def _disagreement_level(spread: int) -> str:
    """spread is on the 1..5 scale (max-min of votes)."""
    if spread >= 3:
        return "High"
    if spread >= 2:
        return "Medium"
    return "Low"


class EnsembleJudge:
    """Runs every configured judge and aggregates their votes."""

    def __init__(self, judges: list[JudgeProvider] | None = None) -> None:
        if judges is None:
            # Primary judge: Anthropic Claude if enabled (temporary, while the
            # Prometheus-2 GPU box is unavailable), otherwise Prometheus-2.
            if settings.judge_anthropic_enabled:
                from app.services.judge.anthropic_judge import AnthropicJudge

                judges = [AnthropicJudge()]
            else:
                judges = [PrometheusJudge()]
            # >>> Additional judges plug in here via settings (see config.py). <<<
            if settings.judge_secondary_enabled:
                judges.append(SecondaryLLMJudge())
        self.judges = judges

    async def grade(self, request: JudgeRequest) -> EnsembleResult:
        # Tolerate a failing judge (e.g. secondary out of quota / down): drop it
        # and grade on the survivors instead of crashing the whole evaluation.
        results = await asyncio.gather(
            *(j.grade(request) for j in self.judges), return_exceptions=True
        )
        votes: list[JudgeVote] = []
        errors: list[BaseException] = []
        for j, r in zip(self.judges, results, strict=True):
            if isinstance(r, BaseException):
                logger.warning("judge.skipped", judge=j.name, error=str(r))
                errors.append(r)
                continue
            votes.append(JudgeVote(judge=j.name, score=r.score, feedback=r.feedback))

        if not votes:
            # Every judge failed — surface the first error so the run is marked
            # failed rather than silently scored.
            raise errors[0]

        scores = [v.score for v in votes]
        consensus = round(sum(scores) / len(scores))
        spread = max(scores) - min(scores)
        disagreement = _disagreement_level(spread)

        combined = "\n".join(f"[{v.judge}] ({v.score}/5) {v.feedback}" for v in votes)
        return EnsembleResult(
            score=consensus,
            feedback=combined,
            votes=votes,
            disagreement=disagreement,
        )
