"""Trend analysis for cron job run history."""

from __future__ import annotations

import sqlite3
from typing import Optional


def get_success_rate_trend(
    conn: sqlite3.Connection,
    job_name: str,
    window: int = 10,
) -> dict:
    """Return success rate for the last `window` runs of a job.

    Returns a dict with keys:
        job_name, total, successes, failures, success_rate, trend
    where `trend` is one of: 'improving', 'degrading', 'stable', 'insufficient_data'.
    """
    rows = conn.execute(
        """
        SELECT exit_code FROM runs
        WHERE job_name = ?
        ORDER BY started_at DESC
        LIMIT ?
        """,
        (job_name, window),
    ).fetchall()

    if not rows:
        return {
            "job_name": job_name,
            "total": 0,
            "successes": 0,
            "failures": 0,
            "success_rate": None,
            "trend": "insufficient_data",
        }

    codes = [r[0] for r in rows]  # newest first
    total = len(codes)
    successes = sum(1 for c in codes if c == 0)
    failures = total - successes
    success_rate = round(successes / total, 4)

    trend = _compute_trend(codes)

    return {
        "job_name": job_name,
        "total": total,
        "successes": successes,
        "failures": failures,
        "success_rate": success_rate,
        "trend": trend,
    }


def _compute_trend(codes: list[int]) -> str:
    """Split codes (newest-first) into two halves and compare success rates."""
    if len(codes) < 4:
        return "insufficient_data"

    mid = len(codes) // 2
    recent = codes[:mid]      # newer half
    older = codes[mid:]       # older half

    recent_rate = sum(1 for c in recent if c == 0) / len(recent)
    older_rate = sum(1 for c in older if c == 0) / len(older)

    delta = recent_rate - older_rate
    if delta > 0.1:
        return "improving"
    if delta < -0.1:
        return "degrading"
    return "stable"


def get_all_trends(
    conn: sqlite3.Connection,
    window: int = 10,
) -> list[dict]:
    """Return trend data for every distinct job in the database."""
    rows = conn.execute(
        "SELECT DISTINCT job_name FROM runs ORDER BY job_name"
    ).fetchall()
    return [get_success_rate_trend(conn, r[0], window) for r in rows]


def format_trends_text(trends: list[dict]) -> str:
    """Render a plain-text summary of trend data."""
    if not trends:
        return "No trend data available."

    lines = ["Job Trends", "=" * 40]
    for t in trends:
        if t["success_rate"] is None:
            lines.append(f"  {t['job_name']}: no runs recorded")
        else:
            pct = f"{t['success_rate'] * 100:.1f}%"
            lines.append(
                f"  {t['job_name']}: {pct} success "
                f"({t['successes']}/{t['total']}) — {t['trend']}"
            )
    return "\n".join(lines)
