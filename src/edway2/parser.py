"""Command parser for edway2.

Grammar:
    command     := [range] cmd [dest] [argument]
    range       := addr ["," addr]
    addr        := position [offset]
    position    := NUMBER | "." | "$" | "'" LETTER | "@" TIME
    offset      := ("+" | "-") NUMBER
    dest        := addr  (for m, t, rm, rt only)
    argument    := SPACE rest_of_line
    TIME        := MINUTES ":" SECONDS ["." MILLIS]
"""

from dataclasses import dataclass
import re
from typing import Literal

from edway2.errors import ParseError


@dataclass
class Address:
    """A single address in a command."""

    type: Literal["number", "dot", "dollar", "mark", "time"]
    value: int | str | float | None  # block number, mark name, seconds, or None
    offset: int = 0  # for +N or -N

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Address):
            return NotImplemented
        return (
            self.type == other.type
            and self.value == other.value
            and self.offset == other.offset
        )


@dataclass
class Command:
    """Parsed command."""

    name: str  # "p", "d", "rm", etc.
    addr1: Address | None = None
    addr2: Address | None = None
    dest: Address | None = None  # for m, t, rm, rt
    arg: str | None = None  # for r, w, db, etc.

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Command):
            return NotImplemented
        return (
            self.name == other.name
            and self.addr1 == other.addr1
            and self.addr2 == other.addr2
            and self.dest == other.dest
            and self.arg == other.arg
        )


# Commands that take a destination address
DEST_COMMANDS = {"m", "t", "rm", "rt"}

# Commands that have attached arguments (no space needed)
# These won't be rejected just because the next char is alpha
ATTACHED_ARG_COMMANDS = {"k", "!"}

# Known commands (for disambiguation)
# Two-letter commands must come before single-letter to match first
COMMANDS = [
    # Multi-letter commands
    "save", "load", "quit", "help",
    "addtrack", "rmtrack", "tracks", "track",
    "mute", "solo",
    "region", "regions",
    "branch", "branches", "checkout", "tag",
    "split", "fxlist", "fxrm",
    "gen", "cap",
    # Two-letter commands
    "rm", "rt", "rd",  # ripple commands (must come before r)
    "db", "fi", "fo", "xf", "mx", "fx",
    "tr", "sr", "nc", "ms", "nb", "uh",
    "q!",  # force quit
    # Single-letter commands
    "p", "z", "d", "m", "t", "r", "w", "k", "q", "u", "U",
    "f", "l", "h", "?", "=", "!",
]


def parse(line: str) -> Command:
    """Parse command line into Command object.

    Args:
        line: Command line to parse.

    Returns:
        Parsed Command object.

    Raises:
        ParseError: If syntax is invalid.
    """
    line = line.strip()
    if not line:
        raise ParseError("empty command")

    pos = 0

    # Try to parse first address
    addr1, pos = _parse_address(line, pos)

    # Check for comma and second address (range)
    addr2 = None
    if pos < len(line) and line[pos] == ",":
        pos += 1
        addr2, pos = _parse_address(line, pos)

    # Parse command name
    cmd_name, pos = _parse_command_name(line, pos)
    if cmd_name is None:
        raise ParseError(f"unknown command at position {pos}")

    # For dest commands, try to parse destination address
    dest = None
    if cmd_name in DEST_COMMANDS:
        dest, pos = _parse_address(line, pos)

    # Parse argument (rest of line after optional space)
    arg = None
    if pos < len(line):
        rest = line[pos:]
        # Some commands have attached args (like z10, ka)
        if rest.startswith(" "):
            arg = rest[1:] if len(rest) > 1 else None
        else:
            # Attached argument (no space)
            arg = rest if rest else None

    return Command(
        name=cmd_name,
        addr1=addr1,
        addr2=addr2,
        dest=dest,
        arg=arg,
    )


def _parse_address(line: str, pos: int) -> tuple[Address | None, int]:
    """Parse an address starting at pos.

    Returns:
        Tuple of (Address or None, new position).
    """
    if pos >= len(line):
        return None, pos

    # Try each address type
    addr, new_pos = _parse_dot(line, pos)
    if addr is not None:
        return _parse_offset(line, new_pos, addr)

    addr, new_pos = _parse_dollar(line, pos)
    if addr is not None:
        return _parse_offset(line, new_pos, addr)

    addr, new_pos = _parse_mark(line, pos)
    if addr is not None:
        return _parse_offset(line, new_pos, addr)

    addr, new_pos = _parse_time(line, pos)
    if addr is not None:
        return _parse_offset(line, new_pos, addr)

    addr, new_pos = _parse_number(line, pos)
    if addr is not None:
        return _parse_offset(line, new_pos, addr)

    return None, pos


def _parse_dot(line: str, pos: int) -> tuple[Address | None, int]:
    """Parse '.' address."""
    if pos < len(line) and line[pos] == ".":
        return Address("dot", None), pos + 1
    return None, pos


def _parse_dollar(line: str, pos: int) -> tuple[Address | None, int]:
    """Parse '$' address."""
    if pos < len(line) and line[pos] == "$":
        return Address("dollar", None), pos + 1
    return None, pos


def _parse_mark(line: str, pos: int) -> tuple[Address | None, int]:
    """Parse 'x mark address (single lowercase letter)."""
    if pos + 1 < len(line) and line[pos] == "'":
        mark = line[pos + 1]
        if mark.isalpha() and mark.islower():
            return Address("mark", mark), pos + 2
        else:
            raise ParseError(f"invalid mark: '{mark}' (must be lowercase letter)")
    return None, pos


def _parse_time(line: str, pos: int) -> tuple[Address | None, int]:
    """Parse @M:SS[.mmm] time address."""
    if pos >= len(line) or line[pos] != "@":
        return None, pos

    # Match @M:SS or @M:SS.mmm
    pattern = r"@(\d+):(\d+)(?:\.(\d+))?"
    match = re.match(pattern, line[pos:])
    if not match:
        raise ParseError(f"invalid time address at position {pos}")

    minutes = int(match.group(1))
    seconds = int(match.group(2))
    millis = int(match.group(3)) if match.group(3) else 0

    # Convert to seconds
    total_seconds = minutes * 60 + seconds + millis / 1000

    return Address("time", total_seconds), pos + match.end()


def _parse_number(line: str, pos: int) -> tuple[Address | None, int]:
    """Parse numeric address."""
    match = re.match(r"\d+", line[pos:])
    if match:
        return Address("number", int(match.group())), pos + match.end()
    return None, pos


def _parse_offset(
    line: str, pos: int, addr: Address
) -> tuple[Address, int]:
    """Parse optional +N or -N offset."""
    if pos >= len(line):
        return addr, pos

    if line[pos] == "+":
        match = re.match(r"\+(\d+)", line[pos:])
        if match:
            addr.offset = int(match.group(1))
            return addr, pos + match.end()
    elif line[pos] == "-":
        match = re.match(r"-(\d+)", line[pos:])
        if match:
            addr.offset = -int(match.group(1))
            return addr, pos + match.end()

    return addr, pos


def _parse_command_name(line: str, pos: int) -> tuple[str | None, int]:
    """Parse command name at position.

    Returns:
        Tuple of (command name or None, new position).
    """
    if pos >= len(line):
        return None, pos

    # Try to match commands in order (longer first)
    for cmd in COMMANDS:
        if line[pos:].startswith(cmd):
            # Make sure we're not matching a prefix of a longer token
            end_pos = pos + len(cmd)
            if end_pos < len(line):
                next_char = line[end_pos]
                # For single-letter commands, check if next is valid separator
                # Exception: commands that have attached arguments (k, !)
                if len(cmd) == 1 and next_char.isalpha() and cmd not in ATTACHED_ARG_COMMANDS:
                    # This might be part of a longer command name
                    continue
            return cmd, end_pos

    return None, pos
