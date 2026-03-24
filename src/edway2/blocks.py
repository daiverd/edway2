"""Block addressing for edway2.

Blocks are the fundamental unit of editing in edway. They provide a
virtual view over the timeline - the same audio can be viewed as
different numbers of blocks depending on block_duration_ms.

Blocks are 1-indexed (block 1 is the first block, like ed line numbers).

Gaps (silence) count as blocks - they're just silent content. The user
doesn't need to know whether a block is a Clip or Gap internally.
"""

from dataclasses import dataclass
from math import ceil, floor


@dataclass
class BlockView:
    """Virtual block view over a timeline duration.

    Attributes:
        duration_seconds: Total timeline duration in seconds (including gaps).
        block_duration_ms: Duration of each block in milliseconds.
    """

    duration_seconds: float
    block_duration_ms: int = 1000

    @property
    def count(self) -> int:
        """Number of blocks (1-indexed, so this is also the last block number).

        Returns 0 for empty timeline.
        """
        if self.duration_seconds <= 0:
            return 0
        return ceil(self.duration_seconds * 1000 / self.block_duration_ms)

    def to_time(self, block: int) -> float:
        """Block number (1-indexed) to start time in seconds.

        Args:
            block: Block number (1-indexed).

        Returns:
            Start time of the block in seconds.

        Raises:
            ValueError: If block < 1.
        """
        if block < 1:
            raise ValueError(f"Block must be >= 1, got {block}")
        return (block - 1) * self.block_duration_ms / 1000

    def to_time_end(self, block: int) -> float:
        """Block number to end time in seconds.

        Args:
            block: Block number (1-indexed).

        Returns:
            End time of the block in seconds.

        Raises:
            ValueError: If block < 1.
        """
        if block < 1:
            raise ValueError(f"Block must be >= 1, got {block}")
        return block * self.block_duration_ms / 1000

    def from_time(self, seconds: float) -> int:
        """Time in seconds to block number (1-indexed).

        Args:
            seconds: Time in seconds.

        Returns:
            Block number containing that time (1-indexed).

        Raises:
            ValueError: If seconds < 0.
        """
        if seconds < 0:
            raise ValueError(f"Time must be >= 0, got {seconds}")
        raw = seconds * 1000 / self.block_duration_ms
        # Round to nearest integer when within floating-point epsilon,
        # so that from_time(to_time(b)) == b holds exactly.
        rounded = round(raw)
        if abs(raw - rounded) < 1e-9:
            raw = rounded
        return floor(raw) + 1

    def clamp(self, block: int) -> int:
        """Clamp block number to valid range [1, count].

        Args:
            block: Block number to clamp.

        Returns:
            Block number clamped to [1, count], or 1 if count is 0.
        """
        if self.count == 0:
            return 1
        return max(1, min(block, self.count))

    def validate(self, block: int) -> None:
        """Validate block number is in range [1, count].

        Args:
            block: Block number to validate.

        Raises:
            ValueError: If block is out of range.
        """
        if block < 1:
            raise ValueError(f"block must be >= 1, got {block}")
        if self.count > 0 and block > self.count:
            raise ValueError(f"block {block} out of range (1-{self.count})")
        if self.count == 0:
            raise ValueError("no blocks in timeline")
