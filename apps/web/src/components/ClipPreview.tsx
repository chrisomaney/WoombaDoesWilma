import { useEffect, useMemo, useRef, useState, type PointerEvent as ReactPointerEvent } from "react";
import type { Segment } from "../api";
import { mediaUrl } from "../api";
import { paintRange, resizeSegmentEdge } from "../segmentMath";

type Clip = {
  id: string;
  path: string;
  duration_ms: number;
};

type Props = {
  projectId: string;
  clip: Clip;
  segments: Segment[];
  activeSegmentId?: string | null;
  previewRequestId?: number;
  onSegmentsChange: (next: Segment[]) => void;
  onActiveSegment: (segmentId: string | null) => void;
};

type DragMode =
  | { kind: "paint"; originX: number; startMs: number }
  | { kind: "edge"; segmentId: string; edge: "in" | "out" }
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

  const clipSegments = useMemo(
    () => segments.filter((s) => s.clip_id === clip.id).sort((a, b) => a.in_ms - b.in_ms),
    [segments, clip.id],
  );

  const durationMs = Math.max(clip.duration_ms, 1);

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
  }, [playUntil, clip.id]);

  function msFromClientX(clientX: number): number {
    const el = trackRef.current;
    if (!el) return 0;
    const rect = el.getBoundingClientRect();
    const ratio = Math.min(1, Math.max(0, (clientX - rect.left) / rect.width));
    return Math.round(ratio * durationMs);
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

  function onTrackPointerDown(event: ReactPointerEvent<HTMLDivElement>) {
    if ((event.target as HTMLElement).dataset.handle) {
      return;
    }
    const ms = msFromClientX(event.clientX);
    seekTo(ms);
    setDrag({ kind: "paint", originX: event.clientX, startMs: ms });
    setPaintPreview({ a: ms, b: ms });
    event.currentTarget.setPointerCapture(event.pointerId);
  }

  function onTrackPointerMove(event: ReactPointerEvent<HTMLDivElement>) {
    if (!drag) return;
    const ms = msFromClientX(event.clientX);
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

  const playhead = (currentMs / durationMs) * 100;

  return (
    <div className="clip-preview">
      <video
        ref={videoRef}
        className="preview"
        controls
        src={mediaUrl(projectId, clip.path)}
        onClick={(e) => {
          // Allow click-to-toggle play on the video surface.
          const video = e.currentTarget;
          if (video.paused) void video.play();
          else video.pause();
        }}
      />

      <div className="preview-toolbar">
        <div className="actions">
          <button
            className={`btn ${tool === "cut" ? "btn-primary" : ""}`}
            onClick={() => setTool("cut")}
            type="button"
          >
            Drag to cut
          </button>
          <button
            className={`btn ${tool === "keep" ? "btn-primary" : ""}`}
            onClick={() => setTool("keep")}
            type="button"
          >
            Drag to keep
          </button>
        </div>
        <span className="muted">
          {formatTime(currentMs)} / {formatTime(durationMs)} — drag the bar; pull handles to resize
        </span>
      </div>

      <div
        ref={trackRef}
        className="scrubber"
        onPointerDown={onTrackPointerDown}
        onPointerMove={onTrackPointerMove}
        onPointerUp={onTrackPointerUp}
      >
        {clipSegments.map((segment) => {
          const left = (segment.in_ms / durationMs) * 100;
          const width = ((segment.out_ms - segment.in_ms) / durationMs) * 100;
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
              left: `${(Math.min(paintPreview.a, paintPreview.b) / durationMs) * 100}%`,
              width: `${(Math.abs(paintPreview.b - paintPreview.a) / durationMs) * 100}%`,
            }}
          />
        ) : null}
        <div className="scrub-playhead" style={{ left: `${playhead}%` }} />
      </div>
    </div>
  );
}

