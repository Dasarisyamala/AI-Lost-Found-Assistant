from __future__ import annotations

import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from backend.config import settings


logger = logging.getLogger(__name__)


def _build_image_url(image_path: str | None) -> str | None:
    if not image_path:
        return None
    return f"{settings.backend_public_url}/uploads/{image_path}"


def send_match_notification(lost_item, found_item, match) -> None:
    if not settings.smtp_host or not settings.smtp_sender:
        logger.info("SMTP is not configured; skipping match notification for match %s", match.id)
        return

    recipient = lost_item.user.email
    subject = "AI Lost & Found: possible match found"
    lost_image = _build_image_url(lost_item.image_path)
    found_image = _build_image_url(found_item.image_path)
    match_url = f"{settings.frontend_url}/matches/{match.id}"

    html = f"""
    <html>
      <body style="font-family: Arial, sans-serif; color: #111827; line-height: 1.5;">
        <h2>Possible match found for your lost item</h2>
        <p><strong>Lost item:</strong> {lost_item.item_name}</p>
        <p><strong>Category:</strong> {lost_item.category}</p>
        <p><strong>Description:</strong> {lost_item.description}</p>
        <p><strong>Location lost:</strong> {lost_item.location}</p>
        <p><strong>Matched found item:</strong> {found_item.description}</p>
        <p><strong>Found location:</strong> {found_item.location}</p>
        <p><strong>Collection point:</strong> {settings.collection_point_info}</p>
        <p><strong>Confidence:</strong> {match.final_score:.2f}</p>
        <p><a href="{match_url}">Review the match in your dashboard</a></p>
        {f'<p>Lost item image: <a href="{lost_image}">{lost_image}</a></p>' if lost_image else ''}
        {f'<p>Found item image: <a href="{found_image}">{found_image}</a></p>' if found_image else ''}
      </body>
    </html>
    """

    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = settings.smtp_sender
    message["To"] = recipient
    message.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP(settings.smtp_host, settings.smtp_port, timeout=20) as server:
            server.starttls()
            if settings.smtp_username and settings.smtp_password:
                server.login(settings.smtp_username, settings.smtp_password)
            server.sendmail(settings.smtp_sender, [recipient], message.as_string())
    except Exception as exc:  # pragma: no cover - network dependent
        logger.exception("Failed to send match notification: %s", exc)

