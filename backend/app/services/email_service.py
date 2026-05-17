"""Async email service via aiosmtplib + Mailtrap sandbox."""
from __future__ import annotations

import logging
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Optional

import aiosmtplib

from app.config import Settings, get_settings

logger = logging.getLogger("email_service")


class EmailService:

    def __init__(self, settings: Optional[Settings] = None):
        s = settings or get_settings()
        self.smtp_host = s.smtp_host
        self.smtp_port = s.smtp_port
        self.smtp_user = s.smtp_username
        self.smtp_password = s.smtp_password
        self.smtp_from = s.smtp_from_email
        self.smtp_from_name = s.smtp_from_name

    def _build_message(
        self,
        to: str,
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
        attachments: Optional[list[str]] = None,
    ) -> MIMEMultipart:
        msg = MIMEMultipart("mixed")
        msg["Subject"] = subject
        msg["From"] = f"{self.smtp_from_name} <{self.smtp_from}>"
        msg["To"] = to

        alt = MIMEMultipart("alternative")
        alt.attach(MIMEText(body_text, "plain", "utf-8"))
        if body_html:
            alt.attach(MIMEText(body_html, "html", "utf-8"))
        msg.attach(alt)

        for path_str in (attachments or []):
            path = Path(path_str)
            if path.exists():
                with path.open("rb") as f:
                    part = MIMEApplication(f.read(), Name=path.name)
                part["Content-Disposition"] = f'attachment; filename="{path.name}"'
                msg.attach(part)
            else:
                logger.warning("Attachment not found: %s", path_str)

        return msg

    async def send_email(
        self,
        to: str,
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
        attachments: Optional[list[str]] = None,
    ) -> bool:
        msg = self._build_message(to, subject, body_text, body_html, attachments)
        try:
            await aiosmtplib.send(
                msg,
                hostname=self.smtp_host,
                port=self.smtp_port,
                username=self.smtp_user,
                password=self.smtp_password,
                start_tls=True,
            )
            logger.info("Email sent to %s: %s", to, subject)
            return True
        except Exception as exc:
            logger.error("Failed to send email to %s: %s", to, exc)
            return False

    async def send_bulk(
        self,
        recipients: list[str],
        subject: str,
        body_text: str,
        body_html: Optional[str] = None,
        attachments: Optional[list[str]] = None,
    ) -> dict:
        sent, failed, errors = 0, 0, []
        for addr in recipients:
            ok = await self.send_email(addr, subject, body_text, body_html, attachments)
            if ok:
                sent += 1
            else:
                failed += 1
                errors.append(addr)
        return {"sent": sent, "failed": failed, "errors": errors}


email_service = EmailService()
