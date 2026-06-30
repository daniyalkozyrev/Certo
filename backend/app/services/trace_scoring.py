"""Score a stored Trace — the trace-ingestion counterpart of `evaluation_service`.

Instead of executing the agent, this grades an already-captured trajectory:
every span gets a per-step grade (`STEP_RUBRIC`), the whole run gets a holistic
grade (`FINAL_RUBRIC`, or `MAS_FINAL_RUBRIC` when the trace shows multiple agent
roles), an optional `test_code` provides the objective axis, and the three blend
into a TrustScore. Reuses the same judge, rubrics and scoring as the agentic path.
"""

from __future__ import annotations

import json
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.exceptions import NotFoundError
from app.core.logging import get_logger
from app.models.trace import Trace, TraceStatus
from app.repositories.trace import TraceRepository
from app.services.judge.base import JudgeRequest
from app.services.judge.ensemble import EnsembleJudge
from app.services.judge.prompts import (
    FINAL_RUBRIC,
    MAS_FINAL_RUBRIC,
    STEP_RUBRIC,
    build_span_instruction,
    format_span_response,
    format_span_trajectory,
)
from app.services.sandbox.e2b_sandbox import SandboxRunner
from app.services.scoring.answer_match import answer_match, extract_final_answer
from app.services.scoring.trust_score import (
    TaskScore,
    blend_agentic_score,
    compute_trust_score,
)

logger = get_logger(__name__)

# Span kinds that signal a multi-agent system (use the MAS criteria).
_MAS_KINDS = {"agent", "handoff"}
# Cost control: per-span grading is one judge call each. Beyond this many spans
# we still keep them and grade the whole trajectory holistically, but skip the
# per-span grade so a long trace can't fan out into unbounded paid calls.
_MAX_GRADED_SPANS = 40


def _unpack(grade) -> tuple[int, str, list[dict] | None, str | None]:
    votes = [{"judge": v.judge, "score": v.score, "feedback": v.feedback} for v in grade.votes]
    return grade.score, grade.feedback, (votes or None), grade.disagreement


class TraceScoringService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.traces = TraceRepository(session)
        self.judge = EnsembleJudge()
        self.sandbox = SandboxRunner()

    async def run(self, trace_id: uuid.UUID) -> None:
        trace = await self.traces.get_with_spans(trace_id)
        if trace is None:
            raise NotFoundError("Trace not found")

        trace.status = TraceStatus.RUNNING
        await self.session.flush()
        try:
            await self._score(trace)
            trace.status = TraceStatus.COMPLETED
        except Exception as exc:
            logger.exception("trace.scoring_failed", trace_id=str(trace_id))
            trace.status = TraceStatus.FAILED
            trace.error = str(exc)
        await self.session.commit()

    async def _score(self, trace: Trace) -> None:
        spans = list(trace.spans)
        is_mas = any(s.kind in _MAS_KINDS for s in spans)
        task = trace.task or ""

        # 1. Grade each span (up to the cost cap).
        span_scores: list[int] = []
        for s in spans[:_MAX_GRADED_SPANS]:
            grade = await self.judge.grade(
                JudgeRequest(
                    instruction=build_span_instruction(task, s.step_index, s.kind, s.name),
                    response=format_span_response(
                        kind=s.kind, name=s.name, input=s.input, output=s.output, error=s.error
                    ),
                    rubric=STEP_RUBRIC,
                )
            )
            sc, fb, votes, _ = _unpack(grade)
            s.judge_score, s.judge_feedback, s.judge_votes = sc, fb, votes
            span_scores.append(sc)

        # 2. Holistic grade of the whole trajectory.
        traj = [
            {
                "step_index": s.step_index, "kind": s.kind, "name": s.name,
                "input": s.input, "output": s.output, "error": s.error,
            }
            for s in spans
        ]
        final_grade = await self.judge.grade(
            JudgeRequest(
                instruction=task,
                response=format_span_trajectory(traj, trace.final_output),
                rubric=MAS_FINAL_RUBRIC if is_mas else FINAL_RUBRIC,
                reference_answer=trace.expected_output,
            )
        )
        final_score, final_fb, final_votes, disagreement = _unpack(final_grade)

        # 3. Objective axis: a `test_code` check (if safe to run) OR a ground-truth
        #    answer-match against `expected_output` (no code execution needed).
        passed: bool | None = None
        if trace.test_code:
            if settings.allow_code_execution:
                passed, detail = await self._run_test(trace.final_output, trace.test_code)
                final_fb = f"{detail}\n\n{final_fb}"
            else:
                final_fb = "test_code skipped (code execution disabled here).\n\n" + final_fb
        elif trace.expected_output:
            final = extract_final_answer(trace.final_output)
            passed = answer_match(final, trace.expected_output)
            detail = (
                f"answer matched reference (extracted {final!r})" if passed
                else f"answer {final!r} did not match reference: {trace.expected_output!r}"
            )
            final_fb = f"{detail}\n\n{final_fb}"

        # 4. Blend per-span quality + final outcome into one 1-5 -> TrustScore.
        effective = blend_agentic_score(span_scores, final_score)
        if passed is False:
            effective = min(effective, 2)
        mean_step = round(sum(span_scores) / len(span_scores), 3) if span_scores else None

        score = TaskScore(judge_score=effective, max_score=5, passed=passed)
        agg = compute_trust_score([score])
        trace.trust_score = agg.trust_score
        trace.summary = {
            "trust_score": agg.trust_score,
            "final_score": final_score,
            "final_feedback": final_fb,
            "mean_step_score": mean_step,
            "n_spans": len(spans),
            "is_multi_agent": is_mas,
            "outcome_passed": passed,
            "disagreement": disagreement,
            "reward": score.reward,
            "final_votes": final_votes,
        }
        await self.session.flush()

    async def _run_test(self, final_output: str | None, test_code: str) -> tuple[bool, str]:
        """Run test_code in the sandbox; it may assert against `agent_stdout`
        (the agent's final output)."""
        harness = f"agent_stdout = {json.dumps(final_output or '')}\n{test_code}"
        res = await self.sandbox.run_python(harness)
        passed = res.exit_code == 0
        return passed, ("test_code passed" if passed else f"test_code failed: {res.stderr.strip()[:500]}")
