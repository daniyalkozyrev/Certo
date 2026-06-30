"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-06-20

Creates: agents, benchmarks, tasks, evaluations, task_results, skills.
Assumes the `vector` extension is created in env.py before this runs.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)
JSONB = postgresql.JSONB

agent_type = sa.Enum("llm_endpoint", name="agent_type")
grading_type = sa.Enum("judge", "code", name="grading_type")
evaluation_status = sa.Enum(
    "pending", "running", "completed", "failed", name="evaluation_status"
)


def upgrade() -> None:
    op.create_table(
        "agents",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("name", sa.String(255), nullable=False, index=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("agent_type", agent_type, nullable=False),
        sa.Column("config", JSONB, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "benchmarks",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("name", sa.String(255), nullable=False, index=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "tasks",
        sa.Column("id", UUID, primary_key=True),
        sa.Column(
            "benchmark_id",
            UUID,
            sa.ForeignKey("benchmarks.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("prompt", sa.Text(), nullable=False),
        sa.Column("rubric", sa.Text(), nullable=True),
        sa.Column("reference_answer", sa.Text(), nullable=True),
        sa.Column("grading_type", grading_type, nullable=False),
        sa.Column("test_code", sa.Text(), nullable=True),
        sa.Column("max_score", sa.Integer(), nullable=False, server_default="5"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "evaluations",
        sa.Column("id", UUID, primary_key=True),
        sa.Column(
            "agent_id",
            UUID,
            sa.ForeignKey("agents.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "benchmark_id",
            UUID,
            sa.ForeignKey("benchmarks.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("status", evaluation_status, nullable=False, index=True),
        sa.Column("trust_score", sa.Float(), nullable=True),
        sa.Column("pass_rate", sa.Float(), nullable=True),
        sa.Column("summary", JSONB, nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "task_results",
        sa.Column("id", UUID, primary_key=True),
        sa.Column(
            "evaluation_id",
            UUID,
            sa.ForeignKey("evaluations.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column(
            "task_id",
            UUID,
            sa.ForeignKey("tasks.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("agent_output", sa.Text(), nullable=True),
        sa.Column("sandbox_stdout", sa.Text(), nullable=True),
        sa.Column("sandbox_stderr", sa.Text(), nullable=True),
        sa.Column("sandbox_exit_code", sa.Integer(), nullable=True),
        sa.Column("judge_score", sa.Integer(), nullable=True),
        sa.Column("judge_feedback", sa.Text(), nullable=True),
        sa.Column("normalized_score", sa.Float(), nullable=True),
        sa.Column("reward", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "skills",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("name", sa.String(255), nullable=False, index=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("definition", JSONB, nullable=False),
        sa.Column("embedding", Vector(1536), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("skills")
    op.drop_table("task_results")
    op.drop_table("evaluations")
    op.drop_table("tasks")
    op.drop_table("benchmarks")
    op.drop_table("agents")
    evaluation_status.drop(op.get_bind(), checkfirst=True)
    grading_type.drop(op.get_bind(), checkfirst=True)
    agent_type.drop(op.get_bind(), checkfirst=True)
