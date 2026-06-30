"""Skill / tool library (scaffold).

Reusable tools and skills that agents can be equipped with. The `embedding`
column (pgvector) enables semantic retrieval of relevant skills for a task.
Active use (population + similarity search) is a post-MVP step.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.config import settings
from app.models.base import Base, JSONType, TimestampMixin, UUIDMixin

# Dimensionality of the embedding model used for skill retrieval.
EMBEDDING_DIM = 1536

# Embedding stored as a pgvector column ONLY when explicitly enabled (the Postgres
# `vector` extension must exist). Otherwise JSON everywhere — so create_all works on
# a plain managed Postgres, and the MVP (no similarity search yet) is unaffected.
EmbeddingType: Any = JSON()
if settings.pgvector_enabled:
    try:
        from pgvector.sqlalchemy import Vector

        EmbeddingType = JSON().with_variant(Vector(EMBEDDING_DIM), "postgresql")
    except ImportError:  # pgvector not installed
        EmbeddingType = JSON()


class Skill(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "skills"

    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Tool/skill definition (e.g. JSON schema, code, or instructions).
    definition: Mapped[dict[str, Any]] = mapped_column(
        JSONType, nullable=False, default=dict
    )
    embedding: Mapped[list[float] | None] = mapped_column(
        EmbeddingType, nullable=True
    )
