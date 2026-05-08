"""Tests for cronjot/export.py"""

import csv
import io
import json
import sqlite3
import time
import pytest

from cronjot.storage import init_db, insert_run
from cronjot.export import export_runs


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    c.row_factory = sqlite3.Row
    init_db(c)
    yield c
    c.close()


def _add_run(conn, job_name="backup", exit_code=0, output="ok"):
    insert_run(conn, job_name=job_name, started_at=time.time(),
               duration_seconds=1.0, exit_code=exit_code, output=output)


# ---------------------------------------------------------------------------
# JSON export
# ---------------------------------------------------------------------------

def test_export_json_empty(conn):
    result = export_runs(conn, fmt="json")
    data = json.loads(result)
    assert data == []


def test_export_json_returns_all_fields(conn):
    _add_run(conn, job_name="sync", exit_code=0, output="done")
    result = export_runs(conn, fmt="json")
    data = json.loads(result)
    assert len(data) == 1
    row = data[0]
    assert row["job_name"] == "sync"
    assert row["exit_code"] == 0
    assert row["output"] == "done"
    assert "started_at" in row
    assert "duration_seconds" in row


def test_export_json_filtered_by_job(conn):
    _add_run(conn, job_name="backup")
    _add_run(conn, job_name="sync")
    result = export_runs(conn, fmt="json", job_name="backup")
    data = json.loads(result)
    assert all(r["job_name"] == "backup" for r in data)
    assert len(data) == 1


# ---------------------------------------------------------------------------
# CSV export
# ---------------------------------------------------------------------------

def test_export_csv_empty(conn):
    result = export_runs(conn, fmt="csv")
    assert result == ""


def test_export_csv_has_header_and_row(conn):
    _add_run(conn, job_name="cleanup", exit_code=1, output="err")
    result = export_runs(conn, fmt="csv")
    reader = csv.DictReader(io.StringIO(result))
    rows = list(reader)
    assert len(rows) == 1
    assert rows[0]["job_name"] == "cleanup"
    assert rows[0]["exit_code"] == "1"
    assert rows[0]["output"] == "err"


def test_export_csv_respects_limit(conn):
    for _ in range(5):
        _add_run(conn)
    result = export_runs(conn, fmt="csv", limit=3)
    reader = csv.DictReader(io.StringIO(result))
    assert len(list(reader)) == 3


# ---------------------------------------------------------------------------
# Invalid format
# ---------------------------------------------------------------------------

def test_export_invalid_format_raises(conn):
    with pytest.raises(ValueError, match="Unsupported export format"):
        export_runs(conn, fmt="xml")  # type: ignore
