from __future__ import annotations

import asyncio
import json
import mimetypes
import re
import tempfile
from pathlib import Path
from typing import Literal

from fastapi import Depends, FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from pydantic import BaseModel, Field

from woomba.consent import CONSENT_TEXT, accept_consent, read_consent, require_consent
from woomba.jobs import create_project, enqueue_job, get_job, get_project, list_jobs, list_projects
from woomba.media.import_clips import (
    VIDEO_EXTS,
    discover_inbox,
    import_paths,
    inbox_summary,
    register_existing_sources,
)
from woomba.models import JobStatus, JobType, Timeline
from woomba.media.export import list_exports
from woomba.paths import ensure_library_layout, project_dir
from woomba.settings import get_settings
from woomba.timeline import load_timeline, save_timeline
from woomba_api.auth import enforce_token
from woomba_api.deps import get_conn
from woomba_api.runner import cancel_job, start_worker

app = FastAPI(title="WoombaDoesWilma", version="0.1.0", dependencies=[Depends(enforce_token)])
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


class ImportBody(BaseModel):
    source: Literal["inbox", "sources"] = "inbox"


@app.on_event("startup")
def _startup() -> None:
    settings = get_settings()
    root = ensure_library_layout(settings.resolve_library())
    get_conn()
    start_worker(root)


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


@app.get("/api/library")
def api_library() -> dict:
    _require()
    settings = get_settings()
    root = ensure_library_layout(settings.resolve_library())
    return {
        "library": str(root),
        "inbox": str(root / "inbox"),
        "projects": str(root / "projects"),
        "exports": str(root / "exports"),
        "inbox_files": inbox_summary(root),
        "recent_exports": list_exports(root)[:10],
    }


@app.get("/api/projects/{project_id}/exports")
def api_project_exports(project_id: str) -> dict:
    _require()
    if not get_project(get_conn(), project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    settings = get_settings()
    root = ensure_library_layout(settings.resolve_library())
    return {"exports_dir": str(root / "exports"), "items": list_exports(root, project_id)}


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


@app.post("/api/projects/{project_id}/import")
def api_import_clips(project_id: str, body: ImportBody) -> dict:
    _require()
    if not get_project(get_conn(), project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    settings = get_settings()
    root = settings.resolve_library()
    before = len(load_timeline(root, project_id).clips)
    if body.source == "inbox":
        paths = discover_inbox(root)
        if not paths:
            raise HTTPException(status_code=400, detail="Inbox is empty — drop .mp4 files into inbox first")
        timeline = import_paths(root, project_id, paths)
    else:
        timeline = register_existing_sources(root, project_id)
        if len(timeline.clips) == before:
            raise HTTPException(
                status_code=400,
                detail="No new clips in sources/ — drop files there or use inbox import",
            )
    return {
        "added": len(timeline.clips) - before,
        "clip_count": len(timeline.clips),
        "timeline": timeline.model_dump(),
    }


@app.post("/api/projects/{project_id}/upload")
async def api_upload_clips(project_id: str, files: list[UploadFile] = File(...)) -> dict:
    _require()
    if not get_project(get_conn(), project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")

    settings = get_settings()
    root = settings.resolve_library()
    before = len(load_timeline(root, project_id).clips)
    saved: list[Path] = []
    with tempfile.TemporaryDirectory(prefix="woomba-upload-") as tmp:
        tmp_path = Path(tmp)
        for upload in files:
            name = Path(upload.filename or "clip.bin").name
            suffix = Path(name).suffix.lower()
            if suffix not in VIDEO_EXTS:
                continue
            dest = tmp_path / name
            dest.write_bytes(await upload.read())
            saved.append(dest)
        if not saved:
            raise HTTPException(status_code=400, detail="No supported video files in upload")
        timeline = import_paths(root, project_id, saved)
    return {
        "added": len(timeline.clips) - before,
        "clip_count": len(timeline.clips),
        "timeline": timeline.model_dump(),
    }


@app.get("/api/projects/{project_id}/media/{media_path:path}")
def api_project_media(project_id: str, media_path: str) -> FileResponse:
    _require()
    if not get_project(get_conn(), project_id):
        raise HTTPException(status_code=404, detail="Project not found")
    settings = get_settings()
    project = project_dir(settings.resolve_library(), project_id).resolve()
    candidate = (project / media_path).resolve()
    try:
        candidate.relative_to(project)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Invalid media path") from exc
    if not candidate.is_file():
        raise HTTPException(status_code=404, detail="Media not found")
    mime, _ = mimetypes.guess_type(str(candidate))
    return FileResponse(candidate, media_type=mime or "application/octet-stream")


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


@app.post("/api/jobs/{job_id}/cancel")
def api_cancel_job(job_id: str) -> dict:
    _require()
    job = get_job(get_conn(), job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    if job.status in {JobStatus.succeeded, JobStatus.failed, JobStatus.cancelled}:
        return job.model_dump()
    cancel_job(get_conn(), job_id)
    updated = get_job(get_conn(), job_id)
    assert updated is not None
    return updated.model_dump()


@app.get("/api/jobs/{job_id}/events")
async def api_job_events(job_id: str) -> StreamingResponse:
    _require()

    async def gen():
        while True:
            job = get_job(get_conn(), job_id)
            if not job:
                yield f"data: {json.dumps({'error': 'not_found'})}\n\n"
                break
            payload = job.model_dump()
            # enums -> values for JSON
            payload["type"] = job.type.value
            payload["status"] = job.status.value
            yield f"data: {json.dumps(payload)}\n\n"
            if job.status in {JobStatus.succeeded, JobStatus.failed, JobStatus.cancelled}:
                break
            await asyncio.sleep(0.5)

    return StreamingResponse(gen(), media_type="text/event-stream")
