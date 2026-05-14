"""Tests for cronjot/cli_labels.py"""

import sqlite3
import argparse
import pytest

from cronjot.storage import init_db, insert_run
from cronjot.labels import init_labels_schema, set_label
from cronjot.cli_labels import (
    cmd_set_label,
    cmd_remove_label,
    cmd_list_labels,
    cmd_runs_by_label,
)


@pytest.fixture
def db(tmp_path):
    path = str(tmp_path / "test.db")
    conn = sqlite3.connect(path)
    init_db(conn)
    init_labels_schema(conn)
    conn.close()
    return path


def _add_run(db_path, job_name="job"):
    conn = sqlite3.connect(db_path)
    init_db(conn)
    rid = insert_run(conn, job_name, "echo hi", 0, 1.0, "out", "")
    conn.close()
    return rid


def _args(**kwargs):
    base = {"db": None}
    base.update(kwargs)
    return argparse.Namespace(**base)


def test_cmd_set_label_prints_confirmation(db, capsys):
    rid = _add_run(db)
    cmd_set_label(_args(db=db, run_id=rid, key="env", value="prod"))
    out = capsys.readouterr().out
    assert "Label set" in out
    assert "env=prod" in out


def test_cmd_list_labels_empty(db, capsys):
    rid = _add_run(db)
    cmd_list_labels(_args(db=db, run_id=rid))
    out = capsys.readouterr().out
    assert "No labels" in out


def test_cmd_list_labels_shows_labels(db, capsys):
    rid = _add_run(db)
    conn = sqlite3.connect(db)
    init_labels_schema(conn)
    set_label(conn, rid, "region", "us-east-1")
    conn.close()
    cmd_list_labels(_args(db=db, run_id=rid))
    out = capsys.readouterr().out
    assert "region=us-east-1" in out


def test_cmd_remove_label_success(db, capsys):
    rid = _add_run(db)
    conn = sqlite3.connect(db)
    init_labels_schema(conn)
    set_label(conn, rid, "env", "prod")
    conn.close()
    cmd_remove_label(_args(db=db, run_id=rid, key="env"))
    out = capsys.readouterr().out
    assert "removed" in out


def test_cmd_remove_label_missing_exits(db):
    rid = _add_run(db)
    with pytest.raises(SystemExit):
        cmd_remove_label(_args(db=db, run_id=rid, key="ghost"))


def test_cmd_runs_by_label_no_match(db, capsys):
    cmd_runs_by_label(_args(db=db, key="env", value=None, limit=100))
    out = capsys.readouterr().out
    assert "No runs matched" in out


def test_cmd_runs_by_label_with_match(db, capsys):
    rid = _add_run(db)
    conn = sqlite3.connect(db)
    init_labels_schema(conn)
    set_label(conn, rid, "env", "prod")
    conn.close()
    cmd_runs_by_label(_args(db=db, key="env", value="prod", limit=100))
    out = capsys.readouterr().out
    assert str(rid) in out
