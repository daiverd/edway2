"""Tests for playback commands (p, z)."""

import pytest
import numpy as np
from unittest.mock import MagicMock

from edway2.session import Track, Clip
from edway2.commands.playback import find_clip_overlaps, apply_crossfade


@pytest.fixture
def mock_playback(mocker):
    """Mock the play_until_keypress function."""
    mock = mocker.patch("edway2.commands.playback.play_until_keypress", return_value=False)
    return mock


class TestPlayCommand:
    """Tests for the p (play) command."""

    def test_play_calls_playback(self, tmp_project, sample_wav, mock_playback):
        """Test p command calls play_until_keypress."""
        tmp_project.execute(f"r {sample_wav}")
        tmp_project.execute("p")
        mock_playback.assert_called_once()

    def test_play_no_audio_shows_error(self, tmp_project, capsys):
        """Test p with no audio shows error."""
        tmp_project.execute("p")
        output = capsys.readouterr().out
        assert "? no audio" in output

    def test_play_range(self, tmp_project, sample_wav, mock_playback):
        """Test playing a specific block range."""
        tmp_project.execute(f"r {sample_wav}")
        tmp_project.execute("1,1p")  # just block 1
        mock_playback.assert_called_once()
        # Check that audio data was passed
        args, kwargs = mock_playback.call_args
        audio_data = args[0]
        assert len(audio_data) > 0

    def test_play_single_block(self, tmp_project, sample_wav, mock_playback):
        """Test playing a single block."""
        tmp_project.execute(f"r {sample_wav}")
        tmp_project.execute("1p")
        mock_playback.assert_called_once()

    def test_play_to_end(self, tmp_project, sample_wav, mock_playback):
        """Test playing from block to end."""
        tmp_project.execute(f"r {sample_wav}")
        tmp_project.session.current_position = 0.0  # reset position
        tmp_project.execute(".,$p")  # current to end
        mock_playback.assert_called_once()

    def test_play_stopped_shows_message(self, tmp_project, sample_wav, mocker, capsys):
        """Test that stopping playback shows (stopped) message."""
        mocker.patch("edway2.commands.playback.play_until_keypress", return_value=True)
        tmp_project.execute(f"r {sample_wav}")
        tmp_project.execute("p")
        output = capsys.readouterr().out
        assert "(stopped)" in output

    def test_play_out_of_range_shows_error(self, tmp_project, sample_wav, capsys):
        """Test playing block past end shows error."""
        tmp_project.execute(f"r {sample_wav}")  # 1 second = 1 block at 1000ms
        tmp_project.execute("100p")  # way past end
        output = capsys.readouterr().out
        assert "? block 100 out of range" in output


class TestPlaySecondsCommand:
    """Tests for the z (play seconds) command."""

    def test_z_plays_default_seconds(self, tmp_project, sample_wav, mock_playback):
        """Test z plays by default."""
        tmp_project.execute(f"r {sample_wav}")
        tmp_project.session.current_position = 0.0  # reset position
        tmp_project.execute("z")
        mock_playback.assert_called_once()

    def test_z_with_seconds_arg(self, tmp_project, sample_wav, mock_playback):
        """Test z with explicit seconds."""
        tmp_project.execute(f"r {sample_wav}")
        tmp_project.session.current_position = 0.0  # reset position
        tmp_project.execute("z0.5")  # play 0.5 seconds
        mock_playback.assert_called_once()

    def test_z_no_audio_shows_error(self, tmp_project, capsys):
        """Test z with no audio shows error."""
        tmp_project.execute("z")
        output = capsys.readouterr().out
        assert "? no audio" in output


class TestFindClipOverlaps:
    """Tests for overlap detection between clips."""

    def test_no_overlap(self):
        """Clips that don't overlap return empty list."""
        track = Track(name="Test")
        clip1 = Clip(source="a.wav", source_start=0, source_end=5, position=0)
        clip2 = Clip(source="b.wav", source_start=0, source_end=5, position=10)
        track.clips = [clip1, clip2]

        overlaps = find_clip_overlaps(track, clip1)
        assert overlaps == []

    def test_overlap_this_clip_fades_in(self):
        """When other clip starts first, this clip fades in."""
        track = Track(name="Test")
        clip1 = Clip(source="a.wav", source_start=0, source_end=10, position=0)  # 0-10
        clip2 = Clip(source="b.wav", source_start=0, source_end=10, position=5)  # 5-15
        track.clips = [clip1, clip2]

        # clip2 overlaps with clip1 which started earlier, so clip2 fades IN
        overlaps = find_clip_overlaps(track, clip2)
        assert len(overlaps) == 1
        overlap_start, overlap_end, fade_type = overlaps[0]
        assert overlap_start == 5.0  # overlap starts at clip2's start
        assert overlap_end == 10.0   # overlap ends at clip1's end
        assert fade_type == 'in'

    def test_overlap_this_clip_fades_out(self):
        """When this clip starts first, it fades out."""
        track = Track(name="Test")
        clip1 = Clip(source="a.wav", source_start=0, source_end=10, position=0)  # 0-10
        clip2 = Clip(source="b.wav", source_start=0, source_end=10, position=5)  # 5-15
        track.clips = [clip1, clip2]

        # clip1 started first, so it fades OUT where clip2 starts
        overlaps = find_clip_overlaps(track, clip1)
        assert len(overlaps) == 1
        overlap_start, overlap_end, fade_type = overlaps[0]
        assert overlap_start == 5.0
        assert overlap_end == 10.0
        assert fade_type == 'out'

    def test_multiple_overlaps(self):
        """Clip can overlap with multiple other clips."""
        track = Track(name="Test")
        clip1 = Clip(source="a.wav", source_start=0, source_end=5, position=0)   # 0-5
        clip2 = Clip(source="b.wav", source_start=0, source_end=15, position=3)  # 3-18
        clip3 = Clip(source="c.wav", source_start=0, source_end=5, position=15)  # 15-20
        track.clips = [clip1, clip2, clip3]

        # clip2 overlaps with clip1 (fades in at 3-5) and clip3 (fades out at 15-18)
        overlaps = find_clip_overlaps(track, clip2)
        assert len(overlaps) == 2


class TestApplyCrossfade:
    """Tests for applying crossfade envelopes."""

    def test_fade_in(self):
        """Fade in ramps from 0 to 1."""
        data = np.ones((100, 2), dtype=np.float32)
        overlaps = [(0.0, 1.0, 'in')]  # fade in over 1 second
        result = apply_crossfade(data, 100, 0.0, overlaps)  # 100 samples = 1 sec

        # Start should be near 0, end should be near 1
        assert result[0, 0] < 0.1
        assert result[-1, 0] > 0.9
        # Should be monotonically increasing
        assert np.all(np.diff(result[:, 0]) >= 0)

    def test_fade_out(self):
        """Fade out ramps from 1 to 0."""
        data = np.ones((100, 2), dtype=np.float32)
        overlaps = [(0.0, 1.0, 'out')]  # fade out over 1 second
        result = apply_crossfade(data, 100, 0.0, overlaps)

        # Start should be near 1, end should be near 0
        assert result[0, 0] > 0.9
        assert result[-1, 0] < 0.1
        # Should be monotonically decreasing
        assert np.all(np.diff(result[:, 0]) <= 0)

    def test_no_overlaps_returns_unchanged(self):
        """No overlaps returns data unchanged."""
        data = np.ones((100, 2), dtype=np.float32)
        result = apply_crossfade(data, 100, 0.0, [])
        np.testing.assert_array_equal(result, data)

    def test_partial_fade(self):
        """Fade that only covers part of the data."""
        data = np.ones((100, 2), dtype=np.float32)
        # Fade in from 0.5s to 1.0s (only second half)
        overlaps = [(0.5, 1.0, 'in')]
        result = apply_crossfade(data, 100, 0.0, overlaps)

        # First half should be unchanged
        np.testing.assert_array_equal(result[:50], data[:50])
        # Second half should have fade
        assert result[50, 0] < 0.1
        assert result[-1, 0] > 0.9

    def test_does_not_modify_original(self):
        """Apply crossfade should not modify the original array."""
        data = np.ones((100, 2), dtype=np.float32)
        original = data.copy()
        overlaps = [(0.0, 1.0, 'in')]
        apply_crossfade(data, 100, 0.0, overlaps)
        np.testing.assert_array_equal(data, original)
