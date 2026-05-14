"""Tests for cronjot/audit.py and cronjot/cli_audit.py."""

import time
import pytest
import sqlite3

from cronjot.audit import (
    init_audit_schema,
    record_action,
    fetch_audit_log,
    purge_audit_log,
)
from cronjot.cli_audit import cmd_list_audit, cmd_purge_audit


@pytest.fixture
def conn():
    c = sqlite3.connect(":memory:")
    init_audit_schema(c)
    yield c
    c.close()


def test_init_creates_table(conn):
    tables = [r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()]
    assert "audit_log" in tables


def test_record_action_returns_id(conn):
    aid = record_action(conn, actor="system", action="set_throttle", target="backup")
    assert isinstance(aid, int) and aid > 0


def test_fetch_returns_recorded_entry(conn):
    record_action(conn, actor="alice", action="add_dependency", target="job_a", detail="depends on job_b")
    entries = fetch_audit_log(conn)
    assert len(entries) == 1
    e = entries[0]
    assert e["actor"] == "alice"
    assert e["action"] == "add_dependency"
    assert e["target"] == "job_a"
    assert "job_b" in e["detail"]


def test_fetch_filtered_by_actor(conn):
    record_action(conn, actor="alice", action="set_throttle", target="job_a")
    record_action(conn, actor="bob", action="remove_throttle", target="job_b")
    entries = fetch_audit_log(conn, actor="alice")
    assert len(entries) == 1
    assert entries[0]["actor"] == "alice"


def test_fetch_filtered_by_action(conn):
    record_action(conn, actor="system", action="set_throttle", target="job_a")
    record_action(conn, actor="system", action="remove_throttle", target="job_b")
    entries = fetch_audit_log(conn, action="set_throttle")
    assert all(e["action"] == "set_throttle" for e in entries)
    assert len(entries) == 1


def test_fetch_respects_limit(conn):
    for i in range(10):
        record_action(conn, actor="system", action="ping", target=f"job_{i}")
    entries = fetch_audit_log(conn, limit=3)
    assert len(entries) == 3


def test_fetch_empty_returns_empty_list(conn):
    assert fetch_audit_log(conn) == []


def test_purge_removes_old_entries(conn):
    old_ts = time.time() - 200
    conn.execute(
        "INSERT INTO audit_log (ts, actor, action, target, detail) VALUES (?, ?, ?, ?, ?)",
        (old_ts, "system", "old_action", None, None),
    )
    conn.commit()
    record_action(conn, actor="system", action="new_action")
    deleted = purge_audit_log(conn, time.time() - 100)
    assert deleted == 1
    remaining = fetch_audit_log(conn)
    assert len(remaining) == 1
    assert remaining[0]["action"] == "new_action"


def test_purge_returns_zero_when_nothing_to_delete(conn):
    record_action(conn, actor="system", action="ping")
    deleted = purge_audit_log(conn, time.time() - 9999)
    assert deleted == 0


# --- CLI tests ---

class _Args:
    def __init__(self, **kw):
        self.__dict__.update(kw)


def test_cmd_list_audit_empty(tmp_path, capsys):
    db = str(tmp_path / "test.db")
    args = _Args(db=db, actor=None, action=None, limit=50)
    cmd_list_audit(args)
    out = capsys.readouterr().out
    assert "No audit entries" in out


def test_cmd_purge_audit_prints_count(tmp_path, capsys):
    db = str(tmp_path / "test.db")
    args = _Args(db=db, days=0)
    cmd_purge_audit(args)
    out = capsys.readouterr().out
    assert "Purged" in out
