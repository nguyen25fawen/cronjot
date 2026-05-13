"""Dependency tracking between cron jobs.

Allows declaring that one job depends on the successful completion
of another before it should run.
"""

import sqlite3
from typing import Optional


def init_dependencies_schema(conn: sqlite3.Connection) -> None:
    """Create the job_dependencies table if it does not exist."""
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS job_dependencies (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            job_name    TEXT NOT NULL,
            depends_on  TEXT NOT NULL,
            created_at  TEXT NOT NULL DEFAULT (datetime('now')),
            UNIQUE(job_name, depends_on)
        )
        """
    )
    conn.commit()


def add_dependency(conn: sqlite3.Connection, job_name: str, depends_on: str) -> None:
    """Declare that *job_name* depends on *depends_on*."""
    if job_name == depends_on:
        raise ValueError("A job cannot depend on itself.")
    conn.execute(
        "INSERT OR IGNORE INTO job_dependencies (job_name, depends_on) VALUES (?, ?)",
        (job_name, depends_on),
    )
    conn.commit()


def remove_dependency(conn: sqlite3.Connection, job_name: str, depends_on: str) -> None:
    """Remove a previously declared dependency."""
    conn.execute(
        "DELETE FROM job_dependencies WHERE job_name = ? AND depends_on = ?",
        (job_name, depends_on),
    )
    conn.commit()


def list_dependencies(conn: sqlite3.Connection, job_name: str) -> list[str]:
    """Return all job names that *job_name* depends on."""
    rows = conn.execute(
        "SELECT depends_on FROM job_dependencies WHERE job_name = ? ORDER BY depends_on",
        (job_name,),
    ).fetchall()
    return [row[0] for row in rows]


def check_dependencies_met(
    conn: sqlite3.Connection,
    job_name: str,
    since: Optional[str] = None,
) -> tuple[bool, list[str]]:
    """Check whether all dependencies for *job_name* have a successful run.

    Parameters
    ----------
    conn:
        Open database connection.
    job_name:
        The job whose dependencies should be evaluated.
    since:
        Optional ISO-8601 datetime string; only runs after this timestamp
        are considered.  When *None*, the most recent run per dependency
        is used regardless of age.

    Returns
    -------
    (all_met, unmet_list)
        *all_met* is True when every dependency has at least one successful
        run (within the optional time window).  *unmet_list* contains the
        names of dependencies that are not yet satisfied.
    """
    deps = list_dependencies(conn, job_name)
    if not deps:
        return True, []

    unmet: list[str] = []
    for dep in deps:
        if since:
            row = conn.execute(
                "SELECT COUNT(*) FROM runs WHERE job_name = ? AND exit_code = 0 AND started_at >= ?",
                (dep, since),
            ).fetchone()
        else:
            row = conn.execute(
                "SELECT COUNT(*) FROM runs WHERE job_name = ? AND exit_code = 0",
                (dep,),
            ).fetchone()
        if row[0] == 0:
            unmet.append(dep)

    return len(unmet) == 0, unmet
