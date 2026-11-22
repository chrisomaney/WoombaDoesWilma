from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path

SILENCE_START_RE = re.compile(r"silence_start:\s*([0-9.]+)")
SILENCE_END_RE = re.compile(r"silence_end:\s*([0-9.]+)")


@dataclass
class TimeRange:
    start_ms: int
    end_ms: int


def detect_silence(
    path: Path,
    *,
    noise_db: float = -35.0,
    min_silence_s: float = 0.4,
) -> list[TimeRange]:
    cmd = [
        "ffmpeg",
        "-i",
        str(path),
        "-af",
        f"silencedetect=noise={noise_db}dB:d={min_silence_s}",
        "-f",
        "null",
        "-",
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    log = proc.stderr or ""
    ranges: list[TimeRange] = []
    start: float | None = None
    for line in log.splitlines():
        if match := SILENCE_START_RE.search(line):
            start = float(match.group(1))
        elif start is not None and (match := SILENCE_END_RE.search(line)):
            end = float(match.group(1))
            ranges.append(TimeRange(start_ms=int(start * 1000), end_ms=int(end * 1000)))
            start = None
    return ranges


def invert_to_keep_ranges(
    duration_ms: int,
    silence: list[TimeRange],
    *,
    pad_ms: int = 120,
    min_keep_ms: int = 200,
) -> list[TimeRange]:
    if duration_ms <= 0:
        return []
    keep: list[TimeRange] = []
    cursor = 0
    for gap in sorted(silence, key=lambda r: r.start_ms):
        gap_start = max(0, gap.start_ms - pad_ms)
        gap_end = min(duration_ms, gap.end_ms + pad_ms)
        if gap_start > cursor:
            keep.append(TimeRange(start_ms=cursor, end_ms=gap_start))
        cursor = max(cursor, gap_end)
    if cursor < duration_ms:
        keep.append(TimeRange(start_ms=cursor, end_ms=duration_ms))
    return [r for r in keep if (r.end_ms - r.start_ms) >= min_keep_ms]
