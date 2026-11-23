from pathlib import Path
import shutil

from woomba.db import connect
from woomba.jobs import create_project
from woomba.media.import_clips import import_paths, register_existing_sources
from woomba.paths import db_path, project_dir

FIXTURE = Path(__file__).parent / "fixtures" / "short_clean.mp4"


def test_register_existing_sources(tmp_path: Path) -> None:
    assert FIXTURE.exists()
    conn = connect(db_path(tmp_path))
    create_project(conn, tmp_path, "drop-demo")
    sources = project_dir(tmp_path, "drop-demo") / "sources"
    shutil.copy2(FIXTURE, sources / "my-clip.mp4")

    timeline = register_existing_sources(tmp_path, "drop-demo")
    assert len(timeline.clips) == 1
    assert timeline.clips[0].path.endswith("my-clip.mp4")
    assert timeline.clips[0].duration_ms > 0

    # Second pass is idempotent
    again = register_existing_sources(tmp_path, "drop-demo")
    assert len(again.clips) == 1


def test_import_from_inbox_paths(tmp_path: Path) -> None:
    assert FIXTURE.exists()
    conn = connect(db_path(tmp_path))
    create_project(conn, tmp_path, "inbox-demo")
    timeline = import_paths(tmp_path, "inbox-demo", [FIXTURE])
    assert len(timeline.clips) == 1
