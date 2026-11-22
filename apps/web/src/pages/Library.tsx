import { FormEvent, useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { createProject, listProjects, type Project } from "../api";

export default function LibraryPage() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [id, setId] = useState("");
  const [title, setTitle] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function refresh() {
    setProjects(await listProjects());
  }

  useEffect(() => {
    refresh().catch((err: unknown) =>
      setError(err instanceof Error ? err.message : "Failed to load projects"),
    );
  }, []);

  async function onCreate(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await createProject(id.trim(), title.trim() || undefined);
      setId("");
      setTitle("");
      await refresh();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Create failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="page">
      <div className="panel">
        <h2>Library</h2>
        <p className="muted">
          Create a project, import clips with the CLI (`woomba import --project …`), then open the
          timeline to rough-cut and export.
        </p>
        <form className="actions" onSubmit={onCreate}>
          <input
            value={id}
            onChange={(e) => setId(e.target.value)}
            placeholder="project-id"
            required
            pattern="[A-Za-z0-9][A-Za-z0-9_-]*"
          />
          <input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Title (optional)" />
          <button className="btn btn-primary" disabled={busy} type="submit">
            Create project
          </button>
        </form>
        {error ? <p style={{ color: "var(--danger)" }}>{error}</p> : null}
      </div>
      <div className="panel">
        <h2>Projects</h2>
        {projects.length === 0 ? (
          <p className="muted">No projects yet.</p>
        ) : (
          <ul className="project-list">
            {projects.map((project) => (
              <li key={project.id}>
                <Link to={`/projects/${project.id}`}>{project.title}</Link>
                <span className="muted">{project.id}</span>
              </li>
            ))}
          </ul>
        )}
      </div>
    </main>
  );
}
