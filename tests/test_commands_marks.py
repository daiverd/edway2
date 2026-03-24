"""Tests for mark commands (k, region, regions)."""

import pytest


class TestMark:
    """Tests for k (mark) command."""

    def test_set_mark_at_current_position(self, tmp_project, sample_wav, capsys):
        """ka sets mark 'a at current position."""
        tmp_project.execute(f"r {sample_wav}")
        tmp_project.session.current_position = 0.5

        tmp_project.execute("ka")

        assert "a" in tmp_project.session.marks
        assert tmp_project.session.marks["a"] == 0.5
        output = capsys.readouterr().out
        assert "mark 'a set" in output

    def test_set_mark_at_block(self, tmp_project, sample_wav, capsys):
        """5ka sets mark 'a at block 5."""
        tmp_project.execute(f"r {sample_wav}")
        tmp_project.session.block_duration_ms = 100  # 10 blocks per second

        tmp_project.execute("5ka")

        assert "a" in tmp_project.session.marks
        # Block 5 at 100ms blocks = 0.4s (block 5 starts at 0.4s)
        assert tmp_project.session.marks["a"] == pytest.approx(0.4, abs=0.01)

    def test_list_marks_empty(self, tmp_project, capsys):
        """k with no marks shows message."""
        tmp_project.execute("k")

        output = capsys.readouterr().out
        assert "no marks set" in output

    def test_list_marks(self, tmp_project, sample_wav, capsys):
        """k lists all marks."""
        tmp_project.execute(f"r {sample_wav}")
        tmp_project.session.marks["a"] = 0.5
        tmp_project.session.marks["b"] = 1.0

        tmp_project.execute("k")

        output = capsys.readouterr().out
        assert "'a:" in output
        assert "'b:" in output

    def test_mark_must_be_single_letter(self, tmp_project, capsys):
        """Mark name must be single lowercase letter."""
        tmp_project.execute("kAB")

        output = capsys.readouterr().out
        assert "single lowercase letter" in output

    def test_mark_must_be_lowercase(self, tmp_project, capsys):
        """Mark name must be lowercase."""
        tmp_project.execute("kA")

        output = capsys.readouterr().out
        assert "single lowercase letter" in output

    def test_overwrite_mark(self, tmp_project, sample_wav, capsys):
        """Setting same mark twice overwrites."""
        tmp_project.execute(f"r {sample_wav}")
        tmp_project.session.marks["a"] = 0.5

        tmp_project.session.current_position = 0.8
        tmp_project.execute("ka")

        assert tmp_project.session.marks["a"] == 0.8


class TestRegion:
    """Tests for region command."""

    def test_list_regions_empty(self, tmp_project, capsys):
        """region with no regions shows message."""
        tmp_project.execute("region")

        output = capsys.readouterr().out
        assert "no regions defined" in output

    def test_define_region(self, tmp_project, sample_wav, capsys):
        """1,10 region intro defines region."""
        tmp_project.execute(f"r {sample_wav}")
        tmp_project.session.block_duration_ms = 100

        tmp_project.execute("1,5 region intro")

        assert "intro" in tmp_project.session.regions
        start, end = tmp_project.session.regions["intro"]
        assert start == pytest.approx(0.0, abs=0.01)  # block 1
        assert end == pytest.approx(0.5, abs=0.01)   # end of block 5

        output = capsys.readouterr().out
        assert "region 'intro' set" in output

    def test_show_specific_region(self, tmp_project, sample_wav, capsys):
        """region intro shows that region."""
        tmp_project.execute(f"r {sample_wav}")
        tmp_project.session.regions["intro"] = (0.0, 1.0)

        tmp_project.execute("region intro")

        output = capsys.readouterr().out
        assert "intro:" in output

    def test_region_not_found(self, tmp_project, capsys):
        """region unknown shows error."""
        tmp_project.execute("region unknown")

        output = capsys.readouterr().out
        assert "not found" in output

    def test_region_requires_range(self, tmp_project, sample_wav, capsys):
        """region with single address shows error."""
        tmp_project.execute(f"r {sample_wav}")

        tmp_project.execute("5 region intro")

        output = capsys.readouterr().out
        assert "requires a range" in output

    def test_list_multiple_regions(self, tmp_project, sample_wav, capsys):
        """region lists all regions."""
        tmp_project.execute(f"r {sample_wav}")
        tmp_project.session.regions["intro"] = (0.0, 1.0)
        tmp_project.session.regions["verse"] = (1.0, 2.0)

        tmp_project.execute("region")

        output = capsys.readouterr().out
        assert "intro:" in output
        assert "verse:" in output


class TestRegionsAlias:
    """Tests for regions command (alias)."""

    def test_regions_lists_all(self, tmp_project, sample_wav, capsys):
        """regions command lists all regions."""
        tmp_project.execute(f"r {sample_wav}")
        tmp_project.session.regions["intro"] = (0.0, 1.0)

        tmp_project.execute("regions")

        output = capsys.readouterr().out
        assert "intro:" in output
