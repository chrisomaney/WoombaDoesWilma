from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    queued = "queued"
    running = "running"
    succeeded = "succeeded"
    failed = "failed"
    cancelled = "cancelled"


class JobType(str, Enum):
    import_clips = "import"
    analyze = "analyze"
    roughcut = "roughcut"
    auto_roughcut = "auto_roughcut"
    polish = "polish"
    privacy = "privacy"
    export = "export"


class Clip(BaseModel):
    id: str
    path: str
    duration_ms: int = 0
    width: int | None = None
    height: int | None = None
    codec: str | None = None
    has_audio: bool = True
    error: str | None = None


class Segment(BaseModel):
    id: str
    clip_id: str
    in_ms: int
    out_ms: int
    state: Literal["keep", "cut"] = "keep"
    mute: bool = False
    blur_faces: bool = False


class ExportSettings(BaseModel):
    codec: Literal["h264", "h265"] = "h264"
    strip_metadata: bool = True
    loudnorm: bool = False
    keep_only: bool = True


class Timeline(BaseModel):
    project_id: str
    version: int = 1
    clips: list[Clip] = Field(default_factory=list)
    segments: list[Segment] = Field(default_factory=list)
    export: ExportSettings = Field(default_factory=ExportSettings)
    # Per-clip silence / boundary snap points in milliseconds
    snap_points_ms: dict[str, list[int]] = Field(default_factory=dict)


class Project(BaseModel):
    id: str
    title: str
    created_at: str
    updated_at: str


class Job(BaseModel):
    id: str
    project_id: str
    type: JobType
    status: JobStatus
    progress: float = 0.0
    error: str | None = None
    created_at: str
    updated_at: str
