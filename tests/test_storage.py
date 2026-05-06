"""Tests for cronjot.storage module."""

import os
import tempfile
from datetime import datetime, timezone

import pytest

from cronjot.storage import init_db, insert_run, fetch_runs


@pytest.fixture()
def tmp_db(tmp_path):
    db_path = str(tmp_path / "test.db")
    init_db(db_path)
    return db_path


def test_init_db_creates_file(tmp_path):
    db_path = str(tmp_path / "new.db")
    init_db(db_path)
    assert os.path.exists(db_path)


def test_insert_and_fetch_run(tmp_db):
    started = datetime(2024, 1, 15, 10, 0, 0, tzinfo=timezone.utc)
    finished = datetime(2024, 1, 15, 10, 0, 5, tzinfo=timezone.utc)

    run_id = insert_run(
        job_name="backup",
        started_at=started,
        finished_at=finished,
        exit_code=0,
        output="Done",
        error=None,
        db_path=tmp_db,
    )

    assert run_id == 1
    runs = fetch_runs(db_path=tmp_db)
    assert len(runs) == 1
    assert runs[0]["job_name"] == "backup"
    assert runs[0]["exit_code"] == 0
    assert runs[0]["duration_seconds"] == pytest.approx(5.0)


def test_fetch_runs_filtered_by_job_name(tmp_db):
    now = datetime.now(timezone.utc)
    insert_run("alpha", now, now, 0, None, None, db_path=tmp_db)
    insert_run("beta", now, now, 1, None, "err", db_path=tmp_db)
    insert_run("alpha", now, now, 0, "ok", None, db_path=tmp_db)

    alpha_runs = fetch_runs(job_name="alpha", db_path=tmp_db)
    assert len(alpha_runs) == 2
    assert all(r["job_name"] == "alpha" for r in alpha_runs)


def test_fetch_runs_respects_limit(tmp_db):
    now = datetime.now(timezone.utc)
    for _ in range(10):
        insert_run("job", now, now, 0, None, None, db_path=tmp_db)

    runs = fetch_runs(limit=3, db_path=tmp_db)
    assert len(runs) == 3


def test_insert_run_with_no_finished_at(tmp_db):
    started = datetime.now(timezone.utc)
    run_id = insert_run(
        job_name="partial",
        started_at=started,
        finished_at=None,
        exit_code=None,
        output=None,
        error=None,
        db_path=tmp_db,
    )
    runs = fetch_runs(db_path=tmp_db)
    assert runs[0]["finished_at"] is None
    assert runs[0]["duration_seconds"] is None
