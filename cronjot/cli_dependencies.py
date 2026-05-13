"""CLI commands for managing job dependencies."""

import argparse
import sys

from cronjot.storage import get_connection, init_db
from cronjot.dependencies import (
    init_dependencies_schema,
    add_dependency,
    remove_dependency,
    list_dependencies,
    check_dependencies_met,
)


def _get_conn(db_path: str):
    conn = get_connection(db_path)
    init_db(conn)
    init_dependencies_schema(conn)
    return conn


def cmd_add_dependency(args: argparse.Namespace) -> None:
    conn = _get_conn(args.db)
    try:
        add_dependency(conn, args.job, args.depends_on)
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)
    print(f"Dependency added: '{args.job}' depends on '{args.depends_on}'.")


def cmd_remove_dependency(args: argparse.Namespace) -> None:
    conn = _get_conn(args.db)
    remove_dependency(conn, args.job, args.depends_on)
    print(f"Dependency removed: '{args.job}' no longer depends on '{args.depends_on}'.")


def cmd_list_dependencies(args: argparse.Namespace) -> None:
    conn = _get_conn(args.db)
    deps = list_dependencies(conn, args.job)
    if not deps:
        print(f"No dependencies registered for '{args.job}'.")
        return
    print(f"Dependencies for '{args.job}':")
    for dep in deps:
        print(f"  - {dep}")


def cmd_check_dependencies(args: argparse.Namespace) -> None:
    conn = _get_conn(args.db)
    met, unmet = check_dependencies_met(conn, args.job, since=args.since)
    if met:
        print(f"All dependencies for '{args.job}' are satisfied.")
    else:
        print(f"Unmet dependencies for '{args.job}':")
        for dep in unmet:
            print(f"  - {dep}")
        sys.exit(1)


def build_dependencies_parser(subparsers) -> None:
    p = subparsers.add_parser("dependencies", help="Manage job dependencies")
    p.add_argument("--db", default="cronjot.db", help="Path to the SQLite database")
    sub = p.add_subparsers(dest="dep_cmd", required=True)

    add_p = sub.add_parser("add", help="Add a dependency")
    add_p.add_argument("job", help="Job that has the dependency")
    add_p.add_argument("depends_on", help="Job that must succeed first")
    add_p.set_defaults(func=cmd_add_dependency)

    rm_p = sub.add_parser("remove", help="Remove a dependency")
    rm_p.add_argument("job")
    rm_p.add_argument("depends_on")
    rm_p.set_defaults(func=cmd_remove_dependency)

    ls_p = sub.add_parser("list", help="List dependencies for a job")
    ls_p.add_argument("job")
    ls_p.set_defaults(func=cmd_list_dependencies)

    chk_p = sub.add_parser("check", help="Check whether dependencies are met")
    chk_p.add_argument("job")
    chk_p.add_argument("--since", default=None, help="Only consider runs after this ISO-8601 datetime")
    chk_p.set_defaults(func=cmd_check_dependencies)
