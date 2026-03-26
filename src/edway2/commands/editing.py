"""Editing commands: d, m, t (non-ripple) and rd, rm, rt (ripple)."""

from dataclasses import replace

from edway2.commands import command
from edway2.parser import Command
from edway2.commands.playback import resolve_address
from edway2.session import Clip, Track

if True:  # TYPE_CHECKING workaround
    from edway2.project import Project


# =============================================================================
# Helper functions for ripple editing
# =============================================================================

def shift_clips_after(track: Track, time: float, delta: float) -> None:
    """Shift all clips that start at or after a time point.

    Args:
        track: Track to modify.
        time: Time point - clips starting at or after this are shifted.
        delta: Amount to shift (negative = left, positive = right).
    """
    for clip in track.clips:
        if clip.position >= time:
            clip.position += delta
            # Don't allow negative positions
            if clip.position < 0:
                clip.position = 0


def ripple_delete_range(track: Track, start: float, end: float) -> None:
    """Delete content in range and shift following clips left.

    Unlike delete_range(), this closes the gap by moving all clips
    after the deleted range to the left.

    Args:
        track: Track to modify.
        start: Start time of range to delete.
        end: End time of range to delete.
    """
    duration = end - start

    # First, delete the content (same as non-ripple)
    delete_range(track, start, end)

    # Then shift all clips after the deleted range left
    shift_clips_after(track, end, -duration)


def make_room_at(track: Track, time: float, duration: float) -> None:
    """Shift clips to make room for insertion at a time point.

    Args:
        track: Track to modify.
        time: Time point where room is needed.
        duration: Amount of room to make.
    """
    shift_clips_after(track, time, duration)


def _set_point_to_block(project: "Project", block: int) -> None:
    """Set current_position to the start of a block.

    Args:
        project: Project instance.
        block: Block number (1-indexed).
    """
    blocks = project.blocks
    block = blocks.clamp(block)
    project.session.current_position = blocks.to_time(block)


def _set_point_to_block_end(project: "Project", block: int) -> None:
    """Set current_position to the end of a block.

    Args:
        project: Project instance.
        block: Block number (1-indexed).
    """
    blocks = project.blocks
    block = blocks.clamp(block)
    project.session.current_position = blocks.to_time_end(block)


@command("")
def cmd_goto(project: "Project", cmd: Command) -> None:
    """Go to address (address-only command).

    Usage:
        7         - move point to block 7
        $         - move point to last block
        'a        - move point to mark a
        .+5       - move point 5 blocks forward
    """
    if cmd.addr1 is None:
        return

    block = resolve_address(project, cmd.addr1, 1)
    blocks = project.blocks

    # Validate block is in range
    if blocks.count == 0:
        print("? no blocks in timeline")
        return

    if block < 1:
        block = 1
    elif block > blocks.count:
        block = blocks.count

    _set_point_to_block(project, block)
    print(f"block {block}")


def extract_clips_in_range(track: Track, start: float, end: float) -> list[Clip]:
    """Extract clips that overlap a time range.

    Returns copies of clips (or portions) that fall within the range.
    The returned clips have positions relative to the start of the range.

    Args:
        track: Track to extract from.
        start: Start time of range.
        end: End time of range.

    Returns:
        List of clips with positions relative to range start.
    """
    extracted = []

    for clip in track.clips:
        clip_start = clip.position
        clip_end = clip.position + clip.duration

        # Skip clips outside range
        if clip_end <= start or clip_start >= end:
            continue

        # Calculate overlap
        overlap_start = max(start, clip_start)
        overlap_end = min(end, clip_end)

        # Calculate source range adjustment
        source_offset = overlap_start - clip_start

        # Create extracted clip with position relative to range start
        extracted_clip = Clip(
            source=clip.source,
            source_start=clip.source_start + source_offset,
            source_end=clip.source_start + source_offset + (overlap_end - overlap_start),
            position=overlap_start - start,  # relative to range start
            gain=clip.gain,
            fade_in=clip.fade_in if overlap_start == clip_start else 0.0,
            fade_out=clip.fade_out if overlap_end == clip_end else 0.0,
        )
        if extracted_clip.duration > 1e-12:
            extracted.append(extracted_clip)

    return extracted


def delete_range(track: Track, start: float, end: float) -> None:
    """Remove or trim clips in range.

    With position-based clips, this is simple:
    - Clips fully inside range: remove
    - Clips partially overlapping: trim
    - Clips outside range: keep unchanged
    """
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
            before_duration = start - clip_start
            before = Clip(
                source=clip.source,
                source_start=clip.source_start,
                source_end=clip.source_start + before_duration,
                position=clip.position,
                gain=clip.gain,
                fade_in=clip.fade_in,
                fade_out=0.0,
            )
            # After part
            after_offset = end - clip_start
            after = Clip(
                source=clip.source,
                source_start=clip.source_start + after_offset,
                source_end=clip.source_end,
                position=end,  # starts at end of deleted range
                gain=clip.gain,
                fade_in=0.0,
                fade_out=clip.fade_out,
            )
            if before.duration > 1e-12:
                new_clips.append(before)
            if after.duration > 1e-12:
                new_clips.append(after)
        elif clip_start < start:
            # Overlaps at end - trim end
            trimmed = Clip(
                source=clip.source,
                source_start=clip.source_start,
                source_end=clip.source_start + (start - clip_start),
                position=clip.position,
                gain=clip.gain,
                fade_in=clip.fade_in,
                fade_out=0.0,
            )
            if trimmed.duration > 1e-12:
                new_clips.append(trimmed)
        else:
            # Overlaps at start - trim start
            trim_amount = end - clip_start
            trimmed = Clip(
                source=clip.source,
                source_start=clip.source_start + trim_amount,
                source_end=clip.source_end,
                position=end,
                gain=clip.gain,
                fade_in=0.0,
                fade_out=clip.fade_out,
            )
            if trimmed.duration > 1e-12:
                new_clips.append(trimmed)

    track.clips = new_clips


def insert_clips_at(track: Track, clips: list[Clip], dest: float) -> None:
    """Insert clips at destination position.

    Args:
        track: Track to insert into.
        clips: Clips to insert (positions relative to 0).
        dest: Destination position in track.
    """
    for clip in clips:
        # Adjust position to destination
        new_clip = Clip(
            source=clip.source,
            source_start=clip.source_start,
            source_end=clip.source_end,
            position=dest + clip.position,
            gain=clip.gain,
            fade_in=clip.fade_in,
            fade_out=clip.fade_out,
        )
        track.clips.append(new_clip)


@command("d")
def cmd_delete(project: "Project", cmd: Command) -> None:
    """Delete content (leaves gap).

    Usage:
        d         - delete current block
        5d        - delete block 5
        1,5d      - delete blocks 1-5

    This is non-destructive: content is removed from the timeline
    but the duration stays the same (gap/silence remains).
    """
    blocks = project.blocks

    if blocks.count == 0:
        print("? no blocks in timeline")
        return

    # Determine range
    if cmd.addr1 is None:
        # Current block
        block1 = blocks.from_time(project.session.current_position)
        block2 = block1
    elif cmd.addr2 is None:
        # Single address
        block1 = resolve_address(project, cmd.addr1, 1)
        block2 = block1
    else:
        # Range
        block1 = resolve_address(project, cmd.addr1, 1)
        block2 = resolve_address(project, cmd.addr2, blocks.count)

    # Validate
    try:
        blocks.validate(block1)
        blocks.validate(block2)
    except ValueError as e:
        print(f"? {e}")
        return

    if block1 > block2:
        block1, block2 = block2, block1

    # Calculate time range
    start_time = blocks.to_time(block1)
    end_time = blocks.to_time_end(block2)

    # Prepare for edit
    project.prepare_edit()

    # Delete content in range
    track = project.session.get_track(project.session.current_track)
    delete_range(track, start_time, end_time)

    project.mark_dirty(f"{block1},{block2}d" if block1 != block2 else f"{block1}d")

    # Update point to start of deleted range
    _set_point_to_block(project, block1)

    n = block2 - block1 + 1
    print(f"deleted {n} block{'s' if n > 1 else ''}")


@command("m")
def cmd_move(project: "Project", cmd: Command) -> None:
    """Move content to destination (leaves gap at source).

    Usage:
        5m10      - move block 5 to position 10
        1,5m20    - move blocks 1-5 to position 20
        5m$       - move block 5 to end

    Source becomes a gap. Content layers at destination.
    """
    blocks = project.blocks

    if blocks.count == 0:
        print("? no blocks in timeline")
        return

    # Need destination
    if cmd.dest is None:
        print("? missing destination")
        return

    # Determine source range
    if cmd.addr1 is None:
        # Current block
        block1 = blocks.from_time(project.session.current_position)
        block2 = block1
    elif cmd.addr2 is None:
        # Single address
        block1 = resolve_address(project, cmd.addr1, 1)
        block2 = block1
    else:
        # Range
        block1 = resolve_address(project, cmd.addr1, 1)
        block2 = resolve_address(project, cmd.addr2, blocks.count)

    # Validate source
    try:
        blocks.validate(block1)
        blocks.validate(block2)
    except ValueError as e:
        print(f"? {e}")
        return

    if block1 > block2:
        block1, block2 = block2, block1

    # Resolve destination
    dest_block = resolve_address(project, cmd.dest, blocks.count)
    if dest_block < 1:
        dest_block = 1

    # Calculate times
    start_time = blocks.to_time(block1)
    end_time = blocks.to_time_end(block2)
    dest_time = blocks.to_time(dest_block)

    # Prepare for edit
    project.prepare_edit()

    # Get track
    track = project.session.get_track(project.session.current_track)

    # Extract clips from source range
    extracted = extract_clips_in_range(track, start_time, end_time)

    if not extracted:
        print("? no content to move")
        return

    # Delete from source
    delete_range(track, start_time, end_time)

    # Insert at destination
    insert_clips_at(track, extracted, dest_time)

    project.mark_dirty(f"{block1},{block2}m{dest_block}" if block1 != block2 else f"{block1}m{dest_block}")

    # Update point to destination
    _set_point_to_block(project, dest_block)

    n = block2 - block1 + 1
    print(f"moved {n} block{'s' if n > 1 else ''} to {dest_block}")


@command("t")
def cmd_copy(project: "Project", cmd: Command) -> None:
    """Copy content to destination.

    Usage:
        5t10      - copy block 5 to position 10
        1,5t$     - copy blocks 1-5 to end

    Content layers at destination (overlaps with existing).
    """
    blocks = project.blocks

    if blocks.count == 0:
        print("? no blocks in timeline")
        return

    # Need destination
    if cmd.dest is None:
        print("? missing destination")
        return

    # Determine source range
    if cmd.addr1 is None:
        # Current block
        block1 = blocks.from_time(project.session.current_position)
        block2 = block1
    elif cmd.addr2 is None:
        # Single address
        block1 = resolve_address(project, cmd.addr1, 1)
        block2 = block1
    else:
        # Range
        block1 = resolve_address(project, cmd.addr1, 1)
        block2 = resolve_address(project, cmd.addr2, blocks.count)

    # Validate source
    try:
        blocks.validate(block1)
        blocks.validate(block2)
    except ValueError as e:
        print(f"? {e}")
        return

    if block1 > block2:
        block1, block2 = block2, block1

    # Resolve destination
    dest_block = resolve_address(project, cmd.dest, blocks.count)
    if dest_block < 1:
        dest_block = 1

    # Calculate times
    start_time = blocks.to_time(block1)
    end_time = blocks.to_time_end(block2)
    dest_time = blocks.to_time(dest_block)

    # Prepare for edit
    project.prepare_edit()

    # Get track
    track = project.session.get_track(project.session.current_track)

    # Extract clips from source range (copies)
    extracted = extract_clips_in_range(track, start_time, end_time)

    if not extracted:
        print("? no content to copy")
        return

    # Insert at destination (source remains intact)
    insert_clips_at(track, extracted, dest_time)

    project.mark_dirty(f"{block1},{block2}t{dest_block}" if block1 != block2 else f"{block1}t{dest_block}")

    # Update point to destination
    _set_point_to_block(project, dest_block)

    n = block2 - block1 + 1
    print(f"copied {n} block{'s' if n > 1 else ''} to {dest_block}")


# =============================================================================
# Ripple editing commands
# =============================================================================

@command("rd")
def cmd_ripple_delete(project: "Project", cmd: Command) -> None:
    """Ripple delete - delete content and close gap.

    Usage:
        rd        - ripple delete current block
        5rd       - ripple delete block 5
        1,5rd     - ripple delete blocks 1-5

    Unlike 'd', this shifts all following content left to close the gap.
    Timeline duration decreases by the deleted amount.
    """
    blocks = project.blocks

    if blocks.count == 0:
        print("? no blocks in timeline")
        return

    # Determine range
    if cmd.addr1 is None:
        # Current block
        block1 = blocks.from_time(project.session.current_position)
        block2 = block1
    elif cmd.addr2 is None:
        # Single address
        block1 = resolve_address(project, cmd.addr1, 1)
        block2 = block1
    else:
        # Range
        block1 = resolve_address(project, cmd.addr1, 1)
        block2 = resolve_address(project, cmd.addr2, blocks.count)

    # Validate
    try:
        blocks.validate(block1)
        blocks.validate(block2)
    except ValueError as e:
        print(f"? {e}")
        return

    if block1 > block2:
        block1, block2 = block2, block1

    # Calculate time range
    start_time = blocks.to_time(block1)
    end_time = blocks.to_time_end(block2)

    # Prepare for edit
    project.prepare_edit()

    # Ripple delete content in range
    track = project.session.get_track(project.session.current_track)
    ripple_delete_range(track, start_time, end_time)

    project.mark_dirty(f"{block1},{block2}rd" if block1 != block2 else f"{block1}rd")

    # Update point to start of deleted range
    _set_point_to_block(project, block1)

    n = block2 - block1 + 1
    print(f"ripple deleted {n} block{'s' if n > 1 else ''}")


@command("rm")
def cmd_ripple_move(project: "Project", cmd: Command) -> None:
    """Ripple move - move content, closing gap at source, making room at dest.

    Usage:
        5rm10     - ripple move block 5 to position 10
        1,5rm20   - ripple move blocks 1-5 to position 20
        5rm$      - ripple move block 5 to end

    Source gap is closed. Destination content shifts right to make room.
    """
    blocks = project.blocks

    if blocks.count == 0:
        print("? no blocks in timeline")
        return

    # Need destination
    if cmd.dest is None:
        print("? missing destination")
        return

    # Determine source range
    if cmd.addr1 is None:
        # Current block
        block1 = blocks.from_time(project.session.current_position)
        block2 = block1
    elif cmd.addr2 is None:
        # Single address
        block1 = resolve_address(project, cmd.addr1, 1)
        block2 = block1
    else:
        # Range
        block1 = resolve_address(project, cmd.addr1, 1)
        block2 = resolve_address(project, cmd.addr2, blocks.count)

    # Validate source
    try:
        blocks.validate(block1)
        blocks.validate(block2)
    except ValueError as e:
        print(f"? {e}")
        return

    if block1 > block2:
        block1, block2 = block2, block1

    # Resolve destination
    dest_block = resolve_address(project, cmd.dest, blocks.count)
    if dest_block < 1:
        dest_block = 1

    # Calculate times
    start_time = blocks.to_time(block1)
    end_time = blocks.to_time_end(block2)
    move_duration = end_time - start_time
    dest_time = blocks.to_time(dest_block)

    # Prepare for edit
    project.prepare_edit()

    # Get track
    track = project.session.get_track(project.session.current_track)

    # Extract clips from source range
    extracted = extract_clips_in_range(track, start_time, end_time)

    if not extracted:
        print("? no content to move")
        return

    # Ripple delete from source (closes gap)
    ripple_delete_range(track, start_time, end_time)

    # Adjust destination time if it was after the source
    # (since we just shifted everything left)
    if dest_time > start_time:
        dest_time -= move_duration

    # Make room at destination
    make_room_at(track, dest_time, move_duration)

    # Insert at destination
    insert_clips_at(track, extracted, dest_time)

    project.mark_dirty(f"{block1},{block2}rm{dest_block}" if block1 != block2 else f"{block1}rm{dest_block}")

    # Update point to destination
    # Recalculate dest_block after the ripple operations
    new_dest_block = blocks.from_time(dest_time)
    _set_point_to_block(project, new_dest_block)

    n = block2 - block1 + 1
    print(f"ripple moved {n} block{'s' if n > 1 else ''}")


@command("rt")
def cmd_ripple_copy(project: "Project", cmd: Command) -> None:
    """Ripple copy - copy content, making room at destination.

    Usage:
        5rt10     - ripple copy block 5 to position 10
        1,5rt$    - ripple copy blocks 1-5 to end

    Destination content shifts right to make room for the copy.
    Timeline duration increases by the copied amount.
    """
    blocks = project.blocks

    if blocks.count == 0:
        print("? no blocks in timeline")
        return

    # Need destination
    if cmd.dest is None:
        print("? missing destination")
        return

    # Determine source range
    if cmd.addr1 is None:
        # Current block
        block1 = blocks.from_time(project.session.current_position)
        block2 = block1
    elif cmd.addr2 is None:
        # Single address
        block1 = resolve_address(project, cmd.addr1, 1)
        block2 = block1
    else:
        # Range
        block1 = resolve_address(project, cmd.addr1, 1)
        block2 = resolve_address(project, cmd.addr2, blocks.count)

    # Validate source
    try:
        blocks.validate(block1)
        blocks.validate(block2)
    except ValueError as e:
        print(f"? {e}")
        return

    if block1 > block2:
        block1, block2 = block2, block1

    # Resolve destination
    dest_block = resolve_address(project, cmd.dest, blocks.count)
    if dest_block < 1:
        dest_block = 1

    # Calculate times
    start_time = blocks.to_time(block1)
    end_time = blocks.to_time_end(block2)
    copy_duration = end_time - start_time
    dest_time = blocks.to_time(dest_block)

    # Prepare for edit
    project.prepare_edit()

    # Get track
    track = project.session.get_track(project.session.current_track)

    # Extract clips from source range (copies)
    extracted = extract_clips_in_range(track, start_time, end_time)

    if not extracted:
        print("? no content to copy")
        return

    # Make room at destination
    make_room_at(track, dest_time, copy_duration)

    # Insert at destination
    insert_clips_at(track, extracted, dest_time)

    project.mark_dirty(f"{block1},{block2}rt{dest_block}" if block1 != block2 else f"{block1}rt{dest_block}")

    # Update point to destination
    _set_point_to_block(project, dest_block)

    n = block2 - block1 + 1
    print(f"ripple copied {n} block{'s' if n > 1 else ''}")
