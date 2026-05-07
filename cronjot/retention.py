"""Retention policy: prune old run records from the database."""

import logging
from datetime import datetime, timedelta
from typing import Optional

from cronjot.storage import get_connection

logger = logging.getLogger(__name__)


def prune_runs(
    db_path: str,
    older_than_days: int,
    job_name: Optional[str] = None,
) -> int:
    """Delete run records older than *older_than_days* days.

    Args:
        db_path: Path to the SQLite database file.
        older_than_days: Records with a ``started_at`` timestamp older than
            this many days will be removed.
        job_name: When provided, only records for this specific job are pruned.

    Returns:
        Number of rows deleted.
    """
    if older_than_days < 1:
        raise ValueError("older_than_days must be >= 1")

    cutoff: str = (
        datetime.utcnow() - timedelta(days=older_than_days)
    ).strftime("%Y-%m-%d %H:%M:%S")

    conn = get_connection(db_path)
    try:
        if job_name:
            cursor = conn.execute(
                "DELETE FROM runs WHERE started_at < ? AND job_name = ?",
                (cutoff, job_name),
            )
        else:
            cursor = conn.execute(
                "DELETE FROM runs WHERE started_at < ?",
                (cutoff,),
            )
        conn.commit()
        deleted = cursor.rowcount
    finally:
        conn.close()

    logger.info(
        "Pruned %d run(s) older than %d day(s)%s",
        deleted,
        older_than_days,
        f" for job '{job_name}'" if job_name else "",
    )
    return deleted


def prune_excess_runs(
    db_path: str,
    keep: int,
    job_name: Optional[str] = None,
) -> int:
    """Keep only the *keep* most-recent runs, deleting the rest.

    Args:
        db_path: Path to the SQLite database file.
        keep: Number of most-recent records to retain per job (or globally).
        job_name: When provided, scope the operation to a single job.

    Returns:
        Number of rows deleted.
    """
    if keep < 1:
        raise ValueError("keep must be >= 1")

    conn = get_connection(db_path)
    try:
        if job_name:
            cursor = conn.execute(
                """
                DELETE FROM runs
                WHERE job_name = ?
                  AND id NOT IN (
                      SELECT id FROM runs
                      WHERE job_name = ?
                      ORDER BY started_at DESC
                      LIMIT ?
                  )
                """,
                (job_name, job_name, keep),
            )
        else:
            cursor = conn.execute(
                """
                DELETE FROM runs
                WHERE id NOT IN (
                    SELECT id FROM runs
                    ORDER BY started_at DESC
                    LIMIT ?
                )
                """,
                (keep,),
            )
        conn.commit()
        deleted = cursor.rowcount
    finally:
        conn.close()

    logger.info(
        "Pruned %d excess run(s), keeping last %d%s",
        deleted,
        keep,
        f" for job '{job_name}'" if job_name else "",
    )
    return deleted
