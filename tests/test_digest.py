"""Tests for the digest builder."""

import pytest
from datetime import datetime, timedelta
from cronjot.digest import build_digest, format_digest_text
from cronjot.storage import init_db, insert_run


@pytest.fixture
def tmp_db(tmp_path):
    db_path = str(tmp_path / "test.db")
    init_db(db_path)
    return db_path


def _add_run(db_path, job_name, exit_code, offset_minutes=0):
    started = datetime.utcnow() - timedelta(minutes=offset_minutes)
    finished = started + timedelta(seconds=1)
    insert_run(
        db_path,
        job_name=job_name,
        command="echo test",
        exit_code=exit_code,
        stdout="ok",
        stderr="" if exit_code == 0 else "error output",
        started_at=started.isoformat(),
        finished_at=finished.isoformat(),
        duration=1.0,
    )


def test_digest_empty_db(tmp_db):
    digest = build_digest(tmp_db, hours=24)
    assert digest["total_runs"] == 0
    assert digest["successes"] == 0
    assert digest["failures"] == 0
    assert digest["failed_jobs"] == []


def test_digest_counts(tmp_db):
    _add_run(tmp_db, "backup", exit_code=0)
    _add_run(tmp_db, "backup", exit_code=0)
    _add_run(tmp_db, "cleanup", exit_code=1)
    digest = build_digest(tmp_db, hours=24)
    assert digest["total_runs"] == 3
    assert digest["successes"] == 2
    assert digest["failures"] == 1
    assert len(digest["failed_jobs"]) == 1
    assert digest["failed_jobs"][0]["job_name"] == "cleanup"


def test_digest_filtered_by_job(tmp_db):
    _add_run(tmp_db, "backup", exit_code=0)
    _add_run(tmp_db, "cleanup", exit_code=1)
    digest = build_digest(tmp_db, hours=24, job_name="backup")
    assert digest["total_runs"] == 1
    assert digest["failures"] == 0


def test_format_digest_text_all_ok(tmp_db):
    _add_run(tmp_db, "backup", exit_code=0)
    digest = build_digest(tmp_db, hours=24)
    text = format_digest_text(digest)
    assert "CronJot Digest" in text
    assert "All jobs completed successfully" in text


def test_format_digest_text_with_failures(tmp_db):
    _add_run(tmp_db, "cleanup", exit_code=2)
    digest = build_digest(tmp_db, hours=24)
    text = format_digest_text(digest)
    assert "Failed Jobs" in text
    assert "cleanup" in text
    assert "error output" in text
