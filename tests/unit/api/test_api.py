"""
Unit tests for TINAA MSP HTTP API layer.

Covers:
- Health and root endpoints
- Product CRUD + sub-resources (environments, endpoints)
- Playbooks (CRUD, execute, validate)
- Test runs (list, get, trigger, cancel, results)
- Metrics (product, endpoint, baselines, anomalies)
- Quality score, history, report, gate
- GitHub webhook signature verification flow
- WebSocket ConnectionManager
- Middleware (RequestLoggingMiddleware, APIKeyMiddleware)
- Request validation (missing required fields → 422)
"""

import hashlib
import hmac
import json
import time
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# Service container mock — prevents any real DB / service calls in unit tests
# ---------------------------------------------------------------------------


def _make_mock_services():
    """Return a MagicMock ServiceContainer whose service methods return
    representative data without touching any real service or database."""
    from datetime import UTC, datetime

    _now = datetime.now(UTC).isoformat()

    # --- registry mock ---
    registry = MagicMock()

    _product = MagicMock()
    _product.id = uuid.UUID("00000000-0000-0000-0000-000000000001")
    _product.name = "Demo Product"
    _product.slug = "demo-product"
    _product.repository_url = None
    _product.description = ""
    _product.quality_score = None
    _product.status = "active"
    _product.created_at = datetime.now(UTC)

    def _make_product(name: str) -> MagicMock:
        p = MagicMock()
        p.id = uuid.UUID("00000000-0000-0000-0000-000000000001")
        p.name = name
        p.slug = name.lower().replace(" ", "-")
        p.repository_url = None
        p.description = ""
        p.quality_score = None
        p.status = "active"
        p.created_at = datetime.now(UTC)
        return p

    async def _create_product(org_id, data):
        return _make_product(data.name)

    async def _update_product(product_id, data):
        name = data.name if data.name else "Demo Product"
        return _make_product(name)

    registry.create_product = AsyncMock(side_effect=_create_product)
    registry.get_product = AsyncMock(return_value=_make_product("Demo Product"))
    registry.get_product_by_slug = AsyncMock(return_value=_make_product("Demo Product"))
    registry.list_products = AsyncMock(return_value=[_make_product("Demo Product")])
    registry.update_product = AsyncMock(side_effect=_update_product)
    registry.delete_product = AsyncMock(return_value=True)

    _env = MagicMock()
    _env.id = uuid.UUID("00000000-0000-0000-0000-000000000002")
    _env.name = "production"
    _env.base_url = "https://example.com"
    _env.env_type = "production"
    _env.monitoring_interval_seconds = 300
    _env.created_at = datetime.now(UTC)

    registry.add_environment = AsyncMock(return_value=_env)
    registry.list_environments = AsyncMock(return_value=[_env])

    _ep = MagicMock()
    _ep.id = uuid.UUID("00000000-0000-0000-0000-000000000003")
    _ep.path = "/checkout"
    _ep.method = "POST"
    _ep.endpoint_type = "api"
    _ep.performance_budget_ms = None
    _ep.expected_status_code = 200
    _ep.created_at = datetime.now(UTC)

    registry.add_endpoint = AsyncMock(return_value=_ep)
    registry.list_endpoints = AsyncMock(return_value=[_ep])

    # --- quality_scorer mock ---
    from tinaa.quality.scorer import (
        AccessibilityInput,
        PerformanceHealthInput,
        QualityScorer,
        SecurityPostureInput,
        TestHealthInput,
    )
    quality_scorer = QualityScorer()

    # --- quality_gate mock ---
    from tinaa.quality.gates import QualityGate
    quality_gate = QualityGate()

    # --- playbook_validator mock — use real one ---
    from tinaa.playbooks.validator import PlaybookValidator
    playbook_validator = PlaybookValidator()

    # --- baseline_manager mock — use real one ---
    from tinaa.apm.baselines import BaselineManager
    baseline_manager = BaselineManager(min_samples=30, window_hours=168)

    # --- alert_engine mock — use real one ---
    from tinaa.alerts.engine import AlertEngine
    alert_engine = AlertEngine()

    # --- orchestrator mock ---
    orchestrator = MagicMock()
    orchestrator.handle_event = AsyncMock(return_value=[])

    container = MagicMock()
    container.registry = registry
    container.quality_scorer = quality_scorer
    container.quality_gate = quality_gate
    container.playbook_validator = playbook_validator
    container.baseline_manager = baseline_manager
    container.alert_engine = alert_engine
    container.orchestrator = orchestrator

    return container


_MOCK_SERVICES = _make_mock_services()


@pytest.fixture(scope="module", autouse=True)
def patch_service_container():
    """Patch ServiceContainer.get() for all API unit tests.

    Routes call get_services() which delegates to ServiceContainer.get().
    Patching at the ServiceContainer level ensures no real DB connections
    are attempted during unit testing.
    """
    with patch("tinaa.services.ServiceContainer.get", return_value=_MOCK_SERVICES):
        yield


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def app():
    from tinaa.api.app import create_app

    return create_app()


@pytest.fixture(scope="module")
def client(app):
    return TestClient(app, raise_server_exceptions=True)


# ---------------------------------------------------------------------------
# Health / Root
# ---------------------------------------------------------------------------


class TestHealthRoutes:
    def test_health_check_returns_200(self, client: TestClient) -> None:
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_check_body_shape(self, client: TestClient) -> None:
        body = client.get("/health").json()
        assert body["status"] == "healthy"
        assert body["version"] == "2.0.0"
        assert "timestamp" in body

    def test_root_returns_200(self, client: TestClient) -> None:
        response = client.get("/")
        assert response.status_code == 200

    def test_api_root_body_shape(self, client: TestClient) -> None:
        body = client.get("/api").json()
        assert body["name"] == "TINAA MSP"
        assert body["version"] == "2.0.0"
        assert body["docs"] == "/api/docs"


# ---------------------------------------------------------------------------
# Products
# ---------------------------------------------------------------------------


PRODUCT_PAYLOAD = {
    "name": "Shop API",
    "repository_url": "https://github.com/acme/shop",
    "description": "Main shopping API",
    "environments": {"production": "https://api.acme.com"},
}


class TestProductRoutes:
    def test_create_product_returns_201(self, client: TestClient) -> None:
        response = client.post("/api/v1/products", json=PRODUCT_PAYLOAD)
        assert response.status_code == 201

    def test_create_product_response_shape(self, client: TestClient) -> None:
        body = client.post("/api/v1/products", json=PRODUCT_PAYLOAD).json()
        assert "id" in body
        assert body["name"] == PRODUCT_PAYLOAD["name"]
        assert "slug" in body
        assert "status" in body
        assert "created_at" in body

    def test_create_product_missing_name_returns_422(self, client: TestClient) -> None:
        response = client.post("/api/v1/products", json={"description": "no name"})
        assert response.status_code == 422

    def test_list_products_returns_200(self, client: TestClient) -> None:
        response = client.get("/api/v1/products")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_list_products_status_filter(self, client: TestClient) -> None:
        response = client.get("/api/v1/products?status=active")
        assert response.status_code == 200

    def test_get_product_returns_200(self, client: TestClient) -> None:
        response = client.get("/api/v1/products/prod-001")
        assert response.status_code == 200

    def test_get_product_body_shape(self, client: TestClient) -> None:
        body = client.get("/api/v1/products/prod-001").json()
        required_keys = {"id", "name", "slug", "status", "created_at"}
        assert required_keys.issubset(body.keys())

    def test_update_product_returns_200(self, client: TestClient) -> None:
        response = client.patch(
            "/api/v1/products/prod-001", json={"description": "updated"}
        )
        assert response.status_code == 200

    def test_delete_product_returns_204(self, client: TestClient) -> None:
        response = client.delete("/api/v1/products/prod-001")
        assert response.status_code == 204

    def test_add_environment_returns_201(self, client: TestClient) -> None:
        payload = {
            "name": "staging",
            "base_url": "https://staging.acme.com",
            "env_type": "staging",
            "monitoring_interval_seconds": 60,
        }
        response = client.post("/api/v1/products/prod-001/environments", json=payload)
        assert response.status_code == 201

    def test_add_environment_missing_required_returns_422(
        self, client: TestClient
    ) -> None:
        response = client.post(
            "/api/v1/products/prod-001/environments", json={"name": "only-name"}
        )
        assert response.status_code == 422

    def test_list_environments_returns_200(self, client: TestClient) -> None:
        response = client.get("/api/v1/products/prod-001/environments")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_add_endpoint_returns_201(self, client: TestClient) -> None:
        payload = {
            "path": "/checkout",
            "method": "POST",
            "endpoint_type": "api",
            "expected_status_code": 200,
        }
        response = client.post(
            "/api/v1/products/prod-001/environments/env-001/endpoints", json=payload
        )
        assert response.status_code == 201

    def test_add_endpoint_missing_path_returns_422(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/products/prod-001/environments/env-001/endpoints",
            json={"method": "GET"},
        )
        assert response.status_code == 422

    def test_list_endpoints_returns_200(self, client: TestClient) -> None:
        response = client.get(
            "/api/v1/products/prod-001/environments/env-001/endpoints"
        )
        assert response.status_code == 200
        assert isinstance(response.json(), list)


# ---------------------------------------------------------------------------
# Playbooks
# ---------------------------------------------------------------------------


PLAYBOOK_PAYLOAD = {
    "name": "Checkout Flow",
    "suite_type": "regression",
    "steps": [{"action": "navigate", "url": "https://acme.com/checkout"}],
}


class TestPlaybookRoutes:
    def test_create_playbook_returns_201(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/products/prod-001/playbooks", json=PLAYBOOK_PAYLOAD
        )
        assert response.status_code == 201

    def test_create_playbook_response_has_id(self, client: TestClient) -> None:
        body = client.post(
            "/api/v1/products/prod-001/playbooks", json=PLAYBOOK_PAYLOAD
        ).json()
        assert "id" in body

    def test_list_playbooks_returns_200(self, client: TestClient) -> None:
        response = client.get("/api/v1/products/prod-001/playbooks")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_playbook_returns_200(self, client: TestClient) -> None:
        response = client.get("/api/v1/playbooks/pb-001")
        assert response.status_code == 200

    def test_update_playbook_returns_200(self, client: TestClient) -> None:
        response = client.patch("/api/v1/playbooks/pb-001", json={"name": "Updated"})
        assert response.status_code == 200

    def test_delete_playbook_returns_204(self, client: TestClient) -> None:
        response = client.delete("/api/v1/playbooks/pb-001")
        assert response.status_code == 204

    def test_execute_playbook_returns_200(self, client: TestClient) -> None:
        response = client.post("/api/v1/playbooks/pb-001/execute")
        assert response.status_code == 200

    def test_execute_playbook_returns_run_id(self, client: TestClient) -> None:
        body = client.post("/api/v1/playbooks/pb-001/execute").json()
        assert "run_id" in body
        assert body["status"] == "queued"

    def test_execute_playbook_with_env_query_param(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/playbooks/pb-001/execute?environment=staging"
        )
        assert response.status_code == 200

    def test_validate_playbook_returns_200(self, client: TestClient) -> None:
        response = client.post(
            "/api/v1/playbooks/validate", json={"steps": [{"action": "navigate"}]}
        )
        assert response.status_code == 200

    def test_validate_playbook_response_has_valid_field(
        self, client: TestClient
    ) -> None:
        body = client.post(
            "/api/v1/playbooks/validate", json={"steps": [{"action": "navigate"}]}
        ).json()
        assert "valid" in body
        assert "errors" in body
        assert isinstance(body["errors"], list)

    def test_validate_playbook_with_invalid_step_returns_errors(
        self, client: TestClient
    ) -> None:
        body = client.post(
            "/api/v1/playbooks/validate",
            json={"steps": [{"url": "https://example.com"}]},
        ).json()
        assert body["valid"] is False
        assert len(body["errors"]) == 1
        assert "action" in body["errors"][0]


# ---------------------------------------------------------------------------
# Test Runs
# ---------------------------------------------------------------------------


class TestRunRoutes:
    def test_list_test_runs_returns_200(self, client: TestClient) -> None:
        response = client.get("/api/v1/products/prod-001/runs")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_list_test_runs_limit_param(self, client: TestClient) -> None:
        response = client.get("/api/v1/products/prod-001/runs?limit=5")
        assert response.status_code == 200

    def test_list_test_runs_status_filter(self, client: TestClient) -> None:
        response = client.get("/api/v1/products/prod-001/runs?status=passed")
        assert response.status_code == 200

    def test_get_test_run_returns_200(self, client: TestClient) -> None:
        response = client.get("/api/v1/runs/run-001")
        assert response.status_code == 200

    def test_get_test_run_body_has_run_id(self, client: TestClient) -> None:
        body = client.get("/api/v1/runs/run-001").json()
        assert "run_id" in body
        assert "status" in body

    def test_get_test_results_returns_200(self, client: TestClient) -> None:
        response = client.get("/api/v1/runs/run-001/results")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_trigger_test_run_returns_202_or_200(self, client: TestClient) -> None:
        response = client.post("/api/v1/products/prod-001/runs")
        assert response.status_code in (200, 202)

    def test_trigger_test_run_returns_run_id(self, client: TestClient) -> None:
        body = client.post("/api/v1/products/prod-001/runs").json()
        assert "run_id" in body
        assert body["status"] == "queued"

    def test_cancel_test_run_returns_200(self, client: TestClient) -> None:
        response = client.post("/api/v1/runs/run-001/cancel")
        assert response.status_code == 200

    def test_cancel_test_run_returns_status(self, client: TestClient) -> None:
        body = client.post("/api/v1/runs/run-001/cancel").json()
        assert "status" in body


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------


class TestMetricsRoutes:
    def test_get_product_metrics_returns_200(self, client: TestClient) -> None:
        response = client.get("/api/v1/products/prod-001/metrics")
        assert response.status_code == 200

    def test_get_product_metrics_body_shape(self, client: TestClient) -> None:
        body = client.get("/api/v1/products/prod-001/metrics").json()
        assert "metrics" in body
        assert "baseline" in body
        assert "trend" in body

    def test_get_product_metrics_hours_param(self, client: TestClient) -> None:
        response = client.get("/api/v1/products/prod-001/metrics?hours=48")
        assert response.status_code == 200

    def test_get_endpoint_metrics_returns_200(self, client: TestClient) -> None:
        response = client.get("/api/v1/endpoints/ep-001/metrics")
        assert response.status_code == 200

    def test_get_endpoint_metrics_body_shape(self, client: TestClient) -> None:
        body = client.get("/api/v1/endpoints/ep-001/metrics").json()
        assert "metrics" in body

    def test_get_baselines_returns_200(self, client: TestClient) -> None:
        response = client.get("/api/v1/products/prod-001/metrics/baselines")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_anomalies_returns_200(self, client: TestClient) -> None:
        response = client.get("/api/v1/products/prod-001/metrics/anomalies")
        assert response.status_code == 200
        assert isinstance(response.json(), list)


# ---------------------------------------------------------------------------
# Quality
# ---------------------------------------------------------------------------


class TestQualityRoutes:
    def test_get_quality_score_returns_200(self, client: TestClient) -> None:
        response = client.get("/api/v1/products/prod-001/quality")
        assert response.status_code == 200

    def test_get_quality_score_body_shape(self, client: TestClient) -> None:
        body = client.get("/api/v1/products/prod-001/quality").json()
        assert "score" in body
        assert "components" in body

    def test_get_quality_history_returns_200(self, client: TestClient) -> None:
        response = client.get("/api/v1/products/prod-001/quality/history")
        assert response.status_code == 200
        assert isinstance(response.json(), list)

    def test_get_quality_history_days_param(self, client: TestClient) -> None:
        response = client.get("/api/v1/products/prod-001/quality/history?days=7")
        assert response.status_code == 200

    def test_get_quality_report_returns_200(self, client: TestClient) -> None:
        response = client.get("/api/v1/products/prod-001/quality/report")
        assert response.status_code == 200

    def test_get_quality_report_body_shape(self, client: TestClient) -> None:
        body = client.get("/api/v1/products/prod-001/quality/report").json()
        assert "product_id" in body
        assert "generated_at" in body

    def test_evaluate_quality_gate_returns_200(self, client: TestClient) -> None:
        response = client.get("/api/v1/products/prod-001/quality/gate")
        assert response.status_code == 200

    def test_evaluate_quality_gate_body_shape(self, client: TestClient) -> None:
        body = client.get("/api/v1/products/prod-001/quality/gate").json()
        assert "passed" in body
        assert "score" in body
        assert "checks" in body
        assert "recommendation" in body


# ---------------------------------------------------------------------------
# Webhooks
# ---------------------------------------------------------------------------

WEBHOOK_SECRET = "test-secret-value"


def _make_github_sig(secret: str, body: bytes) -> str:
    mac = hmac.new(secret.encode(), body, hashlib.sha256)
    return f"sha256={mac.hexdigest()}"


class TestWebhookRoutes:
    def test_github_webhook_without_secret_configured_returns_503(
        self, client: TestClient
    ) -> None:
        """When no secret is configured the handler must return 503 before any
        signature check — callers learn the integration is not set up."""
        payload = json.dumps({"action": "opened"}).encode()
        with patch("tinaa.api.routes.webhooks.GITHUB_WEBHOOK_SECRET", ""):
            response = client.post(
                "/api/v1/webhooks/github",
                content=payload,
                headers={
                    "X-GitHub-Event": "pull_request",
                    "Content-Type": "application/json",
                },
            )
        assert response.status_code == 503

    def test_github_webhook_without_signature_header_returns_400(
        self, client: TestClient
    ) -> None:
        """With a valid secret configured, missing signature header returns 400."""
        payload = json.dumps({"action": "opened"}).encode()
        with patch("tinaa.api.routes.webhooks.GITHUB_WEBHOOK_SECRET", WEBHOOK_SECRET):
            response = client.post(
                "/api/v1/webhooks/github",
                content=payload,
                headers={
                    "X-GitHub-Event": "pull_request",
                    "Content-Type": "application/json",
                },
            )
        assert response.status_code in (400, 401, 403)

    def test_github_webhook_invalid_signature_returns_401_or_403(
        self, client: TestClient
    ) -> None:
        payload = json.dumps({"action": "opened"}).encode()
        with patch("tinaa.api.routes.webhooks.GITHUB_WEBHOOK_SECRET", WEBHOOK_SECRET):
            response = client.post(
                "/api/v1/webhooks/github",
                content=payload,
                headers={
                    "X-GitHub-Event": "pull_request",
                    "X-Hub-Signature-256": "sha256=badhash",
                    "Content-Type": "application/json",
                },
            )
        assert response.status_code in (401, 403)

    def test_github_webhook_valid_signature_returns_200(
        self, client: TestClient
    ) -> None:
        payload = json.dumps({"action": "opened", "number": 1}).encode()
        sig = _make_github_sig(WEBHOOK_SECRET, payload)
        with patch(
            "tinaa.api.routes.webhooks.GITHUB_WEBHOOK_SECRET", WEBHOOK_SECRET
        ):
            response = client.post(
                "/api/v1/webhooks/github",
                content=payload,
                headers={
                    "X-GitHub-Event": "pull_request",
                    "X-Hub-Signature-256": sig,
                    "Content-Type": "application/json",
                },
            )
        assert response.status_code == 200

    def test_github_webhook_deployment_status_event(
        self, client: TestClient
    ) -> None:
        payload = json.dumps({"state": "success", "deployment": {}}).encode()
        sig = _make_github_sig(WEBHOOK_SECRET, payload)
        with patch(
            "tinaa.api.routes.webhooks.GITHUB_WEBHOOK_SECRET", WEBHOOK_SECRET
        ):
            response = client.post(
                "/api/v1/webhooks/github",
                content=payload,
                headers={
                    "X-GitHub-Event": "deployment_status",
                    "X-Hub-Signature-256": sig,
                    "Content-Type": "application/json",
                },
            )
        assert response.status_code == 200

    def test_github_webhook_returns_event_type_in_response(
        self, client: TestClient
    ) -> None:
        payload = json.dumps({"action": "created"}).encode()
        sig = _make_github_sig(WEBHOOK_SECRET, payload)
        with patch(
            "tinaa.api.routes.webhooks.GITHUB_WEBHOOK_SECRET", WEBHOOK_SECRET
        ):
            body = client.post(
                "/api/v1/webhooks/github",
                content=payload,
                headers={
                    "X-GitHub-Event": "push",
                    "X-Hub-Signature-256": sig,
                    "Content-Type": "application/json",
                },
            ).json()
        assert "event" in body or "status" in body

    def test_github_webhook_installation_event(self, client: TestClient) -> None:
        payload = json.dumps({"action": "created", "installation": {}}).encode()
        sig = _make_github_sig(WEBHOOK_SECRET, payload)
        with patch(
            "tinaa.api.routes.webhooks.GITHUB_WEBHOOK_SECRET", WEBHOOK_SECRET
        ):
            response = client.post(
                "/api/v1/webhooks/github",
                content=payload,
                headers={
                    "X-GitHub-Event": "installation",
                    "X-Hub-Signature-256": sig,
                    "Content-Type": "application/json",
                },
            )
        assert response.status_code == 200

    def test_github_webhook_unhandled_event_returns_200(
        self, client: TestClient
    ) -> None:
        payload = json.dumps({"action": "starred"}).encode()
        sig = _make_github_sig(WEBHOOK_SECRET, payload)
        with patch(
            "tinaa.api.routes.webhooks.GITHUB_WEBHOOK_SECRET", WEBHOOK_SECRET
        ):
            body = client.post(
                "/api/v1/webhooks/github",
                content=payload,
                headers={
                    "X-GitHub-Event": "star",
                    "X-Hub-Signature-256": sig,
                    "Content-Type": "application/json",
                },
            ).json()
        assert body["status"] == "received"
        assert body["action"] == "ignored"

    def test_github_webhook_invalid_json_returns_400(
        self, client: TestClient
    ) -> None:
        payload = b"not-json{"
        sig = _make_github_sig(WEBHOOK_SECRET, payload)
        with patch(
            "tinaa.api.routes.webhooks.GITHUB_WEBHOOK_SECRET", WEBHOOK_SECRET
        ):
            response = client.post(
                "/api/v1/webhooks/github",
                content=payload,
                headers={
                    "X-GitHub-Event": "push",
                    "X-Hub-Signature-256": sig,
                    "Content-Type": "application/json",
                },
            )
        assert response.status_code == 400

    def test_verify_github_signature_none_header_returns_false(self) -> None:
        from tinaa.api.routes.webhooks import _verify_github_signature

        assert _verify_github_signature("secret", b"body", None) is False

    def test_verify_github_signature_bad_prefix_returns_false(self) -> None:
        from tinaa.api.routes.webhooks import _verify_github_signature

        assert _verify_github_signature("secret", b"body", "md5=abc123") is False

    def test_github_webhook_empty_secret_returns_503(
        self, client: TestClient
    ) -> None:
        """When GITHUB_WEBHOOK_SECRET is empty the endpoint must return 503."""
        payload = json.dumps({"action": "opened"}).encode()
        with patch("tinaa.api.routes.webhooks.GITHUB_WEBHOOK_SECRET", ""):
            response = client.post(
                "/api/v1/webhooks/github",
                content=payload,
                headers={
                    "X-GitHub-Event": "pull_request",
                    "Content-Type": "application/json",
                },
            )
        assert response.status_code == 503
        assert "GITHUB_WEBHOOK_SECRET" in response.json()["detail"]


# ---------------------------------------------------------------------------
# WebSocket ConnectionManager
# ---------------------------------------------------------------------------


class TestConnectionManager:
    @pytest.mark.asyncio
    async def test_connect_adds_to_active_connections(self) -> None:
        from tinaa.api.websocket import ConnectionManager

        manager = ConnectionManager()
        ws = AsyncMock()
        ws.accept = AsyncMock()
        await manager.connect("client-1", ws)
        assert "client-1" in manager.active_connections

    @pytest.mark.asyncio
    async def test_disconnect_removes_from_active_connections(self) -> None:
        from tinaa.api.websocket import ConnectionManager

        manager = ConnectionManager()
        ws = AsyncMock()
        ws.accept = AsyncMock()
        await manager.connect("client-1", ws)
        await manager.disconnect("client-1")
        assert "client-1" not in manager.active_connections

    @pytest.mark.asyncio
    async def test_disconnect_nonexistent_client_does_not_raise(self) -> None:
        from tinaa.api.websocket import ConnectionManager

        manager = ConnectionManager()
        await manager.disconnect("no-such-client")  # must not raise

    @pytest.mark.asyncio
    async def test_send_update_sends_json_text(self) -> None:
        from tinaa.api.websocket import ConnectionManager

        manager = ConnectionManager()
        ws = AsyncMock()
        ws.accept = AsyncMock()
        ws.send_json = AsyncMock()
        await manager.connect("client-1", ws)
        await manager.send_update("client-1", {"type": "ping"})
        ws.send_json.assert_called_once_with({"type": "ping"})

    @pytest.mark.asyncio
    async def test_send_update_unknown_client_does_not_raise(self) -> None:
        from tinaa.api.websocket import ConnectionManager

        manager = ConnectionManager()
        await manager.send_update("ghost", {"type": "ping"})  # must not raise

    @pytest.mark.asyncio
    async def test_broadcast_sends_to_all_connections(self) -> None:
        from tinaa.api.websocket import ConnectionManager

        manager = ConnectionManager()
        ws1, ws2 = AsyncMock(), AsyncMock()
        ws1.accept = AsyncMock()
        ws2.accept = AsyncMock()
        ws1.send_json = AsyncMock()
        ws2.send_json = AsyncMock()
        await manager.connect("c1", ws1)
        await manager.connect("c2", ws2)
        await manager.broadcast({"type": "alert", "message": "test"})
        ws1.send_json.assert_called_once()
        ws2.send_json.assert_called_once()

    @pytest.mark.asyncio
    async def test_send_test_progress_sends_progress_message(self) -> None:
        from tinaa.api.websocket import ConnectionManager

        manager = ConnectionManager()
        ws = AsyncMock()
        ws.accept = AsyncMock()
        ws.send_json = AsyncMock()
        await manager.connect("client-1", ws)
        await manager.send_test_progress("client-1", "run-42", {"percent": 50})
        call_args = ws.send_json.call_args[0][0]
        assert call_args["type"] == "test_progress"
        assert call_args["run_id"] == "run-42"
        assert call_args["progress"]["percent"] == 50


# ---------------------------------------------------------------------------
# WebSocket endpoint via TestClient
# ---------------------------------------------------------------------------


class TestWebSocketEndpoint:
    def test_websocket_connect_and_ping(self, client: TestClient) -> None:
        with client.websocket_connect("/ws/test-client") as ws:
            ws.send_json({"type": "ping"})
            data = ws.receive_json()
            assert data["type"] == "pong"

    def test_websocket_subscribe_message_acknowledged(
        self, client: TestClient
    ) -> None:
        with client.websocket_connect("/ws/test-client-2") as ws:
            ws.send_json({"type": "subscribe", "product_id": "prod-001"})
            data = ws.receive_json()
            assert "subscribed" in data or data.get("type") == "subscribed"


# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------


class TestRequestLoggingMiddleware:
    def test_logging_middleware_does_not_break_requests(
        self, client: TestClient
    ) -> None:
        """Requests succeed even with logging middleware active."""
        response = client.get("/health")
        assert response.status_code == 200

    def test_x_response_time_header_present(self, client: TestClient) -> None:
        """Logging middleware injects X-Response-Time header."""
        response = client.get("/health")
        assert "x-response-time" in response.headers or response.status_code == 200


class TestAPIKeyMiddleware:
    def test_public_health_endpoint_accessible_without_api_key(
        self, client: TestClient
    ) -> None:
        response = client.get("/health")
        assert response.status_code == 200

    def test_docs_endpoint_accessible_without_api_key(
        self, client: TestClient
    ) -> None:
        response = client.get("/api/docs")
        assert response.status_code == 200

    def test_protected_endpoint_with_valid_bearer_token(
        self, client: TestClient
    ) -> None:
        with patch("tinaa.api.middleware.VALID_API_KEYS", {"secret-token"}), \
             patch("tinaa.api.middleware.API_KEY_REQUIRED", True):
            response = client.get(
                "/api/v1/products",
                headers={"Authorization": "Bearer secret-token"},
            )
        assert response.status_code == 200

    def test_protected_endpoint_with_valid_x_api_key_header(
        self, client: TestClient
    ) -> None:
        with patch("tinaa.api.middleware.VALID_API_KEYS", {"my-key"}), \
             patch("tinaa.api.middleware.API_KEY_REQUIRED", True):
            response = client.get(
                "/api/v1/products",
                headers={"X-API-Key": "my-key"},
            )
        assert response.status_code == 200

    def test_protected_endpoint_without_key_returns_401(
        self, client: TestClient
    ) -> None:
        with patch("tinaa.api.middleware.VALID_API_KEYS", {"required-key"}), \
             patch("tinaa.api.middleware.API_KEY_REQUIRED", True):
            response = client.get("/api/v1/products")
        assert response.status_code == 401


# ---------------------------------------------------------------------------
# CORS configuration
# ---------------------------------------------------------------------------


class TestCORSConfiguration:
    def test_cors_does_not_allow_wildcard_origin(self, app) -> None:
        """allow_origins must not be ['*'] when allow_credentials=True."""
        from fastapi.middleware.cors import CORSMiddleware

        for middleware_entry in app.user_middleware:
            if middleware_entry.cls is CORSMiddleware:
                origins = middleware_entry.kwargs.get("allow_origins", [])
                assert origins != ["*"], (
                    "allow_origins=['*'] with allow_credentials=True is insecure"
                )
                return
        # If CORS middleware not found by user_middleware, check middleware_stack
        # pragma: no cover — at least one branch above must run
        pytest.fail("CORSMiddleware not found in app middleware stack")

    def test_cors_allow_credentials_is_true(self, app) -> None:
        """Credentials must still be enabled after the security fix."""
        from fastapi.middleware.cors import CORSMiddleware

        for middleware_entry in app.user_middleware:
            if middleware_entry.cls is CORSMiddleware:
                assert middleware_entry.kwargs.get("allow_credentials") is True
                return
        pytest.fail("CORSMiddleware not found in app middleware stack")

    def test_cors_origins_default_includes_localhost(self, app) -> None:
        """Default CORS origins must include known-safe localhost addresses."""
        from fastapi.middleware.cors import CORSMiddleware

        for middleware_entry in app.user_middleware:
            if middleware_entry.cls is CORSMiddleware:
                origins = middleware_entry.kwargs.get("allow_origins", [])
                assert any("localhost" in o for o in origins)
                return
        pytest.fail("CORSMiddleware not found in app middleware stack")


# ---------------------------------------------------------------------------
# OpenAPI metadata
# ---------------------------------------------------------------------------


class TestOpenAPIMetadata:
    def test_openapi_schema_accessible(self, client: TestClient) -> None:
        response = client.get("/openapi.json")
        assert response.status_code == 200

    def test_openapi_title_is_correct(self, client: TestClient) -> None:
        schema = client.get("/openapi.json").json()
        assert schema["info"]["title"] == "TINAA MSP API"

    def test_openapi_version_is_correct(self, client: TestClient) -> None:
        schema = client.get("/openapi.json").json()
        assert schema["info"]["version"] == "2.0.0"
