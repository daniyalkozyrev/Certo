"""trace-ingestion core: traces + spans

Revision ID: 0004
Revises: 0003
Create Date: 2026-06-25

Adds the Trace (an agent run) and Span (one graded step) tables — the
trace-first core. Local SQLite dev uses create_all (see scripts/migrate_local.py);
this migration is for Postgres parity. Enum value convention matches 0001/0003.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UUID = postgresql.UUID(as_uuid=True)
JSONB = postgresql.JSONB

trace_status = sa.Enum("running", "completed", "failed", name="trace_status")
trace_source = sa.Enum("sdk", "sandbox", "agentic", name="trace_source")


def upgrade() -> None:
    op.create_table(
        "traces",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("owner_id", UUID, sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True),
        sa.Column("agent_id", UUID, sa.ForeignKey("agents.id", ondelete="SET NULL"), nullable=True, index=True),
        sa.Column("name", sa.String(255), nullable=True),
        sa.Column("task", sa.Text(), nullable=True),
        sa.Column("final_output", sa.Text(), nullable=True),
        sa.Column("expected_output", sa.Text(), nullable=True),
        sa.Column("test_code", sa.Text(), nullable=True),
        sa.Column("status", trace_status, nullable=False, index=True),
        sa.Column("source", trace_source, nullable=False),
        sa.Column("meta", JSONB, nullable=True),
        sa.Column("trust_score", sa.Float(), nullable=True),
        sa.Column("summary", JSONB, nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "spans",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("trace_id", UUID, sa.ForeignKey("traces.id", ondelete="CASCADE"), nullable=False, index=True),
        sa.Column("parent_span_id", UUID, nullable=True),
        sa.Column("step_index", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("name", sa.Text(), nullable=True),
        sa.Column("input", JSONB, nullable=True),
        sa.Column("output", JSONB, nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("tokens", sa.Integer(), nullable=True),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("judge_score", sa.Integer(), nullable=True),
        sa.Column("judge_feedback", sa.Text(), nullable=True),
        sa.Column("judge_votes", JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("spans")
    op.drop_table("traces")
    trace_source.drop(op.get_bind(), checkfirst=True)
    trace_status.drop(op.get_bind(), checkfirst=True)
