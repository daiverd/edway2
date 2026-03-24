"""Command implementations for edway2.

Commands are registered via the @command decorator and dispatched
through the execute() function.
"""

from typing import Callable, TYPE_CHECKING

if TYPE_CHECKING:
    from edway2.project import Project
    from edway2.parser import Command

# Registry: command name → handler function
_commands: dict[str, Callable[["Project", "Command"], None]] = {}


def command(name: str):
    """Decorator to register a command handler.

    Args:
        name: Command name (e.g., "r", "p", "save").

    Usage:
        @command("r")
        def cmd_read(project: Project, cmd: Command) -> None:
            ...
    """
    def decorator(func: Callable[["Project", "Command"], None]):
        _commands[name] = func
        return func
    return decorator


def get_handler(name: str) -> Callable[["Project", "Command"], None] | None:
    """Get handler for a command name.

    Args:
        name: Command name.

    Returns:
        Handler function or None if not found.
    """
    return _commands.get(name)


def execute(project: "Project", cmd: "Command") -> None:
    """Execute a parsed command.

    Args:
        project: Project to operate on.
        cmd: Parsed command.

    Raises:
        ValueError: If command not found.
    """
    handler = get_handler(cmd.name)
    if handler is None:
        raise ValueError(f"unknown command: {cmd.name}")
    handler(project, cmd)


# Import command modules to register handlers
from edway2.commands import files  # noqa: E402, F401
from edway2.commands import info  # noqa: E402, F401
from edway2.commands import misc  # noqa: E402, F401
from edway2.commands import playback  # noqa: E402, F401
from edway2.commands import undo  # noqa: E402, F401
from edway2.commands import editing  # noqa: E402, F401
from edway2.commands import tracks  # noqa: E402, F401
from edway2.commands import marks  # noqa: E402, F401
from edway2.commands import export  # noqa: E402, F401
