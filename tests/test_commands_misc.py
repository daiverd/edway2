"""Tests for misc commands (h, !, l)."""

import pytest


class TestHelp:
    """Tests for h (help) command."""

    def test_help_overview(self, tmp_project, capsys):
        """h shows overview."""
        tmp_project.execute("h")

        output = capsys.readouterr().out
        assert "edway2" in output
        assert "Commands" in output
        assert "File:" in output
        assert "Playback:" in output

    def test_help_specific_command(self, tmp_project, capsys):
        """h p shows help for play command."""
        tmp_project.execute("h p")

        output = capsys.readouterr().out
        assert "Play" in output
        assert "1,10p" in output

    def test_help_ripple_delete(self, tmp_project, capsys):
        """h rd shows help for ripple delete."""
        tmp_project.execute("h rd")

        output = capsys.readouterr().out
        assert "Ripple delete" in output
        assert "shifts" in output.lower()

    def test_help_unknown_command(self, tmp_project, capsys):
        """h xyz shows error for unknown command."""
        tmp_project.execute("h xyz")

        output = capsys.readouterr().out
        assert "no help for" in output

    def test_help_tracks(self, tmp_project, capsys):
        """h tracks shows help for tracks command."""
        tmp_project.execute("h tracks")

        output = capsys.readouterr().out
        assert "List" in output
        assert "muted" in output.lower() or "M" in output

    def test_help_save(self, tmp_project, capsys):
        """h save shows help for save command."""
        tmp_project.execute("h save")

        output = capsys.readouterr().out
        assert "Save" in output
        assert "tag" in output.lower()


class TestLabel:
    """Tests for l (label) command."""

    def test_show_label(self, tmp_project, capsys):
        """l shows current label."""
        tmp_project.execute("l")

        output = capsys.readouterr().out
        assert "label:" in output

    def test_set_label(self, tmp_project, capsys):
        """l text sets label."""
        tmp_project.execute("l My Song")

        assert tmp_project.session.name == "My Song"
        output = capsys.readouterr().out
        assert "My Song" in output

    def test_set_label_marks_dirty(self, tmp_project):
        """l text marks project dirty."""
        assert not tmp_project.is_dirty
        tmp_project.execute("l New Label")
        assert tmp_project.is_dirty
