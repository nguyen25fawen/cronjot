"""Audit log for cronjot — records configuration and administrative actions."""

import sqlite3
import time
from typing import Optional

from cronjot.storage import get_connection


def init_audit_schema(conn: sqlite3.Connection) -> None:
    """Create the audit_log table if it does not exist."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS audit_log (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            ts        REAL    NOT NULL,
            actor     TEXT    NOT NULL,
            action    TEXT    NOT NULL,
            target    TEXT,
            detail    TEXT
        )
        """
    )
    conn.commit()


def record_action(
    conn: sqlite3.Connection,
    actor: str,
    action: str,
    target: Optional[str] = None,
    detail: Optional[str] = None,
) -> int:
    """Insert an audit entry and return its id."""
    cur = conn.execute(
        "INSERT INTO audit_log (ts, actor, action, target, detail) VALUES (?, ?, ?, ?, ?)",
        (time.time(), actor, action, target, detail),
    )
    conn.commit()
    return cur.lastrowid


def fetch_audit_log(
    conn: sqlite3.Connection,
    actor: Optional[str] = None,
    action: Optional[str] = None,
    limit: int = 100,
) -> list:
    """Return audit entries, optionally filtered by actor and/or action."""
    query = "SELECT id, ts, actor, action, target, detail FROM audit_log"
    conditions, params = [], []
    if actor:
        conditions.append("actor = ?")
        params.append(actor)
    if action:
        conditions.append("action = ?")
        params.append(action)
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY ts DESC LIMIT ?"
    params.append(limit)
    rows = conn.execute(query, params).fetchall()
    keys = ("id", "ts", "actor", "action", "target", "detail")
    return [dict(zip(keys, row)) for row in rows]


def purge_audit_log(conn: sqlite3.Connection, older_than_ts: float) -> int:
    """Delete entries older than *older_than_ts* (epoch float). Returns row count."""
    cur = conn.execute("DELETE FROM audit_log WHERE ts < ?", (older_than_ts,))
    conn.commit()
    return cur.rowcount
