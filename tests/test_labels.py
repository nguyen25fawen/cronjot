"""Tests for cronjot/labels.py"""

import sqlite3
import pytest

from cronjot.storage import init_db, insert_run
from cronjot.labels import (
    init_labels_schema,
    set_label,
    remove_label,
    fetch_labels,
    fetch_runs_by_label,
)


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    init_db(c)
    init_labels_schema(c)
    return c


def _add_run(conn, job_name="job", exit_code=0):
    return insert_run(conn, job_name, "echo hi", exit_code, 1.0, "out", "")


def test_set_label_returns_id(conn):
    run_id = _add_run(conn)
    label_id = set_label(conn, run_id, "env", "prod")
    assert isinstance(label_id, int)
    assert label_id > 0


def test_fetch_labels_returns_dict(conn):
    run_id = _add_run(conn)
    set_label(conn, run_id, "env", "prod")
    set_label(conn, run_id, "team", "ops")
    labels = fetch_labels(conn, run_id)
    assert labels == {"env": "prod", "team": "ops"}


def test_fetch_labels_empty_for_unlabelled_run(conn):
    run_id = _add_run(conn)
    assert fetch_labels(conn, run_id) == {}


def test_set_label_updates_existing(conn):
    run_id = _add_run(conn)
    set_label(conn, run_id, "env", "staging")
    set_label(conn, run_id, "env", "prod")
    labels = fetch_labels(conn, run_id)
    assert labels["env"] == "prod"


def test_remove_label_returns_true(conn):
    run_id = _add_run(conn)
    set_label(conn, run_id, "env", "prod")
    result = remove_label(conn, run_id, "env")
    assert result is True
    assert fetch_labels(conn, run_id) == {}


def test_remove_label_missing_returns_false(conn):
    run_id = _add_run(conn)
    result = remove_label(conn, run_id, "nonexistent")
    assert result is False


def test_fetch_runs_by_label_key_only(conn):
    r1 = _add_run(conn, "job_a")
    r2 = _add_run(conn, "job_b")
    _add_run(conn, "job_c")
    set_label(conn, r1, "env", "prod")
    set_label(conn, r2, "env", "staging")
    run_ids = fetch_runs_by_label(conn, "env")
    assert set(run_ids) == {r1, r2}


def test_fetch_runs_by_label_key_and_value(conn):
    r1 = _add_run(conn, "job_a")
    r2 = _add_run(conn, "job_b")
    set_label(conn, r1, "env", "prod")
    set_label(conn, r2, "env", "staging")
    run_ids = fetch_runs_by_label(conn, "env", "prod")
    assert run_ids == [r1]


def test_fetch_runs_by_label_respects_limit(conn):
    for _ in range(5):
        rid = _add_run(conn)
        set_label(conn, rid, "env", "prod")
    run_ids = fetch_runs_by_label(conn, "env", limit=3)
    assert len(run_ids) == 3
