"""CLI sub-command: `cronjot check-alerts` — evaluate alert rules for a job."""

from __future__ import annotations

import argparse
import sys

from cronjot.storage import get_connection, init_db
from cronjot.alerts import evaluate_alerts
from cronjot.notifiers import send_slack, send_email


def cmd_check_alerts(args: argparse.Namespace) -> None:
    """Evaluate alert rules and optionally dispatch notifications."""
    conn = get_connection(args.db)
    init_db(conn)

    messages = evaluate_alerts(
        conn,
        job_name=args.job,
        consecutive_failure_threshold=args.fail_threshold,
        max_duration_seconds=args.max_duration,
    )

    if not messages:
        print(f"No alerts for job '{args.job}'.")
        return

    for msg in messages:
        print(f"ALERT: {msg}")

    if args.slack_webhook:
        body = "\n".join(f":warning: {m}" for m in messages)
        try:
            send_slack(args.slack_webhook, body)
            print("Slack notification sent.")
        except RuntimeError as exc:
            print(f"Slack error: {exc}", file=sys.stderr)

    if args.email_to:
        subject = f"[cronjot] Alerts for job '{args.job}'"
        body = "\n".join(messages)
        try:
            send_email(
                smtp_host=args.smtp_host,
                smtp_port=args.smtp_port,
                sender=args.email_from,
                recipients=[args.email_to],
                subject=subject,
                body=body,
            )
            print("Email notification sent.")
        except Exception as exc:  # noqa: BLE001
            print(f"Email error: {exc}", file=sys.stderr)

    sys.exit(1)  # non-zero so calling scripts know alerts fired


def build_alerts_parser(subparsers) -> None:
    p = subparsers.add_parser("check-alerts", help="Evaluate alert rules for a job")
    p.add_argument("job", help="Job name to check")
    p.add_argument("--db", default="cronjot.db", help="Path to SQLite database")
    p.add_argument("--fail-threshold", type=int, default=3,
                   help="Consecutive failures before alerting (default: 3)")
    p.add_argument("--max-duration", type=float, default=None,
                   help="Max allowed duration in seconds")
    p.add_argument("--slack-webhook", default=None, help="Slack webhook URL")
    p.add_argument("--email-to", default=None, help="Alert recipient email")
    p.add_argument("--email-from", default="cronjot@localhost", help="Sender email")
    p.add_argument("--smtp-host", default="localhost", help="SMTP host")
    p.add_argument("--smtp-port", type=int, default=25, help="SMTP port")
    p.set_defaults(func=cmd_check_alerts)
