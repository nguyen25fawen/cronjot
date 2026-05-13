"""Job throttling: prevent a job from running more frequently than allowed."""

import sqlite3
from datetime import datetime, timedelta
from typing import Optional

from .storage import get_connection


def init_throttle_schema(conn: sqlite3.Connection) -> None:
    """Create the job_throttles table if it does not exist."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS job_throttles (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            job_name    TEXT    NOT NULL UNIQUE,
            min_interval_seconds INTEGER NOT NULL,
            created_at  TEXT    NOT NULL,
            updated_at  TEXT    NOT NULL
        )
        """
    )
    conn.commit()


def set_throttle(conn: sqlite3.Connection, job_name: str, min_interval_seconds: int) -> None:
    """Insert or update the minimum interval for a job."""
    now = datetime.utcnow().isoformat()
    conn.execute(
        """
        INSERT INTO job_throttles (job_name, min_interval_seconds, created_at, updated_at)
        VALUES (?, ?, ?, ?)
        ON CONFLICT(job_name) DO UPDATE SET
            min_interval_seconds = excluded.min_interval_seconds,
            updated_at = excluded.updated_at
        """,
        (job_name, min_interval_seconds, now, now),
    )
    conn.commit()


def remove_throttle(conn: sqlite3.Connection, job_name: str) -> bool:
    """Remove throttle rule for a job. Returns True if a row was deleted."""
    cur = conn.execute(
        "DELETE FROM job_throttles WHERE job_name = ?", (job_name,)
    )
    conn.commit()
    return cur.rowcount > 0


def get_throttle(conn: sqlite3.Connection, job_name: str) -> Optional[int]:
    """Return min_interval_seconds for a job, or None if not set."""
    row = conn.execute(
        "SELECT min_interval_seconds FROM job_throttles WHERE job_name = ?",
        (job_name,),
    ).fetchone()
    return row[0] if row else None


def is_throttled(conn: sqlite3.Connection, job_name: str) -> bool:
    """Return True if the job ran too recently and should be skipped."""
    min_interval = get_throttle(conn, job_name)
    if min_interval is None:
        return False

    row = conn.execute(
        """
        SELECT started_at FROM runs
        WHERE job_name = ?
        ORDER BY started_at DESC
        LIMIT 1
        """,
        (job_name,),
    ).fetchone()

    if row is None:
        return False

    last_run = datetime.fromisoformat(row[0])
    elapsed = (datetime.utcnow() - last_run).total_seconds()
    return elapsed < min_interval


def list_throttles(conn: sqlite3.Connection) -> list:
    """Return all throttle rules as a list of dicts."""
    rows = conn.execute(
        "SELECT job_name, min_interval_seconds, created_at, updated_at FROM job_throttles ORDER BY job_name"
    ).fetchall()
    return [
        {"job_name": r[0], "min_interval_seconds": r[1], "created_at": r[2], "updated_at": r[3]}
        for r in rows
    ]
