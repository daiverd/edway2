"""Property-based tests for edway2 using Hypothesis.

This file contains property-based tests that verify invariants of the
core data types. Strategies are defined in conftest_hypothesis.py.
"""

import tempfile
from pathlib import Path

import hypothesis.strategies as st
from hypothesis import assume, given, settings

from conftest_hypothesis import (
    blockview_strategy,
    clip_strategy,
    session_strategy,
    track_strategy,
)
from edway2.commands.editing import (
    delete_range,
    extract_clips_in_range,
    make_room_at,
    ripple_delete_range,
    shift_clips_after,
)
from edway2.parser import COMMANDS, Command, parse
from edway2.session import Clip, Session, Track


@given(session=session_strategy())
@settings(max_examples=50)
def test_session_track_count_non_negative(session):
    """Smoke test: generated Sessions always have non-negative track_count."""
    assert session.track_count >= 0


# ---------------------------------------------------------------------------
# BlockView property tests (B1-B7)
# ---------------------------------------------------------------------------


@st.composite
def blockview_with_valid_block(draw):
    """Generate a BlockView with count > 0 and a valid block number."""
    view = draw(blockview_strategy())
    assume(view.count > 0)
    block = draw(st.integers(min_value=1, max_value=view.count))
    return view, block


@given(data=blockview_with_valid_block())
@settings(max_examples=200)
def test_b1_block_round_trip(data):
    """B1: from_time(to_time(b)) == b for any valid block b."""
    view, block = data
    time = view.to_time(block)
    result = view.from_time(time)
    assert result == block, (
        f"Round-trip failed: block={block}, to_time={time}, "
        f"from_time={result}, duration={view.duration_seconds}, "
        f"block_ms={view.block_duration_ms}"
    )


@given(data=blockview_with_valid_block())
@settings(max_examples=200)
def test_b2_time_ordering(data):
    """B2: to_time(block) < to_time_end(block) for any valid block."""
    view, block = data
    assert view.to_time(block) < view.to_time_end(block)


@given(data=blockview_with_valid_block())
@settings(max_examples=200)
def test_b3_block_contiguity(data):
    """B3: to_time_end(b) == to_time(b+1) for b < count."""
    view, block = data
    assume(block < view.count)
    assert view.to_time_end(block) == view.to_time(block + 1)


@given(view=blockview_strategy(), x=st.integers(min_value=-1000, max_value=1000))
@settings(max_examples=200)
def test_b4_clamp_range(view, x):
    """B4: clamp(x) is always in [1, max(1, count)]."""
    result = view.clamp(x)
    assert 1 <= result <= max(1, view.count)


@given(data=blockview_with_valid_block())
@settings(max_examples=200)
def test_b5_validate_consistency(data):
    """B5: validate(b) does not raise for valid b in [1, count]."""
    view, block = data
    view.validate(block)  # should not raise


@given(view=blockview_strategy())
@settings(max_examples=200)
def test_b6_count_non_negative(view):
    """B6: count >= 0 for any BlockView."""
    assert view.count >= 0


@given(
    view=blockview_strategy(),
    t1=st.floats(min_value=0.0, max_value=3600.0, allow_nan=False, allow_infinity=False),
    t2=st.floats(min_value=0.0, max_value=3600.0, allow_nan=False, allow_infinity=False),
)
@settings(max_examples=200)
def test_b7_from_time_monotonicity(view, t1, t2):
    """B7: from_time(t1) <= from_time(t2) when t1 <= t2."""
    lo, hi = sorted([t1, t2])
    assert view.from_time(lo) <= view.from_time(hi)


# ---------------------------------------------------------------------------
# Serialization round-trip property tests (S1-S3)
# ---------------------------------------------------------------------------


def assert_clips_equal(original: Clip, restored: Clip) -> None:
    """Compare two Clips field-by-field."""
    assert original.source == restored.source
    assert original.source_start == restored.source_start
    assert original.source_end == restored.source_end
    assert original.position == restored.position
    assert original.gain == restored.gain
    assert original.fade_in == restored.fade_in
    assert original.fade_out == restored.fade_out
    assert original.effects == restored.effects


def assert_tracks_equal(original: Track, restored: Track) -> None:
    """Compare two Tracks field-by-field, including their clips."""
    assert original.name == restored.name
    assert original.start_time == restored.start_time
    assert original.selected == restored.selected
    assert original.muted == restored.muted
    assert original.soloed == restored.soloed
    assert original.record == restored.record
    assert original.gain == restored.gain
    assert original.effects == restored.effects
    assert len(original.clips) == len(restored.clips)
    for orig_clip, rest_clip in zip(original.clips, restored.clips):
        assert_clips_equal(orig_clip, rest_clip)


@given(clip=clip_strategy())
@settings(max_examples=200)
def test_s1_clip_dict_round_trip(clip):
    """S1: Clip.from_dict(clip.to_dict()) produces identical field values."""
    restored = Clip.from_dict(clip.to_dict())
    assert_clips_equal(clip, restored)


@given(track=track_strategy())
@settings(max_examples=200)
def test_s2_track_dict_round_trip(track):
    """S2: Track.from_dict(track.to_dict()) produces identical field values."""
    restored = Track.from_dict(track.to_dict())
    assert_tracks_equal(track, restored)


@given(session=session_strategy())
@settings(max_examples=200)
def test_s3_session_file_round_trip(session):
    """S3: Session written to file and read back has identical fields."""
    # Ensure current_track is valid for the generated session
    assume(session.current_track < len(session.tracks))

    with tempfile.TemporaryDirectory() as tmpdir:
        path = Path(tmpdir) / "test.edway"
        session.to_file(path)
        restored = Session.from_file(path)

    # Scalar fields
    assert session.name == restored.name
    assert session.sample_rate == restored.sample_rate
    assert session.block_duration_ms == restored.block_duration_ms
    assert session.master_gain == restored.master_gain
    assert session.current_position == restored.current_position
    assert session.current_track == restored.current_track

    # Marks
    assert session.marks == restored.marks

    # Regions (JSON round-trips tuples through lists, from_file converts back)
    assert session.regions == restored.regions

    # Tracks
    assert len(session.tracks) == len(restored.tracks)
    for orig_track, rest_track in zip(session.tracks, restored.tracks):
        assert_tracks_equal(orig_track, rest_track)


# ---------------------------------------------------------------------------
# Editing operation property tests (E1-E10)
# ---------------------------------------------------------------------------


@st.composite
def track_with_range(draw):
    """Generate a track with clips and a valid time range within it."""
    track = draw(track_strategy(clips=st.lists(clip_strategy(), min_size=1, max_size=5)))
    # Find the extent of clips
    max_end = max(c.position + c.duration for c in track.clips)
    start = draw(st.floats(min_value=0.0, max_value=max(0.001, max_end), allow_nan=False, allow_infinity=False))
    end = draw(st.floats(min_value=start + 0.001, max_value=max(start + 0.002, max_end + 1.0), allow_nan=False, allow_infinity=False))
    return track, start, end


@given(data=track_with_range())
@settings(max_examples=200)
def test_e1_delete_then_extract_is_empty(data):
    """E1: After delete_range, extract_clips_in_range returns empty list."""
    track, start, end = data
    delete_range(track, start, end)
    extracted = extract_clips_in_range(track, start, end)
    assert extracted == [], (
        f"Expected empty list after delete, got {len(extracted)} clips. "
        f"Range: [{start}, {end})"
    )


@given(data=track_with_range())
@settings(max_examples=200)
def test_e2_extract_duration_bounded(data):
    """E2: Each extracted clip's duration is <= range duration.

    Note: overlapping clips at the same position can produce multiple
    extracted clips whose sum exceeds the range, but each individual
    clip must fit within the range.
    """
    track, start, end = data
    extracted = extract_clips_in_range(track, start, end)
    range_duration = end - start
    for clip in extracted:
        assert clip.duration <= range_duration + 1e-9, (
            f"Extracted clip duration {clip.duration} > range duration {range_duration}"
        )


@given(data=track_with_range())
@settings(max_examples=200)
def test_e3_extract_positions_non_negative(data):
    """E3: All extracted clips have position >= 0."""
    track, start, end = data
    extracted = extract_clips_in_range(track, start, end)
    for clip in extracted:
        assert clip.position >= 0, (
            f"Extracted clip has negative position: {clip.position}"
        )


@given(data=track_with_range())
@settings(max_examples=200)
def test_e4_delete_preserves_outsiders(data):
    """E4: Clips fully outside deleted range are preserved unchanged."""
    track, start, end = data

    # Snapshot clips fully outside the range before delete
    outsiders_before = []
    for clip in track.clips:
        clip_end = clip.position + clip.duration
        if clip_end <= start or clip.position >= end:
            outsiders_before.append((clip.source, clip.source_start, clip.source_end, clip.position))

    delete_range(track, start, end)

    # Verify outsiders are still present
    outsiders_after = [
        (c.source, c.source_start, c.source_end, c.position) for c in track.clips
        if c.position + c.duration <= start or c.position >= end
    ]

    # Every original outsider should still be present
    for ob in outsiders_before:
        assert ob in outsiders_after, (
            f"Outsider clip {ob} was lost after delete_range"
        )


@given(data=track_with_range())
@settings(max_examples=200)
def test_e5_delete_clip_count_bound(data):
    """E5: delete_range clip count bounded by 2 * original count."""
    track, start, end = data
    old_count = len(track.clips)
    delete_range(track, start, end)
    new_count = len(track.clips)
    assert new_count <= 2 * old_count, (
        f"Clip count grew too much: {old_count} -> {new_count}"
    )


@given(data=track_with_range())
@settings(max_examples=200)
def test_e6_ripple_delete_no_negative_positions(data):
    """E6: After ripple_delete_range, no clip has position < 0."""
    track, start, end = data
    ripple_delete_range(track, start, end)
    for clip in track.clips:
        assert clip.position >= -1e-9, (
            f"Clip has negative position {clip.position} after ripple delete"
        )


@given(data=track_with_range())
@settings(max_examples=200)
def test_e7_shift_preserves_clip_count(data):
    """E7: shift_clips_after does not add or remove clips."""
    track, start, end = data
    original_count = len(track.clips)
    delta = end - start  # arbitrary positive delta
    shift_clips_after(track, start, delta)
    assert len(track.clips) == original_count, (
        f"Clip count changed: {original_count} -> {len(track.clips)}"
    )


@given(data=track_with_range())
@settings(max_examples=200)
def test_e8_shift_no_negative_positions(data):
    """E8: After shift_clips_after with any delta, no clip has position < 0."""
    track, start, end = data
    delta = -(end - start)  # negative delta to test clamping
    shift_clips_after(track, start, delta)
    for clip in track.clips:
        assert clip.position >= -1e-9, (
            f"Clip has negative position {clip.position} after shift"
        )


@given(data=track_with_range())
@settings(max_examples=200)
def test_e9_ripple_delete_reduces_content(data):
    """E9: After ripple_delete_range, total content duration <= original."""
    track, start, end = data
    original_total = sum(c.duration for c in track.clips)
    ripple_delete_range(track, start, end)
    new_total = sum(c.duration for c in track.clips)
    assert new_total <= original_total + 1e-9, (
        f"Content duration increased: {original_total} -> {new_total}"
    )


@given(data=track_with_range())
@settings(max_examples=200)
def test_e10_make_room_preserves_count(data):
    """E10: make_room_at does not add or remove clips."""
    track, start, end = data
    original_count = len(track.clips)
    duration = end - start
    make_room_at(track, start, duration)
    assert len(track.clips) == original_count, (
        f"Clip count changed: {original_count} -> {len(track.clips)}"
    )


# ---------------------------------------------------------------------------
# Clip/Track invariant property tests (C1-C4)
# ---------------------------------------------------------------------------


@given(clip=clip_strategy())
@settings(max_examples=200)
def test_c1_clip_duration_consistency(clip):
    """C1: clip.duration == clip.source_end - clip.source_start, and duration >= 0."""
    assert clip.duration == clip.source_end - clip.source_start
    assert clip.duration >= 0


@given(track=track_strategy())
@settings(max_examples=200)
def test_c2_track_duration_zero_iff_empty(track):
    """C2: track.duration == 0.0 if and only if len(track.clips) == 0."""
    if len(track.clips) == 0:
        assert track.duration == 0.0
    else:
        assert track.duration > 0.0


@given(track=track_strategy(clips=st.lists(clip_strategy(), min_size=1, max_size=5)))
@settings(max_examples=200)
def test_c3_track_duration_covers_all_clips(track):
    """C3: track.duration >= max(clip.position + clip.duration for all clips)."""
    max_clip_end = max(c.position + c.duration for c in track.clips)
    assert track.duration >= max_clip_end


@given(track=track_strategy(clips=st.lists(clip_strategy(), min_size=1, max_size=5)))
@settings(max_examples=200)
def test_c4_clips_at_finds_clip_at_own_position(track):
    """C4: For every clip c, c in track.clips_at(track.start_time + c.position)."""
    for c in track.clips:
        found = track.clips_at(track.start_time + c.position)
        assert c in found, (
            f"Clip at position {c.position} not found by clips_at("
            f"{track.start_time + c.position}). "
            f"Clip range: [{c.position}, {c.position + c.duration}), "
            f"start_time: {track.start_time}"
        )


# ---------------------------------------------------------------------------
# Parser property tests (P1-P5)
# ---------------------------------------------------------------------------


@given(data=st.data())
@settings(max_examples=200)
def test_p1_parse_never_returns_none(data):
    """P1: parse() returns a Command (not None) for valid command strings."""
    # Generate various valid command strings
    kind = data.draw(st.sampled_from([
        "standalone", "number_cmd", "range_cmd", "addr_only_num",
        "addr_only_dollar", "addr_only_offset",
    ]))
    if kind == "standalone":
        cmd_name = data.draw(st.sampled_from(COMMANDS))
        line = cmd_name
    elif kind == "number_cmd":
        n = data.draw(st.integers(min_value=1, max_value=9999))
        line = f"{n}p"
    elif kind == "range_cmd":
        a = data.draw(st.integers(min_value=1, max_value=9999))
        b = data.draw(st.integers(min_value=a, max_value=min(a + 1000, 9999)))
        line = f"{a},{b}d"
    elif kind == "addr_only_num":
        n = data.draw(st.integers(min_value=1, max_value=9999))
        line = str(n)
    elif kind == "addr_only_dollar":
        line = "$"
    elif kind == "addr_only_offset":
        n = data.draw(st.integers(min_value=1, max_value=100))
        line = f".+{n}"
    else:
        line = "p"

    result = parse(line)
    assert result is not None
    assert isinstance(result, Command)


@given(
    m=st.integers(min_value=0, max_value=59),
    s=st.integers(min_value=0, max_value=59),
)
@settings(max_examples=200)
def test_p2_time_address_precision(m, s):
    """P2: parse('@M:SSp') gives addr1.value == m * 60 + s."""
    cmd = parse(f"@{m}:{s:02d}p")
    assert cmd.addr1 is not None
    assert cmd.addr1.type == "time"
    assert cmd.addr1.value == m * 60 + s


def test_p2_time_address_millis():
    """P2 (millis): parse('@1:30.500p') gives addr1.value == 90.5."""
    cmd = parse("@1:30.500p")
    assert cmd.addr1 is not None
    assert cmd.addr1.value == 90.5


@given(n=st.integers(min_value=1, max_value=9999))
@settings(max_examples=200)
def test_p3_number_address_round_trip(n):
    """P3: parse(f'{n}p') gives addr1.type == 'number' and addr1.value == n."""
    cmd = parse(f"{n}p")
    assert cmd.addr1 is not None
    assert cmd.addr1.type == "number"
    assert cmd.addr1.value == n


@settings(max_examples=200)
@given(cmd_name=st.sampled_from(COMMANDS))
def test_p4_every_command_parseable(cmd_name):
    """P4: Every command name in COMMANDS is parseable."""
    try:
        result = parse(cmd_name)
        assert isinstance(result, Command)
        # The parsed command name should match, unless it was interpreted
        # as an address (e.g., single-letter overlapping with address syntax)
        # For multi-letter commands, name should match
        if len(cmd_name) > 1 or not cmd_name.isdigit():
            assert result.name == cmd_name or result.name == "", (
                f"Expected command name '{cmd_name}', got '{result.name}'"
            )
    except Exception as e:
        # Note commands that fail to parse but don't fail the test hard
        # (single-letter overlap with address syntax)
        raise AssertionError(
            f"Command '{cmd_name}' failed to parse: {e}"
        ) from e


@given(data=st.data())
@settings(max_examples=200)
def test_p5_range_requires_addr1(data):
    """P5: If parse() returns addr2 is not None, then addr1 is not None."""
    kind = data.draw(st.sampled_from([
        "range_cmd", "single_cmd", "addr_only",
    ]))
    if kind == "range_cmd":
        a = data.draw(st.integers(min_value=1, max_value=999))
        b = data.draw(st.integers(min_value=a, max_value=min(a + 100, 999)))
        cmd_name = data.draw(st.sampled_from(["p", "d", "z"]))
        line = f"{a},{b}{cmd_name}"
    elif kind == "single_cmd":
        n = data.draw(st.integers(min_value=1, max_value=999))
        line = f"{n}p"
    else:
        line = "$"

    result = parse(line)
    if result.addr2 is not None:
        assert result.addr1 is not None, (
            f"addr2 is set but addr1 is None for input '{line}'"
        )


# ---------------------------------------------------------------------------
# Mute/Solo proxy property tests (X1-X4)
# ---------------------------------------------------------------------------


@given(session=session_strategy(), data=st.data())
@settings(max_examples=200)
def test_x1_mute_add_contains(session, data):
    """X1: After muted_tracks.add(i), i in muted_tracks is True."""
    assume(len(session.tracks) > 0)
    i = data.draw(st.integers(min_value=0, max_value=len(session.tracks) - 1))
    session.muted_tracks.add(i)
    assert i in session.muted_tracks


@given(session=session_strategy(), data=st.data())
@settings(max_examples=200)
def test_x2_solo_discard_contains(session, data):
    """X2: After add then discard, i not in soloed_tracks."""
    assume(len(session.tracks) > 0)
    i = data.draw(st.integers(min_value=0, max_value=len(session.tracks) - 1))
    session.soloed_tracks.add(i)
    session.soloed_tracks.discard(i)
    assert i not in session.soloed_tracks


@given(session=session_strategy(), data=st.data())
@settings(max_examples=200)
def test_x3_selected_tracks_never_empty(session, data):
    """X3: selected_tracks() always has at least 1 track."""
    assume(len(session.tracks) > 0)
    session.current_track = data.draw(
        st.integers(min_value=0, max_value=len(session.tracks) - 1)
    )
    assert len(session.selected_tracks()) >= 1


@given(session=session_strategy(), data=st.data())
@settings(max_examples=200)
def test_x4_selected_tracks_default(session, data):
    """X4: With no track selected, selected_tracks() == [current_track]."""
    assume(len(session.tracks) > 0)
    session.current_track = data.draw(
        st.integers(min_value=0, max_value=len(session.tracks) - 1)
    )
    for track in session.tracks:
        track.selected = False
    result = session.selected_tracks()
    assert result == [session.tracks[session.current_track]]
