from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path

from woomba.paths import consent_path

CONSENT_VERSION = 1
CONSENT_TEXT = (
    "I confirm this studio will only be used with footage I own or that was "
    "created with the informed consent of all adults appearing in it. "
    "I will not use this software for non-consensual deepfakes or third-party face-swap."
)


@dataclass
class ConsentRecord:
    accepted: bool
    version: int
    accepted_at: str | None
    text: str


def read_consent(library_root: Path) -> ConsentRecord:
    path = consent_path(library_root)
    if not path.exists():
        return ConsentRecord(
            accepted=False,
            version=CONSENT_VERSION,
            accepted_at=None,
            text=CONSENT_TEXT,
        )
    data = json.loads(path.read_text(encoding="utf-8"))
    return ConsentRecord(
        accepted=bool(data.get("accepted")),
        version=int(data.get("version", 0)),
        accepted_at=data.get("accepted_at"),
        text=str(data.get("text", CONSENT_TEXT)),
    )


def accept_consent(library_root: Path) -> ConsentRecord:
    record = ConsentRecord(
        accepted=True,
        version=CONSENT_VERSION,
        accepted_at=datetime.now(timezone.utc).isoformat(),
        text=CONSENT_TEXT,
    )
    path = consent_path(library_root)
    path.write_text(json.dumps(asdict(record), indent=2) + "\n", encoding="utf-8")
    return record


def require_consent(library_root: Path) -> ConsentRecord:
    record = read_consent(library_root)
    if not record.accepted or record.version != CONSENT_VERSION:
        raise PermissionError("Consent acknowledgment required before using the studio.")
    return record
