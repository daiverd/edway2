"""Tests for git undo system (Phase 7)."""

import pytest


class TestCommitBeforeEdit:
    """Tests for commit-before-edit behavior."""

    def test_first_edit_marks_dirty(self, tmp_project, sample_wav):
        """First edit marks project dirty but doesn't commit."""
        commits_before = len(list(tmp_project.repo.iter_commits()))
        tmp_project.execute(f"r {sample_wav}")
        commits_after = len(list(tmp_project.repo.iter_commits()))
        assert tmp_project.is_dirty
        assert commits_after == commits_before

    def test_second_edit_commits_first(self, tmp_project, sample_wav):
        """Second edit commits the first edit."""
        commits_before = len(list(tmp_project.repo.iter_commits()))
        tmp_project.execute(f"r {sample_wav}")
        tmp_project.execute("ms 500")  # second edit
        commits_after = len(list(tmp_project.repo.iter_commits()))
        assert commits_after == commits_before + 1  # "r test.wav" committed

    def test_save_commits(self, tmp_project, sample_wav):
        """Save commits pending changes."""
        commits_before = len(list(tmp_project.repo.iter_commits()))
        tmp_project.execute(f"r {sample_wav}")
        tmp_project.execute("save")
        commits_after = len(list(tmp_project.repo.iter_commits()))
        assert commits_after == commits_before + 1
        assert not tmp_project.is_dirty


class TestUndo:
    """Tests for u (undo) command."""

    def test_undo_navigates_back(self, tmp_project, sample_wav):
        """u moves back in history."""
        tmp_project.execute(f"r {sample_wav}")
        tmp_project.execute("save")
        tmp_project.execute("ms 500")
        tmp_project.execute("save")

        assert tmp_project.session.block_duration_ms == 500
        tmp_project.execute("u")
        assert tmp_project.session.block_duration_ms == 1000

    def test_undo_no_commit(self, tmp_project, sample_wav):
        """u doesn't create commits."""
        tmp_project.execute(f"r {sample_wav}")
        tmp_project.execute("save")
        tmp_project.execute("ms 500")
        tmp_project.execute("save")

        commits_before = len(list(tmp_project.repo.iter_commits()))
        tmp_project.execute("u")
        commits_after = len(list(tmp_project.repo.iter_commits()))
        assert commits_after == commits_before

    def test_undo_increments_offset(self, tmp_project, sample_wav):
        """u increments undo offset."""
        tmp_project.execute(f"r {sample_wav}")
        tmp_project.execute("save")
        tmp_project.execute("ms 500")
        tmp_project.execute("save")

        assert tmp_project._undo_offset == 0
        tmp_project.execute("u")
        assert tmp_project._undo_offset == 1

    def test_undo_while_dirty_errors(self, tmp_project, sample_wav, capsys):
        """u while dirty shows error."""
        tmp_project.execute(f"r {sample_wav}")  # dirty
        tmp_project.execute("u")
        output = capsys.readouterr().out
        assert "unsaved changes" in output

    def test_undo_at_oldest_errors(self, tmp_project, capsys):
        """u at initial commit shows error."""
        tmp_project.execute("u")
        output = capsys.readouterr().out
        assert "oldest" in output


class TestUndoForce:
    """Tests for u! (force undo) command."""

    def test_undo_force_discards(self, tmp_project, sample_wav):
        """u! discards uncommitted changes."""
        tmp_project.execute(f"r {sample_wav}")
        tmp_project.execute("save")
        tmp_project.execute("ms 500")  # dirty
        assert tmp_project.session.block_duration_ms == 500

        tmp_project.execute("u!")
        assert tmp_project.session.block_duration_ms == 1000
        assert not tmp_project.is_dirty

    def test_undo_force_shows_message(self, tmp_project, sample_wav, capsys):
        """u! shows confirmation message."""
        tmp_project.execute(f"r {sample_wav}")
        tmp_project.execute("save")
        tmp_project.execute("ms 500")
        tmp_project.execute("u!")
        output = capsys.readouterr().out
        assert "discarded" in output


class TestRedo:
    """Tests for U (redo) command."""

    def test_redo_moves_forward(self, tmp_project, sample_wav):
        """U moves forward after u."""
        tmp_project.execute(f"r {sample_wav}")
        tmp_project.execute("save")
        tmp_project.execute("ms 500")
        tmp_project.execute("save")

        tmp_project.execute("u")  # back to ms=1000
        assert tmp_project.session.block_duration_ms == 1000

        tmp_project.execute("U")  # forward to ms=500
        assert tmp_project.session.block_duration_ms == 500

    def test_redo_decrements_offset(self, tmp_project, sample_wav):
        """U decrements undo offset."""
        tmp_project.execute(f"r {sample_wav}")
        tmp_project.execute("save")
        tmp_project.execute("ms 500")
        tmp_project.execute("save")

        tmp_project.execute("u")
        assert tmp_project._undo_offset == 1

        tmp_project.execute("U")
        assert tmp_project._undo_offset == 0

    def test_redo_at_latest_errors(self, tmp_project, sample_wav, capsys):
        """U at latest shows error."""
        tmp_project.execute(f"r {sample_wav}")
        tmp_project.execute("save")
        tmp_project.execute("U")
        output = capsys.readouterr().out
        assert "latest" in output


class TestEditWhileViewingHistory:
    """Tests for editing after undo."""

    def test_edit_after_undo_creates_revert(self, tmp_project, sample_wav):
        """Editing after undo creates a revert commit."""
        tmp_project.execute(f"r {sample_wav}")
        tmp_project.execute("save")  # C1
        tmp_project.execute("ms 500")
        tmp_project.execute("save")  # C2
        tmp_project.execute("ms 250")
        tmp_project.execute("save")  # C3

        commits_before = len(list(tmp_project.repo.iter_commits()))

        tmp_project.execute("u")
        tmp_project.execute("u")  # viewing C1
        tmp_project.execute("ms 100")  # edit creates revert + marks dirty

        commits_after = len(list(tmp_project.repo.iter_commits()))
        assert commits_after == commits_before + 1  # revert commit
        assert tmp_project._undo_offset == 0
        assert tmp_project.is_dirty

    def test_edit_after_undo_resets_offset(self, tmp_project, sample_wav):
        """Editing after undo resets offset to 0."""
        tmp_project.execute(f"r {sample_wav}")
        tmp_project.execute("save")
        tmp_project.execute("ms 500")
        tmp_project.execute("save")

        tmp_project.execute("u")
        assert tmp_project._undo_offset == 1

        tmp_project.execute("ms 250")
        assert tmp_project._undo_offset == 0


class TestSaveWithTag:
    """Tests for save with tag name."""

    def test_save_creates_tag(self, tmp_project, sample_wav):
        """save name creates a git tag."""
        tmp_project.execute(f"r {sample_wav}")
        tmp_project.execute("save rough-mix")
        tags = [t.name for t in tmp_project.repo.tags]
        assert "rough-mix" in tags

    def test_duplicate_tag_gets_suffix(self, tmp_project, sample_wav):
        """Duplicate tag names get auto-suffixed."""
        tmp_project.execute(f"r {sample_wav}")
        tmp_project.execute("save mix")
        tmp_project.execute("ms 500")
        tmp_project.execute("save mix")
        tags = [t.name for t in tmp_project.repo.tags]
        assert "mix" in tags
        assert "mix_2" in tags

    def test_save_without_tag_no_tag(self, tmp_project, sample_wav):
        """save without name doesn't create tag."""
        tmp_project.execute(f"r {sample_wav}")
        tmp_project.execute("save")
        tags = [t.name for t in tmp_project.repo.tags]
        assert len(tags) == 0


class TestHistory:
    """Tests for uh (history) command."""

    def test_history_shows_commits(self, tmp_project, sample_wav, capsys):
        """uh displays commit history."""
        tmp_project.execute(f"r {sample_wav}")
        tmp_project.execute("save")
        tmp_project.execute("uh")
        output = capsys.readouterr().out
        assert "1." in output
        assert "Initial" in output or "save" in output

    def test_history_shows_current_marker(self, tmp_project, sample_wav, capsys):
        """uh marks current position with asterisk."""
        tmp_project.execute(f"r {sample_wav}")
        tmp_project.execute("save")
        tmp_project.execute("ms 500")
        tmp_project.execute("save")
        tmp_project.execute("u")  # go back one
        tmp_project.execute("uh")
        output = capsys.readouterr().out
        # The second commit (not third) should be marked
        lines = output.strip().split("\n")
        # Find the line with asterisk
        marked_line = [l for l in lines if "*" in l]
        assert len(marked_line) == 1

    def test_history_shows_tags(self, tmp_project, sample_wav, capsys):
        """uh shows tags in brackets."""
        tmp_project.execute(f"r {sample_wav}")
        tmp_project.execute("save rough-mix")
        tmp_project.execute("uh")
        output = capsys.readouterr().out
        assert "[rough-mix]" in output

    def test_history_oldest_first(self, tmp_project, sample_wav, capsys):
        """uh shows oldest commit first."""
        tmp_project.execute(f"r {sample_wav}")
        tmp_project.execute("save")
        tmp_project.execute("ms 500")
        tmp_project.execute("save")
        tmp_project.execute("uh")
        output = capsys.readouterr().out
        lines = [l.strip() for l in output.strip().split("\n") if l.strip()]
        # First line should be commit 1
        assert lines[0].startswith("1.") or "* 1." in lines[0] or "1." in lines[0]

    def test_history_shows_uncommitted(self, tmp_project, sample_wav, capsys):
        """uh shows uncommitted changes indicator."""
        tmp_project.execute(f"r {sample_wav}")
        tmp_project.execute("save")
        tmp_project.execute("ms 500")  # dirty
        tmp_project.execute("uh")
        output = capsys.readouterr().out
        assert "uncommitted" in output


class TestGitIgnore:
    """Tests for .gitignore configuration."""

    def test_gitignore_ignores_sources(self, tmp_project):
        """sources/ is in .gitignore."""
        gitignore = tmp_project.path / ".gitignore"
        content = gitignore.read_text()
        assert "sources/" in content

    def test_gitignore_ignores_renders(self, tmp_project):
        """renders/ is in .gitignore."""
        gitignore = tmp_project.path / ".gitignore"
        content = gitignore.read_text()
        assert "renders/" in content
