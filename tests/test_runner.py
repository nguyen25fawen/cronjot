"""Tests for cronjot.runner module."""

import pytest
from cronjot.runner import run_job
from cronjot.storage import fetch_runs


@pytest.fixture()
def db(tmp_path):
    return str(tmp_path / "test.db")


def test_successful_command(db):
    result = run_job("echo_job", "echo hello", db_path=db)
    assert result["success"] is True
    assert result["exit_code"] == 0
    assert result["output"] == "hello"
    assert result["error"] is None
    assert result["duration_seconds"] >= 0


def test_failing_command(db):
    result = run_job("fail_job", "ls /nonexistent_path_xyz", db_path=db)
    assert result["success"] is False
    assert result["exit_code"] != 0


def test_run_is_persisted(db):
    run_job("persist_job", "echo stored", db_path=db)
    runs = fetch_runs(job_name="persist_job", db_path=db)
    assert len(runs) == 1
    assert runs[0]["output"] == "stored"


def test_unknown_command(db):
    result = run_job("bad_cmd", "__no_such_command__", db_path=db)
    assert result["exit_code"] == 127
    assert result["error"] is not None


def test_timeout_is_recorded(db):
    result = run_job("slow_job", "sleep 10", timeout=1, db_path=db)
    assert result["exit_code"] == -1
    assert "Timed out" in result["error"]
    runs = fetch_runs(job_name="slow_job", db_path=db)
    assert len(runs) == 1
