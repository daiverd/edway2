# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

edway2 is a non-destructive multitrack audio editor with a line-editor (ed/vim style) command interface. It's a Python rewrite of the original C-based edway, using modern libraries.

## Development Approach

**TDD**: Write tests first, then implement. Each phase must pass automated tests AND manual verification before proceeding.

**Spec-driven**: All behavior is defined in `SPEC.md`. Consult it for command syntax, interfaces, and test cases.

## Commands

```bash
# Install in development mode
pip install -e ".[dev]"

# Run tests
pytest

# Run single test
pytest tests/test_parser.py::test_parse_simple -v

# Run the application
edway2
edway2 --version
```

## Project Structure

```
edway2/
├── SPEC.md              # Full specification (READ THIS FIRST)
├── CLAUDE.md            # This file
├── pyproject.toml       # Dependencies and project config
├── src/edway2/          # Source code
│   ├── __init__.py      # Version
│   ├── __main__.py      # Entry point
│   ├── cli.py           # CLI argument parsing
│   ├── repl.py          # REPL loop
│   ├── parser.py        # Command parser
│   ├── commands/        # Command implementations
│   ├── session.py       # OTIO timeline wrapper
│   ├── project.py       # Project folder management
│   ├── blocks.py        # Block addressing
│   ├── audio.py         # Playback/recording
│   └── ...
├── tests/               # pytest tests
└── reference/           # Original edway 0.2 C code (for behavior reference)
```

## Key Dependencies

- **pedalboard**: Audio engine, VST3/AU plugins, effects
- **soundfile**: Audio file I/O (WAV, FLAC)
- **sounddevice**: Live playback/recording
- **opentimelineio**: Timeline model
- **prompt_toolkit**: TUI/REPL
- **gitpython**: Undo via git

## Implementation Phases

See SPEC.md for detailed phases. Currently working on: **Phase 0 (Skeleton)**.

Each phase has:
- Specific files to create
- Test code to write first
- "Done when" acceptance criterion

## Reference Code

Original edway 0.2 C source is in `reference/` for behavioral reference. Key files:
- `reference/session.c` - Edit mode, block operations
- `reference/support.c` - Utility functions, command parsing
- `reference/doc/HELP/` - Original command help text

## Design Decisions

See SPEC.md "Command Reference" section. Key points:
- **Ripple OFF by default**: Delete leaves gap, move/copy layers
- **Ripple commands**: `rd`, `rm`, `rt` for ripple behavior
- **Insert BEFORE**: `5m10` inserts before block 10, `5m$` appends
- **Multitrack**: Edit affects current track, playback mixes all
- **Git undo**: Every edit commits, unlimited undo via git
