from __future__ import annotations

import uvicorn
import typer

from woomba.consent import CONSENT_TEXT, accept_consent, read_consent
from woomba.paths import ensure_library_layout
from woomba.settings import get_settings

app = typer.Typer(add_completion=False, no_args_is_help=True, help="WoombaDoesWilma local studio CLI")


@app.command("init")
def init_cmd(
    i_consent: bool = typer.Option(
        False,
        "--i-consent",
        help="Acknowledge consenting-adult / owned-footage terms",
    ),
) -> None:
    """Create the local library layout and optionally accept consent."""
    settings = get_settings()
    root = ensure_library_layout(settings.resolve_library())
    typer.echo(f"Library ready at {root}")
    if not i_consent:
        typer.echo("Consent not accepted yet. Re-run with --i-consent after reading the terms:")
        typer.echo(CONSENT_TEXT)
        raise typer.Exit(code=0)
    record = accept_consent(root)
    typer.echo(f"Consent accepted at {record.accepted_at}")


@app.command("consent")
def consent_cmd() -> None:
    """Show consent status."""
    settings = get_settings()
    record = read_consent(settings.resolve_library())
    typer.echo(f"accepted={record.accepted} version={record.version} at={record.accepted_at}")
    typer.echo(record.text)


@app.command("serve")
def serve_cmd(
    host: str | None = typer.Option(None, help="Override bind host"),
    port: int | None = typer.Option(None, help="Override bind port"),
) -> None:
    """Run the local API server."""
    settings = get_settings()
    ensure_library_layout(settings.resolve_library())
    bind_host = host or settings.host
    bind_port = port or settings.port
    if settings.lan and bind_host in {"127.0.0.1", "localhost"}:
        bind_host = "0.0.0.0"
    if bind_host not in {"127.0.0.1", "localhost"} and not settings.token:
        typer.echo("LAN bind requires WOOMBA_TOKEN to be set.", err=True)
        raise typer.Exit(code=1)
    typer.echo(f"Serving on http://{bind_host}:{bind_port}")
    uvicorn.run("woomba_api.main:app", host=bind_host, port=bind_port, reload=False)


if __name__ == "__main__":
    app()
