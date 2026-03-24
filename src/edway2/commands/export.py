"""Export commands: w (write/export audio)."""

import soundfile as sf
from pathlib import Path

from edway2.commands import command
from edway2.parser import Command
from edway2.commands.playback import render_timeline
from edway2.errors import AudioError

if True:  # TYPE_CHECKING workaround
    from edway2.project import Project


@command("w")
def cmd_write(project: "Project", cmd: Command) -> None:
    """Export audio to file.

    Usage:
        w <file>      - export to file
        w             - export to <session-name>.wav

    Renders all tracks (respecting mute/solo) and writes to audio file.
    Supports any format soundfile supports (wav, flac, ogg, etc.)
    """
    blocks = project.blocks

    if blocks.count == 0:
        print("? no audio to export")
        return

    # Get filename
    if cmd.arg:
        filename = cmd.arg.strip()
    else:
        # Default to session name
        filename = f"{project.session.name}.wav"

    # Resolve path relative to project
    path = project.path / filename
    if not path.suffix:
        path = path.with_suffix(".wav")

    # Get full timeline duration
    duration = blocks.duration_seconds

    # Render timeline
    try:
        audio, sample_rate = render_timeline(project, 0.0, duration)
    except AudioError:
        print("? nothing to export (all tracks muted?)")
        return

    if audio is None or len(audio) == 0:
        print("? nothing to export (all tracks muted?)")
        return

    # Determine format from extension
    subtype = None
    suffix = path.suffix.lower()
    if suffix == ".wav":
        subtype = "PCM_16"
    elif suffix == ".flac":
        subtype = "PCM_16"
    # For ogg, mp3 etc., soundfile will figure it out

    # Write file
    try:
        sf.write(str(path), audio, sample_rate, subtype=subtype)
        print(f"wrote: {path.name} ({duration:.2f}s)")
    except Exception as e:
        print(f"? export error: {e}")
