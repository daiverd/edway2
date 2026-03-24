# edway2

Non-destructive multitrack audio editor for the terminal.

edway2 is a line-oriented audio editor inspired by ed, the Unix text editor. Instead of operating on lines of text, it operates on "blocks" of audio. All edits are non-destructive and fully undoable via git-based versioning.

Based on [edway 0.2](http://edway.ftml.net/) by Chuck Hallenbeck.

## Installation

```bash
pip install edway2
# or with uv
uv pip install edway2
```

### Requirements

- Python 3.10+
- PortAudio (for playback)

On Ubuntu/Debian:
```bash
sudo apt install portaudio19-dev
```

On macOS:
```bash
brew install portaudio
```

## Quick Start

```bash
# Create a new project
edway2 init myproject
cd myproject

# Or work with an existing project
edway2 myproject

# Load audio
r song.wav

# Play the first 10 blocks
1,10p

# Delete blocks 5-7
5,7d

# Save your work
save rough-mix

# Export final audio
w final.wav
```

## Concepts

### Blocks

Audio is divided into **blocks** of equal duration (default: 1 second). Blocks are the atomic unit of editing - you address, play, delete, move, and copy entire blocks at a time.

Change block duration with `ms`:
```
ms 500      # Set to 500ms blocks
ms 0.25     # Set to 250ms blocks
nb 100      # Adjust duration to get ~100 blocks
```

### Non-Destructive Editing

All edits create new timeline states rather than modifying source files:
- Original audio files are preserved in `sources/`
- The timeline is stored in `session.json`
- Every edit is versioned via git
- Full undo/redo to any point in history

### Addresses

Commands use ed-style addressing:

| Address | Meaning |
|---------|---------|
| `5` | Block 5 |
| `.` | Current position |
| `$` | Last block |
| `'a` | Mark named 'a |
| `@1:30` | Time position (1 min 30 sec) |
| `$-3` | 3 blocks before end |
| `.+5` | 5 blocks after current |

Ranges use comma: `1,10` means blocks 1 through 10.

### Tracks

edway2 supports multiple tracks that are mixed during playback and export:

```
addtrack Vocals     # Add a new track
tr 2                # Switch to track 2
r vocals.wav        # Load audio into track 2
tracks              # List all tracks
mute 1              # Mute track 1
solo 2              # Solo track 2
```

## Command Reference

### File Commands

#### r - Read audio file
```
r <file>      Append file to current track
5r <file>     Insert at block 5
```

Copies the file to `sources/` and creates a clip on the timeline. Supports wav, flac, ogg, mp3, and any format that soundfile supports.

#### w - Export audio
```
w [file]      Export entire timeline
w             Export to <session-name>.wav
```

Renders all tracks (respecting mute/solo) to a single audio file.

#### save - Save session
```
save              Commit changes
save <name>       Commit and create named tag
```

Tags create named checkpoints for later reference.

### Playback Commands

#### p - Play
```
p             Play current block
5p            Play block 5
1,10p         Play blocks 1-10
.,$p          Play from current to end
'a,'bp        Play from mark a to mark b
```

Press any key to stop playback.

#### z - Play seconds
```
z             Play 5 seconds from current position
z10           Play 10 seconds from current
5z10          Play 10 seconds from block 5
```

### Editing Commands

edway2 has two editing modes:

**Non-ripple** (`d`, `m`, `t`): Leaves gaps where content was removed. Timeline duration stays the same.

**Ripple** (`rd`, `rm`, `rt`): Closes gaps by shifting content. Timeline duration changes.

#### d - Delete (non-ripple)
```
d             Delete current block
5d            Delete block 5
1,5d          Delete blocks 1-5
```

Leaves a gap (silence) where content was.

#### rd - Ripple delete
```
rd            Ripple delete current block
5rd           Ripple delete block 5
1,5rd         Ripple delete blocks 1-5
```

Removes content and shifts following content left.

#### m - Move (non-ripple)
```
5m10          Move block 5 to position 10
1,5m20        Move blocks 1-5 to position 20
5m$           Move block 5 to end
```

Source becomes a gap. Content layers at destination.

#### rm - Ripple move
```
5rm10         Ripple move block 5 to position 10
1,5rm20       Ripple move blocks 1-5 to position 20
```

Closes gap at source, makes room at destination.

#### t - Copy (non-ripple)
```
5t10          Copy block 5 to position 10
1,5t$         Copy blocks 1-5 to end
```

Content layers at destination.

#### rt - Ripple copy
```
5rt10         Ripple copy block 5 to position 10
1,5rt$        Ripple copy blocks 1-5 to end
```

Makes room at destination before inserting copy.

### Info Commands

#### ? - Session info
```
?
```

Shows project name, session label, track count, duration, and block count.

#### = - Show block number
```
=             Show last block number ($)
.=            Show current block number
'a=           Show block number of mark a
$-3=          Show block 3 from end
```

#### ms - Block duration
```
ms            Show current block duration
ms 500        Set to 500ms
ms 1.0        Set to 1 second
ms 0:00.250   Set to 250ms
```

#### nb - Number of blocks
```
nb            Show block count
nb 100        Adjust duration to get ~100 blocks
```

### Undo/Redo Commands

#### u - Undo
```
u             Navigate to previous commit
```

If there are unsaved changes, shows error. Use `u!` to discard.

#### u! - Undo (discard changes)
```
u!            Discard uncommitted changes
```

#### U - Redo
```
U             Navigate forward in history
```

#### uh - History
```
uh
```

Shows numbered list of commits with tags and current position.

### Track Commands

#### tr - Switch track
```
tr            Show current track
tr 2          Switch to track 2
```

#### ts - Track selection
```
ts            Clear selection
ts 1          Select track 1
ts 1,3        Select tracks 1 and 3
ts 1-4        Select tracks 1 through 4
ts *          Select all tracks
```

#### tracks - List tracks
```
tracks
```

Shows all tracks with status indicators:
- `*` = current track
- `S` = selected
- `M` = muted
- `O` = soloed

#### addtrack - Add track
```
addtrack              Add with default name
addtrack Vocals       Add track named "Vocals"
```

#### rmtrack - Remove track
```
rmtrack               Remove current track
rmtrack 2             Remove track 2
```

Track must be empty (no clips).

#### mute - Toggle mute
```
mute                  Toggle on current track
mute 2                Toggle on track 2
mute 1,3              Toggle on tracks 1 and 3
mute *                Toggle on all tracks
```

#### solo - Toggle solo
```
solo                  Toggle on current track
solo 2                Toggle on track 2
```

When any track is soloed, only soloed tracks play.

### Mark Commands

#### k - Set/list marks
```
k             List all marks
ka            Set mark 'a at current position
5ka           Set mark 'a at block 5
```

Reference marks in addresses: `'a,'bp` plays from mark a to mark b.

#### region - Define/list regions
```
region                List all regions
region intro          Show region 'intro'
1,10 region intro     Define region 'intro' as blocks 1-10
```

### Misc Commands

#### ! - Shell command
```
!ls           List files
!ffmpeg ...   Run external command
```

#### l - Session label
```
l             Show current label
l My Song     Set label
```

#### h - Help
```
h             Show overview
h <cmd>       Show help for command
```

#### q - Quit
```
q             Quit (prompts if unsaved)
q!            Force quit
```

## Project Structure

```
myproject/
  session.json      # Timeline and session data
  sources/          # Original audio files (copied on import)
  .git/             # Version control for undo/redo
```

## Keyboard Shortcuts

During playback:
- Any key: Stop playback

In the REPL:
- Ctrl+C: Cancel current command
- Ctrl+D: Quit

## Examples

### Basic editing workflow
```
r track.wav           # Load audio
1,10p                 # Listen to first 10 blocks
5,7d                  # Delete blocks 5-7 (leaves gap)
save                  # Save changes
```

### Ripple editing (no gaps)
```
r track.wav           # Load audio
5,7rd                 # Ripple delete blocks 5-7
save cleaned          # Save with tag
```

### Multitrack mixing
```
r drums.wav           # Load drums to track 1
addtrack Vocals       # Create track 2
tr 2                  # Switch to track 2
r vocals.wav          # Load vocals
mute 1                # Mute drums while editing vocals
5,10rd                # Remove section from vocals
mute 1                # Unmute drums
1,$p                  # Play everything
w mix.wav             # Export final mix
```

### Using marks
```
r song.wav            # Load audio
1,20 region intro     # Define intro region
21,50 region verse    # Define verse region
ka                    # Set mark at current position
'a,$p                 # Play from mark to end
```

### Undo/redo
```
5d                    # Delete block 5
u                     # Undo - back to before delete
U                     # Redo - forward to after delete
uh                    # Show history
```

## License

GPL-3.0 - see [LICENSE](LICENSE) for details.
