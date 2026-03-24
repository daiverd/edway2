# edway2 Specification

Non-destructive multitrack audio editor with line-editor UX.

**License**: GPL-3.0
**Python**: 3.11+
**Repository**: `edway2/`

---

## Dependencies

```toml
[project]
dependencies = [
    "pedalboard>=0.9.0",
    "soundfile>=0.12.0",
    "sounddevice>=0.4.0",
    "prompt-toolkit>=3.0.0",
    "gitpython>=3.1.0",
    "numpy>=1.24.0",
]

[project.optional-dependencies]
dev = ["pytest>=8.0.0", "pytest-mock>=3.0.0"]
export = ["opentimelineio>=0.15.0"]  # for NLE export
```

---

## Project Structure

```
edway2/
├── pyproject.toml
├── README.md
├── LICENSE
├── src/
│   └── edway2/
│       ├── __init__.py          # version string
│       ├── __main__.py          # entry: python -m edway2
│       ├── cli.py               # CLI argument parsing, main()
│       ├── repl.py              # prompt_toolkit REPL loop
│       ├── parser.py            # command grammar → Command objects
│       ├── commands/
│       │   ├── __init__.py      # command registry
│       │   ├── playback.py      # p, z
│       │   ├── editing.py       # d, m, t, rd, rm, rt, split
│       │   ├── files.py         # r, w, save, load
│       │   ├── marks.py         # k, region
│       │   ├── tracks.py        # tr, tracks, ts, mute, solo, addtrack, rmtrack
│       │   ├── effects.py       # db, fi, fo, xf, mx, fx
│       │   ├── info.py          # ?, =, sr, nc, ms, nb
│       │   ├── undo.py          # u, u!, U, uh, save
│       │   ├── generate.py      # gen, cap
│       │   └── misc.py          # q, qt, l, h, !
│       ├── session.py           # Session class (our custom format)
│       ├── project.py           # Project class (folder, git, paths)
│       ├── blocks.py            # BlockView class
│       ├── audio.py             # playback, recording, rendering
│       ├── mixer.py             # real-time mixing engine
│       ├── effects.py           # effect application via pedalboard
│       └── config.py            # config file loading
└── tests/
    └── ...
```

---

## Timeline Format

Custom JSON format designed for editing operations. Gaps are implicit (no clip = silence).
OTIO export available for NLE interchange.

### Data Model

```
Project
├── name: str
├── sample_rate: int = 44100
├── block_duration_ms: int = 1000
├── master_gain: float = 0.0 (dB)
├── current_position: float = 0.0 (seconds)
├── current_track: int = 0
├── marks: dict[str, float]           # name → time in seconds
├── regions: dict[str, (float, float)] # name → (start, end)
└── tracks: list[Track]

Track
├── name: str
├── start_time: float = 0.0   # offset in global timeline
├── selected: bool = false    # commands operate on selected tracks
├── muted: bool = false       # excluded from playback
├── soloed: bool = false      # solo playback mode
├── record: bool = false      # armed for recording
├── gain: float = 0.0 (dB)
├── effects: list[Effect]
└── clips: list[Clip]

Clip
├── source: str               # path relative to sources/
├── source_start: float       # start time in source file (seconds)
├── source_end: float         # end time in source file (seconds)
├── position: float           # position within track (seconds)
├── gain: float = 0.0 (dB)
├── fade_in: float = 0.0      # fade duration (seconds)
├── fade_out: float = 0.0
└── effects: list[Effect]

Effect
├── type: str                 # "gain", "reverb", "vst:/path/to.vst3"
└── params: dict              # effect-specific parameters
```

### Position Calculation

```
Global position = track.start_time + clip.position
Clip plays from: global_position to global_position + (source_end - source_start)
```

Example:
```
Track 1 (start_time=1.0):
  Clip A: position=0.0, source_range=[0,2]  → plays at global 1.0-3.0
  Clip B: position=3.0, source_range=[0,1]  → plays at global 4.0-5.0
  Gap from 3.0-4.0 (no clip) → silence at global 3.0-4.0
```

### JSON Format

```json
{
  "version": "2.0",
  "name": "my project",
  "sample_rate": 44100,
  "block_duration_ms": 1000,
  "master_gain": 0.0,
  "current_position": 0.0,
  "current_track": 0,
  "marks": {"a": 5.0, "intro_end": 30.0},
  "regions": {"chorus": [60.0, 90.0]},
  "tracks": [
    {
      "name": "Vocals",
      "start_time": 0.0,
      "selected": true,
      "muted": false,
      "soloed": false,
      "record": false,
      "gain": -3.0,
      "effects": [],
      "clips": [
        {
          "source": "sources/vocal_take1.wav",
          "source_start": 0.0,
          "source_end": 30.0,
          "position": 0.0,
          "gain": 0.0,
          "fade_in": 0.0,
          "fade_out": 0.5,
          "effects": []
        },
        {
          "source": "sources/vocal_take2.wav",
          "source_start": 5.0,
          "source_end": 20.0,
          "position": 35.0,
          "gain": -2.0,
          "fade_in": 0.1,
          "fade_out": 0.1,
          "effects": []
        }
      ]
    },
    {
      "name": "Drums",
      "start_time": 0.0,
      "selected": false,
      "muted": false,
      "soloed": false,
      "record": false,
      "gain": 0.0,
      "effects": [{"type": "compressor", "params": {"threshold": -10}}],
      "clips": [
        {
          "source": "sources/drums.wav",
          "source_start": 0.0,
          "source_end": 180.0,
          "position": 0.0,
          "gain": 0.0,
          "fade_in": 0.0,
          "fade_out": 0.0,
          "effects": []
        }
      ]
    }
  ]
}
```

### Why This Format

| OTIO (sequential) | Our format (position-based) |
|-------------------|---------------------------|
| Gap objects needed | Gaps implicit (no clip = silence) |
| Items placed one after another | Clips have absolute positions |
| Split/delete requires gap management | Just remove clip or adjust range |
| C++ interop issues | Pure Python/JSON |
| Complex for editing | Simple operations |
| Great for interchange | Export to OTIO when needed |

---

## Core Interfaces

### Session

```python
# src/edway2/session.py
from dataclasses import dataclass, field

@dataclass
class Clip:
    source: str                    # relative path to source file
    source_start: float            # seconds
    source_end: float              # seconds
    position: float                # position in track (seconds)
    gain: float = 0.0              # dB
    fade_in: float = 0.0           # seconds
    fade_out: float = 0.0          # seconds
    effects: list[dict] = field(default_factory=list)

    @property
    def duration(self) -> float:
        return self.source_end - self.source_start

@dataclass
class Track:
    name: str
    start_time: float = 0.0        # offset in global timeline
    selected: bool = False
    muted: bool = False
    soloed: bool = False
    record: bool = False
    gain: float = 0.0              # dB
    effects: list[dict] = field(default_factory=list)
    clips: list[Clip] = field(default_factory=list)

    def clips_at(self, global_time: float) -> list[Clip]:
        """Return clips that overlap the given global time."""
        ...

    def global_position(self, clip: Clip) -> float:
        """Return clip's position in global timeline."""
        return self.start_time + clip.position

@dataclass
class Session:
    name: str = "untitled"
    sample_rate: int = 44100
    block_duration_ms: int = 1000
    master_gain: float = 0.0
    current_position: float = 0.0
    current_track: int = 0
    marks: dict[str, float] = field(default_factory=dict)
    regions: dict[str, tuple[float, float]] = field(default_factory=dict)
    tracks: list[Track] = field(default_factory=list)

    @classmethod
    def new(cls, name: str = "untitled") -> "Session":
        """Create new session with one empty track."""
        session = cls(name=name)
        session.tracks.append(Track(name="Track 1"))
        return session

    @classmethod
    def from_file(cls, path: Path) -> "Session":
        """Load from .edway JSON file."""
        ...

    def to_file(self, path: Path) -> None:
        """Save to .edway JSON file."""
        ...

    @property
    def duration(self) -> float:
        """Global timeline duration (end of last clip)."""
        max_end = 0.0
        for track in self.tracks:
            for clip in track.clips:
                end = track.start_time + clip.position + clip.duration
                max_end = max(max_end, end)
        return max_end

    def get_track(self, index: int) -> Track:
        return self.tracks[index]

    def selected_tracks(self) -> list[Track]:
        """Return selected tracks, or [current_track] if none selected."""
        selected = [t for t in self.tracks if t.selected]
        return selected if selected else [self.tracks[self.current_track]]
```

### Project

```python
# src/edway2/project.py

@dataclass
class Project:
    path: Path
    session: Session
    repo: git.Repo
    _dirty: bool = False
    _undo_offset: int = 0

    @classmethod
    def create(cls, path: Path) -> "Project":
        """Create new project folder with structure."""
        # Creates:
        #   path/
        #   path/path.edway
        #   path/sources/
        #   path/renders/
        #   path/.git/
        #   path/.gitignore (ignores sources/, renders/)
        ...

    @classmethod
    def open(cls, path: Path) -> "Project":
        """Open existing project."""
        ...

    @property
    def blocks(self) -> BlockView:
        return BlockView(
            duration_seconds=self.session.duration,
            block_duration_ms=self.session.block_duration_ms,
        )
```

### Mixer

```python
# src/edway2/mixer.py

class Mixer:
    """Real-time audio mixer using sounddevice callbacks."""

    def __init__(self, session: Session, project_path: Path):
        self.session = session
        self.project_path = project_path
        self.position = 0.0
        self.playing = False
        self.clip_cache = {}  # source → audio data

    def get_audio_at(self, time: float, num_frames: int) -> np.ndarray:
        """Render audio at given time position."""
        output = np.zeros((num_frames, 2), dtype=np.float32)
        sr = self.session.sample_rate

        # Check for solo mode
        any_solo = any(t.soloed for t in self.session.tracks)

        for track in self.session.tracks:
            if track.muted:
                continue
            if any_solo and not track.soloed:
                continue

            track_audio = self._render_track(track, time, num_frames)
            track_audio *= db_to_linear(track.gain)
            output += track_audio

        output *= db_to_linear(self.session.master_gain)
        return output

    def _render_track(self, track: Track, time: float, num_frames: int) -> np.ndarray:
        """Render a single track."""
        output = np.zeros((num_frames, 2), dtype=np.float32)
        sr = self.session.sample_rate

        for clip in track.clips:
            global_start = track.start_time + clip.position
            global_end = global_start + clip.duration

            # Check if clip overlaps render range
            render_end = time + num_frames / sr
            if global_end <= time or global_start >= render_end:
                continue

            # Calculate overlap and render
            ...

        return output

    def play(self, start: float, end: float) -> bool:
        """Play range, return True if stopped by user."""
        ...
```

---

## Editing Operations

With position-based clips, editing becomes simple:

### Delete (d) - Non-ripple
```python
def delete_range(track: Track, start: float, end: float):
    """Remove or trim clips in range. No gap objects needed."""
    new_clips = []
    for clip in track.clips:
        clip_start = clip.position
        clip_end = clip.position + clip.duration

        if clip_end <= start or clip_start >= end:
            # Outside range - keep unchanged
            new_clips.append(clip)
        elif clip_start >= start and clip_end <= end:
            # Fully inside range - remove entirely
            pass
        elif clip_start < start and clip_end > end:
            # Range is inside clip - split into two
            # Before part
            before = Clip(
                source=clip.source,
                source_start=clip.source_start,
                source_end=clip.source_start + (start - clip_start),
                position=clip.position,
            )
            # After part
            after = Clip(
                source=clip.source,
                source_start=clip.source_start + (end - clip_start),
                source_end=clip.source_end,
                position=end,  # starts at end of deleted range
            )
            new_clips.extend([before, after])
        elif clip_start < start:
            # Trim end
            clip.source_end = clip.source_start + (start - clip_start)
            new_clips.append(clip)
        else:
            # Trim start
            trim = end - clip_start
            clip.source_start += trim
            clip.position = end
            new_clips.append(clip)

    track.clips = new_clips
```

### Ripple Delete (rd)
```python
def ripple_delete_range(track: Track, start: float, end: float):
    """Remove clips in range and shift following clips left."""
    duration = end - start
    delete_range(track, start, end)

    # Shift clips after the deleted range
    for clip in track.clips:
        if clip.position >= end:
            clip.position -= duration
```

### Move (m) - Non-ripple
```python
def move_range(track: Track, start: float, end: float, dest: float):
    """Move clips from range to destination."""
    # Extract clips in range
    moving = [c for c in track.clips
              if c.position >= start and c.position + c.duration <= end]

    # Remove from original position
    delete_range(track, start, end)

    # Adjust positions and add at destination
    offset = dest - start
    for clip in moving:
        clip.position += offset
        track.clips.append(clip)
```

---

## Command Reference

(Same as before - p, z, d, m, t, rd, rm, rt, etc.)

### Track Selection

#### `ts` - Track Select
```
ts [tracks]

Select tracks for multi-track operations.

Examples:
  ts 1        → select track 1 only
  ts 1,3      → select tracks 1 and 3
  ts 1-4      → select tracks 1 through 4
  ts *        → select all tracks
  ts          → clear selection (use current track)
```

Commands like `d`, `m`, `t` operate on all selected tracks.

---

## Implementation Phases

Each phase: write tests first, implement, verify manually.

### Phase 0: Skeleton ✓
Basic CLI structure.

### Phase 1: REPL Shell ✓
Prompt, command loop, quit.

### Phase 2: Project & Session ✓
- Removed OTIO dependency from core
- Session with Track/Clip dataclasses
- Simple JSON serialization

### Phase 3: Command Parser ✓
Already complete.

### Phase 4: Read Audio File ✓
- Creates Clip with position
- Appends to track.clips

### Phase 5: Block Addressing ✓
Blocks are just a view over time.

### Phase 6: Playback ✓
- Position-based rendering
- Walk clips by position, render overlapping ones
- No gap objects needed

### Phase 7: Git Undo ✓
Works the same - just tracking JSON file.

### Phase 8: Basic Editing ✓
- Delete: remove/trim clips, no gap management
- Move: extract clips, delete source, insert at dest
- Copy: extract clips, insert at dest

### Phase 9: Ripple Editing ✓
- `rd`: Ripple delete - removes content and shifts following clips left
- `rm`: Ripple move - closes gap at source, makes room at destination
- `rt`: Ripple copy - makes room at destination, timeline expands

### Phase 10: Marks ✓
Works the same.

### Phase 11: Multitrack ✓
- `tr` / `track`: Switch current track
- `ts`: Track selection (1,3 or 1-4 or *)
- `tracks`: List all tracks with status
- `addtrack` / `rmtrack`: Add/remove tracks

### Phase 12: Mute/Solo ✓
- `mute`: Toggle mute on track(s)
- `solo`: Toggle solo on track(s)
- Playback respects mute/solo, mixes all unmuted tracks

### Phase 13: Export ✓
**Changes**:
- Audio export (w command) works the same
- OTIO export moved to Phase 19

### Phase 14-16: Effects
Works the same - effects stored in clip/track.

### Phase 17-18: Regions, Generate, Capture
Works the same.

### Phase 19: OTIO Export
**New phase**:
- Convert our format to OTIO for NLE interchange
- `export otio` command

```python
def export_to_otio(session: Session, path: Path):
    """Convert session to OTIO timeline."""
    import opentimelineio as otio

    timeline = otio.schema.Timeline(name=session.name)

    for track in session.tracks:
        otio_track = otio.schema.Track(name=track.name)

        # Sort clips by position
        sorted_clips = sorted(track.clips, key=lambda c: c.position)

        current_time = 0.0
        for clip in sorted_clips:
            global_pos = track.start_time + clip.position

            # Insert gap if needed
            if global_pos > current_time:
                gap_duration = global_pos - current_time
                otio_track.append(make_gap(gap_duration))
                current_time = global_pos

            # Insert clip
            otio_track.append(make_clip(clip))
            current_time = global_pos + clip.duration

        timeline.tracks.append(otio_track)

    otio.adapters.write_to_file(timeline, str(path))
```

### Phase 20: Plugins
Works the same.

### Phase 21: Polish
- Callback-based playback for sample-accurate timing
- Help system
- Config file

---

## Migration Path

Since we have existing code using OTIO:

1. **Keep tests passing** during migration
2. **Session rewrite**: New dataclass model, JSON I/O
3. **Commands update**: Simplify delete/move/copy
4. **Playback update**: Position-based mixer
5. **Add OTIO export**: For interchange

The git undo, blocks, parser, and most commands work unchanged.
