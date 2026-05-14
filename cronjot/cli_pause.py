"""CLI commands for pausing and resuming cron jobs."""

import argparse
import sys

from cronjot.storage import get_connection, init_db
from cronjot.pause import (
    init_pause_schema,
    pause_job,
    resume_job,
    is_paused,
    list_paused_jobs,
    get_pause_info,
)


def _get_conn(db_path: str):
    conn = get_connection(db_path)
    init_db(conn)
    init_pause_schema(conn)
    return conn


def cmd_pause(args: argparse.Namespace) -> None:
    conn = _get_conn(args.db)
    if is_paused(conn, args.job_name):
        info = get_pause_info(conn, args.job_name)
        print(f"Job '{args.job_name}' is already paused (since {info['paused_at']}). Updating reason.")
    pause_job(conn, args.job_name, reason=args.reason)
    print(f"Paused '{args.job_name}'." + (f" Reason: {args.reason}" if args.reason else ""))


def cmd_resume(args: argparse.Namespace) -> None:
    conn = _get_conn(args.db)
    removed = resume_job(conn, args.job_name)
    if removed:
        print(f"Resumed '{args.job_name}'.")
    else:
        print(f"Job '{args.job_name}' was not paused.", file=sys.stderr)
        sys.exit(1)


def cmd_list_paused(args: argparse.Namespace) -> None:
    conn = _get_conn(args.db)
    jobs = list_paused_jobs(conn)
    if not jobs:
        print("No jobs are currently paused.")
        return
    print(f"{'JOB NAME':<30}  {'PAUSED AT':<27}  REASON")
    print("-" * 75)
    for j in jobs:
        reason = j["reason"] or ""
        print(f"{j['job_name']:<30}  {j['paused_at']:<27}  {reason}")


def cmd_check_pause(args: argparse.Namespace) -> None:
    conn = _get_conn(args.db)
    info = get_pause_info(conn, args.job_name)
    if info:
        reason_str = f"  Reason: {info['reason']}" if info["reason"] else ""
        print(f"PAUSED since {info['paused_at']}.{reason_str}")
        sys.exit(1)
    else:
        print(f"'{args.job_name}' is not paused.")


def build_pause_parser(subparsers=None) -> argparse.ArgumentParser:
    if subparsers is None:
        parser = argparse.ArgumentParser(description="Manage job pauses")
        sub = parser.add_subparsers(dest="command")
    else:
        parser = subparsers.add_parser("pause-mgr", help="Manage job pauses")
        sub = parser.add_subparsers(dest="pause_command")

    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--db", default="cronjot.db")

    p_pause = sub.add_parser("pause", parents=[common], help="Pause a job")
    p_pause.add_argument("job_name")
    p_pause.add_argument("--reason", default=None)
    p_pause.set_defaults(func=cmd_pause)

    p_resume = sub.add_parser("resume", parents=[common], help="Resume a paused job")
    p_resume.add_argument("job_name")
    p_resume.set_defaults(func=cmd_resume)

    p_list = sub.add_parser("list", parents=[common], help="List paused jobs")
    p_list.set_defaults(func=cmd_list_paused)

    p_check = sub.add_parser("check", parents=[common], help="Check if a job is paused")
    p_check.add_argument("job_name")
    p_check.set_defaults(func=cmd_check_pause)

    return parser


def main() -> None:
    parser = build_pause_parser()
    args = parser.parse_args()
    if not hasattr(args, "func"):
        parser.print_help()
        sys.exit(1)
    args.func(args)


if __name__ == "__main__":
    main()
