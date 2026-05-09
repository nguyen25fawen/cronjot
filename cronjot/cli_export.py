"""CLI commands for exporting run history to JSON or CSV."""

import argparse
import sys

from cronjot.storage import get_connection, init_db
from cronjot.export import export_runs


def cmd_export(args):
    """Handle the 'export' subcommand.

    Exports run history to stdout or a file in JSON or CSV format.
    Optionally filters by job name and limits the number of records.
    """
    conn = get_connection(args.db)
    init_db(conn)

    result = export_runs(
        conn,
        fmt=args.format,
        job_name=args.job,
        limit=args.limit,
    )

    if not result:
        print("No runs found.", file=sys.stderr)
        sys.exit(0)

    if args.output:
        try:
            with open(args.output, "w", encoding="utf-8") as fh:
                fh.write(result)
            print(f"Exported to {args.output}")
        except OSError as exc:
            print(f"Error writing to file: {exc}", file=sys.stderr)
            sys.exit(1)
    else:
        print(result)


def build_export_parser(subparsers):
    """Register the 'export' subcommand on *subparsers*.

    Parameters
    ----------
    subparsers:
        The subparsers action returned by ``ArgumentParser.add_subparsers()``.

    Returns
    -------
    argparse.ArgumentParser
        The newly created subcommand parser.
    """
    parser = subparsers.add_parser(
        "export",
        help="Export run history to JSON or CSV",
        description=(
            "Export cron job run history to JSON or CSV format. "
            "Output is written to stdout by default."
        ),
    )

    parser.add_argument(
        "--db",
        default="cronjot.db",
        help="Path to the SQLite database file (default: cronjot.db)",
    )
    parser.add_argument(
        "--format",
        choices=["json", "csv"],
        default="json",
        help="Output format: json or csv (default: json)",
    )
    parser.add_argument(
        "--job",
        default=None,
        metavar="JOB_NAME",
        help="Filter exported records by job name",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        metavar="N",
        help="Maximum number of records to export",
    )
    parser.add_argument(
        "--output",
        "-o",
        default=None,
        metavar="FILE",
        help="Write output to FILE instead of stdout",
    )

    parser.set_defaults(func=cmd_export)
    return parser


if __name__ == "__main__":  # pragma: no cover
    _root = argparse.ArgumentParser(prog="cronjot-export")
    _sub = _root.add_subparsers()
    build_export_parser(_sub)
    _args = _root.parse_args()
    if hasattr(_args, "func"):
        _args.func(_args)
    else:
        _root.print_help()
