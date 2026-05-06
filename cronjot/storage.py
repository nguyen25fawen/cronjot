"""SQLite-backed storage for cron job run history."""

import sqlite3
import os
from datetime import datetime
from typing import Optional

DEFAULT_DB_PATH = os.path.expanduser("~/.cronjot/history.db")


def get_connection(db_path: str = DEFAULT_DB_PATH) -> sqlite3.Connection:
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str = DEFAULT_DB_PATH) -> None:
    """Create tables if they don't exist."""
    with get_connection(db_path) as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS job_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                job_name TEXT NOT NULL,
                started_at TEXT NOT NULL,
                finished_at TEXT,
                exit_code INTEGER,
                output TEXT,
                error TEXT,
                duration_seconds REAL
            )
        """)
        conn.commit()


def insert_run(
    job_name: str,
    started_at: datetime,
    finished_at: Optional[datetime],
    exit_code: Optional[int],
    output: Optional[str],
    error: Optional[str],
    db_path: str = DEFAULT_DB_PATH,
) -> int:
    """Insert a job run record and return its ID."""
    duration = None
    if finished_at and started_at:
        duration = (finished_at - started_at).total_seconds()

    with get_connection(db_path) as conn:
        cursor = conn.execute(
            """
            INSERT INTO job_runs
                (job_name, started_at, finished_at, exit_code, output, error, duration_seconds)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                job_name,
                started_at.isoformat(),
                finished_at.isoformat() if finished_at else None,
                exit_code,
                output,
                error,
                duration,
            ),
        )
        conn.commit()
        return cursor.lastrowid


def fetch_runs(
    job_name: Optional[str] = None,
    limit: int = 50,
    db_path: str = DEFAULT_DB_PATH,
) -> list[dict]:
    """Fetch recent job runs, optionally filtered by job name."""
    query = "SELECT * FROM job_runs"
    params: list = []
    if job_name:
        query += " WHERE job_name = ?"
        params.append(job_name)
    query += " ORDER BY started_at DESC LIMIT ?"
    params.append(limit)

    with get_connection(db_path) as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(row) for row in rows]
