"""Tests for cronjot.pinned and cronjot.cli_pinned."""

import sqlite3
import pytest

from cronjot.storage import init_db
from cronjot.pinned import (
    init_pinned_schema,
    pin_run,
    unpin_run,
    is_pinned,
    list_pinned_runs,
)


@pytest.fixture()
def conn():
    c = sqlite3.connect(":memory:")
    init_db(c)
    init_pinned_schema(c)
    return c


def _add_run(conn, job_name="backup", exit_code=0, started_at="2024-01-01T00:00:00"):
    cur = conn.execute(
        "INSERT INTO runs (job_name, exit_code, stdout, stderr, started_at, duration)"
        " VALUES (?, ?, '', '', ?, 1.0)",
        (job_name, exit_code, started_at),
    )
    conn.commit()
    return cur.lastrowid


def test_pin_run_returns_id(conn):
    run_id = _add_run(conn)
    pin_id = pin_run(conn, run_id)
    assert isinstance(pin_id, int)
    assert pin_id > 0


def test_is_pinned_true_after_pin(conn):
    run_id = _add_run(conn)
    pin_run(conn, run_id)
    assert is_pinned(conn, run_id) is True


def test_is_pinned_false_before_pin(conn):
    run_id = _add_run(conn)
    assert is_pinned(conn, run_id) is False


def test_pin_run_missing_id_raises(conn):
    with pytest.raises(ValueError, match="does not exist"):
        pin_run(conn, 9999)


def test_unpin_run_returns_true(conn):
    run_id = _add_run(conn)
    pin_run(conn, run_id)
    result = unpin_run(conn, run_id)
    assert result is True
    assert is_pinned(conn, run_id) is False


def test_unpin_run_not_pinned_returns_false(conn):
    run_id = _add_run(conn)
    result = unpin_run(conn, run_id)
    assert result is False


def test_pin_idempotent_updates_label(conn):
    run_id = _add_run(conn)
    pin_run(conn, run_id, label="first")
    pin_run(conn, run_id, label="second")
    rows = list_pinned_runs(conn)
    assert len(rows) == 1
    assert rows[0]["label"] == "second"


def test_list_pinned_runs_empty(conn):
    assert list_pinned_runs(conn) == []


def test_list_pinned_runs_returns_metadata(conn):
    run_id = _add_run(conn, job_name="sync", exit_code=0)
    pin_run(conn, run_id, label="important")
    rows = list_pinned_runs(conn)
    assert len(rows) == 1
    row = rows[0]
    assert row["run_id"] == run_id
    assert row["job_name"] == "sync"
    assert row["label"] == "important"
    assert row["exit_code"] == 0


def test_list_pinned_runs_multiple(conn):
    id1 = _add_run(conn, job_name="job_a")
    id2 = _add_run(conn, job_name="job_b")
    pin_run(conn, id1)
    pin_run(conn, id2, label="b-label")
    rows = list_pinned_runs(conn)
    assert len(rows) == 2
    job_names = {r["job_name"] for r in rows}
    assert job_names == {"job_a", "job_b"}
