"""Tests for edway2 REPL."""

import pytest
from pathlib import Path

from prompt_toolkit.document import Document

from edway2.repl import run_repl, EdwayCompleter


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


def test_unknown_command_returns_error(mock_prompt, capsys, tmp_path):
    """Test unknown command prints error message."""
    mock_prompt(["xyz", "q"])
    run_repl(str(tmp_path / "test_project"))
    captured = capsys.readouterr()
    # Parser can't match "xyz" to any command
    assert "? syntax error" in captured.out


def test_unimplemented_command_returns_error(mock_prompt, capsys, tmp_path):
    """Test unimplemented command shows error."""
    # "fo" is fade out - recognized by parser but not yet implemented
    mock_prompt(["fo", "q"])
    run_repl(str(tmp_path / "test_project"))
    captured = capsys.readouterr()
    assert "? unknown command: fo" in captured.out


def test_empty_line_does_nothing(mock_prompt, capsys):
    """Test empty lines are ignored."""
    mock_prompt(["", "   ", "q"])
    result = run_repl(None)
    assert result == 0
    captured = capsys.readouterr()
    assert "? unknown command" not in captured.out


def test_no_project_shows_message(mock_prompt, capsys):
    """Test commands without project show appropriate message."""
    mock_prompt(["r test.wav", "q"])
    run_repl(None)
    captured = capsys.readouterr()
    assert "? no project open" in captured.out


# --- Completer tests ---


def test_completer_provides_path_completion_for_r_command(tmp_path):
    """Test 'r ' triggers path completion."""
    # Create a test file
    test_file = tmp_path / "audio.wav"
    test_file.touch()

    completer = EdwayCompleter()

    # Simulate typing "r aud" in the tmp_path directory
    # PathCompleter returns the suffix to complete ("io.wav" for "aud" -> "audio.wav")
    import os
    old_cwd = os.getcwd()
    try:
        os.chdir(tmp_path)
        doc = Document("r aud")
        completions = list(completer.get_completions(doc, None))
        texts = [c.text for c in completions]
        # "aud" + "io.wav" = "audio.wav"
        assert "io.wav" in texts
    finally:
        os.chdir(old_cwd)


def test_completer_no_completion_for_other_commands():
    """Test non-file commands don't trigger path completion."""
    completer = EdwayCompleter()
    doc = Document("p")  # play command
    completions = list(completer.get_completions(doc, None))
    assert completions == []


def test_completer_handles_empty_input():
    """Test empty input doesn't crash."""
    completer = EdwayCompleter()
    doc = Document("")
    completions = list(completer.get_completions(doc, None))
    assert completions == []
