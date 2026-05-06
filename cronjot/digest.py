"""Digest summary builder for cron job run history."""

from datetime import datetime, timedelta
from typing import Optional
from cronjot.storage import fetch_runs


def build_digest(db_path: str, hours: int = 24, job_name: Optional[str] = None) -> dict:
    """Build a digest summary of job runs over the last N hours."""
    since = datetime.utcnow() - timedelta(hours=hours)
    runs = fetch_runs(db_path, job_name=job_name, since=since)

    total = len(runs)
    successes = sum(1 for r in runs if r["exit_code"] == 0)
    failures = total - successes

    failed_jobs = [
        {"job_name": r["job_name"], "started_at": r["started_at"], "stderr": r["stderr"]}
        for r in runs
        if r["exit_code"] != 0
    ]

    return {
        "period_hours": hours,
        "generated_at": datetime.utcnow().isoformat(),
        "total_runs": total,
        "successes": successes,
        "failures": failures,
        "failed_jobs": failed_jobs,
    }


def format_digest_text(digest: dict) -> str:
    """Format a digest dict into a human-readable plain-text summary."""
    lines = [
        f"CronJot Digest — Last {digest['period_hours']}h (generated {digest['generated_at']})",
        "-" * 60,
        f"Total runs : {digest['total_runs']}",
        f"Successes  : {digest['successes']}",
        f"Failures   : {digest['failures']}",
    ]

    if digest["failed_jobs"]:
        lines.append("\nFailed Jobs:")
        for job in digest["failed_jobs"]:
            lines.append(f"  • {job['job_name']} at {job['started_at']}")
            if job.get("stderr"):
                snippet = job["stderr"][:200].replace("\n", " ")
                lines.append(f"    stderr: {snippet}")
    else:
        lines.append("\nAll jobs completed successfully. ✓")

    return "\n".join(lines)
