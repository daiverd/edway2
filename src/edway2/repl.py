"""REPL (Read-Eval-Print Loop) for edway2."""

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from pathlib import Path

from edway2 import __version__
from edway2.project import Project


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

    # Initialize or open project
    project: Project | None = None
    if project_path:
        path = Path(project_path)
        if path.exists() and path.is_dir():
            # Try to open existing project
            try:
                project = Project.open(path)
                print(f"Opened project: {path.name}")
            except ValueError:
                # Not a valid project, create new one
                project = Project.create(path)
                print(f"Created project: {path.name}")
        else:
            # Create new project
            project = Project.create(path)
            print(f"Created project: {path.name}")

    prompt_session = PromptSession(
        history=FileHistory(str(get_history_path())),
    )

    while True:
        try:
            line = prompt_session.prompt(": ").strip()
        except (EOFError, KeyboardInterrupt):
            # Ctrl+D or Ctrl+C exits
            print()
            break

        if not line:
            continue

        # Handle quit commands directly (need special processing)
        if line in ("q", "qt"):
            if project and project.is_dirty:
                print("? unsaved changes (use 'save' or 'q!' to force)")
                continue
            break

        if line == "q!":
            # Force quit without saving
            break

        # All other commands go through the dispatcher
        if project:
            project.execute(line)
        else:
            # No project open - only some commands work
            if line.startswith("h"):
                print("? help not implemented yet")
            else:
                print("? no project open")

    return 0
