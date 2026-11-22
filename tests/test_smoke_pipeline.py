from pathlib import Path

import pytest

from woomba.db import connect
from woomba.jobs import create_project, enqueue_job, get_job
from woomba.media.import_clips import import_paths
from woomba.models import JobStatus, JobType
from woomba.paths import db_path
from woomba.workers.runner import run_job

FIXTURE = Path(__file__).parent / "fixtures" / "silence_demo.mp4"


@pytest.mark.skipif(not FIXTURE.exists(), reason="Run scripts/make_fixture.sh first")
def test_import_roughcut_export_pipeline(tmp_path: Path) -> None:
    conn = connect(db_path(tmp_path))
    create_project(conn, tmp_path, "smoke")
    import_paths(tmp_path, "smoke", [FIXTURE])

    for job_type in (JobType.analyze, JobType.roughcut, JobType.export):
        job = enqueue_job(conn, "smoke", job_type)
        run_job(conn, tmp_path, job.id)
        assert get_job(conn, job.id).status == JobStatus.succeeded

    exports = list((tmp_path / "exports").glob("smoke-*.mp4"))
    assert exports
