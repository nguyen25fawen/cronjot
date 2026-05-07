"""Alert rules: notify when a job fails N consecutive times or exceeds a duration threshold."""

from __future__ import annotations

from typing import Optional

from cronjot.storage import fetch_runs


def check_consecutive_failures(
    conn,
    job_name: str,
    threshold: int = 3,
) -> tuple[bool, int]:
    """Return (triggered, count) if the last `threshold` runs all failed."""
    runs = fetch_runs(conn, job_name=job_name, limit=threshold)
    if len(runs) < threshold:
        return False, len(runs)
    consecutive = sum(1 for r in runs if r["exit_code"] != 0)
    triggered = consecutive >= threshold
    return triggered, consecutive


def check_duration_exceeded(
    conn,
    job_name: str,
    max_seconds: float,
    limit: int = 1,
) -> tuple[bool, Optional[float]]:
    """Return (triggered, duration) if the most recent run exceeded max_seconds."""
    runs = fetch_runs(conn, job_name=job_name, limit=limit)
    if not runs:
        return False, None
    last = runs[0]
    duration: Optional[float] = last["duration"]
    if duration is None:
        return False, None
    return duration > max_seconds, duration


def evaluate_alerts(
    conn,
    job_name: str,
    consecutive_failure_threshold: int = 3,
    max_duration_seconds: Optional[float] = None,
) -> list[str]:
    """Evaluate all configured alert rules and return a list of alert messages."""
    messages: list[str] = []

    triggered, count = check_consecutive_failures(
        conn, job_name, threshold=consecutive_failure_threshold
    )
    if triggered:
        messages.append(
            f"Job '{job_name}' has failed {count} consecutive time(s) "
            f"(threshold: {consecutive_failure_threshold})."
        )

    if max_duration_seconds is not None:
        exceeded, duration = check_duration_exceeded(
            conn, job_name, max_seconds=max_duration_seconds
        )
        if exceeded:
            messages.append(
                f"Job '{job_name}' last run took {duration:.2f}s, "
                f"exceeding limit of {max_duration_seconds:.2f}s."
            )

    return messages
