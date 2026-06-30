"""Unit tests for TrustScore aggregation and the Prometheus output parser.

These run without a DB or any external service.
"""

from __future__ import annotations

from app.services.judge.prompts import parse_absolute_output
from app.services.scoring.trust_score import TaskScore, compute_trust_score


def test_normalized_and_reward():
    s = TaskScore(judge_score=5, max_score=5)
    assert s.normalized == 1.0
    assert s.reward == 1

    s = TaskScore(judge_score=1, max_score=5)
    assert s.normalized == 0.0
    assert s.reward == -1


def test_compute_trust_score_perfect():
    scores = [TaskScore(judge_score=5), TaskScore(judge_score=5)]
    result = compute_trust_score(scores)
    assert result.trust_score == 100.0
    assert result.pass_rate == 1.0


def test_compute_trust_score_mixed():
    scores = [TaskScore(judge_score=5), TaskScore(judge_score=1)]
    result = compute_trust_score(scores)
    assert result.trust_score == 50.0
    assert result.pass_rate == 0.5


def test_compute_trust_score_empty():
    result = compute_trust_score([])
    assert result.trust_score == 0.0
    assert result.summary["n_tasks"] == 0


def test_parse_absolute_output_standard():
    score, feedback = parse_absolute_output("Feedback: Good work. [RESULT] 4")
    assert score == 4
    assert "Good work" in feedback


def test_parse_absolute_output_fallback():
    score, _ = parse_absolute_output("The answer deserves a 3 overall")
    assert score == 3
