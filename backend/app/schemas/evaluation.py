"""Evaluation and TaskResult API schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel

from app.models.evaluation import EvaluationStatus
from app.schemas.common import ORMModel


class EvaluationCreate(BaseModel):
    agent_id: uuid.UUID
    benchmark_id: uuid.UUID


class JudgeVoteRead(BaseModel):
    judge: str
    score: int
    feedback: str


class AgentStepRead(ORMModel):
    id: uuid.UUID
    step_index: int
    role: str
    thought: str | None
    action_code: str | None
    observation_stdout: str | None
    observation_stderr: str | None
    exit_code: int | None
    judge_score: int | None
    judge_feedback: str | None
    judge_votes: list[JudgeVoteRead] | None = None


class TaskResultRead(ORMModel):
    id: uuid.UUID
    task_id: uuid.UUID
    agent_output: str | None
    sandbox_stdout: str | None
    sandbox_stderr: str | None
    sandbox_exit_code: int | None
    judge_score: int | None
    judge_feedback: str | None
    judge_votes: list[JudgeVoteRead] | None = None
    disagreement: str | None = None
    normalized_score: float | None
    reward: int | None
    # Agentic runs: the agent's final answer + its graded per-step trajectory.
    final_answer: str | None = None
    step_count: int | None = None
    mean_step_score: float | None = None
    steps: list[AgentStepRead] = []
    created_at: datetime


class EvaluationRead(ORMModel):
    id: uuid.UUID
    agent_id: uuid.UUID
    benchmark_id: uuid.UUID
    status: EvaluationStatus
    trust_score: float | None
    pass_rate: float | None
    summary: dict[str, Any] | None
    error: str | None
    created_at: datetime
    updated_at: datetime


class EvaluationDetail(EvaluationRead):
    results: list[TaskResultRead] = []
