"""Aggregate v1 API router."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import agents, auth, benchmarks, evaluations, trace, traces

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(agents.router)
api_router.include_router(benchmarks.router)
api_router.include_router(evaluations.router)
api_router.include_router(trace.router)
api_router.include_router(traces.router)
