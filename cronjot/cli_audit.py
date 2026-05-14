"""CLI sub-commands for the audit log."""

import argparse
import time
from datetime import datetime

from cronjot.storage import get_connection, init_db
from cronjot.audit import init_audit_schema, fetch_audit_log, purge_audit_log


def _get_conn(db_path: str):
    conn = get_connection(db_path)
    init_db(conn)
    init_audit_schema(conn)
    return conn


def cmd_list_audit(args: argparse.Namespace) -> None:
    conn = _get_conn(args.db)
    entries = fetch_audit_log(
        conn,
        actor=getattr(args, "actor", None),
        action=getattr(args, "action", None),
        limit=args.limit,
    )
    if not entries:
        print("No audit entries found.")
        return
    for e in entries:
        ts_str = datetime.fromtimestamp(e["ts"]).strftime("%Y-%m-%d %H:%M:%S")
        target = e["target"] or "-"
        detail = e["detail"] or ""
        print(f"[{ts_str}] actor={e['actor']} action={e['action']} target={target} {detail}".rstrip())


def cmd_purge_audit(args: argparse.Namespace) -> None:
    conn = _get_conn(args.db)
    cutoff = time.time() - args.days * 86400
    deleted = purge_audit_log(conn, cutoff)
    print(f"Purged {deleted} audit log entries older than {args.days} day(s).")


def build_audit_parser(subparsers: argparse._SubParsersAction) -> None:
    p_audit = subparsers.add_parser("audit", help="Manage the audit log")
    sub = p_audit.add_subparsers(dest="audit_cmd", required=True)

    p_list = sub.add_parser("list", help="List audit log entries")
    p_list.add_argument("--actor", default=None, help="Filter by actor")
    p_list.add_argument("--action", default=None, help="Filter by action type")
    p_list.add_argument("--limit", type=int, default=50, help="Max entries to show")
    p_list.add_argument("--db", default="cronjot.db")
    p_list.set_defaults(func=cmd_list_audit)

    p_purge = sub.add_parser("purge", help="Purge old audit log entries")
    p_purge.add_argument("--days", type=int, default=90, help="Remove entries older than N days")
    p_purge.add_argument("--db", default="cronjot.db")
    p_purge.set_defaults(func=cmd_purge_audit)
