"""Tests for edway2 BlockView."""

import pytest

from edway2.blocks import BlockView


class TestBlockCount:
    """Tests for block count calculation."""

    def test_count_10_seconds_1000ms_blocks(self):
        """10 seconds with 1000ms blocks = 10 blocks."""
        bv = BlockView(duration_seconds=10.0, block_duration_ms=1000)
        assert bv.count == 10

    def test_count_10_seconds_500ms_blocks(self):
        """10 seconds with 500ms blocks = 20 blocks."""
        bv = BlockView(duration_seconds=10.0, block_duration_ms=500)
        assert bv.count == 20

    def test_count_rounds_up(self):
        """Partial blocks round up (1.5 seconds = 2 blocks at 1000ms)."""
        bv = BlockView(duration_seconds=1.5, block_duration_ms=1000)
        assert bv.count == 2

    def test_count_empty_timeline(self):
        """Empty timeline has 0 blocks."""
        bv = BlockView(duration_seconds=0.0, block_duration_ms=1000)
        assert bv.count == 0

    def test_count_negative_duration(self):
        """Negative duration treated as 0 blocks."""
        bv = BlockView(duration_seconds=-1.0, block_duration_ms=1000)
        assert bv.count == 0


class TestBlockToTime:
    """Tests for block number to time conversion."""

    def test_block_1_starts_at_0(self):
        """Block 1 starts at time 0."""
        bv = BlockView(duration_seconds=10.0, block_duration_ms=1000)
        assert bv.to_time(1) == 0.0

    def test_block_2_starts_at_1_second(self):
        """Block 2 starts at 1 second (with 1000ms blocks)."""
        bv = BlockView(duration_seconds=10.0, block_duration_ms=1000)
        assert bv.to_time(2) == 1.0

    def test_block_10_starts_at_9_seconds(self):
        """Block 10 starts at 9 seconds."""
        bv = BlockView(duration_seconds=10.0, block_duration_ms=1000)
        assert bv.to_time(10) == 9.0

    def test_block_with_500ms_duration(self):
        """Block 3 starts at 1 second with 500ms blocks."""
        bv = BlockView(duration_seconds=10.0, block_duration_ms=500)
        assert bv.to_time(3) == 1.0

    def test_block_0_raises(self):
        """Block 0 is invalid."""
        bv = BlockView(duration_seconds=10.0, block_duration_ms=1000)
        with pytest.raises(ValueError, match="Block must be >= 1"):
            bv.to_time(0)

    def test_negative_block_raises(self):
        """Negative block is invalid."""
        bv = BlockView(duration_seconds=10.0, block_duration_ms=1000)
        with pytest.raises(ValueError, match="Block must be >= 1"):
            bv.to_time(-1)


class TestBlockToTimeEnd:
    """Tests for block end time."""

    def test_block_1_ends_at_1_second(self):
        """Block 1 ends at 1 second (with 1000ms blocks)."""
        bv = BlockView(duration_seconds=10.0, block_duration_ms=1000)
        assert bv.to_time_end(1) == 1.0

    def test_block_10_ends_at_10_seconds(self):
        """Block 10 ends at 10 seconds."""
        bv = BlockView(duration_seconds=10.0, block_duration_ms=1000)
        assert bv.to_time_end(10) == 10.0


class TestTimeToBlock:
    """Tests for time to block number conversion."""

    def test_time_0_is_block_1(self):
        """Time 0 is in block 1."""
        bv = BlockView(duration_seconds=10.0, block_duration_ms=1000)
        assert bv.from_time(0.0) == 1

    def test_time_0_5_is_block_1(self):
        """Time 0.5 is still in block 1."""
        bv = BlockView(duration_seconds=10.0, block_duration_ms=1000)
        assert bv.from_time(0.5) == 1

    def test_time_1_0_is_block_2(self):
        """Time 1.0 is in block 2."""
        bv = BlockView(duration_seconds=10.0, block_duration_ms=1000)
        assert bv.from_time(1.0) == 2

    def test_time_9_5_is_block_10(self):
        """Time 9.5 is in block 10."""
        bv = BlockView(duration_seconds=10.0, block_duration_ms=1000)
        assert bv.from_time(9.5) == 10

    def test_negative_time_raises(self):
        """Negative time is invalid."""
        bv = BlockView(duration_seconds=10.0, block_duration_ms=1000)
        with pytest.raises(ValueError, match="Time must be >= 0"):
            bv.from_time(-1.0)


class TestClamp:
    """Tests for clamping block numbers."""

    def test_clamp_within_range(self):
        """Block within range is unchanged."""
        bv = BlockView(duration_seconds=10.0, block_duration_ms=1000)
        assert bv.clamp(5) == 5

    def test_clamp_below_range(self):
        """Block below 1 is clamped to 1."""
        bv = BlockView(duration_seconds=10.0, block_duration_ms=1000)
        assert bv.clamp(0) == 1
        assert bv.clamp(-5) == 1

    def test_clamp_above_range(self):
        """Block above count is clamped to count."""
        bv = BlockView(duration_seconds=10.0, block_duration_ms=1000)
        assert bv.clamp(15) == 10
        assert bv.clamp(100) == 10

    def test_clamp_empty_timeline(self):
        """Empty timeline clamps to 1."""
        bv = BlockView(duration_seconds=0.0, block_duration_ms=1000)
        assert bv.clamp(5) == 1
