"""Tests for cronjot.dependencies."""

import sqlite3
import pytest

from cronjot.storage import init_db
from cronjot.dependencies import (
    init_dependencies_schema,
    add_dependency,
    remove_dependency,
    list_dependencies,
    check_dependencies_met,
)


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    init_db(c)
    init_dependencies_schema(c)
    yield c
    c.close()


def _add_run(conn, job_name, exit_code=0, started_at="2024-01-01T10:00:00"):
    conn.execute(
        "INSERT INTO runs (job_name, command, exit_code, stdout, stderr, duration_seconds, started_at)"
        " VALUES (?, ?, ?, '', '', 1.0, ?)",
        (job_name, f"echo {job_name}", exit_code, started_at),
    )
    conn.commit()


def test_add_and_list_dependency(conn):
    add_dependency(conn, "job_b", "job_a")
    deps = list_dependencies(conn, "job_b")
    assert deps == ["job_a"]


def test_add_dependency_idempotent(conn):
    add_dependency(conn, "job_b", "job_a")
    add_dependency(conn, "job_b", "job_a")  # should not raise
    assert list_dependencies(conn, "job_b") == ["job_a"]


def test_self_dependency_raises(conn):
    with pytest.raises(ValueError, match="cannot depend on itself"):
        add_dependency(conn, "job_a", "job_a")


def test_remove_dependency(conn):
    add_dependency(conn, "job_b", "job_a")
    remove_dependency(conn, "job_b", "job_a")
    assert list_dependencies(conn, "job_b") == []


def test_list_dependencies_empty(conn):
    assert list_dependencies(conn, "nonexistent") == []


def test_check_dependencies_no_deps_returns_true(conn):
    met, unmet = check_dependencies_met(conn, "standalone_job")
    assert met is True
    assert unmet == []


def test_check_dependencies_met_when_success_run_exists(conn):
    add_dependency(conn, "job_b", "job_a")
    _add_run(conn, "job_a", exit_code=0)
    met, unmet = check_dependencies_met(conn, "job_b")
    assert met is True
    assert unmet == []


def test_check_dependencies_unmet_when_no_successful_run(conn):
    add_dependency(conn, "job_b", "job_a")
    _add_run(conn, "job_a", exit_code=1)  # failure only
    met, unmet = check_dependencies_met(conn, "job_b")
    assert met is False
    assert "job_a" in unmet


def test_check_dependencies_unmet_when_no_run_at_all(conn):
    add_dependency(conn, "job_b", "job_a")
    met, unmet = check_dependencies_met(conn, "job_b")
    assert met is False
    assert "job_a" in unmet


def test_check_dependencies_with_since_filter(conn):
    add_dependency(conn, "job_b", "job_a")
    _add_run(conn, "job_a", exit_code=0, started_at="2024-01-01T08:00:00")
    # Run is before the 'since' window — should be unmet
    met, unmet = check_dependencies_met(conn, "job_b", since="2024-01-01T09:00:00")
    assert met is False
    assert "job_a" in unmet


def test_check_dependencies_with_since_filter_satisfied(conn):
    add_dependency(conn, "job_b", "job_a")
    _add_run(conn, "job_a", exit_code=0, started_at="2024-01-01T10:30:00")
    met, unmet = check_dependencies_met(conn, "job_b", since="2024-01-01T09:00:00")
    assert met is True
    assert unmet == []


def test_multiple_dependencies_partial_unmet(conn):
    add_dependency(conn, "job_c", "job_a")
    add_dependency(conn, "job_c", "job_b")
    _add_run(conn, "job_a", exit_code=0)
    # job_b has no successful run
    met, unmet = check_dependencies_met(conn, "job_c")
    assert met is False
    assert unmet == ["job_b"]
