"""CLI sub-commands for snapshot management."""

import argparse
import json
import sys

from cronjot.storage import get_connection, init_db
from cronjot.snapshots import (
    init_snapshots_schema,
    take_snapshot,
    list_snapshots,
    get_snapshot,
    delete_snapshot,
    compare_snapshots,
)


def _get_conn(db_path: str):
    conn = get_connection(db_path)
    init_db(conn)
    init_snapshots_schema(conn)
    return conn


def cmd_take_snapshot(args: argparse.Namespace) -> None:
    conn = _get_conn(args.db)
    snap_id = take_snapshot(conn, args.label)
    print(f"Snapshot #{snap_id} '{args.label}' created.")


def cmd_list_snapshots(args: argparse.Namespace) -> None:
    conn = _get_conn(args.db)
    snapshots = list_snapshots(conn)
    if not snapshots:
        print("No snapshots found.")
        return
    for s in snapshots:
        print(f"[{s['id']}] {s['label']}  ({s['created_at']})")


def cmd_show_snapshot(args: argparse.Namespace) -> None:
    conn = _get_conn(args.db)
    snap = get_snapshot(conn, args.id)
    if snap is None:
        print(f"Snapshot #{args.id} not found.", file=sys.stderr)
        sys.exit(1)
    print(f"Snapshot #{snap['id']} — {snap['label']} @ {snap['created_at']}")
    print(json.dumps(snap["metrics"], indent=2))


def cmd_delete_snapshot(args: argparse.Namespace) -> None:
    conn = _get_conn(args.db)
    removed = delete_snapshot(conn, args.id)
    if removed:
        print(f"Snapshot #{args.id} deleted.")
    else:
        print(f"Snapshot #{args.id} not found.", file=sys.stderr)
        sys.exit(1)


def cmd_compare_snapshots(args: argparse.Namespace) -> None:
    conn = _get_conn(args.db)
    snap_a = get_snapshot(conn, args.id_a)
    snap_b = get_snapshot(conn, args.id_b)
    missing = [i for i, s in [(args.id_a, snap_a), (args.id_b, snap_b)] if s is None]
    if missing:
        print(f"Snapshot(s) not found: {missing}", file=sys.stderr)
        sys.exit(1)
    diff = compare_snapshots(snap_a, snap_b)
    print(f"Diff: snapshot #{args.id_a} → #{args.id_b}")
    print(json.dumps(diff, indent=2))


def build_snapshots_parser(subparsers) -> None:
    p = subparsers.add_parser("snapshots", help="Manage metric snapshots")
    sp = p.add_subparsers(dest="snap_cmd", required=True)

    take = sp.add_parser("take", help="Take a new snapshot")
    take.add_argument("label", help="Human-readable label for the snapshot")
    take.set_defaults(func=cmd_take_snapshot)

    lst = sp.add_parser("list", help="List all snapshots")
    lst.set_defaults(func=cmd_list_snapshots)

    show = sp.add_parser("show", help="Show snapshot details")
    show.add_argument("id", type=int, help="Snapshot id")
    show.set_defaults(func=cmd_show_snapshot)

    delete = sp.add_parser("delete", help="Delete a snapshot")
    delete.add_argument("id", type=int, help="Snapshot id")
    delete.set_defaults(func=cmd_delete_snapshot)

    cmp = sp.add_parser("compare", help="Compare two snapshots")
    cmp.add_argument("id_a", type=int, help="First (older) snapshot id")
    cmp.add_argument("id_b", type=int, help="Second (newer) snapshot id")
    cmp.set_defaults(func=cmd_compare_snapshots)
