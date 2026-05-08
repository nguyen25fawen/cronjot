"""Tests for cronjot/annotations.py"""

import sqlite3
import pytest

from cronjot.storage import init_db, insert_run
from cronjot.annotations import (
    init_annotations_schema,
    annotate_run,
    fetch_annotations,
    delete_annotation,
    fetch_runs_by_annotation,
)


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    init_db(c)
    init_annotations_schema(c)
    yield c
    c.close()


def _add_run(conn, job_name="job", exit_code=0):
    return insert_run(
        conn,
        job_name=job_name,
        command="echo hi",
        started_at="2024-01-01T00:00:00",
        finished_at="2024-01-01T00:00:01",
        duration=1.0,
        exit_code=exit_code,
        stdout="",
        stderr="",
    )


def test_annotate_run_and_fetch(conn):
    run_id = _add_run(conn)
    ann_id = annotate_run(conn, run_id, "env", "production")
    assert ann_id is not None
    annotations = fetch_annotations(conn, run_id)
    assert len(annotations) == 1
    assert annotations[0]["key"] == "env"
    assert annotations[0]["value"] == "production"
    assert annotations[0]["run_id"] == run_id


def test_fetch_annotations_empty(conn):
    run_id = _add_run(conn)
    assert fetch_annotations(conn, run_id) == []


def test_multiple_annotations_on_same_run(conn):
    run_id = _add_run(conn)
    annotate_run(conn, run_id, "env", "staging")
    annotate_run(conn, run_id, "version", "1.2.3")
    annotations = fetch_annotations(conn, run_id)
    assert len(annotations) == 2
    keys = {a["key"] for a in annotations}
    assert keys == {"env", "version"}


def test_delete_annotation(conn):
    run_id = _add_run(conn)
    ann_id = annotate_run(conn, run_id, "env", "production")
    removed = delete_annotation(conn, ann_id)
    assert removed is True
    assert fetch_annotations(conn, run_id) == []


def test_delete_nonexistent_annotation(conn):
    removed = delete_annotation(conn, 9999)
    assert removed is False


def test_fetch_runs_by_annotation_key_only(conn):
    run1 = _add_run(conn, job_name="job_a")
    run2 = _add_run(conn, job_name="job_b")
    _add_run(conn, job_name="job_c")
    annotate_run(conn, run1, "env", "prod")
    annotate_run(conn, run2, "env", "staging")
    run_ids = fetch_runs_by_annotation(conn, "env")
    assert set(run_ids) == {run1, run2}


def test_fetch_runs_by_annotation_key_and_value(conn):
    run1 = _add_run(conn, job_name="job_a")
    run2 = _add_run(conn, job_name="job_b")
    annotate_run(conn, run1, "env", "prod")
    annotate_run(conn, run2, "env", "staging")
    run_ids = fetch_runs_by_annotation(conn, "env", "prod")
    assert run_ids == [run1]


def test_fetch_runs_by_annotation_no_match(conn):
    run_ids = fetch_runs_by_annotation(conn, "nonexistent")
    assert run_ids == []
