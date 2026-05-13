"""Rate limiting for cron jobs — prevents a job from running more than N times
within a rolling time window.
"""

import sqlite3
import time
from typing import Optional


def init_rate_limit_schema(conn: sqlite3.Connection) -> None:
    """Create the rate_limits table if it does not exist."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS rate_limits (
            job_name  TEXT PRIMARY KEY,
            max_runs  INTEGER NOT NULL,
            window_seconds INTEGER NOT NULL
        )
        """
    )
    conn.commit()


def set_rate_limit(conn: sqlite3.Connection, job_name: str, max_runs: int, window_seconds: int) -> None:
    """Insert or replace the rate limit configuration for a job."""
    if max_runs < 1:
        raise ValueError("max_runs must be at least 1")
    if window_seconds < 1:
        raise ValueError("window_seconds must be at least 1")
    conn.execute(
        """
        INSERT INTO rate_limits (job_name, max_runs, window_seconds)
        VALUES (?, ?, ?)
        ON CONFLICT(job_name) DO UPDATE SET
            max_runs = excluded.max_runs,
            window_seconds = excluded.window_seconds
        """,
        (job_name, max_runs, window_seconds),
    )
    conn.commit()


def remove_rate_limit(conn: sqlite3.Connection, job_name: str) -> bool:
    """Remove the rate limit for a job. Returns True if a row was deleted."""
    cursor = conn.execute("DELETE FROM rate_limits WHERE job_name = ?", (job_name,))
    conn.commit()
    return cursor.rowcount > 0


def get_rate_limit(conn: sqlite3.Connection, job_name: str) -> Optional[dict]:
    """Return the rate limit config for a job, or None if not configured."""
    row = conn.execute(
        "SELECT job_name, max_runs, window_seconds FROM rate_limits WHERE job_name = ?",
        (job_name,),
    ).fetchone()
    if row is None:
        return None
    return {"job_name": row[0], "max_runs": row[1], "window_seconds": row[2]}


def is_rate_limited(conn: sqlite3.Connection, job_name: str) -> bool:
    """Return True if the job has exceeded its allowed runs in the rolling window."""
    config = get_rate_limit(conn, job_name)
    if config is None:
        return False

    since = time.time() - config["window_seconds"]
    row = conn.execute(
        """
        SELECT COUNT(*) FROM runs
        WHERE job_name = ? AND started_at >= ?
        """,
        (job_name, since),
    ).fetchone()
    run_count = row[0] if row else 0
    return run_count >= config["max_runs"]


def list_rate_limits(conn: sqlite3.Connection) -> list:
    """Return all configured rate limits."""
    rows = conn.execute(
        "SELECT job_name, max_runs, window_seconds FROM rate_limits ORDER BY job_name"
    ).fetchall()
    return [{"job_name": r[0], "max_runs": r[1], "window_seconds": r[2]} for r in rows]
