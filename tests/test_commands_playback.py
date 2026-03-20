"""Tests for playback commands (p, z)."""

import pytest
import numpy as np
from unittest.mock import MagicMock


@pytest.fixture
def mock_sounddevice(mocker):
    """Mock the sounddevice module via lazy loader."""
    mock_sd = MagicMock()
    mocker.patch("edway2.audio._get_sounddevice", return_value=mock_sd)
    return mock_sd


class TestPlayCommand:
    """Tests for the p (play) command."""

    def test_play_calls_sounddevice(self, tmp_project, sample_wav, mock_sounddevice):
        """Test p command calls sounddevice.play."""
        tmp_project.execute(f"r {sample_wav}")
        tmp_project.execute("p")
        mock_sounddevice.play.assert_called_once()

    def test_play_no_audio_shows_error(self, tmp_project, capsys):
        """Test p with no audio shows error."""
        tmp_project.execute("p")
        output = capsys.readouterr().out
        assert "? no audio" in output

    def test_play_range(self, tmp_project, sample_wav, mock_sounddevice):
        """Test playing a specific block range."""
        tmp_project.execute(f"r {sample_wav}")
        tmp_project.execute("1,1p")  # just block 1
        mock_sounddevice.play.assert_called_once()
        # Check that audio data was passed
        args, kwargs = mock_sounddevice.play.call_args
        audio_data = args[0]
        assert len(audio_data) > 0

    def test_play_single_block(self, tmp_project, sample_wav, mock_sounddevice):
        """Test playing a single block."""
        tmp_project.execute(f"r {sample_wav}")
        tmp_project.execute("1p")
        mock_sounddevice.play.assert_called_once()

    def test_play_to_end(self, tmp_project, sample_wav, mock_sounddevice):
        """Test playing from block to end."""
        tmp_project.execute(f"r {sample_wav}")
        tmp_project.execute(".,$p")  # current to end
        mock_sounddevice.play.assert_called_once()


class TestPlaySecondsCommand:
    """Tests for the z (play seconds) command."""

    def test_z_plays_default_seconds(self, tmp_project, sample_wav, mock_sounddevice):
        """Test z plays 5 seconds by default."""
        tmp_project.execute(f"r {sample_wav}")
        tmp_project.execute("z")
        mock_sounddevice.play.assert_called_once()

    def test_z_with_seconds_arg(self, tmp_project, sample_wav, mock_sounddevice):
        """Test z with explicit seconds."""
        tmp_project.execute(f"r {sample_wav}")
        tmp_project.execute("z0.5")  # play 0.5 seconds
        mock_sounddevice.play.assert_called_once()

    def test_z_no_audio_shows_error(self, tmp_project, capsys):
        """Test z with no audio shows error."""
        tmp_project.execute("z")
        output = capsys.readouterr().out
        assert "? no audio" in output
