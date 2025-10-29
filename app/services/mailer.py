from __future__ import annotations

import asyncio
from email.message import EmailMessage
from email.utils import parseaddr, formataddr

from app.core.config import settings
from app.core.exceptions import BadRequest, ServiceUnavailable
from app.core.logging import get_logger
from pydantic import BaseModel, Field


async def send_mail(to: str, subject: str, html: str) -> None:
    host, port = settings.SMTP_HOST, settings.SMTP_PORT
    username, password = settings.SMTP_USERNAME, settings.SMTP_PASSWORD
    if not host or not port or not settings.MAIL_FROM:
        raise BadRequest("Mail service not configured")

    msg = EmailMessage()
    display = settings.MAIL_FROM or ""
    name, addr = parseaddr(display)
    sender_addr = (settings.SMTP_USERNAME or addr) or ""
    header_from = formataddr((name or sender_addr, sender_addr))
    msg["From"] = header_from
    msg["To"] = to
    msg["Subject"] = subject
    msg.set_content(html, subtype="html")

    class MailMeta(BaseModel):
        host: str
        port: int
        start_tls: bool
        use_tls: bool
        to: str
        from_: str = Field(serialization_alias="from")

    logger = get_logger(__name__)

    async def _send() -> None:
        import aiosmtplib

        use_tls = (not settings.SMTP_STARTTLS) and int(port) == 465
        meta = MailMeta(
            host=host,
            port=int(port),
            start_tls=bool(settings.SMTP_STARTTLS),
            use_tls=use_tls,
            to=to,
            from_=header_from,
        )
        logger.info("mail_sending", extra={"meta": meta.model_dump()})
        await aiosmtplib.send(
            msg,
            hostname=host,
            port=port,
            username=username,
            password=password,
            start_tls=(settings.SMTP_STARTTLS and not use_tls),
            use_tls=use_tls,
            sender=sender_addr,
            recipients=[to],
        )
        logger.info("mail_sent", extra={"meta": meta.model_dump()})

    try:
        await asyncio.wait_for(_send(), timeout=10)
    except Exception as e:
        logger.exception("mail_failed: %s", str(e))
        raise ServiceUnavailable("Failed to send email") from e
