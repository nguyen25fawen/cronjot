"""CLI commands for managing run labels."""

import argparse
import sys

from cronjot.storage import get_connection, init_db
from cronjot.labels import (
    init_labels_schema,
    set_label,
    remove_label,
    fetch_labels,
    fetch_runs_by_label,
)


def _get_conn(db_path: str):
    conn = get_connection(db_path)
    init_db(conn)
    init_labels_schema(conn)
    return conn


def cmd_set_label(args):
    conn = _get_conn(args.db)
    row_id = set_label(conn, args.run_id, args.key, args.value)
    print(f"Label set (id={row_id}): run {args.run_id} [{args.key}={args.value}]")


def cmd_remove_label(args):
    conn = _get_conn(args.db)
    removed = remove_label(conn, args.run_id, args.key)
    if removed:
        print(f"Label '{args.key}' removed from run {args.run_id}.")
    else:
        print(f"No label '{args.key}' found for run {args.run_id}.")
        sys.exit(1)


def cmd_list_labels(args):
    conn = _get_conn(args.db)
    labels = fetch_labels(conn, args.run_id)
    if not labels:
        print(f"No labels for run {args.run_id}.")
        return
    for key, value in labels.items():
        print(f"  {key}={value}")


def cmd_runs_by_label(args):
    conn = _get_conn(args.db)
    run_ids = fetch_runs_by_label(conn, args.key, args.value or None, limit=args.limit)
    if not run_ids:
        print("No runs matched.")
        return
    for rid in run_ids:
        print(rid)


def build_labels_parser(subparsers=None):
    if subparsers is None:
        parser = argparse.ArgumentParser(prog="cronjot-labels")
        sub = parser.add_subparsers(dest="command")
    else:
        parser = subparsers.add_parser("labels", help="Manage run labels")
        sub = parser.add_subparsers(dest="labels_command")

    p_set = sub.add_parser("set", help="Set a label on a run")
    p_set.add_argument("run_id", type=int)
    p_set.add_argument("key")
    p_set.add_argument("value")
    p_set.add_argument("--db", default="cronjot.db")
    p_set.set_defaults(func=cmd_set_label)

    p_rm = sub.add_parser("remove", help="Remove a label from a run")
    p_rm.add_argument("run_id", type=int)
    p_rm.add_argument("key")
    p_rm.add_argument("--db", default="cronjot.db")
    p_rm.set_defaults(func=cmd_remove_label)

    p_ls = sub.add_parser("list", help="List labels for a run")
    p_ls.add_argument("run_id", type=int)
    p_ls.add_argument("--db", default="cronjot.db")
    p_ls.set_defaults(func=cmd_list_labels)

    p_q = sub.add_parser("runs", help="Find runs by label")
    p_q.add_argument("key")
    p_q.add_argument("value", nargs="?", default=None)
    p_q.add_argument("--limit", type=int, default=100)
    p_q.add_argument("--db", default="cronjot.db")
    p_q.set_defaults(func=cmd_runs_by_label)

    return parser
