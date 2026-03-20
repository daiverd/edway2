"""Pytest fixtures for edway2 tests."""

import pytest
from pathlib import Path
import numpy as np
import soundfile as sf

from edway2.project import Project


@pytest.fixture
def tmp_project(tmp_path):
    """Create a temporary project for testing."""
    return Project.create(tmp_path / "test_project")


@pytest.fixture
def sample_wav(tmp_path):
    """Create a 1-second stereo WAV file for testing."""
    path = tmp_path / "test.wav"
    # 1 second of 440Hz sine wave, stereo
    t = np.linspace(0, 1, 44100)
    data = np.sin(2 * np.pi * 440 * t)
    data = np.column_stack([data, data])  # stereo
    sf.write(path, data, 44100)
    return path


@pytest.fixture
def sample_wav_2sec(tmp_path):
    """Create a 2-second stereo WAV file for testing."""
    path = tmp_path / "test_2sec.wav"
    t = np.linspace(0, 2, 88200)
    data = np.sin(2 * np.pi * 440 * t)
    data = np.column_stack([data, data])
    sf.write(path, data, 44100)
    return path


@pytest.fixture
def mock_input(mocker):
    """Mock prompt_toolkit input for REPL testing."""
    def _mock(lines):
        mocker.patch(
            "prompt_toolkit.PromptSession.prompt",
            side_effect=lines + [EOFError]
        )
    return _mock
