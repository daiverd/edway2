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
    "opentimelineio>=0.15.0",
    "prompt-toolkit>=3.0.0",
    "gitpython>=3.1.0",
]

[project.optional-dependencies]
dev = ["pytest>=8.0.0", "pytest-mock>=3.0.0"]
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
│       │   ├── tracks.py        # tr, tracks, mute, solo, addtrack, rmtrack
│       │   ├── effects.py       # db, fi, fo, xf, mx, fx
│       │   ├── info.py          # ?, =, sr, nc, ms, nb
│       │   ├── undo.py          # u, U, uh, branch, checkout, tag
│       │   ├── generate.py      # gen, cap
│       │   └── misc.py          # q, qt, l, h, !
│       ├── session.py           # Session class (wraps OTIO Timeline)
│       ├── project.py           # Project class (folder, git, paths)
│       ├── blocks.py            # BlockView class
│       ├── audio.py             # playback, recording, rendering
│       ├── effects.py           # effect application via pedalboard
│       ├── git_undo.py          # git operations for undo
│       └── config.py            # config file loading
└── tests/
    ├── conftest.py              # fixtures: tmp_project, sample_wav
    ├── test_cli.py
    ├── test_parser.py
    ├── test_session.py
    ├── test_project.py
    ├── test_blocks.py
    ├── test_commands_playback.py
    ├── test_commands_editing.py
    ├── test_commands_files.py
    └── ...
```

---

## Core Interfaces

### Session

```python
# src/edway2/session.py
from dataclasses import dataclass, field
import opentimelineio as otio

@dataclass
class Session:
    timeline: otio.Timeline
    current_position: float = 0.0  # seconds
    current_track: int = 0
    marks: dict[str, float] = field(default_factory=dict)  # name → seconds
    regions: dict[str, tuple[float, float]] = field(default_factory=dict)  # name → (start, end)
    muted_tracks: set[int] = field(default_factory=set)
    soloed_tracks: set[int] = field(default_factory=set)

    @classmethod
    def new(cls, name: str = "untitled") -> "Session": ...

    @classmethod
    def from_file(cls, path: Path) -> "Session": ...

    def to_file(self, path: Path) -> None: ...

    def get_track(self, index: int) -> otio.Track: ...

    def add_track(self, name: str) -> int: ...

    def remove_track(self, index: int) -> None: ...

    @property
    def duration(self) -> float:
        """Total duration in seconds."""
        ...
```

### Project

```python
# src/edway2/project.py
from pathlib import Path
import git

@dataclass
class Project:
    path: Path  # project folder
    session: Session
    repo: git.Repo

    @classmethod
    def create(cls, path: Path) -> "Project":
        """Create new project folder with structure."""
        # Creates:
        #   path/
        #   path/path.edway
        #   path/sources/
        #   path/renders/
        #   path/.git/
        ...

    @classmethod
    def open(cls, path: Path) -> "Project":
        """Open existing project."""
        ...

    def save(self, message: str = "edit") -> None:
        """Save session and commit."""
        ...

    def undo(self) -> None:
        """git checkout HEAD~1"""
        ...

    def redo(self) -> None:
        """git checkout HEAD@{1}"""
        ...

    def resolve_path(self, filepath: Path) -> str:
        """Return relative path if inside project, absolute otherwise."""
        ...

    @property
    def sources_dir(self) -> Path:
        return self.path / "sources"

    @property
    def renders_dir(self) -> Path:
        return self.path / "renders"

    @property
    def session_file(self) -> Path:
        return self.path / f"{self.path.name}.edway"
```

### BlockView

```python
# src/edway2/blocks.py
from math import ceil, floor

@dataclass
class BlockView:
    duration_seconds: float  # total timeline duration
    block_duration_ms: int = 1000

    @property
    def count(self) -> int:
        """Number of blocks (1-indexed, so this is also the last block number)."""
        if self.duration_seconds <= 0:
            return 0
        return ceil(self.duration_seconds * 1000 / self.block_duration_ms)

    def to_time(self, block: int) -> float:
        """Block number (1-indexed) to start time in seconds."""
        if block < 1:
            raise ValueError(f"Block must be >= 1, got {block}")
        return (block - 1) * self.block_duration_ms / 1000

    def to_time_end(self, block: int) -> float:
        """Block number to end time in seconds."""
        return block * self.block_duration_ms / 1000

    def from_time(self, seconds: float) -> int:
        """Time in seconds to block number (1-indexed)."""
        if seconds < 0:
            raise ValueError(f"Time must be >= 0, got {seconds}")
        return floor(seconds * 1000 / self.block_duration_ms) + 1
```

### Command

```python
# src/edway2/parser.py
from dataclasses import dataclass
from typing import Literal

@dataclass
class Address:
    """A single address in a command."""
    type: Literal["number", "dot", "dollar", "mark", "time"]
    value: int | str | float  # block number, mark name, or seconds
    offset: int = 0  # for +N or -N

@dataclass
class Command:
    """Parsed command."""
    name: str  # "p", "d", "rm", etc.
    addr1: Address | None = None
    addr2: Address | None = None
    dest: Address | None = None  # for m, t, rm, rt
    arg: str | None = None  # for r, w, db, etc.

def parse(line: str) -> Command:
    """Parse command line into Command object.

    Raises:
        ParseError: if syntax is invalid
    """
    ...
```

---

## Command Grammar

```
command     := [range] cmd [dest] [argument]
range       := addr ["," addr]
addr        := position [offset]
position    := NUMBER | "." | "$" | "'" LETTER | "@" TIME
offset      := ("+" | "-") NUMBER
dest        := addr  (for m, t, rm, rt only)
argument    := SPACE rest_of_line
TIME        := MINUTES ":" SECONDS ["." MILLIS]

cmd         := "p" | "z" | "d" | "m" | "t" | "rd" | "rm" | "rt" | ...
```

### Parse Examples

| Input | Command | addr1 | addr2 | dest | arg |
|-------|---------|-------|-------|------|-----|
| `p` | p | None | None | None | None |
| `5p` | p | 5 | None | None | None |
| `1,10p` | p | 1 | 10 | None | None |
| `.,$p` | p | . | $ | None | None |
| `'a,5p` | p | 'a | 5 | None | None |
| `5d` | d | 5 | None | None | None |
| `1,5d` | d | 1 | 5 | None | None |
| `5m10` | m | 5 | None | 10 | None |
| `1,5m10` | m | 1 | 5 | 10 | None |
| `5m$` | m | 5 | None | $ | None |
| `1,5rm10` | rm | 1 | 5 | 10 | None |
| `r test.wav` | r | None | None | None | "test.wav" |
| `5r test.wav` | r | 5 | None | None | "test.wav" |
| `w out.mp3` | w | None | None | None | "out.mp3" |
| `db -3` | db | None | None | None | "-3" |
| `1,10db` | db | 1 | 10 | None | None |
| `1,10db -3` | db | 1 | 10 | None | "-3" |
| `ka` | k | None | None | None | "a" |
| `tr 2` | tr | None | None | None | "2" |
| `@0:30,@1:00p` | p | @0:30 | @1:00 | None | None |

---

## Command Reference

### Playback

#### `p` - Play
```
[range]p

Play audio in range. All tracks mixed. Any key stops.
Default range: current block only.

Examples:
  p         → play current block
  5p        → play block 5
  1,10p     → play blocks 1-10
  .,$p      → play from current to end
  'a,'bp    → play from mark a to mark b
```

#### `z` - Play seconds
```
[addr]z[seconds]

Play N seconds starting from position.
Default: 5 seconds from current position.

Examples:
  z         → play 5 seconds from current
  z10       → play 10 seconds from current
  5z10      → play 10 seconds starting at block 5
```

### Editing (Non-Ripple)

#### `d` - Delete
```
[range]d

Remove content from timeline. Leaves gap (silence).

Examples:
  d         → delete current block (leaves gap)
  5d        → delete block 5
  1,5d      → delete blocks 1-5
```

#### `m` - Move
```
[range]m<dest>

Move content to destination. Source becomes gap. Layers at destination.

Examples:
  5m10      → move block 5 to position 10 (layers with existing)
  1,5m20    → move blocks 1-5 to position 20
  5m$       → move block 5 to end
```

#### `t` - Copy
```
[range]t<dest>

Copy content to destination. Layers at destination.

Examples:
  5t10      → copy block 5 to position 10
  1,5t$     → copy blocks 1-5 to end
```

### Editing (Ripple)

#### `rd` - Ripple Delete
```
[range]rd

Remove content AND close gap. Everything after shifts left.

Examples:
  5rd       → delete block 5, timeline shrinks
  1,5rd     → delete blocks 1-5, rest shifts left
```

#### `rm` - Ripple Move
```
[range]rm<dest>

Remove from source (close gap), insert at destination (shift right).

Examples:
  5rm10     → remove block 5, insert before block 10
  1,5rm$    → remove blocks 1-5, append at end
```

#### `rt` - Ripple Copy
```
[range]rt<dest>

Copy to destination, shift everything right.

Examples:
  5rt10     → copy block 5, insert before block 10
```

#### `split` - Split Clip
```
split

Split clip at current position into two clips.
```

### Marks & Regions

#### `k` - Set Mark
```
k<letter>

Set mark at current position. Stored as time (survives block resize).

Examples:
  ka        → set mark 'a' at current position
  kz        → set mark 'z'
```

#### `region` - Define Region
```
region <name> [range]

Define named region. Default range: current block.

Examples:
  region intro 1,30   → define "intro" as blocks 1-30
  region chorus       → define "chorus" as current block
```

#### `regions` - List Regions
```
regions

List all defined regions with their time ranges.
```

### Tracks

#### `tr` / `track` - Select Track
```
tr [N]

Show current track, or switch to track N.

Examples:
  tr        → show current track number and name
  tr 2      → switch to track 2
```

#### `tracks` - List Tracks
```
tracks

List all tracks with index, name, and mute/solo status.
```

#### `addtrack` - Add Track
```
addtrack [name]

Add new track. Optional name.

Examples:
  addtrack          → add track with default name
  addtrack vocals   → add track named "vocals"
```

#### `rmtrack` - Remove Track
```
rmtrack [N]

Remove track N (or current track). Must be empty.
```

#### `mute` - Mute Track
```
mute [N]

Toggle mute on track N (or current track).
```

#### `solo` - Solo Track
```
solo [N]

Toggle solo on track N (or current track).
```

### Files

#### `r` - Read
```
[addr]r <file>

Read audio file into current track at position.
Default position: end of track (append).

Examples:
  r test.wav        → append test.wav to current track
  1r test.wav       → insert at block 1
  r *.wav           → read all wav files (each to new session)
```

#### `w` - Write/Export
```
[range]w [file]

Render timeline to file. Goes to renders/ folder.
Default: entire timeline, default filename.

Examples:
  w                 → render to default name
  w out.mp3         → render to out.mp3
  1,10w clip.wav    → render blocks 1-10 to clip.wav
```

#### `save` - Save Session
```
save

Save session to project .edway file and commit.
```

#### `load` - Load Session
```
load <project>

Load existing project.
```

#### `f` - Filename
```
f [name]

Show or set project filename.
```

#### `ft` - File Type
```
ft [type]

Show or set default export format.

Examples:
  ft        → show current format
  ft mp3    → set default to mp3
```

### Effects

#### `db` - Gain/Loudness
```
[range]db [level]

Without level: show loudness (dB RMS) of range.
With level: apply gain to range (non-destructive).

Examples:
  db        → show loudness of current block
  1,10db    → show loudness of blocks 1-10
  db -3     → apply -3dB to current block
  1,10db -6 → apply -6dB to blocks 1-10
```

#### `fi` - Fade In
```
fi [seconds]

Apply fade in at start of timeline. Default: 1 second.

Examples:
  fi        → 1 second fade in
  fi 2.5    → 2.5 second fade in
```

#### `fo` - Fade Out
```
fo [seconds]

Apply fade out at end of timeline. Default: 1 second.
```

#### `xf` - Crossfade
```
xf [seconds]

Create crossfade at current position. Default: 0.5 seconds.
Requires two adjacent clips.
```

#### `mx` - Mix
```
[range]mx<session> [fade_in] [fade_out]

Mix another session into current track at range.

Examples:
  mx2               → mix session 2 into current position
  1,10mx2 0.5 1.0   → mix session 2 into blocks 1-10 with fades
```

#### `fx` - Add Effect
```
fx <effect>

Add effect to current range.

Examples:
  fx reverb         → add built-in reverb
  fx /path/to.vst3  → load VST3 plugin
```

#### `fxlist` - List Effects
```
fxlist

List effects on current range.
```

#### `fxrm` - Remove Effect
```
fxrm <index>

Remove effect by index from fxlist.
```

### Info

#### `?` - Session Info
```
?

Show: filename, duration, sample rate, channels, track count, block info.
```

#### `=` - Show Position
```
[addr]=

Show block number of address.

Examples:
  =         → show last block number ($)
  .=        → show current block number
  'a=       → show block number of mark a
```

#### `sr` - Sample Rate
```
sr

Show sample rate of current clip/track.
```

#### `nc` - Channels
```
nc

Show channel count of current clip/track.
```

#### `ms` - Milliseconds per Block
```
ms [N]

Show or set block duration in milliseconds.

Examples:
  ms        → show current (e.g., "1000")
  ms 500    → set to 500ms blocks
```

#### `nb` - Number of Blocks
```
nb [N]

Show or set total number of blocks.
Changes block duration to achieve target count.
```

### Undo

#### `u` - Undo
```
u

Undo last edit. Unlimited depth.
```

#### `U` - Redo
```
U

Redo last undone edit.
```

#### `uh` - Undo History
```
uh

Show recent edit history (git log).
```

#### `branch` - Create Branch
```
branch <name>

Create and switch to new branch.
```

#### `branches` - List Branches
```
branches

List all branches.
```

#### `checkout` - Switch Branch
```
checkout <name>

Switch to existing branch.
```

#### `tag` - Tag State
```
tag <name>

Tag current state for easy return.
```

### Generate

#### `gen` - Generate Audio
```
[addr]gen <seconds> [type] [freq]

Generate audio, save to sources/, add to track.
Types: sin, sqw, stw (sine, square, sawtooth). Default: silence.
Default freq: 440 Hz.

Examples:
  gen 10            → 10 seconds silence
  gen 5 sin         → 5 seconds 440Hz sine
  gen 5 sin 880     → 5 seconds 880Hz sine
  gen 3 sqw 200     → 3 seconds 200Hz square
```

#### `cap` - Capture
```
cap

Capture audio from input device. Any key stops.
Saves to sources/, adds to current track.
```

### Misc

#### `q` - Quit Session
```
q

Quit current session. Prompts if unsaved.
```

#### `qt` - Quit All
```
qt

Quit all sessions and exit.
```

#### `l` - Label
```
l [text]

Show or set session label.
```

#### `h` - Help
```
h [command]

Show help. Without argument: overview. With argument: command help.

Examples:
  h         → overview
  h p       → help for play command
  h rm      → help for ripple move
```

#### `!` - Shell
```
![command]

Run shell command, or open interactive shell.

Examples:
  !ls           → run ls
  !             → open shell (exit to return)
```

---

## Error Handling

### Error Messages

| Error | Message |
|-------|---------|
| Unknown command | `? unknown command: {cmd}` |
| Parse error | `? syntax error: {details}` |
| File not found | `? file not found: {path}` |
| Invalid range | `? invalid range: {start} > {end}` |
| Invalid address | `? invalid address: {addr}` |
| Mark not set | `? mark not set: {letter}` |
| Track empty | `? track {n} is not empty` |
| No clips | `? no audio in session` |
| Unsaved changes | `? unsaved changes (use q! to force)` |

### Exceptions

```python
# src/edway2/errors.py

class EdwayError(Exception):
    """Base exception."""
    pass

class ParseError(EdwayError):
    """Command parsing failed."""
    pass

class RangeError(EdwayError):
    """Invalid block range."""
    pass

class FileError(EdwayError):
    """File operation failed."""
    pass

class AudioError(EdwayError):
    """Audio operation failed."""
    pass
```

---

## Configuration

File: `~/.config/edway2/config.toml`

```toml
[playback]
device = "default"      # sounddevice device name
buffer_size = 1024      # samples per buffer

[recording]
device = "default"
sample_rate = 44100
channels = 2

[blocks]
default_duration_ms = 1000

[export]
default_format = "wav"
default_sample_rate = 44100
default_channels = 2

[ui]
prompt = ": "

[plugins]
search_paths = [
    "~/.vst3",
    "/usr/lib/vst3",
]
```

```python
# src/edway2/config.py
from dataclasses import dataclass
from pathlib import Path
import tomllib

@dataclass
class Config:
    playback_device: str = "default"
    playback_buffer_size: int = 1024
    recording_device: str = "default"
    recording_sample_rate: int = 44100
    recording_channels: int = 2
    block_duration_ms: int = 1000
    export_format: str = "wav"
    export_sample_rate: int = 44100
    export_channels: int = 2
    prompt: str = ": "
    plugin_paths: list[str] = None

    @classmethod
    def load(cls) -> "Config":
        path = Path.home() / ".config" / "edway2" / "config.toml"
        if not path.exists():
            return cls()
        with open(path, "rb") as f:
            data = tomllib.load(f)
        # ... parse into Config
        return cls(...)
```

---

## Startup

```python
# src/edway2/cli.py
import argparse
from pathlib import Path

def main():
    parser = argparse.ArgumentParser(prog="edway2")
    parser.add_argument("--version", action="store_true")
    parser.add_argument("path", nargs="?", help="Project folder or audio file")
    parser.add_argument("-p", "--play", action="store_true", help="Play and exit")
    parser.add_argument("-t", "--timing", action="store_true", help="Show info and exit")
    parser.add_argument("-c", "--convert", metavar="FMT", help="Convert and exit")

    args = parser.parse_args()

    if args.version:
        print(f"edway2 {__version__}")
        return 0

    if args.play:
        return play_file(args.path)

    if args.timing:
        return show_info(args.path)

    if args.convert:
        return convert_file(args.path, args.convert)

    # Interactive mode
    return run_repl(args.path)
```

---

## Implementation Phases

Each phase: write tests first, implement, verify manually.

### Phase 0: Skeleton
**Files to create**:
- `pyproject.toml`
- `src/edway2/__init__.py` (version = "0.1.0")
- `src/edway2/__main__.py`
- `src/edway2/cli.py`
- `tests/test_cli.py`

**Tests**:
```python
def test_version(capsys):
    from edway2.cli import main
    import sys
    sys.argv = ["edway2", "--version"]
    main()
    assert "0.1.0" in capsys.readouterr().out
```

**Done when**: `pip install -e .` then `edway2 --version` prints version.

---

### Phase 1: REPL Shell
**Files to create/modify**:
- `src/edway2/repl.py`
- `src/edway2/cli.py` (call repl)
- `tests/test_repl.py`

**Tests**:
```python
def test_quit_exits(mock_input):
    mock_input(["q"])
    from edway2.repl import run_repl
    result = run_repl(None)
    assert result == 0

def test_unknown_command_returns_error(mock_input, capsys):
    mock_input(["xyz", "q"])
    run_repl(None)
    assert "? unknown command" in capsys.readouterr().out
```

**Done when**: Run `edway2`, see prompt, type `q`, exits cleanly.

---

### Phase 2: Project & Session
**Files to create**:
- `src/edway2/project.py`
- `src/edway2/session.py`
- `src/edway2/commands/__init__.py`
- `src/edway2/commands/files.py` (save, load)
- `tests/test_project.py`
- `tests/test_session.py`

**Tests**:
```python
def test_create_project(tmp_path):
    from edway2.project import Project
    proj = Project.create(tmp_path / "myproject")
    assert (proj.path / "myproject.edway").exists()
    assert (proj.path / "sources").is_dir()
    assert (proj.path / "renders").is_dir()
    assert (proj.path / ".git").is_dir()

def test_save_and_load(tmp_path):
    proj = Project.create(tmp_path / "test")
    proj.session.marks["a"] = 5.0
    proj.save()

    proj2 = Project.open(tmp_path / "test")
    assert proj2.session.marks["a"] == 5.0
```

**Done when**: `edway2 ./newproject` creates folder structure.

---

### Phase 3: Command Parser
**Files to create**:
- `src/edway2/parser.py`
- `src/edway2/errors.py`
- `tests/test_parser.py`

**Tests**:
```python
@pytest.mark.parametrize("line,expected", [
    ("p", Command("p")),
    ("5p", Command("p", addr1=Address("number", 5))),
    ("1,10p", Command("p", addr1=Address("number", 1), addr2=Address("number", 10))),
    ("5m10", Command("m", addr1=Address("number", 5), dest=Address("number", 10))),
    ("r test.wav", Command("r", arg="test.wav")),
    ("db -3", Command("db", arg="-3")),
    ("'a,$p", Command("p", addr1=Address("mark", "a"), addr2=Address("dollar", None))),
])
def test_parse(line, expected):
    from edway2.parser import parse
    assert parse(line) == expected

def test_parse_error():
    with pytest.raises(ParseError):
        parse("1,2,3p")  # too many addresses
```

**Done when**: All parse examples from grammar table pass.

---

### Phase 4: Read Audio File
**Files to create/modify**:
- `src/edway2/commands/files.py` (r command)
- `src/edway2/audio.py` (read functions)
- `tests/test_commands_files.py`
- `tests/conftest.py` (sample_wav fixture)

**Tests**:
```python
@pytest.fixture
def sample_wav(tmp_path):
    import numpy as np
    import soundfile as sf
    path = tmp_path / "test.wav"
    data = np.zeros((44100, 2))  # 1 second stereo silence
    sf.write(path, data, 44100)
    return path

def test_read_creates_clip(tmp_project, sample_wav):
    tmp_project.execute(f"r {sample_wav}")
    assert len(tmp_project.session.timeline.tracks[0]) == 1

def test_read_nonexistent_errors(tmp_project, capsys):
    tmp_project.execute("r /nonexistent.wav")
    assert "? file not found" in capsys.readouterr().out
```

**Done when**: `r test.wav` then `?` shows duration.

---

### Phase 5: Block Addressing
**Files to create/modify**:
- `src/edway2/blocks.py`
- `src/edway2/commands/info.py` (=, ms, nb)
- `tests/test_blocks.py`
- `tests/test_commands_info.py`

**Tests**:
```python
def test_block_to_time():
    bv = BlockView(duration_seconds=10.0, block_duration_ms=1000)
    assert bv.to_time(1) == 0.0
    assert bv.to_time(2) == 1.0
    assert bv.to_time(10) == 9.0

def test_time_to_block():
    bv = BlockView(duration_seconds=10.0, block_duration_ms=1000)
    assert bv.from_time(0.0) == 1
    assert bv.from_time(0.5) == 1
    assert bv.from_time(1.0) == 2

def test_block_count():
    bv = BlockView(duration_seconds=10.0, block_duration_ms=1000)
    assert bv.count == 10

def test_ms_changes_block_count(tmp_project, sample_wav):
    tmp_project.execute(f"r {sample_wav}")  # 1 second
    tmp_project.execute("ms 500")
    assert tmp_project.blocks.count == 2
```

**Done when**: `ms 500` then `$=` shows doubled block count.

---

### Phase 6: Playback
**Files to create/modify**:
- `src/edway2/audio.py` (playback functions)
- `src/edway2/commands/playback.py`
- `tests/test_commands_playback.py`

**Tests**:
```python
def test_play_calls_sounddevice(tmp_project, sample_wav, mocker):
    mock_play = mocker.patch("sounddevice.play")
    tmp_project.execute(f"r {sample_wav}")
    tmp_project.execute("p")
    mock_play.assert_called_once()

def test_play_range(tmp_project, sample_wav, mocker):
    mock_play = mocker.patch("sounddevice.play")
    tmp_project.execute(f"r {sample_wav}")
    tmp_project.execute("1,1p")  # just block 1
    # verify correct slice passed to play
```

**Done when**: `p` plays audio audibly.

---

### Phase 7: Git Undo
**Files to create**:
- `src/edway2/git_undo.py`
- `src/edway2/commands/undo.py`
- `tests/test_git_undo.py`

**Tests**:
```python
def test_edit_creates_commit(tmp_project, sample_wav):
    tmp_project.execute(f"r {sample_wav}")
    commits_before = len(list(tmp_project.repo.iter_commits()))
    tmp_project.execute("1d")
    commits_after = len(list(tmp_project.repo.iter_commits()))
    assert commits_after == commits_before + 1

def test_undo_restores(tmp_project, sample_wav):
    tmp_project.execute(f"r {sample_wav}")
    tmp_project.execute("1d")
    assert tmp_project.session.duration == 0
    tmp_project.execute("u")
    assert tmp_project.session.duration > 0
```

**Done when**: Edit, `uh` shows commit, `u` restores.

---

### Phase 8: Basic Editing (Non-Ripple)
**Files to create**:
- `src/edway2/commands/editing.py`
- `tests/test_commands_editing.py`

**Tests**:
```python
def test_delete_leaves_gap(tmp_project, sample_wav):
    tmp_project.execute(f"r {sample_wav}")
    tmp_project.execute("1d")
    # Duration unchanged (gap remains)
    assert tmp_project.session.duration == 1.0

def test_move_creates_gap_at_source(tmp_project, two_clips):
    tmp_project.execute("1m$")
    # Block 1 is now gap, content at end
    ...

def test_copy_layers(tmp_project, sample_wav):
    tmp_project.execute(f"r {sample_wav}")
    tmp_project.execute("1t1")  # copy block 1 onto itself
    # Should have overlapping clips
    ...
```

**Done when**: `d` leaves silence, `m` moves with gap at source.

---

### Phase 9: Ripple Editing
**Files to modify**:
- `src/edway2/commands/editing.py`
- `tests/test_commands_editing.py`

**Tests**:
```python
def test_ripple_delete_closes_gap(tmp_project, sample_wav):
    tmp_project.execute(f"r {sample_wav}")  # 1 sec
    tmp_project.execute(f"r {sample_wav}")  # now 2 sec
    tmp_project.execute("1rd")
    assert tmp_project.session.duration == 1.0  # gap closed

def test_ripple_move_shifts(tmp_project, two_clips):
    original_duration = tmp_project.session.duration
    tmp_project.execute("1rm$")
    assert tmp_project.session.duration == original_duration  # no gap
```

**Done when**: `rd` shrinks timeline, `rm` shifts without gaps.

---

### Phase 10: Marks
**Files to create/modify**:
- `src/edway2/commands/marks.py`
- `tests/test_commands_marks.py`

**Tests**:
```python
def test_set_mark(tmp_project, sample_wav):
    tmp_project.execute(f"r {sample_wav}")
    tmp_project.execute("ka")
    assert "a" in tmp_project.session.marks

def test_mark_in_address(tmp_project, sample_wav):
    tmp_project.execute(f"r {sample_wav}")
    tmp_project.execute("ka")
    tmp_project.execute("'a=")
    # Should show block number

def test_mark_survives_block_resize(tmp_project, sample_wav):
    tmp_project.execute(f"r {sample_wav}")
    tmp_project.execute("ka")  # mark at block 1 = 0.0s
    tmp_project.execute("ms 500")
    # Mark still at 0.0s, but now block 1 (not block 2)
```

**Done when**: Set mark, resize blocks, mark still correct.

---

### Phase 11: Multitrack
**Files to create**:
- `src/edway2/commands/tracks.py`
- `tests/test_commands_tracks.py`

**Tests**:
```python
def test_addtrack(tmp_project):
    tmp_project.execute("addtrack vocals")
    assert len(tmp_project.session.timeline.tracks) == 2

def test_tr_switches(tmp_project):
    tmp_project.execute("addtrack")
    tmp_project.execute("tr 2")
    assert tmp_project.session.current_track == 1  # 0-indexed

def test_read_adds_to_current_track(tmp_project, sample_wav):
    tmp_project.execute("addtrack")
    tmp_project.execute("tr 2")
    tmp_project.execute(f"r {sample_wav}")
    assert len(tmp_project.session.timeline.tracks[1]) == 1
    assert len(tmp_project.session.timeline.tracks[0]) == 0
```

**Done when**: Multiple tracks, read goes to current track.

---

### Phase 12: Mute/Solo
**Tests**:
```python
def test_mute_excludes_from_mix(tmp_project, two_tracks_with_audio, mocker):
    mock_play = mocker.patch("sounddevice.play")
    tmp_project.execute("mute 1")
    tmp_project.execute("p")
    # Verify only track 2 audio in play call

def test_solo(tmp_project, two_tracks_with_audio, mocker):
    tmp_project.execute("solo 2")
    tmp_project.execute("p")
    # Only track 2 plays
```

**Done when**: Muted tracks silent, solo isolates.

---

### Phase 13: Export
**Tests**:
```python
def test_write_creates_file(tmp_project, sample_wav):
    tmp_project.execute(f"r {sample_wav}")
    tmp_project.execute("w out.wav")
    assert (tmp_project.renders_dir / "out.wav").exists()

def test_write_mp3(tmp_project, sample_wav):
    tmp_project.execute(f"r {sample_wav}")
    tmp_project.execute("w out.mp3")
    assert (tmp_project.renders_dir / "out.mp3").exists()
```

**Done when**: `w out.mp3` creates playable MP3.

---

### Phase 14: Gain Effect
**Tests**:
```python
def test_db_shows_loudness(tmp_project, sample_wav, capsys):
    tmp_project.execute(f"r {sample_wav}")
    tmp_project.execute("db")
    output = capsys.readouterr().out
    assert "dB" in output

def test_db_applies_gain(tmp_project, sample_wav):
    tmp_project.execute(f"r {sample_wav}")
    tmp_project.execute("db -6")
    # Check effect in metadata
    clip = tmp_project.session.timeline.tracks[0][0]
    assert clip.metadata.get("edway2", {}).get("gain") == -6
```

**Done when**: Gain affects playback volume.

---

### Phase 15: Fade In/Out
**Tests**:
```python
def test_fade_in(tmp_project, sample_wav):
    tmp_project.execute(f"r {sample_wav}")
    tmp_project.execute("fi 0.5")
    clip = tmp_project.session.timeline.tracks[0][0]
    assert clip.metadata.get("edway2", {}).get("fade_in") == 0.5
```

**Done when**: Fades audible on playback.

---

### Phase 16: Crossfade
**Tests**:
```python
def test_crossfade_creates_transition(tmp_project, two_adjacent_clips):
    tmp_project.execute("xf 0.5")
    track = tmp_project.session.timeline.tracks[0]
    # Check for OTIO Transition between clips
```

---

### Phase 17: Named Regions
**Tests**:
```python
def test_region_stores_range(tmp_project, sample_wav):
    tmp_project.execute(f"r {sample_wav}")
    tmp_project.execute("region intro 1,5")
    assert "intro" in tmp_project.session.regions
```

---

### Phase 18: Generate & Capture
**Tests**:
```python
def test_gen_creates_file(tmp_project):
    tmp_project.execute("gen 1 sin 440")
    files = list(tmp_project.sources_dir.glob("*.wav"))
    assert len(files) == 1

def test_gen_adds_to_track(tmp_project):
    tmp_project.execute("gen 1 sin 440")
    assert len(tmp_project.session.timeline.tracks[0]) == 1
```

---

### Phase 19: Git Branches
**Tests**:
```python
def test_branch_creates(tmp_project, sample_wav):
    tmp_project.execute(f"r {sample_wav}")
    tmp_project.execute("branch experiment")
    assert "experiment" in [b.name for b in tmp_project.repo.branches]

def test_checkout_switches(tmp_project, sample_wav):
    tmp_project.execute(f"r {sample_wav}")
    tmp_project.execute("branch exp")
    tmp_project.execute("1d")
    tmp_project.execute("checkout main")
    assert tmp_project.session.duration == 1.0  # restored
```

---

### Phase 20: NLE Export
**Tests**:
```python
def test_export_edl(tmp_project, sample_wav):
    tmp_project.execute(f"r {sample_wav}")
    tmp_project.execute("export edl")
    assert (tmp_project.renders_dir / "project.edl").exists()
```

---

### Phase 21: Plugins
**Tests**:
```python
def test_fx_loads_builtin(tmp_project, sample_wav):
    tmp_project.execute(f"r {sample_wav}")
    tmp_project.execute("fx reverb")
    tmp_project.execute("fxlist")
    # Should show reverb
```

---

### Phase 22: Polish
- Help system (`h`, `h cmd`)
- Improved error messages
- Time addressing (`@M:SS`)
- `split` command
- `q!` force quit
- Config file loading
- Edge cases

---

## Test Fixtures

```python
# tests/conftest.py
import pytest
from pathlib import Path
import numpy as np
import soundfile as sf

@pytest.fixture
def tmp_project(tmp_path):
    from edway2.project import Project
    return Project.create(tmp_path / "test_project")

@pytest.fixture
def sample_wav(tmp_path):
    path = tmp_path / "test.wav"
    data = np.sin(2 * np.pi * 440 * np.linspace(0, 1, 44100))
    data = np.column_stack([data, data])  # stereo
    sf.write(path, data, 44100)
    return path

@pytest.fixture
def two_clips(tmp_project, sample_wav):
    tmp_project.execute(f"r {sample_wav}")
    tmp_project.execute(f"r {sample_wav}")
    return tmp_project

@pytest.fixture
def mock_input(mocker):
    def _mock(lines):
        mocker.patch("prompt_toolkit.PromptSession.prompt", side_effect=lines + [EOFError])
    return _mock
```
