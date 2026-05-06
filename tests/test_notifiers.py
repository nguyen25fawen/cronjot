"""Tests for email and Slack notifiers (using mocks)."""

import json
from unittest.mock import patch, MagicMock
import pytest
from cronjot.notifiers import send_email, send_slack


@patch("cronjot.notifiers.smtplib.SMTP")
def test_send_email_basic(mock_smtp_cls):
    mock_server = MagicMock()
    mock_smtp_cls.return_value.__enter__.return_value = mock_server

    send_email(
        subject="Test Digest",
        body="All good.",
        to_address="ops@example.com",
        from_address="cronjot@example.com",
    )

    mock_server.sendmail.assert_called_once()
    args = mock_server.sendmail.call_args[0]
    assert args[0] == "cronjot@example.com"
    assert args[1] == ["ops@example.com"]


@patch("cronjot.notifiers.smtplib.SMTP")
def test_send_email_with_tls_and_auth(mock_smtp_cls):
    mock_server = MagicMock()
    mock_smtp_cls.return_value.__enter__.return_value = mock_server

    send_email(
        subject="Digest",
        body="body",
        to_address="a@b.com",
        from_address="c@d.com",
        username="user",
        password="pass",
        use_tls=True,
    )

    mock_server.starttls.assert_called_once()
    mock_server.login.assert_called_once_with("user", "pass")


@patch("cronjot.notifiers.urllib.request.urlopen")
def test_send_slack_success(mock_urlopen):
    mock_resp = MagicMock()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    mock_resp.status = 200
    mock_urlopen.return_value = mock_resp

    send_slack(webhook_url="https://hooks.slack.com/test", text="Hello from CronJot")

    mock_urlopen.assert_called_once()
    req = mock_urlopen.call_args[0][0]
    payload = json.loads(req.data.decode())
    assert payload["text"] == "Hello from CronJot"
    assert payload["username"] == "CronJot"


@patch("cronjot.notifiers.urllib.request.urlopen")
def test_send_slack_non_200_raises(mock_urlopen):
    mock_resp = MagicMock()
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    mock_resp.status = 500
    mock_urlopen.return_value = mock_resp

    with pytest.raises(RuntimeError, match="HTTP 500"):
        send_slack(webhook_url="https://hooks.slack.com/test", text="oops")
