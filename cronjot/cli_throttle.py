"""CLI commands for managing job throttle rules."""

import argparse
import sys

from .storage import get_connection, init_db
from .throttle import (
    init_throttle_schema,
    set_throttle,
    remove_throttle,
    get_throttle,
    is_throttled,
    list_throttles,
)


def _get_conn(db_path: str):
    conn = get_connection(db_path)
    init_db(conn)
    init_throttle_schema(conn)
    return conn


def cmd_set_throttle(args: argparse.Namespace) -> None:
    conn = _get_conn(args.db)
    set_throttle(conn, args.job_name, args.seconds)
    print(f"Throttle set: '{args.job_name}' must wait at least {args.seconds}s between runs.")


def cmd_remove_throttle(args: argparse.Namespace) -> None:
    conn = _get_conn(args.db)
    removed = remove_throttle(conn, args.job_name)
    if removed:
        print(f"Throttle removed for '{args.job_name}'.")
    else:
        print(f"No throttle rule found for '{args.job_name}'.")
        sys.exit(1)


def cmd_list_throttles(args: argparse.Namespace) -> None:
    conn = _get_conn(args.db)
    rules = list_throttles(conn)
    if not rules:
        print("No throttle rules defined.")
        return
    print(f"{'Job':<30} {'Min Interval (s)':>18}  {'Updated At'}")
    print("-" * 65)
    for r in rules:
        print(f"{r['job_name']:<30} {r['min_interval_seconds']:>18}  {r['updated_at']}")


def cmd_check_throttle(args: argparse.Namespace) -> None:
    conn = _get_conn(args.db)
    throttled = is_throttled(conn, args.job_name)
    if throttled:
        interval = get_throttle(conn, args.job_name)
        print(f"THROTTLED: '{args.job_name}' ran too recently (min interval: {interval}s).")
        sys.exit(2)
    else:
        print(f"OK: '{args.job_name}' is not throttled.")


def build_throttle_parser(subparsers) -> None:
    p = subparsers.add_parser("throttle", help="Manage job throttle rules")
    sp = p.add_subparsers(dest="throttle_cmd", required=True)

    s = sp.add_parser("set", help="Set minimum interval for a job")
    s.add_argument("job_name")
    s.add_argument("seconds", type=int, help="Minimum seconds between runs")
    s.set_defaults(func=cmd_set_throttle)

    r = sp.add_parser("remove", help="Remove throttle rule for a job")
    r.add_argument("job_name")
    r.set_defaults(func=cmd_remove_throttle)

    ls = sp.add_parser("list", help="List all throttle rules")
    ls.set_defaults(func=cmd_list_throttles)

    ck = sp.add_parser("check", help="Check if a job is currently throttled")
    ck.add_argument("job_name")
    ck.set_defaults(func=cmd_check_throttle)
