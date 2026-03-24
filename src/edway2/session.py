"""Session model with Track/Clip dataclasses.

Position-based clips where gaps are implicit (no clip = silence).
"""

from dataclasses import dataclass, field, asdict
from pathlib import Path
import json


@dataclass
class Clip:
    """A reference to a portion of a source audio file."""

    source: str  # relative path to source file
    source_start: float  # start time in source file (seconds)
    source_end: float  # end time in source file (seconds)
    position: float  # position within track (seconds)
    gain: float = 0.0  # dB
    fade_in: float = 0.0  # seconds
    fade_out: float = 0.0  # seconds
    effects: list[dict] = field(default_factory=list)

    # Metadata from source file (not serialized to JSON, loaded on demand)
    _sample_rate: int | None = field(default=None, repr=False)
    _channels: int | None = field(default=None, repr=False)

    @property
    def duration(self) -> float:
        """Duration of this clip in seconds."""
        return self.source_end - self.source_start

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict."""
        return {
            "source": self.source,
            "source_start": self.source_start,
            "source_end": self.source_end,
            "position": self.position,
            "gain": self.gain,
            "fade_in": self.fade_in,
            "fade_out": self.fade_out,
            "effects": self.effects,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Clip":
        """Create Clip from dict."""
        return cls(
            source=data["source"],
            source_start=data["source_start"],
            source_end=data["source_end"],
            position=data["position"],
            gain=data.get("gain", 0.0),
            fade_in=data.get("fade_in", 0.0),
            fade_out=data.get("fade_out", 0.0),
            effects=data.get("effects", []),
        )


@dataclass
class Track:
    """An audio track containing clips."""

    name: str
    start_time: float = 0.0  # offset in global timeline
    selected: bool = False  # commands operate on selected tracks
    muted: bool = False  # excluded from playback
    soloed: bool = False  # solo playback mode
    record: bool = False  # armed for recording
    gain: float = 0.0  # dB
    effects: list[dict] = field(default_factory=list)
    clips: list[Clip] = field(default_factory=list)

    def clips_at(self, global_time: float) -> list[Clip]:
        """Return clips that overlap the given global time."""
        result = []
        for clip in self.clips:
            clip_start = self.start_time + clip.position
            clip_end = clip_start + clip.duration
            if clip_start <= global_time < clip_end:
                result.append(clip)
        return result

    def global_position(self, clip: Clip) -> float:
        """Return clip's position in global timeline."""
        return self.start_time + clip.position

    @property
    def duration(self) -> float:
        """Duration of this track (end of last clip)."""
        if not self.clips:
            return 0.0
        max_end = 0.0
        for clip in self.clips:
            end = clip.position + clip.duration
            max_end = max(max_end, end)
        return max_end

    def to_dict(self) -> dict:
        """Convert to JSON-serializable dict."""
        return {
            "name": self.name,
            "start_time": self.start_time,
            "selected": self.selected,
            "muted": self.muted,
            "soloed": self.soloed,
            "record": self.record,
            "gain": self.gain,
            "effects": self.effects,
            "clips": [c.to_dict() for c in self.clips],
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Track":
        """Create Track from dict."""
        return cls(
            name=data["name"],
            start_time=data.get("start_time", 0.0),
            selected=data.get("selected", False),
            muted=data.get("muted", False),
            soloed=data.get("soloed", False),
            record=data.get("record", False),
            gain=data.get("gain", 0.0),
            effects=data.get("effects", []),
            clips=[Clip.from_dict(c) for c in data.get("clips", [])],
        )


@dataclass
class Session:
    """Represents an editing session with tracks and metadata."""

    name: str = "untitled"
    sample_rate: int = 44100
    block_duration_ms: int = 1000
    master_gain: float = 0.0
    current_position: float = 0.0  # seconds
    current_track: int = 0
    marks: dict[str, float] = field(default_factory=dict)  # name → seconds
    regions: dict[str, tuple[float, float]] = field(default_factory=dict)
    tracks: list[Track] = field(default_factory=list)

    @classmethod
    def new(cls, name: str = "untitled") -> "Session":
        """Create new session with one empty track.

        Args:
            name: Name for the session.

        Returns:
            New Session instance.
        """
        session = cls(name=name)
        session.tracks.append(Track(name="Track 1"))
        return session

    @classmethod
    def from_file(cls, path: Path) -> "Session":
        """Load session from .edway JSON file.

        Args:
            path: Path to .edway file.

        Returns:
            Loaded Session instance.
        """
        with open(path) as f:
            data = json.load(f)

        return cls(
            name=data.get("name", "untitled"),
            sample_rate=data.get("sample_rate", 44100),
            block_duration_ms=data.get("block_duration_ms", 1000),
            master_gain=data.get("master_gain", 0.0),
            current_position=data.get("current_position", 0.0),
            current_track=data.get("current_track", 0),
            marks=data.get("marks", {}),
            regions={k: tuple(v) for k, v in data.get("regions", {}).items()},
            tracks=[Track.from_dict(t) for t in data.get("tracks", [])],
        )

    def to_file(self, path: Path) -> None:
        """Save session to .edway JSON file.

        Args:
            path: Path to .edway file.
        """
        data = {
            "version": "2.0",
            "name": self.name,
            "sample_rate": self.sample_rate,
            "block_duration_ms": self.block_duration_ms,
            "master_gain": self.master_gain,
            "current_position": self.current_position,
            "current_track": self.current_track,
            "marks": self.marks,
            "regions": {k: list(v) for k, v in self.regions.items()},
            "tracks": [t.to_dict() for t in self.tracks],
        }

        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    def get_track(self, index: int) -> Track:
        """Get track by index.

        Args:
            index: 0-based track index.

        Returns:
            Track at index.

        Raises:
            IndexError: If index out of range.
        """
        return self.tracks[index]

    def add_track(self, name: str | None = None) -> int:
        """Add a new audio track.

        Args:
            name: Optional track name. Defaults to "Track N".

        Returns:
            Index of new track.
        """
        index = len(self.tracks)
        if name is None:
            name = f"Track {index + 1}"
        self.tracks.append(Track(name=name))
        return index

    def remove_track(self, index: int) -> None:
        """Remove track by index.

        Args:
            index: 0-based track index.

        Raises:
            IndexError: If index out of range.
            ValueError: If track is not empty.
        """
        track = self.tracks[index]
        if len(track.clips) > 0:
            raise ValueError(f"Track {index + 1} is not empty")
        del self.tracks[index]

    @property
    def duration(self) -> float:
        """Global timeline duration (end of last clip across all tracks)."""
        if not self.tracks:
            return 0.0
        max_end = 0.0
        for track in self.tracks:
            for clip in track.clips:
                end = track.start_time + clip.position + clip.duration
                max_end = max(max_end, end)
        return max_end

    @property
    def track_count(self) -> int:
        """Number of tracks."""
        return len(self.tracks)

    def selected_tracks(self) -> list[Track]:
        """Return selected tracks, or [current_track] if none selected."""
        selected = [t for t in self.tracks if t.selected]
        return selected if selected else [self.tracks[self.current_track]]

    # Compatibility properties for old API (muted_tracks/soloed_tracks as sets)

    @property
    def muted_tracks(self) -> "_MutedTracksProxy":
        """Compatibility: return set-like object for muted track indices."""
        return _MutedTracksProxy(self)

    @property
    def soloed_tracks(self) -> "_SoloedTracksProxy":
        """Compatibility: return set-like object for soloed track indices."""
        return _SoloedTracksProxy(self)


class _MutedTracksProxy:
    """Proxy to make muted tracks look like a set of indices."""

    def __init__(self, session: Session):
        self._session = session

    def add(self, index: int) -> None:
        self._session.tracks[index].muted = True

    def discard(self, index: int) -> None:
        if 0 <= index < len(self._session.tracks):
            self._session.tracks[index].muted = False

    def __contains__(self, index: int) -> bool:
        if 0 <= index < len(self._session.tracks):
            return self._session.tracks[index].muted
        return False

    def __iter__(self):
        return (i for i, t in enumerate(self._session.tracks) if t.muted)


class _SoloedTracksProxy:
    """Proxy to make soloed tracks look like a set of indices."""

    def __init__(self, session: Session):
        self._session = session

    def add(self, index: int) -> None:
        self._session.tracks[index].soloed = True

    def discard(self, index: int) -> None:
        if 0 <= index < len(self._session.tracks):
            self._session.tracks[index].soloed = False

    def __contains__(self, index: int) -> bool:
        if 0 <= index < len(self._session.tracks):
            return self._session.tracks[index].soloed
        return False

    def __iter__(self):
        return (i for i, t in enumerate(self._session.tracks) if t.soloed)
