"""CLI commands for displaying job metrics."""

from __future__ import annotations

import argparse
import json
import sys

from cronjot.storage import get_connection, init_db
from cronjot.metrics import get_all_job_metrics, get_job_metrics, format_metrics_text


def cmd_metrics(args: argparse.Namespace) -> None:
    """Display aggregated metrics for one or all jobs."""
    conn = get_connection(args.db)
    init_db(conn)

    if args.job:
        metrics_list = [get_job_metrics(conn, args.job)]
    else:
        metrics_list = get_all_job_metrics(conn)

    if not metrics_list:
        print("No metrics available.")
        sys.exit(0)

    if args.format == "json":
        print(json.dumps(metrics_list, indent=2))
    else:
        print(format_metrics_text(metrics_list))


def build_metrics_parser(subparsers: argparse._SubParsersAction) -> None:
    """Register the 'metrics' subcommand."""
    p = subparsers.add_parser(
        "metrics",
        help="Show aggregated run statistics for cron jobs",
    )
    p.add_argument(
        "--db",
        default="cronjot.db",
        help="Path to the SQLite database (default: cronjot.db)",
    )
    p.add_argument(
        "--job",
        default=None,
        metavar="JOB_NAME",
        help="Filter metrics to a single job",
    )
    p.add_argument(
        "--format",
        choices=["text", "json"],
        default="text",
        help="Output format (default: text)",
    )
    p.set_defaults(func=cmd_metrics)
