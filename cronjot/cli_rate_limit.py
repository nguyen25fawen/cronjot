"""CLI commands for managing per-job rate limits."""

import argparse
import sys

from cronjot.storage import get_connection, init_db
from cronjot.rate_limit import (
    init_rate_limit_schema,
    set_rate_limit,
    remove_rate_limit,
    get_rate_limit,
    is_rate_limited,
    list_rate_limits,
)


def _get_conn(args):
    conn = get_connection(args.db)
    init_db(conn)
    init_rate_limit_schema(conn)
    return conn


def cmd_set_rate_limit(args):
    conn = _get_conn(args)
    try:
        set_rate_limit(conn, args.job_name, args.max_runs, args.window)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
    print(
        f"Rate limit set: {args.job_name} — max {args.max_runs} run(s) "
        f"per {args.window}s window."
    )


def cmd_remove_rate_limit(args):
    conn = _get_conn(args)
    removed = remove_rate_limit(conn, args.job_name)
    if removed:
        print(f"Rate limit removed for '{args.job_name}'.")
    else:
        print(f"No rate limit found for '{args.job_name}'.")
        sys.exit(1)


def cmd_list_rate_limits(args):
    conn = _get_conn(args)
    limits = list_rate_limits(conn)
    if not limits:
        print("No rate limits configured.")
        return
    print(f"{'JOB':<30} {'MAX RUNS':>10} {'WINDOW (s)':>12}")
    print("-" * 54)
    for rl in limits:
        print(f"{rl['job_name']:<30} {rl['max_runs']:>10} {rl['window_seconds']:>12}")


def cmd_check_rate_limit(args):
    conn = _get_conn(args)
    cfg = get_rate_limit(conn, args.job_name)
    if cfg is None:
        print(f"No rate limit configured for '{args.job_name}'.")
        return
    limited = is_rate_limited(conn, args.job_name)
    status = "RATE LIMITED" if limited else "OK"
    print(
        f"{args.job_name}: {status} "
        f"(max {cfg['max_runs']} runs / {cfg['window_seconds']}s)"
    )
    if limited:
        sys.exit(2)


def build_rate_limit_parser(subparsers):
    p = subparsers.add_parser("rate-limit", help="Manage per-job rate limits")
    sub = p.add_subparsers(dest="rate_limit_cmd", required=True)

    ps = sub.add_parser("set", help="Set or update a rate limit")
    ps.add_argument("job_name")
    ps.add_argument("max_runs", type=int, help="Max allowed runs in the window")
    ps.add_argument("window", type=int, help="Rolling window size in seconds")
    ps.set_defaults(func=cmd_set_rate_limit)

    pr = sub.add_parser("remove", help="Remove a rate limit")
    pr.add_argument("job_name")
    pr.set_defaults(func=cmd_remove_rate_limit)

    pl = sub.add_parser("list", help="List all rate limits")
    pl.set_defaults(func=cmd_list_rate_limits)

    pc = sub.add_parser("check", help="Check whether a job is currently rate-limited")
    pc.add_argument("job_name")
    pc.set_defaults(func=cmd_check_rate_limit)

    return p
