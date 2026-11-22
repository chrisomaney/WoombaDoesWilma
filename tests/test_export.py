from pathlib import Path

import pytest

from woomba.db import connect
from woomba.jobs import create_project
from woomba.media.export import export_project
from woomba.media.import_clips import import_paths
from woomba.media.roughcut import build_roughcut
from woomba.paths import db_path

FIXTURE = Path(__file__).parent / "fixtures" / "short_clean.mp4"


@pytest.mark.skipif(not FIXTURE.exists(), reason="Run scripts/make_fixture.sh first")
def test_export_writes_mp4_and_sidecar(tmp_path: Path) -> None:
    conn = connect(db_path(tmp_path))
    create_project(conn, tmp_path, "exp")
    import_paths(tmp_path, "exp", [FIXTURE])
    build_roughcut(tmp_path, "exp")
    out = export_project(tmp_path, "exp")
    assert out.exists()
    assert out.suffix == ".mp4"
    assert out.with_suffix(".timeline.json").exists()
