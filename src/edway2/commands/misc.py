"""Misc commands: h (help), ! (shell), l (label)."""

from edway2.commands import command
from edway2.parser import Command

if True:  # TYPE_CHECKING workaround
    from edway2.project import Project


OVERVIEW = """
edway2 - non-destructive multitrack audio editor

Commands (use 'h <cmd>' for details):

File:        r, w, save
Playback:    p, z
Editing:     d, m, t (leave gaps), rd, rm, rt (ripple/close gaps)
Info:        ?, =, ms, nb
Undo:        u, u!, U, uh
Tracks:      tr, ts, tracks, addtrack, rmtrack, mute, solo
Marks:       k, region, regions
Misc:        !, l, h, q

Addresses:   5 (block), . (current), $ (last), 'a (mark), @1:30 (time)
             +N/-N offsets work with any address: $-3, .+1

Examples:    5         Go to block 5
             1,10p     Play blocks 1-10
             5d        Delete block 5
             1,5m10    Move blocks 1-5 to position 10
             1,5rd     Ripple delete blocks 1-5
"""

COMMAND_HELP = {
    # File commands
    "r": """r - Read audio file

Usage:
    r <file>      Append file to current track
    5r <file>     Insert at block 5

The file is copied to sources/ and a clip is created on the timeline.
Supports any format that soundfile supports (wav, flac, ogg, mp3, etc.)
""",

    "w": """w - Export/write audio

Usage:
    w [file]      Export entire timeline to file
    w             Export to <session-name>.wav

Renders all tracks (respecting mute/solo) to a single audio file.
Output is saved in the project folder.
Supports wav, flac, ogg based on extension.
""",

    "save": """save - Save session

Usage:
    save              Commit changes
    save <name>       Commit and create named tag

Tags create checkpoints you can reference later (undo to, export from).
Duplicate tag names get auto-suffixed: mix, mix_2, mix_3.
""",

    # Playback commands
    "p": """p - Play audio

Usage:
    p             Play current block
    5p            Play block 5
    1,10p         Play blocks 1-10
    .,$p          Play from current position to end
    'a,'bp        Play from mark a to mark b

Press any key to stop playback.
""",

    "z": """z - Play seconds from position

Usage:
    z             Play 5 seconds from current position
    z10           Play 10 seconds from current position
    5z10          Play 10 seconds starting from block 5

Press any key to stop playback.
""",

    # Editing commands (non-ripple)
    "d": """d - Delete (non-ripple)

Usage:
    d             Delete current block
    5d            Delete block 5
    1,5d          Delete blocks 1-5

Non-ripple delete leaves a gap (silence) where content was.
Timeline duration stays the same. Use 'rd' to close gaps.
""",

    "m": """m - Move (non-ripple)

Usage:
    5m10          Move block 5 to position 10
    1,5m20        Move blocks 1-5 to position 20
    5m$           Move block 5 to end

Source becomes a gap. Content layers at destination.
Use 'rm' for ripple move (closes gap at source, makes room at dest).
""",

    "t": """t - Copy (non-ripple)

Usage:
    5t10          Copy block 5 to position 10
    1,5t$         Copy blocks 1-5 to end

Content layers at destination (overlaps with existing content).
Use 'rt' for ripple copy (makes room at destination).
""",

    # Editing commands (ripple)
    "rd": """rd - Ripple delete

Usage:
    rd            Ripple delete current block
    5rd           Ripple delete block 5
    1,5rd         Ripple delete blocks 1-5

Unlike 'd', this shifts all following content left to close the gap.
Timeline duration decreases by the deleted amount.
""",

    "rm": """rm - Ripple move

Usage:
    5rm10         Ripple move block 5 to position 10
    1,5rm20       Ripple move blocks 1-5 to position 20
    5rm$          Ripple move block 5 to end

Source gap is closed (content shifts left).
Destination content shifts right to make room.
""",

    "rt": """rt - Ripple copy

Usage:
    5rt10         Ripple copy block 5 to position 10
    1,5rt$        Ripple copy blocks 1-5 to end

Destination content shifts right to make room for the copy.
Timeline duration increases by the copied amount.
""",

    # Info commands
    "?": """? - Session info

Shows project name, session name, track count, duration, block count.
Also indicates if there are unsaved changes.
""",

    "=": """= - Show block number

Usage:
    =             Show last block number ($)
    .=            Show current block number
    5=            Show 5 (for calculating expressions)
    'a=           Show block number of mark a
    $-3=          Show block number 3 from end

Useful for checking mark positions or calculating addresses.
""",

    "ms": """ms - Block duration

Usage:
    ms            Show current block duration
    ms 500        Set to 500ms (integer = milliseconds)
    ms 1.0        Set to 1 second (float = seconds)
    ms 0:01       Set to 1 second (time notation)
    ms 0:00.250   Set to 250ms

Blocks are the atomic unit of editing. Default is 1000ms (1 second).
""",

    "nb": """nb - Number of blocks

Usage:
    nb            Show current block count
    nb 100        Adjust block duration to get ~100 blocks

This adjusts block duration automatically. Useful for setting up
a specific number of blocks for a piece of audio.
""",

    # Undo commands
    "u": """u - Undo

Usage:
    u             Navigate to previous commit

Navigates to the previous state in history. Does not discard changes.
If there are unsaved changes, shows error. Use 'u!' to discard.
""",

    "u!": """u! - Undo (force/discard)

Usage:
    u!            Discard uncommitted changes

Discards any changes since the last save and moves to previous state.
Use this to undo a mistake without polluting history.
""",

    "U": """U - Redo

Usage:
    U             Navigate forward in history

Only works after using 'u' to go back in history.
""",

    "uh": """uh - History

Shows the edit history with numbered commits.
Current position marked with *.
Tags shown in brackets.

Example:
    1. Project created
    2. r test.wav
  * 3. [rough-mix] 2,3d
    4. 5,6d
    (uncommitted changes)
""",

    # Track commands
    "tr": """tr - Switch track

Usage:
    tr            Show current track
    tr 2          Switch to track 2

Track numbers start at 1.
""",

    "track": """track - Switch track (alias for tr)

See 'h tr' for details.
""",

    "ts": """ts - Track selection

Usage:
    ts            Clear selection (use current track only)
    ts 1          Select track 1 only
    ts 1,3        Select tracks 1 and 3
    ts 1-4        Select tracks 1 through 4
    ts *          Select all tracks

Selected tracks are used by editing commands (d, m, t, etc.)
When nothing is selected, commands operate on the current track.
""",

    "tracks": """tracks - List all tracks

Shows all tracks with status indicators:
    * = current track
    S = selected
    M = muted
    O = soloed
    R = record armed

Example:
    1. [*   ] Track 1      (2 clips, 10.0s)
    2. [M   ] Vocals       (1 clips, 8.5s)
    3. [ S O] Drums        (3 clips, 10.0s)
""",

    "addtrack": """addtrack - Add new track

Usage:
    addtrack              Add track with default name (Track N)
    addtrack Vocals       Add track named "Vocals"

New track is added at the end. Use 'tr N' to switch to it.
""",

    "rmtrack": """rmtrack - Remove track

Usage:
    rmtrack               Remove current track
    rmtrack 2             Remove track 2

Track must be empty (no clips) before removal.
Cannot remove the last track.
""",

    "mute": """mute - Toggle mute

Usage:
    mute                  Toggle mute on current track
    mute 2                Toggle mute on track 2
    mute 1,3              Toggle mute on tracks 1 and 3
    mute *                Toggle mute on all tracks

Muted tracks are excluded from playback and export.
""",

    "solo": """solo - Toggle solo

Usage:
    solo                  Toggle solo on current track
    solo 2                Toggle solo on track 2
    solo 1,3              Toggle solo on tracks 1 and 3

When any track is soloed, only soloed tracks play.
Solo takes precedence over mute.
""",

    # Mark commands
    "k": """k - Set/list marks

Usage:
    k             List all marks
    ka            Set mark 'a at current position
    5ka           Set mark 'a at block 5

Marks are single lowercase letters (a-z).
Reference marks in addresses with 'a, 'b, etc.
Example: 'a,'bp plays from mark a to mark b.
""",

    "region": """region - Define/list regions

Usage:
    region                List all regions
    region intro          Show region 'intro'
    1,10 region intro     Define region 'intro' as blocks 1-10

Regions are named ranges. Useful for organizing sections of audio.
""",

    "regions": """regions - List all regions

Alias for 'region' with no arguments.
Shows all defined regions with their block ranges.
""",

    # Misc commands
    "!": """! - Shell command

Usage:
    !<cmd>        Run shell command
    !ls           List files
    !ffmpeg ...   Run ffmpeg

Runs command in shell and displays output.
""",

    "l": """l - Session label

Usage:
    l             Show current session label
    l My Song     Set session label to "My Song"

The label is used as the default export filename.
""",

    "h": """h - Help

Usage:
    h             Show overview
    h <cmd>       Show help for specific command

Examples:
    h p           Help for play command
    h rd          Help for ripple delete
""",

    "q": """q - Quit

Usage:
    q             Quit (prompts if unsaved changes)
    q!            Force quit (discard unsaved changes)

If there are unsaved changes, you'll be prompted to save first.
""",

    "q!": """q! - Force quit

Quit immediately, discarding any unsaved changes.
Use with caution.
""",
}

# Aliases
COMMAND_HELP["help"] = COMMAND_HELP["h"]


@command("h")
def cmd_help(project: "Project", cmd: Command) -> None:
    """Show help.

    Usage:
        h         - show overview
        h <cmd>   - show help for command
    """
    if cmd.arg:
        cmd_name = cmd.arg.strip().lower()
        if cmd_name in COMMAND_HELP:
            print(COMMAND_HELP[cmd_name].strip())
        else:
            print(f"? no help for '{cmd_name}'")
            print("Use 'h' to see all commands")
    else:
        print(OVERVIEW.strip())


@command("!")
def cmd_shell(project: "Project", cmd: Command) -> None:
    """Run shell command.

    Usage:
        !<cmd>    - run command
        !         - open interactive shell
    """
    import subprocess

    if cmd.arg:
        try:
            result = subprocess.run(
                cmd.arg,
                shell=True,
                capture_output=True,
                text=True,
            )
            if result.stdout:
                print(result.stdout, end="")
            if result.stderr:
                print(result.stderr, end="")
        except Exception as e:
            print(f"? shell error: {e}")
    else:
        print("? interactive shell not implemented")


@command("l")
def cmd_label(project: "Project", cmd: Command) -> None:
    """Show or set session label.

    Usage:
        l           - show current label
        l <text>    - set label
    """
    if cmd.arg:
        project.prepare_edit()
        project.session.name = cmd.arg
        project.mark_dirty(f"l {cmd.arg}")
        print(f"label: {cmd.arg}")
    else:
        print(f"label: {project.session.name}")
