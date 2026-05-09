"""Standalone entry-point for the snapshots CLI (used in setup.py console_scripts)."""

import argparse
import sys

from cronjot.cli_snapshots import build_snapshots_parser


DEFAULT_DB = "cronjot.db"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cronjot-snapshots",
        description="Manage cronjot metric snapshots",
    )
    parser.add_argument(
        "--db",
        default=DEFAULT_DB,
        metavar="PATH",
        help=f"Path to the SQLite database (default: {DEFAULT_DB})",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    build_snapshots_parser(subparsers)
    return parser


def main(argv=None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)
    if hasattr(args, "func"):
        args.func(args)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
