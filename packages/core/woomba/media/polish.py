from __future__ import annotations

from pathlib import Path

from woomba.timeline import load_timeline, save_timeline


def apply_polish_defaults(library_root: Path, project_id: str) -> None:
    """v1 marker job: confirms polish step ran; loudnorm applied during export later."""
    timeline = load_timeline(library_root, project_id)
    timeline.version = max(timeline.version, 1)
    save_timeline(library_root, timeline)
