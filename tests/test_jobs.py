from pathlib import Path

from woomba.db import connect
from woomba.jobs import create_project, enqueue_job, get_job, list_projects, update_job
from woomba.models import JobStatus, JobType
from woomba.paths import db_path


def test_create_project_and_enqueue(tmp_path: Path) -> None:
    conn = connect(db_path(tmp_path))
    project = create_project(conn, tmp_path, "weekend-01", title="Weekend")
    assert project.id == "weekend-01"
    assert list_projects(conn)[0].title == "Weekend"

    job = enqueue_job(conn, project.id, JobType.analyze)
    assert job.status == JobStatus.queued
    updated = update_job(conn, job.id, status=JobStatus.running, progress=0.5)
    assert updated.progress == 0.5
    assert get_job(conn, job.id).status == JobStatus.running
