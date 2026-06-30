"""Arq worker settings. Run with: `arq app.workers.settings.WorkerSettings`."""

from __future__ import annotations

from arq.connections import RedisSettings

from app.core.config import settings
from app.core.logging import configure_logging
from app.workers.tasks import run_evaluation_task, score_trace_task


async def startup(ctx: dict) -> None:
    configure_logging()


class WorkerSettings:
    functions = [run_evaluation_task, score_trace_task]
    redis_settings = RedisSettings.from_dsn(settings.redis_url)
    on_startup = startup
    max_jobs = 4
    job_timeout = 600  # seconds; evaluations can be long
