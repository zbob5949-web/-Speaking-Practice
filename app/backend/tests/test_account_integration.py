import json
import sqlite3
import pytest
from fastapi.testclient import TestClient
from app.main import app, _hits
from app.db import connect, init_db

@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("COACH_DB_PATH", str(tmp_path / "test.sqlite"))
    monkeypatch.setenv("JWT_SECRET", "integration-test-secret-with-32-characters")
    monkeypatch.setenv("LLM_PROVIDER", "fake")
    monkeypatch.delenv("ACCESS_PASSWORD", raising=False)
    _hits.clear()
    return TestClient(app)

def register(client, phone):
    result = client.post("/api/auth/register", json={"phone": phone, "password": "secret123"})
    assert result.status_code == 200
    return {"Authorization": "Bearer " + result.json()["access_token"]}

def test_preferences_sync_to_admin(client, tmp_path):
    headers = register(client, "13800000111")
    other = register(client, "13800000222")
    assert client.put("/api/auth/me", headers=headers, json={"username": " Alice ", "avatar": "panda"}).json()["username"] == "Alice"
    assert client.get("/api/auth/me", headers=headers).json()["avatar"] == "panda"
    assert client.get("/api/auth/me", headers=other).json()["username"] != "Alice"
    assert client.put("/api/auth/me", headers=headers, json={"username": " ", "avatar": "fox"}).status_code == 422
    assert client.put("/api/auth/me", headers=headers, json={"username": "Alice", "avatar": "invalid"}).status_code == 422
    assert client.get("/api/admin/users", headers=headers).status_code == 403
    with connect(tmp_path / "test.sqlite") as conn:
        conn.execute("UPDATE users SET role='admin' WHERE phone='13800000222'")
    response = client.get("/api/admin/users?keyword=Alice", headers=other)
    assert response.status_code == 200
    assert response.json()["data"]["items"][0]["username"] == "Alice"
    assert response.json()["data"]["items"][0]["avatar"] == "panda"

def test_favorites_are_isolated_idempotent_and_admin_managed(client, tmp_path):
    headers = register(client, "13800000333")
    other = register(client, "13800000444")
    path = "/api/favorites/airport-check-in"
    assert client.post(path, headers=headers).status_code == 200
    assert client.post(path, headers=headers).json()["favorite"] is False
    assert len(client.get("/api/favorites", headers=headers).json()["favorites"]) == 1
    assert client.get("/api/favorites", headers=other).json()["favorites"] == []
    assert not client.delete(path, headers=other).json()["removed"]
    catalog = client.get("/api/scenarios", headers=headers).json()["scenarios"]
    assert next(row for row in catalog if row["id"] == "airport-check-in")["is_favorite"]
    assert client.post("/api/favorites/invalid", headers=headers).status_code == 404
    with connect(tmp_path / "test.sqlite") as conn:
        conn.execute("UPDATE users SET role='admin' WHERE phone='13800000444'")
    listing = client.get("/api/admin/tables/account_favorites", headers=other)
    assert listing.status_code == 200
    row = listing.json()["data"]["items"][0]
    assert row["owner_key"] == "13800000333"
    deleted = client.delete(f"/api/admin/tables/account_favorites/{row['id']}", headers=other)
    assert deleted.status_code == 200
    assert client.get("/api/favorites", headers=headers).json()["favorites"] == []

def test_guest_preferences_and_favorites(client):
    guest = client.post("/api/auth/guest").json()
    headers = {"Authorization": "Bearer " + guest["token"]}
    assert client.put("/api/auth/me", headers=headers, json={"username": "Visitor", "avatar": "cat"}).json()["is_guest"]
    assert client.get("/api/auth/me", headers=headers).json()["username"] == "Visitor"
    assert client.post("/api/favorites/hotel-check-in", headers=headers).status_code == 200
    assert len(client.get("/api/favorites", headers=headers).json()["favorites"]) == 1

def test_voice_mode_survives_stream_and_reload(client):
    headers = register(client, "13800000555")
    session = client.post("/api/sessions/start", headers=headers, json={"scenario_id": "free_talk"})
    assert session.status_code == 200
    sid = session.json()["session"]["id"]
    response = client.post("/api/sessions/turn/stream", headers=headers, json={"session_id": sid, "text": "Hello, I want to practice English.", "input_mode": "voice"})
    assert response.status_code == 200
    payloads = [json.loads(line[6:]) for line in response.text.splitlines() if line.startswith("data: ")]
    meta = next(item for item in payloads if item.get("type") == "meta")
    assert meta["user_turn"]["input_mode"] == "voice"
    assert meta["assistant_turn"]["input_mode"] == "voice"
    restored = client.post("/api/sessions/start", headers=headers, json={"scenario_id": "free_talk"}).json()
    assert [turn["input_mode"] for turn in restored["turns"][-2:]] == ["voice", "voice"]

def test_existing_database_migration_preserves_accounts(tmp_path):
    path = tmp_path / "old.sqlite"
    with sqlite3.connect(path) as conn:
        conn.execute("CREATE TABLE users (id INTEGER PRIMARY KEY, phone TEXT, password TEXT)")
        conn.execute("INSERT INTO users VALUES (1, '13800000000', 'existing-hash')")
    init_db(path)
    init_db(path)
    with connect(path) as conn:
        row = conn.execute("SELECT * FROM users WHERE id=1").fetchone()
        assert row["password"] == "existing-hash"
        assert row["avatar"] == "fox"
