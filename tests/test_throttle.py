"""Tests for cronjot/throttle.py"""

import sqlite3
from datetime import datetime, timedelta

import pytest

from cronjot.storage import init_db
from cronjot.throttle import (
    init_throttle_schema,
    set_throttle,
    remove_throttle,
    get_throttle,
    is_throttled,
    list_throttles,
)


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    init_db(c)
    init_throttle_schema(c)
    return c


def _add_run(conn, job_name, started_at, exit_code=0, duration=1.0):
    conn.execute(
        "INSERT INTO runs (job_name, started_at, finished_at, exit_code, stdout, stderr, duration) "
        "VALUES (?, ?, ?, ?, '', '', ?)",
        (job_name, started_at, started_at, exit_code, duration),
    )
    conn.commit()


def test_set_and_get_throttle(conn):
    set_throttle(conn, "backup", 3600)
    assert get_throttle(conn, "backup") == 3600


def test_get_throttle_returns_none_if_not_set(conn):
    assert get_throttle(conn, "nonexistent") is None


def test_set_throttle_updates_existing(conn):
    set_throttle(conn, "backup", 3600)
    set_throttle(conn, "backup", 7200)
    assert get_throttle(conn, "backup") == 7200


def test_remove_throttle_returns_true(conn):
    set_throttle(conn, "backup", 3600)
    assert remove_throttle(conn, "backup") is True
    assert get_throttle(conn, "backup") is None


def test_remove_throttle_returns_false_if_not_found(conn):
    assert remove_throttle(conn, "ghost") is False


def test_is_throttled_no_rule_returns_false(conn):
    _add_run(conn, "backup", datetime.utcnow().isoformat())
    assert is_throttled(conn, "backup") is False


def test_is_throttled_no_runs_returns_false(conn):
    set_throttle(conn, "backup", 3600)
    assert is_throttled(conn, "backup") is False


def test_is_throttled_recent_run_returns_true(conn):
    set_throttle(conn, "backup", 3600)
    recent = datetime.utcnow().isoformat()
    _add_run(conn, "backup", recent)
    assert is_throttled(conn, "backup") is True


def test_is_throttled_old_run_returns_false(conn):
    set_throttle(conn, "backup", 60)
    old = (datetime.utcnow() - timedelta(seconds=120)).isoformat()
    _add_run(conn, "backup", old)
    assert is_throttled(conn, "backup") is False


def test_list_throttles_empty(conn):
    assert list_throttles(conn) == []


def test_list_throttles_returns_all(conn):
    set_throttle(conn, "alpha", 60)
    set_throttle(conn, "beta", 300)
    rules = list_throttles(conn)
    assert len(rules) == 2
    names = [r["job_name"] for r in rules]
    assert "alpha" in names
    assert "beta" in names


def test_list_throttles_fields(conn):
    set_throttle(conn, "myjob", 120)
    rules = list_throttles(conn)
    assert rules[0]["min_interval_seconds"] == 120
    assert "created_at" in rules[0]
    assert "updated_at" in rules[0]
