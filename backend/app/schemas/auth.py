"""Auth API schemas."""

from __future__ import annotations

import uuid
from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.schemas.common import ORMModel


class RequestCodeIn(BaseModel):
    email: EmailStr


class RequestCodeOut(BaseModel):
    sent: bool
    # True once the account is verified and can log in with a password.
    verified: bool = False
    # Returned only in local/console mode so the flow is testable without email.
    dev_code: str | None = None


class SignupIn(BaseModel):
    email: EmailStr
    # bcrypt truncates >72 bytes; cap it well under that and require a floor.
    password: str = Field(min_length=8, max_length=72)
    name: str | None = Field(default=None, max_length=255)


class LoginIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=72)


class VerifyCodeIn(BaseModel):
    email: EmailStr
    code: str


class UserRead(ORMModel):
    id: uuid.UUID
    email: str
    name: str | None
    auth_provider: str
    email_verified: bool = False
    created_at: datetime


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserRead


class AuthConfigOut(BaseModel):
    google_enabled: bool
    email_mode: str
