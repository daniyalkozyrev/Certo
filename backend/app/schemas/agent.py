"""Agent API schemas."""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.agent import AgentType
from app.schemas.common import ORMModel

# Config keys whose values must never leave the server in an API response.
_SENSITIVE_KEYS = {"api_key", "apikey", "token", "secret", "password"}


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


class AgentUpdate(BaseModel):
    """Partial update. Any field left None is unchanged; `config`, if provided,
    REPLACES the stored config wholesale (so a key can be dropped by omitting it)."""

    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    config: AgentConfig | None = None


class AgentRead(ORMModel):
    id: uuid.UUID
    name: str
    description: str | None
    agent_type: AgentType
    config: dict[str, Any]
    created_at: datetime
    updated_at: datetime

    @field_validator("config", mode="before")
    @classmethod
    def _redact_secrets(cls, v: Any) -> Any:
        """Never return an agent's api_key (etc.) over the API — mask it so the UI
        can still show that a value is configured without leaking it."""
        if isinstance(v, dict):
            return {
                k: ("***configured***" if k.lower() in _SENSITIVE_KEYS and val else val)
                for k, val in v.items()
            }
        return v
