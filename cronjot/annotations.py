"""Run annotations: attach key-value notes to job runs."""

import sqlite3
from typing import Optional


def init_annotations_schema(conn: sqlite3.Connection) -> None:
    """Create the run_annotations table if it doesn't exist."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS run_annotations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            run_id INTEGER NOT NULL,
            key TEXT NOT NULL,
            value TEXT NOT NULL,
            created_at TEXT NOT NULL DEFAULT (datetime('now')),
            FOREIGN KEY (run_id) REFERENCES runs(id) ON DELETE CASCADE
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_annotations_run_id ON run_annotations(run_id)"
    )
    conn.commit()


def annotate_run(
    conn: sqlite3.Connection, run_id: int, key: str, value: str
) -> int:
    """Attach a key-value annotation to a run. Returns the new annotation id."""
    cur = conn.execute(
        "INSERT INTO run_annotations (run_id, key, value) VALUES (?, ?, ?)",
        (run_id, key, value),
    )
    conn.commit()
    return cur.lastrowid


def fetch_annotations(conn: sqlite3.Connection, run_id: int) -> list[dict]:
    """Return all annotations for a given run_id."""
    cur = conn.execute(
        "SELECT id, run_id, key, value, created_at FROM run_annotations WHERE run_id = ? ORDER BY id",
        (run_id,),
    )
    rows = cur.fetchall()
    return [
        {"id": r[0], "run_id": r[1], "key": r[2], "value": r[3], "created_at": r[4]}
        for r in rows
    ]


def delete_annotation(conn: sqlite3.Connection, annotation_id: int) -> bool:
    """Delete a single annotation by id. Returns True if a row was deleted."""
    cur = conn.execute(
        "DELETE FROM run_annotations WHERE id = ?", (annotation_id,)
    )
    conn.commit()
    return cur.rowcount > 0


def fetch_runs_by_annotation(
    conn: sqlite3.Connection, key: str, value: Optional[str] = None
) -> list[int]:
    """Return distinct run_ids that have a matching annotation key (and optionally value)."""
    if value is None:
        cur = conn.execute(
            "SELECT DISTINCT run_id FROM run_annotations WHERE key = ? ORDER BY run_id",
            (key,),
        )
    else:
        cur = conn.execute(
            "SELECT DISTINCT run_id FROM run_annotations WHERE key = ? AND value = ? ORDER BY run_id",
            (key, value),
        )
    return [row[0] for row in cur.fetchall()]
