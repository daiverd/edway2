"""Tests for track commands (tr, ts, tracks, addtrack, rmtrack, mute, solo)."""

import pytest


class TestTrackSwitch:
    """Tests for tr (track) command."""

    def test_show_current_track(self, tmp_project, capsys):
        """tr with no arg shows current track."""
        tmp_project.execute("tr")

        output = capsys.readouterr().out
        assert "track 1" in output
        assert "Track 1" in output

    def test_switch_track(self, tmp_project, capsys):
        """tr with number switches to that track."""
        tmp_project.execute("addtrack Vocals")
        tmp_project.execute("tr 2")

        assert tmp_project.session.current_track == 1
        output = capsys.readouterr().out
        assert "track 2" in output
        assert "Vocals" in output

    def test_switch_invalid_track(self, tmp_project, capsys):
        """tr with invalid track shows error."""
        tmp_project.execute("tr 99")

        output = capsys.readouterr().out
        assert "does not exist" in output

    def test_switch_track_zero(self, tmp_project, capsys):
        """tr 0 shows error."""
        tmp_project.execute("tr 0")

        output = capsys.readouterr().out
        assert "start at 1" in output


class TestTrackSelect:
    """Tests for ts (track select) command."""

    def test_select_single_track(self, tmp_project, capsys):
        """ts 1 selects track 1."""
        tmp_project.execute("addtrack")
        tmp_project.execute("ts 1")

        assert tmp_project.session.tracks[0].selected is True
        assert tmp_project.session.tracks[1].selected is False

        output = capsys.readouterr().out
        assert "selected track 1" in output

    def test_select_multiple_tracks(self, tmp_project, capsys):
        """ts 1,2 selects tracks 1 and 2."""
        tmp_project.execute("addtrack")
        tmp_project.execute("addtrack")
        tmp_project.execute("ts 1,3")

        assert tmp_project.session.tracks[0].selected is True
        assert tmp_project.session.tracks[1].selected is False
        assert tmp_project.session.tracks[2].selected is True

        output = capsys.readouterr().out
        assert "selected tracks" in output

    def test_select_range(self, tmp_project, capsys):
        """ts 1-3 selects tracks 1 through 3."""
        tmp_project.execute("addtrack")
        tmp_project.execute("addtrack")
        tmp_project.execute("addtrack")
        tmp_project.execute("ts 1-3")

        assert tmp_project.session.tracks[0].selected is True
        assert tmp_project.session.tracks[1].selected is True
        assert tmp_project.session.tracks[2].selected is True
        assert tmp_project.session.tracks[3].selected is False

    def test_select_all(self, tmp_project, capsys):
        """ts * selects all tracks."""
        tmp_project.execute("addtrack")
        tmp_project.execute("addtrack")
        tmp_project.execute("ts *")

        assert all(t.selected for t in tmp_project.session.tracks)

    def test_clear_selection(self, tmp_project, capsys):
        """ts with no arg clears selection."""
        tmp_project.execute("addtrack")
        tmp_project.execute("ts *")
        tmp_project.execute("ts")

        assert not any(t.selected for t in tmp_project.session.tracks)
        output = capsys.readouterr().out
        assert "cleared" in output

    def test_select_out_of_range(self, tmp_project, capsys):
        """ts 99 shows error for out of range track."""
        tmp_project.execute("ts 99")

        output = capsys.readouterr().out
        assert "out of range" in output


class TestTracksList:
    """Tests for tracks command."""

    def test_list_single_track(self, tmp_project, capsys):
        """tracks shows single track."""
        tmp_project.execute("tracks")

        output = capsys.readouterr().out
        assert "1." in output
        assert "Track 1" in output

    def test_list_multiple_tracks(self, tmp_project, capsys):
        """tracks shows all tracks."""
        tmp_project.execute("addtrack Vocals")
        tmp_project.execute("addtrack Drums")
        tmp_project.execute("tracks")

        output = capsys.readouterr().out
        assert "Track 1" in output
        assert "Vocals" in output
        assert "Drums" in output

    def test_list_shows_current(self, tmp_project, capsys):
        """tracks shows * for current track."""
        tmp_project.execute("addtrack")
        tmp_project.execute("tr 2")
        capsys.readouterr()  # clear previous output

        tmp_project.execute("tracks")

        output = capsys.readouterr().out
        lines = output.strip().split("\n")
        # Track 2 (second line) should have * indicator
        assert "*" in lines[1]

    def test_list_shows_muted(self, tmp_project, capsys):
        """tracks shows M for muted track."""
        tmp_project.execute("mute")
        tmp_project.execute("tracks")

        output = capsys.readouterr().out
        assert "M" in output

    def test_list_shows_soloed(self, tmp_project, capsys):
        """tracks shows O for soloed track."""
        tmp_project.execute("solo")
        tmp_project.execute("tracks")

        output = capsys.readouterr().out
        assert "O" in output


class TestAddTrack:
    """Tests for addtrack command."""

    def test_add_track_default_name(self, tmp_project, capsys):
        """addtrack with no name uses default."""
        tmp_project.execute("addtrack")

        assert tmp_project.session.track_count == 2
        assert tmp_project.session.tracks[1].name == "Track 2"

        output = capsys.readouterr().out
        assert "added track 2" in output

    def test_add_track_with_name(self, tmp_project, capsys):
        """addtrack with name uses that name."""
        tmp_project.execute("addtrack Vocals")

        assert tmp_project.session.tracks[1].name == "Vocals"

        output = capsys.readouterr().out
        assert "Vocals" in output

    def test_add_track_marks_dirty(self, tmp_project):
        """addtrack marks project dirty."""
        assert not tmp_project.is_dirty
        tmp_project.execute("addtrack")
        assert tmp_project.is_dirty


class TestRemoveTrack:
    """Tests for rmtrack command."""

    def test_remove_empty_track(self, tmp_project, capsys):
        """rmtrack removes empty track."""
        tmp_project.execute("addtrack Temp")
        assert tmp_project.session.track_count == 2

        tmp_project.execute("rmtrack 2")

        assert tmp_project.session.track_count == 1
        output = capsys.readouterr().out
        assert "removed" in output
        assert "Temp" in output

    def test_cannot_remove_last_track(self, tmp_project, capsys):
        """rmtrack refuses to remove last track."""
        tmp_project.execute("rmtrack")

        output = capsys.readouterr().out
        assert "cannot remove last track" in output
        assert tmp_project.session.track_count == 1

    def test_cannot_remove_nonempty_track(self, tmp_project, sample_wav, capsys):
        """rmtrack refuses to remove track with clips."""
        tmp_project.execute("addtrack")
        tmp_project.execute(f"r {sample_wav}")  # adds clip to track 1

        tmp_project.execute("rmtrack 1")

        output = capsys.readouterr().out
        assert "not empty" in output

    def test_remove_adjusts_current_track(self, tmp_project):
        """rmtrack adjusts current_track if needed."""
        tmp_project.execute("addtrack")
        tmp_project.execute("tr 2")
        assert tmp_project.session.current_track == 1

        tmp_project.execute("rmtrack 2")

        # Should be adjusted to valid track
        assert tmp_project.session.current_track == 0


class TestMute:
    """Tests for mute command."""

    def test_toggle_mute_current(self, tmp_project, capsys):
        """mute toggles mute on current track."""
        assert tmp_project.session.tracks[0].muted is False

        tmp_project.execute("mute")
        assert tmp_project.session.tracks[0].muted is True

        output = capsys.readouterr().out
        assert "muted" in output

        tmp_project.execute("mute")
        assert tmp_project.session.tracks[0].muted is False

    def test_mute_specific_track(self, tmp_project, capsys):
        """mute 2 toggles mute on track 2."""
        tmp_project.execute("addtrack")
        tmp_project.execute("mute 2")

        assert tmp_project.session.tracks[0].muted is False
        assert tmp_project.session.tracks[1].muted is True

    def test_mute_multiple_tracks(self, tmp_project):
        """mute 1,2 toggles mute on tracks 1 and 2."""
        tmp_project.execute("addtrack")
        tmp_project.execute("mute 1,2")

        assert tmp_project.session.tracks[0].muted is True
        assert tmp_project.session.tracks[1].muted is True


class TestSolo:
    """Tests for solo command."""

    def test_toggle_solo_current(self, tmp_project, capsys):
        """solo toggles solo on current track."""
        assert tmp_project.session.tracks[0].soloed is False

        tmp_project.execute("solo")
        assert tmp_project.session.tracks[0].soloed is True

        output = capsys.readouterr().out
        assert "soloed" in output

        tmp_project.execute("solo")
        assert tmp_project.session.tracks[0].soloed is False

    def test_solo_specific_track(self, tmp_project):
        """solo 2 toggles solo on track 2."""
        tmp_project.execute("addtrack")
        tmp_project.execute("solo 2")

        assert tmp_project.session.tracks[0].soloed is False
        assert tmp_project.session.tracks[1].soloed is True


class TestSelectedTracks:
    """Tests for selected_tracks() method."""

    def test_no_selection_returns_current(self, tmp_project):
        """With no selection, selected_tracks returns current track."""
        tmp_project.execute("addtrack")
        tmp_project.execute("tr 2")

        selected = tmp_project.session.selected_tracks()
        assert len(selected) == 1
        assert selected[0] is tmp_project.session.tracks[1]

    def test_selection_returns_selected(self, tmp_project):
        """With selection, selected_tracks returns selected tracks."""
        tmp_project.execute("addtrack")
        tmp_project.execute("addtrack")
        tmp_project.execute("ts 1,3")

        selected = tmp_project.session.selected_tracks()
        assert len(selected) == 2
        assert tmp_project.session.tracks[0] in selected
        assert tmp_project.session.tracks[2] in selected


class TestMultitrackPlayback:
    """Tests for multitrack playback with mute/solo."""

    def test_muted_track_not_played(self, tmp_project, sample_wav, mocker):
        """Muted tracks are excluded from playback."""
        mock_play = mocker.patch(
            "edway2.commands.playback.play_until_keypress", return_value=False
        )

        # Add audio to track 1
        tmp_project.execute(f"r {sample_wav}")

        # Mute track 1
        tmp_project.execute("mute")

        # Try to play - should fail because the only track is muted
        tmp_project.execute("1p")

        # Play should not have been called (no unmuted tracks with clips)
        mock_play.assert_not_called()

    def test_solo_plays_only_soloed(self, tmp_project, sample_wav, mocker):
        """Only soloed tracks play when any track is soloed."""
        mock_play = mocker.patch(
            "edway2.commands.playback.play_until_keypress", return_value=False
        )

        # Add audio to track 1
        tmp_project.execute(f"r {sample_wav}")

        # Add track 2 (empty)
        tmp_project.execute("addtrack")

        # Solo track 2 (which has no audio)
        tmp_project.execute("solo 2")

        # Play - should fail because only soloed track (2) has no clips
        tmp_project.execute("1p")

        # Play should not have been called
        mock_play.assert_not_called()

    def test_unsolo_allows_playback(self, tmp_project, sample_wav, mocker):
        """Unsoloing allows normal playback."""
        mock_play = mocker.patch(
            "edway2.commands.playback.play_until_keypress", return_value=False
        )

        tmp_project.execute(f"r {sample_wav}")
        tmp_project.execute("addtrack")
        tmp_project.execute("solo 2")  # solo empty track
        tmp_project.execute("solo 2")  # unsolo it

        tmp_project.execute("1p")

        # Now play should work
        mock_play.assert_called_once()
