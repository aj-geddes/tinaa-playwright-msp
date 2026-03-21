"""
Tests for the alert channel configuration API routes.

Covers:
- GET /api/v1/alerts/channels: returns list
- POST /api/v1/alerts/channels: adds a channel, returns id + status
- DELETE /api/v1/alerts/channels/{id}: removes existing channel
- DELETE /api/v1/alerts/channels/{id}: 404 for unknown id
- PATCH /api/v1/alerts/channels/{id}: updates channel fields
- PATCH /api/v1/alerts/channels/{id}: 404 for unknown id
- POST /api/v1/alerts/channels/test: returns success/failure dict
- GET /api/v1/alerts/rules: returns list
- POST /api/v1/alerts/rules: adds rule, returns id
- DELETE /api/v1/alerts/rules/{id}: removes existing rule
- DELETE /api/v1/alerts/rules/{id}: 404 for unknown id
- GET /api/v1/alerts/setup-guides: returns all five channel types
- router prefix is /alerts
"""

import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI


def _make_app():
    from tinaa.api.routes.alerts_config import router

    app = FastAPI()
    app.include_router(router, prefix="/api/v1")
    return app


@pytest.fixture()
def client():
    """Fresh TestClient with a clean in-memory store per test."""
    # Re-import the module so the store is isolated per test
    import importlib
    import tinaa.api.routes.alerts_config as mod
    importlib.reload(mod)
    app = FastAPI()
    app.include_router(mod.router, prefix="/api/v1")
    return TestClient(app)


# ---------------------------------------------------------------------------
# GET /alerts/channels
# ---------------------------------------------------------------------------

class TestListChannels:
    def test_returns_list(self, client):
        resp = client.get("/api/v1/alerts/channels")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)

    def test_empty_initially(self, client):
        resp = client.get("/api/v1/alerts/channels")
        assert resp.json() == []


# ---------------------------------------------------------------------------
# POST /alerts/channels
# ---------------------------------------------------------------------------

class TestAddChannel:
    def test_add_slack_channel(self, client):
        payload = {
            "channel_type": "slack",
            "name": "Engineering Slack",
            "enabled": True,
            "config": {"webhook_url": "https://hooks.slack.com/services/abc"},
        }
        resp = client.post("/api/v1/alerts/channels", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data
        assert data["type"] == "slack"
        assert data["name"] == "Engineering Slack"
        assert data["status"] == "configured"

    def test_add_teams_channel(self, client):
        payload = {
            "channel_type": "teams",
            "name": "Ops Teams",
            "enabled": True,
            "config": {"webhook_url": "https://outlook.office.com/webhook/xyz"},
        }
        resp = client.post("/api/v1/alerts/channels", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["type"] == "teams"
        assert "id" in data

    def test_added_channel_appears_in_list(self, client):
        client.post(
            "/api/v1/alerts/channels",
            json={
                "channel_type": "slack",
                "name": "Alerts",
                "enabled": True,
                "config": {"webhook_url": "https://hooks.slack.com/x"},
            },
        )
        resp = client.get("/api/v1/alerts/channels")
        assert len(resp.json()) == 1
        assert resp.json()[0]["name"] == "Alerts"

    def test_returned_id_is_string(self, client):
        resp = client.post(
            "/api/v1/alerts/channels",
            json={
                "channel_type": "email",
                "name": "SMTP",
                "enabled": False,
                "config": {},
            },
        )
        assert isinstance(resp.json()["id"], str)
        assert len(resp.json()["id"]) > 0


# ---------------------------------------------------------------------------
# DELETE /alerts/channels/{id}
# ---------------------------------------------------------------------------

class TestRemoveChannel:
    def test_remove_existing_channel(self, client):
        add_resp = client.post(
            "/api/v1/alerts/channels",
            json={"channel_type": "slack", "name": "X", "enabled": True, "config": {}},
        )
        channel_id = add_resp.json()["id"]
        del_resp = client.delete(f"/api/v1/alerts/channels/{channel_id}")
        assert del_resp.status_code == 200

    def test_channel_gone_after_removal(self, client):
        add_resp = client.post(
            "/api/v1/alerts/channels",
            json={"channel_type": "slack", "name": "X", "enabled": True, "config": {}},
        )
        channel_id = add_resp.json()["id"]
        client.delete(f"/api/v1/alerts/channels/{channel_id}")
        resp = client.get("/api/v1/alerts/channels")
        assert all(c["id"] != channel_id for c in resp.json())

    def test_remove_unknown_channel_returns_404(self, client):
        resp = client.delete("/api/v1/alerts/channels/nonexistent-id")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# PATCH /alerts/channels/{id}
# ---------------------------------------------------------------------------

class TestUpdateChannel:
    def test_update_enabled_flag(self, client):
        add_resp = client.post(
            "/api/v1/alerts/channels",
            json={"channel_type": "slack", "name": "X", "enabled": True, "config": {}},
        )
        channel_id = add_resp.json()["id"]
        patch_resp = client.patch(
            f"/api/v1/alerts/channels/{channel_id}",
            json={"enabled": False},
        )
        assert patch_resp.status_code == 200
        assert patch_resp.json()["enabled"] is False

    def test_update_unknown_channel_returns_404(self, client):
        resp = client.patch(
            "/api/v1/alerts/channels/no-such-id",
            json={"enabled": False},
        )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /alerts/channels/test
# ---------------------------------------------------------------------------

class TestTestChannel:
    def test_returns_success_or_failure_dict(self, client):
        payload = {
            "channel_type": "webhook",
            "config": {"url": "https://example.com/hook"},
        }
        resp = client.post("/api/v1/alerts/channels/test", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert "success" in data
        assert "message" in data
        assert isinstance(data["success"], bool)
        assert isinstance(data["message"], str)


# ---------------------------------------------------------------------------
# GET /alerts/rules
# ---------------------------------------------------------------------------

class TestListRules:
    def test_returns_list(self, client):
        resp = client.get("/api/v1/alerts/rules")
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)


# ---------------------------------------------------------------------------
# POST /alerts/rules
# ---------------------------------------------------------------------------

class TestAddRule:
    def test_add_rule_returns_id(self, client):
        payload = {
            "name": "quality-drop",
            "condition_type": "quality_score_drop",
            "severity": "warning",
            "channels": [],
            "threshold": {"drop_amount": 10},
        }
        resp = client.post("/api/v1/alerts/rules", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert "id" in data

    def test_added_rule_appears_in_list(self, client):
        client.post(
            "/api/v1/alerts/rules",
            json={"name": "my-rule", "condition_type": "test_failure"},
        )
        resp = client.get("/api/v1/alerts/rules")
        assert len(resp.json()) == 1


# ---------------------------------------------------------------------------
# DELETE /alerts/rules/{id}
# ---------------------------------------------------------------------------

class TestRemoveRule:
    def test_remove_existing_rule(self, client):
        add_resp = client.post(
            "/api/v1/alerts/rules",
            json={"name": "r1", "condition_type": "endpoint_down"},
        )
        rule_id = add_resp.json()["id"]
        del_resp = client.delete(f"/api/v1/alerts/rules/{rule_id}")
        assert del_resp.status_code == 200

    def test_remove_unknown_rule_returns_404(self, client):
        resp = client.delete("/api/v1/alerts/rules/nope")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# GET /alerts/setup-guides
# ---------------------------------------------------------------------------

class TestSetupGuides:
    def test_returns_dict(self, client):
        resp = client.get("/api/v1/alerts/setup-guides")
        assert resp.status_code == 200
        assert isinstance(resp.json(), dict)

    def test_all_five_channel_types_present(self, client):
        resp = client.get("/api/v1/alerts/setup-guides")
        guides = resp.json()
        for key in ("slack", "teams", "pagerduty", "email", "webhook"):
            assert key in guides, f"Missing guide for {key}"

    def test_each_guide_has_steps_and_fields(self, client):
        resp = client.get("/api/v1/alerts/setup-guides")
        for key, guide in resp.json().items():
            assert "steps" in guide, f"{key} guide missing 'steps'"
            assert "fields" in guide, f"{key} guide missing 'fields'"
            assert len(guide["steps"]) > 0, f"{key} guide has no steps"
            assert len(guide["fields"]) > 0, f"{key} guide has no fields"

    def test_teams_guide_has_webhook_url_field(self, client):
        resp = client.get("/api/v1/alerts/setup-guides")
        teams_fields = resp.json()["teams"]["fields"]
        field_names = [f["name"] for f in teams_fields]
        assert "webhook_url" in field_names


# ---------------------------------------------------------------------------
# Router registration in app.py
# ---------------------------------------------------------------------------

class TestRouterRegistration:
    def test_alerts_config_router_registered_in_app(self):
        from tinaa.api.app import create_app

        app = create_app()
        routes = [r.path for r in app.routes]
        alert_routes = [r for r in routes if "/alerts/" in r or r.endswith("/alerts")]
        assert len(alert_routes) > 0, "No alert config routes found in app"
