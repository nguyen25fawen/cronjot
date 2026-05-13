"""Tests for cronjot/trends.py"""

import sqlite3
import pytest

from cronjot.storage import init_db
from cronjot.trends import (
    get_success_rate_trend,
    get_all_trends,
    format_trends_text,
)


@pytest.fixture
def conn(tmp_path):
    db_path = tmp_path / "test.db"
    c = sqlite3.connect(str(db_path))
    init_db(c)
    yield c
    c.close()


def _add_run(conn, job_name, exit_code, started_at="2024-01-01T00:00:00"):
    conn.execute(
        """
        INSERT INTO runs (job_name, started_at, finished_at, exit_code, output)
        VALUES (?, ?, ?, ?, '')
        """,
        (job_name, started_at, started_at, exit_code),
    )
    conn.commit()


def test_no_runs_returns_insufficient_data(conn):
    result = get_success_rate_trend(conn, "backup")
    assert result["total"] == 0
    assert result["success_rate"] is None
    assert result["trend"] == "insufficient_data"


def test_counts_successes_and_failures(conn):
    for code in [0, 0, 1, 0]:
        _add_run(conn, "sync", code)
    result = get_success_rate_trend(conn, "sync", window=10)
    assert result["total"] == 4
    assert result["successes"] == 3
    assert result["failures"] == 1
    assert result["success_rate"] == pytest.approx(0.75)


def test_trend_insufficient_data_when_fewer_than_four(conn):
    for code in [0, 1, 0]:
        _add_run(conn, "job", code)
    result = get_success_rate_trend(conn, "job", window=10)
    assert result["trend"] == "insufficient_data"


def test_trend_stable(conn):
    # 8 runs, 50% success in both halves
    for code in [0, 1, 0, 1, 0, 1, 0, 1]:
        _add_run(conn, "job", code)
    result = get_success_rate_trend(conn, "job", window=8)
    assert result["trend"] == "stable"


def test_trend_improving(conn):
    # older half: all failures; recent half: all successes
    # insert oldest first so DESC order gives recent first
    for code in [1, 1, 1, 1, 0, 0, 0, 0]:
        _add_run(conn, "job", code)
    result = get_success_rate_trend(conn, "job", window=8)
    assert result["trend"] == "improving"


def test_trend_degrading(conn):
    # older half: all successes; recent half: all failures
    for code in [0, 0, 0, 0, 1, 1, 1, 1]:
        _add_run(conn, "job", code)
    result = get_success_rate_trend(conn, "job", window=8)
    assert result["trend"] == "degrading"


def test_window_limits_rows(conn):
    for code in [1, 1, 1, 1, 0, 0, 0, 0, 0, 0]:
        _add_run(conn, "job", code)
    # window=4 → only the 4 most recent (all failures in our insert order)
    result = get_success_rate_trend(conn, "job", window=4)
    assert result["total"] == 4


def test_get_all_trends_returns_one_per_job(conn):
    _add_run(conn, "alpha", 0)
    _add_run(conn, "beta", 1)
    trends = get_all_trends(conn, window=10)
    names = [t["job_name"] for t in trends]
    assert "alpha" in names
    assert "beta" in names
    assert len(trends) == 2


def test_format_trends_text_empty():
    text = format_trends_text([])
    assert "No trend data" in text


def test_format_trends_text_contains_job_name(conn):
    _add_run(conn, "myjob", 0)
    trends = get_all_trends(conn)
    text = format_trends_text(trends)
    assert "myjob" in text
    assert "%" in text
