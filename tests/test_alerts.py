"""Tests for cronjot.alerts module."""

import sqlite3
import time
import pytest

from cronjot.storage import init_db, insert_run
from cronjot.alerts import (
    check_consecutive_failures,
    check_duration_exceeded,
    evaluate_alerts,
)


@pytest.fixture
def conn(tmp_path):
    db_path = str(tmp_path / "test.db")
    c = sqlite3.connect(db_path)
    c.row_factory = sqlite3.Row
    init_db(c)
    yield c
    c.close()


def _add_run(conn, job_name, exit_code, duration=1.0):
    insert_run(conn, job_name=job_name, exit_code=exit_code,
               stdout="", stderr="", duration=duration)


# --- check_consecutive_failures ---

def test_no_runs_does_not_trigger(conn):
    triggered, count = check_consecutive_failures(conn, "backup", threshold=3)
    assert not triggered
    assert count == 0


def test_fewer_runs_than_threshold_does_not_trigger(conn):
    _add_run(conn, "backup", exit_code=1)
    _add_run(conn, "backup", exit_code=1)
    triggered, count = check_consecutive_failures(conn, "backup", threshold=3)
    assert not triggered
    assert count == 2


def test_consecutive_failures_triggers(conn):
    for _ in range(3):
        _add_run(conn, "backup", exit_code=1)
    triggered, count = check_consecutive_failures(conn, "backup", threshold=3)
    assert triggered
    assert count == 3


def test_mixed_results_do_not_trigger(conn):
    _add_run(conn, "backup", exit_code=0)
    _add_run(conn, "backup", exit_code=1)
    _add_run(conn, "backup", exit_code=1)
    triggered, count = check_consecutive_failures(conn, "backup", threshold=3)
    assert not triggered


# --- check_duration_exceeded ---

def test_duration_not_exceeded(conn):
    _add_run(conn, "sync", exit_code=0, duration=5.0)
    triggered, duration = check_duration_exceeded(conn, "sync", max_seconds=10.0)
    assert not triggered
    assert duration == pytest.approx(5.0)


def test_duration_exceeded(conn):
    _add_run(conn, "sync", exit_code=0, duration=15.0)
    triggered, duration = check_duration_exceeded(conn, "sync", max_seconds=10.0)
    assert triggered
    assert duration == pytest.approx(15.0)


def test_duration_no_runs(conn):
    triggered, duration = check_duration_exceeded(conn, "sync", max_seconds=10.0)
    assert not triggered
    assert duration is None


# --- evaluate_alerts ---

def test_evaluate_alerts_no_issues(conn):
    _add_run(conn, "etl", exit_code=0, duration=2.0)
    msgs = evaluate_alerts(conn, "etl", consecutive_failure_threshold=3,
                           max_duration_seconds=10.0)
    assert msgs == []


def test_evaluate_alerts_both_triggered(conn):
    for _ in range(3):
        _add_run(conn, "etl", exit_code=1, duration=20.0)
    msgs = evaluate_alerts(conn, "etl", consecutive_failure_threshold=3,
                           max_duration_seconds=10.0)
    assert len(msgs) == 2
    assert any("failed" in m for m in msgs)
    assert any("exceeding" in m for m in msgs)
