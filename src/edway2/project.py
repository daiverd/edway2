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
    _undo_offset: int = 0  # 0 = at HEAD, N = viewing HEAD~N
    _dirty_reason: str = ""  # description of what made us dirty

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
        # Sources and renders are immutable, only track .edway file
        gitignore = path / ".gitignore"
        gitignore.write_text(
            "# Audio files (immutable, not tracked)\n"
            "sources/\n"
            "renders/\n"
            "\n"
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

    def save(self, message: str = "save", tag: str | None = None) -> None:
        """Save session and commit. Optionally create a tag.

        Args:
            message: Commit message.
            tag: Optional tag name for this save point.
        """
        if not self._dirty:
            # Nothing to save, but maybe create tag
            if tag:
                self._create_tag(tag)
            return

        # Save session file
        self.session.to_file(self.session_file)

        # Stage and commit
        self.repo.index.add([self.session_file.name])
        self.repo.index.commit(message)

        self._dirty = False
        self._dirty_reason = ""

        # Create tag if requested
        if tag:
            self._create_tag(tag)

    def _create_tag(self, name: str) -> str:
        """Create a git tag, auto-suffixing if name exists.

        Args:
            name: Desired tag name.

        Returns:
            Actual tag name used (may have suffix).
        """
        existing_tags = {t.name for t in self.repo.tags}

        if name not in existing_tags:
            self.repo.create_tag(name)
            return name

        # Find next available suffix
        n = 2
        while f"{name}_{n}" in existing_tags:
            n += 1
        actual_name = f"{name}_{n}"
        self.repo.create_tag(actual_name)
        return actual_name

    def commit_if_dirty(self, message: str) -> None:
        """Commit pending changes before next edit.

        Args:
            message: Commit message for the pending changes.
        """
        if self._dirty:
            self.save(message)

    def mark_dirty(self, reason: str = "edit") -> None:
        """Mark project as having unsaved changes.

        Args:
            reason: Description of the change (used as commit message later).
        """
        self._dirty = True
        self._dirty_reason = reason

    @property
    def is_dirty(self) -> bool:
        """Check if project has unsaved changes."""
        return self._dirty

    def undo(self, force: bool = False) -> tuple[bool, str]:
        """Navigate to previous commit.

        Args:
            force: If True, discard uncommitted changes (u!).

        Returns:
            Tuple of (success, message).
        """
        if self._dirty and not force:
            return False, "unsaved changes (use u! to discard)"

        if self._dirty and force:
            # Discard changes by reloading from current commit
            self._checkout_offset(self._undo_offset)
            self._dirty = False
            # Don't increment offset - just discard
            return True, "changes discarded"

        # Count available commits
        commits = list(self.repo.iter_commits())
        max_offset = len(commits) - 1  # Can't go past initial commit

        if self._undo_offset >= max_offset:
            return False, "already at oldest"

        # Navigate back
        self._undo_offset += 1
        self._checkout_offset(self._undo_offset)
        return True, f"viewing {self._undo_offset} back"

    def redo(self) -> tuple[bool, str]:
        """Navigate forward in history.

        Returns:
            Tuple of (success, message).
        """
        if self._undo_offset == 0:
            return False, "already at latest"

        self._undo_offset -= 1
        self._checkout_offset(self._undo_offset)
        return True, "forward" if self._undo_offset > 0 else "at latest"

    def _checkout_offset(self, offset: int) -> None:
        """Checkout the .edway file at HEAD~offset and reload session.

        Args:
            offset: Number of commits back from HEAD.
        """
        if offset == 0:
            ref = "HEAD"
        else:
            ref = f"HEAD~{offset}"

        self.repo.git.checkout(ref, "--", self.session_file.name)
        self.session = Session.from_file(self.session_file)

    def prepare_edit(self) -> None:
        """Prepare for an edit: commit if dirty, handle undo state.

        Call this before any command that modifies the session.
        Uses the stored dirty reason as the commit message.
        """
        if self._undo_offset > 0:
            # We're viewing history and about to edit - create revert commit
            # The file already has the old content, just commit it
            self.session.to_file(self.session_file)
            self.repo.index.add([self.session_file.name])
            self.repo.index.commit(f"revert to {self._undo_offset} back")
            self._undo_offset = 0
            self._dirty = False
            self._dirty_reason = ""
        elif self._dirty:
            # Commit previous changes first
            self.save(message=self._dirty_reason)

    def history(self) -> list[dict]:
        """Return list of commits with metadata.

        Returns:
            List of dicts with: number, message, tags, is_current.
            Ordered oldest first (number 1 = first commit).
        """
        commits = list(self.repo.iter_commits())
        commits.reverse()  # Oldest first

        # Build tag lookup
        tag_lookup: dict[str, list[str]] = {}
        for tag in self.repo.tags:
            sha = tag.commit.hexsha
            if sha not in tag_lookup:
                tag_lookup[sha] = []
            tag_lookup[sha].append(tag.name)

        # Current position
        current_idx = len(commits) - 1 - self._undo_offset

        result = []
        for i, commit in enumerate(commits):
            result.append({
                "number": i + 1,
                "message": commit.message.strip(),
                "tags": tag_lookup.get(commit.hexsha, []),
                "is_current": i == current_idx,
            })

        return result

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
        """Get block view for current session.

        Blocks map to timeline positions including gaps. Gaps are just
        silent blocks - the user doesn't need to know the difference.
        """
        return BlockView(
            duration_seconds=self.session.duration,
            block_duration_ms=self.session.block_duration_ms,
        )
