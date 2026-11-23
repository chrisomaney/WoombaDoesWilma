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
