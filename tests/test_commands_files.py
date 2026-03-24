"""Tests for file commands (r, w, save, load)."""

import pytest
from pathlib import Path

from edway2.project import Project


class TestReadCommand:
    """Tests for the r (read) command."""

    def test_read_creates_clip(self, tmp_project, sample_wav):
        """Test reading a file creates a clip on the timeline."""
        tmp_project.execute(f"r {sample_wav}")
        track = tmp_project.session.tracks[0]
        assert len(track.clips) == 1

    def test_read_sets_duration(self, tmp_project, sample_wav):
        """Test reading a file sets correct duration."""
        tmp_project.execute(f"r {sample_wav}")
        # 1 second file
        assert abs(tmp_project.session.duration - 1.0) < 0.01

    def test_read_copies_to_sources(self, tmp_project, sample_wav):
        """Test reading copies file to sources folder."""
        tmp_project.execute(f"r {sample_wav}")
        sources = list(tmp_project.sources_dir.glob("*.wav"))
        assert len(sources) == 1

    def test_read_nonexistent_errors(self, tmp_project, capsys):
        """Test reading nonexistent file shows error."""
        tmp_project.execute("r /nonexistent.wav")
        output = capsys.readouterr().out
        assert "? file not found" in output

    def test_read_at_position(self, tmp_project, sample_wav, sample_wav_2sec):
        """Test reading at specific block position."""
        tmp_project.execute(f"r {sample_wav_2sec}")  # 2 seconds
        tmp_project.execute(f"1r {sample_wav}")  # insert at block 1
        # Should have 2 clips now
        track = tmp_project.session.tracks[0]
        assert len(track.clips) == 2

    def test_read_marks_dirty(self, tmp_project, sample_wav):
        """Test reading marks project as dirty."""
        assert not tmp_project.is_dirty
        tmp_project.execute(f"r {sample_wav}")
        assert tmp_project.is_dirty

    def test_read_mp3(self, tmp_project, tmp_path):
        """Test reading MP3 file (via pedalboard)."""
        # Create a simple MP3 using pedalboard
        import numpy as np
        from pedalboard.io import AudioFile

        mp3_path = tmp_path / "test.mp3"
        t = np.linspace(0, 1, 44100)
        data = np.sin(2 * np.pi * 440 * t).astype(np.float32)
        data = np.column_stack([data, data])

        with AudioFile(str(mp3_path), "w", 44100, 2) as f:
            f.write(data.T)

        tmp_project.execute(f"r {mp3_path}")
        assert tmp_project.session.duration > 0


class TestInfoCommand:
    """Tests for the ? (info) command."""

    def test_info_shows_duration(self, tmp_project, sample_wav, capsys):
        """Test ? command shows duration after reading file."""
        tmp_project.execute(f"r {sample_wav}")
        tmp_project.execute("?")
        output = capsys.readouterr().out
        assert "Duration:" in output or "duration" in output.lower()

    def test_info_no_project(self, capsys):
        """Test ? with no audio shows appropriate message."""
        from edway2.project import Project
        import tempfile
        with tempfile.TemporaryDirectory() as tmp:
            proj = Project.create(Path(tmp) / "test")
            proj.execute("?")
            output = capsys.readouterr().out
            # Should show project info even with no audio
            assert "Project:" in output or "project" in output.lower()
