"""Tests for cronjot.retention (prune_runs, prune_excess_runs)."""

import os
import sqlite3
from datetime import datetime, timedelta

import pytest

from cronjot.storage import init_db, get_connection
from cronjot.retention import prune_runs, prune_excess_runs


@pytest.fixture()
def tmp_db(tmp_path):
    db_path = str(tmp_path / "test.db")
    init_db(db_path)
    return db_path


def _add_run(db_path, job_name, days_ago, exit_code=0):
    """Insert a run record with started_at set *days_ago* days in the past."""
    started_at = (datetime.utcnow() - timedelta(days=days_ago)).strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    conn = get_connection(db_path)
    conn.execute(
        "INSERT INTO runs (job_name, started_at, duration, exit_code, output)"
        " VALUES (?, ?, ?, ?, ?)",
        (job_name, started_at, 1.0, exit_code, ""),
    )
    conn.commit()
    conn.close()


def _count_runs(db_path, job_name=None):
    conn = get_connection(db_path)
    if job_name:
        row = conn.execute(
            "SELECT COUNT(*) FROM runs WHERE job_name = ?", (job_name,)
        ).fetchone()
    else:
        row = conn.execute("SELECT COUNT(*) FROM runs").fetchone()
    conn.close()
    return row[0]


# ---------------------------------------------------------------------------
# prune_runs
# ---------------------------------------------------------------------------

def test_prune_runs_removes_old_records(tmp_db):
    _add_run(tmp_db, "backup", days_ago=10)
    _add_run(tmp_db, "backup", days_ago=2)
    deleted = prune_runs(tmp_db, older_than_days=7)
    assert deleted == 1
    assert _count_runs(tmp_db) == 1


def test_prune_runs_nothing_to_delete(tmp_db):
    _add_run(tmp_db, "backup", days_ago=1)
    deleted = prune_runs(tmp_db, older_than_days=7)
    assert deleted == 0
    assert _count_runs(tmp_db) == 1


def test_prune_runs_filtered_by_job_name(tmp_db):
    _add_run(tmp_db, "backup", days_ago=10)
    _add_run(tmp_db, "report", days_ago=10)
    deleted = prune_runs(tmp_db, older_than_days=7, job_name="backup")
    assert deleted == 1
    assert _count_runs(tmp_db, "report") == 1


def test_prune_runs_invalid_days_raises(tmp_db):
    with pytest.raises(ValueError):
        prune_runs(tmp_db, older_than_days=0)


# ---------------------------------------------------------------------------
# prune_excess_runs
# ---------------------------------------------------------------------------

def test_prune_excess_runs_keeps_most_recent(tmp_db):
    for days_ago in range(10, 0, -1):  # oldest first
        _add_run(tmp_db, "sync", days_ago=days_ago)
    deleted = prune_excess_runs(tmp_db, keep=3)
    assert deleted == 7
    assert _count_runs(tmp_db) == 3


def test_prune_excess_runs_scoped_to_job(tmp_db):
    for days_ago in range(5, 0, -1):
        _add_run(tmp_db, "sync", days_ago=days_ago)
        _add_run(tmp_db, "backup", days_ago=days_ago)
    deleted = prune_excess_runs(tmp_db, keep=2, job_name="sync")
    assert deleted == 3
    assert _count_runs(tmp_db, "sync") == 2
    assert _count_runs(tmp_db, "backup") == 5  # untouched


def test_prune_excess_runs_invalid_keep_raises(tmp_db):
    with pytest.raises(ValueError):
        prune_excess_runs(tmp_db, keep=0)


def test_prune_excess_runs_noop_when_under_limit(tmp_db):
    _add_run(tmp_db, "sync", days_ago=1)
    deleted = prune_excess_runs(tmp_db, keep=10)
    assert deleted == 0
