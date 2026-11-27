"""
Health check, request ID correlation, analytics, settings, rate limiter 429 behavior,
and WebSocket auth/scoping tests.
"""
import pytest
from starlette.websockets import WebSocketDisconnect


def test_health_endpoint_and_request_id_header(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json() == {"status": "ok", "database": "connected"}
    assert "x-request-id" in res.headers


def test_analytics_endpoint(client, auth_headers):
    client.post(
        "/api/tickets/",
        headers=auth_headers,
        json={
            "title": "Analytics sample ticket",
            "description": "Sample ticket created to verify analytics endpoint metrics.",
            "category": "Technical",
            "urgency": "Medium",
        },
    )

    res = client.get("/api/analytics", headers=auth_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["task_completion"]["total"] >= 1
    assert "status_counts" in data
    assert "category_counts" in data
    assert "daily_trends" in data
    assert "resolution_times" in data
    assert "escalation_stats" in data


def test_settings_get_and_patch(client, auth_headers):
    get_res = client.get("/api/settings", headers=auth_headers)
    assert get_res.status_code == 200
    assert get_res.json()["has_nvidia_key"] is False
    assert get_res.json()["has_openai_key"] is False

    patch_res = client.patch(
        "/api/settings",
        headers=auth_headers,
        json={"name": "Updated Tester"},
    )
    assert patch_res.status_code == 200
    assert patch_res.json()["name"] == "Updated Tester"


def test_rate_limiter_returns_429_json_response(client):
    # /api/auth/register allows 5 requests per minute
    for i in range(5):
        res = client.post(
            "/api/auth/register",
            json={
                "email": f"ratelimit_{i}@example.com",
                "name": "Rate User",
                "password": "ValidPass123",
            },
        )
        assert res.status_code == 201

    throttled = client.post(
        "/api/auth/register",
        json={
            "email": "ratelimit_over@example.com",
            "name": "Rate User",
            "password": "ValidPass123",
        },
    )
    assert throttled.status_code == 429
    assert throttled.json()["detail"]["error_code"] == "RATE_LIMIT_EXCEEDED"


def test_websocket_auth_and_ping_pong(client, test_user):
    # Missing token must be rejected
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/api/ws/tickets"):
            pass

    # Invalid token must be rejected
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/api/ws/tickets?token=invalid.jwt.token"):
            pass

    # Valid token connects and handles ping/pong
    login_res = client.post(
        "/api/auth/login",
        json={"email": "test@example.com", "password": "TestPass123"},
    )
    token = login_res.json()["access_token"]

    with client.websocket_connect(f"/api/ws/tickets?token={token}") as ws:
        ws.send_text("ping")
        assert ws.receive_text() == "pong"
