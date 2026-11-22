from __future__ import annotations

from pathlib import Path

import typer
import uvicorn

from woomba.consent import CONSENT_TEXT, accept_consent, read_consent, require_consent
from woomba.db import connect
from woomba.jobs import create_project, enqueue_job, get_project, list_projects
from woomba.media.export import export_project
from woomba.media.import_clips import discover_inbox, import_paths
from woomba.media.polish import apply_polish_defaults
from woomba.media.privacy import apply_privacy_flags
from woomba.media.roughcut import build_roughcut
from woomba.models import JobType
from woomba.paths import db_path, ensure_library_layout
from woomba.settings import get_settings
from woomba.timeline import load_timeline, save_timeline
from woomba.workers.runner import run_job

app = typer.Typer(add_completion=False, no_args_is_help=True, help="WoombaDoesWilma local studio CLI")
project_app = typer.Typer(help="Manage projects")
app.add_typer(project_app, name="project")


def _root():
    settings = get_settings()
    root = ensure_library_layout(settings.resolve_library())
    require_consent(root)
    return root


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


@project_app.command("create")
def project_create(
    project_id: str = typer.Argument(..., help="Project id (letters, numbers, _-)"),
    title: str | None = typer.Option(None, help="Optional title"),
) -> None:
    root = _root()
    conn = connect(db_path(root))
    project = create_project(conn, root, project_id, title)
    typer.echo(f"Created project {project.id}")


@project_app.command("list")
def project_list() -> None:
    root = _root()
    conn = connect(db_path(root))
    projects = list_projects(conn)
    if not projects:
        typer.echo("No projects yet.")
        return
    for project in projects:
        typer.echo(f"{project.id}\t{project.title}")


@app.command("import")
def import_cmd(
    project_id: str = typer.Option(..., "--project", help="Target project id"),
    paths: list[Path] | None = typer.Argument(None, help="Clip paths (defaults to inbox)"),
) -> None:
    root = _root()
    conn = connect(db_path(root))
    if not get_project(conn, project_id):
        create_project(conn, root, project_id)
    sources = list(paths) if paths else discover_inbox(root)
    if not sources:
        typer.echo("No clips found to import.", err=True)
        raise typer.Exit(code=1)
    timeline = import_paths(root, project_id, sources)
    typer.echo(f"Imported {len(timeline.clips)} clip(s) into {project_id}")


@app.command("analyze")
def analyze_cmd(project_id: str = typer.Argument(...)) -> None:
    root = _root()
    conn = connect(db_path(root))
    job = enqueue_job(conn, project_id, JobType.analyze)
    run_job(conn, root, job.id)
    typer.echo(f"analyze {job.status.value}")


@app.command("roughcut")
def roughcut_cmd(
    project_id: str = typer.Argument(...),
    silence: float = typer.Option(-35.0, "--silence", help="Silence threshold dB"),
) -> None:
    root = _root()
    timeline = build_roughcut(root, project_id, noise_db=silence)
    keep = sum(1 for s in timeline.segments if s.state == "keep")
    cut = sum(1 for s in timeline.segments if s.state == "cut")
    typer.echo(f"roughcut complete: keep={keep} cut={cut}")


@app.command("polish")
def polish_cmd(project_id: str = typer.Argument(...)) -> None:
    root = _root()
    apply_polish_defaults(root, project_id)
    typer.echo("polish marked")


@app.command("privacy")
def privacy_cmd(
    project_id: str = typer.Argument(...),
    mute: bool = typer.Option(False, help="Mute all keep segments"),
    blur: bool = typer.Option(False, help="Blur keep segments (full-frame soft blur in v1)"),
) -> None:
    root = _root()
    apply_privacy_flags(root, project_id, mute_all_keep=mute, blur_all_keep=blur)
    typer.echo("privacy flags updated")


@app.command("export")
def export_cmd(
    project_id: str = typer.Argument(...),
    codec: str = typer.Option("h264", help="h264 or h265"),
) -> None:
    root = _root()
    timeline = load_timeline(root, project_id)
    if codec in {"h264", "h265"}:
        timeline.export.codec = codec  # type: ignore[assignment]
        save_timeline(root, timeline)
    out = export_project(root, project_id)
    typer.echo(f"exported {out}")


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
