"""Audio file I/O and processing for edway2."""

from pathlib import Path
import shutil

import soundfile as sf
from pedalboard.io import AudioFile

from edway2.errors import FileError, AudioError


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
