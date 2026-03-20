"""Playback commands: p (play), z (play seconds)."""

from edway2.commands import command
from edway2.parser import Command

if True:  # TYPE_CHECKING workaround
    from edway2.project import Project


@command("p")
def cmd_play(project: "Project", cmd: Command) -> None:
    """Play audio.

    Usage:
        p           - play current block
        5p          - play block 5
        1,10p       - play blocks 1-10
        .,$p        - play from current to end
    """
    # TODO: Implement in Phase 6
    if project.session.duration == 0:
        print("? no audio in session")
        return
    print("? play not implemented yet (Phase 6)")


@command("z")
def cmd_play_seconds(project: "Project", cmd: Command) -> None:
    """Play N seconds from position.

    Usage:
        z           - play 5 seconds from current
        z10         - play 10 seconds from current
        5z10        - play 10 seconds from block 5
    """
    # TODO: Implement in Phase 6
    print("? play not implemented yet (Phase 6)")
