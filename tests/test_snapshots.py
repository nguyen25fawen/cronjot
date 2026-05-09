"""Tests for cronjot/snapshots.py."""

import sqlite3
import pytest

from cronjot.storage import init_db
from cronjot.snapshots import (
    init_snapshots_schema,
    take_snapshot,
    list_snapshots,
    get_snapshot,
    delete_snapshot,
    compare_snapshots,
)


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    init_db(c)
    init_snapshots_schema(c)
    yield c
    c.close()


def _add_run(conn, job_name, exit_code=0, duration=1.0):
    conn.execute(
        "INSERT INTO runs (job_name, started_at, duration_seconds, exit_code, output) "
        "VALUES (?, datetime('now'), ?, ?, '')",
        (job_name, duration, exit_code),
    )
    conn.commit()


def test_take_snapshot_returns_id(conn):
    _add_run(conn, "backup")
    snap_id = take_snapshot(conn, "baseline")
    assert isinstance(snap_id, int)
    assert snap_id >= 1


def test_list_snapshots_empty(conn):
    assert list_snapshots(conn) == []


def test_list_snapshots_returns_metadata(conn):
    _add_run(conn, "backup")
    take_snapshot(conn, "first")
    take_snapshot(conn, "second")
    snaps = list_snapshots(conn)
    assert len(snaps) == 2
    labels = [s["label"] for s in snaps]
    assert "first" in labels and "second" in labels


def test_get_snapshot_not_found(conn):
    assert get_snapshot(conn, 999) is None


def test_get_snapshot_contains_metrics(conn):
    _add_run(conn, "sync", exit_code=0, duration=2.5)
    snap_id = take_snapshot(conn, "v1")
    snap = get_snapshot(conn, snap_id)
    assert snap["label"] == "v1"
    assert isinstance(snap["metrics"], list)
    job_names = [m["job_name"] for m in snap["metrics"]]
    assert "sync" in job_names


def test_delete_snapshot_removes_record(conn):
    _add_run(conn, "job")
    snap_id = take_snapshot(conn, "to-delete")
    assert delete_snapshot(conn, snap_id) is True
    assert get_snapshot(conn, snap_id) is None


def test_delete_snapshot_nonexistent_returns_false(conn):
    assert delete_snapshot(conn, 9999) is False


def test_compare_snapshots_delta(conn):
    _add_run(conn, "etl", exit_code=0, duration=1.0)
    snap_a = {"metrics": [{"job_name": "etl", "total_runs": 1, "successes": 1,
                           "failures": 0, "avg_duration_seconds": 1.0}]}
    snap_b = {"metrics": [{"job_name": "etl", "total_runs": 3, "successes": 2,
                           "failures": 1, "avg_duration_seconds": 1.5}]}
    diff = compare_snapshots(snap_a, snap_b)
    assert diff["etl"]["total_runs"] == 2
    assert diff["etl"]["successes"] == 1
    assert diff["etl"]["failures"] == 1
    assert abs(diff["etl"]["avg_duration_seconds"] - 0.5) < 1e-6


def test_compare_snapshots_new_job(conn):
    snap_a = {"metrics": []}
    snap_b = {"metrics": [{"job_name": "new-job", "total_runs": 5,
                           "successes": 5, "failures": 0,
                           "avg_duration_seconds": 0.2}]}
    diff = compare_snapshots(snap_a, snap_b)
    assert "new-job" in diff
    assert diff["new-job"]["total_runs"] == 5
