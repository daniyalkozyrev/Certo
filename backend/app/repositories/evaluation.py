"""Evaluation repository."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.evaluation import Evaluation, TaskResult
from app.repositories.base import BaseRepository


class EvaluationRepository(BaseRepository[Evaluation]):
    model = Evaluation

    async def get_with_results(self, id_: uuid.UUID) -> Evaluation | None:
        stmt = (
            select(Evaluation)
            .where(Evaluation.id == id_)
            .options(selectinload(Evaluation.results).selectinload(TaskResult.steps))
        )
        return await self.session.scalar(stmt)
