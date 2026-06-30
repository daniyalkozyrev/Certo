"""Record an internally-executed run as a unified Trace + Spans (no re-judging).

Certo's own execution paths (the agentic runner via `evaluation_service`, and the
E2B `trace-eval` endpoint) already produce graded trajectories. This persists them
as `Trace`/`Span` rows — the same representation as ingested traces — so EVERY run,
internal or external, shows up in one place (`/traces`). Scores are passed in
(already computed); this does not call the judge again.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.trace import Span, Trace, TraceSource, TraceStatus


async def record_trace(
    session: AsyncSession,
    *,
    owner_id: uuid.UUID | None,
    source: TraceSource,
    spans: list[dict[str, Any]],
    agent_id: uuid.UUID | None = None,
    name: str | None = None,
    task: str | None = None,
    final_output: str | None = None,
    trust_score: float | None = None,
    summary: dict[str, Any] | None = None,
) -> Trace:
    """Create a COMPLETED Trace from an already-scored internal run."""
    trace = Trace(
        owner_id=owner_id,
        agent_id=agent_id,
        name=name,
        task=task,
        source=source,
        final_output=final_output,
        trust_score=trust_score,
        summary=summary,
        status=TraceStatus.COMPLETED,
    )
    trace.spans = [
        Span(
            step_index=i,
            kind=sp.get("kind") or "agent",
            name=sp.get("name"),
            input=sp.get("input"),
            output=sp.get("output"),
            error=sp.get("error"),
            judge_score=sp.get("judge_score"),
            judge_feedback=sp.get("judge_feedback"),
            judge_votes=sp.get("judge_votes"),
        )
        for i, sp in enumerate(spans, start=1)
    ]
    session.add(trace)
    await session.flush()
    return trace
