"""Tests for cronjot/metrics.py and cronjot/cli_metrics.py."""

from __future__ import annotations

import json
import sqlite3
from argparse import Namespace
from unittest.mock import patch

import pytest

from cronjot.storage import init_db
from cronjot.metrics import get_job_metrics, get_all_job_metrics, format_metrics_text
from cronjot.cli_metrics import cmd_metrics


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    init_db(c)
    yield c
    c.close()


def _add_run(conn, job_name, exit_code=0, duration=1.0, started_at="2024-01-01T00:00:00"):
    conn.execute(
        "INSERT INTO runs (job_name, command, exit_code, duration_seconds, started_at, output)"
        " VALUES (?, ?, ?, ?, ?, ?)",
        (job_name, "echo test", exit_code, duration, started_at, ""),
    )
    conn.commit()


def test_no_runs_returns_empty_metrics(conn):
    m = get_job_metrics(conn, "missing_job")
    assert m["total_runs"] == 0
    assert m["job_name"] == "missing_job"


def test_metrics_counts_successes_and_failures(conn):
    _add_run(conn, "backup", exit_code=0, duration=2.0)
    _add_run(conn, "backup", exit_code=0, duration=4.0)
    _add_run(conn, "backup", exit_code=1, duration=1.0)

    m = get_job_metrics(conn, "backup")
    assert m["total_runs"] == 3
    assert m["successes"] == 2
    assert m["failures"] == 1
    assert m["success_rate"] == pytest.approx(66.67, abs=0.01)


def test_metrics_duration_aggregates(conn):
    _add_run(conn, "sync", duration=1.0)
    _add_run(conn, "sync", duration=3.0)

    m = get_job_metrics(conn, "sync")
    assert m["min_duration"] == pytest.approx(1.0)
    assert m["max_duration"] == pytest.approx(3.0)
    assert m["avg_duration"] == pytest.approx(2.0)


def test_get_all_job_metrics_returns_each_job(conn):
    _add_run(conn, "job_a")
    _add_run(conn, "job_b")
    _add_run(conn, "job_b", exit_code=1)

    all_m = get_all_job_metrics(conn)
    names = [m["job_name"] for m in all_m]
    assert "job_a" in names
    assert "job_b" in names


def test_format_metrics_text_empty():
    text = format_metrics_text([])
    assert "No job metrics" in text


def test_format_metrics_text_contains_job_name(conn):
    _add_run(conn, "nightly")
    m = get_all_job_metrics(conn)
    text = format_metrics_text(m)
    assert "nightly" in text
    assert "Total runs" in text


def test_cmd_metrics_text_output(conn, capsys):
    _add_run(conn, "report")
    args = Namespace(db=":memory:", job=None, format="text")
    with patch("cronjot.cli_metrics.get_connection", return_value=conn), \
         patch("cronjot.cli_metrics.init_db"):
        cmd_metrics(args)
    captured = capsys.readouterr()
    assert "report" in captured.out


def test_cmd_metrics_json_output(conn, capsys):
    _add_run(conn, "report", exit_code=0, duration=5.0)
    args = Namespace(db=":memory:", job="report", format="json")
    with patch("cronjot.cli_metrics.get_connection", return_value=conn), \
         patch("cronjot.cli_metrics.init_db"):
        cmd_metrics(args)
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert isinstance(data, list)
    assert data[0]["job_name"] == "report"
    assert data[0]["total_runs"] == 1
