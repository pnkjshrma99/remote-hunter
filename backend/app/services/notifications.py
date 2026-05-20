import logging
import smtplib
from email.message import EmailMessage
from typing import Iterable

import httpx

from app.config import get_settings
from app.models.job import Job

logger = logging.getLogger(__name__)
settings = get_settings()


def _format_jobs(jobs: Iterable[Job]) -> str:
    lines = []
    for job in jobs:
        lines.append(
            f"- {job.title} at {job.company} ({job.location or 'Remote'})\n"
            f"  Stack: {job.tech_stack or 'Unknown'}\n"
            f"  Apply: {job.url}"
        )
    return "\n".join(lines)


def send_email_alert(jobs: list[Job]) -> None:
    if not jobs or not settings.alert_email_to or not settings.smtp_host:
        return

    message = EmailMessage()
    message["Subject"] = f"{len(jobs)} new remote junior DevOps/SRE jobs"
    message["From"] = settings.smtp_from or settings.smtp_user
    message["To"] = settings.alert_email_to
    message.set_content(
        "Fresh matches for global remote roles open to India:\n\n"
        + _format_jobs(jobs)
    )

    with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as server:
        server.starttls()
        if settings.smtp_user and settings.smtp_password:
            server.login(settings.smtp_user, settings.smtp_password)
        server.send_message(message)


def send_slack_alert(jobs: list[Job]) -> None:
    if not jobs or not settings.slack_webhook_url:
        return

    text = "*Fresh remote junior DevOps/SRE matches open to India:*\n" + _format_jobs(jobs)
    with httpx.Client(timeout=20) as client:
        response = client.post(settings.slack_webhook_url, json={"text": text})
        response.raise_for_status()


def notify_new_jobs(jobs: list[Job]) -> None:
    if not jobs or not settings.alerts_enabled:
        return

    try:
        send_email_alert(jobs)
    except Exception as exc:
        logger.warning("Email alert failed: %s", exc)

    try:
        send_slack_alert(jobs)
    except Exception as exc:
        logger.warning("Slack alert failed: %s", exc)
