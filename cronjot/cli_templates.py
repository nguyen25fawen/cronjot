"""CLI commands for previewing cronjot notification templates."""

import argparse
from datetime import datetime

from cronjot.templates import render_digest, render_run_line, render_alert


def cmd_preview_digest(args: argparse.Namespace) -> None:
    """Print a rendered digest preview using sample or provided data."""
    summary = {
        "generated_at": datetime.utcnow().isoformat(),
        "total_jobs": args.total_jobs,
        "total_runs": args.total_runs,
        "body": args.body or "  backup-db  SUCCESS x3  FAILURE x1\n  sync-files SUCCESS x5",
    }
    template = args.template or None
    print(render_digest(summary, template=template))


def cmd_preview_run(args: argparse.Namespace) -> None:
    """Print a rendered run-line preview."""
    run = {
        "status": args.status,
        "job_name": args.job_name,
        "started_at": args.started_at or datetime.utcnow().isoformat(),
        "duration_s": args.duration_s,
    }
    template = args.template or None
    print(render_run_line(run, template=template))


def cmd_preview_alert(args: argparse.Namespace) -> None:
    """Print a rendered alert preview."""
    alert = {
        "level": args.level,
        "job_name": args.job_name,
        "message": args.message,
    }
    template = args.template or None
    print(render_alert(alert, template=template))


def build_templates_parser(subparsers: argparse._SubParsersAction) -> None:
    p = subparsers.add_parser("templates", help="Preview notification templates")
    sub = p.add_subparsers(dest="templates_cmd", required=True)

    # digest preview
    pd = sub.add_parser("digest", help="Preview digest template")
    pd.add_argument("--total-jobs", type=int, default=2)
    pd.add_argument("--total-runs", type=int, default=9)
    pd.add_argument("--body", default=None)
    pd.add_argument("--template", default=None, help="Custom format string")
    pd.set_defaults(func=cmd_preview_digest)

    # run-line preview
    pr = sub.add_parser("run", help="Preview run-line template")
    pr.add_argument("--job-name", default="example-job")
    pr.add_argument("--status", default="success")
    pr.add_argument("--started-at", default=None)
    pr.add_argument("--duration-s", type=float, default=1.23)
    pr.add_argument("--template", default=None)
    pr.set_defaults(func=cmd_preview_run)

    # alert preview
    pa = sub.add_parser("alert", help="Preview alert template")
    pa.add_argument("--job-name", default="example-job")
    pa.add_argument("--level", default="warning")
    pa.add_argument("--message", default="3 consecutive failures detected")
    pa.add_argument("--template", default=None)
    pa.set_defaults(func=cmd_preview_alert)
