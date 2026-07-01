"""Async SQLAlchemy engine, session factory and FastAPI dependency."""

from __future__ import annotations

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import settings

# SQLite (local dev) doesn't support pool_pre_ping the same way; keep engine simple.
_engine_kwargs: dict = {"echo": settings.db_echo, "future": True}
if not settings.is_sqlite:
    _engine_kwargs["pool_pre_ping"] = True

engine = create_async_engine(settings.database_url, **_engine_kwargs)

SessionFactory = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
)


async def init_models() -> None:
    """Create all tables directly (used for SQLite local dev — no Alembic)."""
    # Import models so every table is registered on the metadata.
    from app.models import Base  # noqa: PLC0415

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def ensure_auth_columns() -> None:
    """Add password_hash / email_verified to an EXISTING users table.

    create_all() only creates missing tables — it never ALTERs an existing one.
    A DB that predates password auth (e.g. the live Postgres) already has a
    `users` table, so its new columns must be added explicitly. Idempotent and
    dialect-aware; safe to run on every boot."""
    from sqlalchemy import text  # noqa: PLC0415

    from app.core.logging import get_logger  # noqa: PLC0415

    logger = get_logger(__name__)
    try:
        async with engine.begin() as conn:
            if engine.dialect.name == "postgresql":
                await conn.execute(
                    text("ALTER TABLE users ADD COLUMN IF NOT EXISTS password_hash VARCHAR(255)")
                )
                await conn.execute(
                    text(
                        "ALTER TABLE users ADD COLUMN IF NOT EXISTS "
                        "email_verified BOOLEAN NOT NULL DEFAULT FALSE"
                    )
                )
            else:  # sqlite — no ADD COLUMN IF NOT EXISTS; check pragma first
                rows = await conn.execute(text("PRAGMA table_info(users)"))
                cols = {r[1] for r in rows}
                if "password_hash" not in cols:
                    await conn.execute(text("ALTER TABLE users ADD COLUMN password_hash VARCHAR(255)"))
                if "email_verified" not in cols:
                    await conn.execute(
                        text("ALTER TABLE users ADD COLUMN email_verified BOOLEAN NOT NULL DEFAULT 0")
                    )
    except Exception as exc:  # never block startup on a best-effort migration
        logger.warning("db.ensure_auth_columns_failed", error=str(exc))


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency yielding a session with commit/rollback handling."""
    async with SessionFactory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
