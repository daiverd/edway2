"""Reusable Hypothesis strategies for edway2 core data types.

Provides composite strategies for generating valid instances of:
- Clip, Track, Session (session.py)
- BlockView (blocks.py)
- Address, Command (parser.py)

These are registered as pytest fixtures so they're available project-wide.
Import strategies directly or use the fixtures.
"""

import string

import hypothesis.strategies as st
from hypothesis import settings

from edway2.blocks import BlockView
from edway2.parser import Address, Command, COMMANDS
from edway2.session import Clip, Session, Track

# Suppress the Hypothesis home directory warning on Windows
settings.register_profile("edway2", database=None)


# ---------------------------------------------------------------------------
# Clip
# ---------------------------------------------------------------------------

@st.composite
def clip_strategy(draw):
    """Generate a Clip with reasonable bounds.

    - position: 0-3600 s
    - source_start < source_end, durations 0.001-300 s
    - gain: -60 to +24 dB
    - fades: 0-10 s each
    """
    position = draw(st.floats(min_value=0.0, max_value=3600.0, allow_nan=False, allow_infinity=False))
    source_start = draw(st.floats(min_value=0.0, max_value=3600.0, allow_nan=False, allow_infinity=False))
    duration = draw(st.floats(min_value=0.001, max_value=300.0, allow_nan=False, allow_infinity=False))
    source_end = source_start + duration
    gain = draw(st.floats(min_value=-60.0, max_value=24.0, allow_nan=False, allow_infinity=False))
    fade_in = draw(st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False))
    fade_out = draw(st.floats(min_value=0.0, max_value=10.0, allow_nan=False, allow_infinity=False))
    source = draw(st.text(alphabet=string.ascii_lowercase + string.digits + "_-", min_size=1, max_size=20).map(lambda s: f"sources/{s}.wav"))

    return Clip(
        source=source,
        source_start=source_start,
        source_end=source_end,
        position=position,
        gain=gain,
        fade_in=fade_in,
        fade_out=fade_out,
    )


# ---------------------------------------------------------------------------
# Track
# ---------------------------------------------------------------------------

@st.composite
def track_strategy(draw, clips=None):
    """Generate a Track with optional clip list strategy.

    Args:
        clips: Optional strategy for generating clip lists.
               Defaults to 0-5 clips from clip_strategy().
    """
    name = draw(st.text(alphabet=string.ascii_letters + string.digits + " _-", min_size=1, max_size=30))
    start_time = draw(st.floats(min_value=0.0, max_value=3600.0, allow_nan=False, allow_infinity=False))
    selected = draw(st.booleans())
    muted = draw(st.booleans())
    soloed = draw(st.booleans())
    record = draw(st.booleans())
    gain = draw(st.floats(min_value=-60.0, max_value=24.0, allow_nan=False, allow_infinity=False))

    if clips is None:
        clips = st.lists(clip_strategy(), min_size=0, max_size=5)
    clip_list = draw(clips)

    return Track(
        name=name,
        start_time=start_time,
        selected=selected,
        muted=muted,
        soloed=soloed,
        record=record,
        gain=gain,
        clips=clip_list,
    )


# ---------------------------------------------------------------------------
# Session
# ---------------------------------------------------------------------------

@st.composite
def session_strategy(draw):
    """Generate a Session with reasonable parameters.

    - sample_rate: one of 22050, 44100, 48000, 96000
    - block_duration_ms: 100-5000
    - 1-8 tracks
    """
    name = draw(st.text(alphabet=string.ascii_letters + string.digits + " _-", min_size=1, max_size=30))
    sample_rate = draw(st.sampled_from([22050, 44100, 48000, 96000]))
    block_duration_ms = draw(st.integers(min_value=100, max_value=5000))
    master_gain = draw(st.floats(min_value=-60.0, max_value=24.0, allow_nan=False, allow_infinity=False))
    num_tracks = draw(st.integers(min_value=1, max_value=8))
    tracks = draw(st.lists(track_strategy(), min_size=num_tracks, max_size=num_tracks))

    return Session(
        name=name,
        sample_rate=sample_rate,
        block_duration_ms=block_duration_ms,
        master_gain=master_gain,
        tracks=tracks,
    )


# ---------------------------------------------------------------------------
# BlockView
# ---------------------------------------------------------------------------

@st.composite
def blockview_strategy(draw):
    """Generate a BlockView with reasonable parameters.

    - duration_seconds: 0-3600
    - block_duration_ms: 100-5000
    """
    duration = draw(st.floats(min_value=0.0, max_value=3600.0, allow_nan=False, allow_infinity=False))
    block_duration_ms = draw(st.integers(min_value=100, max_value=5000))

    return BlockView(
        duration_seconds=duration,
        block_duration_ms=block_duration_ms,
    )


# ---------------------------------------------------------------------------
# Address
# ---------------------------------------------------------------------------

@st.composite
def address_strategy(draw):
    """Generate a valid Address instance covering all 5 types.

    Types: number, dot, dollar, mark, time -- each with reasonable offsets.
    """
    addr_type = draw(st.sampled_from(["number", "dot", "dollar", "mark", "time"]))
    offset = draw(st.integers(min_value=-100, max_value=100))

    if addr_type == "number":
        value = draw(st.integers(min_value=1, max_value=10000))
    elif addr_type == "dot":
        value = None
    elif addr_type == "dollar":
        value = None
    elif addr_type == "mark":
        value = draw(st.sampled_from(list(string.ascii_lowercase)))
    elif addr_type == "time":
        value = draw(st.floats(min_value=0.0, max_value=3600.0, allow_nan=False, allow_infinity=False))
    else:
        raise ValueError(f"Unknown address type: {addr_type}")

    return Address(type=addr_type, value=value, offset=offset)


# ---------------------------------------------------------------------------
# Command
# ---------------------------------------------------------------------------

@st.composite
def command_strategy(draw):
    """Generate a Command with a valid command name from parser.COMMANDS.

    Optionally includes addr1, addr2, dest (for dest commands), and arg.
    """
    name = draw(st.sampled_from(COMMANDS))
    addr1 = draw(st.one_of(st.none(), address_strategy()))
    addr2 = draw(st.one_of(st.none(), address_strategy()))

    # dest only for dest commands
    from edway2.parser import DEST_COMMANDS
    if name in DEST_COMMANDS:
        dest = draw(st.one_of(st.none(), address_strategy()))
    else:
        dest = None

    arg = draw(st.one_of(st.none(), st.text(min_size=1, max_size=50)))

    return Command(
        name=name,
        addr1=addr1,
        addr2=addr2,
        dest=dest,
        arg=arg,
    )
