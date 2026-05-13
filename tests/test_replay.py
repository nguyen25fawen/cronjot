"""Tests for cronjot.replay and cronjot.cli_replay."""

import sqlite3
import argparse
import pytest
from unittest.mock import patch, MagicMock

from cronjot.storage import init_db, insert_run
from cronjot.replay import get_run_by_id, replay_run, replay_latest
from cronjot.cli_replay import cmd_replay_by_id, cmd_replay_latest, build_replay_parser


@pytest.fixture
def conn(tmp_path):
    db_path = str(tmp_path / "test.db")
    c = sqlite3.connect(db_path)
    c.row_factory = sqlite3.Row
    init_db(c)
    yield c, db_path
    c.close()


def _add_run(conn, job_name="myjob", command="echo hi", status="success", exit_code=0):
    insert_run(conn, job_name=job_name, command=command, status=status,
               exit_code=exit_code, stdout="hi", stderr="", duration_seconds=0.1)
    cur = conn.execute("SELECT id FROM runs ORDER BY id DESC LIMIT 1")
    return cur.fetchone()[0]


# --- Unit tests for replay module ---

def test_get_run_by_id_returns_dict(conn):
    c, _ = conn
    run_id = _add_run(c)
    row = get_run_by_id(c, run_id)
    assert row is not None
    assert row["job_name"] == "myjob"
    assert row["command"] == "echo hi"


def test_get_run_by_id_missing_returns_none(conn):
    c, _ = conn
    assert get_run_by_id(c, 9999) is None


def test_replay_run_raises_for_missing_id(conn):
    c, db_path = conn
    with pytest.raises(ValueError, match="No run found with id=999"):
        replay_run(c, run_id=999, db_path=db_path)


def test_replay_run_calls_run_job(conn):
    c, db_path = conn
    run_id = _add_run(c, command="echo replay")
    fake_result = {"job_name": "myjob", "command": "echo replay",
                   "exit_code": 0, "stdout": "replay", "stderr": "", "duration_seconds": 0.05}
    with patch("cronjot.replay.run_job", return_value=fake_result) as mock_run:
        result = replay_run(c, run_id=run_id, db_path=db_path)
    mock_run.assert_called_once_with(job_name="myjob", command="echo replay", db_path=db_path)
    assert result["exit_code"] == 0


def test_replay_latest_raises_when_no_runs(conn):
    c, db_path = conn
    with pytest.raises(ValueError, match="No runs found for job 'ghost'"):
        replay_latest(c, job_name="ghost", db_path=db_path)


def test_replay_latest_uses_most_recent(conn):
    c, db_path = conn
    _add_run(c, command="echo first")
    _add_run(c, command="echo second")
    fake_result = {"job_name": "myjob", "command": "echo second",
                   "exit_code": 0, "stdout": "", "stderr": "", "duration_seconds": 0.02}
    with patch("cronjot.replay.run_job", return_value=fake_result) as mock_run:
        replay_latest(c, job_name="myjob", db_path=db_path)
    _, kwargs = mock_run.call_args
    assert mock_run.call_args[1]["command"] == "echo second"


# --- CLI tests ---

@pytest.fixture
def db(tmp_path):
    db_path = str(tmp_path / "cli.db")
    c = sqlite3.connect(db_path)
    c.row_factory = sqlite3.Row
    init_db(c)
    yield c, db_path
    c.close()


def _args(**kwargs):
    base = {"db": "cronjot.db"}
    base.update(kwargs)
    return argparse.Namespace(**base)


def test_cmd_replay_by_id_success(db, capsys):
    c, db_path = db
    run_id = _add_run(c)
    fake = {"job_name": "myjob", "command": "echo hi", "exit_code": 0,
            "stdout": "hi", "stderr": "", "duration_seconds": 0.1}
    with patch("cronjot.cli_replay._get_conn", return_value=c), \
         patch("cronjot.cli_replay.replay_run", return_value=fake):
        cmd_replay_by_id(_args(db=db_path, run_id=run_id))
    out = capsys.readouterr().out
    assert "SUCCESS" in out
    assert "myjob" in out


def test_cmd_replay_by_id_missing_exits(db, capsys):
    c, db_path = db
    with patch("cronjot.cli_replay._get_conn", return_value=c), \
         patch("cronjot.cli_replay.replay_run", side_effect=ValueError("No run found with id=999")):
        with pytest.raises(SystemExit) as exc:
            cmd_replay_by_id(_args(db=db_path, run_id=999))
    assert exc.value.code == 1


def test_cmd_replay_latest_success(db, capsys):
    c, db_path = db
    _add_run(c)
    fake = {"job_name": "myjob", "command": "echo hi", "exit_code": 0,
            "stdout": "hi", "stderr": "", "duration_seconds": 0.2}
    with patch("cronjot.cli_replay._get_conn", return_value=c), \
         patch("cronjot.cli_replay.replay_latest", return_value=fake):
        cmd_replay_latest(_args(db=db_path, job_name="myjob"))
    out = capsys.readouterr().out
    assert "myjob" in out
    assert "SUCCESS" in out


def test_build_replay_parser_returns_parser():
    parser = build_replay_parser()
    assert isinstance(parser, argparse.ArgumentParser)
