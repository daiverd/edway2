"""Undo commands: u, u!, U, uh."""

from edway2.commands import command
from edway2.parser import Command

if True:  # TYPE_CHECKING workaround
    from edway2.project import Project


@command("u")
def cmd_undo(project: "Project", cmd: Command) -> None:
    """Navigate to previous commit.

    Usage:
        u         - view previous state
        u u u     - view 3 states back

    If there are unsaved changes, shows error. Use u! to discard.
    """
    success, message = project.undo(force=False)
    if not success:
        print(f"? {message}")


@command("u!")
def cmd_undo_force(project: "Project", cmd: Command) -> None:
    """Discard changes and navigate to previous commit.

    Usage:
        u!        - discard uncommitted changes

    Use this to undo a mistake without polluting history.
    """
    success, message = project.undo(force=True)
    if not success:
        print(f"? {message}")
    else:
        print(f"({message})")


@command("U")
def cmd_redo(project: "Project", cmd: Command) -> None:
    """Navigate forward in history.

    Usage:
        U         - view next state (after undo)

    Only works after using u to go back in history.
    """
    success, message = project.redo()
    if not success:
        print(f"? {message}")


@command("uh")
def cmd_history(project: "Project", cmd: Command) -> None:
    """Show edit history.

    Displays numbered list of commits, oldest first.
    Current position marked with asterisk.
    Tags shown in brackets.

    Example output:
        1. Project created
        2. r test.wav
      * 3. [rough-mix] 2,3d
        4. 5,6d
        (uncommitted changes)
    """
    history = project.history()

    for entry in history:
        # Format tags
        tag_str = ""
        if entry["tags"]:
            tag_str = "[" + ", ".join(entry["tags"]) + "] "

        # Format marker
        marker = "*" if entry["is_current"] else " "

        print(f"  {marker} {entry['number']}. {tag_str}{entry['message']}")

    # Show uncommitted changes indicator
    if project.is_dirty:
        print("    (uncommitted changes)")
