"""Agent API schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.agent import AgentType
from app.schemas.common import ORMModel


class AgentConfig(BaseModel):
    """Inference config for the agent under test. All fields optional; missing
    api_key/base_url/model fall back to AGENT_DEFAULT_* settings.

    Extra keys are allowed and passed through to the runner — e.g. `provider`
    ("anthropic" | "openai") and `max_steps` for agentic/multi-agent agents."""

    model_config = ConfigDict(extra="allow")

    base_url: str | None = None
    api_key: str | None = None
    model: str | None = None
    system_prompt: str | None = None
    provider: str | None = None
    max_steps: int | None = None


class AgentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    agent_type: AgentType = AgentType.LLM_ENDPOINT
    config: AgentConfig = Field(default_factory=AgentConfig)


class AgentRead(ORMModel):
    id: uuid.UUID
    name: str
    description: str | None
    agent_type: AgentType
    config: dict[str, Any]
    created_at: datetime
    updated_at: datetime
