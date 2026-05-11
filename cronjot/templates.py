"""Notification template rendering for cronjot digest and alert messages."""

from datetime import datetime
from typing import Optional


DEFAULT_DIGEST_TEMPLATE = """
Cronjot Digest — {generated_at}
{'=' * 48}
{body}
{'=' * 48}
Total jobs tracked: {total_jobs} | Runs: {total_runs}
""".strip()

DEFAULT_RUN_TEMPLATE = (
    "[{status}] {job_name} | started: {started_at} | duration: {duration_s:.2f}s"
)

DEFAULT_ALERT_TEMPLATE = (
    "ALERT [{level}] {job_name}: {message}"
)


def render_digest(summary: dict, template: Optional[str] = None) -> str:
    """Render a digest summary dict into a human-readable string.

    Args:
        summary: dict with keys total_jobs, total_runs, generated_at, body.
        template: optional format string overriding the default.

    Returns:
        Rendered digest string.
    """
    tmpl = template or DEFAULT_DIGEST_TEMPLATE
    generated_at = summary.get("generated_at", datetime.utcnow().isoformat())
    body = summary.get("body", "")
    total_jobs = summary.get("total_jobs", 0)
    total_runs = summary.get("total_runs", 0)
    return tmpl.format(
        generated_at=generated_at,
        body=body,
        total_jobs=total_jobs,
        total_runs=total_runs,
    )


def render_run_line(run: dict, template: Optional[str] = None) -> str:
    """Render a single run record into a one-line summary.

    Args:
        run: dict with keys status, job_name, started_at, duration_s.
        template: optional format string overriding the default.

    Returns:
        Rendered run line string.
    """
    tmpl = template or DEFAULT_RUN_TEMPLATE
    return tmpl.format(
        status=run.get("status", "unknown").upper(),
        job_name=run.get("job_name", ""),
        started_at=run.get("started_at", ""),
        duration_s=float(run.get("duration_s", 0.0)),
    )


def render_alert(alert: dict, template: Optional[str] = None) -> str:
    """Render an alert dict into a notification string.

    Args:
        alert: dict with keys level, job_name, message.
        template: optional format string overriding the default.

    Returns:
        Rendered alert string.
    """
    tmpl = template or DEFAULT_ALERT_TEMPLATE
    return tmpl.format(
        level=alert.get("level", "WARNING").upper(),
        job_name=alert.get("job_name", ""),
        message=alert.get("message", ""),
    )
