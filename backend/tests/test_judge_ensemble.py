"""Ensemble judge tests (run offline in mock mode, no external services)."""

from __future__ import annotations

import asyncio

from app.services.judge.base import JudgeRequest
from app.services.judge.ensemble import EnsembleJudge, _disagreement_level
from app.services.judge.prometheus import PrometheusJudge
from app.services.judge.secondary import SecondaryLLMJudge


def test_disagreement_levels():
    assert _disagreement_level(0) == "Low"
    assert _disagreement_level(1) == "Low"
    assert _disagreement_level(2) == "Medium"
    assert _disagreement_level(4) == "High"


def test_ensemble_two_judges_consensus():
    judge = EnsembleJudge(judges=[PrometheusJudge(), SecondaryLLMJudge()])
    req = JudgeRequest(
        instruction="Print the sum of 2 and 3.",
        response="5",
        rubric="Score 5 if it outputs 5.",
        reference_answer="5",
    )
    result = asyncio.run(judge.grade(req))

    assert len(result.votes) == 2
    assert 1 <= result.score <= 5
    assert result.disagreement in {"Low", "Medium", "High"}
    # combined feedback mentions both judges
    assert "Prometheus-2" in result.feedback


def test_ensemble_single_judge_default():
    judge = EnsembleJudge(judges=[PrometheusJudge()])
    req = JudgeRequest(instruction="x", response="hello world output", rubric="")
    result = asyncio.run(judge.grade(req))
    assert len(result.votes) == 1
    assert result.disagreement == "Low"
