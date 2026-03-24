"""Tests for export commands (w)."""

import pytest
import soundfile as sf


class TestWrite:
    """Tests for w (write/export) command."""

    def test_export_with_filename(self, tmp_project, sample_wav, capsys):
        """w output.wav exports to that file."""
        tmp_project.execute(f"r {sample_wav}")

        tmp_project.execute("w output.wav")

        output_path = tmp_project.path / "output.wav"
        assert output_path.exists()

        output = capsys.readouterr().out
        assert "wrote:" in output
        assert "output.wav" in output

    def test_export_default_filename(self, tmp_project, sample_wav, capsys):
        """w with no arg uses session name."""
        tmp_project.execute(f"r {sample_wav}")
        tmp_project.session.name = "my_session"

        tmp_project.execute("w")

        output_path = tmp_project.path / "my_session.wav"
        assert output_path.exists()

    def test_export_adds_extension(self, tmp_project, sample_wav, capsys):
        """w without extension adds .wav."""
        tmp_project.execute(f"r {sample_wav}")

        tmp_project.execute("w noext")

        output_path = tmp_project.path / "noext.wav"
        assert output_path.exists()

    def test_export_no_audio(self, tmp_project, capsys):
        """w with no audio shows error."""
        tmp_project.execute("w output.wav")

        output = capsys.readouterr().out
        assert "no audio to export" in output

    def test_export_muted_track(self, tmp_project, sample_wav, capsys):
        """w with all tracks muted shows error."""
        tmp_project.execute(f"r {sample_wav}")
        tmp_project.execute("mute")  # mute current track

        tmp_project.execute("w output.wav")

        output = capsys.readouterr().out
        assert "nothing to export" in output or "muted" in output

    def test_exported_audio_valid(self, tmp_project, sample_wav):
        """Exported audio is valid and has correct duration."""
        tmp_project.execute(f"r {sample_wav}")

        tmp_project.execute("w output.wav")

        output_path = tmp_project.path / "output.wav"
        info = sf.info(str(output_path))

        # Original sample is 1 second
        assert info.duration == pytest.approx(1.0, abs=0.1)

    def test_export_flac(self, tmp_project, sample_wav, capsys):
        """w output.flac exports as FLAC."""
        tmp_project.execute(f"r {sample_wav}")

        tmp_project.execute("w output.flac")

        output_path = tmp_project.path / "output.flac"
        assert output_path.exists()

        info = sf.info(str(output_path))
        assert info.format == "FLAC"


class TestWriteMultitrack:
    """Tests for multitrack export."""

    def test_export_mixes_tracks(self, tmp_project, sample_wav, mocker):
        """Export mixes multiple tracks."""
        # Add audio to two tracks
        tmp_project.execute(f"r {sample_wav}")
        tmp_project.execute("addtrack")
        tmp_project.execute("tr 2")
        tmp_project.execute(f"r {sample_wav}")

        tmp_project.execute("w mixed.wav")

        output_path = tmp_project.path / "mixed.wav"
        assert output_path.exists()

    def test_export_respects_solo(self, tmp_project, sample_wav):
        """Export only includes soloed tracks."""
        tmp_project.execute(f"r {sample_wav}")
        tmp_project.execute("addtrack")
        tmp_project.execute("tr 2")
        tmp_project.execute(f"r {sample_wav}")

        # Solo track 1 only
        tmp_project.execute("solo 1")

        tmp_project.execute("w soloed.wav")

        output_path = tmp_project.path / "soloed.wav"
        assert output_path.exists()
