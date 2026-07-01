"""Send login/verification codes by email.

Delivery modes (settings.email_mode):
- "console" (dev): logs the code; no mail server. In local mode the API also
  returns the code so the flow is testable without email.
- "smtp": classic SMTP. NOTE: many PaaS (incl. Railway) block outbound SMTP,
  so this fails there with "Network is unreachable".
- "brevo" / "sendgrid" / "resend": transactional email HTTP APIs over :443 —
  these work on Railway. Set the matching *_API_KEY and a verified EMAIL_FROM.
"""

from __future__ import annotations

import asyncio
from email.message import EmailMessage
from email.utils import parseaddr

from app.core.config import settings
from app.core.exceptions import ExternalServiceError
from app.core.logging import get_logger

logger = get_logger(__name__)

_SUBJECT = "Your Certo verification code"


def _body(code: str) -> str:
    return (
        f"Your Certo verification code is: {code}\n\n"
        f"It expires in {settings.code_ttl_minutes} minutes. "
        "If you didn't request this, you can ignore this email."
    )


def _from_parts() -> tuple[str, str]:
    """(name, email) parsed from EMAIL_FROM, e.g. 'Certo <x@gmail.com>'."""
    name, addr = parseaddr(settings.email_from)
    return (name or "Certo"), addr


# ── SMTP (may be blocked on PaaS) ────────────────────────────────────────────
def _send_smtp(to_email: str, code: str) -> None:
    import smtplib

    msg = EmailMessage()
    msg["Subject"] = _SUBJECT
    msg["From"] = settings.email_from
    msg["To"] = to_email
    msg.set_content(_body(code))
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as server:
        if settings.smtp_tls:
            server.starttls()
        if settings.smtp_user:
            server.login(settings.smtp_user, settings.smtp_password or "")
        server.send_message(msg)


# ── HTTP email APIs (work over :443, so fine on Railway) ─────────────────────
async def _send_http(to_email: str, code: str) -> None:
    import httpx

    name, from_addr = _from_parts()
    mode = settings.email_mode
    if mode == "brevo":
        url = "https://api.brevo.com/v3/smtp/email"
        headers = {"api-key": settings.brevo_api_key or "", "content-type": "application/json"}
        payload = {
            "sender": {"email": from_addr, "name": name},
            "to": [{"email": to_email}],
            "subject": _SUBJECT,
            "textContent": _body(code),
        }
    elif mode == "sendgrid":
        url = "https://api.sendgrid.com/v3/mail/send"
        headers = {
            "Authorization": f"Bearer {settings.sendgrid_api_key or ''}",
            "content-type": "application/json",
        }
        payload = {
            "personalizations": [{"to": [{"email": to_email}]}],
            "from": {"email": from_addr, "name": name},
            "subject": _SUBJECT,
            "content": [{"type": "text/plain", "value": _body(code)}],
        }
    elif mode == "resend":
        url = "https://api.resend.com/emails"
        headers = {
            "Authorization": f"Bearer {settings.resend_api_key or ''}",
            "content-type": "application/json",
        }
        payload = {
            "from": f"{name} <{from_addr}>",
            "to": [to_email],
            "subject": _SUBJECT,
            "text": _body(code),
        }
    else:  # pragma: no cover - guarded by caller
        raise ExternalServiceError(f"Unsupported email_mode: {mode}")

    async with httpx.AsyncClient(timeout=20) as client:
        resp = await client.post(url, headers=headers, json=payload)
    if resp.status_code >= 300:
        logger.error("email.http_error", provider=mode, status=resp.status_code, body=resp.text[:300])
        raise ExternalServiceError("Could not send the verification email. Please try again shortly.")


async def send_login_code(to_email: str, code: str) -> None:
    mode = settings.email_mode
    if mode in ("brevo", "sendgrid", "resend"):
        await _send_http(to_email, code)
        logger.info("email.sent_http", provider=mode, to=to_email)
    elif mode == "smtp" and settings.smtp_host:
        try:
            await asyncio.to_thread(_send_smtp, to_email, code)
        except Exception as exc:
            logger.error("email.smtp_error", to=to_email, error=str(exc))
            raise ExternalServiceError(
                "Could not send the verification email. Please try again shortly."
            ) from exc
        logger.info("email.sent_smtp", to=to_email)
    else:
        # Dev mode: surface the code in logs so it can be used without a mail server.
        logger.info("email.console_code", to=to_email, code=code)
