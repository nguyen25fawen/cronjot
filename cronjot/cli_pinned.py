"""CLI commands for managing pinned runs."""

import argparse
import sys

from cronjot.storage import get_connection, init_db
from cronjot.pinned import (
    init_pinned_schema,
    pin_run,
    unpin_run,
    is_pinned,
    list_pinned_runs,
)


def _get_conn(db_path: str):
    conn = get_connection(db_path)
    init_db(conn)
    init_pinned_schema(conn)
    return conn


def cmd_pin(args: argparse.Namespace) -> None:
    conn = _get_conn(args.db)
    try:
        pin_id = pin_run(conn, args.run_id, label=args.label)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
    label_info = f" (label: {args.label})" if args.label else ""
    print(f"Pinned run {args.run_id}{label_info} [pin #{pin_id}].")


def cmd_unpin(args: argparse.Namespace) -> None:
    conn = _get_conn(args.db)
    removed = unpin_run(conn, args.run_id)
    if removed:
        print(f"Unpinned run {args.run_id}.")
    else:
        print(f"Run {args.run_id} was not pinned.", file=sys.stderr)
        sys.exit(1)


def cmd_list_pinned(args: argparse.Namespace) -> None:
    conn = _get_conn(args.db)
    rows = list_pinned_runs(conn)
    if not rows:
        print("No pinned runs.")
        return
    for row in rows:
        label = f"  [{row['label']}]" if row["label"] else ""
        print(
            f"run_id={row['run_id']}  job={row['job_name']}"
            f"  exit={row['exit_code']}  started={row['started_at']}"
            f"  pinned_at={row['pinned_at']}{label}"
        )


def cmd_check_pin(args: argparse.Namespace) -> None:
    conn = _get_conn(args.db)
    pinned = is_pinned(conn, args.run_id)
    print(f"Run {args.run_id} is {'pinned' if pinned else 'not pinned'}.")
    sys.exit(0 if pinned else 1)


def build_pinned_parser(parent_subparsers=None):
    if parent_subparsers is not None:
        parser = parent_subparsers.add_parser("pinned", help="Manage pinned runs")
    else:
        parser = argparse.ArgumentParser(description="Manage pinned runs")

    parser.add_argument("--db", default="cronjot.db", help="Path to SQLite database")
    sub = parser.add_subparsers(dest="pinned_cmd", required=True)

    p_pin = sub.add_parser("pin", help="Pin a run")
    p_pin.add_argument("run_id", type=int)
    p_pin.add_argument("--label", default=None, help="Optional label")
    p_pin.set_defaults(func=cmd_pin)

    p_unpin = sub.add_parser("unpin", help="Unpin a run")
    p_unpin.add_argument("run_id", type=int)
    p_unpin.set_defaults(func=cmd_unpin)

    p_list = sub.add_parser("list", help="List all pinned runs")
    p_list.set_defaults(func=cmd_list_pinned)

    p_check = sub.add_parser("check", help="Check whether a run is pinned")
    p_check.add_argument("run_id", type=int)
    p_check.set_defaults(func=cmd_check_pin)

    return parser
