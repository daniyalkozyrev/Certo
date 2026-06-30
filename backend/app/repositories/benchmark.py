"""Benchmark repository."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.benchmark import Benchmark
from app.repositories.base import BaseRepository


class BenchmarkRepository(BaseRepository[Benchmark]):
    model = Benchmark

    async def get_with_tasks(self, id_: uuid.UUID) -> Benchmark | None:
        stmt = (
            select(Benchmark)
            .where(Benchmark.id == id_)
            .options(selectinload(Benchmark.tasks))
        )
        return await self.session.scalar(stmt)
