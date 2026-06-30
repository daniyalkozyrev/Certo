"""Trace repository."""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.models.trace import Trace
from app.repositories.base import BaseRepository


class TraceRepository(BaseRepository[Trace]):
    model = Trace

    async def get_with_spans(self, id_: uuid.UUID) -> Trace | None:
        stmt = (
            select(Trace)
            .where(Trace.id == id_)
            .options(selectinload(Trace.spans))
        )
        return await self.session.scalar(stmt)
