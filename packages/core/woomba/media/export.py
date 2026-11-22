from __future__ import annotations

import shutil
import subprocess
import tempfile
import time
from pathlib import Path

from woomba.models import Timeline
from woomba.paths import exports_dir, project_dir
from woomba.timeline import load_timeline, write_sidecar


def _disk_free_bytes(path: Path) -> int:
    return shutil.disk_usage(path).free


def export_project(library_root: Path, project_id: str) -> Path:
    timeline = load_timeline(library_root, project_id)
    project = project_dir(library_root, project_id)
    out_dir = exports_dir(library_root)
    if _disk_free_bytes(out_dir) < 200 * 1024 * 1024:
        raise RuntimeError("Less than 200MB free disk space; aborting export.")

    keep = [s for s in timeline.segments if s.state == "keep"]
    if not keep:
        # If no roughcut yet, keep whole clips.
        keep_clips = [c for c in timeline.clips if not c.error]
        if not keep_clips:
            raise RuntimeError("No clips available to export.")
        stamp = time.strftime("%Y%m%d-%H%M%S")
        out = out_dir / f"{project_id}-{stamp}.mp4"
        first = project / keep_clips[0].path
        _render_file(first, out, timeline, mute=False, blur=False)
        write_sidecar(out, timeline)
        return out

    stamp = time.strftime("%Y%m%d-%H%M%S")
    out = out_dir / f"{project_id}-{stamp}.mp4"
    with tempfile.TemporaryDirectory(prefix="woomba-export-") as tmp:
        tmp_path = Path(tmp)
        parts: list[Path] = []
        for index, segment in enumerate(keep):
            clip = next((c for c in timeline.clips if c.id == segment.clip_id), None)
            if clip is None:
                continue
            src = project / clip.path
            part = tmp_path / f"part-{index:04d}.mp4"
            _render_segment(src, part, segment.in_ms, segment.out_ms, timeline, segment.mute, segment.blur_faces)
            parts.append(part)
        if not parts:
            raise RuntimeError("No keep segments could be rendered.")
        _concat(parts, out, strip_metadata=timeline.export.strip_metadata)
    write_sidecar(out, timeline)
    return out


def _codec_args(timeline: Timeline) -> list[str]:
    if timeline.export.codec == "h265":
        return ["-c:v", "libx265", "-tag:v", "hvc1"]
    return ["-c:v", "libx264", "-pix_fmt", "yuv420p"]


def _render_file(src: Path, dest: Path, timeline: Timeline, *, mute: bool, blur: bool) -> None:
    filters: list[str] = []
    if blur:
        filters.append("boxblur=8:1")
    cmd = ["ffmpeg", "-y", "-i", str(src), *_codec_args(timeline), "-c:a", "aac"]
    if filters:
        cmd.extend(["-vf", ",".join(filters)])
    if mute:
        cmd.extend(["-af", "volume=0"])
    if timeline.export.strip_metadata:
        cmd.extend(["-map_metadata", "-1"])
    cmd.append(str(dest))
    subprocess.run(cmd, check=True, capture_output=True, text=True)


def _render_segment(
    src: Path,
    dest: Path,
    in_ms: int,
    out_ms: int,
    timeline: Timeline,
    mute: bool,
    blur: bool,
) -> None:
    start = in_ms / 1000.0
    duration = max(0.01, (out_ms - in_ms) / 1000.0)
    filters: list[str] = []
    if blur:
        filters.append("boxblur=8:1")
    cmd = [
        "ffmpeg",
        "-y",
        "-ss",
        f"{start:.3f}",
        "-t",
        f"{duration:.3f}",
        "-i",
        str(src),
        *_codec_args(timeline),
        "-c:a",
        "aac",
    ]
    if filters:
        cmd.extend(["-vf", ",".join(filters)])
    if mute:
        cmd.extend(["-af", "volume=0"])
    if timeline.export.strip_metadata:
        cmd.extend(["-map_metadata", "-1"])
    cmd.append(str(dest))
    subprocess.run(cmd, check=True, capture_output=True, text=True)


def _concat(parts: list[Path], out: Path, *, strip_metadata: bool) -> None:
    list_file = parts[0].parent / "concat.txt"
    list_file.write_text("".join(f"file '{p}'\n" for p in parts), encoding="utf-8")
    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(list_file),
        "-c",
        "copy",
    ]
    if strip_metadata:
        cmd.extend(["-map_metadata", "-1"])
    cmd.append(str(out))
    subprocess.run(cmd, check=True, capture_output=True, text=True)
