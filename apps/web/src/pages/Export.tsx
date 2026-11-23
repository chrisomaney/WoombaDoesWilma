import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  enqueueJob,
  fetchLibrary,
  getProject,
  listProjectExports,
  saveTimeline,
  waitForJob,
  type Timeline,
} from "../api";

export default function ExportPage() {
  const { projectId = "" } = useParams();
  const [timeline, setTimeline] = useState<Timeline | null>(null);
  const [exportsDir, setExportsDir] = useState("");
  const [exports, setExports] = useState<Array<{ name: string; path: string; size_bytes: number }>>([]);
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function refreshExports() {
    const data = await listProjectExports(projectId);
    setExportsDir(data.exports_dir);
    setExports(data.items);
  }

  useEffect(() => {
    getProject(projectId)
      .then((data) => setTimeline(data.timeline))
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "Load failed"));
    fetchLibrary()
      .then((lib) => setExportsDir(lib.exports))
      .catch(() => undefined);
    refreshExports().catch(() => undefined);
  }, [projectId]);

  async function onExport() {
    if (!timeline) return;
    setBusy(true);
    setError(null);
    setStatus(null);
    try {
      const next = {
        ...timeline,
        export: { ...timeline.export, keep_only: true },
      };
      setTimeline(next);
      await saveTimeline(projectId, next);
      const job = await enqueueJob(projectId, "export");
      const finished = await waitForJob(job.id, (j) =>
        setStatus(`${j.status} ${Math.round(j.progress * 100)}%`),
      );
      if (finished.status === "failed") {
        setError(finished.error || "Export failed");
      } else {
        setStatus("Export finished.");
        await refreshExports();
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
        <h2>Export keep only</h2>
        <p className="muted">Renders only green/keep segments into one MP4.</p>
        {exportsDir ? (
          <div className="path-box">
            <div>
              <span className="muted">Exports folder</span>
              <code>{exportsDir}</code>
            </div>
          </div>
        ) : null}
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
        <label className="field">
          <input
            type="checkbox"
            checked={Boolean(timeline.export.loudnorm)}
            onChange={(e) =>
              setTimeline({
                ...timeline,
                export: { ...timeline.export, loudnorm: e.target.checked },
              })
            }
          />
          Normalize audio (loudnorm)
        </label>
        <div className="actions">
          <button className="btn btn-primary" disabled={busy} onClick={onExport}>
            {busy ? "Exporting…" : "Export keep only"}
          </button>
        </div>
        {status ? <p className="muted">{status}</p> : null}
        {error ? <p style={{ color: "var(--danger)" }}>{error}</p> : null}
      </div>

      <div className="panel">
        <h2>Recent exports</h2>
        {exports.length === 0 ? (
          <p className="muted">No exports for this project yet.</p>
        ) : (
          <ul className="segment-list">
            {exports.map((item) => (
              <li key={item.name}>
                <span>{item.name}</span>
                <span className="muted">{(item.size_bytes / (1024 * 1024)).toFixed(1)} MB</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </main>
  );
}
