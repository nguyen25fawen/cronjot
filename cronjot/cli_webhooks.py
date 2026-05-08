"""CLI sub-commands for webhook testing in cronjot."""

import argparse
import json
import sys

from cronjot.storage import get_connection, fetch_runs
from cronjot.webhooks import send_webhook, build_run_payload


def cmd_webhook_test(args: argparse.Namespace) -> None:
    """Send the most recent run for a job to a webhook URL (smoke-test helper)."""
    conn = get_connection(args.db)
    runs = fetch_runs(conn, job_name=args.job_name, limit=1)
    if not runs:
        print(f"No runs found for job {args.job_name!r}.", file=sys.stderr)
        sys.exit(1)

    payload = build_run_payload(dict(runs[0]))
    try:
        send_webhook(args.url, payload, secret=args.secret)
        print(f"Webhook delivered to {args.url!r}.")
        if args.verbose:
            print(json.dumps(payload, indent=2))
    except RuntimeError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


def build_webhooks_parser(subparsers: argparse._SubParsersAction) -> None:  # type: ignore[type-arg]
    p = subparsers.add_parser(
        "webhook-test",
        help="POST the latest run for a job to a webhook endpoint.",
    )
    p.add_argument("job_name", help="Name of the job whose last run to send.")
    p.add_argument("url", help="Destination webhook URL.")
    p.add_argument("--secret", default=None, help="Optional shared secret header value.")
    p.add_argument("--verbose", "-v", action="store_true", help="Print the payload.")
    p.add_argument("--db", default="cronjot.db", help="Path to the SQLite database.")
    p.set_defaults(func=cmd_webhook_test)
