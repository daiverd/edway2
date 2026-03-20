"""Tests for playback commands (p, z)."""

import pytest
import numpy as np
from unittest.mock import MagicMock


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
        tmp_project.execute("z")
        mock_playback.assert_called_once()

    def test_z_with_seconds_arg(self, tmp_project, sample_wav, mock_playback):
        """Test z with explicit seconds."""
        tmp_project.execute(f"r {sample_wav}")
        tmp_project.execute("z0.5")  # play 0.5 seconds
        mock_playback.assert_called_once()

    def test_z_no_audio_shows_error(self, tmp_project, capsys):
        """Test z with no audio shows error."""
        tmp_project.execute("z")
        output = capsys.readouterr().out
        assert "? no audio" in output
