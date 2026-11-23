from pathlib import Path
import shutil

from woomba.db import connect
from woomba.jobs import create_project
from woomba.media.clips import delete_clip
from woomba.media.import_clips import import_paths
from woomba.paths import db_path

FIXTURE = Path(__file__).parent / "fixtures" / "short_clean.mp4"


def test_delete_clip(tmp_path: Path) -> None:
    assert FIXTURE.exists()
    conn = connect(db_path(tmp_path))
    create_project(conn, tmp_path, "del-demo")
    timeline = import_paths(tmp_path, "del-demo", [FIXTURE])
    clip_id = timeline.clips[0].id
    remaining = delete_clip(tmp_path, "del-demo", clip_id)
    assert remaining == 0
