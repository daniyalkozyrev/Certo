"""Evaluation endpoints: trigger a run, poll status, read per-task results."""

from __future__ import annotations

import asyncio
import uuid

from fastapi import APIRouter, Request, status

from app.api.deps import CurrentUser, PaginationDep, SessionDep
from app.core.config import settings
from app.core.exceptions import NotFoundError
from app.models.evaluation import Evaluation, EvaluationStatus
from app.repositories.agent import AgentRepository
from app.repositories.benchmark import BenchmarkRepository
from app.repositories.evaluation import EvaluationRepository
from app.schemas.common import Page
from app.schemas.evaluation import (
    EvaluationCreate,
    EvaluationDetail,
    EvaluationRead,
)

router = APIRouter(prefix="/evaluations", tags=["evaluations"])

# Hold strong references to detached inline-run tasks so the event loop can't
# garbage-collect them mid-flight (asyncio.create_task footgun).
_bg_tasks: set[asyncio.Task] = set()


@router.post("", response_model=EvaluationRead, status_code=status.HTTP_202_ACCEPTED)
async def create_evaluation(
    payload: EvaluationCreate, session: SessionDep, request: Request, user: CurrentUser
) -> Evaluation:
    # Validate referenced resources exist and are accessible to this user.
    agent = await AgentRepository(session).get(payload.agent_id)
    if agent is None or (agent.owner_id is not None and agent.owner_id != user.id):
        raise NotFoundError("Agent not found")
    benchmark = await BenchmarkRepository(session).get(payload.benchmark_id)
    if benchmark is None or (
        benchmark.owner_id is not None and benchmark.owner_id != user.id
    ):
        raise NotFoundError("Benchmark not found")

    repo = EvaluationRepository(session)
    evaluation = Evaluation(
        owner_id=user.id,
        agent_id=payload.agent_id,
        benchmark_id=payload.benchmark_id,
        status=EvaluationStatus.PENDING,
    )
    await repo.add(evaluation)
    # Commit now so the worker (separate session) can see the row.
    await session.commit()

    if settings.run_worker_inline:
        # Local dev: run in-process as a detached task (no Redis needed).
        from app.workers.tasks import run_evaluation_inline

        task = asyncio.create_task(run_evaluation_inline(str(evaluation.id)))
        _bg_tasks.add(task)
        task.add_done_callback(_bg_tasks.discard)
    else:
        await request.app.state.arq.enqueue_job(
            "run_evaluation_task", str(evaluation.id)
        )
    return evaluation


@router.get("", response_model=Page[EvaluationRead])
async def list_evaluations(
    session: SessionDep, page: PaginationDep, user: CurrentUser
) -> Page[EvaluationRead]:
    repo = EvaluationRepository(session)
    items = await repo.list_owned(user.id, limit=page.limit, offset=page.offset)
    total = await repo.count_owned(user.id)
    return Page[EvaluationRead](
        items=[EvaluationRead.model_validate(e) for e in items],
        total=total,
        limit=page.limit,
        offset=page.offset,
    )


@router.get("/{evaluation_id}", response_model=EvaluationDetail)
async def get_evaluation(
    evaluation_id: uuid.UUID, session: SessionDep, user: CurrentUser
) -> Evaluation:
    evaluation = await EvaluationRepository(session).get_with_results(evaluation_id)
    if evaluation is None or (
        evaluation.owner_id is not None and evaluation.owner_id != user.id
    ):
        raise NotFoundError("Evaluation not found")
    return evaluation
