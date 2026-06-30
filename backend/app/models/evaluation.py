"""Evaluation (one run of an agent over a benchmark) and per-task results.

A TaskResult doubles as a reward-labelled trajectory record: it is exactly the
data we later export to build agent-improvement datasets (+1 / -1 reward).
"""

from __future__ import annotations

import enum
import uuid
from typing import Any

from sqlalchemy import Enum as SAEnum
from sqlalchemy import Float, ForeignKey, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import GUID, Base, JSONType, TimestampMixin, UUIDMixin


class EvaluationStatus(str, enum.Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Evaluation(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "evaluations"

    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )
    agent_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("agents.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    benchmark_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("benchmarks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    status: Mapped[EvaluationStatus] = mapped_column(
        SAEnum(EvaluationStatus, name="evaluation_status"),
        default=EvaluationStatus.PENDING,
        nullable=False,
        index=True,
    )
    # Aggregate metrics, populated when status == COMPLETED.
    trust_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    pass_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    # Free-form per-dimension breakdown for the UI.
    summary: Mapped[dict[str, Any] | None] = mapped_column(JSONType, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    results: Mapped[list[TaskResult]] = relationship(
        back_populates="evaluation",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class TaskResult(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "task_results"

    evaluation_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("evaluations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    task_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("tasks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # What the agent produced.
    agent_output: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Sandbox execution outcome.
    sandbox_stdout: Mapped[str | None] = mapped_column(Text, nullable=True)
    sandbox_stderr: Mapped[str | None] = mapped_column(Text, nullable=True)
    sandbox_exit_code: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Judge outcome (ensemble consensus on the 1..5 absolute scale).
    judge_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    judge_feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Per-judge votes: [{"judge": str, "score": int, "feedback": str}, ...].
    judge_votes: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSONType, nullable=True
    )
    disagreement: Mapped[str | None] = mapped_column(Text, nullable=True)  # Low/Medium/High

    # Derived signals.
    normalized_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    reward: Mapped[int | None] = mapped_column(Integer, nullable=True)  # +1 / -1

    # ── Agentic runs (agent_type = agentic / multi_agent) ────────────────
    # The agent's final answer after its multi-step trajectory.
    final_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Number of steps the agent took, and the mean per-step judge score.
    step_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    mean_step_score: Mapped[float | None] = mapped_column(Float, nullable=True)

    evaluation: Mapped[Evaluation] = relationship(back_populates="results")
    # Per-step trajectory with per-step judge grades (empty for one-shot agents).
    steps: Mapped[list[AgentStep]] = relationship(
        back_populates="task_result",
        cascade="all, delete-orphan",
        order_by="AgentStep.step_index",
        lazy="selectin",
    )


class AgentStep(UUIDMixin, TimestampMixin, Base):
    """One step of an agent's trajectory inside the sandbox, graded on its own.

    This is the unit the LLM judge scores "каждый шаг": for every action the
    agent takes we keep what it thought, the code it ran, what the sandbox
    returned, and the judge's per-step verdict. Together the rows form a
    reward-labelled trajectory for later agent-improvement datasets.
    """

    __tablename__ = "agent_steps"

    task_result_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("task_results.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    step_index: Mapped[int] = mapped_column(Integer, nullable=False)
    # Which agent produced this step: "agent" | "planner" | "worker" | "reviewer".
    role: Mapped[str] = mapped_column(Text, nullable=False, default="agent")

    # What the agent did.
    thought: Mapped[str | None] = mapped_column(Text, nullable=True)
    action_code: Mapped[str | None] = mapped_column(Text, nullable=True)

    # What the sandbox returned for this step.
    observation_stdout: Mapped[str | None] = mapped_column(Text, nullable=True)
    observation_stderr: Mapped[str | None] = mapped_column(Text, nullable=True)
    exit_code: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # The judge's per-step grade (1..5 ensemble consensus).
    judge_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    judge_feedback: Mapped[str | None] = mapped_column(Text, nullable=True)
    judge_votes: Mapped[list[dict[str, Any]] | None] = mapped_column(
        JSONType, nullable=True
    )

    task_result: Mapped[TaskResult] = relationship(back_populates="steps")
