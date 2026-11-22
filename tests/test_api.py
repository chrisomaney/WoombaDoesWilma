from pathlib import Path

from fastapi.testclient import TestClient


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
