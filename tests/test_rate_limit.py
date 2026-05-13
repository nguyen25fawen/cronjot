"""Tests for cronjot/rate_limit.py"""

import time
import sqlite3
import pytest

from cronjot.storage import init_db
from cronjot.rate_limit import (
    init_rate_limit_schema,
    set_rate_limit,
    remove_rate_limit,
    get_rate_limit,
    is_rate_limited,
    list_rate_limits,
)


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    init_db(c)
    init_rate_limit_schema(c)
    return c


def _add_run(conn, job_name, started_at=None):
    if started_at is None:
        started_at = time.time()
    conn.execute(
        "INSERT INTO runs (job_name, started_at, finished_at, exit_code, stdout, stderr)"
        " VALUES (?, ?, ?, 0, '', '')",
        (job_name, started_at, started_at + 1),
    )
    conn.commit()


def test_set_and_get_rate_limit(conn):
    set_rate_limit(conn, "backup", max_runs=5, window_seconds=3600)
    cfg = get_rate_limit(conn, "backup")
    assert cfg["job_name"] == "backup"
    assert cfg["max_runs"] == 5
    assert cfg["window_seconds"] == 3600


def test_get_rate_limit_returns_none_if_not_set(conn):
    assert get_rate_limit(conn, "nonexistent") is None


def test_set_rate_limit_updates_existing(conn):
    set_rate_limit(conn, "backup", max_runs=5, window_seconds=3600)
    set_rate_limit(conn, "backup", max_runs=10, window_seconds=7200)
    cfg = get_rate_limit(conn, "backup")
    assert cfg["max_runs"] == 10
    assert cfg["window_seconds"] == 7200


def test_set_rate_limit_invalid_max_runs_raises(conn):
    with pytest.raises(ValueError, match="max_runs"):
        set_rate_limit(conn, "backup", max_runs=0, window_seconds=60)


def test_set_rate_limit_invalid_window_raises(conn):
    with pytest.raises(ValueError, match="window_seconds"):
        set_rate_limit(conn, "backup", max_runs=3, window_seconds=0)


def test_remove_rate_limit_returns_true(conn):
    set_rate_limit(conn, "backup", 3, 60)
    assert remove_rate_limit(conn, "backup") is True
    assert get_rate_limit(conn, "backup") is None


def test_remove_rate_limit_returns_false_if_missing(conn):
    assert remove_rate_limit(conn, "ghost") is False


def test_not_rate_limited_when_no_config(conn):
    _add_run(conn, "daily")
    assert is_rate_limited(conn, "daily") is False


def test_not_rate_limited_below_threshold(conn):
    set_rate_limit(conn, "daily", max_runs=3, window_seconds=3600)
    _add_run(conn, "daily")
    _add_run(conn, "daily")
    assert is_rate_limited(conn, "daily") is False


def test_rate_limited_at_threshold(conn):
    set_rate_limit(conn, "daily", max_runs=2, window_seconds=3600)
    _add_run(conn, "daily")
    _add_run(conn, "daily")
    assert is_rate_limited(conn, "daily") is True


def test_old_runs_outside_window_not_counted(conn):
    set_rate_limit(conn, "daily", max_runs=2, window_seconds=60)
    old_ts = time.time() - 120  # outside the 60s window
    _add_run(conn, "daily", started_at=old_ts)
    _add_run(conn, "daily", started_at=old_ts)
    assert is_rate_limited(conn, "daily") is False


def test_list_rate_limits_empty(conn):
    assert list_rate_limits(conn) == []


def test_list_rate_limits_returns_all(conn):
    set_rate_limit(conn, "alpha", 1, 60)
    set_rate_limit(conn, "beta", 5, 300)
    limits = list_rate_limits(conn)
    names = [r["job_name"] for r in limits]
    assert "alpha" in names
    assert "beta" in names
    assert len(limits) == 2
