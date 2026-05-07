"""schedule_runner – run all jobs whose cron expressions match *now*.

Expected config format (TOML-like dict, typically loaded from a file):

    jobs = [
        {"name": "backup", "command": "./backup.sh", "schedule": "0 2 * * *"},
        {"name": "report", "command": "python report.py", "schedule": "*/15 * * * *"},
    ]
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from cronjot.runner import run_job
from cronjot.scheduler import CronExpression
from cronjot.storage import get_connection, init_db

logger = logging.getLogger(__name__)


def run_scheduled_jobs(
    jobs: list[dict[str, Any]],
    db_path: str,
    now: datetime | None = None,
) -> list[dict[str, Any]]:
    """Evaluate each job's schedule and execute matching jobs.

    Parameters
    ----------
    jobs:
        List of job dicts, each with keys ``name``, ``command``, ``schedule``.
    db_path:
        Path to the SQLite database file.
    now:
        Datetime to evaluate schedules against (defaults to current time).

    Returns
    -------
    List of result dicts returned by :func:`~cronjot.runner.run_job` for every
    job that was actually executed.
    """
    if now is None:
        now = datetime.now()

    conn = get_connection(db_path)
    init_db(conn)

    results: list[dict[str, Any]] = []
    for job in jobs:
        name = job["name"]
        command = job["command"]
        schedule = job.get("schedule", "* * * * *")

        try:
            expr = CronExpression(schedule)
        except ValueError as exc:
            logger.error("Invalid schedule for job %r: %s", name, exc)
            continue

        if not expr.matches(now):
            logger.debug("Skipping job %r (schedule %r does not match %s)", name, schedule, now)
            continue

        logger.info("Running job %r (%s)", name, command)
        result = run_job(name=name, command=command, conn=conn)
        results.append(result)

    conn.close()
    return results
