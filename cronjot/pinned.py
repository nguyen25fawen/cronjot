"""Pinned runs: mark specific run IDs as important for long-term reference."""

import sqlite3
from typing import Optional


def init_pinned_schema(conn: sqlite3.Connection) -> None:
    """Create the pinned_runs table if it does not exist."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS pinned_runs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id      INTEGER NOT NULL UNIQUE,
            label       TEXT,
            pinned_at   TEXT NOT NULL DEFAULT (datetime('now'))
        )
        """
    )
    conn.commit()


def pin_run(
    conn: sqlite3.Connection, run_id: int, label: Optional[str] = None
) -> int:
    """Pin a run by its ID. Returns the pin record ID."""
    cur = conn.execute(
        "SELECT id FROM runs WHERE id = ?", (run_id,)
    )
    if cur.fetchone() is None:
        raise ValueError(f"Run ID {run_id} does not exist.")

    cur = conn.execute(
        """
        INSERT INTO pinned_runs (run_id, label)
        VALUES (?, ?)
        ON CONFLICT(run_id) DO UPDATE SET label = excluded.label
        """,
        (run_id, label),
    )
    conn.commit()
    return cur.lastrowid


def unpin_run(conn: sqlite3.Connection, run_id: int) -> bool:
    """Remove a pin for the given run ID. Returns True if a row was deleted."""
    cur = conn.execute(
        "DELETE FROM pinned_runs WHERE run_id = ?", (run_id,)
    )
    conn.commit()
    return cur.rowcount > 0


def is_pinned(conn: sqlite3.Connection, run_id: int) -> bool:
    """Return True if the run is currently pinned."""
    cur = conn.execute(
        "SELECT 1 FROM pinned_runs WHERE run_id = ?", (run_id,)
    )
    return cur.fetchone() is not None


def list_pinned_runs(conn: sqlite3.Connection) -> list:
    """Return all pinned run records joined with run metadata."""
    cur = conn.execute(
        """
        SELECT p.run_id, p.label, p.pinned_at,
               r.job_name, r.exit_code, r.started_at
        FROM pinned_runs p
        JOIN runs r ON r.id = p.run_id
        ORDER BY p.pinned_at DESC
        """
    )
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]
