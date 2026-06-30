"""Agent under evaluation."""

from __future__ import annotations

import enum
import uuid
from typing import Any

from sqlalchemy import Enum as SAEnum
from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import GUID, Base, JSONType, TimestampMixin, UUIDMixin


class AgentType(str, enum.Enum):
    """How the agent produces a solution for a task."""

    LLM_ENDPOINT = "llm_endpoint"  # one-shot: calls a chat endpoint once -> code
    AGENTIC = "agentic"  # multi-step loop: think -> run code in a live sandbox -> observe -> repeat
    MULTI_AGENT = "multi_agent"  # planner -> worker(loop) -> reviewer, in a live sandbox


class Agent(UUIDMixin, TimestampMixin, Base):
    __tablename__ = "agents"

    # Owner (null = shared/demo data visible to everyone).
    owner_id: Mapped[uuid.UUID | None] = mapped_column(
        GUID, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    agent_type: Mapped[AgentType] = mapped_column(
        SAEnum(AgentType, name="agent_type"),
        default=AgentType.LLM_ENDPOINT,
        nullable=False,
    )
    # Inference config: {base_url, api_key, model, system_prompt, ...}.
    # api_key may be null -> falls back to AGENT_DEFAULT_* settings.
    config: Mapped[dict[str, Any]] = mapped_column(
        JSONType, nullable=False, default=dict
    )
