"""Auth API schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr

from app.schemas.common import ORMModel


class RequestCodeIn(BaseModel):
    email: EmailStr


class RequestCodeOut(BaseModel):
    sent: bool
    # Returned only in local/console mode so the flow is testable without email.
    dev_code: str | None = None


class VerifyCodeIn(BaseModel):
    email: EmailStr
    code: str


class UserRead(ORMModel):
    id: uuid.UUID
    email: str
    name: str | None
    auth_provider: str
    created_at: datetime


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead


class AuthConfigOut(BaseModel):
    google_enabled: bool
    email_mode: str
