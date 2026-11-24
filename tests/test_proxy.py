from pathlib import Path

from woomba.db import connect
from woomba.jobs import create_project
from woomba.media.import_clips import import_paths
from woomba.media.proxy import ensure_proxy_and_peaks, peaks_rel_path, proxy_rel_path
from woomba.paths import db_path, project_dir

FIXTURE = Path(__file__).parent / "fixtures" / "short_clean.mp4"


def test_proxy_and_peaks(tmp_path: Path) -> None:
    assert FIXTURE.exists()
    conn = connect(db_path(tmp_path))
    create_project(conn, tmp_path, "proxy-demo")
    timeline = import_paths(tmp_path, "proxy-demo", [FIXTURE])
    clip_id = timeline.clips[0].id
    updated = ensure_proxy_and_peaks(tmp_path, "proxy-demo", clip_id)
    clip = updated.clips[0]
    assert clip.proxy_path == proxy_rel_path(clip_id)
    assert clip.waveform_path == peaks_rel_path(clip_id)
    project = project_dir(tmp_path, "proxy-demo")
    assert (project / clip.proxy_path).is_file()
    assert (project / clip.waveform_path).is_file()
