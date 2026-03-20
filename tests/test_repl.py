"""Tests for edway2 REPL."""

import pytest

from edway2.repl import run_repl


@pytest.fixture
def mock_prompt(mocker):
    """Mock prompt_toolkit PromptSession.prompt."""
    def _mock(responses: list[str]):
        # Create iterator that raises EOFError after responses exhausted
        response_iter = iter(responses)

        def mock_prompt_fn(*args, **kwargs):
            try:
                return next(response_iter)
            except StopIteration:
                raise EOFError()

        mock_session = mocker.MagicMock()
        mock_session.prompt = mock_prompt_fn
        mocker.patch(
            "edway2.repl.PromptSession",
            return_value=mock_session,
        )
    return _mock


def test_quit_exits(mock_prompt):
    """Test 'q' command exits with code 0."""
    mock_prompt(["q"])
    result = run_repl(None)
    assert result == 0


def test_qt_exits(mock_prompt):
    """Test 'qt' command exits with code 0."""
    mock_prompt(["qt"])
    result = run_repl(None)
    assert result == 0


def test_eof_exits(mock_prompt):
    """Test Ctrl+D (EOF) exits cleanly."""
    mock_prompt([])  # Empty list triggers EOFError immediately
    result = run_repl(None)
    assert result == 0


def test_unknown_command_returns_error(mock_prompt, capsys):
    """Test unknown command prints error message."""
    mock_prompt(["xyz", "q"])
    run_repl(None)
    captured = capsys.readouterr()
    assert "? unknown command: xyz" in captured.out


def test_unknown_command_with_args(mock_prompt, capsys):
    """Test unknown command with arguments shows just the command."""
    mock_prompt(["foo bar baz", "q"])
    run_repl(None)
    captured = capsys.readouterr()
    assert "? unknown command: foo" in captured.out


def test_empty_line_does_nothing(mock_prompt, capsys):
    """Test empty lines are ignored."""
    mock_prompt(["", "   ", "q"])
    result = run_repl(None)
    assert result == 0
    captured = capsys.readouterr()
    assert "? unknown command" not in captured.out
