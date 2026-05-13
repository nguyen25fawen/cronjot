"""Tests for cronjot.circuit_breaker."""

import sqlite3
import time
import pytest

from cronjot.circuit_breaker import (
    init_circuit_breaker_schema,
    get_circuit_state,
    record_failure,
    record_success,
    is_open,
    reset_circuit,
)


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    init_circuit_breaker_schema(c)
    yield c
    c.close()


def test_init_creates_table(conn):
    tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    assert ("circuit_breakers",) in tables


def test_get_state_returns_defaults_for_unknown_job(conn):
    state = get_circuit_state(conn, "nonexistent")
    assert state["state"] == "closed"
    assert state["failure_count"] == 0
    assert state["opened_at"] is None


def test_record_failure_increments_count(conn):
    state = record_failure(conn, "backup", threshold=3)
    assert state["failure_count"] == 1
    assert state["state"] == "closed"


def test_record_failure_opens_circuit_at_threshold(conn):
    for _ in range(3):
        state = record_failure(conn, "backup", threshold=3)
    assert state["state"] == "open"
    assert state["opened_at"] is not None


def test_record_success_resets_circuit(conn):
    record_failure(conn, "backup", threshold=3)
    record_failure(conn, "backup", threshold=3)
    record_success(conn, "backup")
    state = get_circuit_state(conn, "backup")
    assert state["state"] == "closed"
    assert state["failure_count"] == 0
    assert state["opened_at"] is None


def test_is_open_returns_false_when_closed(conn):
    assert is_open(conn, "backup") is False


def test_is_open_returns_true_when_circuit_open(conn):
    for _ in range(3):
        record_failure(conn, "backup", threshold=3)
    assert is_open(conn, "backup", cooldown_seconds=300) is True


def test_is_open_returns_false_after_cooldown(conn):
    for _ in range(3):
        record_failure(conn, "backup", threshold=3)
    # Manually set opened_at to far in the past
    conn.execute(
        "UPDATE circuit_breakers SET opened_at = ? WHERE job_name = ?",
        (time.time() - 400, "backup"),
    )
    conn.commit()
    assert is_open(conn, "backup", cooldown_seconds=300) is False


def test_reset_circuit_removes_record(conn):
    record_failure(conn, "backup", threshold=1)
    reset_circuit(conn, "backup")
    state = get_circuit_state(conn, "backup")
    assert state["state"] == "closed"
    assert state["failure_count"] == 0


def test_multiple_jobs_are_independent(conn):
    for _ in range(3):
        record_failure(conn, "job_a", threshold=3)
    record_failure(conn, "job_b", threshold=3)
    assert is_open(conn, "job_a") is True
    assert is_open(conn, "job_b") is False
