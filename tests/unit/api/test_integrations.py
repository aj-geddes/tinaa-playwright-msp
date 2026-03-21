"""
Unit tests for integrations API routes.

Tests cover:
- POST /integrations/github/pat/verify — token verification + user info
- POST /integrations/github/pat/save — save PAT credentials
- GET /integrations/github/repos — list repos from saved credentials
- POST /integrations/github/repos/import — import repo as TINAA product
- GET /integrations/github/status — check current integration status
- POST /integrations/github/app/setup — configure GitHub App credentials
- GET /integrations/github/setup-guide — step-by-step setup instructions
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


# ---------------------------------------------------------------------------
# App fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def client():
    """Create a test client with mocked services."""
    from tinaa.api.app import create_app

    app = create_app()

    # Override service dependency
    from tinaa.services import get_services
    mock_services = MagicMock()
    mock_services.registry = MagicMock()
    app.dependency_overrides[get_services] = lambda: mock_services

    return TestClient(app)


# ---------------------------------------------------------------------------
# GET /api/v1/integrations/github/setup-guide
# ---------------------------------------------------------------------------


class TestSetupGuide:
    def test_returns_200(self, client):
        resp = client.get("/api/v1/integrations/github/setup-guide")
        assert resp.status_code == 200

    def test_response_has_pat_section(self, client):
        resp = client.get("/api/v1/integrations/github/setup-guide")
        data = resp.json()
        assert "pat" in data

    def test_response_has_app_section(self, client):
        resp = client.get("/api/v1/integrations/github/setup-guide")
        data = resp.json()
        assert "app" in data

    def test_pat_has_steps(self, client):
        resp = client.get("/api/v1/integrations/github/setup-guide")
        data = resp.json()
        assert len(data["pat"]["steps"]) >= 4

    def test_app_has_steps(self, client):
        resp = client.get("/api/v1/integrations/github/setup-guide")
        data = resp.json()
        assert len(data["app"]["steps"]) >= 6

    def test_pat_steps_have_required_fields(self, client):
        resp = client.get("/api/v1/integrations/github/setup-guide")
        data = resp.json()
        for step in data["pat"]["steps"]:
            assert "step" in step
            assert "title" in step
            assert "description" in step

    def test_pat_has_required_permissions(self, client):
        resp = client.get("/api/v1/integrations/github/setup-guide")
        data = resp.json()
        assert "required_permissions" in data["pat"]
        assert len(data["pat"]["required_permissions"]) > 0

    def test_app_has_required_permissions(self, client):
        resp = client.get("/api/v1/integrations/github/setup-guide")
        data = resp.json()
        assert "required_permissions" in data["app"]
        assert len(data["app"]["required_permissions"]) > 0

    def test_pat_title_is_string(self, client):
        resp = client.get("/api/v1/integrations/github/setup-guide")
        data = resp.json()
        assert isinstance(data["pat"]["title"], str)
        assert len(data["pat"]["title"]) > 0

    def test_app_title_is_string(self, client):
        resp = client.get("/api/v1/integrations/github/setup-guide")
        data = resp.json()
        assert isinstance(data["app"]["title"], str)


# ---------------------------------------------------------------------------
# GET /api/v1/integrations/github/status
# ---------------------------------------------------------------------------


class TestGitHubStatus:
    def test_returns_200(self, client):
        resp = client.get("/api/v1/integrations/github/status")
        assert resp.status_code == 200

    def test_response_has_configured_field(self, client):
        resp = client.get("/api/v1/integrations/github/status")
        data = resp.json()
        assert "configured" in data

    def test_configured_is_bool(self, client):
        resp = client.get("/api/v1/integrations/github/status")
        data = resp.json()
        assert isinstance(data["configured"], bool)

    def test_response_has_type_field(self, client):
        resp = client.get("/api/v1/integrations/github/status")
        data = resp.json()
        assert "type" in data

    def test_type_is_none_when_not_configured(self, client):
        resp = client.get("/api/v1/integrations/github/status")
        data = resp.json()
        if not data["configured"]:
            assert data["type"] is None


# ---------------------------------------------------------------------------
# POST /api/v1/integrations/github/pat/verify
# ---------------------------------------------------------------------------


class TestVerifyGitHubPAT:
    def test_returns_200_with_valid_token(self, client):
        mock_user = {"login": "octocat", "name": "The Octocat", "avatar_url": "https://...", "scopes": ["repo"]}
        mock_repos = [{"full_name": "octocat/Hello-World"}]

        with patch("tinaa.api.routes.integrations.GitHubPATClient") as mock_cls:
            mock_gh = AsyncMock()
            mock_gh.verify_token = AsyncMock(return_value=mock_user)
            mock_gh.list_repos = AsyncMock(return_value=mock_repos)
            mock_cls.return_value = mock_gh

            resp = client.post(
                "/api/v1/integrations/github/pat/verify",
                json={"token": "ghp_test123"}
            )

        assert resp.status_code == 200

    def test_returns_valid_true_on_success(self, client):
        mock_user = {"login": "octocat", "name": "Octocat", "avatar_url": "", "scopes": []}
        mock_repos = []

        with patch("tinaa.api.routes.integrations.GitHubPATClient") as mock_cls:
            mock_gh = AsyncMock()
            mock_gh.verify_token = AsyncMock(return_value=mock_user)
            mock_gh.list_repos = AsyncMock(return_value=mock_repos)
            mock_cls.return_value = mock_gh

            resp = client.post(
                "/api/v1/integrations/github/pat/verify",
                json={"token": "ghp_test123"}
            )

        assert resp.json()["valid"] is True

    def test_response_has_user_info(self, client):
        mock_user = {"login": "octocat", "name": "Octocat", "avatar_url": "https://example.com/avatar.png", "scopes": ["repo"]}
        mock_repos = []

        with patch("tinaa.api.routes.integrations.GitHubPATClient") as mock_cls:
            mock_gh = AsyncMock()
            mock_gh.verify_token = AsyncMock(return_value=mock_user)
            mock_gh.list_repos = AsyncMock(return_value=mock_repos)
            mock_cls.return_value = mock_gh

            resp = client.post(
                "/api/v1/integrations/github/pat/verify",
                json={"token": "ghp_test123"}
            )

        data = resp.json()
        assert "user" in data
        assert data["user"]["login"] == "octocat"

    def test_response_has_repos(self, client):
        mock_user = {"login": "octocat", "name": "Octocat", "avatar_url": "", "scopes": []}
        mock_repos = [{"full_name": "octocat/Hello-World"}]

        with patch("tinaa.api.routes.integrations.GitHubPATClient") as mock_cls:
            mock_gh = AsyncMock()
            mock_gh.verify_token = AsyncMock(return_value=mock_user)
            mock_gh.list_repos = AsyncMock(return_value=mock_repos)
            mock_cls.return_value = mock_gh

            resp = client.post(
                "/api/v1/integrations/github/pat/verify",
                json={"token": "ghp_test123"}
            )

        data = resp.json()
        assert "repos" in data
        assert len(data["repos"]) == 1

    def test_returns_422_without_token(self, client):
        resp = client.post("/api/v1/integrations/github/pat/verify", json={})
        assert resp.status_code == 422

    def test_returns_400_on_github_error(self, client):
        import httpx

        with patch("tinaa.api.routes.integrations.GitHubPATClient") as mock_cls:
            mock_gh = AsyncMock()
            mock_resp = MagicMock()
            mock_resp.status_code = 401
            mock_gh.verify_token = AsyncMock(
                side_effect=httpx.HTTPStatusError("Unauthorized", request=MagicMock(), response=mock_resp)
            )
            mock_cls.return_value = mock_gh

            resp = client.post(
                "/api/v1/integrations/github/pat/verify",
                json={"token": "ghp_bad_token"}
            )

        assert resp.status_code in (400, 401, 422)


# ---------------------------------------------------------------------------
# POST /api/v1/integrations/github/pat/save
# ---------------------------------------------------------------------------


class TestSaveGitHubPAT:
    def test_returns_200_on_success(self, client):
        mock_user = {"login": "octocat", "name": "Octocat", "avatar_url": "", "scopes": []}

        with patch("tinaa.api.routes.integrations.GitHubPATClient") as mock_cls:
            mock_gh = AsyncMock()
            mock_gh.verify_token = AsyncMock(return_value=mock_user)
            mock_cls.return_value = mock_gh

            resp = client.post(
                "/api/v1/integrations/github/pat/save",
                json={"token": "ghp_test123"}
            )

        assert resp.status_code == 200

    def test_response_has_saved_true(self, client):
        mock_user = {"login": "octocat", "name": "Octocat", "avatar_url": "", "scopes": []}

        with patch("tinaa.api.routes.integrations.GitHubPATClient") as mock_cls:
            mock_gh = AsyncMock()
            mock_gh.verify_token = AsyncMock(return_value=mock_user)
            mock_cls.return_value = mock_gh

            resp = client.post(
                "/api/v1/integrations/github/pat/save",
                json={"token": "ghp_test123"}
            )

        assert resp.json()["saved"] is True

    def test_response_has_user_info(self, client):
        mock_user = {"login": "octocat", "name": "Octocat", "avatar_url": "https://...", "scopes": []}

        with patch("tinaa.api.routes.integrations.GitHubPATClient") as mock_cls:
            mock_gh = AsyncMock()
            mock_gh.verify_token = AsyncMock(return_value=mock_user)
            mock_cls.return_value = mock_gh

            resp = client.post(
                "/api/v1/integrations/github/pat/save",
                json={"token": "ghp_test123"}
            )

        assert resp.json()["user"]["login"] == "octocat"

    def test_returns_422_without_token(self, client):
        resp = client.post("/api/v1/integrations/github/pat/save", json={})
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# GET /api/v1/integrations/github/repos
# ---------------------------------------------------------------------------


class TestListGitHubRepos:
    def test_returns_200_when_configured(self, client):
        mock_repos = [
            {"full_name": "octocat/Hello-World", "html_url": "https://...", "language": "Python", "default_branch": "main"}
        ]

        with patch("tinaa.api.routes.integrations._get_saved_pat", return_value="ghp_test"):
            with patch("tinaa.api.routes.integrations.GitHubPATClient") as mock_cls:
                mock_gh = AsyncMock()
                mock_gh.list_repos = AsyncMock(return_value=mock_repos)
                mock_cls.return_value = mock_gh

                resp = client.get("/api/v1/integrations/github/repos")

        assert resp.status_code == 200

    def test_returns_list_of_repos(self, client):
        mock_repos = [
            {"full_name": "octocat/Hello-World", "html_url": "https://github.com/octocat/Hello-World",
             "language": "Python", "default_branch": "main", "private": False, "description": ""}
        ]

        with patch("tinaa.api.routes.integrations._get_saved_pat", return_value="ghp_test"):
            with patch("tinaa.api.routes.integrations.GitHubPATClient") as mock_cls:
                mock_gh = AsyncMock()
                mock_gh.list_repos = AsyncMock(return_value=mock_repos)
                mock_cls.return_value = mock_gh

                resp = client.get("/api/v1/integrations/github/repos")

        assert isinstance(resp.json(), list)

    def test_returns_404_when_not_configured(self, client):
        with patch("tinaa.api.routes.integrations._get_saved_pat", return_value=None):
            resp = client.get("/api/v1/integrations/github/repos")
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /api/v1/integrations/github/repos/import
# ---------------------------------------------------------------------------


class TestImportGitHubRepo:
    def test_returns_201_on_success(self, client):
        mock_repo = {
            "full_name": "octocat/Hello-World",
            "html_url": "https://github.com/octocat/Hello-World",
            "description": "My first repo",
            "language": "Python",
            "default_branch": "main",
            "private": False,
        }

        with patch("tinaa.api.routes.integrations._get_saved_pat", return_value="ghp_test"):
            with patch("tinaa.api.routes.integrations.GitHubPATClient") as mock_cls:
                mock_gh = AsyncMock()
                mock_gh.get_repo = AsyncMock(return_value=mock_repo)
                mock_gh.get_file_content = AsyncMock(return_value=None)
                mock_gh.list_environments = AsyncMock(return_value=[])
                mock_cls.return_value = mock_gh

                # Mock registry product creation
                from tinaa.services import get_services
                mock_services = MagicMock()
                mock_product = MagicMock()
                mock_product.id = "test-id-123"
                mock_product.name = "Hello-World"
                mock_product.slug = "hello-world"
                mock_services.registry.create_product = AsyncMock(return_value=mock_product)
                client.app.dependency_overrides[get_services] = lambda: mock_services

                resp = client.post(
                    "/api/v1/integrations/github/repos/import",
                    json={"repo_full_name": "octocat/Hello-World"}
                )

        assert resp.status_code in (200, 201)

    def test_returns_422_without_repo_name(self, client):
        resp = client.post("/api/v1/integrations/github/repos/import", json={})
        assert resp.status_code == 422

    def test_returns_404_when_not_configured(self, client):
        with patch("tinaa.api.routes.integrations._get_saved_pat", return_value=None):
            resp = client.post(
                "/api/v1/integrations/github/repos/import",
                json={"repo_full_name": "octocat/Hello-World"}
            )
        assert resp.status_code == 404


# ---------------------------------------------------------------------------
# POST /api/v1/integrations/github/app/setup
# ---------------------------------------------------------------------------


class TestSetupGitHubApp:
    def test_returns_200_on_success(self, client):
        resp = client.post(
            "/api/v1/integrations/github/app/setup",
            json={
                "app_id": "12345",
                "private_key": "-----BEGIN RSA PRIVATE KEY-----\nfake\n-----END RSA PRIVATE KEY-----",
                "webhook_secret": "mysecret"
            }
        )
        assert resp.status_code == 200

    def test_response_has_configured_true(self, client):
        resp = client.post(
            "/api/v1/integrations/github/app/setup",
            json={
                "app_id": "12345",
                "private_key": "-----BEGIN RSA PRIVATE KEY-----\nfake\n-----END RSA PRIVATE KEY-----",
                "webhook_secret": "mysecret"
            }
        )
        assert resp.json()["configured"] is True

    def test_response_has_app_id(self, client):
        resp = client.post(
            "/api/v1/integrations/github/app/setup",
            json={
                "app_id": "12345",
                "private_key": "-----BEGIN RSA PRIVATE KEY-----\nfake\n-----END RSA PRIVATE KEY-----",
                "webhook_secret": "mysecret"
            }
        )
        assert resp.json()["app_id"] == "12345"

    def test_returns_422_without_required_fields(self, client):
        resp = client.post("/api/v1/integrations/github/app/setup", json={"app_id": "123"})
        assert resp.status_code == 422
