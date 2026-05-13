"""Dead-letter queue: capture and inspect jobs that have exceeded a
maximum consecutive-failure threshold so they can be reviewed and
requed or suppressed without spamming the normal alert channel."""

import sqlite3
import time
from typing import Optional


def init_deadletter_schema(conn: sqlite3.Connection) -> None:
    """Create the dead_letter_jobs table if it does not already exist."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS dead_letter_jobs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            job_name    TEXT    NOT NULL,
            queued_at   REAL    NOT NULL,
            reason      TEXT    NOT NULL,
            resolved    INTEGER NOT NULL DEFAULT 0,
            resolved_at REAL
        )
        """
    )
    conn.commit()


def enqueue_dead_letter(
    conn: sqlite3.Connection,
    job_name: str,
    reason: str,
) -> int:
    """Add *job_name* to the dead-letter queue and return the new row id.

    If the job is already present and unresolved, the existing entry is
    returned unchanged (idempotent).
    """
    existing = conn.execute(
        "SELECT id FROM dead_letter_jobs WHERE job_name = ? AND resolved = 0",
        (job_name,),
    ).fetchone()
    if existing:
        return existing[0]

    cur = conn.execute(
        "INSERT INTO dead_letter_jobs (job_name, queued_at, reason) VALUES (?, ?, ?)",
        (job_name, time.time(), reason),
    )
    conn.commit()
    return cur.lastrowid


def resolve_dead_letter(conn: sqlite3.Connection, job_name: str) -> bool:
    """Mark the unresolved dead-letter entry for *job_name* as resolved.

    Returns True if a row was updated, False if none was found.
    """
    cur = conn.execute(
        """
        UPDATE dead_letter_jobs
           SET resolved = 1, resolved_at = ?
         WHERE job_name = ? AND resolved = 0
        """,
        (time.time(), job_name),
    )
    conn.commit()
    return cur.rowcount > 0


def list_dead_letters(
    conn: sqlite3.Connection,
    include_resolved: bool = False,
) -> list[dict]:
    """Return dead-letter entries as a list of dicts."""
    sql = "SELECT id, job_name, queued_at, reason, resolved, resolved_at FROM dead_letter_jobs"
    if not include_resolved:
        sql += " WHERE resolved = 0"
    sql += " ORDER BY queued_at DESC"
    rows = conn.execute(sql).fetchall()
    keys = ("id", "job_name", "queued_at", "reason", "resolved", "resolved_at")
    return [dict(zip(keys, row)) for row in rows]


def is_dead_lettered(conn: sqlite3.Connection, job_name: str) -> bool:
    """Return True if *job_name* has an unresolved dead-letter entry."""
    row = conn.execute(
        "SELECT 1 FROM dead_letter_jobs WHERE job_name = ? AND resolved = 0",
        (job_name,),
    ).fetchone()
    return row is not None
