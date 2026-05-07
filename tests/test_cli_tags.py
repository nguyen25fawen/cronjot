"""Tests for cronjot/cli_tags.py"""

import argparse
import pytest

from cronjot.storage import get_connection, init_db
from cronjot.tags import init_tags_schema, tag_run
from cronjot.cli_tags import (
    cmd_tag_run,
    cmd_list_tags,
    cmd_runs_by_tag,
    cmd_run_tags,
)


@pytest.fixture()
def db(tmp_path):
    path = str(tmp_path / "test.db")
    conn = get_connection(path)
    init_db(conn)
    init_tags_schema(conn)
    conn.close()
    return path


def _add_run(db_path, job_name="job"):
    conn = get_connection(db_path)
    cur = conn.execute(
        """
        INSERT INTO runs (job_name, command, started_at, duration_seconds, status, exit_code, output)
        VALUES (?, 'echo hi', datetime('now'), 0.1, 'success', 0, '')
        """,
        (job_name,),
    )
    conn.commit()
    rid = cur.lastrowid
    conn.close()
    return rid


def _args(**kwargs):
    ns = argparse.Namespace(**kwargs)
    return ns


def test_cmd_tag_run_prints_confirmation(db, capsys):
    run_id = _add_run(db)
    cmd_tag_run(_args(db=db, run_id=run_id, tags=["prod", "nightly"]))
    out = capsys.readouterr().out
    assert "prod" in out
    assert "nightly" in out


def test_cmd_list_tags_empty(db, capsys):
    cmd_list_tags(_args(db=db))
    out = capsys.readouterr().out
    assert "No tags" in out


def test_cmd_list_tags_shows_tags(db, capsys):
    run_id = _add_run(db)
    cmd_tag_run(_args(db=db, run_id=run_id, tags=["alpha", "beta"]))
    capsys.readouterr()  # clear
    cmd_list_tags(_args(db=db))
    out = capsys.readouterr().out
    assert "alpha" in out
    assert "beta" in out


def test_cmd_runs_by_tag_no_results(db, capsys):
    cmd_runs_by_tag(_args(db=db, tag="ghost", limit=10))
    out = capsys.readouterr().out
    assert "No runs" in out


def test_cmd_runs_by_tag_shows_matching(db, capsys):
    run_id = _add_run(db, job_name="backup")
    cmd_tag_run(_args(db=db, run_id=run_id, tags=["important"]))
    capsys.readouterr()
    cmd_runs_by_tag(_args(db=db, tag="important", limit=10))
    out = capsys.readouterr().out
    assert "backup" in out


def test_cmd_run_tags_no_tags(db, capsys):
    run_id = _add_run(db)
    cmd_run_tags(_args(db=db, run_id=run_id))
    out = capsys.readouterr().out
    assert "no tags" in out.lower()


def test_cmd_run_tags_shows_tags(db, capsys):
    run_id = _add_run(db)
    cmd_tag_run(_args(db=db, run_id=run_id, tags=["deploy"]))
    capsys.readouterr()
    cmd_run_tags(_args(db=db, run_id=run_id))
    out = capsys.readouterr().out
    assert "deploy" in out
