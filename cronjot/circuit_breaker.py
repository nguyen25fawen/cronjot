"""Circuit breaker for cron jobs — pauses scheduling when failure rate is too high."""

import sqlite3
import time
from typing import Optional


def init_circuit_breaker_schema(conn: sqlite3.Connection) -> None:
    conn.execute("""
        CREATE TABLE IF NOT EXISTS circuit_breakers (
            job_name TEXT PRIMARY KEY,
            state TEXT NOT NULL DEFAULT 'closed',
            failure_count INTEGER NOT NULL DEFAULT 0,
            opened_at REAL,
            updated_at REAL NOT NULL
        )
    """)
    conn.commit()


def get_circuit_state(conn: sqlite3.Connection, job_name: str) -> dict:
    row = conn.execute(
        "SELECT state, failure_count, opened_at, updated_at FROM circuit_breakers WHERE job_name = ?",
        (job_name,),
    ).fetchone()
    if row is None:
        return {"state": "closed", "failure_count": 0, "opened_at": None, "updated_at": None}
    return {"state": row[0], "failure_count": row[1], "opened_at": row[2], "updated_at": row[3]}


def record_failure(conn: sqlite3.Connection, job_name: str, threshold: int = 3) -> dict:
    """Increment failure count; open circuit when threshold is reached."""
    now = time.time()
    current = get_circuit_state(conn, job_name)
    new_count = current["failure_count"] + 1
    new_state = "open" if new_count >= threshold else current["state"]
    opened_at = now if new_state == "open" and current["state"] != "open" else current["opened_at"]

    conn.execute(
        """
        INSERT INTO circuit_breakers (job_name, state, failure_count, opened_at, updated_at)
        VALUES (?, ?, ?, ?, ?)
        ON CONFLICT(job_name) DO UPDATE SET
            state = excluded.state,
            failure_count = excluded.failure_count,
            opened_at = excluded.opened_at,
            updated_at = excluded.updated_at
        """,
        (job_name, new_state, new_count, opened_at, now),
    )
    conn.commit()
    return get_circuit_state(conn, job_name)


def record_success(conn: sqlite3.Connection, job_name: str) -> None:
    """Reset circuit breaker on success."""
    now = time.time()
    conn.execute(
        """
        INSERT INTO circuit_breakers (job_name, state, failure_count, opened_at, updated_at)
        VALUES (?, 'closed', 0, NULL, ?)
        ON CONFLICT(job_name) DO UPDATE SET
            state = 'closed',
            failure_count = 0,
            opened_at = NULL,
            updated_at = excluded.updated_at
        """,
        (job_name, now),
    )
    conn.commit()


def is_open(conn: sqlite3.Connection, job_name: str, cooldown_seconds: float = 300.0) -> bool:
    """Return True if the circuit is open (and cooldown has not elapsed)."""
    state = get_circuit_state(conn, job_name)
    if state["state"] != "open":
        return False
    if state["opened_at"] is not None and (time.time() - state["opened_at"]) >= cooldown_seconds:
        return False
    return True


def reset_circuit(conn: sqlite3.Connection, job_name: str) -> None:
    """Manually reset a circuit breaker to closed state."""
    conn.execute("DELETE FROM circuit_breakers WHERE job_name = ?", (job_name,))
    conn.commit()
