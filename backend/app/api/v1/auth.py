"""Authentication: passwordless email codes + optional Google OAuth."""

from __future__ import annotations

import urllib.parse
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select

from app.api.deps import CurrentUser, SessionDep
from app.core.config import settings
from app.core.exceptions import ExternalServiceError, ForbiddenError, ValidationError
from app.core.logging import get_logger
from app.core.security import (
    create_access_token,
    generate_code,
    hash_code,
    hash_password,
    verify_code,
    verify_password,
)
from app.models.user import LoginCode, User
from app.schemas.auth import (
    AuthConfigOut,
    LoginIn,
    RequestCodeIn,
    RequestCodeOut,
    SignupIn,
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


async def _issue_verification_code(session: SessionDep, email: str) -> str:
    """Create + email a fresh one-time code. Returns it (surfaced to the API only
    in local console mode)."""
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
    return code


@router.post("/signup", response_model=RequestCodeOut, status_code=201)
async def signup(payload: SignupIn, session: SessionDep) -> RequestCodeOut:
    """Create an email+password account and email a verification code. The account
    can't log in until the code is confirmed via /auth/verify."""
    email = payload.email.lower()
    user = await session.scalar(select(User).where(User.email == email))
    if user is not None and user.password_hash and user.email_verified:
        raise ValidationError("An account with this email already exists. Please log in.")
    if user is None:
        user = User(email=email, auth_provider="email")
        session.add(user)
    # (Re)set the password for a new or not-yet-verified account (lets a user who
    # never finished verification start over, and lets a legacy code-only user
    # claim a password).
    user.password_hash = hash_password(payload.password)
    user.email_verified = False
    if payload.name:
        user.name = payload.name
    await session.flush()

    code = await _issue_verification_code(session, email)
    return RequestCodeOut(sent=True, dev_code=code if settings.expose_dev_code else None)


@router.post("/login", response_model=TokenOut)
async def login(payload: LoginIn, session: SessionDep) -> TokenOut:
    email = payload.email.lower()
    user = await session.scalar(select(User).where(User.email == email))
    if user is None or not verify_password(payload.password, user.password_hash):
        raise ValidationError("Incorrect email or password.")
    if not user.email_verified:
        # Help them finish: send a fresh code and tell the client to verify.
        await _issue_verification_code(session, email)
        raise ForbiddenError("Please verify your email — we've sent you a new code.")
    token = create_access_token(user.id, user.email)
    return TokenOut(access_token=token, user=UserRead.model_validate(user))


@router.post("/request-code", response_model=RequestCodeOut)
async def request_code(payload: RequestCodeIn, session: SessionDep) -> RequestCodeOut:
    """Resend a verification code (used by the 'resend' button on the verify step)."""
    email = payload.email.lower()
    code = await _issue_verification_code(session, email)
    return RequestCodeOut(sent=True, dev_code=code if settings.expose_dev_code else None)


@router.post("/verify", response_model=TokenOut)
async def verify(payload: VerifyCodeIn, session: SessionDep) -> TokenOut:
    """Confirm the emailed code -> mark the email verified -> log the user in."""
    email = payload.email.lower()
    now = datetime.now(timezone.utc)
    # Accept ANY outstanding (unconsumed, unexpired) code — a user may have several
    # in flight (signup + a resend), and entering any valid one should work.
    rows = (
        await session.scalars(
            select(LoginCode)
            .where(LoginCode.email == email, LoginCode.consumed.is_(False))
            .order_by(LoginCode.created_at.desc())
        )
    ).all()
    submitted = payload.code.strip()

    def _valid(row: LoginCode) -> bool:
        expires = row.expires_at
        if expires.tzinfo is None:  # SQLite returns naive datetimes -> treat as UTC
            expires = expires.replace(tzinfo=timezone.utc)
        return expires >= now and verify_code(submitted, row.code_hash)

    match = next((r for r in rows if _valid(r)), None)
    if match is None:
        # Distinguish "no code at all" from "wrong/expired code" for a clearer message.
        raise ValidationError(
            "Incorrect code." if rows else "Code expired or not found. Request a new one."
        )
    match.consumed = True
    user = await _get_or_create_user(session, email, "email")
    user.email_verified = True
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
