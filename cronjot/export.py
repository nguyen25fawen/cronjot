"""Export run history to CSV or JSON formats."""

import csv
import io
import json
from typing import Literal, Optional

from cronjot.storage import fetch_runs


def export_runs(
    conn,
    fmt: Literal["csv", "json"],
    job_name: Optional[str] = None,
    limit: int = 500,
) -> str:
    """Fetch runs and return them serialised as CSV or JSON string."""
    runs = fetch_runs(conn, job_name=job_name, limit=limit)

    rows = [
        {
            "id": r["id"],
            "job_name": r["job_name"],
            "started_at": r["started_at"],
            "duration_seconds": r["duration_seconds"],
            "exit_code": r["exit_code"],
            "output": r["output"],
        }
        for r in runs
    ]

    if fmt == "json":
        return _to_json(rows)
    elif fmt == "csv":
        return _to_csv(rows)
    else:
        raise ValueError(f"Unsupported export format: {fmt!r}")


def _to_json(rows: list) -> str:
    return json.dumps(rows, indent=2, default=str)


def _to_csv(rows: list) -> str:
    if not rows:
        return ""

    fieldnames = ["id", "job_name", "started_at", "duration_seconds", "exit_code", "output"]
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return buf.getvalue()
