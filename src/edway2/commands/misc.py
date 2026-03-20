"""Misc commands: h (help), ! (shell), l (label)."""

from edway2.commands import command
from edway2.parser import Command

if True:  # TYPE_CHECKING workaround
    from edway2.project import Project


HELP_TEXT = """
edway2 - non-destructive multitrack audio editor

Ready to test:
  r <file>      Read audio file into current track
  ?             Show session info (duration, tracks, blocks)
  =             Show last block number (or [addr]= for any address)
  ms [N]        Show/set block duration (500, 0.5, 0:00.500)
  nb [N]        Show/set number of blocks
  save [msg]    Save session (commits to git)
  !<cmd>        Run shell command
  l [text]      Show/set session label
  h             Show this help
  q             Quit (prompts if unsaved)
  q!            Force quit

Addresses (for use with =):
  5             Block number
  .             Current position
  $             Last block
  'a            Mark a
  @1:30         Time (1 min 30 sec)
  $-3           Offset (3 blocks before end)

Not yet implemented:
  p, z          Playback (Phase 6)
  d, m, t       Editing (Phase 8)
  rd, rm, rt    Ripple editing (Phase 9)
  k, region     Marks (Phase 10)
  w             Export (Phase 13)
"""


@command("h")
def cmd_help(project: "Project", cmd: Command) -> None:
    """Show help.

    Usage:
        h         - show overview
        h <cmd>   - show help for command
    """
    if cmd.arg:
        # TODO: Per-command help
        print(f"? help for '{cmd.arg}' not available yet")
    else:
        print(HELP_TEXT.strip())


@command("!")
def cmd_shell(project: "Project", cmd: Command) -> None:
    """Run shell command.

    Usage:
        !<cmd>    - run command
        !         - open interactive shell
    """
    import subprocess

    if cmd.arg:
        try:
            result = subprocess.run(
                cmd.arg,
                shell=True,
                capture_output=True,
                text=True,
            )
            if result.stdout:
                print(result.stdout, end="")
            if result.stderr:
                print(result.stderr, end="")
        except Exception as e:
            print(f"? shell error: {e}")
    else:
        print("? interactive shell not implemented")


@command("l")
def cmd_label(project: "Project", cmd: Command) -> None:
    """Show or set session label.

    Usage:
        l           - show current label
        l <text>    - set label
    """
    if cmd.arg:
        project.session.timeline.name = cmd.arg
        project.mark_dirty()
        print(f"label: {cmd.arg}")
    else:
        print(f"label: {project.session.timeline.name}")
