"""Trace + Span — the canonical record of an agent's run.

This is the new core: an agent runs wherever it lives, emits a *trace* (a list of
spans: tool calls, LLM calls, observations, hand-offs), and Certo ingests + scores
that trajectory. A Span is the generalised, source-agnostic form of an `AgentStep`
(`models/evaluation.py`); internal sandbox/agentic runs also produce Traces.
"""

from __future__ import annotations

import enum
import uuid
from typing import Any

from sqlalchemy import Enum as SAEnum
from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import GUID, Base, JSONType, TimestampMixin, UUIDMixin


class TraceStatus(str, enum.Enum):
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class TraceSource(str, enum.Enum):
    SDK = "sdk"  # ingested from an externally-instrumented agent
    SANDBOX = "sandbox"  # produced by Certo's E2B trace-eval
    AGENTIC = "agentic"  # produced by Certo's in-house agentic runner


class SpanKind(str, enum.Enum):
    LLM = "llm"
    TOOL = "tool"
    AGENT = "agent"
    OBSERVATION = "observation"
    HANDOFF = "handoff"


class Trace(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "traces"

    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )
    agent_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("agents.id", ondelete="SET NULL"), nullable=True, index=True
    )

    name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # The goal/instruction the agent was working on.
    task: Mapped[str | None] = mapped_column(Text, nullable=True)
    final_output: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Optional ground truth for the objective axis.
    expected_output: Mapped[str | None] = mapped_column(Text, nullable=True)
    test_code: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[TraceStatus] = mapped_column(
        SAEnum(TraceStatus, name="trace_status"),
        default=TraceStatus.RUNNING,
        nullable=False,
        index=True,
    )
    source: Mapped[TraceSource] = mapped_column(
        SAEnum(TraceSource, name="trace_source"),
        default=TraceSource.SDK,
        nullable=False,
    )
    # Free-form run metadata: framework / model / total_tokens / latency_ms / cost.
    meta: Mapped[dict[str, Any] | None] = mapped_column(JSONType, nullable=True)

    # Scoring outputs (populated once graded).
    trust_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    summary: Mapped[dict[str, Any] | None] = mapped_column(JSONType, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    spans: Mapped[list[Span]] = relationship(
        back_populates="trace",
        cascade="all, delete-orphan",
        order_by="Span.step_index",
        lazy="selectin",
    )


class Span(UUIDMixin, TimestampMixin, Base):
    """One step of a trace, graded on its own by the judge."""

    __tablename__ = "spans"

    trace_id: Mapped[uuid.UUID] = mapped_column(
        GUID, ForeignKey("traces.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # Optional nesting / multi-agent parent (by id; no hard FK to stay flexible).
    parent_span_id: Mapped[uuid.UUID | None] = mapped_column(GUID, nullable=True)
    step_index: Mapped[int] = mapped_column(Integer, nullable=False)

    kind: Mapped[str] = mapped_column(String(32), nullable=False, default=SpanKind.TOOL.value)
    name: Mapped[str | None] = mapped_column(Text, nullable=True)  # tool name / agent role

    input: Mapped[Any | None] = mapped_column(JSONType, nullable=True)
    output: Mapped[Any | None] = mapped_column(JSONType, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    tokens: Mapped[int | None] = mapped_column(Integer, nullable=True)
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Per-span judge verdict.
    judge_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    judge_feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    judge_votes: Mapped[list[dict[str, Any]] | None] = mapped_column(JSONType, nullable=True)

    trace: Mapped[Trace] = relationship(back_populates="spans")
