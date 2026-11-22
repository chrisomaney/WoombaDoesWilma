from __future__ import annotations

import json
from pathlib import Path

from woomba.models import Timeline
from woomba.paths import project_dir


def timeline_path(library_root: Path, project_id: str) -> Path:
    return project_dir(library_root, project_id) / "timeline.json"


def load_timeline(library_root: Path, project_id: str) -> Timeline:
    path = timeline_path(library_root, project_id)
    if not path.exists():
        return Timeline(project_id=project_id)
    return Timeline.model_validate_json(path.read_text(encoding="utf-8"))


def save_timeline(library_root: Path, timeline: Timeline) -> Path:
    path = timeline_path(library_root, timeline.project_id)
    path.write_text(timeline.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return path


def write_sidecar(export_file: Path, timeline: Timeline) -> Path:
    sidecar = export_file.with_suffix(".timeline.json")
    sidecar.write_text(timeline.model_dump_json(indent=2) + "\n", encoding="utf-8")
    return sidecar
