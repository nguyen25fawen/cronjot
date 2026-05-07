"""Command-line interface for cronjot."""

import argparse
import sys

from cronjot.storage import init_db, fetch_runs
from cronjot.runner import run_job
from cronjot.digest import build_digest, format_digest_text
from cronjot.notifiers import send_email, send_slack


def cmd_run(args):
    """Execute a command and log the result."""
    db_path = args.db
    init_db(db_path)
    result = run_job(args.name, args.command, db_path=db_path)
    status = "OK" if result["exit_code"] == 0 else "FAIL"
    print(f"[{status}] {args.name} exited with code {result['exit_code']}")
    if result["exit_code"] != 0:
        sys.exit(1)


def cmd_history(args):
    """Print recent run history for a job (or all jobs)."""
    db_path = args.db
    init_db(db_path)
    runs = fetch_runs(db_path, job_name=args.name or None, limit=args.limit)
    if not runs:
        print("No runs found.")
        return
    print(f"{'JOB':<30} {'STATUS':<8} {'EXIT':>4}  {'STARTED':<20}  {'DURATION':>10}")
    print("-" * 80)
    for r in runs:
        status = "OK" if r["exit_code"] == 0 else "FAIL"
        duration = f"{r['duration_seconds']:.2f}s" if r["duration_seconds"] is not None else "N/A"
        print(f"{r['job_name']:<30} {status:<8} {r['exit_code']:>4}  {r['started_at']:<20}  {duration:>10}")


def cmd_digest(args):
    """Build and optionally send a digest summary."""
    db_path = args.db
    init_db(db_path)
    digest = build_digest(db_path, job_name=args.name or None, hours=args.hours)
    text = format_digest_text(digest)
    print(text)

    if args.email:
        send_email(
            to=args.email,
            subject="Cronjot Digest",
            body=text,
            smtp_host=args.smtp_host or "localhost",
            smtp_port=int(args.smtp_port or 25),
        )
        print(f"Digest sent to {args.email}")

    if args.slack_webhook:
        send_slack(webhook_url=args.slack_webhook, text=text)
        print("Digest sent to Slack")


def build_parser():
    parser = argparse.ArgumentParser(
        prog="cronjot",
        description="Lightweight cron job logger and digest sender.",
    )
    parser.add_argument("--db", default="cronjot.db", help="Path to SQLite database (default: cronjot.db)")

    sub = parser.add_subparsers(dest="command", required=True)

    # run
    p_run = sub.add_parser("run", help="Run a command and log the result")
    p_run.add_argument("name", help="Job name")
    p_run.add_argument("command", help="Shell command to execute")
    p_run.set_defaults(func=cmd_run)

    # history
    p_hist = sub.add_parser("history", help="Show run history")
    p_hist.add_argument("--name", default="", help="Filter by job name")
    p_hist.add_argument("--limit", type=int, default=20, help="Max rows to show (default: 20)")
    p_hist.set_defaults(func=cmd_history)

    # digest
    p_dig = sub.add_parser("digest", help="Print (and optionally send) a digest summary")
    p_dig.add_argument("--name", default="", help="Filter by job name")
    p_dig.add_argument("--hours", type=int, default=24, help="Look-back window in hours (default: 24)")
    p_dig.add_argument("--email", default="", help="Send digest to this email address")
    p_dig.add_argument("--smtp-host", default="", help="SMTP host")
    p_dig.add_argument("--smtp-port", default="25", help="SMTP port")
    p_dig.add_argument("--slack-webhook", default="", help="Slack incoming webhook URL")
    p_dig.set_defaults(func=cmd_digest)

    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
