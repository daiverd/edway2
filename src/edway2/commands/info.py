"""Info commands: ?, =, sr, nc, ms, nb."""

from edway2.commands import command
from edway2.parser import Command

if True:  # TYPE_CHECKING workaround for circular import
    from edway2.project import Project


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
    """Show or set block duration in milliseconds.

    Usage:
        ms        - show current block duration
        ms 500    - set to 500ms blocks
    """
    if cmd.arg:
        try:
            ms = int(cmd.arg)
            if ms <= 0:
                print("? block duration must be positive")
                return
            project.session.block_duration_ms = ms
            project.mark_dirty()
            print(f"block duration: {ms}ms")
        except ValueError:
            print(f"? invalid number: {cmd.arg}")
    else:
        print(f"block duration: {project.session.block_duration_ms}ms")


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
