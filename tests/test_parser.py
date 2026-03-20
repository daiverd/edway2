"""Tests for edway2 command parser."""

import pytest

from edway2.parser import parse, Command, Address
from edway2.errors import ParseError


class TestParseSimpleCommands:
    """Test parsing commands without addresses."""

    def test_parse_bare_command(self):
        """Test parsing a command with no addresses."""
        cmd = parse("p")
        assert cmd.name == "p"
        assert cmd.addr1 is None
        assert cmd.addr2 is None
        assert cmd.dest is None
        assert cmd.arg is None

    def test_parse_quit(self):
        """Test parsing quit command."""
        cmd = parse("q")
        assert cmd.name == "q"

    def test_parse_force_quit(self):
        """Test parsing force quit command."""
        cmd = parse("q!")
        assert cmd.name == "q!"

    def test_parse_save(self):
        """Test parsing save command."""
        cmd = parse("save")
        assert cmd.name == "save"

    def test_parse_undo(self):
        """Test parsing undo command."""
        cmd = parse("u")
        assert cmd.name == "u"

    def test_parse_redo(self):
        """Test parsing redo command."""
        cmd = parse("U")
        assert cmd.name == "U"


class TestParseWithAddresses:
    """Test parsing commands with block addresses."""

    def test_parse_single_number_address(self):
        """Test parsing command with single number address."""
        cmd = parse("5p")
        assert cmd.name == "p"
        assert cmd.addr1 == Address("number", 5)
        assert cmd.addr2 is None

    def test_parse_range_addresses(self):
        """Test parsing command with range (two addresses)."""
        cmd = parse("1,10p")
        assert cmd.name == "p"
        assert cmd.addr1 == Address("number", 1)
        assert cmd.addr2 == Address("number", 10)

    def test_parse_dot_address(self):
        """Test parsing dot (current position) address."""
        cmd = parse(".p")
        assert cmd.addr1 == Address("dot", None)

    def test_parse_dollar_address(self):
        """Test parsing dollar (last block) address."""
        cmd = parse("$p")
        assert cmd.addr1 == Address("dollar", None)

    def test_parse_dot_to_dollar_range(self):
        """Test parsing .,$p (current to end)."""
        cmd = parse(".,$p")
        assert cmd.addr1 == Address("dot", None)
        assert cmd.addr2 == Address("dollar", None)

    def test_parse_mark_address(self):
        """Test parsing mark address 'a."""
        cmd = parse("'ap")
        assert cmd.addr1 == Address("mark", "a")

    def test_parse_mark_to_number_range(self):
        """Test parsing 'a,5p."""
        cmd = parse("'a,5p")
        assert cmd.addr1 == Address("mark", "a")
        assert cmd.addr2 == Address("number", 5)

    def test_parse_mark_to_mark_range(self):
        """Test parsing 'a,'bp."""
        cmd = parse("'a,'bp")
        assert cmd.addr1 == Address("mark", "a")
        assert cmd.addr2 == Address("mark", "b")


class TestParseWithOffset:
    """Test parsing addresses with +N or -N offsets."""

    def test_parse_positive_offset(self):
        """Test parsing address with positive offset."""
        cmd = parse(".+5p")
        assert cmd.addr1 == Address("dot", None, offset=5)

    def test_parse_negative_offset(self):
        """Test parsing address with negative offset."""
        cmd = parse("$-3p")
        assert cmd.addr1 == Address("dollar", None, offset=-3)

    def test_parse_number_with_offset(self):
        """Test parsing number address with offset."""
        cmd = parse("10+2p")
        assert cmd.addr1 == Address("number", 10, offset=2)


class TestParseTimeAddress:
    """Test parsing time addresses @M:SS."""

    def test_parse_time_address(self):
        """Test parsing @0:30 time address."""
        cmd = parse("@0:30p")
        assert cmd.addr1 == Address("time", 30.0)

    def test_parse_time_address_minutes(self):
        """Test parsing @1:30 (90 seconds)."""
        cmd = parse("@1:30p")
        assert cmd.addr1 == Address("time", 90.0)

    def test_parse_time_address_with_millis(self):
        """Test parsing @0:30.500 (30.5 seconds)."""
        cmd = parse("@0:30.500p")
        assert cmd.addr1 == Address("time", 30.5)

    def test_parse_time_range(self):
        """Test parsing @0:30,@1:00p."""
        cmd = parse("@0:30,@1:00p")
        assert cmd.addr1 == Address("time", 30.0)
        assert cmd.addr2 == Address("time", 60.0)


class TestParseDestination:
    """Test parsing commands with destination (m, t, rm, rt)."""

    def test_parse_move_with_dest(self):
        """Test parsing 5m10 (move block 5 to position 10)."""
        cmd = parse("5m10")
        assert cmd.name == "m"
        assert cmd.addr1 == Address("number", 5)
        assert cmd.addr2 is None
        assert cmd.dest == Address("number", 10)

    def test_parse_move_range_with_dest(self):
        """Test parsing 1,5m10."""
        cmd = parse("1,5m10")
        assert cmd.name == "m"
        assert cmd.addr1 == Address("number", 1)
        assert cmd.addr2 == Address("number", 5)
        assert cmd.dest == Address("number", 10)

    def test_parse_move_to_end(self):
        """Test parsing 5m$ (move to end)."""
        cmd = parse("5m$")
        assert cmd.name == "m"
        assert cmd.addr1 == Address("number", 5)
        assert cmd.dest == Address("dollar", None)

    def test_parse_copy_with_dest(self):
        """Test parsing 5t10."""
        cmd = parse("5t10")
        assert cmd.name == "t"
        assert cmd.addr1 == Address("number", 5)
        assert cmd.dest == Address("number", 10)

    def test_parse_copy_to_end(self):
        """Test parsing 1,5t$."""
        cmd = parse("1,5t$")
        assert cmd.name == "t"
        assert cmd.addr1 == Address("number", 1)
        assert cmd.addr2 == Address("number", 5)
        assert cmd.dest == Address("dollar", None)

    def test_parse_ripple_move(self):
        """Test parsing 1,5rm10."""
        cmd = parse("1,5rm10")
        assert cmd.name == "rm"
        assert cmd.addr1 == Address("number", 1)
        assert cmd.addr2 == Address("number", 5)
        assert cmd.dest == Address("number", 10)

    def test_parse_ripple_copy(self):
        """Test parsing 5rt10."""
        cmd = parse("5rt10")
        assert cmd.name == "rt"
        assert cmd.addr1 == Address("number", 5)
        assert cmd.dest == Address("number", 10)


class TestParseWithArguments:
    """Test parsing commands with arguments."""

    def test_parse_read_file(self):
        """Test parsing r test.wav."""
        cmd = parse("r test.wav")
        assert cmd.name == "r"
        assert cmd.addr1 is None
        assert cmd.arg == "test.wav"

    def test_parse_read_file_with_address(self):
        """Test parsing 5r test.wav."""
        cmd = parse("5r test.wav")
        assert cmd.name == "r"
        assert cmd.addr1 == Address("number", 5)
        assert cmd.arg == "test.wav"

    def test_parse_write_file(self):
        """Test parsing w out.mp3."""
        cmd = parse("w out.mp3")
        assert cmd.name == "w"
        assert cmd.arg == "out.mp3"

    def test_parse_db_with_arg(self):
        """Test parsing db -3."""
        cmd = parse("db -3")
        assert cmd.name == "db"
        assert cmd.arg == "-3"

    def test_parse_db_range_no_arg(self):
        """Test parsing 1,10db (show loudness)."""
        cmd = parse("1,10db")
        assert cmd.name == "db"
        assert cmd.addr1 == Address("number", 1)
        assert cmd.addr2 == Address("number", 10)
        assert cmd.arg is None

    def test_parse_db_range_with_arg(self):
        """Test parsing 1,10db -3."""
        cmd = parse("1,10db -3")
        assert cmd.name == "db"
        assert cmd.addr1 == Address("number", 1)
        assert cmd.addr2 == Address("number", 10)
        assert cmd.arg == "-3"

    def test_parse_mark_command(self):
        """Test parsing ka (set mark a)."""
        cmd = parse("ka")
        assert cmd.name == "k"
        assert cmd.arg == "a"

    def test_parse_track_switch(self):
        """Test parsing tr 2."""
        cmd = parse("tr 2")
        assert cmd.name == "tr"
        assert cmd.arg == "2"

    def test_parse_help_command(self):
        """Test parsing h p."""
        cmd = parse("h p")
        assert cmd.name == "h"
        assert cmd.arg == "p"

    def test_parse_help_no_arg(self):
        """Test parsing h."""
        cmd = parse("h")
        assert cmd.name == "h"
        assert cmd.arg is None

    def test_parse_shell_command(self):
        """Test parsing !ls."""
        cmd = parse("!ls")
        assert cmd.name == "!"
        assert cmd.arg == "ls"

    def test_parse_shell_no_arg(self):
        """Test parsing ! (interactive shell)."""
        cmd = parse("!")
        assert cmd.name == "!"
        assert cmd.arg is None

    def test_parse_read_with_spaces_in_path(self):
        """Test parsing r /path/with spaces/file.wav."""
        cmd = parse("r /path/with spaces/file.wav")
        assert cmd.name == "r"
        assert cmd.arg == "/path/with spaces/file.wav"


class TestParseZCommand:
    """Test parsing z (play seconds) command."""

    def test_parse_z_bare(self):
        """Test parsing z (5 seconds from current)."""
        cmd = parse("z")
        assert cmd.name == "z"
        assert cmd.arg is None

    def test_parse_z_with_seconds(self):
        """Test parsing z10 (10 seconds)."""
        cmd = parse("z10")
        assert cmd.name == "z"
        assert cmd.arg == "10"

    def test_parse_z_with_address_and_seconds(self):
        """Test parsing 5z10 (10 seconds from block 5)."""
        cmd = parse("5z10")
        assert cmd.name == "z"
        assert cmd.addr1 == Address("number", 5)
        assert cmd.arg == "10"


class TestParseRippleDelete:
    """Test parsing rd command."""

    def test_parse_ripple_delete(self):
        """Test parsing rd."""
        cmd = parse("rd")
        assert cmd.name == "rd"

    def test_parse_ripple_delete_range(self):
        """Test parsing 1,5rd."""
        cmd = parse("1,5rd")
        assert cmd.name == "rd"
        assert cmd.addr1 == Address("number", 1)
        assert cmd.addr2 == Address("number", 5)


class TestParseDelete:
    """Test parsing d command."""

    def test_parse_delete(self):
        """Test parsing d."""
        cmd = parse("d")
        assert cmd.name == "d"

    def test_parse_delete_single(self):
        """Test parsing 5d."""
        cmd = parse("5d")
        assert cmd.name == "d"
        assert cmd.addr1 == Address("number", 5)

    def test_parse_delete_range(self):
        """Test parsing 1,5d."""
        cmd = parse("1,5d")
        assert cmd.name == "d"
        assert cmd.addr1 == Address("number", 1)
        assert cmd.addr2 == Address("number", 5)


class TestParseErrors:
    """Test parsing errors."""

    def test_parse_empty_raises(self):
        """Test parsing empty string raises."""
        with pytest.raises(ParseError):
            parse("")

    def test_parse_whitespace_only_raises(self):
        """Test parsing whitespace-only raises."""
        with pytest.raises(ParseError):
            parse("   ")

    def test_parse_invalid_mark(self):
        """Test parsing invalid mark (not a letter) raises."""
        with pytest.raises(ParseError):
            parse("'1p")

    def test_parse_incomplete_time(self):
        """Test parsing incomplete time address raises."""
        with pytest.raises(ParseError):
            parse("@30p")  # missing colon


class TestCommandEquality:
    """Test Command and Address equality."""

    def test_address_equality(self):
        """Test Address __eq__."""
        a1 = Address("number", 5)
        a2 = Address("number", 5)
        assert a1 == a2

    def test_address_inequality(self):
        """Test Address __eq__ when not equal."""
        a1 = Address("number", 5)
        a2 = Address("number", 10)
        assert a1 != a2

    def test_command_equality(self):
        """Test Command __eq__."""
        c1 = Command("p", addr1=Address("number", 5))
        c2 = Command("p", addr1=Address("number", 5))
        assert c1 == c2
