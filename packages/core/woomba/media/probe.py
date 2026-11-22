from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ProbeResult:
    duration_ms: int
    width: int | None
    height: int | None
    codec: str | None
    has_audio: bool


def probe_clip(path: Path) -> ProbeResult:
    cmd = [
        "ffprobe",
        "-v",
        "error",
        "-show_entries",
        "format=duration:stream=index,codec_type,codec_name,width,height",
        "-of",
        "json",
        str(path),
    ]
    proc = subprocess.run(cmd, check=True, capture_output=True, text=True)
    payload = json.loads(proc.stdout)
    duration_s = float(payload.get("format", {}).get("duration") or 0)
    width = height = None
    codec = None
    has_audio = False
    for stream in payload.get("streams", []):
        if stream.get("codec_type") == "video" and width is None:
            width = stream.get("width")
            height = stream.get("height")
            codec = stream.get("codec_name")
        if stream.get("codec_type") == "audio":
            has_audio = True
    return ProbeResult(
        duration_ms=int(round(duration_s * 1000)),
        width=width,
        height=height,
        codec=codec,
        has_audio=has_audio,
    )
