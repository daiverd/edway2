"""Property-based tests for edway2 using Hypothesis.

This file contains property-based tests that verify invariants of the
core data types. Strategies are defined in conftest_hypothesis.py.
"""

import hypothesis.strategies as st
from hypothesis import assume, given, settings

from conftest_hypothesis import blockview_strategy, session_strategy


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
