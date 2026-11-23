import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  enqueueJob,
  fetchLibrary,
  getProject,
  importClips,
  saveTimeline,
  uploadClips,
  waitForJob,
  type Job,
  type Segment,
  type Timeline,
} from "../api";
import ClipPreview from "../components/ClipPreview";
import ImportDialog from "../components/ImportDialog";
import { ensureClipSegments } from "../segmentMath";

const JOB_ORDER = ["analyze", "roughcut", "polish", "privacy", "export"] as const;

export default function ProjectPage() {
  const { projectId = "" } = useParams();
  const [timeline, setTimeline] = useState<Timeline | null>(null);
  const [title, setTitle] = useState("");
  const [inboxPath, setInboxPath] = useState<string>("");
  const [error, setError] = useState<string | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [job, setJob] = useState<Job | null>(null);
  const [busy, setBusy] = useState(false);
  const [activeClip, setActiveClip] = useState<string | null>(null);
  const [activeSegment, setActiveSegment] = useState<string | null>(null);
  const [previewRequestId, setPreviewRequestId] = useState(0);
  const [importOpen, setImportOpen] = useState(false);

  async function refresh() {
    const data = await getProject(projectId);
    setTitle(data.project.title);
    setTimeline(data.timeline);
    if (!activeClip && data.timeline.clips[0]) {
      setActiveClip(data.timeline.clips[0].id);
    }
  }

  useEffect(() => {
    refresh().catch((err: unknown) =>
      setError(err instanceof Error ? err.message : "Failed to load project"),
    );
    fetchLibrary()
      .then((lib) => setInboxPath(lib.inbox))
      .catch(() => undefined);
  }, [projectId]);

  async function persistSegments(nextSegments: Segment[]) {
    if (!timeline) return;
    const next: Timeline = { ...timeline, segments: nextSegments };
    setTimeline(next);
    setTimeline(await saveTimeline(projectId, next));
  }

  async function toggleSegment(segmentId: string) {
    if (!timeline) return;
    const nextSegments: Segment[] = timeline.segments.map((segment) =>
      segment.id === segmentId
        ? { ...segment, state: segment.state === "keep" ? ("cut" as const) : ("keep" as const) }
        : segment,
    );
    await persistSegments(nextSegments);
  }

  async function applyImportResult(result: {
    added: number;
    clip_count: number;
    timeline: Timeline;
  }) {
    setTimeline(result.timeline);
    setStatus(`Imported ${result.added} clip(s). Total now ${result.clip_count}.`);
    if (result.timeline.clips[0]) {
      setActiveClip(result.timeline.clips[0].id);
    }
  }

  async function runImport(source: "inbox" | "sources") {
    setBusy(true);
    setError(null);
    setStatus(null);
    try {
      await applyImportResult(await importClips(projectId, source));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Import failed");
      throw err;
    } finally {
      setBusy(false);
    }
  }

  async function runUpload(files: FileList) {
    setBusy(true);
    setError(null);
    setStatus(null);
    try {
      await applyImportResult(await uploadClips(projectId, files));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
      throw err;
    } finally {
      setBusy(false);
    }
  }

  async function runJob(type: (typeof JOB_ORDER)[number]) {
    setBusy(true);
    setError(null);
    try {
      const created = await enqueueJob(projectId, type);
      const finished = await waitForJob(created.id, setJob);
      if (finished.status === "failed") {
        setError(finished.error || "Job failed");
      }
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Job failed");
    } finally {
      setBusy(false);
    }
  }

  if (!timeline) {
    return (
      <main className="page">
        <p className="muted">{error || "Loading…"}</p>
      </main>
    );
  }

  const selected = timeline.clips.find((clip) => clip.id === activeClip) || timeline.clips[0];
  const selectedSegments = selected
    ? ensureClipSegments(timeline.segments, selected.id, selected.duration_ms).filter(
        (s) => s.clip_id === selected.id,
      )
    : [];

  return (
    <main className="page">
      <div className="panel">
        <p className="muted">
          <Link to="/">Library</Link> / {projectId}
        </p>
        <h2>{title}</h2>
        <p className="muted">
          {timeline.clips.length} clip(s) · {timeline.segments.filter((s) => s.state === "keep").length}{" "}
          keep · {timeline.segments.filter((s) => s.state === "cut").length} cut
        </p>
        <div className="actions">
          <button className="btn btn-primary" disabled={busy} onClick={() => setImportOpen(true)}>
            Import files…
          </button>
          {JOB_ORDER.map((type) => (
            <button key={type} className="btn" disabled={busy} onClick={() => runJob(type)}>
              {type}
            </button>
          ))}
          <Link className="btn" to={`/projects/${projectId}/export`}>
            Export page
          </Link>
        </div>
        {job ? (
          <p className="muted">
            Job {job.type}: {job.status} ({Math.round(job.progress * 100)}%)
          </p>
        ) : null}
        {status ? <p className="muted">{status}</p> : null}
        {error ? <p style={{ color: "var(--danger)" }}>{error}</p> : null}
      </div>

      <div className="panel">
        <h2>Editor</h2>
        {timeline.clips.length === 0 ? (
          <p className="muted">
            No clips yet. Click <strong>Import files…</strong> to choose videos from this Mac.
          </p>
        ) : (
          <div className="clip-layout">
            <ul className="segment-list">
              {timeline.clips.map((clip) => (
                <li key={clip.id}>
                  <button className="btn" onClick={() => setActiveClip(clip.id)}>
                    {clip.id === selected?.id ? "active" : "select"}
                  </button>
                  <span>
                    {clip.path} · {(clip.duration_ms / 1000).toFixed(1)}s
                    {clip.error ? ` · error: ${clip.error}` : ""}
                  </span>
                </li>
              ))}
            </ul>
            {selected ? (
              <ClipPreview
                projectId={projectId}
                clip={selected}
                segments={
                  // Use full timeline segments so edits to one clip preserve others.
                  ensureClipSegments(timeline.segments, selected.id, selected.duration_ms)
                }
                activeSegmentId={activeSegment}
                previewRequestId={previewRequestId}
                onActiveSegment={setActiveSegment}
                onSegmentsChange={(next) => {
                  void persistSegments(next);
                }}
              />
            ) : null}
          </div>
        )}
      </div>

      <div className="panel">
        <h2>Segments</h2>
        {selectedSegments.length === 0 ? (
          <p className="muted">Import a clip, then drag on the timeline to cut.</p>
        ) : (
          <ul className="segment-list">
            {selectedSegments.map((segment) => (
              <li key={segment.id}>
                <div className="actions">
                  <button className="btn" onClick={() => toggleSegment(segment.id)}>
                    {segment.state}
                  </button>
                  <button
                    className="btn"
                    onClick={() => {
                      setActiveSegment(segment.id);
                      setPreviewRequestId((n) => n + 1);
                    }}
                  >
                    Preview
                  </button>
                </div>
                <span>
                  {(segment.in_ms / 1000).toFixed(1)}s → {(segment.out_ms / 1000).toFixed(1)}s
                  {segment.mute ? " · muted" : ""}
                  {segment.blur_faces ? " · blur" : ""}
                </span>
              </li>
            ))}
          </ul>
        )}
        <p className="muted">Tip: double-click a colored block on the scrubber to preview that segment.</p>
      </div>

      <ImportDialog
        open={importOpen}
        busy={busy}
        inboxPath={inboxPath}
        onClose={() => setImportOpen(false)}
        onUpload={runUpload}
        onImportInbox={() => runImport("inbox")}
        onScanSources={() => runImport("sources")}
      />
    </main>
  );
}
