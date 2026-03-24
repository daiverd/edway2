"""Property-based tests for edway2 using Hypothesis.

This file contains property-based tests that verify invariants of the
core data types. Strategies are defined in conftest_hypothesis.py.
"""

from hypothesis import given, settings

from conftest_hypothesis import session_strategy


@given(session=session_strategy())
@settings(max_examples=50)
def test_session_track_count_non_negative(session):
    """Smoke test: generated Sessions always have non-negative track_count."""
    assert session.track_count >= 0
