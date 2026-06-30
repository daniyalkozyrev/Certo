"""Authentication: passwordless email codes + optional Google OAuth."""

from __future__ import annotations

import urllib.parse
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select

from app.api.deps import CurrentUser, SessionDep
from app.core.config import settings
from app.core.exceptions import ExternalServiceError, ValidationError
from app.core.logging import get_logger
from app.core.security import (
    create_access_token,
    generate_code,
    hash_code,
    verify_code,
)
from app.models.user import LoginCode, User
from app.schemas.auth import (
    AuthConfigOut,
    RequestCodeIn,
    RequestCodeOut,
    TokenOut,
    UserRead,
    VerifyCodeIn,
)
from app.services.email.sender import send_login_code

logger = get_logger(__name__)
router = APIRouter(prefix="/auth", tags=["auth"])


async def _get_or_create_user(session: SessionDep, email: str, provider: str) -> User:
    user = await session.scalar(select(User).where(User.email == email))
    if user is None:
        user = User(email=email, auth_provider=provider)
        session.add(user)
        await session.flush()
    return user


@router.get("/config", response_model=AuthConfigOut)
async def auth_config() -> AuthConfigOut:
    return AuthConfigOut(google_enabled=settings.google_enabled, email_mode=settings.email_mode)


@router.post("/request-code", response_model=RequestCodeOut)
async def request_code(payload: RequestCodeIn, session: SessionDep) -> RequestCodeOut:
    email = payload.email.lower()
    code = generate_code()
    session.add(
        LoginCode(
            email=email,
            code_hash=hash_code(code),
            expires_at=datetime.now(timezone.utc)
            + timedelta(minutes=settings.code_ttl_minutes),
        )
    )
    await session.commit()
    await send_login_code(email, code)
    return RequestCodeOut(sent=True, dev_code=code if settings.expose_dev_code else None)


@router.post("/verify", response_model=TokenOut)
async def verify(payload: VerifyCodeIn, session: SessionDep) -> TokenOut:
    email = payload.email.lower()
    row = await session.scalar(
        select(LoginCode)
        .where(LoginCode.email == email, LoginCode.consumed.is_(False))
        .order_by(LoginCode.created_at.desc())
    )
    if row is not None:
        # SQLite returns naive datetimes; treat them as UTC for the comparison.
        expires = row.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)
    if row is None or expires < datetime.now(timezone.utc):
        raise ValidationError("Code expired or not found. Request a new one.")
    if not verify_code(payload.code.strip(), row.code_hash):
        raise ValidationError("Incorrect code.")

    row.consumed = True
    user = await _get_or_create_user(session, email, "email")
    await session.commit()

    token = create_access_token(user.id, user.email)
    return TokenOut(access_token=token, user=UserRead.model_validate(user))


@router.get("/me", response_model=UserRead)
async def me(user: CurrentUser) -> User:
    return user


# ── Google OAuth (optional) ──────────────────────────────────
_GOOGLE_AUTH = "https://accounts.google.com/o/oauth2/v2/auth"
_GOOGLE_TOKEN = "https://oauth2.googleapis.com/token"
_GOOGLE_USERINFO = "https://openidconnect.googleapis.com/v1/userinfo"


def _redirect_uri(request: Request) -> str:
    base = str(request.base_url).rstrip("/")
    return f"{base}{settings.api_prefix}/auth/google/callback"


@router.get("/google/authorize")
async def google_authorize(request: Request) -> RedirectResponse:
    if not settings.google_enabled:
        raise ValidationError("Google login is not configured.")
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": _redirect_uri(request),
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "online",
        "prompt": "select_account",
    }
    return RedirectResponse(f"{_GOOGLE_AUTH}?{urllib.parse.urlencode(params)}")


@router.get("/google/callback")
async def google_callback(request: Request, code: str, session: SessionDep) -> RedirectResponse:
    if not settings.google_enabled:
        raise ValidationError("Google login is not configured.")
    import httpx

    async with httpx.AsyncClient(timeout=15) as client:
        try:
            token_resp = await client.post(
                _GOOGLE_TOKEN,
                data={
                    "code": code,
                    "client_id": settings.google_client_id,
                    "client_secret": settings.google_client_secret,
                    "redirect_uri": _redirect_uri(request),
                    "grant_type": "authorization_code",
                },
            )
            token_resp.raise_for_status()
            access = token_resp.json()["access_token"]
            info = await client.get(
                _GOOGLE_USERINFO, headers={"Authorization": f"Bearer {access}"}
            )
            info.raise_for_status()
            data = info.json()
        except Exception as exc:
            logger.error("auth.google_error", error=str(exc))
            raise ExternalServiceError("Google sign-in failed.") from exc

    email = (data.get("email") or "").lower()
    if not email:
        raise ValidationError("Google account has no email.")
    user = await _get_or_create_user(session, email, "google")
    if data.get("name") and not user.name:
        user.name = data["name"]
    await session.commit()

    jwt_token = create_access_token(user.id, user.email)
    # Hand the token back to the SPA, which stores it and continues.
    return RedirectResponse(f"{settings.frontend_url}/login?token={jwt_token}")
