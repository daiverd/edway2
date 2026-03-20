"""File commands: r (read), w (write), save, load."""

from pathlib import Path

import opentimelineio as otio

from edway2.commands import command
from edway2.parser import Command
from edway2.audio import read_audio_info, copy_to_sources
from edway2.errors import FileError, AudioError

if True:  # TYPE_CHECKING workaround for circular import
    from edway2.project import Project


@command("r")
def cmd_read(project: "Project", cmd: Command) -> None:
    """Read audio file into current track.

    Usage:
        r <file>      - append file to current track
        5r <file>     - insert at block 5

    The file is copied to the sources/ folder and a clip
    is created on the timeline referencing it.
    """
    if not cmd.arg:
        print("? missing filename")
        return

    src_path = Path(cmd.arg).expanduser()
    if not src_path.is_absolute():
        # Try relative to current directory
        src_path = Path.cwd() / cmd.arg

    if not src_path.exists():
        print(f"? file not found: {cmd.arg}")
        return

    try:
        # Get audio info
        info = read_audio_info(src_path)

        # Copy to sources folder
        dest_path = copy_to_sources(src_path, project.sources_dir)

        # Create OTIO clip
        # Use relative path from project root
        rel_path = project.resolve_path(dest_path)

        # Create media reference
        media_ref = otio.schema.ExternalReference(
            target_url=str(rel_path),
            available_range=otio.opentime.TimeRange(
                start_time=otio.opentime.RationalTime(0, info["sample_rate"]),
                duration=otio.opentime.RationalTime(
                    info["frames"], info["sample_rate"]
                ),
            ),
        )

        # Store audio metadata
        media_ref.metadata["edway2"] = {
            "sample_rate": info["sample_rate"],
            "channels": info["channels"],
            "duration": info["duration"],
            "original_path": str(src_path),
        }

        # Create clip
        clip = otio.schema.Clip(
            name=src_path.name,
            media_reference=media_ref,
            source_range=otio.opentime.TimeRange(
                start_time=otio.opentime.RationalTime(0, info["sample_rate"]),
                duration=otio.opentime.RationalTime(
                    info["frames"], info["sample_rate"]
                ),
            ),
        )

        # Get current track
        track = project.session.get_track(project.session.current_track)

        # Determine insert position
        if cmd.addr1 is not None:
            # Insert at specified position
            # For now, just append (position handling comes in Phase 5)
            track.append(clip)
        else:
            # Append to end
            track.append(clip)

        project.mark_dirty()
        print(f"read: {src_path.name} ({info['duration']:.2f}s)")

    except FileError as e:
        print(f"? {e}")
    except AudioError as e:
        print(f"? {e}")
    except Exception as e:
        print(f"? error reading file: {e}")


@command("save")
def cmd_save(project: "Project", cmd: Command) -> None:
    """Save current session.

    Usage:
        save [message]
    """
    message = cmd.arg if cmd.arg else "save"
    project.save(message)
    print(f"saved: {project.session_file.name}")


@command("w")
def cmd_write(project: "Project", cmd: Command) -> None:
    """Write/export timeline to file.

    Usage:
        w [file]          - render entire timeline
        1,10w [file]      - render blocks 1-10

    Output goes to renders/ folder.
    """
    # TODO: Implement in Phase 13
    print("? write not implemented yet")
