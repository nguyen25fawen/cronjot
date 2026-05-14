"""Tests for cronjot/pause.py and cronjot/cli_pause.py."""

import argparse
import sqlite3
import sys
from unittest.mock import patch

import pytest

from cronjot.pause import (
    init_pause_schema,
    pause_job,
    resume_job,
    is_paused,
    list_paused_jobs,
    get_pause_info,
)
from cronjot.cli_pause import cmd_pause, cmd_resume, cmd_list_paused, cmd_check_pause


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    init_pause_schema(c)
    yield c
    c.close()


def _args(**kwargs):
    base = {"db": ":memory:"}
    base.update(kwargs)
    return argparse.Namespace(**base)


# --- unit tests for pause.py ---

def test_init_creates_table(conn):
    cur = conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='job_pauses'")
    assert cur.fetchone() is not None


def test_pause_job_marks_as_paused(conn):
    pause_job(conn, "backup", reason="maintenance")
    assert is_paused(conn, "backup") is True


def test_is_paused_returns_false_for_unknown(conn):
    assert is_paused(conn, "nonexistent") is False


def test_pause_idempotent_updates_reason(conn):
    pause_job(conn, "sync", reason="first")
    pause_job(conn, "sync", reason="second")
    info = get_pause_info(conn, "sync")
    assert info["reason"] == "second"


def test_resume_removes_pause(conn):
    pause_job(conn, "deploy")
    removed = resume_job(conn, "deploy")
    assert removed is True
    assert is_paused(conn, "deploy") is False


def test_resume_returns_false_if_not_paused(conn):
    assert resume_job(conn, "ghost") is False


def test_list_paused_jobs_empty(conn):
    assert list_paused_jobs(conn) == []


def test_list_paused_jobs_returns_all(conn):
    pause_job(conn, "alpha")
    pause_job(conn, "beta", reason="testing")
    jobs = list_paused_jobs(conn)
    names = [j["job_name"] for j in jobs]
    assert "alpha" in names
    assert "beta" in names


def test_get_pause_info_returns_none_when_not_paused(conn):
    assert get_pause_info(conn, "missing") is None


def test_get_pause_info_contains_fields(conn):
    pause_job(conn, "cleanup", reason="disk full")
    info = get_pause_info(conn, "cleanup")
    assert info["job_name"] == "cleanup"
    assert info["reason"] == "disk full"
    assert "paused_at" in info


# --- CLI tests ---

def test_cmd_pause_prints_confirmation(conn, capsys):
    with patch("cronjot.cli_pause._get_conn", return_value=conn):
        cmd_pause(_args(job_name="etl", reason=None))
    out = capsys.readouterr().out
    assert "Paused 'etl'" in out


def test_cmd_resume_success(conn, capsys):
    pause_job(conn, "etl")
    with patch("cronjot.cli_pause._get_conn", return_value=conn):
        cmd_resume(_args(job_name="etl"))
    out = capsys.readouterr().out
    assert "Resumed 'etl'" in out


def test_cmd_resume_not_paused_exits(conn):
    with patch("cronjot.cli_pause._get_conn", return_value=conn):
        with pytest.raises(SystemExit) as exc:
            cmd_resume(_args(job_name="ghost"))
    assert exc.value.code == 1


def test_cmd_list_paused_empty(conn, capsys):
    with patch("cronjot.cli_pause._get_conn", return_value=conn):
        cmd_list_paused(_args())
    assert "No jobs" in capsys.readouterr().out


def test_cmd_check_pause_exits_when_paused(conn):
    pause_job(conn, "report")
    with patch("cronjot.cli_pause._get_conn", return_value=conn):
        with pytest.raises(SystemExit) as exc:
            cmd_check_pause(_args(job_name="report"))
    assert exc.value.code == 1


def test_cmd_check_pause_ok_when_not_paused(conn, capsys):
    with patch("cronjot.cli_pause._get_conn", return_value=conn):
        cmd_check_pause(_args(job_name="report"))
    assert "not paused" in capsys.readouterr().out
