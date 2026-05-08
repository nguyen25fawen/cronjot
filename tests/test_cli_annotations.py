"""Tests for cronjot/cli_annotations.py"""

import sqlite3
import argparse
import pytest

from cronjot.storage import init_db, insert_run
from cronjot.annotations import init_annotations_schema, annotate_run
from cronjot.cli_annotations import (
    cmd_annotate,
    cmd_list_annotations,
    cmd_delete_annotation,
    cmd_runs_by_annotation,
)


@pytest.fixture
def db(tmp_path):
    path = str(tmp_path / "test.db")
    conn = sqlite3.connect(path)
    init_db(conn)
    init_annotations_schema(conn)
    conn.close()
    return path


def _add_run(db_path, job_name="job"):
    conn = sqlite3.connect(db_path)
    run_id = insert_run(
        conn,
        job_name=job_name,
        command="echo hi",
        started_at="2024-01-01T00:00:00",
        finished_at="2024-01-01T00:00:01",
        duration=1.0,
        exit_code=0,
        stdout="",
        stderr="",
    )
    conn.close()
    return run_id


def _args(**kwargs):
    ns = argparse.Namespace()
    for k, v in kwargs.items():
        setattr(ns, k, v)
    return ns


def test_cmd_annotate_prints_confirmation(db, capsys):
    run_id = _add_run(db)
    args = _args(db=db, run_id=run_id, key="env", value="prod")
    cmd_annotate(args)
    out = capsys.readouterr().out
    assert "env=prod" in out
    assert str(run_id) in out


def test_cmd_list_annotations_empty(db, capsys):
    run_id = _add_run(db)
    args = _args(db=db, run_id=run_id)
    cmd_list_annotations(args)
    out = capsys.readouterr().out
    assert "No annotations" in out


def test_cmd_list_annotations_shows_entries(db, capsys):
    run_id = _add_run(db)
    conn = sqlite3.connect(db)
    annotate_run(conn, run_id, "version", "2.0")
    conn.close()
    args = _args(db=db, run_id=run_id)
    cmd_list_annotations(args)
    out = capsys.readouterr().out
    assert "version=2.0" in out


def test_cmd_delete_annotation_success(db, capsys):
    run_id = _add_run(db)
    conn = sqlite3.connect(db)
    ann_id = annotate_run(conn, run_id, "k", "v")
    conn.close()
    args = _args(db=db, annotation_id=ann_id)
    cmd_delete_annotation(args)
    out = capsys.readouterr().out
    assert "deleted" in out


def test_cmd_delete_annotation_not_found_exits(db):
    args = _args(db=db, annotation_id=9999)
    with pytest.raises(SystemExit):
        cmd_delete_annotation(args)


def test_cmd_runs_by_annotation_no_match(db, capsys):
    args = _args(db=db, key="missing", value=None)
    cmd_runs_by_annotation(args)
    out = capsys.readouterr().out
    assert "No runs matched" in out


def test_cmd_runs_by_annotation_with_match(db, capsys):
    run_id = _add_run(db)
    conn = sqlite3.connect(db)
    annotate_run(conn, run_id, "env", "prod")
    conn.close()
    args = _args(db=db, key="env", value="prod")
    cmd_runs_by_annotation(args)
    out = capsys.readouterr().out
    assert str(run_id) in out
