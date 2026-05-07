"""CLI sub-commands for tag management."""

import argparse
import sys

from cronjot.storage import get_connection, init_db
from cronjot.tags import (
    init_tags_schema,
    tag_run,
    fetch_runs_by_tag,
    list_tags,
    get_tags_for_run,
)


def cmd_tag_run(args: argparse.Namespace) -> None:
    """Attach one or more tags to an existing run by its ID."""
    conn = get_connection(args.db)
    init_db(conn)
    init_tags_schema(conn)
    tag_run(conn, args.run_id, args.tags)
    print(f"Tagged run {args.run_id} with: {', '.join(args.tags)}")


def cmd_list_tags(args: argparse.Namespace) -> None:
    """Print all known tags."""
    conn = get_connection(args.db)
    init_db(conn)
    init_tags_schema(conn)
    tags = list_tags(conn)
    if not tags:
        print("No tags found.")
        return
    for t in tags:
        print(t)


def cmd_runs_by_tag(args: argparse.Namespace) -> None:
    """List runs that carry a specific tag."""
    conn = get_connection(args.db)
    init_db(conn)
    init_tags_schema(conn)
    rows = fetch_runs_by_tag(conn, args.tag, limit=args.limit)
    if not rows:
        print(f"No runs found for tag '{args.tag}'.")
        return
    for row in rows:
        status_sym = "✓" if row["status"] == "success" else "✗"
        print(f"{status_sym} [{row['id']}] {row['job_name']}  {row['started_at']}")


def cmd_run_tags(args: argparse.Namespace) -> None:
    """Show tags attached to a specific run."""
    conn = get_connection(args.db)
    init_db(conn)
    init_tags_schema(conn)
    tags = get_tags_for_run(conn, args.run_id)
    if not tags:
        print(f"Run {args.run_id} has no tags.")
        return
    print(", ".join(tags))


def build_tags_parser(parent: argparse._SubParsersAction, db_default: str) -> None:
    """Register tag sub-commands onto *parent*."""
    p_tag = parent.add_parser("tag", help="manage run tags")
    p_tag.add_argument("--db", default=db_default)
    sub = p_tag.add_subparsers(dest="tag_cmd", required=True)

    p_add = sub.add_parser("add", help="attach tags to a run")
    p_add.add_argument("run_id", type=int)
    p_add.add_argument("tags", nargs="+")
    p_add.set_defaults(func=cmd_tag_run)

    p_ls = sub.add_parser("list", help="list all tags")
    p_ls.set_defaults(func=cmd_list_tags)

    p_runs = sub.add_parser("runs", help="list runs by tag")
    p_runs.add_argument("tag")
    p_runs.add_argument("--limit", type=int, default=50)
    p_runs.set_defaults(func=cmd_runs_by_tag)

    p_show = sub.add_parser("show", help="show tags for a run")
    p_show.add_argument("run_id", type=int)
    p_show.set_defaults(func=cmd_run_tags)
