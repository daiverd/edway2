"""Track commands: tr, ts, tracks, addtrack, rmtrack, mute, solo."""

import re

from edway2.commands import command
from edway2.parser import Command

if True:  # TYPE_CHECKING workaround
    from edway2.project import Project


def parse_track_selection(arg: str, track_count: int) -> list[int]:
    """Parse track selection syntax.

    Accepts:
        1       - single track
        1,3     - multiple tracks
        1-4     - range of tracks
        *       - all tracks

    Args:
        arg: Selection string.
        track_count: Total number of tracks.

    Returns:
        List of 0-indexed track indices.

    Raises:
        ValueError: If syntax is invalid or tracks out of range.
    """
    if not arg or arg.strip() == "":
        return []

    arg = arg.strip()

    # All tracks
    if arg == "*":
        return list(range(track_count))

    result = set()

    # Split by comma
    parts = arg.split(",")
    for part in parts:
        part = part.strip()
        if not part:
            continue

        # Check for range (e.g., "1-4")
        if "-" in part:
            match = re.match(r"^(\d+)-(\d+)$", part)
            if not match:
                raise ValueError(f"invalid range: {part}")
            start = int(match.group(1))
            end = int(match.group(2))
            if start < 1 or end < 1:
                raise ValueError("track numbers must be >= 1")
            if start > track_count or end > track_count:
                raise ValueError(f"track out of range (have {track_count} tracks)")
            if start > end:
                start, end = end, start
            for i in range(start, end + 1):
                result.add(i - 1)  # convert to 0-indexed
        else:
            # Single track number
            try:
                track_num = int(part)
            except ValueError:
                raise ValueError(f"invalid track number: {part}")
            if track_num < 1:
                raise ValueError("track numbers must be >= 1")
            if track_num > track_count:
                raise ValueError(f"track {track_num} out of range (have {track_count} tracks)")
            result.add(track_num - 1)  # convert to 0-indexed

    return sorted(result)


@command("tr")
def cmd_track(project: "Project", cmd: Command) -> None:
    """Switch to track or show current track.

    Usage:
        tr        - show current track
        tr 2      - switch to track 2
    """
    if cmd.arg:
        try:
            track_num = int(cmd.arg)
        except ValueError:
            print(f"? invalid track number: {cmd.arg}")
            return

        if track_num < 1:
            print("? track numbers start at 1")
            return

        if track_num > project.session.track_count:
            print(f"? track {track_num} does not exist (have {project.session.track_count} tracks)")
            return

        project.session.current_track = track_num - 1
        track = project.session.get_track(track_num - 1)
        print(f"track {track_num}: {track.name}")
    else:
        track_num = project.session.current_track + 1
        track = project.session.get_track(project.session.current_track)
        print(f"track {track_num}: {track.name}")


@command("track")
def cmd_track_long(project: "Project", cmd: Command) -> None:
    """Alias for tr command."""
    cmd_track(project, cmd)


@command("ts")
def cmd_track_select(project: "Project", cmd: Command) -> None:
    """Select tracks for multi-track operations.

    Usage:
        ts        - clear selection (use current track only)
        ts 1      - select track 1 only
        ts 1,3    - select tracks 1 and 3
        ts 1-4    - select tracks 1 through 4
        ts *      - select all tracks

    Selected tracks are used by editing commands (d, m, t, rd, rm, rt).
    """
    if not cmd.arg:
        # Clear selection
        for track in project.session.tracks:
            track.selected = False
        print("selection cleared (using current track)")
        return

    try:
        indices = parse_track_selection(cmd.arg, project.session.track_count)
    except ValueError as e:
        print(f"? {e}")
        return

    if not indices:
        # Clear selection
        for track in project.session.tracks:
            track.selected = False
        print("selection cleared (using current track)")
        return

    # Clear all, then select specified
    for track in project.session.tracks:
        track.selected = False

    for idx in indices:
        project.session.tracks[idx].selected = True

    if len(indices) == 1:
        print(f"selected track {indices[0] + 1}")
    else:
        track_nums = [str(i + 1) for i in indices]
        print(f"selected tracks {', '.join(track_nums)}")


@command("tracks")
def cmd_tracks_list(project: "Project", cmd: Command) -> None:
    """List all tracks with status.

    Shows track number, name, and status indicators:
        * = current track
        S = selected
        M = muted
        O = soloed (sOlo)
        R = record armed
    """
    for i, track in enumerate(project.session.tracks):
        track_num = i + 1
        flags = []

        if i == project.session.current_track:
            flags.append("*")
        if track.selected:
            flags.append("S")
        if track.muted:
            flags.append("M")
        if track.soloed:
            flags.append("O")
        if track.record:
            flags.append("R")

        flag_str = "".join(flags) if flags else "-"
        clip_count = len(track.clips)
        duration = track.duration

        print(f"{track_num:2}. [{flag_str:4}] {track.name:<20} ({clip_count} clips, {duration:.1f}s)")


@command("addtrack")
def cmd_addtrack(project: "Project", cmd: Command) -> None:
    """Add a new track.

    Usage:
        addtrack          - add track with default name
        addtrack Vocals   - add track named "Vocals"
    """
    project.prepare_edit()

    name = cmd.arg if cmd.arg else None
    index = project.session.add_track(name)

    track = project.session.get_track(index)
    project.mark_dirty(f"addtrack {track.name}")

    print(f"added track {index + 1}: {track.name}")


@command("rmtrack")
def cmd_rmtrack(project: "Project", cmd: Command) -> None:
    """Remove a track.

    Usage:
        rmtrack       - remove current track (must be empty)
        rmtrack 2     - remove track 2 (must be empty)

    Track must be empty (no clips) before removal.
    Cannot remove the last track.
    """
    if project.session.track_count <= 1:
        print("? cannot remove last track")
        return

    if cmd.arg:
        try:
            track_num = int(cmd.arg)
        except ValueError:
            print(f"? invalid track number: {cmd.arg}")
            return

        if track_num < 1 or track_num > project.session.track_count:
            print(f"? track {track_num} does not exist")
            return

        track_idx = track_num - 1
    else:
        track_idx = project.session.current_track

    track = project.session.get_track(track_idx)

    if len(track.clips) > 0:
        print(f"? track {track_idx + 1} is not empty ({len(track.clips)} clips)")
        return

    project.prepare_edit()

    track_name = track.name
    project.session.remove_track(track_idx)

    # Adjust current track if needed
    if project.session.current_track >= project.session.track_count:
        project.session.current_track = project.session.track_count - 1

    project.mark_dirty(f"rmtrack {track_name}")

    print(f"removed track: {track_name}")


@command("mute")
def cmd_mute(project: "Project", cmd: Command) -> None:
    """Toggle mute on track(s).

    Usage:
        mute          - toggle mute on current track
        mute 2        - toggle mute on track 2
        mute 1,3      - toggle mute on tracks 1 and 3
        mute *        - toggle mute on all tracks

    Muted tracks are excluded from playback.
    """
    if cmd.arg:
        try:
            indices = parse_track_selection(cmd.arg, project.session.track_count)
        except ValueError as e:
            print(f"? {e}")
            return
    else:
        indices = [project.session.current_track]

    if not indices:
        indices = [project.session.current_track]

    for idx in indices:
        track = project.session.tracks[idx]
        track.muted = not track.muted
        status = "muted" if track.muted else "unmuted"
        print(f"track {idx + 1}: {status}")


@command("solo")
def cmd_solo(project: "Project", cmd: Command) -> None:
    """Toggle solo on track(s).

    Usage:
        solo          - toggle solo on current track
        solo 2        - toggle solo on track 2
        solo 1,3      - toggle solo on tracks 1 and 3

    When any track is soloed, only soloed tracks play.
    """
    if cmd.arg:
        try:
            indices = parse_track_selection(cmd.arg, project.session.track_count)
        except ValueError as e:
            print(f"? {e}")
            return
    else:
        indices = [project.session.current_track]

    if not indices:
        indices = [project.session.current_track]

    for idx in indices:
        track = project.session.tracks[idx]
        track.soloed = not track.soloed
        status = "soloed" if track.soloed else "unsoloed"
        print(f"track {idx + 1}: {status}")
