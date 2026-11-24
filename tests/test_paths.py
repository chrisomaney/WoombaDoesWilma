from pathlib import Path

from woomba.paths import ensure_library_layout, inbox_dir, project_dir


def test_ensure_library_layout(tmp_path: Path) -> None:
    root = ensure_library_layout(tmp_path / "lib")
    assert (root / "inbox").is_dir()
    assert (root / "projects").is_dir()
    assert (root / "exports").is_dir()
    assert (root / "assets" / "backgrounds").is_dir()
    assert (root / "assets" / "faces").is_dir()
    assert inbox_dir(root).is_dir()


def test_project_dir_creates_subfolders(tmp_path: Path) -> None:
    root = ensure_library_layout(tmp_path / "lib")
    project = project_dir(root, "weekend-01")
    assert (project / "sources").is_dir()
    assert (project / "proxies").is_dir()
    assert (project / "jobs").is_dir()
    assert (project / "logs").is_dir()
