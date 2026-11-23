from pathlib import Path
import shutil

from fastapi.testclient import TestClient

FIXTURE = Path(__file__).parent / "fixtures" / "short_clean.mp4"


def test_health_and_consent(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("WOOMBA_LIBRARY", str(tmp_path))
    from woomba_api.deps import _conn_for
    from woomba_api.main import app

    _conn_for.cache_clear()
    client = TestClient(app)
    assert client.get("/api/health").json()["status"] == "ok"
    consent = client.get("/api/consent").json()
    assert consent["accepted"] is False
    accepted = client.post("/api/consent", json={"accept": True}).json()
    assert accepted["accepted"] is True
    created = client.post("/api/projects", json={"id": "api-demo", "title": "API"}).json()
    assert created["id"] == "api-demo"
    listed = client.get("/api/projects").json()
    assert listed[0]["id"] == "api-demo"
    library = client.get("/api/library").json()
    assert library["inbox"].endswith("inbox")


def test_import_sources_and_media(tmp_path: Path, monkeypatch) -> None:
    assert FIXTURE.exists()
    monkeypatch.setenv("WOOMBA_LIBRARY", str(tmp_path))
    from woomba_api.deps import _conn_for
    from woomba_api.main import app

    _conn_for.cache_clear()
    client = TestClient(app)
    client.post("/api/consent", json={"accept": True})
    client.post("/api/projects", json={"id": "media-demo", "title": "Media"})
    sources = tmp_path / "projects" / "media-demo" / "sources"
    sources.mkdir(parents=True, exist_ok=True)
    shutil.copy2(FIXTURE, sources / "clip.mp4")
    imported = client.post("/api/projects/media-demo/import", json={"source": "sources"}).json()
    assert imported["added"] == 1
    path = imported["timeline"]["clips"][0]["path"]
    media = client.get(f"/api/projects/media-demo/media/{path}")
    assert media.status_code == 200
    assert len(media.content) > 100


def test_delete_clip_and_auto_job_type(tmp_path: Path, monkeypatch) -> None:
    assert FIXTURE.exists()
    monkeypatch.setenv("WOOMBA_LIBRARY", str(tmp_path))
    from woomba_api.deps import _conn_for
    from woomba_api.main import app

    _conn_for.cache_clear()
    client = TestClient(app)
    client.post("/api/consent", json={"accept": True})
    client.post("/api/projects", json={"id": "del-api", "title": "Del"})
    sources = tmp_path / "projects" / "del-api" / "sources"
    sources.mkdir(parents=True, exist_ok=True)
    shutil.copy2(FIXTURE, sources / "clip.mp4")
    imported = client.post("/api/projects/del-api/import", json={"source": "sources"}).json()
    clip_id = imported["timeline"]["clips"][0]["id"]
    deleted = client.delete(f"/api/projects/del-api/clips/{clip_id}").json()
    assert deleted["remaining"] == 0
    job = client.post("/api/projects/del-api/jobs", json={"type": "auto_roughcut"}).json()
    assert job["type"] == "auto_roughcut"
    finish = client.post("/api/projects/del-api/jobs", json={"type": "finish"}).json()
    assert finish["type"] == "finish"
    proxy = client.post("/api/projects/del-api/jobs", json={"type": "proxy"}).json()
    assert proxy["type"] == "proxy"


def test_upload_files(tmp_path: Path, monkeypatch) -> None:
    assert FIXTURE.exists()
    monkeypatch.setenv("WOOMBA_LIBRARY", str(tmp_path))
    from woomba_api.deps import _conn_for
    from woomba_api.main import app

    _conn_for.cache_clear()
    client = TestClient(app)
    client.post("/api/consent", json={"accept": True})
    client.post("/api/projects", json={"id": "up-demo", "title": "Up"})
    with FIXTURE.open("rb") as handle:
        response = client.post(
            "/api/projects/up-demo/upload",
            files=[("files", ("clip.mp4", handle, "video/mp4"))],
        )
    assert response.status_code == 200
    payload = response.json()
    assert payload["added"] == 1
    assert payload["clip_count"] == 1
