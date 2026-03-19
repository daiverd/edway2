# edway2

Non-destructive multitrack audio editor with line-editor UX.

A Python rewrite of the original C-based [edway](http://edway.ftml.net/) audio editor, using modern libraries and a non-destructive editing model.

## Features

- **Line-editor UX**: ed/vim style commands (`p` play, `d` delete, `m` move, etc.)
- **Non-destructive**: Source files never modified; edits stored as timeline operations
- **Multitrack**: Multiple tracks per session, mixed on playback
- **Unlimited undo**: Git-based history with branches and tags
- **Plugin support**: VST3 and AU plugins via pedalboard
- **Interoperable**: Export to EDL, AAF, FCP XML via OpenTimelineIO

## Installation

```bash
pip install edway2
```

Or for development:

```bash
git clone <repo>
cd edway2
pip install -e ".[dev]"
```

## Usage

```bash
edway2                    # Interactive editor
edway2 myproject/         # Open existing project
edway2 audio.wav          # Import file into new session
edway2 --version          # Show version
```

## Quick Start

```
: r myfile.wav            # Read audio file
: ?                       # Show session info
: p                       # Play all
: 1,10p                   # Play blocks 1-10
: 5d                      # Delete block 5 (leaves gap)
: u                       # Undo
: w output.mp3            # Export to MP3
: q                       # Quit
```

## Documentation

See [SPEC.md](SPEC.md) for full specification.

## License

GPL-3.0 - see [LICENSE](LICENSE) for details.

Based on edway 0.2 by Chuck Hallenbeck.
