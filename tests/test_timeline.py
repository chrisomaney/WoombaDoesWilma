from pathlib import Path

from woomba.models import Clip, Segment, Timeline
from woomba.timeline import load_timeline, save_timeline


def test_timeline_round_trip(tmp_path: Path) -> None:
    timeline = Timeline(
        project_id="weekend-01",
        clips=[Clip(id="c1", path="sources/a.mp4", duration_ms=1000)],
        segments=[Segment(id="s1", clip_id="c1", in_ms=0, out_ms=1000, state="keep")],
    )
    save_timeline(tmp_path, timeline)
    loaded = load_timeline(tmp_path, "weekend-01")
    assert loaded.project_id == "weekend-01"
    assert loaded.clips[0].path == "sources/a.mp4"
    assert loaded.segments[0].state == "keep"
