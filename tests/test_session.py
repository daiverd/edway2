"""Tests for edway2 Session."""

import pytest
from pathlib import Path

from edway2.session import Session


def test_new_session():
    """Test creating a new session."""
    session = Session.new("test")
    assert session.timeline.name == "test"
    assert session.current_position == 0.0
    assert session.current_track == 0
    assert session.track_count == 1


def test_new_session_default_name():
    """Test new session with default name."""
    session = Session.new()
    assert session.timeline.name == "untitled"


def test_session_has_one_track():
    """Test new session has one audio track."""
    session = Session.new()
    assert session.track_count == 1
    assert session.get_track(0).name == "Track 1"


def test_add_track():
    """Test adding a track."""
    session = Session.new()
    index = session.add_track("Vocals")
    assert index == 1
    assert session.track_count == 2
    assert session.get_track(1).name == "Vocals"


def test_add_track_default_name():
    """Test adding track with default name."""
    session = Session.new()
    session.add_track()
    assert session.get_track(1).name == "Track 2"


def test_remove_empty_track():
    """Test removing an empty track."""
    session = Session.new()
    session.add_track()
    assert session.track_count == 2
    session.remove_track(1)
    assert session.track_count == 1


def test_duration_empty():
    """Test duration of empty session."""
    session = Session.new()
    assert session.duration == 0.0


def test_marks():
    """Test setting marks."""
    session = Session.new()
    session.marks["a"] = 5.0
    session.marks["b"] = 10.5
    assert session.marks["a"] == 5.0
    assert session.marks["b"] == 10.5


def test_regions():
    """Test setting regions."""
    session = Session.new()
    session.regions["intro"] = (0.0, 30.0)
    assert session.regions["intro"] == (0.0, 30.0)


def test_save_and_load(tmp_path):
    """Test saving and loading session."""
    path = tmp_path / "test.edway"

    # Create and save
    session = Session.new("test_project")
    session.marks["a"] = 5.0
    session.current_position = 10.0
    session.block_duration_ms = 500
    session.to_file(path)

    # Load and verify
    loaded = Session.from_file(path)
    assert loaded.timeline.name == "test_project"
    assert loaded.marks["a"] == 5.0
    assert loaded.current_position == 10.0
    assert loaded.block_duration_ms == 500


def test_muted_tracks_persist(tmp_path):
    """Test muted tracks are saved and loaded."""
    path = tmp_path / "test.edway"

    session = Session.new()
    session.add_track()
    session.muted_tracks.add(1)
    session.to_file(path)

    loaded = Session.from_file(path)
    assert 1 in loaded.muted_tracks


def test_soloed_tracks_persist(tmp_path):
    """Test soloed tracks are saved and loaded."""
    path = tmp_path / "test.edway"

    session = Session.new()
    session.add_track()
    session.soloed_tracks.add(0)
    session.to_file(path)

    loaded = Session.from_file(path)
    assert 0 in loaded.soloed_tracks
