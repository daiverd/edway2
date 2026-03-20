"""Tests for edway2 CLI."""

import pytest

from edway2 import __version__
from edway2.cli import main


def test_version(capsys):
    """Test --version flag prints version."""
    with pytest.raises(SystemExit) as exc_info:
        main(["--version"])

    assert exc_info.value.code == 0
    captured = capsys.readouterr()
    assert __version__ in captured.out
    assert "edway2" in captured.out


def test_version_value():
    """Test version is set correctly."""
    assert __version__ == "0.1.0"


def test_main_no_args(mocker):
    """Test running with no arguments starts REPL."""
    # Mock the REPL to avoid interactive prompt
    mock_repl = mocker.patch("edway2.repl.run_repl", return_value=0)
    result = main([])
    assert result == 0
    mock_repl.assert_called_once_with(None)


def test_play_not_implemented(capsys):
    """Test -p flag shows not implemented."""
    result = main(["-p"])
    assert result == 1
    captured = capsys.readouterr()
    assert "not yet implemented" in captured.out


def test_timing_not_implemented(capsys):
    """Test -t flag shows not implemented."""
    result = main(["-t"])
    assert result == 1
    captured = capsys.readouterr()
    assert "not yet implemented" in captured.out


def test_convert_not_implemented(capsys):
    """Test -c flag shows not implemented."""
    result = main(["-c", "mp3"])
    assert result == 1
    captured = capsys.readouterr()
    assert "not yet implemented" in captured.out
