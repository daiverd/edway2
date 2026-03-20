"""Audio file I/O and processing for edway2."""

from pathlib import Path
import shutil

import numpy as np
import soundfile as sf
from pedalboard.io import AudioFile

from edway2.errors import FileError, AudioError

# Lazy import sounddevice to avoid PortAudio dependency at import time
_sd = None


def _get_sounddevice():
    """Lazy load sounddevice module."""
    global _sd
    if _sd is None:
        import sounddevice
        _sd = sounddevice
    return _sd


def read_audio_info(path: Path) -> dict:
    """Read audio file metadata without loading samples.

    Args:
        path: Path to audio file.

    Returns:
        Dict with keys: sample_rate, channels, duration, frames.

    Raises:
        FileError: If file not found.
        AudioError: If file format not supported.
    """
    if not path.exists():
        raise FileError(f"file not found: {path}")

    try:
        # Try soundfile first (WAV, FLAC, OGG, AIFF)
        info = sf.info(str(path))
        return {
            "sample_rate": info.samplerate,
            "channels": info.channels,
            "duration": info.duration,
            "frames": info.frames,
        }
    except Exception:
        pass

    try:
        # Try pedalboard for MP3 and other formats
        with AudioFile(str(path)) as f:
            return {
                "sample_rate": f.samplerate,
                "channels": f.num_channels,
                "duration": f.duration,
                "frames": f.frames,
            }
    except Exception as e:
        raise AudioError(f"cannot read audio file: {path} ({e})")


def copy_to_sources(src_path: Path, sources_dir: Path) -> Path:
    """Copy audio file to project sources directory.

    Args:
        src_path: Source file path.
        sources_dir: Project sources directory.

    Returns:
        Path to copied file in sources directory.
    """
    sources_dir.mkdir(parents=True, exist_ok=True)

    dest_path = sources_dir / src_path.name

    # Handle name collision
    if dest_path.exists():
        stem = src_path.stem
        suffix = src_path.suffix
        counter = 1
        while dest_path.exists():
            dest_path = sources_dir / f"{stem}_{counter}{suffix}"
            counter += 1

    shutil.copy2(src_path, dest_path)
    return dest_path


def load_audio(path: Path, start_frame: int = 0, num_frames: int = -1) -> tuple[np.ndarray, int]:
    """Load audio samples from file.

    Args:
        path: Path to audio file.
        start_frame: Frame to start reading from.
        num_frames: Number of frames to read (-1 for all).

    Returns:
        Tuple of (audio_data as numpy array, sample_rate).

    Raises:
        FileError: If file not found.
        AudioError: If file cannot be read.
    """
    if not path.exists():
        raise FileError(f"file not found: {path}")

    try:
        # Try soundfile first
        data, sr = sf.read(str(path), start=start_frame, frames=num_frames if num_frames > 0 else None)
        return data.astype(np.float32), sr
    except Exception:
        pass

    try:
        # Try pedalboard for MP3
        with AudioFile(str(path)) as f:
            if start_frame > 0:
                f.seek(start_frame)
            frames_to_read = num_frames if num_frames > 0 else f.frames - start_frame
            data = f.read(frames_to_read)
            # pedalboard returns (channels, frames), transpose to (frames, channels)
            return data.T.astype(np.float32), f.samplerate
    except Exception as e:
        raise AudioError(f"cannot load audio: {path} ({e})")


def play_audio(data: np.ndarray, sample_rate: int, blocking: bool = True) -> None:
    """Play audio data through the default output device.

    Args:
        data: Audio samples as numpy array (frames, channels).
        sample_rate: Sample rate in Hz.
        blocking: If True, wait for playback to complete.
    """
    sd = _get_sounddevice()
    sd.play(data, sample_rate)
    if blocking:
        sd.wait()


def play_until_keypress(data: np.ndarray, sample_rate: int) -> bool:
    """Play audio, stopping on any keypress.

    Args:
        data: Audio samples as numpy array (frames, channels).
        sample_rate: Sample rate in Hz.

    Returns:
        True if stopped by keypress, False if played to completion.
    """
    import sys
    import select
    import tty
    import termios

    sd = _get_sounddevice()

    # Save terminal settings
    old_settings = None
    try:
        old_settings = termios.tcgetattr(sys.stdin)
    except termios.error:
        # Not a terminal, fall back to blocking play
        sd.play(data, sample_rate)
        sd.wait()
        return False

    try:
        # Set terminal to raw mode (no buffering, no echo)
        tty.setraw(sys.stdin.fileno())

        # Start non-blocking playback
        sd.play(data, sample_rate)

        # Poll for keypress while audio plays
        stopped = False
        while sd.get_stream() and sd.get_stream().active:
            # Check for keypress with 50ms timeout
            ready, _, _ = select.select([sys.stdin], [], [], 0.05)
            if ready:
                sys.stdin.read(1)  # consume the key
                sd.stop()
                stopped = True
                break

        return stopped

    finally:
        # Restore terminal settings
        if old_settings:
            termios.tcsetattr(sys.stdin, termios.TCSADRAIN, old_settings)


def stop_playback() -> None:
    """Stop any currently playing audio."""
    sd = _get_sounddevice()
    sd.stop()
