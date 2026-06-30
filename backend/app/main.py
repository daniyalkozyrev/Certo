"""FastAPI application entrypoint."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.v1.router import api_router
from app.core.config import settings
from app.core.database import init_models
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging, get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()

    # Local dev (SQLite): create tables directly instead of running Alembic.
    if settings.is_sqlite:
        await init_models()

    # Background execution: Arq+Redis in production, in-process for local dev.
    if settings.run_worker_inline:
        app.state.arq = None
    else:
        from arq import create_pool
        from arq.connections import RedisSettings

        app.state.arq = await create_pool(RedisSettings.from_dsn(settings.redis_url))

    logger.info("startup", env=settings.env, sqlite=settings.is_sqlite,
                inline_worker=settings.run_worker_inline,
                mock_judge=settings.mock_judge, mock_sandbox=settings.mock_sandbox)
    try:
        yield
    finally:
        if app.state.arq is not None:
            await app.state.arq.close()
        logger.info("shutdown")


app = FastAPI(
    title=f"{settings.project_name} API",
    version="0.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)
app.include_router(api_router, prefix=settings.api_prefix)


@app.get("/health", tags=["meta"])
async def health() -> dict[str, str]:
    return {"status": "ok", "env": settings.env}
