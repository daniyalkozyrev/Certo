"""Trace + Span API schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.models.trace import SpanKind, TraceSource, TraceStatus
from app.schemas.common import ORMModel
from app.schemas.evaluation import JudgeVoteRead

# Hard caps to keep ingestion bounded: each span is graded by the judge, so an
# unbounded trace would mean an unbounded number of (paid) LLM calls.
MAX_SPANS = 100
_KINDS = {k.value for k in SpanKind}


class SpanIn(BaseModel):
    kind: str = Field(description="llm | tool | agent | observation | handoff")
    name: str | None = Field(default=None, max_length=255)
    input: Any | None = None
    output: Any | None = None
    error: str | None = Field(default=None, max_length=20_000)
    tokens: int | None = None
    latency_ms: int | None = None

    @field_validator("kind", mode="before")
    @classmethod
    def _normalise_kind(cls, v: object) -> str:
        # Coerce unknown kinds to "tool" rather than 500-ing on a typo.
        s = str(v or "").strip().lower()
        return s if s in _KINDS else SpanKind.TOOL.value


class TraceIngest(BaseModel):
    task: str = Field(min_length=1, max_length=20_000, description="The goal/instruction the agent worked on.")
    name: str | None = Field(default=None, max_length=255)
    agent_id: uuid.UUID | None = None
    source: TraceSource = TraceSource.SDK
    final_output: str | None = Field(default=None, max_length=100_000)
    expected_output: str | None = Field(default=None, max_length=20_000)  # ground truth (objective axis)
    test_code: str | None = Field(default=None, max_length=20_000)  # deterministic check vs `agent_stdout`
    meta: dict[str, Any] | None = None
    spans: list[SpanIn] = Field(default_factory=list, max_length=MAX_SPANS)


class SpanRead(ORMModel):
    id: uuid.UUID
    step_index: int
    kind: str
    name: str | None
    input: Any | None
    output: Any | None
    error: str | None
    tokens: int | None
    latency_ms: int | None
    judge_score: int | None
    judge_feedback: str | None
    judge_votes: list[JudgeVoteRead] | None = None


class TraceRead(ORMModel):
    id: uuid.UUID
    agent_id: uuid.UUID | None
    name: str | None
    task: str | None
    final_output: str | None
    status: TraceStatus
    source: TraceSource
    meta: dict[str, Any] | None
    trust_score: float | None
    summary: dict[str, Any] | None
    error: str | None
    created_at: datetime
    updated_at: datetime


class TraceDetail(TraceRead):
    spans: list[SpanRead] = []
