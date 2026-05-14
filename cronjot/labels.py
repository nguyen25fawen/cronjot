"""Label (key-value metadata) support for cron job runs."""

import sqlite3
from typing import Optional


def init_labels_schema(conn: sqlite3.Connection) -> None:
    """Create the labels table if it does not exist."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS labels (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id   INTEGER NOT NULL,
            key      TEXT NOT NULL,
            value    TEXT NOT NULL,
            UNIQUE(run_id, key)
        )
        """
    )
    conn.commit()


def set_label(conn: sqlite3.Connection, run_id: int, key: str, value: str) -> int:
    """Attach or update a label on a run. Returns the label row id."""
    cur = conn.execute(
        """
        INSERT INTO labels (run_id, key, value)
        VALUES (?, ?, ?)
        ON CONFLICT(run_id, key) DO UPDATE SET value=excluded.value
        """,
        (run_id, key, value),
    )
    conn.commit()
    return cur.lastrowid


def remove_label(conn: sqlite3.Connection, run_id: int, key: str) -> bool:
    """Remove a label from a run. Returns True if a row was deleted."""
    cur = conn.execute(
        "DELETE FROM labels WHERE run_id=? AND key=?", (run_id, key)
    )
    conn.commit()
    return cur.rowcount > 0


def fetch_labels(conn: sqlite3.Connection, run_id: int) -> dict:
    """Return all labels for a run as a {key: value} dict."""
    rows = conn.execute(
        "SELECT key, value FROM labels WHERE run_id=? ORDER BY key", (run_id,)
    ).fetchall()
    return {row[0]: row[1] for row in rows}


def fetch_runs_by_label(
    conn: sqlite3.Connection,
    key: str,
    value: Optional[str] = None,
    limit: int = 100,
) -> list:
    """Return run_ids that carry a given label key (and optionally value)."""
    if value is None:
        rows = conn.execute(
            "SELECT DISTINCT run_id FROM labels WHERE key=? LIMIT ?",
            (key, limit),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT DISTINCT run_id FROM labels WHERE key=? AND value=? LIMIT ?",
            (key, value, limit),
        ).fetchall()
    return [row[0] for row in rows]
