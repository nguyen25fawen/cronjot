"""Tests for cronjot.webhooks."""

import json
import urllib.error
from io import BytesIO
from unittest.mock import MagicMock, patch

import pytest

from cronjot.webhooks import build_run_payload, send_webhook


SAMPLE_RUN = {
    "job_name": "backup",
    "started_at": "2024-01-15T02:00:00",
    "duration_seconds": 12.4,
    "exit_code": 0,
    "output": "done",
}


def _mock_response(status: int = 200) -> MagicMock:
    resp = MagicMock()
    resp.status = status
    resp.__enter__ = lambda s: s
    resp.__exit__ = MagicMock(return_value=False)
    return resp


def test_build_run_payload_success():
    payload = build_run_payload(SAMPLE_RUN)
    assert payload["event"] == "run_completed"
    assert payload["status"] == "success"
    assert payload["job_name"] == "backup"
    assert payload["exit_code"] == 0


def test_build_run_payload_failure():
    run = {**SAMPLE_RUN, "exit_code": 1}
    payload = build_run_payload(run)
    assert payload["status"] == "failure"


def test_send_webhook_posts_json():
    with patch("urllib.request.urlopen", return_value=_mock_response(200)) as mock_open:
        send_webhook("http://example.com/hook", {"key": "value"})
    mock_open.assert_called_once()
    req = mock_open.call_args[0][0]
    assert req.get_header("Content-type") == "application/json"
    assert json.loads(req.data) == {"key": "value"}


def test_send_webhook_attaches_secret():
    with patch("urllib.request.urlopen", return_value=_mock_response(200)) as mock_open:
        send_webhook("http://example.com/hook", {}, secret="mysecret")
    req = mock_open.call_args[0][0]
    assert req.get_header("X-cronjot-secret") == "mysecret"


def test_send_webhook_http_error_raises():
    err = urllib.error.HTTPError("http://x", 500, "Internal Server Error", {}, BytesIO())
    with patch("urllib.request.urlopen", side_effect=err):
        with pytest.raises(RuntimeError, match="HTTP 500"):
            send_webhook("http://x", {})


def test_send_webhook_url_error_raises():
    err = urllib.error.URLError("connection refused")
    with patch("urllib.request.urlopen", side_effect=err):
        with pytest.raises(RuntimeError, match="connection refused"):
            send_webhook("http://x", {})


def test_send_webhook_non_2xx_raises():
    with patch("urllib.request.urlopen", return_value=_mock_response(404)):
        with pytest.raises(RuntimeError, match="404"):
            send_webhook("http://x", {})
