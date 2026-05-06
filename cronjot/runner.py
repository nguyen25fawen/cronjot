"""Execute a shell command as a cron job and record its run history."""

import subprocess
import shlex
from datetime import datetime, timezone
from typing import Optional

from cronjot.storage import init_db, insert_run, DEFAULT_DB_PATH


def run_job(
    job_name: str,
    command: str,
    timeout: Optional[int] = None,
    db_path: str = DEFAULT_DB_PATH,
) -> dict:
    """
    Run a shell command, capture its output, and store the result.

    Returns a dict summarising the run.
    """
    init_db(db_path)
    started_at = datetime.now(timezone.utc)

    try:
        result = subprocess.run(
            shlex.split(command),
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        exit_code = result.returncode
        output = result.stdout.strip() or None
        error = result.stderr.strip() or None
    except subprocess.TimeoutExpired as exc:
        exit_code = -1
        output = None
        error = f"Timed out after {timeout}s"
    except FileNotFoundError as exc:
        exit_code = 127
        output = None
        error = str(exc)

    finished_at = datetime.now(timezone.utc)

    run_id = insert_run(
        job_name=job_name,
        started_at=started_at,
        finished_at=finished_at,
        exit_code=exit_code,
        output=output,
        error=error,
        db_path=db_path,
    )

    return {
        "id": run_id,
        "job_name": job_name,
        "started_at": started_at.isoformat(),
        "finished_at": finished_at.isoformat(),
        "exit_code": exit_code,
        "output": output,
        "error": error,
        "duration_seconds": (finished_at - started_at).total_seconds(),
        "success": exit_code == 0,
    }
