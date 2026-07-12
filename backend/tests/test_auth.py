"""
Auth endpoint tests: register, login, /me, change-password, refresh.
"""
import pytest


def test_register_success(client):
    res = client.post("/api/auth/register", json={
        "email": "newuser@example.com",
        "name": "New User",
        "password": "SecurePass123"
    })
    assert res.status_code == 201
    data = res.json()
    assert data["email"] == "newuser@example.com"
    assert data["name"] == "New User"
    assert "password" not in data
    assert "password_hash" not in data


def test_register_duplicate_email(client, test_user):
    res = client.post("/api/auth/register", json={
        "email": "test@example.com",
        "name": "Duplicate",
        "password": "SecurePass123"
    })
    assert res.status_code in [400, 409]


def test_login_success(client, test_user):
    res = client.post("/api/auth/login", json={
        "email": "test@example.com",
        "password": "TestPass123"
    })
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


def test_login_wrong_password(client, test_user):
    res = client.post("/api/auth/login", json={
        "email": "test@example.com",
        "password": "WrongPassword123"
    })
    assert res.status_code == 401


def test_login_unknown_email(client):
    res = client.post("/api/auth/login", json={
        "email": "nobody@example.com",
        "password": "AnyPass123"
    })
    assert res.status_code == 401


def test_me_authenticated(client, auth_headers):
    res = client.get("/api/auth/me", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["email"] == "test@example.com"


def test_me_unauthenticated(client):
    res = client.get("/api/auth/me")
    assert res.status_code == 401


def test_refresh_token(client, auth_headers):
    res = client.post("/api/auth/refresh", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert "access_token" in data


def test_change_password(client, auth_headers):
    res = client.post("/api/auth/change-password", headers=auth_headers, json={
        "current_password": "TestPass123",
        "new_password": "NewSecurePass456"
    })
    assert res.status_code == 200
    assert res.json()["message"] == "Password updated successfully."

    # Verify new password works for login
    login_res = client.post("/api/auth/login", json={
        "email": "test@example.com",
        "password": "NewSecurePass456"
    })
    assert login_res.status_code == 200


def test_change_password_wrong_current(client, auth_headers):
    res = client.post("/api/auth/change-password", headers=auth_headers, json={
        "current_password": "WrongOldPassword",
        "new_password": "NewSecurePass456"
    })
    assert res.status_code == 401
