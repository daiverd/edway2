"""Project management for edway2."""

from dataclasses import dataclass
from pathlib import Path

import git

from edway2.session import Session
from edway2.blocks import BlockView


@dataclass
class Project:
    """Represents an edway2 project folder."""

    path: Path
    session: Session
    repo: git.Repo
    _dirty: bool = False

    @classmethod
    def create(cls, path: Path) -> "Project":
        """Create a new project folder with structure.

        Creates:
            path/
            path/<name>.edway
            path/sources/
            path/renders/
            path/.git/

        Args:
            path: Path to project folder.

        Returns:
            New Project instance.
        """
        path = Path(path)

        # Create directory structure
        path.mkdir(parents=True, exist_ok=True)
        (path / "sources").mkdir(exist_ok=True)
        (path / "renders").mkdir(exist_ok=True)

        # Create session
        session = Session.new(name=path.name)

        # Initialize git repo
        repo = git.Repo.init(path)

        # Create .gitignore
        gitignore = path / ".gitignore"
        gitignore.write_text(
            "# Temporary files\n"
            "*.tmp\n"
            "*~\n"
        )

        # Save session file
        session_file = path / f"{path.name}.edway"
        session.to_file(session_file)

        # Initial commit
        repo.index.add([".gitignore", f"{path.name}.edway"])
        repo.index.commit("Initial project")

        return cls(path=path, session=session, repo=repo, _dirty=False)

    @classmethod
    def open(cls, path: Path) -> "Project":
        """Open an existing project.

        Args:
            path: Path to project folder.

        Returns:
            Project instance.

        Raises:
            FileNotFoundError: If project doesn't exist.
            ValueError: If path is not a valid project.
        """
        path = Path(path)

        if not path.is_dir():
            raise FileNotFoundError(f"Project not found: {path}")

        # Find session file
        session_file = path / f"{path.name}.edway"
        if not session_file.exists():
            # Try to find any .edway file
            edway_files = list(path.glob("*.edway"))
            if not edway_files:
                raise ValueError(f"No .edway file found in {path}")
            session_file = edway_files[0]

        # Load session
        session = Session.from_file(session_file)

        # Open git repo
        try:
            repo = git.Repo(path)
        except git.InvalidGitRepositoryError:
            # Initialize git if missing
            repo = git.Repo.init(path)

        return cls(path=path, session=session, repo=repo, _dirty=False)

    def save(self, message: str = "edit") -> None:
        """Save session and commit.

        Args:
            message: Commit message.
        """
        # Save session file
        self.session.to_file(self.session_file)

        # Stage and commit
        self.repo.index.add([self.session_file.name])
        self.repo.index.commit(message)

        self._dirty = False

    def mark_dirty(self) -> None:
        """Mark project as having unsaved changes."""
        self._dirty = True

    @property
    def is_dirty(self) -> bool:
        """Check if project has unsaved changes."""
        return self._dirty

    def undo(self) -> bool:
        """Undo last edit (git checkout HEAD~1).

        Returns:
            True if undo succeeded, False if at initial commit.
        """
        try:
            # Check if we have a parent commit
            if not self.repo.head.commit.parents:
                return False

            # Reset to previous commit
            self.repo.git.checkout("HEAD~1", "--", self.session_file.name)

            # Reload session
            self.session = Session.from_file(self.session_file)
            self._dirty = False
            return True
        except git.GitCommandError:
            return False

    def redo(self) -> bool:
        """Redo last undone edit.

        Returns:
            True if redo succeeded, False if nothing to redo.
        """
        # Git doesn't have native redo - this is a simplified implementation
        # A full implementation would track the reflog
        try:
            self.repo.git.checkout("HEAD@{1}", "--", self.session_file.name)
            self.session = Session.from_file(self.session_file)
            self._dirty = False
            return True
        except git.GitCommandError:
            return False

    def execute(self, line: str) -> None:
        """Parse and execute a command line.

        Args:
            line: Command line to execute.
        """
        from edway2.parser import parse
        from edway2.errors import ParseError
        from edway2 import commands

        line = line.strip()
        if not line:
            return

        try:
            cmd = parse(line)
            commands.execute(self, cmd)
        except ParseError as e:
            print(f"? syntax error: {e}")
        except ValueError as e:
            print(f"? {e}")

    def resolve_path(self, filepath: Path) -> str:
        """Return relative path if inside project, absolute otherwise.

        Args:
            filepath: Path to resolve.

        Returns:
            String path (relative or absolute).
        """
        filepath = Path(filepath).resolve()
        try:
            return str(filepath.relative_to(self.path.resolve()))
        except ValueError:
            return str(filepath)

    @property
    def sources_dir(self) -> Path:
        """Path to sources directory."""
        return self.path / "sources"

    @property
    def renders_dir(self) -> Path:
        """Path to renders directory."""
        return self.path / "renders"

    @property
    def session_file(self) -> Path:
        """Path to session .edway file."""
        return self.path / f"{self.path.name}.edway"

    @property
    def blocks(self) -> BlockView:
        """Get block view for current session."""
        return BlockView(
            duration_seconds=self.session.duration,
            block_duration_ms=self.session.block_duration_ms,
        )
