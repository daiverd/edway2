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


class TestClips:
    """Tests for clips command."""

    def test_clips_empty_track(self, tmp_project, capsys):
        """clips on empty track shows (empty)."""
        tmp_project.execute("clips")
        output = capsys.readouterr().out
        assert "(empty)" in output
        assert "Track 1" in output

    def test_clips_shows_clip_info(self, tmp_project, sample_wav, capsys):
        """clips shows clip with block range and source."""
        tmp_project.execute(f"r {sample_wav}")
        tmp_project.execute("clips")
        output = capsys.readouterr().out
        assert "Track 1" in output
        assert "1-1" in output  # 1-second clip = 1 block at 1000ms
        assert "test.wav" in output
        assert "[0.0-1.0]" in output  # source time range

    def test_clips_shows_gap(self, tmp_project, sample_wav_2sec, capsys):
        """clips shows gaps between clips."""
        # Load 2-second clip -> blocks 1-2
        tmp_project.execute(f"r {sample_wav_2sec}")
        # Delete block 1 (non-ripple) -> gap at block 1, clip remains at block 2
        tmp_project.execute("1d")
        tmp_project.execute("clips")
        output = capsys.readouterr().out
        assert "(gap)" in output

    def test_clips_shows_crossfade(self, tmp_project, sample_wav_2sec, capsys):
        """clips shows crossfade when clips overlap."""
        from edway2.session import Clip

        # Manually create overlapping clips
        track = tmp_project.session.tracks[0]

        # Copy file to sources first
        from edway2.audio import copy_to_sources, read_audio_info
        dest = copy_to_sources(sample_wav_2sec, tmp_project.path / "sources")
        info = read_audio_info(dest)

        # Clip 1: blocks 1-2 (0-2 seconds)
        clip1 = Clip(
            source=f"sources/{dest.name}",
            source_start=0.0,
            source_end=2.0,
            position=0.0,
        )
        # Clip 2: blocks 2-3 (1-3 seconds) - overlaps at block 2
        clip2 = Clip(
            source=f"sources/{dest.name}",
            source_start=0.0,
            source_end=2.0,
            position=1.0,
        )
        track.clips = [clip1, clip2]

        tmp_project.execute("clips")
        output = capsys.readouterr().out
        assert "(xf" in output  # crossfade indicator

    def test_clips_multiple_tracks(self, tmp_project, sample_wav, capsys):
        """clips shows all tracks."""
        tmp_project.execute(f"r {sample_wav}")
        tmp_project.execute("addtrack Vocals")
        tmp_project.execute("tr 2")
        tmp_project.execute(f"r {sample_wav}")

        tmp_project.execute("clips")
        output = capsys.readouterr().out
        assert "Track 1" in output
        assert "Track 2" in output
        assert "Vocals" in output

    def test_clips_shows_track_indicators(self, tmp_project, sample_wav, capsys):
        """clips shows current/muted/soloed indicators."""
        tmp_project.execute(f"r {sample_wav}")
        tmp_project.execute("mute")  # mute track 1

        tmp_project.execute("clips")
        output = capsys.readouterr().out
        assert "[" in output and "M" in output  # muted indicator
