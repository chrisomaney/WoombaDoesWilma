from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from woomba.consent import CONSENT_TEXT, accept_consent, read_consent
from woomba.paths import ensure_library_layout
from woomba.settings import get_settings

app = FastAPI(title="WoombaDoesWilma", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ConsentAcceptBody(BaseModel):
    accept: bool = True


@app.on_event("startup")
def _startup() -> None:
    settings = get_settings()
    ensure_library_layout(settings.resolve_library())


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "woomba"}


@app.get("/api/consent")
def get_consent() -> dict:
    settings = get_settings()
    record = read_consent(settings.resolve_library())
    return {
        "accepted": record.accepted,
        "version": record.version,
        "accepted_at": record.accepted_at,
        "text": record.text or CONSENT_TEXT,
    }


@app.post("/api/consent")
def post_consent(body: ConsentAcceptBody) -> dict:
    if not body.accept:
        raise HTTPException(status_code=400, detail="Consent must be accepted to continue.")
    settings = get_settings()
    record = accept_consent(settings.resolve_library())
    return {
        "accepted": record.accepted,
        "version": record.version,
        "accepted_at": record.accepted_at,
        "text": record.text,
    }
