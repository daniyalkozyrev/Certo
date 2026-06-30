"""Shared API dependencies: DB session, pagination, (placeholder) auth."""

from __future__ import annotations

import uuid
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, Query
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.exceptions import CertoError
from app.core.security import decode_access_token
from app.models.user import User


async def db_session() -> AsyncGenerator[AsyncSession, None]:
    async for session in get_session():
        yield session


SessionDep = Annotated[AsyncSession, Depends(db_session)]


@dataclass
class Pagination:
    limit: int
    offset: int


def pagination(
    limit: Annotated[int, Query(ge=1, le=200)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> Pagination:
    return Pagination(limit=limit, offset=offset)


PaginationDep = Annotated[Pagination, Depends(pagination)]


# ── Authentication ───────────────────────────────────────────
class AuthError(CertoError):
    """Authentication failed."""

    status_code = 401
    code = "unauthorized"


_bearer = HTTPBearer(auto_error=False)


async def get_current_user(
    session: SessionDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
) -> User:
    if credentials is None:
        raise AuthError("Not authenticated")
    try:
        payload = decode_access_token(credentials.credentials)
    except Exception as exc:  # invalid / expired token
        raise AuthError("Invalid or expired token") from exc

    user = await session.get(User, uuid.UUID(payload["sub"]))
    if user is None:
        raise AuthError("User not found")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]
