from __future__ import annotations

import shutil
import subprocess
import uuid
from pathlib import Path

from woomba.media.probe import probe_clip
from woomba.models import Clip, Timeline
from woomba.paths import project_dir
from woomba.timeline import load_timeline, save_timeline

VIDEO_EXTS = {".mp4", ".mov", ".mkv", ".m4v", ".webm", ".avi"}


def _copy_stripped(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(src),
        "-map_metadata",
        "-1",
        "-c",
        "copy",
        str(dest),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        # Fall back to byte copy if remux fails (odd containers).
        shutil.copy2(src, dest)


def import_paths(library_root: Path, project_id: str, sources: list[Path]) -> Timeline:
    project = project_dir(library_root, project_id)
    timeline = load_timeline(library_root, project_id)
    for src in sources:
        src = src.expanduser().resolve()
        if not src.exists() or src.suffix.lower() not in VIDEO_EXTS:
            continue
        clip_id = f"c_{uuid.uuid4().hex[:8]}"
        dest_name = f"{clip_id}{src.suffix.lower()}"
        dest = project / "sources" / dest_name
        _copy_stripped(src, dest)
        try:
            info = probe_clip(dest)
            clip = Clip(
                id=clip_id,
                path=f"sources/{dest_name}",
                duration_ms=info.duration_ms,
                width=info.width,
                height=info.height,
                codec=info.codec,
                has_audio=info.has_audio,
            )
        except Exception as exc:  # noqa: BLE001 - capture probe failures per clip
            clip = Clip(id=clip_id, path=f"sources/{dest_name}", error=str(exc))
        timeline.clips.append(clip)
    save_timeline(library_root, timeline)
    return timeline


def discover_inbox(library_root: Path) -> list[Path]:
    inbox = library_root / "inbox"
    if not inbox.exists():
        return []
    return sorted(
        p for p in inbox.iterdir() if p.is_file() and p.suffix.lower() in VIDEO_EXTS
    )
