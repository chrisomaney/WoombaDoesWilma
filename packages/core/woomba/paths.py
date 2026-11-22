from __future__ import annotations

from pathlib import Path


LIBRARY_SUBDIRS = ("inbox", "projects", "exports")


def ensure_library_layout(library_root: Path) -> Path:
    root = library_root.expanduser().resolve()
    root.mkdir(parents=True, exist_ok=True)
    for name in LIBRARY_SUBDIRS:
        (root / name).mkdir(parents=True, exist_ok=True)
    return root


def inbox_dir(library_root: Path) -> Path:
    return ensure_library_layout(library_root) / "inbox"


def projects_dir(library_root: Path) -> Path:
    return ensure_library_layout(library_root) / "projects"


def exports_dir(library_root: Path) -> Path:
    return ensure_library_layout(library_root) / "exports"


def project_dir(library_root: Path, project_id: str) -> Path:
    path = projects_dir(library_root) / project_id
    for name in ("sources", "proxies", "jobs", "logs"):
        (path / name).mkdir(parents=True, exist_ok=True)
    return path


def db_path(library_root: Path) -> Path:
    return ensure_library_layout(library_root) / "studio.db"


def consent_path(library_root: Path) -> Path:
    return ensure_library_layout(library_root) / ".consent.json"
