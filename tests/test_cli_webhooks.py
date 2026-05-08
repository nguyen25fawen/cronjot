"""Tests for cronjot.cli_webhooks."""

import sqlite3
import argparse
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from cronjot.storage import get_connection, init_db, insert_run
from cronjot.cli_webhooks import cmd_webhook_test, build_webhooks_parser


@pytest.fixture()
def db(tmp_path):
    path = str(tmp_path / "test.db")
    conn = get_connection(path)
    init_db(conn)
    return path


def _add_run(db_path, job_name="myjob", exit_code=0):
    conn = get_connection(db_path)
    insert_run(conn, job_name=job_name, started_at="2024-06-01T10:00:00",
               duration_seconds=5.0, exit_code=exit_code, output="ok")


def _args(**kwargs):
    defaults = dict(db="cronjot.db", job_name="myjob", url="http://hook",
                    secret=None, verbose=False)
    defaults.update(kwargs)
    return SimpleNamespace(**defaults)


def test_cmd_webhook_test_no_runs_exits(db, capsys):
    args = _args(db=db)
    with pytest.raises(SystemExit) as exc:
        cmd_webhook_test(args)
    assert exc.value.code == 1


def test_cmd_webhook_test_success(db, capsys):
    _add_run(db)
    args = _args(db=db)
    with patch("cronjot.cli_webhooks.send_webhook") as mock_send:
        cmd_webhook_test(args)
    mock_send.assert_called_once()
    out = capsys.readouterr().out
    assert "delivered" in out


def test_cmd_webhook_test_verbose_prints_payload(db, capsys):
    _add_run(db)
    args = _args(db=db, verbose=True)
    with patch("cronjot.cli_webhooks.send_webhook"):
        cmd_webhook_test(args)
    out = capsys.readouterr().out
    assert "job_name" in out


def test_cmd_webhook_test_error_exits(db, capsys):
    _add_run(db)
    args = _args(db=db)
    with patch("cronjot.cli_webhooks.send_webhook", side_effect=RuntimeError("boom")):
        with pytest.raises(SystemExit) as exc:
            cmd_webhook_test(args)
    assert exc.value.code == 1
    assert "boom" in capsys.readouterr().err


def test_build_webhooks_parser_registers_subcommand():
    parser = argparse.ArgumentParser()
    sub = parser.add_subparsers()
    build_webhooks_parser(sub)
    args = parser.parse_args(["webhook-test", "myjob", "http://example.com"])
    assert args.job_name == "myjob"
    assert args.url == "http://example.com"
    assert args.secret is None
