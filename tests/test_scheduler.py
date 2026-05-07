"""Tests for CronExpression and schedule_runner.run_scheduled_jobs."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from unittest.mock import patch

import pytest

from cronjot.scheduler import CronExpression
from cronjot.schedule_runner import run_scheduled_jobs


# ---------------------------------------------------------------------------
# CronExpression unit tests
# ---------------------------------------------------------------------------


def test_wildcard_matches_any():
    expr = CronExpression("* * * * *")
    assert expr.matches(datetime(2024, 6, 15, 10, 30))


def test_exact_match():
    expr = CronExpression("30 2 * * *")
    assert expr.matches(datetime(2024, 1, 1, 2, 30))
    assert not expr.matches(datetime(2024, 1, 1, 2, 31))
    assert not expr.matches(datetime(2024, 1, 1, 3, 30))


def test_step_expression():
    expr = CronExpression("*/15 * * * *")
    for minute in (0, 15, 30, 45):
        assert expr.matches(datetime(2024, 3, 10, 8, minute))
    assert not expr.matches(datetime(2024, 3, 10, 8, 1))


def test_range_expression():
    expr = CronExpression("0 9-17 * * *")
    for hour in range(9, 18):
        assert expr.matches(datetime(2024, 5, 20, hour, 0))
    assert not expr.matches(datetime(2024, 5, 20, 8, 0))


def test_list_expression():
    expr = CronExpression("0 8,12,18 * * *")
    assert expr.matches(datetime(2024, 7, 4, 12, 0))
    assert not expr.matches(datetime(2024, 7, 4, 11, 0))


def test_invalid_expression_raises():
    with pytest.raises(ValueError, match="5 fields"):
        CronExpression("* * * *")  # only 4 fields


# ---------------------------------------------------------------------------
# run_scheduled_jobs integration tests
# ---------------------------------------------------------------------------


@pytest.fixture()
def tmp_db(tmp_path):
    return str(tmp_path / "test.db")


JOBS = [
    {"name": "always", "command": "echo hello", "schedule": "* * * * *"},
    {"name": "never", "command": "echo world", "schedule": "0 0 1 1 0"},
]


def test_matching_job_is_executed(tmp_db):
    now = datetime(2024, 6, 15, 10, 30)  # Saturday – won't match dow=0
    results = run_scheduled_jobs(JOBS, tmp_db, now=now)
    names = [r["name"] for r in results]
    assert "always" in names
    assert "never" not in names


def test_no_jobs_run_when_nothing_matches(tmp_db):
    # Use a schedule that never fires in practice
    jobs = [{"name": "rare", "command": "echo hi", "schedule": "0 0 31 2 *"}]
    results = run_scheduled_jobs(jobs, tmp_db, now=datetime(2024, 6, 15, 10, 30))
    assert results == []


def test_invalid_schedule_skipped(tmp_db, caplog):
    jobs = [{"name": "bad", "command": "echo x", "schedule": "bad expr here"}]
    results = run_scheduled_jobs(jobs, tmp_db, now=datetime(2024, 1, 1, 0, 0))
    assert results == []
    assert "Invalid schedule" in caplog.text


def test_results_contain_exit_code(tmp_db):
    jobs = [{"name": "ok", "command": "echo done", "schedule": "* * * * *"}]
    results = run_scheduled_jobs(jobs, tmp_db, now=datetime(2024, 6, 15, 10, 30))
    assert len(results) == 1
    assert results[0]["exit_code"] == 0
