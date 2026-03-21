"""
Unit tests for TINAA GitHub App Integration.

Tests cover:
- GitHubClient: JWT generation, installation token exchange, API requests
- WebhookHandler: signature verification, event routing, payload extraction
- ChecksManager: check run creation, update, and test result reporting
- DeploymentTracker: deployment URL discovery, protection rule responses
- TINAAGitHubApp: high-level orchestration
"""

import hashlib
import hmac
import json
import time
from unittest.mock import AsyncMock, MagicMock, patch

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from tinaa.github.client import GitHubClient
from tinaa.github.webhooks import (
    WebhookHandler,
    extract_deployment_info,
    extract_pull_request_info,
    extract_push_info,
)
from tinaa.github.checks import ChecksManager
from tinaa.github.deployments import DeploymentTracker
from tinaa.github.app import TINAAGitHubApp


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

FAKE_APP_ID = "12345"
FAKE_WEBHOOK_SECRET = "test_secret_abc123"


def _generate_test_rsa_key() -> str:
    """Generate a real RSA private key for use in tests."""
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")


# Generated once at module load so all tests share the same valid key
FAKE_PRIVATE_KEY = _generate_test_rsa_key()


@pytest.fixture
def github_client() -> GitHubClient:
    return GitHubClient(app_id=FAKE_APP_ID, private_key=FAKE_PRIVATE_KEY)


@pytest.fixture
def webhook_handler() -> WebhookHandler:
    return WebhookHandler(webhook_secret=FAKE_WEBHOOK_SECRET)


@pytest.fixture
def checks_manager(github_client: GitHubClient) -> ChecksManager:
    return ChecksManager(client=github_client)


@pytest.fixture
def deployment_tracker(github_client: GitHubClient) -> DeploymentTracker:
    return DeploymentTracker(client=github_client)


@pytest.fixture
def tinaa_app() -> TINAAGitHubApp:
    return TINAAGitHubApp(
        app_id=FAKE_APP_ID,
        private_key=FAKE_PRIVATE_KEY,
        webhook_secret=FAKE_WEBHOOK_SECRET,
    )


# ---------------------------------------------------------------------------
# GitHubClient Tests
# ---------------------------------------------------------------------------


class TestGitHubClientInit:
    def test_stores_app_id(self, github_client: GitHubClient) -> None:
        assert github_client.app_id == FAKE_APP_ID

    def test_stores_private_key(self, github_client: GitHubClient) -> None:
        assert github_client.private_key == FAKE_PRIVATE_KEY


class TestGitHubClientJWT:
    def test_generate_jwt_returns_string(self, github_client: GitHubClient) -> None:
        token = github_client._generate_jwt()
        assert isinstance(token, str)
        assert len(token) > 0

    def test_jwt_contains_correct_issuer(self, github_client: GitHubClient) -> None:
        token = github_client._generate_jwt()
        # Decode without verification to inspect claims
        payload = jwt.decode(token, options={"verify_signature": False})
        assert payload["iss"] == FAKE_APP_ID

    def test_jwt_has_valid_expiry(self, github_client: GitHubClient) -> None:
        before = int(time.time())
        token = github_client._generate_jwt()
        after = int(time.time())
        payload = jwt.decode(token, options={"verify_signature": False})
        # exp should be ~10 minutes (600s) from now
        assert payload["exp"] >= before + 599
        assert payload["exp"] <= after + 601

    def test_jwt_issued_at_is_backdated(self, github_client: GitHubClient) -> None:
        """iat must be 60 seconds in the past to account for clock skew."""
        before = int(time.time())
        token = github_client._generate_jwt()
        after = int(time.time())
        payload = jwt.decode(token, options={"verify_signature": False})
        # iat should be now - 60
        assert payload["iat"] <= before - 59
        assert payload["iat"] >= after - 61

    def test_jwt_algorithm_is_rs256(self, github_client: GitHubClient) -> None:
        token = github_client._generate_jwt()
        header = jwt.get_unverified_header(token)
        assert header["alg"] == "RS256"


class TestGitHubClientInstallationToken:
    @pytest.mark.asyncio
    async def test_get_installation_token_calls_correct_endpoint(
        self, github_client: GitHubClient
    ) -> None:
        installation_id = 99887766
        fake_token = "ghs_fakeInstallationToken"

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_response = MagicMock()
            mock_response.json.return_value = {"token": fake_token}
            mock_response.raise_for_status = MagicMock()
            mock_instance = AsyncMock()
            mock_instance.post = AsyncMock(return_value=mock_response)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            mock_client_class.return_value = mock_instance

            token = await github_client.get_installation_token(installation_id)

        assert token == fake_token
        call_args = mock_instance.post.call_args
        assert f"/app/installations/{installation_id}/access_tokens" in call_args[0][0]

    @pytest.mark.asyncio
    async def test_get_installation_token_sends_jwt_auth_header(
        self, github_client: GitHubClient
    ) -> None:
        installation_id = 11223344

        with patch("httpx.AsyncClient") as mock_client_class:
            mock_response = MagicMock()
            mock_response.json.return_value = {"token": "ghs_any"}
            mock_response.raise_for_status = MagicMock()
            mock_instance = AsyncMock()
            mock_instance.post = AsyncMock(return_value=mock_response)
            mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
            mock_instance.__aexit__ = AsyncMock(return_value=False)
            mock_client_class.return_value = mock_instance

            await github_client.get_installation_token(installation_id)

        call_kwargs = mock_instance.post.call_args[1]
        headers = call_kwargs.get("headers", {})
        assert "Authorization" in headers
        assert headers["Authorization"].startswith("Bearer ")


class TestGitHubClientRequest:
    @pytest.mark.asyncio
    async def test_request_uses_installation_token(
        self, github_client: GitHubClient
    ) -> None:
        installation_id = 55443322
        fake_token = "ghs_requestToken"

        with patch.object(
            github_client,
            "get_installation_token",
            new=AsyncMock(return_value=fake_token),
        ):
            with patch("httpx.AsyncClient") as mock_client_class:
                mock_response = MagicMock()
                mock_response.json.return_value = {"id": 1}
                mock_response.raise_for_status = MagicMock()
                mock_instance = AsyncMock()
                mock_instance.request = AsyncMock(return_value=mock_response)
                mock_instance.__aenter__ = AsyncMock(return_value=mock_instance)
                mock_instance.__aexit__ = AsyncMock(return_value=False)
                mock_client_class.return_value = mock_instance

                result = await github_client._request(
                    "GET",
                    "https://api.github.com/repos/owner/repo",
                    installation_id,
                )

        assert result == {"id": 1}
        call_kwargs = mock_instance.request.call_args[1]
        headers = call_kwargs.get("headers", {})
        assert headers.get("Authorization") == f"token {fake_token}"


class TestGitHubClientConvenienceMethods:
    @pytest.mark.asyncio
    async def test_get_repository_calls_correct_url(
        self, github_client: GitHubClient
    ) -> None:
        installation_id = 111
        owner = "acme"
        repo = "myapp"
        fake_repo = {"id": 42, "full_name": f"{owner}/{repo}"}

        with patch.object(
            github_client,
            "_request",
            new=AsyncMock(return_value=fake_repo),
        ) as mock_request:
            result = await github_client.get_repository(installation_id, owner, repo)

        assert result == fake_repo
        call_args = mock_request.call_args
        assert f"/repos/{owner}/{repo}" in call_args[0][1]

    @pytest.mark.asyncio
    async def test_get_file_content_decodes_base64(
        self, github_client: GitHubClient
    ) -> None:
        import base64

        content = "hello world"
        encoded = base64.b64encode(content.encode()).decode()
        fake_response = {"content": encoded + "\n", "encoding": "base64"}

        with patch.object(
            github_client,
            "_request",
            new=AsyncMock(return_value=fake_response),
        ):
            result = await github_client.get_file_content(
                installation_id=111,
                owner="acme",
                repo="myapp",
                path="src/index.ts",
            )

        assert result == content

    @pytest.mark.asyncio
    async def test_list_directory_returns_list(
        self, github_client: GitHubClient
    ) -> None:
        fake_entries = [
            {"name": "src", "type": "dir"},
            {"name": "README.md", "type": "file"},
        ]

        with patch.object(
            github_client,
            "_request",
            new=AsyncMock(return_value=fake_entries),
        ):
            result = await github_client.list_directory(
                installation_id=111,
                owner="acme",
                repo="myapp",
            )

        assert result == fake_entries
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_get_file_content_with_ref(
        self, github_client: GitHubClient
    ) -> None:
        import base64

        content = "const x = 1;"
        encoded = base64.b64encode(content.encode()).decode()
        fake_response = {"content": encoded, "encoding": "base64"}

        with patch.object(
            github_client,
            "_request",
            new=AsyncMock(return_value=fake_response),
        ) as mock_request:
            await github_client.get_file_content(
                installation_id=111,
                owner="acme",
                repo="myapp",
                path="src/app.ts",
                ref="main",
            )

        call_args = mock_request.call_args
        assert "ref=main" in call_args[0][1]

    @pytest.mark.asyncio
    async def test_list_directory_with_ref(
        self, github_client: GitHubClient
    ) -> None:
        fake_entries = [{"name": "index.ts", "type": "file"}]

        with patch.object(
            github_client,
            "_request",
            new=AsyncMock(return_value=fake_entries),
        ) as mock_request:
            result = await github_client.list_directory(
                installation_id=111,
                owner="acme",
                repo="myapp",
                path="src",
                ref="feature/branch",
            )

        assert result == fake_entries
        call_args = mock_request.call_args
        assert "ref=feature/branch" in call_args[0][1]


# ---------------------------------------------------------------------------
# WebhookHandler Tests
# ---------------------------------------------------------------------------


def _make_signature(secret: str, payload: bytes) -> str:
    """Helper: create a valid HMAC-SHA256 signature."""
    digest = hmac.new(
        secret.encode(), payload, hashlib.sha256
    ).hexdigest()
    return f"sha256={digest}"


class TestWebhookSignatureVerification:
    def test_valid_signature_returns_true(
        self, webhook_handler: WebhookHandler
    ) -> None:
        payload = b'{"action": "opened"}'
        signature = _make_signature(FAKE_WEBHOOK_SECRET, payload)
        assert webhook_handler.verify_signature(payload, signature) is True

    def test_invalid_signature_returns_false(
        self, webhook_handler: WebhookHandler
    ) -> None:
        payload = b'{"action": "opened"}'
        assert (
            webhook_handler.verify_signature(payload, "sha256=deadbeef") is False
        )

    def test_tampered_payload_returns_false(
        self, webhook_handler: WebhookHandler
    ) -> None:
        original = b'{"action": "opened"}'
        tampered = b'{"action": "closed"}'
        signature = _make_signature(FAKE_WEBHOOK_SECRET, original)
        assert webhook_handler.verify_signature(tampered, signature) is False

    def test_empty_payload_valid_signature(
        self, webhook_handler: WebhookHandler
    ) -> None:
        payload = b""
        signature = _make_signature(FAKE_WEBHOOK_SECRET, payload)
        assert webhook_handler.verify_signature(payload, signature) is True

    def test_missing_sha256_prefix_returns_false(
        self, webhook_handler: WebhookHandler
    ) -> None:
        payload = b'{"action": "opened"}'
        digest = hmac.new(
            FAKE_WEBHOOK_SECRET.encode(), payload, hashlib.sha256
        ).hexdigest()
        # signature without prefix
        assert webhook_handler.verify_signature(payload, digest) is False

    def test_uses_constant_time_comparison(
        self, webhook_handler: WebhookHandler
    ) -> None:
        """Ensure implementation uses hmac.compare_digest (not ==)."""
        import inspect
        source = inspect.getsource(webhook_handler.verify_signature)
        assert "compare_digest" in source


class TestWebhookHandlerRegistration:
    @pytest.mark.asyncio
    async def test_on_registers_handler(
        self, webhook_handler: WebhookHandler
    ) -> None:
        called_with: list = []

        async def my_handler(payload: dict) -> str:
            called_with.append(payload)
            return "handled"

        webhook_handler.on("pull_request", my_handler)
        results = await webhook_handler.handle("pull_request", "opened", {"key": "val"})
        assert called_with == [{"key": "val"}]
        assert results == ["handled"]

    @pytest.mark.asyncio
    async def test_multiple_handlers_for_same_event(
        self, webhook_handler: WebhookHandler
    ) -> None:
        results: list = []

        async def handler_a(payload: dict) -> str:
            return "a"

        async def handler_b(payload: dict) -> str:
            return "b"

        webhook_handler.on("push", handler_a)
        webhook_handler.on("push", handler_b)
        out = await webhook_handler.handle("push", None, {})
        assert "a" in out
        assert "b" in out

    @pytest.mark.asyncio
    async def test_no_handlers_returns_empty_list(
        self, webhook_handler: WebhookHandler
    ) -> None:
        results = await webhook_handler.handle("unknown_event", None, {})
        assert results == []

    @pytest.mark.asyncio
    async def test_handler_receives_payload(
        self, webhook_handler: WebhookHandler
    ) -> None:
        received = []

        async def capture(payload: dict) -> None:
            received.append(payload)

        payload = {"repository": {"full_name": "acme/app"}}
        webhook_handler.on("push", capture)
        await webhook_handler.handle("push", "created", payload)
        assert received[0] == payload


# ---------------------------------------------------------------------------
# Webhook Payload Extraction Tests
# ---------------------------------------------------------------------------


DEPLOYMENT_STATUS_PAYLOAD = {
    "deployment_status": {
        "id": 4321,
        "state": "success",
        "target_url": "https://app.example.com",
        "environment": "production",
    },
    "deployment": {
        "id": 9876,
        "sha": "abc123def456",
        "ref": "main",
        "creator": {"login": "octocat"},
    },
    "repository": {"full_name": "acme/myapp"},
    "installation": {"id": 55667788},
}

PULL_REQUEST_PAYLOAD = {
    "action": "opened",
    "number": 42,
    "pull_request": {
        "title": "Add login page",
        "head": {
            "sha": "deadbeef1234",
            "ref": "feature/login",
        },
        "base": {"ref": "main"},
    },
    "repository": {
        "full_name": "acme/myapp",
        "pulls_url": "https://api.github.com/repos/acme/myapp/pulls{/number}",
    },
    "installation": {"id": 11223344},
}

PUSH_PAYLOAD = {
    "ref": "refs/heads/main",
    "after": "cafebabe5678",
    "commits": [
        {
            "id": "cafebabe5678",
            "message": "Fix login bug",
            "modified": ["src/login.ts"],
            "added": [],
            "removed": [],
        }
    ],
    "repository": {"full_name": "acme/myapp"},
    "installation": {"id": 99887766},
}


class TestExtractDeploymentInfo:
    def test_extracts_deployment_id(self) -> None:
        info = extract_deployment_info(DEPLOYMENT_STATUS_PAYLOAD)
        assert info["deployment_id"] == 9876

    def test_extracts_environment(self) -> None:
        info = extract_deployment_info(DEPLOYMENT_STATUS_PAYLOAD)
        assert info["environment"] == "production"

    def test_extracts_state(self) -> None:
        info = extract_deployment_info(DEPLOYMENT_STATUS_PAYLOAD)
        assert info["state"] == "success"

    def test_extracts_target_url(self) -> None:
        info = extract_deployment_info(DEPLOYMENT_STATUS_PAYLOAD)
        assert info["target_url"] == "https://app.example.com"

    def test_extracts_commit_sha(self) -> None:
        info = extract_deployment_info(DEPLOYMENT_STATUS_PAYLOAD)
        assert info["commit_sha"] == "abc123def456"

    def test_extracts_ref(self) -> None:
        info = extract_deployment_info(DEPLOYMENT_STATUS_PAYLOAD)
        assert info["ref"] == "main"

    def test_extracts_creator(self) -> None:
        info = extract_deployment_info(DEPLOYMENT_STATUS_PAYLOAD)
        assert info["creator"] == "octocat"

    def test_extracts_repository_full_name(self) -> None:
        info = extract_deployment_info(DEPLOYMENT_STATUS_PAYLOAD)
        assert info["repository_full_name"] == "acme/myapp"

    def test_extracts_installation_id(self) -> None:
        info = extract_deployment_info(DEPLOYMENT_STATUS_PAYLOAD)
        assert info["installation_id"] == 55667788

    def test_target_url_none_when_missing(self) -> None:
        payload = {
            **DEPLOYMENT_STATUS_PAYLOAD,
            "deployment_status": {
                **DEPLOYMENT_STATUS_PAYLOAD["deployment_status"],
                "target_url": None,
            },
        }
        info = extract_deployment_info(payload)
        assert info["target_url"] is None


class TestExtractPullRequestInfo:
    def test_extracts_pr_number(self) -> None:
        info = extract_pull_request_info(PULL_REQUEST_PAYLOAD)
        assert info["pr_number"] == 42

    def test_extracts_action(self) -> None:
        info = extract_pull_request_info(PULL_REQUEST_PAYLOAD)
        assert info["action"] == "opened"

    def test_extracts_title(self) -> None:
        info = extract_pull_request_info(PULL_REQUEST_PAYLOAD)
        assert info["title"] == "Add login page"

    def test_extracts_head_sha(self) -> None:
        info = extract_pull_request_info(PULL_REQUEST_PAYLOAD)
        assert info["head_sha"] == "deadbeef1234"

    def test_extracts_head_ref(self) -> None:
        info = extract_pull_request_info(PULL_REQUEST_PAYLOAD)
        assert info["head_ref"] == "feature/login"

    def test_extracts_base_ref(self) -> None:
        info = extract_pull_request_info(PULL_REQUEST_PAYLOAD)
        assert info["base_ref"] == "main"

    def test_extracts_repository_full_name(self) -> None:
        info = extract_pull_request_info(PULL_REQUEST_PAYLOAD)
        assert info["repository_full_name"] == "acme/myapp"

    def test_extracts_installation_id(self) -> None:
        info = extract_pull_request_info(PULL_REQUEST_PAYLOAD)
        assert info["installation_id"] == 11223344

    def test_changed_files_url_contains_pr_number(self) -> None:
        info = extract_pull_request_info(PULL_REQUEST_PAYLOAD)
        assert "42" in info["changed_files_url"]


class TestExtractPushInfo:
    def test_extracts_ref(self) -> None:
        info = extract_push_info(PUSH_PAYLOAD)
        assert info["ref"] == "refs/heads/main"

    def test_extracts_commit_sha(self) -> None:
        info = extract_push_info(PUSH_PAYLOAD)
        assert info["commit_sha"] == "cafebabe5678"

    def test_extracts_commits_list(self) -> None:
        info = extract_push_info(PUSH_PAYLOAD)
        assert len(info["commits"]) == 1
        assert info["commits"][0]["id"] == "cafebabe5678"

    def test_commit_has_required_keys(self) -> None:
        info = extract_push_info(PUSH_PAYLOAD)
        commit = info["commits"][0]
        for key in ("id", "message", "modified", "added", "removed"):
            assert key in commit

    def test_extracts_repository_full_name(self) -> None:
        info = extract_push_info(PUSH_PAYLOAD)
        assert info["repository_full_name"] == "acme/myapp"

    def test_extracts_installation_id(self) -> None:
        info = extract_push_info(PUSH_PAYLOAD)
        assert info["installation_id"] == 99887766


# ---------------------------------------------------------------------------
# ChecksManager Tests
# ---------------------------------------------------------------------------


class TestChecksManagerCreateCheckRun:
    @pytest.mark.asyncio
    async def test_create_check_run_returns_id(
        self, checks_manager: ChecksManager
    ) -> None:
        fake_response = {"id": 777, "status": "queued"}

        with patch.object(
            checks_manager._client,
            "_request",
            new=AsyncMock(return_value=fake_response),
        ):
            result = await checks_manager.create_check_run(
                installation_id=111,
                owner="acme",
                repo="myapp",
                name="TINAA Quality Check",
                head_sha="abc123",
            )

        assert result == {"check_run_id": 777}

    @pytest.mark.asyncio
    async def test_create_check_run_posts_to_correct_url(
        self, checks_manager: ChecksManager
    ) -> None:
        with patch.object(
            checks_manager._client,
            "_request",
            new=AsyncMock(return_value={"id": 1}),
        ) as mock_req:
            await checks_manager.create_check_run(
                installation_id=111,
                owner="acme",
                repo="myapp",
                name="Test",
                head_sha="sha123",
            )

        call_args = mock_req.call_args
        assert call_args[0][0] == "POST"
        assert "/repos/acme/myapp/check-runs" in call_args[0][1]

    @pytest.mark.asyncio
    async def test_create_check_run_default_status_is_queued(
        self, checks_manager: ChecksManager
    ) -> None:
        with patch.object(
            checks_manager._client,
            "_request",
            new=AsyncMock(return_value={"id": 1}),
        ) as mock_req:
            await checks_manager.create_check_run(
                installation_id=111,
                owner="acme",
                repo="myapp",
                name="Test",
                head_sha="sha123",
            )

        json_body = mock_req.call_args[1].get("json", {})
        assert json_body.get("status") == "queued"

    @pytest.mark.asyncio
    async def test_create_check_run_includes_details_url_when_provided(
        self, checks_manager: ChecksManager
    ) -> None:
        with patch.object(
            checks_manager._client,
            "_request",
            new=AsyncMock(return_value={"id": 1}),
        ) as mock_req:
            await checks_manager.create_check_run(
                installation_id=111,
                owner="acme",
                repo="myapp",
                name="Test",
                head_sha="sha123",
                details_url="https://tinaa.example.com/runs/42",
            )

        json_body = mock_req.call_args[1].get("json", {})
        assert json_body.get("details_url") == "https://tinaa.example.com/runs/42"


class TestChecksManagerUpdateCheckRun:
    @pytest.mark.asyncio
    async def test_update_check_run_patches_correct_url(
        self, checks_manager: ChecksManager
    ) -> None:
        check_run_id = 999

        with patch.object(
            checks_manager._client,
            "_request",
            new=AsyncMock(return_value={"id": check_run_id}),
        ) as mock_req:
            await checks_manager.update_check_run(
                installation_id=111,
                owner="acme",
                repo="myapp",
                check_run_id=check_run_id,
                status="completed",
                conclusion="success",
            )

        call_args = mock_req.call_args
        assert call_args[0][0] == "PATCH"
        assert f"/repos/acme/myapp/check-runs/{check_run_id}" in call_args[0][1]

    @pytest.mark.asyncio
    async def test_update_check_run_sends_annotations(
        self, checks_manager: ChecksManager
    ) -> None:
        annotations = [
            {
                "path": "src/login.tsx",
                "start_line": 47,
                "end_line": 47,
                "annotation_level": "warning",
                "message": "Button missing aria-label",
                "title": "Accessibility Issue",
            }
        ]

        with patch.object(
            checks_manager._client,
            "_request",
            new=AsyncMock(return_value={"id": 1}),
        ) as mock_req:
            await checks_manager.update_check_run(
                installation_id=111,
                owner="acme",
                repo="myapp",
                check_run_id=1,
                status="completed",
                conclusion="failure",
                annotations=annotations,
            )

        json_body = mock_req.call_args[1].get("json", {})
        assert "output" in json_body
        assert json_body["output"]["annotations"] == annotations

    @pytest.mark.asyncio
    async def test_update_check_run_omits_none_fields(
        self, checks_manager: ChecksManager
    ) -> None:
        with patch.object(
            checks_manager._client,
            "_request",
            new=AsyncMock(return_value={"id": 1}),
        ) as mock_req:
            await checks_manager.update_check_run(
                installation_id=111,
                owner="acme",
                repo="myapp",
                check_run_id=1,
                status="in_progress",
            )

        json_body = mock_req.call_args[1].get("json", {})
        assert "conclusion" not in json_body or json_body.get("conclusion") is None


class TestChecksManagerReportTestResults:
    @pytest.mark.asyncio
    async def test_report_test_results_returns_check_run_id(
        self, checks_manager: ChecksManager
    ) -> None:
        test_run_summary = {
            "name": "TINAA Quality Check",
            "passed": 10,
            "failed": 2,
            "skipped": 1,
            "duration_ms": 4500,
            "quality_score": 87.5,
            "quality_score_delta": 2.3,
            "performance_summary": "P95: 1200ms",
            "issues": [
                {
                    "file": "src/login.tsx",
                    "line": 47,
                    "message": "Missing aria-label",
                    "severity": "warning",
                }
            ],
        }

        with patch.object(
            checks_manager,
            "create_check_run",
            new=AsyncMock(return_value={"check_run_id": 42}),
        ):
            with patch.object(
                checks_manager,
                "update_check_run",
                new=AsyncMock(return_value={"id": 42}),
            ):
                check_run_id = await checks_manager.report_test_results(
                    installation_id=111,
                    owner="acme",
                    repo="myapp",
                    head_sha="abc123",
                    test_run_summary=test_run_summary,
                )

        assert check_run_id == 42

    @pytest.mark.asyncio
    async def test_report_test_results_conclusion_failure_when_tests_fail(
        self, checks_manager: ChecksManager
    ) -> None:
        test_run_summary = {
            "name": "TINAA Quality Check",
            "passed": 8,
            "failed": 2,
            "skipped": 0,
            "duration_ms": 3000,
            "quality_score": 75.0,
            "quality_score_delta": -5.0,
            "performance_summary": "P95: 800ms",
            "issues": [],
        }

        with patch.object(
            checks_manager,
            "create_check_run",
            new=AsyncMock(return_value={"check_run_id": 10}),
        ):
            with patch.object(
                checks_manager,
                "update_check_run",
                new=AsyncMock(return_value={"id": 10}),
            ) as mock_update:
                await checks_manager.report_test_results(
                    installation_id=111,
                    owner="acme",
                    repo="myapp",
                    head_sha="abc123",
                    test_run_summary=test_run_summary,
                )

        call_kwargs = mock_update.call_args[1]
        assert call_kwargs["conclusion"] == "failure"

    @pytest.mark.asyncio
    async def test_report_test_results_conclusion_success_when_all_pass(
        self, checks_manager: ChecksManager
    ) -> None:
        test_run_summary = {
            "name": "TINAA Quality Check",
            "passed": 10,
            "failed": 0,
            "skipped": 0,
            "duration_ms": 2000,
            "quality_score": 95.0,
            "quality_score_delta": 1.0,
            "performance_summary": "P95: 500ms",
            "issues": [],
        }

        with patch.object(
            checks_manager,
            "create_check_run",
            new=AsyncMock(return_value={"check_run_id": 20}),
        ):
            with patch.object(
                checks_manager,
                "update_check_run",
                new=AsyncMock(return_value={"id": 20}),
            ) as mock_update:
                await checks_manager.report_test_results(
                    installation_id=111,
                    owner="acme",
                    repo="myapp",
                    head_sha="abc123",
                    test_run_summary=test_run_summary,
                )

        call_kwargs = mock_update.call_args[1]
        assert call_kwargs["conclusion"] == "success"

    @pytest.mark.asyncio
    async def test_report_test_results_summary_contains_score(
        self, checks_manager: ChecksManager
    ) -> None:
        test_run_summary = {
            "name": "TINAA Quality Check",
            "passed": 5,
            "failed": 0,
            "skipped": 0,
            "duration_ms": 1500,
            "quality_score": 91.0,
            "quality_score_delta": 0.5,
            "performance_summary": "P95: 300ms",
            "issues": [],
        }

        with patch.object(
            checks_manager,
            "create_check_run",
            new=AsyncMock(return_value={"check_run_id": 30}),
        ):
            with patch.object(
                checks_manager,
                "update_check_run",
                new=AsyncMock(return_value={"id": 30}),
            ) as mock_update:
                await checks_manager.report_test_results(
                    installation_id=111,
                    owner="acme",
                    repo="myapp",
                    head_sha="abc123",
                    test_run_summary=test_run_summary,
                )

        call_kwargs = mock_update.call_args[1]
        summary = call_kwargs.get("summary", "")
        assert "91" in summary

    @pytest.mark.asyncio
    async def test_report_test_results_creates_annotations_from_issues(
        self, checks_manager: ChecksManager
    ) -> None:
        test_run_summary = {
            "name": "TINAA Quality Check",
            "passed": 5,
            "failed": 1,
            "skipped": 0,
            "duration_ms": 1500,
            "quality_score": 80.0,
            "quality_score_delta": -1.0,
            "performance_summary": "P95: 400ms",
            "issues": [
                {
                    "file": "src/button.tsx",
                    "line": 12,
                    "message": "No accessible name",
                    "severity": "failure",
                }
            ],
        }

        with patch.object(
            checks_manager,
            "create_check_run",
            new=AsyncMock(return_value={"check_run_id": 40}),
        ):
            with patch.object(
                checks_manager,
                "update_check_run",
                new=AsyncMock(return_value={"id": 40}),
            ) as mock_update:
                await checks_manager.report_test_results(
                    installation_id=111,
                    owner="acme",
                    repo="myapp",
                    head_sha="abc123",
                    test_run_summary=test_run_summary,
                )

        call_kwargs = mock_update.call_args[1]
        annotations = call_kwargs.get("annotations", [])
        assert len(annotations) == 1
        assert annotations[0]["path"] == "src/button.tsx"
        assert annotations[0]["start_line"] == 12


# ---------------------------------------------------------------------------
# DeploymentTracker Tests
# ---------------------------------------------------------------------------


class TestDeploymentTrackerGetLatestUrl:
    @pytest.mark.asyncio
    async def test_returns_environment_url_on_success(
        self, deployment_tracker: DeploymentTracker
    ) -> None:
        deployment = {"id": 55, "statuses_url": "https://api.github.com/repos/acme/app/deployments/55/statuses"}
        status = {"state": "success", "environment_url": "https://prod.example.com"}

        async def fake_request(method: str, url: str, installation_id: int, **kwargs):
            if "deployments" in url and "statuses" not in url:
                return [deployment]
            if "statuses" in url:
                return [status]
            return {}

        with patch.object(
            deployment_tracker._client, "_request", side_effect=fake_request
        ):
            url = await deployment_tracker.get_latest_deployment_url(
                installation_id=111,
                owner="acme",
                repo="app",
                environment="production",
            )

        assert url == "https://prod.example.com"

    @pytest.mark.asyncio
    async def test_returns_none_when_no_deployments(
        self, deployment_tracker: DeploymentTracker
    ) -> None:
        with patch.object(
            deployment_tracker._client,
            "_request",
            new=AsyncMock(return_value=[]),
        ):
            url = await deployment_tracker.get_latest_deployment_url(
                installation_id=111,
                owner="acme",
                repo="app",
                environment="staging",
            )

        assert url is None

    @pytest.mark.asyncio
    async def test_returns_none_when_no_successful_status(
        self, deployment_tracker: DeploymentTracker
    ) -> None:
        deployment = {"id": 66, "statuses_url": "https://api.github.com/repos/acme/app/deployments/66/statuses"}
        status = {"state": "failure", "environment_url": None}

        async def fake_request(method: str, url: str, installation_id: int, **kwargs):
            if "statuses" in url:
                return [status]
            return [deployment]

        with patch.object(
            deployment_tracker._client, "_request", side_effect=fake_request
        ):
            url = await deployment_tracker.get_latest_deployment_url(
                installation_id=111,
                owner="acme",
                repo="app",
                environment="production",
            )

        assert url is None


class TestDeploymentTrackerListEnvironments:
    @pytest.mark.asyncio
    async def test_returns_list_of_environments(
        self, deployment_tracker: DeploymentTracker
    ) -> None:
        fake_envs = [
            {"name": "production", "html_url": "https://prod.example.com", "protection_rules": []},
            {"name": "staging", "html_url": None, "protection_rules": []},
        ]

        with patch.object(
            deployment_tracker._client,
            "_request",
            new=AsyncMock(return_value={"environments": fake_envs}),
        ):
            result = await deployment_tracker.list_environments(
                installation_id=111, owner="acme", repo="app"
            )

        assert len(result) == 2
        assert result[0]["name"] == "production"

    @pytest.mark.asyncio
    async def test_list_environments_calls_correct_url(
        self, deployment_tracker: DeploymentTracker
    ) -> None:
        with patch.object(
            deployment_tracker._client,
            "_request",
            new=AsyncMock(return_value={"environments": []}),
        ) as mock_req:
            await deployment_tracker.list_environments(
                installation_id=111, owner="acme", repo="app"
            )

        call_args = mock_req.call_args
        assert "/repos/acme/app/environments" in call_args[0][1]


class TestDeploymentTrackerHandleDeploymentStatus:
    @pytest.mark.asyncio
    async def test_returns_dict_on_success_with_url(
        self, deployment_tracker: DeploymentTracker
    ) -> None:
        result = await deployment_tracker.handle_deployment_status(
            DEPLOYMENT_STATUS_PAYLOAD
        )
        assert result is not None
        assert result["environment"] == "production"
        assert result["url"] == "https://app.example.com"
        assert result["commit_sha"] == "abc123def456"
        assert result["deployment_id"] == 9876

    @pytest.mark.asyncio
    async def test_returns_none_for_pending_state(
        self, deployment_tracker: DeploymentTracker
    ) -> None:
        payload = {
            **DEPLOYMENT_STATUS_PAYLOAD,
            "deployment_status": {
                **DEPLOYMENT_STATUS_PAYLOAD["deployment_status"],
                "state": "pending",
            },
        }
        result = await deployment_tracker.handle_deployment_status(payload)
        assert result is None

    @pytest.mark.asyncio
    async def test_returns_none_when_no_target_url(
        self, deployment_tracker: DeploymentTracker
    ) -> None:
        payload = {
            **DEPLOYMENT_STATUS_PAYLOAD,
            "deployment_status": {
                **DEPLOYMENT_STATUS_PAYLOAD["deployment_status"],
                "target_url": None,
            },
        }
        result = await deployment_tracker.handle_deployment_status(payload)
        assert result is None

    @pytest.mark.asyncio
    async def test_is_production_true_for_production_env(
        self, deployment_tracker: DeploymentTracker
    ) -> None:
        result = await deployment_tracker.handle_deployment_status(
            DEPLOYMENT_STATUS_PAYLOAD
        )
        assert result["is_production"] is True

    @pytest.mark.asyncio
    async def test_is_production_false_for_staging_env(
        self, deployment_tracker: DeploymentTracker
    ) -> None:
        payload = {
            **DEPLOYMENT_STATUS_PAYLOAD,
            "deployment_status": {
                **DEPLOYMENT_STATUS_PAYLOAD["deployment_status"],
                "environment": "staging",
            },
        }
        result = await deployment_tracker.handle_deployment_status(payload)
        assert result["is_production"] is False


class TestDeploymentTrackerRespondToProtectionRule:
    @pytest.mark.asyncio
    async def test_approve_posts_approved_state(
        self, deployment_tracker: DeploymentTracker
    ) -> None:
        with patch.object(
            deployment_tracker._client,
            "_request",
            new=AsyncMock(return_value={}),
        ) as mock_req:
            await deployment_tracker.respond_to_protection_rule(
                installation_id=111,
                owner="acme",
                repo="app",
                run_id=999,
                approved=True,
                comment="All checks passed",
            )

        call_args = mock_req.call_args
        assert call_args[0][0] == "POST"
        assert "/actions/runs/999/deployment_protection_rule" in call_args[0][1]
        assert call_args[1]["json"]["state"] == "approved"

    @pytest.mark.asyncio
    async def test_reject_posts_rejected_state(
        self, deployment_tracker: DeploymentTracker
    ) -> None:
        with patch.object(
            deployment_tracker._client,
            "_request",
            new=AsyncMock(return_value={}),
        ) as mock_req:
            await deployment_tracker.respond_to_protection_rule(
                installation_id=111,
                owner="acme",
                repo="app",
                run_id=999,
                approved=False,
                comment="Quality score too low",
            )

        json_body = mock_req.call_args[1]["json"]
        assert json_body["state"] == "rejected"
        assert json_body["comment"] == "Quality score too low"


# ---------------------------------------------------------------------------
# TINAAGitHubApp Tests
# ---------------------------------------------------------------------------


class TestTINAAGitHubAppInit:
    def test_has_client_attribute(self, tinaa_app: TINAAGitHubApp) -> None:
        assert isinstance(tinaa_app.client, GitHubClient)

    def test_has_webhooks_attribute(self, tinaa_app: TINAAGitHubApp) -> None:
        assert isinstance(tinaa_app.webhooks, WebhookHandler)

    def test_has_checks_attribute(self, tinaa_app: TINAAGitHubApp) -> None:
        assert isinstance(tinaa_app.checks, ChecksManager)

    def test_has_deployments_attribute(self, tinaa_app: TINAAGitHubApp) -> None:
        assert isinstance(tinaa_app.deployments, DeploymentTracker)


class TestTINAAGitHubAppHandleWebhook:
    @pytest.mark.asyncio
    async def test_returns_error_on_invalid_signature(
        self, tinaa_app: TINAAGitHubApp
    ) -> None:
        payload = json.dumps({"action": "opened"}).encode()
        result = await tinaa_app.handle_webhook(
            event="pull_request",
            payload=payload,
            signature="sha256=badsignature",
        )
        assert result["status"] == "error"
        assert "signature" in result["message"].lower()

    @pytest.mark.asyncio
    async def test_returns_ok_on_valid_signature(
        self, tinaa_app: TINAAGitHubApp
    ) -> None:
        payload = json.dumps({"action": "opened", "number": 1,
                              "pull_request": {"title": "t", "head": {"sha": "s", "ref": "r"}, "base": {"ref": "main"}},
                              "repository": {"full_name": "a/b", "pulls_url": "https://api.github.com/repos/a/b/pulls{/number}"},
                              "installation": {"id": 1}}).encode()
        signature = _make_signature(FAKE_WEBHOOK_SECRET, payload)
        result = await tinaa_app.handle_webhook(
            event="pull_request",
            payload=payload,
            signature=signature,
        )
        assert result["status"] == "ok"

    @pytest.mark.asyncio
    async def test_handle_webhook_routes_to_handlers(
        self, tinaa_app: TINAAGitHubApp
    ) -> None:
        received = []

        async def spy_handler(p: dict) -> None:
            received.append(p)

        tinaa_app.webhooks.on("push", spy_handler)
        payload_dict = {
            "ref": "refs/heads/main",
            "after": "abc",
            "commits": [],
            "repository": {"full_name": "a/b"},
            "installation": {"id": 1},
        }
        payload = json.dumps(payload_dict).encode()
        signature = _make_signature(FAKE_WEBHOOK_SECRET, payload)

        await tinaa_app.handle_webhook(
            event="push",
            payload=payload,
            signature=signature,
        )

        assert len(received) >= 1


class TestTINAAGitHubAppOnboardRepository:
    @pytest.mark.asyncio
    async def test_onboard_returns_dict_with_environments(
        self, tinaa_app: TINAAGitHubApp
    ) -> None:
        fake_envs = [{"name": "production", "url": "https://prod.example.com", "protection_rules": []}]

        with patch.object(
            tinaa_app.deployments,
            "list_environments",
            new=AsyncMock(return_value=fake_envs),
        ):
            with patch.object(
                tinaa_app.deployments,
                "get_latest_deployment_url",
                new=AsyncMock(return_value="https://prod.example.com"),
            ):
                with patch.object(
                    tinaa_app.client,
                    "get_file_content",
                    new=AsyncMock(side_effect=Exception("Not found")),
                ):
                    result = await tinaa_app.onboard_repository(
                        installation_id=111, owner="acme", repo="myapp"
                    )

        assert "environments" in result
        assert result["environments"] == fake_envs

    @pytest.mark.asyncio
    async def test_onboard_returns_tinaa_config_when_present(
        self, tinaa_app: TINAAGitHubApp
    ) -> None:
        tinaa_config = "base_url: https://app.example.com\nenvironments:\n  - production\n"

        with patch.object(
            tinaa_app.deployments,
            "list_environments",
            new=AsyncMock(return_value=[]),
        ):
            with patch.object(
                tinaa_app.deployments,
                "get_latest_deployment_url",
                new=AsyncMock(return_value=None),
            ):
                with patch.object(
                    tinaa_app.client,
                    "get_file_content",
                    new=AsyncMock(return_value=tinaa_config),
                ):
                    result = await tinaa_app.onboard_repository(
                        installation_id=111, owner="acme", repo="myapp"
                    )

        assert "tinaa_config" in result
        assert result["tinaa_config"] == tinaa_config

    @pytest.mark.asyncio
    async def test_onboard_tinaa_config_none_when_absent(
        self, tinaa_app: TINAAGitHubApp
    ) -> None:
        with patch.object(
            tinaa_app.deployments,
            "list_environments",
            new=AsyncMock(return_value=[]),
        ):
            with patch.object(
                tinaa_app.deployments,
                "get_latest_deployment_url",
                new=AsyncMock(return_value=None),
            ):
                with patch.object(
                    tinaa_app.client,
                    "get_file_content",
                    new=AsyncMock(side_effect=Exception("404")),
                ):
                    result = await tinaa_app.onboard_repository(
                        installation_id=111, owner="acme", repo="myapp"
                    )

        assert result["tinaa_config"] is None


# ---------------------------------------------------------------------------
# Additional branch-coverage tests (REFACTOR phase)
# ---------------------------------------------------------------------------


class TestWebhookHandlerExceptionSuppression:
    @pytest.mark.asyncio
    async def test_exception_in_handler_is_suppressed(
        self, webhook_handler: WebhookHandler
    ) -> None:
        """Handlers that raise must not propagate; other handlers still run."""
        results: list = []

        async def bad_handler(payload: dict) -> None:
            raise RuntimeError("simulated failure")

        async def good_handler(payload: dict) -> str:
            results.append("ok")
            return "ok"

        webhook_handler.on("push", bad_handler)
        webhook_handler.on("push", good_handler)
        out = await webhook_handler.handle("push", None, {})
        assert "ok" in out
        assert results == ["ok"]


class TestTINAAGitHubAppInvalidPayloadJson:
    @pytest.mark.asyncio
    async def test_returns_error_for_non_json_payload(
        self, tinaa_app: TINAAGitHubApp
    ) -> None:
        payload = b"this is not json"
        signature = _make_signature(FAKE_WEBHOOK_SECRET, payload)
        result = await tinaa_app.handle_webhook(
            event="push",
            payload=payload,
            signature=signature,
        )
        assert result["status"] == "error"
        assert "parse" in result["message"].lower()


class TestTINAAGitHubAppDefaultHandlers:
    @pytest.mark.asyncio
    async def test_deployment_status_handler_fires_on_event(
        self, tinaa_app: TINAAGitHubApp
    ) -> None:
        payload_dict = DEPLOYMENT_STATUS_PAYLOAD.copy()
        payload = json.dumps(payload_dict).encode()
        signature = _make_signature(FAKE_WEBHOOK_SECRET, payload)

        result = await tinaa_app.handle_webhook(
            event="deployment_status",
            payload=payload,
            signature=signature,
        )
        assert result["status"] == "ok"

    @pytest.mark.asyncio
    async def test_installation_handler_fires_on_event(
        self, tinaa_app: TINAAGitHubApp
    ) -> None:
        payload_dict = {
            "action": "created",
            "installation": {"id": 123456},
        }
        payload = json.dumps(payload_dict).encode()
        signature = _make_signature(FAKE_WEBHOOK_SECRET, payload)

        result = await tinaa_app.handle_webhook(
            event="installation",
            payload=payload,
            signature=signature,
        )
        assert result["status"] == "ok"


class TestChecksManagerUpdateWithTextAndTitle:
    @pytest.mark.asyncio
    async def test_update_check_run_includes_title_and_text(
        self, checks_manager: ChecksManager
    ) -> None:
        with patch.object(
            checks_manager._client,
            "_request",
            new=AsyncMock(return_value={"id": 1}),
        ) as mock_req:
            await checks_manager.update_check_run(
                installation_id=111,
                owner="acme",
                repo="myapp",
                check_run_id=1,
                status="completed",
                conclusion="success",
                title="All good",
                summary="## Summary\nEverything passed.",
                text="Detailed output here.",
            )

        json_body = mock_req.call_args[1].get("json", {})
        assert json_body["output"]["title"] == "All good"
        assert "Summary" in json_body["output"]["summary"]
        assert json_body["output"]["text"] == "Detailed output here."
