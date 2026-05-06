"""Notification backends: email and Slack."""

import smtplib
import urllib.request
import urllib.error
import json
from email.mime.text import MIMEText
from typing import Optional


def send_email(
    subject: str,
    body: str,
    to_address: str,
    from_address: str,
    smtp_host: str = "localhost",
    smtp_port: int = 25,
    username: Optional[str] = None,
    password: Optional[str] = None,
    use_tls: bool = False,
) -> None:
    """Send a plain-text email digest."""
    msg = MIMEText(body, "plain")
    msg["Subject"] = subject
    msg["From"] = from_address
    msg["To"] = to_address

    with smtplib.SMTP(smtp_host, smtp_port) as server:
        if use_tls:
            server.starttls()
        if username and password:
            server.login(username, password)
        server.sendmail(from_address, [to_address], msg.as_string())


def send_slack(
    webhook_url: str,
    text: str,
    username: str = "CronJot",
    icon_emoji: str = ":alarm_clock:",
) -> None:
    """Send a digest message to a Slack incoming webhook."""
    payload = json.dumps(
        {"text": text, "username": username, "icon_emoji": icon_emoji}
    ).encode("utf-8")

    req = urllib.request.Request(
        webhook_url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            if resp.status != 200:
                raise RuntimeError(f"Slack webhook returned HTTP {resp.status}")
    except urllib.error.HTTPError as exc:
        raise RuntimeError(f"Slack webhook error: {exc.code} {exc.reason}") from exc
