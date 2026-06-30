"""Benchmark (a collection of tasks) and Task (a single unit of evaluation)."""

from __future__ import annotations

import enum
import uuid

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import GUID, Base, JSONType, TimestampMixin, UUIDMixin


class GradingType(str, enum.Enum):
    """How a task's output is graded."""

    JUDGE = "judge"  # LLM-as-a-Judge scores against the rubric
    CODE = "code"  # deterministic: run test_code in the sandbox, pass/fail
    MATCH = "match"  # objective: normalised answer-match vs reference_answer (no code run)
    SWEBENCH = "swebench"  # objective: apply the agent's patch + run the repo's tests (official harness)


class Benchmark(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "benchmarks"

    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    tasks: Mapped[list[Task]] = relationship(
        back_populates="benchmark",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class Task(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "tasks"

    benchmark_id: Mapped[uuid.UUID] = mapped_column(
        GUID,
        ForeignKey("benchmarks.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # The instruction shown to the agent under test.
    prompt: Mapped[str] = mapped_column(Text, nullable=False)
    # Scoring rubric handed to the judge (Prometheus-2 absolute grading).
    rubric: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Optional gold answer to anchor the judge.
    reference_answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    grading_type: Mapped[GradingType] = mapped_column(
        SAEnum(GradingType, name="grading_type"),
        default=GradingType.JUDGE,
        nullable=False,
    )
    # For grading_type=CODE: code run in the sandbox to assert correctness.
    test_code: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Benchmark-specific payload that doesn't fit the generic columns. For
    # grading_type=SWEBENCH this holds the harness inputs:
    #   {instance_id, repo, base_commit, version, test_patch,
    #    FAIL_TO_PASS, PASS_TO_PASS, environment_setup_commit, gold_patch}.
    meta: Mapped[dict | None] = mapped_column(JSONType, nullable=True)
    max_score: Mapped[int] = mapped_column(Integer, default=5, nullable=False)

    benchmark: Mapped[Benchmark] = relationship(back_populates="tasks")
