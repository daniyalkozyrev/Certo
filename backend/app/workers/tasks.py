"""Arq background tasks."""

from __future__ import annotations

import uuid
from typing import Any

from app.core.database import SessionFactory
from app.core.logging import get_logger
from app.services.evaluation_service import EvaluationService
from app.services.trace_scoring import TraceScoringService

logger = get_logger(__name__)


async def _execute(evaluation_id: str) -> None:
    async with SessionFactory() as session:
        service = EvaluationService(session)
        await service.run(uuid.UUID(evaluation_id))


async def _score_trace(trace_id: str) -> None:
    async with SessionFactory() as session:
        await TraceScoringService(session).run(uuid.UUID(trace_id))


async def run_evaluation_task(ctx: dict[str, Any], evaluation_id: str) -> None:
    """Arq entrypoint: execute a full evaluation run in a background worker."""
    logger.info("worker.run_evaluation", evaluation_id=evaluation_id)
    await _execute(evaluation_id)
    logger.info("worker.run_evaluation_done", evaluation_id=evaluation_id)


async def run_evaluation_inline(evaluation_id: str) -> None:
    """In-process entrypoint (local dev, no Redis). Swallows errors — the run's
    own status/error fields already capture failures."""
    logger.info("inline.run_evaluation", evaluation_id=evaluation_id)
    try:
        await _execute(evaluation_id)
    except Exception:
        logger.exception("inline.run_evaluation_failed", evaluation_id=evaluation_id)
    logger.info("inline.run_evaluation_done", evaluation_id=evaluation_id)


async def score_trace_task(ctx: dict[str, Any], trace_id: str) -> None:
    """Arq entrypoint: score an ingested trace in a background worker."""
    logger.info("worker.score_trace", trace_id=trace_id)
    await _score_trace(trace_id)
    logger.info("worker.score_trace_done", trace_id=trace_id)


async def score_trace_inline(trace_id: str) -> None:
    """In-process entrypoint (local dev, no Redis)."""
    logger.info("inline.score_trace", trace_id=trace_id)
    try:
        await _score_trace(trace_id)
    except Exception:
        logger.exception("inline.score_trace_failed", trace_id=trace_id)
    logger.info("inline.score_trace_done", trace_id=trace_id)
