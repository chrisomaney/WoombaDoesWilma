from __future__ import annotations

import re

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from woomba.consent import CONSENT_TEXT, accept_consent, read_consent, require_consent
from woomba.jobs import create_project, enqueue_job, get_job, get_project, list_jobs, list_projects
from woomba.models import JobType, Timeline
from woomba.paths import ensure_library_layout
from woomba.settings import get_settings
from woomba.timeline import load_timeline, save_timeline
from woomba_api.deps import get_conn

app = FastAPI(title="WoombaDoesWilma", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

PROJECT_ID_RE = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9_-]{0,63}$")


class ConsentAcceptBody(BaseModel):
    accept: bool = True


class CreateProjectBody(BaseModel):
    id: str = Field(min_length=1, max_length=64)
    title: str | None = None


class EnqueueJobBody(BaseModel):
    type: JobType


class TimelineUpdateBody(BaseModel):
    timeline: dict


@app.on_event("startup")
def _startup() -> None:
    settings = get_settings()
    ensure_library_layout(settings.resolve_library())
    get_conn()


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "woomba"}


@app.get("/api/consent")
def get_consent() -> dict:
    settings = get_settings()
    record = read_consent(settings.resolve_library())
    return {
        "accepted": record.accepted,
        "version": record.version,
        "accepted_at": record.accepted_at,
        "text": record.text or CONSENT_TEXT,
    }


@app.post("/api/consent")
def post_consent(body: ConsentAcceptBody) -> dict:
    if not body.accept:
        raise HTTPException(status_code=400, detail="Consent must be accepted to continue.")
    settings = get_settings()
    record = accept_consent(settings.resolve_library())
    return {
        "accepted": record.accepted,
        "version": record.version,
        "accepted_at": record.accepted_at,
        "text": record.text,
    }


def _require() -> None:
    settings = get_settings()
    try:
        require_consent(settings.resolve_library())
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc


@app.get("/api/projects")
def api_list_projects() -> list[dict]:
    _require()
    return [p.model_dump() for p in list_projects(get_conn())]


@app.post("/api/projects")
def api_create_project(body: CreateProjectBody) -> dict:
    _require()
    if not PROJECT_ID_RE.match(body.id):
        raise HTTPException(status_code=400, detail="Invalid project id")
    conn = get_conn()
    if get_project(conn, body.id):
        raise HTTPException(status_code=409, detail="Project already exists")
    settings = get_settings()
    project = create_project(conn, settings.resolve_library(), body.id, body.title)
    return project.model_dump()


@app.get("/api/projects/{project_id}")
def api_get_project(project_id: str) -> dict:
    _require()
    project = get_project(get_conn(), project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    settings = get_settings()
    timeline = load_timeline(settings.resolve_library(), project_id)
    return {"project": project.model_dump(), "timeline": timeline.model_dump()}


@app.put("/api/projects/{project_id}/timeline")
def api_put_timeline(project_id: str, body: TimelineUpdateBody) -> dict:
    _require()
    if not get_project(get_conn(), project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    settings = get_settings()
    timeline = Timeline.model_validate({**body.timeline, "project_id": project_id})
    save_timeline(settings.resolve_library(), timeline)
    return timeline.model_dump()


@app.get("/api/projects/{project_id}/jobs")
def api_list_project_jobs(project_id: str) -> list[dict]:
    _require()
    return [j.model_dump() for j in list_jobs(get_conn(), project_id)]


@app.post("/api/projects/{project_id}/jobs")
def api_enqueue_job(project_id: str, body: EnqueueJobBody) -> dict:
    _require()
    if not get_project(get_conn(), project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    job = enqueue_job(get_conn(), project_id, body.type)
    return job.model_dump()


@app.get("/api/jobs/{job_id}")
def api_get_job(job_id: str) -> dict:
    _require()
    job = get_job(get_conn(), job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job.model_dump()
