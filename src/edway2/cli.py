"""CLI entry point for edway2."""

import argparse
import sys

from edway2 import __version__


def main(argv: list[str] | None = None) -> int:
    """Main entry point for edway2.

    Args:
        argv: Command line arguments. Defaults to sys.argv[1:].

    Returns:
        Exit code (0 for success).
    """
    parser = argparse.ArgumentParser(
        prog="edway2",
        description="Non-destructive multitrack audio editor with line-editor UX",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"edway2 {__version__}",
    )
    parser.add_argument(
        "path",
        nargs="?",
        help="Project folder or audio file to open",
    )
    parser.add_argument(
        "-p", "--play",
        action="store_true",
        help="Play file and exit (non-interactive)",
    )
    parser.add_argument(
        "-t", "--timing",
        action="store_true",
        help="Show file info and exit (non-interactive)",
    )
    parser.add_argument(
        "-c", "--convert",
        metavar="FORMAT",
        help="Convert file to format and exit (non-interactive)",
    )

    args = parser.parse_args(argv)

    # Non-interactive modes (to be implemented)
    if args.play:
        print("Play mode not yet implemented")
        return 1

    if args.timing:
        print("Timing mode not yet implemented")
        return 1

    if args.convert:
        print("Convert mode not yet implemented")
        return 1

    # Interactive mode (to be implemented)
    print(f"edway2 {__version__}")
    print("Interactive mode not yet implemented")
    return 0
