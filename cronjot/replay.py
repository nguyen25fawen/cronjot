"""Replay module: re-execute past cron job runs by run ID or job name."""

import sqlite3
from typing import Optional

from cronjot.storage import fetch_runs
from cronjot.runner import run_job


def get_run_by_id(conn: sqlite3.Connection, run_id: int) -> Optional[dict]:
    """Fetch a single run record by its ID."""
    cur = conn.execute(
        "SELECT id, job_name, command, status, exit_code, stdout, stderr, "
        "started_at, finished_at, duration_seconds "
        "FROM runs WHERE id = ?",
        (run_id,),
    )
    row = cur.fetchone()
    if row is None:
        return None
    keys = [d[0] for d in cur.description]
    return dict(zip(keys, row))


def replay_run(conn: sqlite3.Connection, run_id: int, db_path: str) -> dict:
    """Re-execute a job using the command from a previous run record.

    Args:
        conn: Active database connection (used to look up the original run).
        run_id: The ID of the run to replay.
        db_path: Path to the SQLite database file (passed to run_job for persistence).

    Returns:
        A dict with keys: job_name, command, exit_code, stdout, stderr, duration_seconds.

    Raises:
        ValueError: If no run with the given ID exists.
    """
    original = get_run_by_id(conn, run_id)
    if original is None:
        raise ValueError(f"No run found with id={run_id}")

    result = run_job(
        job_name=original["job_name"],
        command=original["command"],
        db_path=db_path,
    )
    return result


def replay_latest(conn: sqlite3.Connection, job_name: str, db_path: str) -> dict:
    """Re-execute the most recent run of a given job.

    Args:
        conn: Active database connection.
        job_name: The job whose latest run should be replayed.
        db_path: Path to the SQLite database file.

    Returns:
        Result dict from run_job.

    Raises:
        ValueError: If no runs exist for the given job name.
    """
    runs = fetch_runs(conn, job_name=job_name, limit=1)
    if not runs:
        raise ValueError(f"No runs found for job '{job_name}'")

    latest = runs[0]
    result = run_job(
        job_name=latest["job_name"],
        command=latest["command"],
        db_path=db_path,
    )
    return result
