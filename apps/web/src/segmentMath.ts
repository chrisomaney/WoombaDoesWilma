import type { Segment } from "./api";

function uid(): string {
  return `s_${Math.random().toString(16).slice(2, 10)}`;
}

/** Ensure a clip has full coverage segments; default whole clip to keep. */
export function ensureClipSegments(
  segments: Segment[],
  clipId: string,
  durationMs: number,
): Segment[] {
  const others = segments.filter((s) => s.clip_id !== clipId);
  const mine = segments
    .filter((s) => s.clip_id === clipId)
    .sort((a, b) => a.in_ms - b.in_ms);
  if (durationMs <= 0) {
    return others;
  }
  if (mine.length === 0) {
    return [
      ...others,
      {
        id: uid(),
        clip_id: clipId,
        in_ms: 0,
        out_ms: durationMs,
        state: "keep",
        mute: false,
        blur_faces: false,
      },
    ];
  }
  return [...others, ...normalizeClipSegments(mine, clipId, durationMs)];
}

export function normalizeClipSegments(
  mine: Segment[],
  clipId: string,
  durationMs: number,
): Segment[] {
  const sorted = [...mine]
    .map((s) => ({
      ...s,
      in_ms: Math.max(0, Math.min(durationMs, s.in_ms)),
      out_ms: Math.max(0, Math.min(durationMs, s.out_ms)),
    }))
    .filter((s) => s.out_ms > s.in_ms)
    .sort((a, b) => a.in_ms - b.in_ms);

  const filled: Segment[] = [];
  let cursor = 0;
  for (const seg of sorted) {
    if (seg.in_ms > cursor) {
      filled.push({
        id: uid(),
        clip_id: clipId,
        in_ms: cursor,
        out_ms: seg.in_ms,
        state: "keep",
        mute: false,
        blur_faces: false,
      });
    }
    filled.push({ ...seg, clip_id: clipId });
    cursor = Math.max(cursor, seg.out_ms);
  }
  if (cursor < durationMs) {
    filled.push({
      id: uid(),
      clip_id: clipId,
      in_ms: cursor,
      out_ms: durationMs,
      state: "keep",
      mute: false,
      blur_faces: false,
    });
  }

  // Merge adjacent same-state
  const merged: Segment[] = [];
  for (const seg of filled) {
    const prev = merged[merged.length - 1];
    if (prev && prev.state === seg.state && prev.out_ms === seg.in_ms) {
      prev.out_ms = seg.out_ms;
    } else {
      merged.push({ ...seg, id: seg.id || uid() });
    }
  }
  return merged;
}

/** Paint a range as keep or cut on one clip, rebuilding that clip's segments. */
export function paintRange(
  segments: Segment[],
  clipId: string,
  durationMs: number,
  startMs: number,
  endMs: number,
  state: "keep" | "cut",
): Segment[] {
  const a = Math.max(0, Math.min(startMs, endMs));
  const b = Math.min(durationMs, Math.max(startMs, endMs));
  if (b - a < 40) {
    return ensureClipSegments(segments, clipId, durationMs);
  }
  const others = segments.filter((s) => s.clip_id !== clipId);
  const mine = ensureClipSegments(segments, clipId, durationMs).filter((s) => s.clip_id === clipId);
  const next: Segment[] = [];
  for (const seg of mine) {
    if (seg.out_ms <= a || seg.in_ms >= b) {
      next.push(seg);
      continue;
    }
    if (seg.in_ms < a) {
      next.push({ ...seg, id: uid(), out_ms: a });
    }
    next.push({
      id: uid(),
      clip_id: clipId,
      in_ms: Math.max(seg.in_ms, a),
      out_ms: Math.min(seg.out_ms, b),
      state,
      mute: seg.mute,
      blur_faces: seg.blur_faces,
    });
    if (seg.out_ms > b) {
      next.push({ ...seg, id: uid(), in_ms: b });
    }
  }
  return [...others, ...normalizeClipSegments(next, clipId, durationMs)];
}

export function snapMs(ms: number, points: number[], threshold = 120): number {
  if (!points.length) return ms;
  let best = ms;
  let bestDist = threshold + 1;
  for (const point of points) {
    const dist = Math.abs(point - ms);
    if (dist <= threshold && dist < bestDist) {
      best = point;
      bestDist = dist;
    }
  }
  return best;
}

export function resizeSegmentEdge(
  segments: Segment[],
  clipId: string,
  durationMs: number,
  segmentId: string,
  edge: "in" | "out",
  nextMs: number,
): Segment[] {
  const others = segments.filter((s) => s.clip_id !== clipId);
  const mine = ensureClipSegments(segments, clipId, durationMs)
    .filter((s) => s.clip_id === clipId)
    .sort((a, b) => a.in_ms - b.in_ms);
  const idx = mine.findIndex((s) => s.id === segmentId);
  if (idx < 0) {
    return segments;
  }
  const current = { ...mine[idx] };
  if (edge === "in") {
    const min = idx === 0 ? 0 : mine[idx - 1].in_ms + 40;
    const max = current.out_ms - 40;
    current.in_ms = Math.max(min, Math.min(max, nextMs));
    if (idx > 0) {
      mine[idx - 1] = { ...mine[idx - 1], out_ms: current.in_ms };
    }
  } else {
    const min = current.in_ms + 40;
    const max = idx === mine.length - 1 ? durationMs : mine[idx + 1].out_ms - 40;
    current.out_ms = Math.max(min, Math.min(max, nextMs));
    if (idx < mine.length - 1) {
      mine[idx + 1] = { ...mine[idx + 1], in_ms: current.out_ms };
    }
  }
  mine[idx] = current;
  return [...others, ...normalizeClipSegments(mine, clipId, durationMs)];
}
