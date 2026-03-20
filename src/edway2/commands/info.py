"""Info commands: ?, =, sr, nc, ms, nb."""

import re

from edway2.commands import command
from edway2.parser import Command

if True:  # TYPE_CHECKING workaround for circular import
    from edway2.project import Project


def display_time(ms: int) -> str:
    """Format milliseconds as human-readable time.

    Args:
        ms: Milliseconds.

    Returns:
        Formatted string:
        - Under 60s: seconds with decimals (e.g., "0.5", "30.25")
        - 60s+: mm:ss.ss format (e.g., "1:00.00", "2:30.50")
    """
    total_seconds = ms / 1000

    if total_seconds < 60:
        # Show as seconds, strip trailing zeros
        if ms % 1000 == 0:
            return f"{int(total_seconds)}"
        else:
            return f"{total_seconds:.2f}".rstrip("0").rstrip(".")
    else:
        minutes = int(total_seconds // 60)
        seconds = total_seconds % 60
        return f"{minutes}:{seconds:05.2f}"


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

    Displays: project name, session name, track count, duration.
    """
    print(f"Project: {project.path.name}")
    print(f"Session: {project.session.timeline.name}")
    print(f"Tracks: {project.session.track_count}")
    print(f"Duration: {project.session.duration:.2f}s")

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
    # TODO: Implement with BlockView in Phase 5
    print("? not implemented yet")


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
        project.session.block_duration_ms = ms
        project.mark_dirty()
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
    # TODO: Implement with BlockView in Phase 5
    if cmd.arg:
        print("? nb set not implemented yet")
    else:
        # Show current count (rough calculation)
        duration = project.session.duration
        block_ms = project.session.block_duration_ms
        if duration > 0:
            count = int(duration * 1000 / block_ms) + 1
            print(f"blocks: {count}")
        else:
            print("blocks: 0")
