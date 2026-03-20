"""Tests for edway2 Project."""

import pytest
from pathlib import Path

from edway2.project import Project
from edway2.session import Session


def test_create_project_folder_structure(tmp_path):
    """Test project creation creates correct folder structure."""
    proj = Project.create(tmp_path / "myproject")

    assert proj.path.exists()
    assert (proj.path / "myproject.edway").exists()
    assert (proj.path / "sources").is_dir()
    assert (proj.path / "renders").is_dir()
    assert (proj.path / ".git").is_dir()


def test_create_project_has_session(tmp_path):
    """Test created project has a session."""
    proj = Project.create(tmp_path / "test")
    assert proj.session is not None
    assert proj.session.timeline.name == "test"


def test_create_project_has_git_repo(tmp_path):
    """Test created project has initialized git repo."""
    proj = Project.create(tmp_path / "test")
    assert proj.repo is not None
    # Should have at least one commit
    assert proj.repo.head.is_valid()


def test_create_project_initial_commit(tmp_path):
    """Test created project has initial commit."""
    proj = Project.create(tmp_path / "test")
    commits = list(proj.repo.iter_commits())
    assert len(commits) == 1
    assert "Initial project" in commits[0].message


def test_open_project(tmp_path):
    """Test opening an existing project."""
    # Create project
    Project.create(tmp_path / "myproject")

    # Open it
    proj = Project.open(tmp_path / "myproject")
    assert proj.path == tmp_path / "myproject"
    assert proj.session.timeline.name == "myproject"


def test_open_nonexistent_raises(tmp_path):
    """Test opening nonexistent project raises."""
    with pytest.raises(FileNotFoundError):
        Project.open(tmp_path / "nonexistent")


def test_save_creates_commit(tmp_path):
    """Test saving creates a git commit."""
    proj = Project.create(tmp_path / "test")
    initial_commits = len(list(proj.repo.iter_commits()))

    proj.session.marks["a"] = 5.0
    proj.save("added mark a")

    commits = list(proj.repo.iter_commits())
    assert len(commits) == initial_commits + 1
    assert "added mark a" in commits[0].message


def test_save_and_load_preserves_session(tmp_path):
    """Test save and load preserves session state."""
    proj = Project.create(tmp_path / "test")
    proj.session.marks["a"] = 5.0
    proj.session.current_position = 10.0
    proj.save()

    proj2 = Project.open(tmp_path / "test")
    assert proj2.session.marks["a"] == 5.0
    assert proj2.session.current_position == 10.0


def test_dirty_flag(tmp_path):
    """Test dirty flag tracking."""
    proj = Project.create(tmp_path / "test")
    assert not proj.is_dirty

    proj.mark_dirty()
    assert proj.is_dirty

    proj.save()
    assert not proj.is_dirty


def test_sources_dir(tmp_path):
    """Test sources_dir property."""
    proj = Project.create(tmp_path / "test")
    assert proj.sources_dir == tmp_path / "test" / "sources"


def test_renders_dir(tmp_path):
    """Test renders_dir property."""
    proj = Project.create(tmp_path / "test")
    assert proj.renders_dir == tmp_path / "test" / "renders"


def test_session_file(tmp_path):
    """Test session_file property."""
    proj = Project.create(tmp_path / "test")
    assert proj.session_file == tmp_path / "test" / "test.edway"


def test_resolve_path_inside_project(tmp_path):
    """Test resolve_path for file inside project."""
    proj = Project.create(tmp_path / "test")
    inside = proj.sources_dir / "audio.wav"
    resolved = proj.resolve_path(inside)
    assert resolved == "sources/audio.wav"


def test_resolve_path_outside_project(tmp_path):
    """Test resolve_path for file outside project."""
    proj = Project.create(tmp_path / "test")
    outside = tmp_path / "other" / "audio.wav"
    resolved = proj.resolve_path(outside)
    assert resolved == str(outside.resolve())


def test_undo(tmp_path):
    """Test undo restores previous state."""
    proj = Project.create(tmp_path / "test")

    # Make a change and save
    proj.session.marks["a"] = 5.0
    proj.save("added mark")

    # Make another change and save
    proj.session.marks["b"] = 10.0
    proj.save("added another mark")

    # Undo
    assert proj.undo()
    assert "a" in proj.session.marks
    # Note: undo uses git checkout which affects the file,
    # but doesn't remove commits. The session is reloaded.


def test_undo_at_initial_fails(tmp_path):
    """Test undo at initial commit returns False."""
    proj = Project.create(tmp_path / "test")
    # At initial commit, can't undo further
    assert not proj.undo()
