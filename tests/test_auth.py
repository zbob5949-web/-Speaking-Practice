"""账号体系端到端测试：注册、登录、刷新、游客、状态。"""
from fastapi.testclient import TestClient

from app.main import app


def test_auth_register_login_refresh_flow(tmp_path, monkeypatch):
    db_path = tmp_path / "coach.sqlite"
    monkeypatch.setenv("COACH_DB_PATH", str(db_path))
    monkeypatch.setenv("JWT_SECRET", "test-secret")
    client = TestClient(app)

    # 注册
    reg = client.post("/api/auth/register", json={"phone": "13800138000", "password": "secret123"})
    assert reg.status_code == 200
    body = reg.json()
    assert body["status"] == "success"
    access_token = body["access_token"]
    refresh_token = body["refresh_token"]

    # 重复注册 400
    dup = client.post("/api/auth/register", json={"phone": "13800138000", "password": "secret123"})
    assert dup.status_code == 400

    # 登录成功
    login = client.post("/api/auth/login", json={"phone": "13800138000", "password": "secret123"})
    assert login.status_code == 200
    assert login.json()["access_token"]

    # 密码错误 401
    bad = client.post("/api/auth/login", json={"phone": "13800138000", "password": "wrong123"})
    assert bad.status_code == 401

    # 带 token 的身份是 user
    ok = client.get("/api/auth/status", headers={"Authorization": f"Bearer {access_token}"})
    assert ok.status_code == 200
    assert ok.json()["identity"]["type"] == "user"

    # 未登录是 anonymous
    anon = client.get("/api/auth/status")
    assert anon.status_code == 200
    assert anon.json()["identity"]["type"] == "anonymous"

    # refresh 换取新 access token
    refreshed = client.post("/api/auth/refresh", json={"refresh_token": refresh_token})
    assert refreshed.status_code == 200
    assert refreshed.json()["access_token"]

    # 无效 refresh token 401
    bad_refresh = client.post("/api/auth/refresh", json={"refresh_token": "not-a-token"})
    assert bad_refresh.status_code == 401

    # 游客模式
    guest = client.post("/api/auth/guest")
    assert guest.status_code == 200
    assert guest.json()["type"] == "guest"
    guest_status = client.get(
        "/api/auth/status",
        headers={"Authorization": f"Bearer {guest.json()['token']}"},
    )
    assert guest_status.json()["identity"]["type"] == "guest"
