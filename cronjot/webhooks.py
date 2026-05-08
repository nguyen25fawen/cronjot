"""Webhook notifier for cronjot — sends run summaries to arbitrary HTTP endpoints."""

import json
import urllib.request
import urllib.error
from typing import Optional, Dict, Any


def send_webhook(
    url: str,
    payload: Dict[str, Any],
    secret: Optional[str] = None,
    timeout: int = 10,
) -> None:
    """POST *payload* as JSON to *url*.

    If *secret* is provided it is sent as the ``X-Cronjot-Secret`` header so
    the receiving end can verify the request origin.

    Raises ``RuntimeError`` on non-2xx responses or network errors.
    """
    body = json.dumps(payload).encode()
    headers = {"Content-Type": "application/json"}
    if secret:
        headers["X-Cronjot-Secret"] = secret

    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status = resp.status
    except urllib.error.HTTPError as exc:
        raise RuntimeError(
            f"Webhook POST to {url!r} failed with HTTP {exc.code}: {exc.reason}"
        ) from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(
            f"Webhook POST to {url!r} failed: {exc.reason}"
        ) from exc

    if not (200 <= status < 300):
        raise RuntimeError(
            f"Webhook POST to {url!r} returned unexpected status {status}"
        )


def build_run_payload(run: Dict[str, Any]) -> Dict[str, Any]:
    """Convert a run row (as returned by ``fetch_runs``) to a webhook payload."""
    return {
        "event": "run_completed",
        "job_name": run.get("job_name"),
        "started_at": run.get("started_at"),
        "duration_seconds": run.get("duration_seconds"),
        "exit_code": run.get("exit_code"),
        "status": "success" if run.get("exit_code") == 0 else "failure",
        "output": run.get("output"),
    }
