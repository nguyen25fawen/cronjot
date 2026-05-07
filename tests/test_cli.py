"""Tests for the cronjot CLI."""

import os
import pytest
from unittest.mock import patch, MagicMock

from cronjot.cli import build_parser, cmd_run, cmd_history, cmd_digest
from cronjot.storage import init_db, insert_run


@pytest.fixture
def db(tmp_path):
    path = str(tmp_path / "test.db")
    init_db(path)
    return path


def _make_args(**kwargs):
    """Build a simple namespace for CLI arg simulation."""
    defaults = {"db": None, "name": "", "limit": 20, "hours": 24,
                "email": "", "smtp_host": "", "smtp_port": "25", "slack_webhook": ""}
    defaults.update(kwargs)
    return MagicMock(**defaults)


# --- cmd_run ---

def test_cmd_run_success(db):
    args = _make_args(db=db, name="echo-job", command="echo hello")
    cmd_run(args)  # should not raise


def test_cmd_run_failure_exits(db):
    args = _make_args(db=db, name="fail-job", command="exit 1")
    with pytest.raises(SystemExit) as exc_info:
        cmd_run(args)
    assert exc_info.value.code == 1


# --- cmd_history ---

def test_cmd_history_empty(db, capsys):
    args = _make_args(db=db, name="", limit=10)
    cmd_history(args)
    out = capsys.readouterr().out
    assert "No runs found" in out


def test_cmd_history_shows_runs(db, capsys):
    insert_run(db, job_name="backup", command="tar -czf /tmp/b.tgz /etc",
               exit_code=0, stdout="", stderr="", duration_seconds=1.5)
    args = _make_args(db=db, name="", limit=10)
    cmd_history(args)
    out = capsys.readouterr().out
    assert "backup" in out
    assert "OK" in out


def test_cmd_history_filter_by_name(db, capsys):
    insert_run(db, job_name="job-a", command="true", exit_code=0,
               stdout="", stderr="", duration_seconds=0.1)
    insert_run(db, job_name="job-b", command="false", exit_code=1,
               stdout="", stderr="err", duration_seconds=0.2)
    args = _make_args(db=db, name="job-a", limit=10)
    cmd_history(args)
    out = capsys.readouterr().out
    assert "job-a" in out
    assert "job-b" not in out


# --- cmd_digest ---

def test_cmd_digest_prints_text(db, capsys):
    insert_run(db, job_name="nightly", command="./nightly.sh", exit_code=0,
               stdout="done", stderr="", duration_seconds=10.0)
    args = _make_args(db=db, name="", hours=24)
    cmd_digest(args)
    out = capsys.readouterr().out
    assert "nightly" in out or "Digest" in out or "run" in out.lower()


def test_cmd_digest_sends_email(db, capsys):
    args = _make_args(db=db, name="", hours=24, email="ops@example.com",
                      smtp_host="localhost", smtp_port="25")
    with patch("cronjot.cli.send_email") as mock_email:
        cmd_digest(args)
        mock_email.assert_called_once()
        call_kwargs = mock_email.call_args
        assert call_kwargs[1]["to"] == "ops@example.com" or call_kwargs[0][0] == "ops@example.com"


def test_cmd_digest_sends_slack(db, capsys):
    args = _make_args(db=db, name="", hours=24,
                      slack_webhook="https://hooks.slack.com/test")
    with patch("cronjot.cli.send_slack") as mock_slack:
        cmd_digest(args)
        mock_slack.assert_called_once()


# --- parser ---

def test_parser_run_subcommand():
    parser = build_parser()
    args = parser.parse_args(["run", "my-job", "echo hi"])
    assert args.name == "my-job"
    assert args.command == "echo hi"


def test_parser_history_defaults():
    parser = build_parser()
    args = parser.parse_args(["history"])
    assert args.limit == 20


def test_parser_digest_hours():
    parser = build_parser()
    args = parser.parse_args(["digest", "--hours", "48"])
    assert args.hours == 48
