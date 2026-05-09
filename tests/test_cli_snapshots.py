"""Tests for cronjot/cli_snapshots.py."""

import argparse
import sqlite3
import sys
import pytest

from cronjot.storage import init_db
from cronjot.snapshots import init_snapshots_schema, take_snapshot
from cronjot.cli_snapshots import (
    cmd_take_snapshot,
    cmd_list_snapshots,
    cmd_show_snapshot,
    cmd_delete_snapshot,
    cmd_compare_snapshots,
)


@pytest.fixture
def db(tmp_path):
    path = str(tmp_path / "test.db")
    conn = sqlite3.connect(path)
    init_db(conn)
    init_snapshots_schema(conn)
    conn.close()
    return path


def _args(db_path, **kwargs):
    ns = argparse.Namespace(db=db_path, **kwargs)
    return ns


def _add_run(db_path, job_name="job", exit_code=0):
    conn = sqlite3.connect(db_path)
    conn.execute(
        "INSERT INTO runs (job_name, started_at, duration_seconds, exit_code, output) "
        "VALUES (?, datetime('now'), 1.0, ?, '')",
        (job_name, exit_code),
    )
    conn.commit()
    conn.close()


def test_cmd_take_snapshot_prints_confirmation(db, capsys):
    _add_run(db)
    cmd_take_snapshot(_args(db, label="baseline"))
    out = capsys.readouterr().out
    assert "baseline" in out
    assert "created" in out


def test_cmd_list_snapshots_empty(db, capsys):
    cmd_list_snapshots(_args(db))
    out = capsys.readouterr().out
    assert "No snapshots" in out


def test_cmd_list_snapshots_shows_labels(db, capsys):
    _add_run(db)
    cmd_take_snapshot(_args(db, label="alpha"))
    cmd_take_snapshot(_args(db, label="beta"))
    cmd_list_snapshots(_args(db))
    out = capsys.readouterr().out
    assert "alpha" in out
    assert "beta" in out


def test_cmd_show_snapshot_not_found_exits(db):
    with pytest.raises(SystemExit):
        cmd_show_snapshot(_args(db, id=999))


def test_cmd_show_snapshot_prints_metrics(db, capsys):
    _add_run(db, "myservice")
    cmd_take_snapshot(_args(db, label="snap1"))
    # id is 1 for first snapshot
    cmd_show_snapshot(_args(db, id=1))
    out = capsys.readouterr().out
    assert "snap1" in out
    assert "myservice" in out


def test_cmd_delete_snapshot_removes_it(db, capsys):
    _add_run(db)
    cmd_take_snapshot(_args(db, label="temp"))
    cmd_delete_snapshot(_args(db, id=1))
    out = capsys.readouterr().out
    assert "deleted" in out


def test_cmd_delete_snapshot_missing_exits(db):
    with pytest.raises(SystemExit):
        cmd_delete_snapshot(_args(db, id=999))


def test_cmd_compare_snapshots_outputs_diff(db, capsys):
    _add_run(db, "etl", exit_code=0)
    cmd_take_snapshot(_args(db, label="before"))
    _add_run(db, "etl", exit_code=0)
    cmd_take_snapshot(_args(db, label="after"))
    cmd_compare_snapshots(_args(db, id_a=1, id_b=2))
    out = capsys.readouterr().out
    assert "etl" in out
    assert "→" in out
