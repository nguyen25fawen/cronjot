"""Tests for cronjot.deadletter."""

import sqlite3
import time

import pytest

from cronjot.deadletter import (
    init_deadletter_schema,
    enqueue_dead_letter,
    resolve_dead_letter,
    list_dead_letters,
    is_dead_lettered,
)


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    init_deadletter_schema(c)
    yield c
    c.close()


# ---------------------------------------------------------------------------
# schema
# ---------------------------------------------------------------------------

def test_init_creates_table(conn):
    tables = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table'"
    ).fetchall()
    names = [t[0] for t in tables]
    assert "dead_letter_jobs" in names


# ---------------------------------------------------------------------------
# enqueue
# ---------------------------------------------------------------------------

def test_enqueue_returns_id(conn):
    row_id = enqueue_dead_letter(conn, "backup", "5 consecutive failures")
    assert isinstance(row_id, int)
    assert row_id > 0


def test_enqueue_is_idempotent(conn):
    id1 = enqueue_dead_letter(conn, "backup", "reason a")
    id2 = enqueue_dead_letter(conn, "backup", "reason b")
    assert id1 == id2
    rows = conn.execute(
        "SELECT COUNT(*) FROM dead_letter_jobs WHERE job_name = 'backup'"
    ).fetchone()[0]
    assert rows == 1


def test_enqueue_different_jobs(conn):
    id1 = enqueue_dead_letter(conn, "job_a", "reason")
    id2 = enqueue_dead_letter(conn, "job_b", "reason")
    assert id1 != id2


# ---------------------------------------------------------------------------
# is_dead_lettered
# ---------------------------------------------------------------------------

def test_is_dead_lettered_true(conn):
    enqueue_dead_letter(conn, "nightly", "too many failures")
    assert is_dead_lettered(conn, "nightly") is True


def test_is_dead_lettered_false_when_absent(conn):
    assert is_dead_lettered(conn, "unknown_job") is False


# ---------------------------------------------------------------------------
# resolve
# ---------------------------------------------------------------------------

def test_resolve_marks_resolved(conn):
    enqueue_dead_letter(conn, "sync", "failing")
    result = resolve_dead_letter(conn, "sync")
    assert result is True
    assert is_dead_lettered(conn, "sync") is False


def test_resolve_returns_false_when_not_found(conn):
    result = resolve_dead_letter(conn, "nonexistent")
    assert result is False


def test_resolve_sets_resolved_at(conn):
    before = time.time()
    enqueue_dead_letter(conn, "cleanup", "reason")
    resolve_dead_letter(conn, "cleanup")
    row = conn.execute(
        "SELECT resolved_at FROM dead_letter_jobs WHERE job_name = 'cleanup'"
    ).fetchone()
    assert row[0] >= before


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------

def test_list_excludes_resolved_by_default(conn):
    enqueue_dead_letter(conn, "job_a", "r")
    enqueue_dead_letter(conn, "job_b", "r")
    resolve_dead_letter(conn, "job_a")
    items = list_dead_letters(conn)
    names = [i["job_name"] for i in items]
    assert "job_b" in names
    assert "job_a" not in names


def test_list_includes_resolved_when_requested(conn):
    enqueue_dead_letter(conn, "job_a", "r")
    resolve_dead_letter(conn, "job_a")
    items = list_dead_letters(conn, include_resolved=True)
    assert any(i["job_name"] == "job_a" for i in items)


def test_list_empty_db(conn):
    assert list_dead_letters(conn) == []


def test_list_entry_has_expected_keys(conn):
    enqueue_dead_letter(conn, "report", "3 failures")
    item = list_dead_letters(conn)[0]
    for key in ("id", "job_name", "queued_at", "reason", "resolved", "resolved_at"):
        assert key in item
