"""Mark commands: k (set mark), region."""

from edway2.commands import command
from edway2.parser import Command
from edway2.commands.playback import resolve_address

if True:  # TYPE_CHECKING workaround
    from edway2.project import Project


@command("k")
def cmd_mark(project: "Project", cmd: Command) -> None:
    """Set a mark at position.

    Usage:
        ka        - set mark 'a' at current position
        5ka       - set mark 'a' at block 5
        k         - list all marks

    Marks are single lowercase letters. Use 'a in addresses to reference them.
    Example: 'a,'bp plays from mark a to mark b.
    """
    if not cmd.arg:
        # List all marks
        if not project.session.marks:
            print("no marks set")
            return

        blocks = project.blocks
        for name in sorted(project.session.marks.keys()):
            time = project.session.marks[name]
            if blocks.count > 0:
                block = blocks.from_time(time)
                print(f"'{name}: block {block} ({time:.2f}s)")
            else:
                print(f"'{name}: {time:.2f}s")
        return

    # Set mark - arg should be a single lowercase letter
    mark_name = cmd.arg.strip()
    if len(mark_name) != 1 or not mark_name.islower():
        print("? mark must be a single lowercase letter")
        return

    # Get position
    blocks = project.blocks
    if cmd.addr1 is not None:
        if blocks.count == 0:
            print("? no blocks in timeline")
            return
        block = resolve_address(project, cmd.addr1, 1)
        block = blocks.clamp(block)
        time = blocks.to_time(block)
    else:
        time = project.session.current_position

    # Set the mark
    project.session.marks[mark_name] = time

    if blocks.count > 0:
        block = blocks.from_time(time)
        print(f"mark '{mark_name} set at block {block}")
    else:
        print(f"mark '{mark_name} set at {time:.2f}s")


@command("region")
def cmd_region(project: "Project", cmd: Command) -> None:
    """Define or list regions.

    Usage:
        region              - list all regions
        region intro        - show region 'intro'
        1,10 region intro   - define region 'intro' as blocks 1-10

    Regions are named ranges that can be used for batch operations.
    """
    blocks = project.blocks

    if not cmd.arg:
        # List all regions
        if not project.session.regions:
            print("no regions defined")
            return

        for name in sorted(project.session.regions.keys()):
            start, end = project.session.regions[name]
            if blocks.count > 0:
                start_block = blocks.from_time(start)
                end_block = blocks.from_time(end)
                print(f"{name}: blocks {start_block}-{end_block} ({start:.2f}s - {end:.2f}s)")
            else:
                print(f"{name}: {start:.2f}s - {end:.2f}s")
        return

    region_name = cmd.arg.strip()

    if cmd.addr1 is None:
        # Show specific region
        if region_name not in project.session.regions:
            print(f"? region '{region_name}' not found")
            return

        start, end = project.session.regions[region_name]
        if blocks.count > 0:
            start_block = blocks.from_time(start)
            end_block = blocks.from_time(end)
            print(f"{region_name}: blocks {start_block}-{end_block} ({start:.2f}s - {end:.2f}s)")
        else:
            print(f"{region_name}: {start:.2f}s - {end:.2f}s")
        return

    # Define region - need both addresses
    if cmd.addr2 is None:
        print("? region requires a range (e.g., 1,10 region intro)")
        return

    if blocks.count == 0:
        print("? no blocks in timeline")
        return

    # Resolve addresses
    block1 = resolve_address(project, cmd.addr1, 1)
    block2 = resolve_address(project, cmd.addr2, blocks.count)

    try:
        blocks.validate(block1)
        blocks.validate(block2)
    except ValueError as e:
        print(f"? {e}")
        return

    if block1 > block2:
        block1, block2 = block2, block1

    start_time = blocks.to_time(block1)
    end_time = blocks.to_time_end(block2)

    project.session.regions[region_name] = (start_time, end_time)
    print(f"region '{region_name}' set to blocks {block1}-{block2}")


@command("regions")
def cmd_regions(project: "Project", cmd: Command) -> None:
    """List all regions (alias for 'region' with no args)."""
    cmd.arg = None
    cmd_region(project, cmd)
