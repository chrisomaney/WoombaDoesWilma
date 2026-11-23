from __future__ import annotations

from pathlib import Path

from woomba.paths import project_dir
from woomba.timeline import load_timeline, save_timeline


def delete_clip(library_root: Path, project_id: str, clip_id: str, *, remove_file: bool = True) -> int:
    timeline = load_timeline(library_root, project_id)
    clip = next((c for c in timeline.clips if c.id == clip_id), None)
    if clip is None:
        raise KeyError(clip_id)
    timeline.clips = [c for c in timeline.clips if c.id != clip_id]
    timeline.segments = [s for s in timeline.segments if s.clip_id != clip_id]
    timeline.snap_points_ms.pop(clip_id, None)
    save_timeline(library_root, timeline)
    if remove_file:
        path = project_dir(library_root, project_id) / clip.path
        if path.is_file():
            path.unlink()
    return len(timeline.clips)
