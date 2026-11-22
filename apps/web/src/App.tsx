import { useEffect, useState } from "react";
import { Navigate, Route, Routes } from "react-router-dom";
import { acceptConsent, fetchConsent, type ConsentState } from "./api";
import ExportPage from "./pages/Export";
import LibraryPage from "./pages/Library";
import ProjectPage from "./pages/Project";

function TopBar() {
  return (
    <header className="topbar">
      <div className="brand">WoombaDoesWilma</div>
      <div className="muted">Private local studio</div>
    </header>
  );
}

function ConsentGate({
  consent,
  onAccepted,
}: {
  consent: ConsentState;
  onAccepted: (next: ConsentState) => void;
}) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onAccept() {
    setBusy(true);
    setError(null);
    try {
      onAccepted(await acceptConsent());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not accept consent");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="page hero-consent">
      <h1>WoombaDoesWilma</h1>
      <p>
        A private Mac studio for editing your own amateur videos. Nothing leaves this machine unless
        you move the files yourself.
      </p>
      <div className="consent-box">
        <p>{consent.text}</p>
        {error ? <p style={{ color: "var(--danger)" }}>{error}</p> : null}
        <div className="actions">
          <button className="btn btn-primary" disabled={busy} onClick={onAccept}>
            {busy ? "Saving…" : "I agree — continue"}
          </button>
        </div>
      </div>
    </main>
  );
}

export default function App() {
  const [consent, setConsent] = useState<ConsentState | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let cancelled = false;
    fetchConsent()
      .then((state) => {
        if (!cancelled) setConsent(state);
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : "API unavailable");
        }
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (error) {
    return (
      <div className="app-shell">
        <TopBar />
        <main className="page">
          <p style={{ color: "var(--danger)" }}>Cannot reach local API: {error}</p>
          <p className="muted">Start it with `woomba serve` then reload.</p>
        </main>
      </div>
    );
  }

  if (!consent) {
    return (
      <div className="app-shell">
        <TopBar />
        <main className="page">
          <p className="muted">Loading…</p>
        </main>
      </div>
    );
  }

  if (!consent.accepted) {
    return (
      <div className="app-shell">
        <TopBar />
        <ConsentGate consent={consent} onAccepted={setConsent} />
      </div>
    );
  }

  return (
    <div className="app-shell">
      <TopBar />
      <Routes>
        <Route path="/" element={<LibraryPage />} />
        <Route path="/projects/:projectId" element={<ProjectPage />} />
        <Route path="/projects/:projectId/export" element={<ExportPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </div>
  );
}
