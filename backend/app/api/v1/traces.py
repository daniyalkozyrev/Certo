"""Trace ingestion + read endpoints — the trace-first core.

An agent (running anywhere) POSTs its captured trajectory here; Certo persists it
and scores the trajectory asynchronously (judge over spans + final + optional test).
"""

from __future__ import annotations

import asyncio
import uuid

from fastapi import APIRouter, Request, status

from app.api.deps import CurrentUser, PaginationDep, SessionDep
from app.core.config import settings
from app.core.exceptions import NotFoundError
from app.models.trace import Span, Trace, TraceStatus
from app.repositories.agent import AgentRepository
from app.repositories.trace import TraceRepository
from app.schemas.common import Page
from app.schemas.trace import TraceDetail, TraceIngest, TraceRead

router = APIRouter(prefix="/traces", tags=["traces"])


@router.post("", response_model=TraceRead, status_code=status.HTTP_202_ACCEPTED)
async def ingest_trace(
    payload: TraceIngest, session: SessionDep, request: Request, user: CurrentUser
) -> Trace:
    if payload.agent_id is not None:
        agent = await AgentRepository(session).get(payload.agent_id)
        if agent is None or (agent.owner_id is not None and agent.owner_id != user.id):
            raise NotFoundError("Agent not found")

    trace = Trace(
        owner_id=user.id,
        agent_id=payload.agent_id,
        name=payload.name,
        task=payload.task,
        final_output=payload.final_output,
        expected_output=payload.expected_output,
        test_code=payload.test_code,
        source=payload.source,
        meta=payload.meta,
        status=TraceStatus.RUNNING,
    )
    trace.spans = [
        Span(
            step_index=i,
            kind=s.kind,
            name=s.name,
            input=s.input,
            output=s.output,
            error=s.error,
            tokens=s.tokens,
            latency_ms=s.latency_ms,
        )
        for i, s in enumerate(payload.spans, start=1)
    ]
    await TraceRepository(session).add(trace)
    await session.commit()  # commit so the worker (separate session) sees the row

    if settings.run_worker_inline:
        from app.workers.tasks import score_trace_inline

        asyncio.create_task(score_trace_inline(str(trace.id)))
    else:
        await request.app.state.arq.enqueue_job("score_trace_task", str(trace.id))
    return trace


@router.get("", response_model=Page[TraceRead])
async def list_traces(
    session: SessionDep, page: PaginationDep, user: CurrentUser
) -> Page[TraceRead]:
    repo = TraceRepository(session)
    items = await repo.list_owned(user.id, limit=page.limit, offset=page.offset)
    total = await repo.count_owned(user.id)
    return Page[TraceRead](
        items=[TraceRead.model_validate(t) for t in items],
        total=total,
        limit=page.limit,
        offset=page.offset,
    )


@router.get("/{trace_id}", response_model=TraceDetail)
async def get_trace(
    trace_id: uuid.UUID, session: SessionDep, user: CurrentUser
) -> Trace:
    trace = await TraceRepository(session).get_with_spans(trace_id)
    if trace is None or (trace.owner_id is not None and trace.owner_id != user.id):
        raise NotFoundError("Trace not found")
    return trace
