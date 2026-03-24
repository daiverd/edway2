"""Tests for editing commands and point management (Phase 8)."""

import pytest


class TestPointManagement:
    """Tests for current_position (point) updates."""

    def test_play_updates_point(self, tmp_project, sample_wav, mocker):
        """Play updates point to end of played range."""
        mocker.patch("edway2.commands.playback.play_until_keypress", return_value=False)
        tmp_project.execute(f"r {sample_wav}")
        tmp_project.execute("ms 100")  # 10 blocks for 1 second
        tmp_project.execute("1,5p")

        # Point should be at end of block 5 (0.5 seconds)
        assert tmp_project.session.current_position == pytest.approx(0.5, abs=0.01)

    def test_z_updates_point(self, tmp_project, sample_wav, mocker):
        """z (play seconds) updates point to end of played range."""
        mocker.patch("edway2.commands.playback.play_until_keypress", return_value=False)
        tmp_project.execute(f"r {sample_wav}")
        tmp_project.session.current_position = 0.0
        tmp_project.execute("z0.3")  # play 0.3 seconds

        assert tmp_project.session.current_position == pytest.approx(0.3, abs=0.01)

    def test_read_updates_point(self, tmp_project, sample_wav):
        """Read updates point to end of inserted audio."""
        tmp_project.execute(f"r {sample_wav}")  # 1 second audio

        # Point should be at end of audio (1.0 seconds)
        assert tmp_project.session.current_position == pytest.approx(1.0, abs=0.01)

    def test_address_only_updates_point(self, tmp_project, sample_wav):
        """Address-only command (e.g., '7') moves point."""
        tmp_project.execute(f"r {sample_wav}")
        tmp_project.execute("ms 100")  # 10 blocks

        tmp_project.execute("7")  # just an address

        # Point should be at start of block 7 (0.6 seconds)
        block = tmp_project.blocks.from_time(tmp_project.session.current_position)
        assert block == 7

    def test_address_only_shows_block(self, tmp_project, sample_wav, capsys):
        """Address-only command shows the block number."""
        tmp_project.execute(f"r {sample_wav}")
        tmp_project.execute("ms 100")  # 10 blocks

        tmp_project.execute("5")

        output = capsys.readouterr().out
        assert "block 5" in output

    def test_address_dollar_goes_to_last(self, tmp_project, sample_wav):
        """$ address goes to last block."""
        tmp_project.execute(f"r {sample_wav}")
        tmp_project.execute("ms 100")  # 10 blocks

        tmp_project.execute("$")

        block = tmp_project.blocks.from_time(tmp_project.session.current_position)
        assert block == 10

    def test_address_with_offset(self, tmp_project, sample_wav):
        """Address with offset works correctly."""
        tmp_project.execute(f"r {sample_wav}")
        tmp_project.execute("ms 100")  # 10 blocks
        tmp_project.execute("5")  # go to block 5

        tmp_project.execute("$-3")  # last block minus 3 = 7

        block = tmp_project.blocks.from_time(tmp_project.session.current_position)
        assert block == 7

    def test_delete_updates_point(self, tmp_project, sample_wav):
        """Delete updates point to start of deleted range."""
        tmp_project.execute(f"r {sample_wav}")
        tmp_project.execute("ms 100")  # 10 blocks
        tmp_project.session.current_position = 0.0

        tmp_project.execute("5d")

        block = tmp_project.blocks.from_time(tmp_project.session.current_position)
        assert block == 5


class TestDelete:
    """Tests for d (delete) command."""

    def test_delete_single_block(self, tmp_project, sample_wav, capsys):
        """Delete single block shows confirmation."""
        tmp_project.execute(f"r {sample_wav}")
        tmp_project.execute("1d")

        output = capsys.readouterr().out
        assert "deleted 1 block" in output

    def test_delete_range(self, tmp_project, sample_wav, capsys):
        """Delete range shows confirmation."""
        tmp_project.execute(f"r {sample_wav}")
        tmp_project.execute("ms 100")  # 10 blocks
        tmp_project.execute("1,3d")

        output = capsys.readouterr().out
        assert "deleted 3 blocks" in output

    def test_delete_removes_clip(self, tmp_project, sample_wav):
        """Delete removes clip from track."""
        tmp_project.execute(f"r {sample_wav}")
        track = tmp_project.session.get_track(0)
        assert len(track.clips) == 1

        tmp_project.execute("1d")

        # Clip should be removed
        assert len(track.clips) == 0

    def test_delete_out_of_range_errors(self, tmp_project, sample_wav, capsys):
        """Delete out of range shows error."""
        tmp_project.execute(f"r {sample_wav}")
        tmp_project.execute("ms 100")  # 10 blocks

        tmp_project.execute("20d")

        output = capsys.readouterr().out
        assert "out of range" in output

    def test_delete_empty_timeline_errors(self, tmp_project, capsys):
        """Delete on empty timeline shows error."""
        tmp_project.execute("1d")

        output = capsys.readouterr().out
        assert "no blocks" in output

    def test_delete_current_block(self, tmp_project, sample_wav):
        """Delete with no address deletes current block."""
        tmp_project.execute(f"r {sample_wav}")
        tmp_project.execute("ms 100")  # 10 blocks
        tmp_project.execute("5")  # go to block 5
        tmp_project.execute("d")  # delete current

        # Point should be at block 5 (start of deleted range)
        block = tmp_project.blocks.from_time(tmp_project.session.current_position)
        assert block == 5

    def test_delete_commits_previous_edit(self, tmp_project, sample_wav):
        """Delete triggers commit of previous dirty edit."""
        tmp_project.execute(f"r {sample_wav}")
        # r marks dirty

        commits_before = len(list(tmp_project.repo.iter_commits()))
        tmp_project.execute("1d")  # should commit r first
        commits_after = len(list(tmp_project.repo.iter_commits()))

        assert commits_after == commits_before + 1


class TestPlayAfterPartialDelete:
    """Tests for playing after partial delete."""

    def test_play_after_partial_delete_works(self, tmp_project, sample_wav, mocker):
        """Playing remaining content after partial delete should work."""
        mock_play = mocker.patch("edway2.commands.playback.play_until_keypress", return_value=False)

        tmp_project.execute(f"r {sample_wav}")
        tmp_project.execute("ms 500")  # 2 blocks for 1 second audio

        # Delete first half
        tmp_project.execute("1d")

        # Should still have content (block 2)
        assert tmp_project.session.duration > 0

        # Play remaining block
        tmp_project.session.current_position = 0.0
        tmp_project.execute("1p")  # play what's left

        # Should have called play
        mock_play.assert_called_once()


class TestMove:
    """Tests for m (move) command."""

    def test_move_single_block(self, tmp_project, sample_wav, capsys):
        """Move single block to new position."""
        tmp_project.execute(f"r {sample_wav}")
        tmp_project.execute("ms 500")  # 2 blocks for 1 second
        tmp_project.execute("1m2")

        output = capsys.readouterr().out
        assert "moved 1 block" in output

    def test_move_removes_from_source(self, tmp_project, sample_wav):
        """Move removes content from source position."""
        tmp_project.execute(f"r {sample_wav}")
        track = tmp_project.session.get_track(0)

        # Initially 1 clip at position 0
        assert len(track.clips) == 1
        assert track.clips[0].position == 0.0

        # Move block 1 to position 2 (with default 1s blocks, this moves the whole clip)
        tmp_project.execute("1m2")

        # Clip should be at block 2 position (1.0 seconds with 1000ms blocks)
        assert len(track.clips) == 1
        assert track.clips[0].position == pytest.approx(1.0, abs=0.01)

    def test_move_needs_destination(self, tmp_project, sample_wav, capsys):
        """Move without destination shows error."""
        tmp_project.execute(f"r {sample_wav}")
        tmp_project.execute("1m")

        output = capsys.readouterr().out
        assert "missing destination" in output

    def test_move_updates_point(self, tmp_project, sample_wav):
        """Move updates point to destination."""
        tmp_project.execute(f"r {sample_wav}")
        tmp_project.execute("ms 100")  # 10 blocks
        tmp_project.execute("1m5")

        block = tmp_project.blocks.from_time(tmp_project.session.current_position)
        assert block == 5


class TestCopy:
    """Tests for t (copy) command."""

    def test_copy_single_block(self, tmp_project, sample_wav, capsys):
        """Copy single block to new position."""
        tmp_project.execute(f"r {sample_wav}")
        tmp_project.execute("ms 500")  # 2 blocks
        tmp_project.execute("1t2")

        output = capsys.readouterr().out
        assert "copied 1 block" in output

    def test_copy_creates_duplicate(self, tmp_project, sample_wav):
        """Copy creates duplicate clip at destination."""
        tmp_project.execute(f"r {sample_wav}")
        tmp_project.execute("ms 500")  # 2 blocks
        track = tmp_project.session.get_track(0)

        # Initially 1 clip
        assert len(track.clips) == 1

        # Copy block 1 to position 2
        tmp_project.execute("1t2")

        # Should now have 2 clips
        assert len(track.clips) == 2

    def test_copy_preserves_source(self, tmp_project, sample_wav):
        """Copy preserves source content."""
        tmp_project.execute(f"r {sample_wav}")
        tmp_project.execute("ms 500")
        track = tmp_project.session.get_track(0)

        original_source = track.clips[0].source

        tmp_project.execute("1t2")

        # Both clips should reference same source
        assert track.clips[0].source == original_source
        assert track.clips[1].source == original_source

    def test_copy_needs_destination(self, tmp_project, sample_wav, capsys):
        """Copy without destination shows error."""
        tmp_project.execute(f"r {sample_wav}")
        tmp_project.execute("1t")

        output = capsys.readouterr().out
        assert "missing destination" in output

    def test_copy_updates_point(self, tmp_project, sample_wav):
        """Copy updates point to destination."""
        tmp_project.execute(f"r {sample_wav}")
        tmp_project.execute("ms 100")  # 10 blocks
        tmp_project.execute("1t5")

        block = tmp_project.blocks.from_time(tmp_project.session.current_position)
        assert block == 5


class TestRippleDelete:
    """Tests for rd (ripple delete) command."""

    def test_ripple_delete_single_block(self, tmp_project, sample_wav, capsys):
        """Ripple delete shows confirmation."""
        tmp_project.execute(f"r {sample_wav}")
        tmp_project.execute("1rd")

        output = capsys.readouterr().out
        assert "ripple deleted 1 block" in output

    def test_ripple_delete_closes_gap(self, tmp_project, sample_wav, sample_wav_2sec):
        """Ripple delete shifts following content left."""
        # Read 2 second file, then 1 second file
        tmp_project.execute(f"r {sample_wav_2sec}")  # 2 seconds at position 0
        tmp_project.execute(f"r {sample_wav}")  # 1 second at position 2

        track = tmp_project.session.get_track(0)
        assert len(track.clips) == 2
        assert track.clips[1].position == pytest.approx(2.0, abs=0.01)

        # Ripple delete the first clip (block 1 with 1s blocks = first 1 second)
        tmp_project.execute("1rd")

        # Second clip should have shifted left by 1 second
        remaining_clips = [c for c in track.clips if c.duration > 0]
        # The first clip was trimmed (1 second deleted), second clip shifted
        # Actually, with default 1000ms blocks, block 1 = 0-1s
        # Deleting 0-1s of the 2s clip leaves 1s, and shifts the 1s clip left by 1s
        assert any(c.position == pytest.approx(1.0, abs=0.01) for c in track.clips)

    def test_ripple_delete_reduces_duration(self, tmp_project, sample_wav):
        """Ripple delete reduces timeline duration."""
        tmp_project.execute(f"r {sample_wav}")  # 1 second
        initial_duration = tmp_project.session.duration

        tmp_project.execute("1rd")  # delete the whole thing

        # Duration should be 0 now
        assert tmp_project.session.duration < initial_duration

    def test_ripple_delete_range(self, tmp_project, sample_wav, capsys):
        """Ripple delete range shows confirmation."""
        tmp_project.execute(f"r {sample_wav}")
        tmp_project.execute("ms 100")  # 10 blocks
        tmp_project.execute("1,3rd")

        output = capsys.readouterr().out
        assert "ripple deleted 3 blocks" in output


class TestRippleMove:
    """Tests for rm (ripple move) command."""

    def test_ripple_move_single_block(self, tmp_project, sample_wav, capsys):
        """Ripple move shows confirmation."""
        tmp_project.execute(f"r {sample_wav}")
        tmp_project.execute("ms 500")  # 2 blocks
        tmp_project.execute("1rm2")

        output = capsys.readouterr().out
        assert "ripple moved 1 block" in output

    def test_ripple_move_needs_destination(self, tmp_project, sample_wav, capsys):
        """Ripple move without destination shows error."""
        tmp_project.execute(f"r {sample_wav}")
        tmp_project.execute("1rm")

        output = capsys.readouterr().out
        assert "missing destination" in output

    def test_ripple_move_closes_source_gap(self, tmp_project, sample_wav, sample_wav_2sec):
        """Ripple move closes gap at source."""
        # Two clips: 2s at 0, 1s at 2
        tmp_project.execute(f"r {sample_wav_2sec}")
        tmp_project.execute(f"r {sample_wav}")
        tmp_project.execute("ms 1000")  # 1s blocks

        initial_duration = tmp_project.session.duration
        assert initial_duration == pytest.approx(3.0, abs=0.01)

        # Ripple move block 1 to end (block 4 = after all content)
        tmp_project.execute("1rm4")

        # Duration should stay roughly the same (content moved, not duplicated)
        # The first 1s moved to end, but gap closed
        assert tmp_project.session.duration == pytest.approx(3.0, abs=0.1)


class TestRippleCopy:
    """Tests for rt (ripple copy) command."""

    def test_ripple_copy_single_block(self, tmp_project, sample_wav, capsys):
        """Ripple copy shows confirmation."""
        tmp_project.execute(f"r {sample_wav}")
        tmp_project.execute("ms 500")
        tmp_project.execute("1rt2")

        output = capsys.readouterr().out
        assert "ripple copied 1 block" in output

    def test_ripple_copy_needs_destination(self, tmp_project, sample_wav, capsys):
        """Ripple copy without destination shows error."""
        tmp_project.execute(f"r {sample_wav}")
        tmp_project.execute("1rt")

        output = capsys.readouterr().out
        assert "missing destination" in output

    def test_ripple_copy_increases_duration(self, tmp_project, sample_wav):
        """Ripple copy increases timeline duration."""
        tmp_project.execute(f"r {sample_wav}")  # 1 second
        initial_duration = tmp_project.session.duration

        # Ripple copy block 1 to position 2 (after end)
        tmp_project.execute("1rt2")

        # Duration should increase by 1 second
        assert tmp_project.session.duration == pytest.approx(
            initial_duration + 1.0, abs=0.1
        )

    def test_ripple_copy_makes_room(self, tmp_project, sample_wav, sample_wav_2sec):
        """Ripple copy shifts content to make room."""
        # Read 2 second file
        tmp_project.execute(f"r {sample_wav_2sec}")
        tmp_project.execute("ms 1000")  # 2 blocks

        track = tmp_project.session.get_track(0)
        initial_duration = tmp_project.session.duration

        # Ripple copy block 1 to position 1 (insert at beginning)
        tmp_project.execute("1rt1")

        # Duration should increase by 1 second (the copied block)
        assert tmp_project.session.duration == pytest.approx(
            initial_duration + 1.0, abs=0.1
        )

        # Should have 2 clips now
        assert len(track.clips) == 2
