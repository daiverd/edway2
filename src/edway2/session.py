"""Session model wrapping OpenTimelineIO Timeline."""

from dataclasses import dataclass, field
from pathlib import Path
import json

import opentimelineio as otio


@dataclass
class Session:
    """Represents an editing session with timeline and metadata."""

    timeline: otio.schema.Timeline
    current_position: float = 0.0  # seconds
    current_track: int = 0
    marks: dict[str, float] = field(default_factory=dict)  # name → seconds
    regions: dict[str, tuple[float, float]] = field(default_factory=dict)  # name → (start, end)
    muted_tracks: set[int] = field(default_factory=set)
    soloed_tracks: set[int] = field(default_factory=set)
    block_duration_ms: int = 1000

    @classmethod
    def new(cls, name: str = "untitled") -> "Session":
        """Create a new empty session.

        Args:
            name: Name for the timeline.

        Returns:
            New Session instance.
        """
        timeline = otio.schema.Timeline(name=name)
        # Add one empty audio track by default
        track = otio.schema.Track(name="Track 1", kind=otio.schema.TrackKind.Audio)
        timeline.tracks.append(track)
        return cls(timeline=timeline)

    @classmethod
    def from_file(cls, path: Path) -> "Session":
        """Load session from .edway file.

        Args:
            path: Path to .edway file.

        Returns:
            Loaded Session instance.
        """
        # Use otio_json adapter explicitly for .edway files
        timeline = otio.adapters.read_from_file(str(path), adapter_name="otio_json")

        # Extract edway2 metadata
        metadata = timeline.metadata.get("edway2", {})

        return cls(
            timeline=timeline,
            current_position=metadata.get("current_position", 0.0),
            current_track=metadata.get("current_track", 0),
            marks=metadata.get("marks", {}),
            regions={k: tuple(v) for k, v in metadata.get("regions", {}).items()},
            muted_tracks=set(metadata.get("muted_tracks", [])),
            soloed_tracks=set(metadata.get("soloed_tracks", [])),
            block_duration_ms=metadata.get("block_duration_ms", 1000),
        )

    def to_file(self, path: Path) -> None:
        """Save session to .edway file.

        Args:
            path: Path to .edway file.
        """
        # Store edway2 metadata in timeline
        self.timeline.metadata["edway2"] = {
            "version": "2.0",
            "current_position": self.current_position,
            "current_track": self.current_track,
            "marks": self.marks,
            "regions": {k: list(v) for k, v in self.regions.items()},
            "muted_tracks": list(self.muted_tracks),
            "soloed_tracks": list(self.soloed_tracks),
            "block_duration_ms": self.block_duration_ms,
        }

        # Use otio_json adapter explicitly for .edway files
        otio.adapters.write_to_file(self.timeline, str(path), adapter_name="otio_json")

    def get_track(self, index: int) -> otio.schema.Track:
        """Get track by index.

        Args:
            index: 0-based track index.

        Returns:
            Track at index.

        Raises:
            IndexError: If index out of range.
        """
        return self.timeline.tracks[index]

    def add_track(self, name: str | None = None) -> int:
        """Add a new audio track.

        Args:
            name: Optional track name. Defaults to "Track N".

        Returns:
            Index of new track.
        """
        index = len(self.timeline.tracks)
        if name is None:
            name = f"Track {index + 1}"
        track = otio.schema.Track(name=name, kind=otio.schema.TrackKind.Audio)
        self.timeline.tracks.append(track)
        return index

    def remove_track(self, index: int) -> None:
        """Remove track by index.

        Args:
            index: 0-based track index.

        Raises:
            IndexError: If index out of range.
            ValueError: If track is not empty.
        """
        track = self.timeline.tracks[index]
        if len(track) > 0:
            raise ValueError(f"Track {index + 1} is not empty")
        del self.timeline.tracks[index]

    @property
    def duration(self) -> float:
        """Total duration in seconds."""
        if not self.timeline.tracks:
            return 0.0
        # Get max duration across all tracks
        max_duration = 0.0
        for track in self.timeline.tracks:
            track_duration = track.duration().to_seconds()
            if track_duration > max_duration:
                max_duration = track_duration
        return max_duration

    @property
    def track_count(self) -> int:
        """Number of tracks."""
        return len(self.timeline.tracks)
