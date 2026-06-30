"""Send login codes by email.

Two modes (settings.email_mode):
- "console" (dev): logs the code; no mail server needed. The API also returns
  the code in the response when ENV=local so the flow is testable end-to-end.
- "smtp": real email via SMTP (fill in SMTP_* in .env).
"""

from __future__ import annotations

import asyncio
from email.message import EmailMessage

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


def _build_message(to_email: str, code: str) -> EmailMessage:
    msg = EmailMessage()
    msg["Subject"] = "Your Certo verification code"
    msg["From"] = settings.email_from
    msg["To"] = to_email
    msg.set_content(
        f"Your Certo verification code is: {code}\n\n"
        f"It expires in {settings.code_ttl_minutes} minutes. "
        "If you didn't request this, you can ignore this email."
    )
    return msg


def _send_smtp(to_email: str, code: str) -> None:
    import smtplib

    msg = _build_message(to_email, code)
    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=15) as server:
        if settings.smtp_tls:
            server.starttls()
        if settings.smtp_user:
            server.login(settings.smtp_user, settings.smtp_password or "")
        server.send_message(msg)


async def send_login_code(to_email: str, code: str) -> None:
    if settings.email_mode == "smtp" and settings.smtp_host:
        await asyncio.to_thread(_send_smtp, to_email, code)
        logger.info("email.sent_smtp", to=to_email)
    else:
        # Dev mode: surface the code in logs so it can be used without a mail server.
        logger.info("email.console_code", to=to_email, code=code)
