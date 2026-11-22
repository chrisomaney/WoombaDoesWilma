from __future__ import annotations

from fastapi import Header, HTTPException, Request

from woomba.settings import get_settings


def enforce_token(request: Request, x_woomba_token: str | None = Header(default=None)) -> None:
    """Require token only when LAN mode is enabled."""
    settings = get_settings()
    if not settings.lan:
        return
    if not settings.token:
        raise HTTPException(status_code=503, detail="WOOMBA_TOKEN must be set for LAN access")
    provided = x_woomba_token or request.query_params.get("token")
    if provided != settings.token:
        raise HTTPException(status_code=401, detail="Invalid or missing token")
