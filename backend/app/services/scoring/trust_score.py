"""TrustScore aggregation.

MVP formula: TrustScore = 100 * weighted mean of per-task normalized judge
scores. `pass_rate` is reported separately. The structure (weights, named
dimensions) is intentionally extensible so we can add safety / efficiency /
robustness dimensions later without changing callers.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from app.core.config import settings


@dataclass
class TaskScore:
    """Per-task scoring input."""

    judge_score: int  # 1..5
    max_score: int = 5
    passed: bool | None = None  # for grading_type=CODE; None -> derive from threshold

    @property
    def normalized(self) -> float:
        """Map judge_score to [0, 1]."""
        denom = max(self.max_score - 1, 1)
        return max(0.0, min(1.0, (self.judge_score - 1) / denom))

    @property
    def reward(self) -> int:
        """+1 if the task is considered passed, else -1."""
        if self.passed is not None:
            return 1 if self.passed else -1
        return 1 if self.judge_score >= settings.reward_pass_threshold else -1


def blend_agentic_score(step_scores: list[int], final_score: int) -> int:
    """Combine per-step judge grades with the final holistic grade into one 1..5.

    Weighted 40% mean-of-steps / 60% final outcome: a run that never crashed but
    made no real progress gets low *step* scores and a low *final* score, so it
    can no longer score 5/5 just for "not erroring". With no steps recorded we
    fall back to the final grade.
    """
    if not step_scores:
        return max(1, min(5, final_score))
    mean_step = sum(step_scores) / len(step_scores)
    blended = 0.4 * mean_step + 0.6 * final_score
    return max(1, min(5, round(blended)))


@dataclass
class TrustScoreResult:
    trust_score: float  # 0..100
    pass_rate: float  # 0..1
    summary: dict = field(default_factory=dict)


def compute_trust_score(
    scores: list[TaskScore],
    *,
    weights: list[float] | None = None,
) -> TrustScoreResult:
    """Aggregate per-task scores into an overall TrustScore."""
    if not scores:
        return TrustScoreResult(trust_score=0.0, pass_rate=0.0, summary={"n_tasks": 0})

    if weights is None:
        weights = [1.0] * len(scores)
    if len(weights) != len(scores):
        raise ValueError("weights length must match scores length")

    total_w = sum(weights) or 1.0
    weighted = sum(s.normalized * w for s, w in zip(scores, weights, strict=True))
    trust = 100.0 * weighted / total_w

    n_passed = sum(1 for s in scores if s.reward > 0)
    pass_rate = n_passed / len(scores)

    summary = {
        "n_tasks": len(scores),
        "n_passed": n_passed,
        "mean_judge_score": round(
            sum(s.judge_score for s in scores) / len(scores), 3
        ),
        "trust_score": round(trust, 2),
        "pass_rate": round(pass_rate, 3),
    }
    return TrustScoreResult(
        trust_score=round(trust, 2), pass_rate=round(pass_rate, 4), summary=summary
    )
