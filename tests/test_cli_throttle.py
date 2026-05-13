"""Tests for cronjot/cli_throttle.py"""

import sqlite3
import argparse
from datetime import datetime, timedelta

import pytest

from cronjot.storage import init_db
from cronjot.throttle import init_throttle_schema, set_throttle
from cronjot.cli_throttle import (
    cmd_set_throttle,
    cmd_remove_throttle,
    cmd_list_throttles,
    cmd_check_throttle,
)


@pytest.fixture
def db(tmp_path):
    path = str(tmp_path / "test.db")
    conn = sqlite3.connect(path)
    init_db(conn)
    init_throttle_schema(conn)
    conn.close()
    return path


def _args(db, **kwargs):
    ns = argparse.Namespace(db=db)
    for k, v in kwargs.items():
        setattr(ns, k, v)
    return ns


def _add_run(db_path, job_name, started_at):
    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT INTO runs (job_name, started_at, finished_at, exit_code, stdout, stderr, duration) "
        "VALUES (?, ?, ?, 0, '', '', 1.0)",
        (job_name, started_at, started_at),
    )
    conn.commit()
    conn.close()


def test_cmd_set_throttle_prints_confirmation(db, capsys):
    cmd_set_throttle(_args(db, job_name="backup", seconds=3600))
    out = capsys.readouterr().out
    assert "backup" in out
    assert "3600" in out


def test_cmd_remove_throttle_success(db, capsys):
    conn = sqlite3.connect(db)
    init_throttle_schema(conn)
    set_throttle(conn, "backup", 3600)
    conn.close()
    cmd_remove_throttle(_args(db, job_name="backup"))
    out = capsys.readouterr().out
    assert "removed" in out.lower()


def test_cmd_remove_throttle_not_found_exits(db):
    with pytest.raises(SystemExit) as exc:
        cmd_remove_throttle(_args(db, job_name="ghost"))
    assert exc.value.code == 1


def test_cmd_list_throttles_empty(db, capsys):
    cmd_list_throttles(_args(db))
    out = capsys.readouterr().out
    assert "No throttle rules" in out


def test_cmd_list_throttles_shows_rules(db, capsys):
    conn = sqlite3.connect(db)
    init_throttle_schema(conn)
    set_throttle(conn, "alpha", 60)
    set_throttle(conn, "beta", 300)
    conn.close()
    cmd_list_throttles(_args(db))
    out = capsys.readouterr().out
    assert "alpha" in out
    assert "beta" in out


def test_cmd_check_throttle_not_throttled(db, capsys):
    cmd_check_throttle(_args(db, job_name="backup"))
    out = capsys.readouterr().out
    assert "OK" in out


def test_cmd_check_throttle_throttled_exits(db):
    conn = sqlite3.connect(db)
    init_throttle_schema(conn)
    set_throttle(conn, "backup", 3600)
    conn.close()
    _add_run(db, "backup", datetime.utcnow().isoformat())
    with pytest.raises(SystemExit) as exc:
        cmd_check_throttle(_args(db, job_name="backup"))
    assert exc.value.code == 2
