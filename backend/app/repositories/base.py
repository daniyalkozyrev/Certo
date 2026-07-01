"""Generic async repository with common CRUD operations."""

from __future__ import annotations

import uuid
from typing import Generic, TypeVar

from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.base import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    model: type[ModelT]

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get(self, id_: uuid.UUID) -> ModelT | None:
        return await self.session.get(self.model, id_)

    async def list(self, *, limit: int = 50, offset: int = 0) -> list[ModelT]:
        stmt = (
            select(self.model)
            .order_by(self.model.created_at.desc())  # type: ignore[attr-defined]
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.scalars(stmt)
        return list(result.all())

    async def count(self) -> int:
        stmt = select(func.count()).select_from(self.model)
        return int(await self.session.scalar(stmt) or 0)

    # ── Owner-scoped variants (own rows + shared/demo rows where owner is null) ──
    def _owned_filter(self, owner_id: uuid.UUID):
        owner_col = self.model.owner_id  # type: ignore[attr-defined]
        return or_(owner_col == owner_id, owner_col.is_(None))

    async def list_owned(
        self, owner_id: uuid.UUID, *, limit: int = 50, offset: int = 0
    ) -> list[ModelT]:
        stmt = (
            select(self.model)
            .where(self._owned_filter(owner_id))
            .order_by(self.model.created_at.desc())  # type: ignore[attr-defined]
            .limit(limit)
            .offset(offset)
        )
        result = await self.session.scalars(stmt)
        return list(result.all())

    async def count_owned(self, owner_id: uuid.UUID) -> int:
        stmt = (
            select(func.count())
            .select_from(self.model)
            .where(self._owned_filter(owner_id))
        )
        return int(await self.session.scalar(stmt) or 0)

    async def add(self, obj: ModelT) -> ModelT:
        self.session.add(obj)
        await self.session.flush()
        return obj

    async def delete(self, obj: ModelT) -> None:
        await self.session.delete(obj)
        await self.session.flush()
