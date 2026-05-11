"""Tests for cronjot.templates rendering helpers."""

import pytest
from cronjot.templates import render_digest, render_run_line, render_alert


# ---------------------------------------------------------------------------
# render_digest
# ---------------------------------------------------------------------------

def test_render_digest_contains_generated_at():
    summary = {
        "generated_at": "2024-01-15T12:00:00",
        "total_jobs": 3,
        "total_runs": 10,
        "body": "some body text",
    }
    result = render_digest(summary)
    assert "2024-01-15T12:00:00" in result


def test_render_digest_contains_totals():
    summary = {
        "generated_at": "2024-01-15T12:00:00",
        "total_jobs": 5,
        "total_runs": 42,
        "body": "",
    }
    result = render_digest(summary)
    assert "5" in result
    assert "42" in result


def test_render_digest_contains_body():
    summary = {
        "generated_at": "now",
        "total_jobs": 1,
        "total_runs": 1,
        "body": "UNIQUE_BODY_CONTENT_XYZ",
    }
    result = render_digest(summary)
    assert "UNIQUE_BODY_CONTENT_XYZ" in result


def test_render_digest_custom_template():
    summary = {"generated_at": "T", "total_jobs": 1, "total_runs": 2, "body": "B"}
    result = render_digest(summary, template="jobs={total_jobs} runs={total_runs}")
    assert result == "jobs=1 runs=2"


def test_render_digest_missing_keys_use_defaults():
    # Should not raise even with empty summary
    result = render_digest({})
    assert isinstance(result, str)


# ---------------------------------------------------------------------------
# render_run_line
# ---------------------------------------------------------------------------

def test_render_run_line_success():
    run = {"status": "success", "job_name": "backup", "started_at": "2024-01-01", "duration_s": 2.5}
    result = render_run_line(run)
    assert "SUCCESS" in result
    assert "backup" in result
    assert "2.50" in result


def test_render_run_line_failure():
    run = {"status": "failure", "job_name": "sync", "started_at": "2024-01-01", "duration_s": 0.1}
    result = render_run_line(run)
    assert "FAILURE" in result
    assert "sync" in result


def test_render_run_line_custom_template():
    run = {"status": "success", "job_name": "myjob", "started_at": "T", "duration_s": 1.0}
    result = render_run_line(run, template="{job_name}:{status}")
    assert result == "myjob:SUCCESS"


def test_render_run_line_missing_duration_defaults_zero():
    run = {"status": "success", "job_name": "j", "started_at": "T"}
    result = render_run_line(run)
    assert "0.00" in result


# ---------------------------------------------------------------------------
# render_alert
# ---------------------------------------------------------------------------

def test_render_alert_contains_level_and_job():
    alert = {"level": "critical", "job_name": "db-backup", "message": "5 failures"}
    result = render_alert(alert)
    assert "CRITICAL" in result
    assert "db-backup" in result
    assert "5 failures" in result


def test_render_alert_custom_template():
    alert = {"level": "warning", "job_name": "j", "message": "msg"}
    result = render_alert(alert, template="[{level}] {message}")
    assert result == "[WARNING] msg"


def test_render_alert_defaults_when_keys_missing():
    result = render_alert({})
    assert "WARNING" in result
