"""Tests for edway2 Session."""

import pytest
from pathlib import Path

from edway2.session import Session, Track, Clip


def test_new_session():
    """Test creating a new session."""
    session = Session.new("test")
    assert session.name == "test"
    assert session.current_position == 0.0
    assert session.current_track == 0
    assert session.track_count == 1


def test_new_session_default_name():
    """Test new session with default name."""
    session = Session.new()
    assert session.name == "untitled"


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
    assert loaded.name == "test_project"
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


def test_session_json_roundtrip_with_clips(tmp_path):
    """Test JSON roundtrip preserves clips."""
    path = tmp_path / "test.edway"

    session = Session.new("test")
    session.tracks[0].clips.append(Clip(
        source="sources/test.wav",
        source_start=0.0,
        source_end=10.0,
        position=0.0,
        gain=-3.0,
    ))
    session.tracks[0].clips.append(Clip(
        source="sources/test.wav",
        source_start=5.0,
        source_end=15.0,
        position=15.0,
        gain=0.0,
        fade_in=0.1,
        fade_out=0.2,
    ))
    session.to_file(path)

    loaded = Session.from_file(path)
    assert len(loaded.tracks[0].clips) == 2

    clip1 = loaded.tracks[0].clips[0]
    assert clip1.source == "sources/test.wav"
    assert clip1.source_start == 0.0
    assert clip1.source_end == 10.0
    assert clip1.position == 0.0
    assert clip1.gain == -3.0

    clip2 = loaded.tracks[0].clips[1]
    assert clip2.source_start == 5.0
    assert clip2.position == 15.0
    assert clip2.fade_in == 0.1
    assert clip2.fade_out == 0.2


def test_clip_duration():
    """Test Clip.duration property."""
    clip = Clip(
        source="test.wav",
        source_start=5.0,
        source_end=15.0,
        position=0.0,
    )
    assert clip.duration == 10.0


def test_track_duration():
    """Test Track.duration property."""
    track = Track(name="Test")
    assert track.duration == 0.0

    track.clips.append(Clip(
        source="test.wav",
        source_start=0.0,
        source_end=5.0,
        position=0.0,
    ))
    assert track.duration == 5.0

    track.clips.append(Clip(
        source="test.wav",
        source_start=0.0,
        source_end=3.0,
        position=10.0,
    ))
    assert track.duration == 13.0  # 10 + 3


def test_session_duration_with_clips():
    """Test Session.duration with clips."""
    session = Session.new("test")
    assert session.duration == 0.0

    session.tracks[0].clips.append(Clip(
        source="test.wav",
        source_start=0.0,
        source_end=10.0,
        position=0.0,
    ))
    assert session.duration == 10.0


def test_track_clips_at():
    """Test Track.clips_at method."""
    track = Track(name="Test", start_time=1.0)
    track.clips.append(Clip(
        source="test.wav",
        source_start=0.0,
        source_end=5.0,
        position=0.0,  # global: 1.0 to 6.0
    ))
    track.clips.append(Clip(
        source="test.wav",
        source_start=0.0,
        source_end=3.0,
        position=10.0,  # global: 11.0 to 14.0
    ))

    # At time 0.0 (before track starts) - no clips
    assert len(track.clips_at(0.0)) == 0

    # At time 2.0 (inside first clip) - first clip
    clips = track.clips_at(2.0)
    assert len(clips) == 1
    assert clips[0].position == 0.0

    # At time 8.0 (gap between clips) - no clips
    assert len(track.clips_at(8.0)) == 0

    # At time 12.0 (inside second clip) - second clip
    clips = track.clips_at(12.0)
    assert len(clips) == 1
    assert clips[0].position == 10.0
