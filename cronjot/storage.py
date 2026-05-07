"""SQLite storage layer for cronjot run history."""

import sqlite3
from typing import List, Optional


ROW_FACTORY = sqlite3.Row


def get_connection(db_path: str) -> sqlite3.Connection:
    """Open (or create) the SQLite database at *db_path*."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = ROW_FACTORY
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    """Create the *runs* table if it does not already exist."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS runs (
            id               INTEGER PRIMARY KEY AUTOINCREMENT,
            job_name         TEXT    NOT NULL,
            command          TEXT    NOT NULL,
            started_at       TEXT    NOT NULL,
            duration_seconds REAL    NOT NULL,
            status           TEXT    NOT NULL,
            exit_code        INTEGER NOT NULL,
            output           TEXT    NOT NULL DEFAULT ''
        );

        CREATE INDEX IF NOT EXISTS idx_runs_job_name
            ON runs (job_name);

        CREATE INDEX IF NOT EXISTS idx_runs_started_at
            ON runs (started_at);
    """)
    conn.commit()


def insert_run(
    conn: sqlite3.Connection,
    job_name: str,
    command: str,
    started_at: str,
    duration_seconds: float,
    status: str,
    exit_code: int,
    output: str = "",
) -> int:
    """Insert a run record and return its new *id*."""
    cur = conn.execute(
        """
        INSERT INTO runs
            (job_name, command, started_at, duration_seconds, status, exit_code, output)
        VALUES
            (?, ?, ?, ?, ?, ?, ?)
        """,
        (job_name, command, started_at, duration_seconds, status, exit_code, output),
    )
    conn.commit()
    return cur.lastrowid


def fetch_runs(
    conn: sqlite3.Connection,
    job_name: Optional[str] = None,
    limit: int = 100,
    status: Optional[str] = None,
) -> List[sqlite3.Row]:
    """Fetch run records, optionally filtered by *job_name* and/or *status*."""
    clauses: List[str] = []
    params: List = []

    if job_name is not None:
        clauses.append("job_name = ?")
        params.append(job_name)

    if status is not None:
        clauses.append("status = ?")
        params.append(status)

    where = ("WHERE " + " AND ".join(clauses)) if clauses else ""
    params.append(limit)

    cur = conn.execute(
        f"SELECT * FROM runs {where} ORDER BY started_at DESC LIMIT ?",
        params,
    )
    return cur.fetchall()
