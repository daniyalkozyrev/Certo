"""agentic agents: new agent types, trajectory steps, agentic task_result fields

Revision ID: 0003
Revises: 0002
Create Date: 2026-06-21

Adds the `agentic` / `multi_agent` agent types, the per-step `agent_steps`
trajectory table (each step graded by the judge), and the agentic summary
columns on `task_results`.

NOTE: the Postgres enum keeps the lowercase value convention established in
0001. Local SQLite dev does not use Alembic (see scripts/migrate_local.py).
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)
JSONB = postgresql.JSONB


def upgrade() -> None:
    # 1. New agent types on the existing enum.
    op.execute("ALTER TYPE agent_type ADD VALUE IF NOT EXISTS 'agentic'")
    op.execute("ALTER TYPE agent_type ADD VALUE IF NOT EXISTS 'multi_agent'")

    # 2. Agentic summary columns on task_results.
    op.add_column("task_results", sa.Column("final_answer", sa.Text(), nullable=True))
    op.add_column("task_results", sa.Column("step_count", sa.Integer(), nullable=True))
    op.add_column("task_results", sa.Column("mean_step_score", sa.Float(), nullable=True))

    # 3. Per-step trajectory table.
    op.create_table(
        "agent_steps",
        sa.Column("id", UUID, primary_key=True),
        sa.Column(
            "task_result_id",
            UUID,
            sa.ForeignKey("task_results.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("step_index", sa.Integer(), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("thought", sa.Text(), nullable=True),
        sa.Column("action_code", sa.Text(), nullable=True),
        sa.Column("observation_stdout", sa.Text(), nullable=True),
        sa.Column("observation_stderr", sa.Text(), nullable=True),
        sa.Column("exit_code", sa.Integer(), nullable=True),
        sa.Column("judge_score", sa.Integer(), nullable=True),
        sa.Column("judge_feedback", sa.Text(), nullable=True),
        sa.Column("judge_votes", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("agent_steps")
    op.drop_column("task_results", "mean_step_score")
    op.drop_column("task_results", "step_count")
    op.drop_column("task_results", "final_answer")
    # NOTE: Postgres cannot easily DROP enum values; agent_type keeps the
    # 'agentic' / 'multi_agent' labels after downgrade (harmless).
