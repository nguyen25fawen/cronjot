"""CLI interface for the replay feature."""

import argparse
import sys

from cronjot.storage import get_connection, init_db
from cronjot.replay import replay_run, replay_latest


def _get_conn(db_path: str):
    conn = get_connection(db_path)
    init_db(conn)
    return conn


def cmd_replay_by_id(args: argparse.Namespace) -> None:
    """Replay a specific run by its ID."""
    conn = _get_conn(args.db)
    try:
        result = replay_run(conn, run_id=args.run_id, db_path=args.db)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
    finally:
        conn.close()

    status = "SUCCESS" if result["exit_code"] == 0 else "FAILURE"
    print(f"Replayed run id={args.run_id} -> {status} (exit {result['exit_code']})")
    print(f"  job    : {result['job_name']}")
    print(f"  command: {result['command']}")
    print(f"  duration: {result['duration_seconds']:.3f}s")
    if result["exit_code"] != 0:
        sys.exit(result["exit_code"])


def cmd_replay_latest(args: argparse.Namespace) -> None:
    """Replay the most recent run for a given job name."""
    conn = _get_conn(args.db)
    try:
        result = replay_latest(conn, job_name=args.job_name, db_path=args.db)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
    finally:
        conn.close()

    status = "SUCCESS" if result["exit_code"] == 0 else "FAILURE"
    print(f"Replayed latest run of '{args.job_name}' -> {status} (exit {result['exit_code']})")
    print(f"  command: {result['command']}")
    print(f"  duration: {result['duration_seconds']:.3f}s")
    if result["exit_code"] != 0:
        sys.exit(result["exit_code"])


def build_replay_parser(subparsers=None) -> argparse.ArgumentParser:
    if subparsers is not None:
        parser = subparsers.add_parser("replay", help="Replay past job runs")
    else:
        parser = argparse.ArgumentParser(prog="cronjot-replay", description="Replay past job runs")

    parser.add_argument("--db", default="cronjot.db", help="Path to the SQLite database")
    sub = parser.add_subparsers(dest="replay_cmd", required=True)

    p_id = sub.add_parser("by-id", help="Replay a run by its numeric ID")
    p_id.add_argument("run_id", type=int, help="Run ID to replay")
    p_id.set_defaults(func=cmd_replay_by_id)

    p_latest = sub.add_parser("latest", help="Replay the latest run for a job")
    p_latest.add_argument("job_name", help="Name of the job")
    p_latest.set_defaults(func=cmd_replay_latest)

    return parser


def main() -> None:  # pragma: no cover
    parser = build_replay_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":  # pragma: no cover
    main()
