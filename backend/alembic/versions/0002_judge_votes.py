"""add judge ensemble votes to task_results

Revision ID: 0002
Revises: 0001
Create Date: 2026-06-21

Adds per-judge votes + disagreement level produced by the ensemble judge.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "task_results",
        sa.Column("judge_votes", postgresql.JSONB, nullable=True),
    )
    op.add_column(
        "task_results",
        sa.Column("disagreement", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("task_results", "disagreement")
    op.drop_column("task_results", "judge_votes")
