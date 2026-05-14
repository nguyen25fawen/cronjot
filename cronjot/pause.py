"""Pause/resume support for cron jobs — prevents scheduled runs while paused."""

import sqlite3
from datetime import datetime, timezone
from typing import Optional


def init_pause_schema(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS job_pauses (
            job_name  TEXT PRIMARY KEY,
            paused_at TEXT NOT NULL,
            reason    TEXT
        )
    """)
    conn.commit()


def pause_job(conn: sqlite3.Connection, job_name: str, reason: Optional[str] = None) -> None:
    """Mark a job as paused. Idempotent — updates reason if already paused."""
    now = datetime.now(timezone.utc).isoformat()
    conn.execute(
        """
        INSERT INTO job_pauses (job_name, paused_at, reason)
        VALUES (?, ?, ?)
        ON CONFLICT(job_name) DO UPDATE SET paused_at = excluded.paused_at,
                                            reason    = excluded.reason
        """,
        (job_name, now, reason),
    )
    conn.commit()


def resume_job(conn: sqlite3.Connection, job_name: str) -> bool:
    """Remove the pause for a job. Returns True if a row was deleted."""
    cur = conn.execute("DELETE FROM job_pauses WHERE job_name = ?", (job_name,))
    conn.commit()
    return cur.rowcount > 0


def is_paused(conn: sqlite3.Connection, job_name: str) -> bool:
    """Return True if the job is currently paused."""
    cur = conn.execute(
        "SELECT 1 FROM job_pauses WHERE job_name = ?", (job_name,)
    )
    return cur.fetchone() is not None


def list_paused_jobs(conn: sqlite3.Connection) -> list[dict]:
    """Return all paused jobs as a list of dicts."""
    cur = conn.execute(
        "SELECT job_name, paused_at, reason FROM job_pauses ORDER BY paused_at"
    )
    rows = cur.fetchall()
    return [
        {"job_name": r[0], "paused_at": r[1], "reason": r[2]}
        for r in rows
    ]


def get_pause_info(conn: sqlite3.Connection, job_name: str) -> Optional[dict]:
    """Return pause details for a specific job, or None if not paused."""
    cur = conn.execute(
        "SELECT job_name, paused_at, reason FROM job_pauses WHERE job_name = ?",
        (job_name,),
    )
    row = cur.fetchone()
    if row is None:
        return None
    return {"job_name": row[0], "paused_at": row[1], "reason": row[2]}
