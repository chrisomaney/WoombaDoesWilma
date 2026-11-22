from pathlib import Path

import pytest

from woomba.db import connect
from woomba.jobs import create_project
from woomba.media.import_clips import import_paths
from woomba.media.roughcut import build_roughcut
from woomba.paths import db_path

FIXTURE = Path(__file__).parent / "fixtures" / "silence_demo.mp4"


@pytest.mark.skipif(not FIXTURE.exists(), reason="Run scripts/make_fixture.sh first")
def test_roughcut_marks_keep_and_cut(tmp_path: Path) -> None:
    conn = connect(db_path(tmp_path))
    create_project(conn, tmp_path, "cut-demo")
    import_paths(tmp_path, "cut-demo", [FIXTURE])
    timeline = build_roughcut(tmp_path, "cut-demo", noise_db=-35.0)
    states = {s.state for s in timeline.segments}
    assert "keep" in states
    assert "cut" in states
