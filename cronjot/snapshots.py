"""Snapshot support: capture and compare point-in-time metric summaries."""

import json
import sqlite3
from datetime import datetime, timezone
from typing import Optional

from cronjot.storage import get_connection
from cronjot.metrics import get_all_job_metrics


def init_snapshots_schema(conn: sqlite3.Connection) -> None:
    """Create the snapshots table if it does not exist."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            label TEXT NOT NULL,
            created_at TEXT NOT NULL,
            payload TEXT NOT NULL
        )
        """
    )
    conn.commit()


def take_snapshot(conn: sqlite3.Connection, label: str) -> int:
    """Capture current metrics for all jobs and store as a named snapshot.

    Returns the new snapshot id.
    """
    metrics = get_all_job_metrics(conn)
    payload = json.dumps(metrics)
    created_at = datetime.now(timezone.utc).isoformat()
    cur = conn.execute(
        "INSERT INTO snapshots (label, created_at, payload) VALUES (?, ?, ?)",
        (label, created_at, payload),
    )
    conn.commit()
    return cur.lastrowid


def list_snapshots(conn: sqlite3.Connection) -> list:
    """Return all snapshots ordered by creation time descending."""
    cur = conn.execute(
        "SELECT id, label, created_at FROM snapshots ORDER BY created_at DESC"
    )
    return [{"id": r[0], "label": r[1], "created_at": r[2]} for r in cur.fetchall()]


def get_snapshot(conn: sqlite3.Connection, snapshot_id: int) -> Optional[dict]:
    """Fetch a single snapshot by id, returning None if not found."""
    cur = conn.execute(
        "SELECT id, label, created_at, payload FROM snapshots WHERE id = ?",
        (snapshot_id,),
    )
    row = cur.fetchone()
    if row is None:
        return None
    return {
        "id": row[0],
        "label": row[1],
        "created_at": row[2],
        "metrics": json.loads(row[3]),
    }


def delete_snapshot(conn: sqlite3.Connection, snapshot_id: int) -> bool:
    """Delete a snapshot by id. Returns True if a row was removed."""
    cur = conn.execute("DELETE FROM snapshots WHERE id = ?", (snapshot_id,))
    conn.commit()
    return cur.rowcount > 0


def compare_snapshots(snap_a: dict, snap_b: dict) -> dict:
    """Return a diff of two snapshot metric payloads.

    For each job present in either snapshot the function reports the delta
    for total_runs, successes, failures and avg_duration_seconds.
    """
    metrics_a = {m["job_name"]: m for m in snap_a.get("metrics", [])}
    metrics_b = {m["job_name"]: m for m in snap_b.get("metrics", [])}
    all_jobs = set(metrics_a) | set(metrics_b)
    FIELDS = ("total_runs", "successes", "failures", "avg_duration_seconds")
    diff = {}
    for job in sorted(all_jobs):
        a = metrics_a.get(job, {})
        b = metrics_b.get(job, {})
        diff[job] = {
            f: round((b.get(f) or 0) - (a.get(f) or 0), 4) for f in FIELDS
        }
    return diff
