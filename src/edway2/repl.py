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

        # Parse command (simple split for now)
        parts = line.split(maxsplit=1)
        cmd = parts[0]
        arg = parts[1] if len(parts) > 1 else None

        # Handle quit commands
        if cmd == "q" or cmd == "qt":
            if project and project.is_dirty:
                print("? unsaved changes (use 'save' or 'q!' to force)")
                continue
            break

        if cmd == "q!":
            # Force quit without saving
            break

        # Handle save command
        if cmd == "save":
            if project:
                message = arg if arg else "save"
                project.save(message)
                print(f"Saved: {project.session_file.name}")
            else:
                print("? no project open")
            continue

        # Handle info command
        if cmd == "?":
            if project:
                print(f"Project: {project.path.name}")
                print(f"Session: {project.session.timeline.name}")
                print(f"Tracks: {project.session.track_count}")
                print(f"Duration: {project.session.duration:.2f}s")
            else:
                print("? no project open")
            continue

        # Unknown command
        print(f"? unknown command: {cmd}")

    return 0
