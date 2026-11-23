from __future__ import annotations

import uuid
from pathlib import Path

from woomba.media.silence import detect_silence, invert_to_keep_ranges
from woomba.models import Segment, Timeline
from woomba.paths import project_dir
from woomba.timeline import load_timeline, save_timeline


def build_roughcut(
    library_root: Path,
    project_id: str,
    *,
    noise_db: float = -35.0,
) -> Timeline:
    timeline = load_timeline(library_root, project_id)
    project = project_dir(library_root, project_id)
    segments: list[Segment] = []
    for clip in timeline.clips:
        if clip.error or clip.duration_ms <= 0:
            continue
        abs_path = project / clip.path
        silence = detect_silence(abs_path, noise_db=noise_db) if clip.has_audio else []
        points = {0, clip.duration_ms}
        for gap in silence:
            points.add(gap.start_ms)
            points.add(gap.end_ms)
        timeline.snap_points_ms[clip.id] = sorted(points)
        keep_ranges = invert_to_keep_ranges(clip.duration_ms, silence)
        if not keep_ranges:
            keep_ranges = []
            # No keep ranges means all silence — mark full clip cut.
            segments.append(
                Segment(
                    id=f"s_{uuid.uuid4().hex[:8]}",
                    clip_id=clip.id,
                    in_ms=0,
                    out_ms=clip.duration_ms,
                    state="cut",
                )
            )
            continue

        cursor = 0
        for keep in keep_ranges:
            if keep.start_ms > cursor:
                segments.append(
                    Segment(
                        id=f"s_{uuid.uuid4().hex[:8]}",
                        clip_id=clip.id,
                        in_ms=cursor,
                        out_ms=keep.start_ms,
                        state="cut",
                    )
                )
            segments.append(
                Segment(
                    id=f"s_{uuid.uuid4().hex[:8]}",
                    clip_id=clip.id,
                    in_ms=keep.start_ms,
                    out_ms=keep.end_ms,
                    state="keep",
                )
            )
            cursor = keep.end_ms
        if cursor < clip.duration_ms:
            segments.append(
                Segment(
                    id=f"s_{uuid.uuid4().hex[:8]}",
                    clip_id=clip.id,
                    in_ms=cursor,
                    out_ms=clip.duration_ms,
                    state="cut",
                )
            )

    timeline.segments = segments
    save_timeline(library_root, timeline)
    return timeline
