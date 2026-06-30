"""Trajectory-eval endpoint.

Runs an agent inside an E2B sandbox while streaming EVERY output line into a
single transcript (Agent Trajectory Logging), then grades that whole transcript
with the LLM-as-a-Judge — so the judge sees the agent's actual steps/tool use,
not just a final answer.

`cmd` is the command that launches the agent inside the sandbox, e.g.
    "git clone <repo> /home/user/a && pip install -e /home/user/a && python -m a 'task'"
or a script you've uploaded. (For a locally-installed agent like Hermes you'd
capture its subprocess output instead — same transcript idea, different source.)
"""

from __future__ import annotations

import time
from pathlib import Path

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.api.deps import CurrentUser, SessionDep
from app.models.trace import TraceSource
from app.services.judge.base import JudgeRequest
from app.services.judge.ensemble import EnsembleJudge
from app.services.judge.prompts import FINAL_RUBRIC
from app.services.sandbox.transcript import run_agent_with_transcript
from app.services.scoring.trust_score import TaskScore, compute_trust_score
from app.services.trace_recorder import record_trace

router = APIRouter(prefix="/trace-eval", tags=["trace-eval"])


class TraceEvalRequest(BaseModel):
    task: str = Field(min_length=1, description="The task given to the agent.")
    cmd: str = Field(min_length=1, description="Command that launches the agent in the sandbox.")
    rubric: str | None = Field(default=None, description="Override rubric; defaults to the auditor rubric.")
    timeout: int = Field(default=600, ge=10, le=1800)


class JudgeVoteOut(BaseModel):
    judge: str
    score: int
    feedback: str


class TraceEvalResult(BaseModel):
    exit_code: int
    trust_score: int  # 1..5 ensemble consensus
    disagreement: str
    feedback: str
    votes: list[JudgeVoteOut]
    lines: int
    transcript_path: str | None
    transcript: str
    trace_id: str | None = None  # view it under /traces


@router.post("", response_model=TraceEvalResult)
async def trace_eval(
    payload: TraceEvalRequest, session: SessionDep, user: CurrentUser
) -> TraceEvalResult:
    # 1. Run the agent, streaming every stdout/stderr line into one transcript.
    log_path = Path("logs") / f"trace-{user.id}-{int(time.time())}.log"
    run = await run_agent_with_transcript(
        cmd=payload.cmd,
        timeout=payload.timeout,
        log_path=log_path,
    )

    # 2. Hand the full trajectory (not just a final answer) to the judge.
    grade = await EnsembleJudge().grade(
        JudgeRequest(
            instruction=payload.task,
            response=run.transcript,
            rubric=payload.rubric or FINAL_RUBRIC,
        )
    )
    votes = [{"judge": v.judge, "score": v.score, "feedback": v.feedback} for v in grade.votes]

    # 3. Record it as a unified Trace (one sandbox span) so it appears in /traces.
    trust = compute_trust_score([TaskScore(judge_score=grade.score, max_score=5)]).trust_score
    trace = await record_trace(
        session,
        owner_id=user.id,
        source=TraceSource.SANDBOX,
        name=f"sandbox · {payload.task[:50]}",
        task=payload.task,
        final_output=run.transcript[-4000:],
        trust_score=trust,
        summary={"final_score": grade.score, "exit_code": run.exit_code,
                 "disagreement": grade.disagreement, "lines": run.lines},
        spans=[{
            "kind": "tool", "name": "command",
            "input": payload.cmd, "output": run.transcript[-8000:],
            "error": None if run.exit_code == 0 else f"exit {run.exit_code}",
            "judge_score": grade.score, "judge_feedback": grade.feedback,
            "judge_votes": votes or None,
        }],
    )
    await session.commit()

    return TraceEvalResult(
        exit_code=run.exit_code,
        trust_score=grade.score,
        disagreement=grade.disagreement,
        feedback=grade.feedback,
        votes=[JudgeVoteOut(**v) for v in votes],
        lines=run.lines,
        transcript_path=run.transcript_path,
        transcript=run.transcript,
        trace_id=str(trace.id),
    )
