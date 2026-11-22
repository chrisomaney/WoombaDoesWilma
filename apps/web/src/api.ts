export type ConsentState = {
  accepted: boolean;
  version: number;
  accepted_at: string | null;
  text: string;
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

export async function fetchHealth(): Promise<{ status: string }> {
  return parseJson(await fetch("/api/health"));
}
