"""Benchmark endpoints."""

from __future__ import annotations

import uuid

from fastapi import APIRouter, status

from app.api.deps import CurrentUser, PaginationDep, SessionDep
from app.core.exceptions import NotFoundError
from app.models.benchmark import Benchmark, Task
from app.repositories.benchmark import BenchmarkRepository
from app.schemas.benchmark import BenchmarkCreate, BenchmarkRead
from app.schemas.common import Page

router = APIRouter(prefix="/benchmarks", tags=["benchmarks"])


@router.post("", response_model=BenchmarkRead, status_code=status.HTTP_201_CREATED)
async def create_benchmark(
    payload: BenchmarkCreate, session: SessionDep, user: CurrentUser
) -> Benchmark:
    repo = BenchmarkRepository(session)
    benchmark = Benchmark(owner_id=user.id, name=payload.name, description=payload.description)
    benchmark.tasks = [
        Task(
            prompt=t.prompt,
            rubric=t.rubric,
            reference_answer=t.reference_answer,
            grading_type=t.grading_type,
            test_code=t.test_code,
            meta=t.meta,
            max_score=t.max_score,
        )
        for t in payload.tasks
    ]
    await repo.add(benchmark)
    # Reload with tasks eagerly for the response.
    return await repo.get_with_tasks(benchmark.id)  # type: ignore[return-value]


@router.get("", response_model=Page[BenchmarkRead])
async def list_benchmarks(
    session: SessionDep, page: PaginationDep, user: CurrentUser
) -> Page[BenchmarkRead]:
    repo = BenchmarkRepository(session)
    items = await repo.list_owned(user.id, limit=page.limit, offset=page.offset)
    total = await repo.count_owned(user.id)
    return Page[BenchmarkRead](
        items=[BenchmarkRead.model_validate(b) for b in items],
        total=total,
        limit=page.limit,
        offset=page.offset,
    )


@router.get("/{benchmark_id}", response_model=BenchmarkRead)
async def get_benchmark(
    benchmark_id: uuid.UUID, session: SessionDep, user: CurrentUser
) -> Benchmark:
    benchmark = await BenchmarkRepository(session).get_with_tasks(benchmark_id)
    if benchmark is None or (
        benchmark.owner_id is not None and benchmark.owner_id != user.id
    ):
        raise NotFoundError("Benchmark not found")
    return benchmark
