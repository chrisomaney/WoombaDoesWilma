from __future__ import annotations

import traceback
from pathlib import Path

from woomba.jobs import get_job, update_job
from woomba.media.export import export_project
from woomba.media.import_clips import discover_inbox, import_paths
from woomba.media.polish import apply_polish_defaults
from woomba.media.privacy import apply_privacy_flags
from woomba.media.probe import probe_clip
from woomba.media.proxy import ensure_proxy_and_peaks
from woomba.media.roughcut import build_roughcut
from woomba.media.silence import detect_silence
from woomba.models import JobStatus, JobType
from woomba.paths import project_dir
from woomba.timeline import load_timeline, save_timeline


def run_job(conn, library_root: Path, job_id: str) -> None:
    job = get_job(conn, job_id)
    if job is None:
        raise KeyError(job_id)
    if job.status == JobStatus.cancelled:
        return
    update_job(conn, job_id, status=JobStatus.running, progress=0.05)
    try:
        if job.type == JobType.import_clips:
            paths = discover_inbox(library_root)
            import_paths(library_root, job.project_id, paths)
        elif job.type == JobType.analyze:
            _analyze(library_root, job.project_id)
            update_job(conn, job_id, progress=0.7)
            ensure_proxy_and_peaks(library_root, job.project_id)
        elif job.type == JobType.roughcut:
            build_roughcut(library_root, job.project_id)
        elif job.type == JobType.auto_roughcut:
            _analyze(library_root, job.project_id)
            update_job(conn, job_id, progress=0.35)
            ensure_proxy_and_peaks(library_root, job.project_id)
            update_job(conn, job_id, progress=0.7)
            build_roughcut(library_root, job.project_id)
        elif job.type == JobType.proxy:
            ensure_proxy_and_peaks(library_root, job.project_id)
        elif job.type == JobType.polish:
            apply_polish_defaults(library_root, job.project_id)
        elif job.type == JobType.privacy:
            apply_privacy_flags(library_root, job.project_id)
        elif job.type == JobType.export:
            export_project(library_root, job.project_id)
        elif job.type == JobType.finish:
            _analyze(library_root, job.project_id)
            update_job(conn, job_id, progress=0.2)
            ensure_proxy_and_peaks(library_root, job.project_id)
            update_job(conn, job_id, progress=0.35)
            build_roughcut(library_root, job.project_id)
            update_job(conn, job_id, progress=0.55)
            apply_polish_defaults(library_root, job.project_id)
            timeline = load_timeline(library_root, job.project_id)
            timeline.export.loudnorm = True
            timeline.export.keep_only = True
            save_timeline(library_root, timeline)
            update_job(conn, job_id, progress=0.7)
            export_project(library_root, job.project_id)
        else:
            exhaustive = job.type
            raise ValueError(f"Unhandled job type: {exhaustive}")
        update_job(conn, job_id, status=JobStatus.succeeded, progress=1.0, error=None)
    except Exception as exc:  # noqa: BLE001 - persist failure onto job row
        update_job(conn, job_id, status=JobStatus.failed, error=str(exc))
        log_path = project_dir(library_root, job.project_id) / "logs" / f"{job_id}.log"
        log_path.write_text(traceback.format_exc(), encoding="utf-8")


def _analyze(library_root: Path, project_id: str) -> None:
    timeline = load_timeline(library_root, project_id)
    project = project_dir(library_root, project_id)
    for clip in timeline.clips:
        if clip.error:
            continue
        abs_path = project / clip.path
        try:
            info = probe_clip(abs_path)
            clip.duration_ms = info.duration_ms
            clip.width = info.width
            clip.height = info.height
            clip.codec = info.codec
            clip.has_audio = info.has_audio
            points = {0, clip.duration_ms}
            if clip.has_audio:
                for gap in detect_silence(abs_path):
                    points.add(gap.start_ms)
                    points.add(gap.end_ms)
            timeline.snap_points_ms[clip.id] = sorted(points)
        except Exception as exc:  # noqa: BLE001
            clip.error = str(exc)
    save_timeline(library_root, timeline)
