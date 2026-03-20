"""Playback commands: p (play), z (play seconds)."""

from pathlib import Path

import numpy as np

from edway2.commands import command
from edway2.parser import Command, Address
from edway2.audio import load_audio, play_until_keypress, stop_playback
from edway2.errors import AudioError

if True:  # TYPE_CHECKING workaround
    from edway2.project import Project


def resolve_address(project: "Project", addr: Address | None, default_block: int) -> int:
    """Resolve an address to a block number.

    Args:
        project: Project instance.
        addr: Address to resolve, or None.
        default_block: Block to use if addr is None.

    Returns:
        Block number (1-indexed).
    """
    if addr is None:
        return default_block

    blocks = project.blocks
    base_block = default_block

    if addr.type == "number":
        base_block = addr.value
    elif addr.type == "dot":
        base_block = blocks.from_time(project.session.current_position)
    elif addr.type == "dollar":
        base_block = blocks.count
    elif addr.type == "mark":
        mark_name = addr.value
        if mark_name in project.session.marks:
            mark_time = project.session.marks[mark_name]
            base_block = blocks.from_time(mark_time)
        else:
            base_block = 1  # fallback
    elif addr.type == "time":
        base_block = blocks.from_time(addr.value)

    return base_block + addr.offset


def get_playback_range(project: "Project", cmd: Command) -> tuple[float, float]:
    """Get start and end times for playback from command addresses.

    Args:
        project: Project instance.
        cmd: Parsed command with addr1, addr2.

    Returns:
        Tuple of (start_time, end_time) in seconds.

    Raises:
        ValueError: If block addresses are out of range.
    """
    blocks = project.blocks

    if cmd.addr1 is None and cmd.addr2 is None:
        # No addresses: play current block
        current_block = blocks.from_time(project.session.current_position)
        current_block = blocks.clamp(current_block)
        blocks.validate(current_block)
        start = blocks.to_time(current_block)
        end = blocks.to_time_end(current_block)
    elif cmd.addr2 is None:
        # Single address: play that block
        block = resolve_address(project, cmd.addr1, 1)
        blocks.validate(block)
        start = blocks.to_time(block)
        end = blocks.to_time_end(block)
    else:
        # Range: play from addr1 to addr2
        block1 = resolve_address(project, cmd.addr1, 1)
        block2 = resolve_address(project, cmd.addr2, blocks.count)
        blocks.validate(block1)
        blocks.validate(block2)
        if block1 > block2:
            block1, block2 = block2, block1
        start = blocks.to_time(block1)
        end = blocks.to_time_end(block2)

    # Clamp to actual duration
    duration = project.session.duration
    start = max(0, min(start, duration))
    end = max(start, min(end, duration))

    return start, end


def render_timeline(project: "Project", start_time: float, end_time: float) -> tuple[np.ndarray, int]:
    """Render timeline audio between start and end times.

    Args:
        project: Project instance.
        start_time: Start time in seconds.
        end_time: End time in seconds.

    Returns:
        Tuple of (audio_data, sample_rate).
    """
    # For now, simple implementation: find first clip and load from it
    # TODO: proper mixing of multiple tracks/clips

    track = project.session.get_track(project.session.current_track)

    if len(track) == 0:
        raise AudioError("no clips in track")

    # Get first clip
    clip = track[0]
    media_ref = clip.media_reference

    if media_ref is None:
        raise AudioError("clip has no media reference")

    # Get file path
    target_url = media_ref.target_url
    if target_url.startswith("sources/"):
        file_path = project.path / target_url
    else:
        file_path = Path(target_url)

    # Get clip info
    clip_sr = media_ref.metadata.get("edway2", {}).get("sample_rate", 44100)

    # Calculate frame range
    start_frame = int(start_time * clip_sr)
    end_frame = int(end_time * clip_sr)
    num_frames = end_frame - start_frame

    if num_frames <= 0:
        raise AudioError("invalid playback range")

    # Load audio
    data, sr = load_audio(file_path, start_frame, num_frames)

    return data, sr


@command("p")
def cmd_play(project: "Project", cmd: Command) -> None:
    """Play audio.

    Usage:
        p           - play current block
        5p          - play block 5
        1,10p       - play blocks 1-10
        .,$p        - play from current to end
    """
    if project.session.duration == 0:
        print("? no audio in session")
        return

    try:
        start, end = get_playback_range(project, cmd)
        data, sr = render_timeline(project, start, end)
        stopped = play_until_keypress(data, sr)
        if stopped:
            print("(stopped)")
    except ValueError as e:
        print(f"? {e}")
    except AudioError as e:
        print(f"? {e}")
    except Exception as e:
        print(f"? playback error: {e}")


@command("z")
def cmd_play_seconds(project: "Project", cmd: Command) -> None:
    """Play N seconds from position.

    Usage:
        z           - play 5 seconds from current
        z10         - play 10 seconds from current
        5z10        - play 10 seconds from block 5
    """
    if project.session.duration == 0:
        print("? no audio in session")
        return

    # Parse seconds argument
    seconds = 5.0  # default
    if cmd.arg:
        try:
            seconds = float(cmd.arg)
        except ValueError:
            print(f"? invalid seconds: {cmd.arg}")
            return

    # Get start position
    blocks = project.blocks
    if cmd.addr1 is not None:
        block = resolve_address(project, cmd.addr1, 1)
        block = blocks.clamp(block)
        start = blocks.to_time(block)
    else:
        start = project.session.current_position

    end = min(start + seconds, project.session.duration)

    if end <= start:
        print("? nothing to play")
        return

    try:
        data, sr = render_timeline(project, start, end)
        stopped = play_until_keypress(data, sr)
        if stopped:
            print("(stopped)")
    except AudioError as e:
        print(f"? {e}")
    except Exception as e:
        print(f"? playback error: {e}")
