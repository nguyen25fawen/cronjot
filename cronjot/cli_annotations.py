"""CLI commands for managing run annotations."""

import argparse
import sys

from cronjot.storage import get_connection, init_db
from cronjot.annotations import (
    init_annotations_schema,
    annotate_run,
    fetch_annotations,
    delete_annotation,
    fetch_runs_by_annotation,
)


def cmd_annotate(args: argparse.Namespace) -> None:
    with get_connection(args.db) as conn:
        init_db(conn)
        init_annotations_schema(conn)
        ann_id = annotate_run(conn, args.run_id, args.key, args.value)
        print(f"Annotation #{ann_id} added to run {args.run_id}: {args.key}={args.value}")


def cmd_list_annotations(args: argparse.Namespace) -> None:
    with get_connection(args.db) as conn:
        init_db(conn)
        init_annotations_schema(conn)
        annotations = fetch_annotations(conn, args.run_id)
    if not annotations:
        print(f"No annotations for run {args.run_id}.")
        return
    for a in annotations:
        print(f"[{a['id']}] {a['key']}={a['value']}  (at {a['created_at']})")


def cmd_delete_annotation(args: argparse.Namespace) -> None:
    with get_connection(args.db) as conn:
        init_annotations_schema(conn)
        removed = delete_annotation(conn, args.annotation_id)
    if removed:
        print(f"Annotation #{args.annotation_id} deleted.")
    else:
        print(f"Annotation #{args.annotation_id} not found.", file=sys.stderr)
        sys.exit(1)


def cmd_runs_by_annotation(args: argparse.Namespace) -> None:
    with get_connection(args.db) as conn:
        init_db(conn)
        init_annotations_schema(conn)
        run_ids = fetch_runs_by_annotation(conn, args.key, args.value)
    if not run_ids:
        print("No runs matched.")
        return
    for rid in run_ids:
        print(rid)


def build_annotations_parser(subparsers, parent_parser) -> None:
    p = subparsers.add_parser("annotations", help="Manage run annotations")
    sub = p.add_subparsers(dest="annotations_cmd", required=True)

    add_p = sub.add_parser("add", help="Add annotation to a run", parents=[parent_parser])
    add_p.add_argument("run_id", type=int)
    add_p.add_argument("key")
    add_p.add_argument("value")
    add_p.set_defaults(func=cmd_annotate)

    ls_p = sub.add_parser("list", help="List annotations for a run", parents=[parent_parser])
    ls_p.add_argument("run_id", type=int)
    ls_p.set_defaults(func=cmd_list_annotations)

    del_p = sub.add_parser("delete", help="Delete an annotation", parents=[parent_parser])
    del_p.add_argument("annotation_id", type=int)
    del_p.set_defaults(func=cmd_delete_annotation)

    find_p = sub.add_parser("find", help="Find runs by annotation key/value", parents=[parent_parser])
    find_p.add_argument("key")
    find_p.add_argument("value", nargs="?", default=None)
    find_p.set_defaults(func=cmd_runs_by_annotation)
