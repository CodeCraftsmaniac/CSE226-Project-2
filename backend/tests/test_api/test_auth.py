"""Authentication endpoint tests."""

from app.api.v1 import auth as auth_routes


def test_auth_config(test_client):
    """Test auth config endpoint returns config."""
    response = test_client.get("/auth/config")
    assert response.status_code == 200
    data = response.json()
    assert "config" in data
    assert "supabase_url" in data["config"]


def test_auth_user_without_token(test_client):
    """Test /auth/user without token returns error."""
    response = test_client.get("/auth/user")
    assert response.status_code == 401


def test_auth_me_without_token(test_client):
    """Test /auth/me without token returns error."""
    response = test_client.get("/auth/me")
    assert response.status_code == 401


def test_device_code_request(test_client):
    """Test device code generation."""
    response = test_client.post("/auth/device/code")
    assert response.status_code == 200
    data = response.json()
    assert "device_code" in data
    assert "user_code" in data
    assert "verification_url" in data
    assert "expires_in" in data


def test_device_code_poll_invalid(test_client):
    """Test polling with invalid device code."""
    response = test_client.post("/auth/device/poll", json={"device_code": "invalid-code"})
    assert response.status_code == 400


def test_auth_google_requires_verified_access_token(test_client, monkeypatch):
    """Direct email-only login must be rejected."""
    monkeypatch.setattr(
        auth_routes,
        "get_db_functions",
        lambda: (lambda **kwargs: {"id": "db-1", "email": "user@example.com"}, None, None, None, None),
    )
    monkeypatch.setattr(
        auth_routes,
        "get_dependencies",
        lambda: (None, None, None, True, True),
    )

    response = test_client.post(
        "/auth/google",
        json={"email": "user@example.com", "name": "User", "provider": "cli"},
    )

    assert response.status_code == 400
    assert "access token" in response.json()["detail"].lower()


def test_auth_google_rejects_email_mismatch(test_client, monkeypatch):
    """Posted email must match the verified token identity."""
    monkeypatch.setattr(
        auth_routes,
        "get_db_functions",
        lambda: (lambda **kwargs: {"id": "db-1", "email": "verified@example.com"}, None, None, None, None),
    )
    monkeypatch.setattr(
        auth_routes,
        "get_dependencies",
        lambda: (None, None, None, True, True),
    )
    monkeypatch.setattr(
        auth_routes,
        "verify_supabase_access_token",
        lambda token: {
            "id": "supabase-user",
            "email": "verified@example.com",
            "name": "Verified User",
            "avatar_url": "",
            "provider": "google",
        },
    )

    response = test_client.post(
        "/auth/google",
        json={
            "email": "different@example.com",
            "name": "Posted User",
            "provider": "google",
            "access_token": "token-123",
        },
    )

    assert response.status_code == 403
    assert "does not match" in response.json()["detail"].lower()


def test_auth_google_uses_verified_identity(test_client, monkeypatch):
    """The backend should trust the verified token identity, not the posted profile fields."""
    captured = {}

    def fake_create_user(email, name, provider="google"):
        captured["email"] = email
        captured["name"] = name
        captured["provider"] = provider
        return {
            "id": "db-user-1",
            "email": email,
            "name": name,
            "provider": provider,
            "avatar_url": "",
        }

    monkeypatch.setattr(
        auth_routes,
        "get_db_functions",
        lambda: (fake_create_user, None, None, None, lambda: None),
    )
    monkeypatch.setattr(
        auth_routes,
        "get_dependencies",
        lambda: (None, None, None, True, True),
    )
    monkeypatch.setattr(
        auth_routes,
        "verify_supabase_access_token",
        lambda token: {
            "id": "supabase-user",
            "email": "verified@example.com",
            "name": "Verified User",
            "avatar_url": "https://example.com/avatar.png",
            "provider": "google",
        },
    )

    response = test_client.post(
        "/auth/google",
        json={
            "email": "verified@example.com",
            "name": "Untrusted Name",
            "avatar_url": "https://bad.example/avatar.png",
            "provider": "cli",
            "access_token": "verified-token",
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["token"] == "verified-token"
    assert data["user"]["id"] == "supabase-user"
    assert data["user"]["db_id"] == "db-user-1"
    assert data["user"]["email"] == "verified@example.com"
    assert data["user"]["name"] == "Verified User"
    assert captured == {
        "email": "verified@example.com",
        "name": "Verified User",
        "provider": "google",
    }
