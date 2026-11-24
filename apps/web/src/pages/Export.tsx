import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import {
  defaultLooks,
  enqueueJob,
  fetchLibrary,
  getProject,
  listBackgrounds,
  listFaceRefs,
  listProjectExports,
  saveTimeline,
  uploadBackgrounds,
  uploadFaceRefs,
  waitForJob,
  type CreativeLooks,
  type Timeline,
} from "../api";

export default function ExportPage() {
  const { projectId = "" } = useParams();
  const [timeline, setTimeline] = useState<Timeline | null>(null);
  const [exportsDir, setExportsDir] = useState("");
  const [exports, setExports] = useState<Array<{ name: string; path: string; size_bytes: number }>>([]);
  const [backgrounds, setBackgrounds] = useState<string[]>([]);
  const [faces, setFaces] = useState<string[]>([]);
  const [status, setStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  function looksOf(t: Timeline): CreativeLooks {
    return { ...defaultLooks(), ...(t.looks || {}) };
  }

  function patchLooks(patch: Partial<CreativeLooks>) {
    if (!timeline) return;
    setTimeline({
      ...timeline,
      looks: { ...looksOf(timeline), ...patch },
    });
  }

  async function refreshAssets() {
    const [bg, face] = await Promise.all([listBackgrounds(), listFaceRefs()]);
    setBackgrounds(bg.items.map((i) => i.name));
    setFaces(face.items.map((i) => i.name));
  }

  async function refreshExports() {
    const data = await listProjectExports(projectId);
    setExportsDir(data.exports_dir);
    setExports(data.items);
  }

  useEffect(() => {
    getProject(projectId)
      .then((data) =>
        setTimeline({
          ...data.timeline,
          looks: { ...defaultLooks(), ...(data.timeline.looks || {}) },
        }),
      )
      .catch((err: unknown) => setError(err instanceof Error ? err.message : "Load failed"));
    fetchLibrary()
      .then((lib) => setExportsDir(lib.exports))
      .catch(() => undefined);
    refreshExports().catch(() => undefined);
    refreshAssets().catch(() => undefined);
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
        looks: looksOf(timeline),
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

  const looks = looksOf(timeline);

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
      </div>

      <div className="panel">
        <h2>Creative looks</h2>
        <p className="muted">
          Local-only. Backgrounds work with a green/magenta screen; face grades and body reshape run on CPU
          without a model pack. Likeness morph needs your own face still + a local model pack.
        </p>

        <label className="field">
          Background
          <select
            value={looks.background_mode}
            onChange={(e) =>
              patchLooks({
                background_mode: e.target.value as CreativeLooks["background_mode"],
              })
            }
          >
            <option value="none">None</option>
            <option value="soft_blur">Soft blur wash</option>
            <option value="solid">Solid frame pad</option>
            <option value="chroma_solid">Chroma → solid color</option>
            <option value="chroma_image">Chroma → image</option>
          </select>
        </label>

        {looks.background_mode === "solid" || looks.background_mode === "chroma_solid" ? (
          <label className="field">
            Background color
            <input
              type="color"
              value={looks.background_color.startsWith("#") ? looks.background_color : `#${looks.background_color}`}
              onChange={(e) => patchLooks({ background_color: e.target.value })}
            />
          </label>
        ) : null}

        {looks.background_mode.startsWith("chroma") ? (
          <>
            <label className="field">
              Screen color
              <select
                value={looks.chroma_color}
                onChange={(e) =>
                  patchLooks({ chroma_color: e.target.value as CreativeLooks["chroma_color"] })
                }
              >
                <option value="green">Green</option>
                <option value="magenta">Magenta</option>
              </select>
            </label>
            <label className="field">
              Key sensitivity ({looks.chroma_similarity.toFixed(2)})
              <input
                type="range"
                min={0.05}
                max={0.6}
                step={0.01}
                value={looks.chroma_similarity}
                onChange={(e) => patchLooks({ chroma_similarity: Number(e.target.value) })}
              />
            </label>
          </>
        ) : null}

        {looks.background_mode === "chroma_image" ? (
          <label className="field">
            Background image
            <select
              value={looks.background_image || ""}
              onChange={(e) => patchLooks({ background_image: e.target.value || null })}
            >
              <option value="">Select uploaded still…</option>
              {backgrounds.map((name) => (
                <option key={name} value={name}>
                  {name}
                </option>
              ))}
            </select>
          </label>
        ) : null}

        <label className="field">
          Upload background stills
          <input
            type="file"
            accept="image/jpeg,image/png,image/webp"
            multiple
            onChange={(e) => {
              if (!e.target.files?.length) return;
              uploadBackgrounds(e.target.files)
                .then((res) => setBackgrounds(res.items.map((i) => i.name)))
                .catch((err: unknown) =>
                  setError(err instanceof Error ? err.message : "Background upload failed"),
                );
            }}
          />
        </label>

        <label className="field">
          Face look
          <select
            value={looks.face_look}
            onChange={(e) => patchLooks({ face_look: e.target.value as CreativeLooks["face_look"] })}
          >
            <option value="none">None</option>
            <option value="soft_beauty">Soft beauty</option>
            <option value="warm_glow">Warm glow</option>
            <option value="cool_clean">Cool clean</option>
          </select>
        </label>

        <label className="field">
          Body type reshape
          <select
            value={looks.body_type}
            onChange={(e) => patchLooks({ body_type: e.target.value as CreativeLooks["body_type"] })}
          >
            <option value="none">None</option>
            <option value="slim">Slimmer</option>
            <option value="soft">Softer / wider</option>
            <option value="athletic">Athletic</option>
            <option value="tall">Taller</option>
          </select>
        </label>

        <label className="field">
          Face morph
          <select
            value={looks.face_morph}
            onChange={(e) =>
              patchLooks({ face_morph: e.target.value as CreativeLooks["face_morph"] })
            }
          >
            <option value="none">None</option>
            <option value="likeness_ref">Likeness from my face still (needs model pack)</option>
          </select>
        </label>

        {looks.face_morph === "likeness_ref" ? (
          <>
            <label className="field">
              My face reference
              <select
                value={looks.face_ref_image || ""}
                onChange={(e) => patchLooks({ face_ref_image: e.target.value || null })}
              >
                <option value="">Select uploaded face still…</option>
                {faces.map((name) => (
                  <option key={name} value={name}>
                    {name}
                  </option>
                ))}
              </select>
            </label>
            <label className="field">
              Upload my face stills
              <input
                type="file"
                accept="image/jpeg,image/png,image/webp"
                multiple
                onChange={(e) => {
                  if (!e.target.files?.length) return;
                  uploadFaceRefs(e.target.files)
                    .then((res) => setFaces(res.items.map((i) => i.name)))
                    .catch((err: unknown) =>
                      setError(err instanceof Error ? err.message : "Face upload failed"),
                    );
                }}
              />
            </label>
          </>
        ) : null}

        <label className="field confirm-looks">
          <input
            type="checkbox"
            checked={looks.confirm_own_likeness}
            onChange={(e) => patchLooks({ confirm_own_likeness: e.target.checked })}
          />
          I confirm these looks only change my own (or mutually consented) likeness — not third parties.
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
