"""REPL (Read-Eval-Print Loop) for edway2."""

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from pathlib import Path

from edway2 import __version__


def get_history_path() -> Path:
    """Get path to command history file."""
    config_dir = Path.home() / ".config" / "edway2"
    config_dir.mkdir(parents=True, exist_ok=True)
    return config_dir / "history"


def run_repl(project_path: str | None) -> int:
    """Run the interactive REPL.

    Args:
        project_path: Path to project folder or audio file, or None.

    Returns:
        Exit code (0 for success).
    """
    print(f"edway2 {__version__}")
    print("Type 'h' for help, 'q' to quit.")

    session = PromptSession(
        history=FileHistory(str(get_history_path())),
    )

    while True:
        try:
            line = session.prompt(": ").strip()
        except (EOFError, KeyboardInterrupt):
            # Ctrl+D or Ctrl+C exits
            print()
            break

        if not line:
            continue

        # Handle quit commands
        if line == "q" or line == "qt":
            break

        # Unknown command
        print(f"? unknown command: {line.split()[0]}")

    return 0
