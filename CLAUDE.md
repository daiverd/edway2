# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

edway2 is a non-destructive multitrack audio editor with a line-editor (ed/vim style) command interface. Python rewrite of the original C-based edway.

## Commands

```bash
uv run pytest                                    # Run all tests
uv run pytest tests/test_parser.py::test_name -v # Run single test
uv run edway2                                    # Run application
uv run edway2 /path/to/project                   # Open/create project
```

## Architecture

### Data Flow
```
User input → repl.py → parser.py → commands/*.py → project.py → session.py
                                                       ↓
                                                   git (undo)
```

### Key Abstractions

**Project** (`project.py`): Wraps a folder containing `<name>.edway`, `sources/`, `renders/`, and `.git/`. Manages git commits for undo. All commands receive a Project instance.

**Session** (`session.py`): Timeline data model - tracks, clips, marks, regions. Serializes to JSON. Clips reference source files, have positions (seconds), no explicit gap objects.

**BlockView** (`blocks.py`): Virtual view over timeline. Converts between 1-indexed block numbers and seconds based on `block_duration_ms`. Blocks include gaps (silence = no clip at position).

**Parser** (`parser.py`): ed-style grammar: `[range] cmd [dest] [arg]`. Addresses: number, `.` (current), `$` (last), `'x` (mark), `@M:SS` (time). Returns `Command` dataclass.

**Command Registry** (`commands/__init__.py`): `@command("name")` decorator registers handlers. Handler signature: `(project: Project, cmd: Command) -> None`.

### Position-Based Clips (vs sequential)
Clips have absolute `position` in track (seconds). Gaps are implicit - no clip at a position = silence. This simplifies editing: delete just removes clips, no gap management needed. OTIO is only used for export interchange.

### Undo via Git
Every edit auto-commits the `.edway` file. `u` navigates back, `U` forward. `_undo_offset` tracks position in history. `prepare_edit()` handles dirty state before modifications.

## Development

**TDD**: Write tests first. `SPEC.md` defines all behavior.

**Phase status**: Phases 0-13 complete (through Export). See `SPEC.md` for remaining phases (Effects, Regions, OTIO export, Plugins).

**Test files**: `tests/test_files/` contains audio for manual testing. Don't modify directly.

**Reference**: Original C code in `reference/` for behavioral reference.

## Design Decisions

- **Ripple OFF by default**: `d` leaves gap, `rd` ripples
- **Insert BEFORE**: `5m10` inserts before block 10, `5m$` appends
- **Track selection**: Commands affect current track unless `ts` selects others
- **Solo overrides mute**: If any track soloed, only soloed tracks play
