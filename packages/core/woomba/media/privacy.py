from __future__ import annotations

from pathlib import Path

from woomba.timeline import load_timeline, save_timeline


def apply_privacy_flags(
    library_root: Path,
    project_id: str,
    *,
    mute_all_keep: bool = False,
    blur_all_keep: bool = False,
    strip_metadata: bool = True,
) -> None:
    timeline = load_timeline(library_root, project_id)
    for segment in timeline.segments:
        if segment.state != "keep":
            continue
        if mute_all_keep:
            segment.mute = True
        if blur_all_keep:
            segment.blur_faces = True
    timeline.export.strip_metadata = strip_metadata
    save_timeline(library_root, timeline)
