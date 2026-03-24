"""File commands: r (read), w (write), save, load."""

from pathlib import Path

from edway2.commands import command
from edway2.parser import Command
from edway2.session import Clip
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

        # Use relative path from project root
        rel_path = project.resolve_path(dest_path)

        # Determine insert position (where in the track the clip starts)
        track = project.session.get_track(project.session.current_track)
        if cmd.addr1 is not None:
            # Insert at specified block position
            from edway2.commands.playback import resolve_address
            block = resolve_address(project, cmd.addr1, 1)
            position = project.blocks.to_time(block)
        else:
            # Append to end of track
            position = track.duration

        # Create clip
        clip = Clip(
            source=rel_path,
            source_start=0.0,
            source_end=info["duration"],
            position=position,
            gain=0.0,
        )
        # Store metadata for playback
        clip._sample_rate = info["sample_rate"]
        clip._channels = info["channels"]

        # Prepare for edit (commits previous if dirty)
        project.prepare_edit()

        # Add clip to track
        track.clips.append(clip)

        project.mark_dirty(f"r {src_path.name}")

        # Update point to end of inserted audio
        project.session.current_position = project.session.duration

        print(f"read: {src_path.name} ({info['duration']:.2f}s)")

    except FileError as e:
        print(f"? {e}")
    except AudioError as e:
        print(f"? {e}")
    except Exception as e:
        print(f"? error reading file: {e}")


@command("save")
def cmd_save(project: "Project", cmd: Command) -> None:
    """Save current session, optionally with a tag.

    Usage:
        save              - commit only
        save <name>       - commit and create tag

    Tags create named checkpoints you can reference later.
    Duplicate tag names get auto-suffixed: mix, mix_2, mix_3.
    """
    if not project.is_dirty:
        if cmd.arg:
            # Create tag even if not dirty
            actual_tag = project._create_tag(cmd.arg)
            print(f"tagged: {actual_tag}")
        else:
            print("(nothing to save)")
        return

    tag = cmd.arg if cmd.arg else None
    project.save(message="save", tag=tag)

    if tag:
        print(f"saved and tagged: {tag}")
    else:
        print(f"saved: {project.session_file.name}")


