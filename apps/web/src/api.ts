export type ConsentState = {
  accepted: boolean;
  version: number;
  accepted_at: string | null;
  text: string;
};

export type Project = {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
};

export type Segment = {
  id: string;
  clip_id: string;
  in_ms: number;
  out_ms: number;
  state: "keep" | "cut";
  mute: boolean;
  blur_faces: boolean;
};

export type Timeline = {
  project_id: string;
  version: number;
  clips: Array<{
    id: string;
    path: string;
    duration_ms: number;
    error?: string | null;
  }>;
  segments: Segment[];
  export: { codec: "h264" | "h265"; strip_metadata: boolean };
};

export type Job = {
  id: string;
  project_id: string;
  type: string;
  status: string;
  progress: number;
  error?: string | null;
};

export type LibraryInfo = {
  library: string;
  inbox: string;
  projects: string;
  exports: string;
  inbox_files: { count: number; names: string[] };
};

async function parseJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(detail || `Request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export async function fetchConsent(): Promise<ConsentState> {
  return parseJson(await fetch("/api/consent"));
}

export async function acceptConsent(): Promise<ConsentState> {
  return parseJson(
    await fetch("/api/consent", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ accept: true }),
    }),
  );
}

export async function fetchLibrary(): Promise<LibraryInfo> {
  return parseJson(await fetch("/api/library"));
}

export async function listProjects(): Promise<Project[]> {
  return parseJson(await fetch("/api/projects"));
}

export async function createProject(id: string, title?: string): Promise<Project> {
  return parseJson(
    await fetch("/api/projects", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ id, title }),
    }),
  );
}

export async function getProject(id: string): Promise<{ project: Project; timeline: Timeline }> {
  return parseJson(await fetch(`/api/projects/${id}`));
}

export async function saveTimeline(projectId: string, timeline: Timeline): Promise<Timeline> {
  return parseJson(
    await fetch(`/api/projects/${projectId}/timeline`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ timeline }),
    }),
  );
}

export async function importClips(
  projectId: string,
  source: "inbox" | "sources",
): Promise<{ added: number; clip_count: number; timeline: Timeline }> {
  return parseJson(
    await fetch(`/api/projects/${projectId}/import`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ source }),
    }),
  );
}

export async function uploadClips(
  projectId: string,
  files: FileList | File[],
): Promise<{ added: number; clip_count: number; timeline: Timeline }> {
  const body = new FormData();
  for (const file of Array.from(files)) {
    body.append("files", file);
  }
  return parseJson(await fetch(`/api/projects/${projectId}/upload`, { method: "POST", body }));
}

export function mediaUrl(projectId: string, relativePath: string): string {
  return `/api/projects/${projectId}/media/${relativePath}`;
}

export async function enqueueJob(projectId: string, type: string): Promise<Job> {
  return parseJson(
    await fetch(`/api/projects/${projectId}/jobs`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ type }),
    }),
  );
}

export async function getJob(jobId: string): Promise<Job> {
  return parseJson(await fetch(`/api/jobs/${jobId}`));
}

export async function waitForJob(jobId: string, onUpdate?: (job: Job) => void): Promise<Job> {
  for (;;) {
    const job = await getJob(jobId);
    onUpdate?.(job);
    if (["succeeded", "failed", "cancelled"].includes(job.status)) {
      return job;
    }
    await new Promise((r) => setTimeout(r, 400));
  }
}
