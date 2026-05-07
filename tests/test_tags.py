"""Tests for cronjot/tags.py"""

import sqlite3
import pytest

from cronjot.storage import get_connection, init_db
from cronjot.tags import (
    init_tags_schema,
    ensure_tag,
    tag_run,
    fetch_runs_by_tag,
    list_tags,
    get_tags_for_run,
)


@pytest.fixture()
def conn(tmp_path):
    db_path = str(tmp_path / "test.db")
    c = get_connection(db_path)
    init_db(c)
    init_tags_schema(c)
    yield c
    c.close()


def _add_run(conn, job_name="job", status="success", exit_code=0):
    cur = conn.execute(
        """
        INSERT INTO runs (job_name, command, started_at, duration_seconds, status, exit_code, output)
        VALUES (?, 'echo hi', datetime('now'), 0.1, ?, ?, '')
        """,
        (job_name, status, exit_code),
    )
    conn.commit()
    return cur.lastrowid


def test_ensure_tag_creates_new(conn):
    tag_id = ensure_tag(conn, "nightly")
    assert isinstance(tag_id, int)
    assert tag_id > 0


def test_ensure_tag_idempotent(conn):
    id1 = ensure_tag(conn, "nightly")
    id2 = ensure_tag(conn, "nightly")
    assert id1 == id2


def test_tag_run_and_get_tags(conn):
    run_id = _add_run(conn)
    tag_run(conn, run_id, ["prod", "daily"])
    tags = get_tags_for_run(conn, run_id)
    assert sorted(tags) == ["daily", "prod"]


def test_tag_run_idempotent(conn):
    run_id = _add_run(conn)
    tag_run(conn, run_id, ["prod"])
    tag_run(conn, run_id, ["prod"])  # should not raise or duplicate
    tags = get_tags_for_run(conn, run_id)
    assert tags.count("prod") == 1


def test_fetch_runs_by_tag(conn):
    r1 = _add_run(conn, job_name="backup")
    r2 = _add_run(conn, job_name="report")
    _add_run(conn, job_name="cleanup")
    tag_run(conn, r1, ["important"])
    tag_run(conn, r2, ["important"])

    rows = fetch_runs_by_tag(conn, "important")
    ids = [row["id"] for row in rows]
    assert r1 in ids
    assert r2 in ids
    assert len(ids) == 2


def test_fetch_runs_by_tag_respects_limit(conn):
    for _ in range(5):
        rid = _add_run(conn)
        tag_run(conn, rid, ["batch"])
    rows = fetch_runs_by_tag(conn, "batch", limit=3)
    assert len(rows) == 3


def test_fetch_runs_by_nonexistent_tag_returns_empty(conn):
    rows = fetch_runs_by_tag(conn, "ghost")
    assert rows == []


def test_list_tags(conn):
    ensure_tag(conn, "zebra")
    ensure_tag(conn, "alpha")
    ensure_tag(conn, "middle")
    assert list_tags(conn) == ["alpha", "middle", "zebra"]


def test_get_tags_for_untagged_run(conn):
    run_id = _add_run(conn)
    assert get_tags_for_run(conn, run_id) == []
