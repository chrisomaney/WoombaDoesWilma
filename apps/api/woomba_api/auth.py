from __future__ import annotations

from fastapi import Header, HTTPException, Request

from woomba.settings import get_settings


def enforce_token(request: Request, x_woomba_token: str | None = Header(default=None)) -> None:
    settings = get_settings()
    # Localhost binds do not require a token.
    client_host = request.client.host if request.client else "127.0.0.1"
    local = client_host in {"127.0.0.1", "::1", "localhost"}
    if local and not settings.lan:
        return
    if not settings.token:
        if settings.lan or not local:
            raise HTTPException(status_code=503, detail="WOOMBA_TOKEN must be set for LAN access")
        return
    provided = x_woomba_token or request.query_params.get("token")
    if provided != settings.token:
        raise HTTPException(status_code=401, detail="Invalid or missing token")
