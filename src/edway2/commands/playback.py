"""Playback commands: p (play), z (play seconds)."""

from pathlib import Path

import numpy as np

from edway2.commands import command
from edway2.parser import Command, Address
from edway2.audio import load_audio, play_until_keypress, stop_playback
from edway2.errors import AudioError
from edway2.session import Clip, Track

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


def _get_clip_sample_rate(project: "Project", clip: Clip) -> int:
    """Get sample rate for a clip, loading from file if needed."""
    if clip._sample_rate is not None:
        return clip._sample_rate

    # Load from file
    from edway2.audio import read_audio_info
    source_path = _resolve_source_path(project, clip.source)
    try:
        info = read_audio_info(source_path)
        clip._sample_rate = info["sample_rate"]
        clip._channels = info["channels"]
        return clip._sample_rate
    except Exception:
        return 44100  # default


def _get_clip_channels(project: "Project", clip: Clip) -> int:
    """Get channel count for a clip."""
    if clip._channels is not None:
        return clip._channels

    # Will be set by _get_clip_sample_rate
    _get_clip_sample_rate(project, clip)
    return clip._channels if clip._channels is not None else 2


def _resolve_source_path(project: "Project", source: str) -> Path:
    """Resolve source path to absolute path."""
    if source.startswith("sources/"):
        return project.path / source
    return Path(source)


def db_to_linear(db: float) -> float:
    """Convert decibels to linear gain."""
    return 10 ** (db / 20)


def render_track(
    project: "Project",
    track,
    start_time: float,
    end_time: float,
    sample_rate: int,
    channels: int,
) -> np.ndarray:
    """Render a single track to audio buffer.

    Args:
        project: Project instance.
        track: Track to render.
        start_time: Start time in seconds.
        end_time: End time in seconds.
        sample_rate: Output sample rate.
        channels: Output channel count.

    Returns:
        Audio data as numpy array.
    """
    duration = end_time - start_time
    num_frames = int(duration * sample_rate)
    output = np.zeros((num_frames, channels), dtype=np.float32)

    # Walk through clips and render those that overlap our range
    for clip in track.clips:
        # Calculate global position of this clip
        clip_start = track.start_time + clip.position
        clip_end = clip_start + clip.duration

        # Check if this clip overlaps with our render range
        if clip_end <= start_time or clip_start >= end_time:
            continue

        # Calculate overlap
        overlap_start = max(start_time, clip_start)
        overlap_end = min(end_time, clip_end)

        # Get file path
        file_path = _resolve_source_path(project, clip.source)

        # Get sample rate for this clip
        clip_sr = _get_clip_sample_rate(project, clip)

        # Calculate frame positions in source file
        clip_offset = overlap_start - clip_start
        source_offset = clip.source_start + clip_offset
        clip_start_frame = int(source_offset * clip_sr)
        clip_num_frames = int((overlap_end - overlap_start) * clip_sr)

        if clip_num_frames > 0:
            try:
                data, sr = load_audio(file_path, clip_start_frame, clip_num_frames)

                # Apply clip gain
                if clip.gain != 0.0:
                    data = data * db_to_linear(clip.gain)

                # Where in output buffer to write
                out_start = int((overlap_start - start_time) * sample_rate)

                # Handle channel mismatch
                if len(data.shape) == 1:
                    data = data.reshape(-1, 1)

                if data.shape[1] != channels:
                    if data.shape[1] == 1 and channels == 2:
                        data = np.column_stack([data[:, 0], data[:, 0]])
                    elif data.shape[1] == 2 and channels == 1:
                        data = ((data[:, 0] + data[:, 1]) / 2).reshape(-1, 1)
                    elif data.shape[1] > channels:
                        data = data[:, :channels]
                    else:
                        data = np.column_stack([data[:, 0]] * channels)

                # Mix into output (additive for overlapping clips)
                actual_len = min(len(data), len(output) - out_start)
                if actual_len > 0:
                    output[out_start:out_start + actual_len] += data[:actual_len]

            except Exception:
                pass  # Leave silence on error

    # Apply track gain
    if track.gain != 0.0:
        output *= db_to_linear(track.gain)

    return output


def render_timeline(project: "Project", start_time: float, end_time: float) -> tuple[np.ndarray, int]:
    """Render timeline audio between start and end times.

    Mixes all tracks together, respecting mute/solo settings.

    Args:
        project: Project instance.
        start_time: Start time in seconds.
        end_time: End time in seconds.

    Returns:
        Tuple of (audio_data, sample_rate).
    """
    session = project.session

    # Find tracks to play
    any_solo = any(t.soloed for t in session.tracks)
    tracks_to_play = []

    for track in session.tracks:
        if track.muted:
            continue
        if any_solo and not track.soloed:
            continue
        if len(track.clips) > 0:
            tracks_to_play.append(track)

    if not tracks_to_play:
        raise AudioError("no clips in track")

    # Get sample rate from first clip of first track
    sample_rate = 44100
    channels = 2
    for track in tracks_to_play:
        if track.clips:
            sample_rate = _get_clip_sample_rate(project, track.clips[0])
            channels = _get_clip_channels(project, track.clips[0])
            break

    # Calculate output buffer size
    duration = end_time - start_time
    num_frames = int(duration * sample_rate)

    if num_frames <= 0:
        raise AudioError("invalid playback range")

    # Initialize output buffer with silence
    output = np.zeros((num_frames, channels), dtype=np.float32)

    # Render and mix all tracks
    for track in tracks_to_play:
        track_audio = render_track(
            project, track, start_time, end_time, sample_rate, channels
        )
        output += track_audio

    # Apply master gain
    if session.master_gain != 0.0:
        output *= db_to_linear(session.master_gain)

    # Clip to prevent distortion
    np.clip(output, -1.0, 1.0, out=output)

    return output, sample_rate


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
        # Update point to end of played range
        project.session.current_position = end
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
        # Update point to end of played range
        project.session.current_position = end
    except AudioError as e:
        print(f"? {e}")
    except Exception as e:
        print(f"? playback error: {e}")
