"""Tag management for cron jobs — attach metadata labels to runs and query by tag."""

import sqlite3
from typing import List, Optional


def init_tags_schema(conn: sqlite3.Connection) -> None:
    """Create tags and run_tags tables if they don't exist."""
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS tags (
            id   INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE
        );

        CREATE TABLE IF NOT EXISTS run_tags (
            run_id  INTEGER NOT NULL,
            tag_id  INTEGER NOT NULL,
            PRIMARY KEY (run_id, tag_id),
            FOREIGN KEY (run_id)  REFERENCES runs(id)  ON DELETE CASCADE,
            FOREIGN KEY (tag_id)  REFERENCES tags(id)  ON DELETE CASCADE
        );
    """)
    conn.commit()


def ensure_tag(conn: sqlite3.Connection, tag_name: str) -> int:
    """Return the id of *tag_name*, creating it if necessary."""
    cur = conn.execute("SELECT id FROM tags WHERE name = ?", (tag_name,))
    row = cur.fetchone()
    if row:
        return row["id"]
    cur = conn.execute("INSERT INTO tags (name) VALUES (?)", (tag_name,))
    conn.commit()
    return cur.lastrowid


def tag_run(conn: sqlite3.Connection, run_id: int, tags: List[str]) -> None:
    """Associate *tags* with *run_id*."""
    for tag_name in tags:
        tag_id = ensure_tag(conn, tag_name)
        conn.execute(
            "INSERT OR IGNORE INTO run_tags (run_id, tag_id) VALUES (?, ?)",
            (run_id, tag_id),
        )
    conn.commit()


def fetch_runs_by_tag(
    conn: sqlite3.Connection,
    tag_name: str,
    limit: Optional[int] = 100,
) -> List[sqlite3.Row]:
    """Return runs that carry *tag_name*, newest first."""
    query = """
        SELECT r.*
        FROM runs r
        JOIN run_tags rt ON rt.run_id = r.id
        JOIN tags    t  ON t.id = rt.tag_id
        WHERE t.name = ?
        ORDER BY r.started_at DESC
        LIMIT ?
    """
    cur = conn.execute(query, (tag_name, limit))
    return cur.fetchall()


def list_tags(conn: sqlite3.Connection) -> List[str]:
    """Return all distinct tag names sorted alphabetically."""
    cur = conn.execute("SELECT name FROM tags ORDER BY name")
    return [row["name"] for row in cur.fetchall()]


def get_tags_for_run(conn: sqlite3.Connection, run_id: int) -> List[str]:
    """Return tag names attached to *run_id*."""
    cur = conn.execute(
        """
        SELECT t.name FROM tags t
        JOIN run_tags rt ON rt.tag_id = t.id
        WHERE rt.run_id = ?
        ORDER BY t.name
        """,
        (run_id,),
    )
    return [row["name"] for row in cur.fetchall()]
