from __future__ import annotations

import json
import struct
import subprocess
import tempfile
from pathlib import Path

from woomba.models import Timeline
from woomba.paths import project_dir
from woomba.timeline import load_timeline, save_timeline


def proxy_rel_path(clip_id: str) -> str:
    return f"proxies/{clip_id}.mp4"


def peaks_rel_path(clip_id: str) -> str:
    return f"proxies/{clip_id}.peaks.json"


def ensure_proxy_and_peaks(library_root: Path, project_id: str, clip_id: str | None = None) -> Timeline:
    timeline = load_timeline(library_root, project_id)
    project = project_dir(library_root, project_id)
    (project / "proxies").mkdir(parents=True, exist_ok=True)

    for clip in timeline.clips:
        if clip_id and clip.id != clip_id:
            continue
        if clip.error:
            continue
        src = project / clip.path
        if not src.is_file():
            continue
        proxy = project / proxy_rel_path(clip.id)
        peaks = project / peaks_rel_path(clip.id)
        if not proxy.is_file():
            _make_proxy(src, proxy)
        clip.proxy_path = proxy_rel_path(clip.id)
        if not peaks.is_file():
            _make_peaks(src, peaks)
        clip.waveform_path = peaks_rel_path(clip.id)
    save_timeline(library_root, timeline)
    return timeline


def _make_proxy(src: Path, dest: Path) -> None:
    cmd = [
        "ffmpeg",
        "-y",
        "-i",
        str(src),
        "-vf",
        "scale='min(640,iw)':-2",
        "-c:v",
        "libx264",
        "-preset",
        "veryfast",
        "-crf",
        "28",
        "-c:a",
        "aac",
        "-b:a",
        "96k",
        "-movflags",
        "+faststart",
        str(dest),
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True)


def _make_peaks(src: Path, dest: Path, buckets: int = 400) -> None:
    with tempfile.TemporaryDirectory(prefix="woomba-peaks-") as tmp:
        wav = Path(tmp) / "audio.wav"
        cmd = [
            "ffmpeg",
            "-y",
            "-i",
            str(src),
            "-ac",
            "1",
            "-ar",
            "8000",
            "-f",
            "wav",
            str(wav),
        ]
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0 or not wav.is_file():
            dest.write_text(json.dumps({"peaks": [0.0] * buckets}) + "\n", encoding="utf-8")
            return
        peaks = _wav_peaks(wav, buckets)
        dest.write_text(json.dumps({"peaks": peaks}) + "\n", encoding="utf-8")


def _wav_peaks(path: Path, buckets: int) -> list[float]:
    data = path.read_bytes()
    # Skip RIFF header; find "data" chunk.
    idx = data.find(b"data")
    if idx < 0 or idx + 8 > len(data):
        return [0.0] * buckets
    size = struct.unpack_from("<I", data, idx + 4)[0]
    start = idx + 8
    pcm = data[start : start + size]
    if len(pcm) < 2:
        return [0.0] * buckets
    sample_count = len(pcm) // 2
    samples = struct.unpack("<" + "h" * sample_count, pcm[: sample_count * 2])
    peaks: list[float] = []
    bucket_size = max(1, sample_count // buckets)
    for i in range(buckets):
        chunk = samples[i * bucket_size : (i + 1) * bucket_size]
        if not chunk:
            peaks.append(0.0)
            continue
        peak = max(abs(s) for s in chunk) / 32768.0
        peaks.append(round(min(1.0, peak), 4))
    return peaks
