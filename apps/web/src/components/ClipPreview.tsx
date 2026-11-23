import { useEffect, useMemo, useRef, useState, type PointerEvent as ReactPointerEvent } from "react";
import type { Segment } from "../api";
import { mediaUrl } from "../api";
import { paintRange, resizeSegmentEdge, snapMs } from "../segmentMath";

type Clip = {
  id: string;
  path: string;
  duration_ms: number;
  proxy_path?: string | null;
  waveform_path?: string | null;
};

type Props = {
  projectId: string;
  clip: Clip;
  segments: Segment[];
  snapPoints?: number[];
  activeSegmentId?: string | null;
  previewRequestId?: number;
  onSegmentsChange: (next: Segment[]) => void;
  onActiveSegment: (segmentId: string | null) => void;
};

type DragMode =
  | { kind: "paint"; originX: number; startMs: number }
  | { kind: "edge"; segmentId: string; edge: "in" | "out" }
  | { kind: "pan"; originX: number; originStart: number; originEnd: number }
  | null;

function formatTime(ms: number): string {
  const s = Math.max(0, ms) / 1000;
  const m = Math.floor(s / 60);
  const rem = s - m * 60;
  return `${m}:${rem.toFixed(1).padStart(4, "0")}`;
}

export default function ClipPreview({
  projectId,
  clip,
  segments,
  snapPoints = [],
  activeSegmentId,
  previewRequestId = 0,
  onSegmentsChange,
  onActiveSegment,
}: Props) {
  const videoRef = useRef<HTMLVideoElement>(null);
  const trackRef = useRef<HTMLDivElement>(null);
  const [currentMs, setCurrentMs] = useState(0);
  const [drag, setDrag] = useState<DragMode>(null);
  const [paintPreview, setPaintPreview] = useState<{ a: number; b: number } | null>(null);
  const [playUntil, setPlayUntil] = useState<number | null>(null);
  const [tool, setTool] = useState<"cut" | "keep">("cut");
  const [snapEnabled, setSnapEnabled] = useState(true);
  const [viewStart, setViewStart] = useState(0);
  const [viewEnd, setViewEnd] = useState(1);
  const [peaks, setPeaks] = useState<number[]>([]);
  const [useProxy, setUseProxy] = useState(true);

  const clipSegments = useMemo(
    () => segments.filter((s) => s.clip_id === clip.id).sort((a, b) => a.in_ms - b.in_ms),
    [segments, clip.id],
  );

  const durationMs = Math.max(clip.duration_ms, 1);
  const viewSpan = Math.max(0.05, viewEnd - viewStart);
  const previewSrc = useProxy && clip.proxy_path ? clip.proxy_path : clip.path;

  useEffect(() => {
    setViewStart(0);
    setViewEnd(1);
    setPeaks([]);
  }, [clip.id]);

  useEffect(() => {
    if (!clip.waveform_path) {
      setPeaks([]);
      return;
    }
    let cancelled = false;
    fetch(mediaUrl(projectId, clip.waveform_path))
      .then((r) => (r.ok ? r.json() : null))
      .then((data: { peaks?: number[] } | null) => {
        if (!cancelled && data?.peaks) setPeaks(data.peaks);
      })
      .catch(() => undefined);
    return () => {
      cancelled = true;
    };
  }, [projectId, clip.waveform_path, clip.id]);

  useEffect(() => {
    const video = videoRef.current;
    if (!video) return;
    const onTime = () => {
      const ms = video.currentTime * 1000;
      setCurrentMs(ms);
      if (playUntil != null && ms >= playUntil) {
        video.pause();
        setPlayUntil(null);
      }
    };
    video.addEventListener("timeupdate", onTime);
    return () => video.removeEventListener("timeupdate", onTime);
  }, [playUntil, clip.id, previewSrc]);

  function maybeSnap(ms: number): number {
    return snapEnabled ? snapMs(ms, snapPoints, 150) : ms;
  }

  function msFromClientX(clientX: number): number {
    const el = trackRef.current;
    if (!el) return 0;
    const rect = el.getBoundingClientRect();
    const ratio = Math.min(1, Math.max(0, (clientX - rect.left) / rect.width));
    const ms = (viewStart + ratio * viewSpan) * durationMs;
    return Math.round(ms);
  }

  function seekTo(ms: number) {
    const video = videoRef.current;
    if (!video) return;
    video.currentTime = ms / 1000;
    setCurrentMs(ms);
  }

  function playSegment(segment: Segment) {
    onActiveSegment(segment.id);
    const video = videoRef.current;
    if (!video) return;
    video.currentTime = segment.in_ms / 1000;
    setPlayUntil(segment.out_ms);
    void video.play();
  }

  useEffect(() => {
    if (!previewRequestId || !activeSegmentId) return;
    const segment = clipSegments.find((s) => s.id === activeSegmentId);
    if (!segment) return;
    const video = videoRef.current;
    if (!video) return;
    video.currentTime = segment.in_ms / 1000;
    setPlayUntil(segment.out_ms);
    void video.play();
  }, [previewRequestId, activeSegmentId, clipSegments]);

  function zoomBy(factor: number) {
    const center = currentMs / durationMs;
    const nextSpan = Math.min(1, Math.max(0.05, viewSpan * factor));
    let start = center - nextSpan / 2;
    let end = center + nextSpan / 2;
    if (start < 0) {
      end -= start;
      start = 0;
    }
    if (end > 1) {
      start -= end - 1;
      end = 1;
    }
    setViewStart(Math.max(0, start));
    setViewEnd(Math.min(1, end));
  }

  function onTrackPointerDown(event: ReactPointerEvent<HTMLDivElement>) {
    if ((event.target as HTMLElement).dataset.handle) {
      return;
    }
    if (event.shiftKey) {
      setDrag({ kind: "pan", originX: event.clientX, originStart: viewStart, originEnd: viewEnd });
      event.currentTarget.setPointerCapture(event.pointerId);
      return;
    }
    const ms = maybeSnap(msFromClientX(event.clientX));
    seekTo(ms);
    setDrag({ kind: "paint", originX: event.clientX, startMs: ms });
    setPaintPreview({ a: ms, b: ms });
    event.currentTarget.setPointerCapture(event.pointerId);
  }

  function onTrackPointerMove(event: ReactPointerEvent<HTMLDivElement>) {
    if (!drag) return;
    if (drag.kind === "pan") {
      const el = trackRef.current;
      if (!el) return;
      const dx = event.clientX - drag.originX;
      const delta = -(dx / el.getBoundingClientRect().width) * (drag.originEnd - drag.originStart);
      let start = drag.originStart + delta;
      let end = drag.originEnd + delta;
      const span = end - start;
      if (start < 0) {
        start = 0;
        end = span;
      }
      if (end > 1) {
        end = 1;
        start = 1 - span;
      }
      setViewStart(start);
      setViewEnd(end);
      return;
    }
    const ms = maybeSnap(msFromClientX(event.clientX));
    if (drag.kind === "paint") {
      setPaintPreview({ a: drag.startMs, b: ms });
      seekTo(ms);
    } else {
      onSegmentsChange(resizeSegmentEdge(segments, clip.id, durationMs, drag.segmentId, drag.edge, ms));
      seekTo(ms);
    }
  }

  function onTrackPointerUp(event: ReactPointerEvent<HTMLDivElement>) {
    if (!drag) return;
    if (drag.kind === "paint" && paintPreview) {
      const moved = Math.abs(event.clientX - drag.originX) > 4;
      if (moved) {
        onSegmentsChange(
          paintRange(segments, clip.id, durationMs, paintPreview.a, paintPreview.b, tool),
        );
      }
    }
    setDrag(null);
    setPaintPreview(null);
  }

  function startEdgeDrag(segmentId: string, edge: "in" | "out", event: ReactPointerEvent) {
    event.stopPropagation();
    setDrag({ kind: "edge", segmentId, edge });
    trackRef.current?.setPointerCapture(event.pointerId);
  }

  const playheadPct = ((currentMs / durationMs - viewStart) / viewSpan) * 100;
  const visiblePeaks = useMemo(() => {
    if (!peaks.length) return [];
    const start = Math.floor(viewStart * peaks.length);
    const end = Math.ceil(viewEnd * peaks.length);
    return peaks.slice(start, Math.max(start + 1, end));
  }, [peaks, viewStart, viewEnd]);

  return (
    <div className="clip-preview">
      <video
        ref={videoRef}
        className="preview"
        key={`${clip.id}-${previewSrc}`}
        controls
        src={mediaUrl(projectId, previewSrc)}
        onClick={(e) => {
          const video = e.currentTarget;
          if (video.paused) void video.play();
          else video.pause();
        }}
      />

      <div className="preview-toolbar">
        <div className="actions">
          <button className={`btn ${tool === "cut" ? "btn-primary" : ""}`} onClick={() => setTool("cut")} type="button">
            Drag to cut
          </button>
          <button className={`btn ${tool === "keep" ? "btn-primary" : ""}`} onClick={() => setTool("keep")} type="button">
            Drag to keep
          </button>
          <button className={`btn ${snapEnabled ? "btn-primary" : ""}`} onClick={() => setSnapEnabled((v) => !v)} type="button">
            Snap {snapEnabled ? "on" : "off"}
          </button>
          {clip.proxy_path ? (
            <button className={`btn ${useProxy ? "btn-primary" : ""}`} onClick={() => setUseProxy((v) => !v)} type="button">
              {useProxy ? "Proxy" : "Full res"}
            </button>
          ) : null}
          <button className="btn" type="button" onClick={() => zoomBy(0.7)}>
            Zoom in
          </button>
          <button className="btn" type="button" onClick={() => zoomBy(1.4)}>
            Zoom out
          </button>
          <button
            className="btn"
            type="button"
            onClick={() => {
              setViewStart(0);
              setViewEnd(1);
            }}
          >
            Fit
          </button>
        </div>
        <span className="muted">
          {formatTime(currentMs)} / {formatTime(durationMs)} — Shift-drag to pan when zoomed
        </span>
      </div>

      <div
        ref={trackRef}
        className="scrubber"
        onPointerDown={onTrackPointerDown}
        onPointerMove={onTrackPointerMove}
        onPointerUp={onTrackPointerUp}
      >
        {visiblePeaks.length > 0 ? (
          <div className="scrub-wave" aria-hidden>
            {visiblePeaks.map((peak, index) => (
              <span key={`p-${index}`} style={{ height: `${Math.max(8, peak * 100)}%` }} />
            ))}
          </div>
        ) : null}
        {snapPoints.map((point) => {
          const pct = ((point / durationMs - viewStart) / viewSpan) * 100;
          if (pct < 0 || pct > 100) return null;
          return <div key={`snap-${point}`} className="scrub-snap" style={{ left: `${pct}%` }} />;
        })}
        {clipSegments.map((segment) => {
          const left = ((segment.in_ms / durationMs - viewStart) / viewSpan) * 100;
          const right = ((segment.out_ms / durationMs - viewStart) / viewSpan) * 100;
          const width = right - left;
          if (right < 0 || left > 100) return null;
          return (
            <div
              key={segment.id}
              className={`scrub-seg scrub-${segment.state} ${
                segment.id === activeSegmentId ? "is-active" : ""
              }`}
              style={{ left: `${left}%`, width: `${width}%` }}
              title={`${segment.state} ${formatTime(segment.in_ms)}–${formatTime(segment.out_ms)}`}
              onDoubleClick={(e) => {
                e.stopPropagation();
                playSegment(segment);
              }}
            >
              <span
                className="scrub-handle"
                data-handle="in"
                onPointerDown={(e) => startEdgeDrag(segment.id, "in", e)}
              />
              <span
                className="scrub-handle scrub-handle-right"
                data-handle="out"
                onPointerDown={(e) => startEdgeDrag(segment.id, "out", e)}
              />
            </div>
          );
        })}
        {paintPreview ? (
          <div
            className={`scrub-paint scrub-${tool}`}
            style={{
              left: `${((Math.min(paintPreview.a, paintPreview.b) / durationMs - viewStart) / viewSpan) * 100}%`,
              width: `${(Math.abs(paintPreview.b - paintPreview.a) / durationMs / viewSpan) * 100}%`,
            }}
          />
        ) : null}
        {playheadPct >= 0 && playheadPct <= 100 ? (
          <div className="scrub-playhead" style={{ left: `${playheadPct}%` }} />
        ) : null}
      </div>
    </div>
  );
}
