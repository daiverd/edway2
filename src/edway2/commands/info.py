"""Info commands: ?, =, sr, nc, ms, nb."""

import re
from math import ceil

from edway2.commands import command
from edway2.parser import Command

if True:  # TYPE_CHECKING workaround for circular import
    from edway2.project import Project


def display_time(ms: int) -> str:
    """Format milliseconds as human-readable time (MM:SS.mmm).

    Args:
        ms: Milliseconds.

    Returns:
        Formatted string with millisecond precision:
        - Under 60s: "SS.mmm" (e.g., "0.001", "30.500")
        - 60s+: "M:SS.mmm" (e.g., "1:00.000", "2:30.500")

    This matches the precision used by most DAWs (Pro Tools, Ardour, etc.)
    """
    total_seconds = ms / 1000
    minutes = int(total_seconds // 60)
    seconds = total_seconds % 60

    if minutes == 0:
        return f"{seconds:.3f}"
    else:
        return f"{minutes}:{seconds:06.3f}"


def parse_time_to_ms(arg: str) -> int | None:
    """Parse time notation, float seconds, or integer ms to milliseconds.

    Accepts:
        500         - 500 ms (integer = milliseconds)
        1.0         - 1 second = 1000 ms (float = seconds)
        0.5         - 0.5 seconds = 500 ms
        0:30        - 30 seconds = 30000 ms
        1:30        - 1 min 30 sec = 90000 ms
        0:00.500    - 500 ms
        @0:30       - 30 seconds (@ prefix optional)

    Returns:
        Milliseconds as int, or None if invalid.
    """
    arg = arg.strip()

    # Strip optional @ prefix
    if arg.startswith("@"):
        arg = arg[1:]

    # Try time notation: M:SS or M:SS.mmm
    time_match = re.match(r"^(\d+):(\d+)(?:\.(\d+))?$", arg)
    if time_match:
        minutes = int(time_match.group(1))
        seconds = int(time_match.group(2))
        millis = int(time_match.group(3)) if time_match.group(3) else 0
        return (minutes * 60 + seconds) * 1000 + millis

    # Try float (seconds) - must contain decimal point
    if "." in arg:
        try:
            seconds = float(arg)
            return int(seconds * 1000)
        except ValueError:
            return None

    # Try plain integer (milliseconds)
    try:
        return int(arg)
    except ValueError:
        return None


@command("?")
def cmd_info(project: "Project", cmd: Command) -> None:
    """Show session info.

    Displays: project name, session name, track count, duration, blocks.
    """
    print(f"Project: {project.path.name}")
    print(f"Session: {project.session.name}")
    print(f"Tracks: {project.session.track_count}")
    print(f"Duration: {project.session.duration:.2f}s")
    print(f"Blocks: {project.blocks.count} @ {display_time(project.session.block_duration_ms)}")

    if project.is_dirty:
        print("(unsaved changes)")


@command("=")
def cmd_show_position(project: "Project", cmd: Command) -> None:
    """Show block number of address.

    Usage:
        =       - show last block number ($)
        .=      - show current block number
        'a=     - show block number of mark a
    """
    blocks = project.blocks

    if cmd.addr1 is None:
        # No address = show $ (last block)
        print(blocks.count)
    elif cmd.addr1.type == "number":
        # Show the number itself (with offset applied)
        block = cmd.addr1.value + cmd.addr1.offset
        print(block)
    elif cmd.addr1.type == "dot":
        # Current position
        block = blocks.from_time(project.session.current_position)
        block += cmd.addr1.offset
        print(block)
    elif cmd.addr1.type == "dollar":
        # Last block
        block = blocks.count + cmd.addr1.offset
        print(block)
    elif cmd.addr1.type == "mark":
        # Mark position
        mark_name = cmd.addr1.value
        if mark_name not in project.session.marks:
            print(f"? mark not set: {mark_name}")
            return
        mark_time = project.session.marks[mark_name]
        block = blocks.from_time(mark_time) + cmd.addr1.offset
        print(block)
    elif cmd.addr1.type == "time":
        # Time address
        block = blocks.from_time(cmd.addr1.value) + cmd.addr1.offset
        print(block)


@command("sr")
def cmd_sample_rate(project: "Project", cmd: Command) -> None:
    """Show sample rate of current clip/track."""
    # TODO: Implement
    print("? not implemented yet")


@command("nc")
def cmd_channels(project: "Project", cmd: Command) -> None:
    """Show channel count of current clip/track."""
    # TODO: Implement
    print("? not implemented yet")


@command("ms")
def cmd_ms(project: "Project", cmd: Command) -> None:
    """Show or set block duration.

    Usage:
        ms          - show current block duration
        ms 500      - set to 500ms (integer = milliseconds)
        ms 1.0      - set to 1 second (float = seconds)
        ms 0:01     - set to 1 second (time notation)
    """
    if cmd.arg:
        ms = parse_time_to_ms(cmd.arg)
        if ms is None:
            print(f"? invalid time/number: {cmd.arg}")
            return
        if ms <= 0:
            print("? block duration must be positive")
            return
        project.prepare_edit()
        project.session.block_duration_ms = ms
        project.mark_dirty(f"ms {cmd.arg}")
        print(f"block duration: {display_time(ms)}")
    else:
        print(f"block duration: {display_time(project.session.block_duration_ms)}")


@command("nb")
def cmd_nb(project: "Project", cmd: Command) -> None:
    """Show or set number of blocks.

    Usage:
        nb        - show current block count
        nb 100    - adjust block duration to get 100 blocks
    """
    if cmd.arg:
        try:
            target_count = int(cmd.arg)
            if target_count <= 0:
                print("? block count must be positive")
                return
            duration = project.session.duration
            if duration <= 0:
                print("? no audio in session")
                return
            # Calculate block duration to achieve target count
            # Use ceil to ensure blocks are long enough (avoid extra block from rounding)
            new_ms = ceil((duration * 1000) / target_count)
            if new_ms <= 0:
                new_ms = 1  # minimum 1ms
            project.prepare_edit()
            project.session.block_duration_ms = new_ms
            project.mark_dirty(f"nb {cmd.arg}")
            print(f"blocks: {project.blocks.count} @ {display_time(new_ms)}")
        except ValueError:
            print(f"? invalid number: {cmd.arg}")
    else:
        print(f"blocks: {project.blocks.count}")
