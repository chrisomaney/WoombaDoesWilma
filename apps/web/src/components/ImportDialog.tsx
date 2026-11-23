import { useRef, useState } from "react";

type Props = {
  open: boolean;
  busy?: boolean;
  inboxPath?: string;
  onClose: () => void;
  onUpload: (files: FileList) => Promise<void>;
  onImportInbox: () => Promise<void>;
  onScanSources: () => Promise<void>;
};

export default function ImportDialog({
  open,
  busy,
  inboxPath,
  onClose,
  onUpload,
  onImportInbox,
  onScanSources,
}: Props) {
  const inputRef = useRef<HTMLInputElement>(null);
  const [error, setError] = useState<string | null>(null);

  if (!open) {
    return null;
  }

  async function handleFiles(files: FileList | null) {
    if (!files || files.length === 0) return;
    setError(null);
    try {
      await onUpload(files);
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    }
  }

  return (
    <div className="dialog-backdrop" role="presentation" onClick={onClose}>
      <div
        className="dialog"
        role="dialog"
        aria-modal="true"
        aria-label="Import clips"
        onClick={(e) => e.stopPropagation()}
      >
        <h2>Import clips</h2>
        <p className="muted">Choose files from this Mac, or pull from the library folders.</p>

        <div className="dialog-drop" onClick={() => inputRef.current?.click()}>
          <strong>Choose video files</strong>
          <span className="muted">.mp4 .mov .mkv .m4v .webm .avi</span>
          <input
            ref={inputRef}
            type="file"
            accept="video/*,.mp4,.mov,.mkv,.m4v,.webm,.avi"
            multiple
            hidden
            onChange={(e) => handleFiles(e.target.files)}
          />
        </div>

        {inboxPath ? (
          <p className="muted">
            Or drop files into <code>{inboxPath}</code> then import inbox.
          </p>
        ) : null}

        <div className="actions">
          <button
            className="btn btn-primary"
            disabled={busy}
            onClick={() => inputRef.current?.click()}
          >
            Browse files…
          </button>
          <button
            className="btn"
            disabled={busy}
            onClick={async () => {
              setError(null);
              try {
                await onImportInbox();
                onClose();
              } catch (err) {
                setError(err instanceof Error ? err.message : "Inbox import failed");
              }
            }}
          >
            Import inbox
          </button>
          <button
            className="btn"
            disabled={busy}
            onClick={async () => {
              setError(null);
              try {
                await onScanSources();
                onClose();
              } catch (err) {
                setError(err instanceof Error ? err.message : "Scan failed");
              }
            }}
          >
            Scan sources
          </button>
          <button className="btn" disabled={busy} onClick={onClose}>
            Cancel
          </button>
        </div>
        {error ? <p style={{ color: "var(--danger)" }}>{error}</p> : null}
      </div>
    </div>
  );
}
