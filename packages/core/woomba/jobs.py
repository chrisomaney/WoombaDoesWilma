from __future__ import annotations

import sqlite3
import uuid
from datetime import datetime, timezone

from woomba.models import Job, JobStatus, JobType, Project
from woomba.paths import project_dir
from woomba.timeline import save_timeline
from woomba.models import Timeline


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_project(conn: sqlite3.Connection, library_root, project_id: str, title: str | None = None) -> Project:
    now = _now()
    project = Project(id=project_id, title=title or project_id, created_at=now, updated_at=now)
    conn.execute(
        "INSERT INTO projects (id, title, created_at, updated_at) VALUES (?, ?, ?, ?)",
        (project.id, project.title, project.created_at, project.updated_at),
    )
    conn.commit()
    project_dir(library_root, project.id)
    save_timeline(library_root, Timeline(project_id=project.id))
    return project


def list_projects(conn: sqlite3.Connection) -> list[Project]:
    rows = conn.execute("SELECT * FROM projects ORDER BY created_at DESC").fetchall()
    return [Project(**dict(row)) for row in rows]


def get_project(conn: sqlite3.Connection, project_id: str) -> Project | None:
    row = conn.execute("SELECT * FROM projects WHERE id = ?", (project_id,)).fetchone()
    return Project(**dict(row)) if row else None


def enqueue_job(conn: sqlite3.Connection, project_id: str, job_type: JobType) -> Job:
    now = _now()
    job = Job(
        id=str(uuid.uuid4()),
        project_id=project_id,
        type=job_type,
        status=JobStatus.queued,
        progress=0.0,
        created_at=now,
        updated_at=now,
    )
    conn.execute(
        """
        INSERT INTO jobs (id, project_id, type, status, progress, error, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            job.id,
            job.project_id,
            job.type.value,
            job.status.value,
            job.progress,
            job.error,
            job.created_at,
            job.updated_at,
        ),
    )
    conn.commit()
    return job


def get_job(conn: sqlite3.Connection, job_id: str) -> Job | None:
    row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
    if not row:
        return None
    data = dict(row)
    data["type"] = JobType(data["type"])
    data["status"] = JobStatus(data["status"])
    return Job(**data)


def list_jobs(conn: sqlite3.Connection, project_id: str | None = None) -> list[Job]:
    if project_id:
        rows = conn.execute(
            "SELECT * FROM jobs WHERE project_id = ? ORDER BY created_at DESC",
            (project_id,),
        ).fetchall()
    else:
        rows = conn.execute("SELECT * FROM jobs ORDER BY created_at DESC").fetchall()
    jobs: list[Job] = []
    for row in rows:
        data = dict(row)
        data["type"] = JobType(data["type"])
        data["status"] = JobStatus(data["status"])
        jobs.append(Job(**data))
    return jobs


def update_job(
    conn: sqlite3.Connection,
    job_id: str,
    *,
    status: JobStatus | None = None,
    progress: float | None = None,
    error: str | None = None,
) -> Job:
    job = get_job(conn, job_id)
    if job is None:
        raise KeyError(f"Unknown job: {job_id}")
    if status is not None:
        job.status = status
    if progress is not None:
        job.progress = progress
    if error is not None:
        job.error = error
    job.updated_at = _now()
    conn.execute(
        """
        UPDATE jobs
        SET status = ?, progress = ?, error = ?, updated_at = ?
        WHERE id = ?
        """,
        (job.status.value, job.progress, job.error, job.updated_at, job.id),
    )
    conn.commit()
    return job


def next_queued_job(conn: sqlite3.Connection) -> Job | None:
    row = conn.execute(
        "SELECT * FROM jobs WHERE status = ? ORDER BY created_at ASC LIMIT 1",
        (JobStatus.queued.value,),
    ).fetchone()
    if not row:
        return None
    data = dict(row)
    data["type"] = JobType(data["type"])
    data["status"] = JobStatus(data["status"])
    return Job(**data)
