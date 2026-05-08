"""Aggregate metrics and statistics for cron job runs."""

from __future__ import annotations

import sqlite3
from typing import Optional


def get_job_metrics(conn: sqlite3.Connection, job_name: str) -> dict:
    """Return aggregated metrics for a specific job."""
    cur = conn.execute(
        """
        SELECT
            COUNT(*) AS total_runs,
            SUM(CASE WHEN exit_code = 0 THEN 1 ELSE 0 END) AS successes,
            SUM(CASE WHEN exit_code != 0 THEN 1 ELSE 0 END) AS failures,
            AVG(duration_seconds) AS avg_duration,
            MIN(duration_seconds) AS min_duration,
            MAX(duration_seconds) AS max_duration,
            MAX(started_at) AS last_run
        FROM runs
        WHERE job_name = ?
        """,
        (job_name,),
    )
    row = cur.fetchone()
    if row is None or row["total_runs"] == 0:
        return {"job_name": job_name, "total_runs": 0}

    total = row["total_runs"]
    successes = row["successes"] or 0
    return {
        "job_name": job_name,
        "total_runs": total,
        "successes": successes,
        "failures": row["failures"] or 0,
        "success_rate": round(successes / total * 100, 2),
        "avg_duration": round(row["avg_duration"], 3) if row["avg_duration"] else None,
        "min_duration": round(row["min_duration"], 3) if row["min_duration"] else None,
        "max_duration": round(row["max_duration"], 3) if row["max_duration"] else None,
        "last_run": row["last_run"],
    }


def get_all_job_metrics(conn: sqlite3.Connection) -> list[dict]:
    """Return metrics for every distinct job in the database."""
    cur = conn.execute("SELECT DISTINCT job_name FROM runs ORDER BY job_name")
    job_names = [r["job_name"] for r in cur.fetchall()]
    return [get_job_metrics(conn, name) for name in job_names]


def format_metrics_text(metrics_list: list[dict]) -> str:
    """Render a human-readable metrics summary."""
    if not metrics_list:
        return "No job metrics available."

    lines = ["=== CronJot Job Metrics ==="]
    for m in metrics_list:
        if m["total_runs"] == 0:
            lines.append(f"\n[{m['job_name']}] — no runs recorded")
            continue
        lines.append(f"\n[{m['job_name']}]")
        lines.append(f"  Total runs   : {m['total_runs']}")
        lines.append(f"  Successes    : {m['successes']} ({m['success_rate']}%)")
        lines.append(f"  Failures     : {m['failures']}")
        if m.get("avg_duration") is not None:
            lines.append(f"  Avg duration : {m['avg_duration']}s")
            lines.append(f"  Min duration : {m['min_duration']}s")
            lines.append(f"  Max duration : {m['max_duration']}s")
        if m.get("last_run"):
            lines.append(f"  Last run     : {m['last_run']}")
    return "\n".join(lines)
