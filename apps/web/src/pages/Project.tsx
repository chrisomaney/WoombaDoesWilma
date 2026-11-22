import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  enqueueJob,
  getProject,
  saveTimeline,
  waitForJob,
  type Job,
  type Timeline,
} from "../api";

const JOB_ORDER = ["analyze", "roughcut", "polish", "privacy", "export"] as const;

export default function ProjectPage() {
  const { projectId = "" } = useParams();
  const [timeline, setTimeline] = useState<Timeline | null>(null);
  const [title, setTitle] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [job, setJob] = useState<Job | null>(null);
  const [busy, setBusy] = useState(false);

  async function refresh() {
    const data = await getProject(projectId);
    setTitle(data.project.title);
    setTimeline(data.timeline);
  }

  useEffect(() => {
    refresh().catch((err: unknown) =>
      setError(err instanceof Error ? err.message : "Failed to load project"),
    );
  }, [projectId]);

  async function toggleSegment(segmentId: string) {
    if (!timeline) return;
    const next: Timeline = {
      ...timeline,
      segments: timeline.segments.map((segment) =>
        segment.id === segmentId
          ? { ...segment, state: segment.state === "keep" ? "cut" : "keep" }
          : segment,
      ),
    };
    setTimeline(await saveTimeline(projectId, next));
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
          {JOB_ORDER.map((type) => (
            <button key={type} className="btn" disabled={busy} onClick={() => runJob(type)}>
              {type}
            </button>
          ))}
          <Link className="btn btn-primary" to={`/projects/${projectId}/export`}>
            Export
          </Link>
        </div>
        {job ? (
          <p className="muted">
            Job {job.type}: {job.status} ({Math.round(job.progress * 100)}%)
          </p>
        ) : null}
        {error ? <p style={{ color: "var(--danger)" }}>{error}</p> : null}
      </div>
      <div className="panel">
        <h2>Segments</h2>
        {timeline.segments.length === 0 ? (
          <p className="muted">Run analyze/roughcut after importing clips via CLI.</p>
        ) : (
          <ul className="segment-list">
            {timeline.segments.map((segment) => (
              <li key={segment.id}>
                <button className="btn" onClick={() => toggleSegment(segment.id)}>
                  {segment.state}
                </button>
                <span>
                  {segment.clip_id} · {(segment.in_ms / 1000).toFixed(1)}s →{" "}
                  {(segment.out_ms / 1000).toFixed(1)}s
                  {segment.mute ? " · muted" : ""}
                  {segment.blur_faces ? " · blur" : ""}
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </main>
  );
}
