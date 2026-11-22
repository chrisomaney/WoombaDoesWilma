import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { enqueueJob, getProject, saveTimeline, waitForJob, type Timeline } from "../api";

export default function ExportPage() {
  const { projectId = "" } = useParams();
  const [timeline, setTimeline] = useState<Timeline | null>(null);
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    getProject(projectId)
      .then((data) => setTimeline(data.timeline))
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "Load failed"));
  }, [projectId]);

  async function onExport() {
    if (!timeline) return;
    setBusy(true);
    setError(null);
    setStatus(null);
    try {
      await saveTimeline(projectId, timeline);
      const job = await enqueueJob(projectId, "export");
      const finished = await waitForJob(job.id, (j) => setStatus(`${j.status} ${Math.round(j.progress * 100)}%`));
      if (finished.status === "failed") {
        setError(finished.error || "Export failed");
      } else {
        setStatus("Export finished — check your library exports folder.");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Export failed");
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
          <Link to={`/projects/${projectId}`}>Project</Link> / export
        </p>
        <h2>Export</h2>
        <label className="field">
          Codec
          <select
            value={timeline.export.codec}
            onChange={(e) =>
              setTimeline({
                ...timeline,
                export: { ...timeline.export, codec: e.target.value as "h264" | "h265" },
              })
            }
          >
            <option value="h264">H.264</option>
            <option value="h265">H.265</option>
          </select>
        </label>
        <label className="field">
          <input
            type="checkbox"
            checked={timeline.export.strip_metadata}
            onChange={(e) =>
              setTimeline({
                ...timeline,
                export: { ...timeline.export, strip_metadata: e.target.checked },
              })
            }
          />
          Strip metadata
        </label>
        <div className="actions">
          <button className="btn btn-primary" disabled={busy} onClick={onExport}>
            {busy ? "Exporting…" : "Export now"}
          </button>
        </div>
        {status ? <p className="muted">{status}</p> : null}
        {error ? <p style={{ color: "var(--danger)" }}>{error}</p> : null}
      </div>
    </main>
  );
}
