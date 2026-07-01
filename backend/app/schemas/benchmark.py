"""Benchmark and Task API schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.models.benchmark import GradingType
from app.schemas.common import ORMModel


class TaskCreate(BaseModel):
    prompt: str = Field(min_length=1)
    rubric: str | None = None
    reference_answer: str | None = None
    grading_type: GradingType = GradingType.JUDGE
    test_code: str | None = None
    # Benchmark-specific payload (e.g. SWE-bench harness inputs:
    # instance_id / repo / base_commit / FAIL_TO_PASS / gold_patch ...).
    meta: dict[str, Any] | None = None
    max_score: int = Field(default=5, ge=1, le=10)


class TaskRead(ORMModel):
    id: uuid.UUID
    benchmark_id: uuid.UUID
    prompt: str
    rubric: str | None
    reference_answer: str | None
    grading_type: GradingType
    test_code: str | None
    meta: dict[str, Any] | None = None
    max_score: int
    created_at: datetime


class BenchmarkCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    tasks: list[TaskCreate] = Field(default_factory=list)


class BenchmarkRead(ORMModel):
    id: uuid.UUID
    name: str
    description: str | None
    created_at: datetime
    tasks: list[TaskRead] = Field(default_factory=list)
