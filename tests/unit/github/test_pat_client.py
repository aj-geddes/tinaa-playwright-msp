"""
Unit tests for GitHubPATClient.

Tests cover:
- Token initialization and header construction
- verify_token: returns normalized user info dict with scopes
- list_repos: returns list of normalized repo dicts
- get_repo: returns repo detail dict
- list_environments: returns list of environment dicts
- get_latest_deployment: returns URL string or None
- get_file_content: decodes base64 file content, returns None on 404
- list_directory: returns list of directory entry dicts
- HTTP error propagation
"""

import base64
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from tinaa.github.pat_client import GitHubPATClient


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

TOKEN = "ghp_test_token_abc123"


def _make_client() -> GitHubPATClient:
    return GitHubPATClient(token=TOKEN)


def _mock_response(json_data, status_code: int = 200, headers: dict | None = None):
    """Build a mock httpx Response."""
    resp = MagicMock()
    resp.status_code = status_code
    resp.json.return_value = json_data
    resp.headers = headers or {}
    resp.raise_for_status = MagicMock()
    if status_code >= 400:
        import httpx

        resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            f"HTTP {status_code}",
            request=MagicMock(),
            response=resp,
        )
    return resp


# ---------------------------------------------------------------------------
# Initialization
# ---------------------------------------------------------------------------


class TestGitHubPATClientInit:
    def test_stores_token(self):
        client = GitHubPATClient(token=TOKEN)
        assert client._token == TOKEN

    def test_sets_bearer_authorization_header(self):
        client = GitHubPATClient(token=TOKEN)
        assert client._headers["Authorization"] == f"Bearer {TOKEN}"

    def test_sets_github_api_version_header(self):
        client = GitHubPATClient(token=TOKEN)
        assert client._headers["X-GitHub-Api-Version"] == "2022-11-28"

    def test_sets_accept_header(self):
        client = GitHubPATClient(token=TOKEN)
        assert "application/vnd.github+json" in client._headers["Accept"]

    def test_github_api_constant(self):
        assert GitHubPATClient.GITHUB_API == "https://api.github.com"


# ---------------------------------------------------------------------------
# verify_token
# ---------------------------------------------------------------------------


class TestVerifyToken:
    @pytest.mark.asyncio
    async def test_returns_user_info(self):
        client = _make_client()
        user_json = {
            "login": "octocat",
            "name": "The Octocat",
            "avatar_url": "https://github.com/images/octocat.png",
        }
        scopes_header = "repo, read:org"
        mock_resp = _mock_response(user_json, headers={"x-oauth-scopes": scopes_header})

        with patch("httpx.AsyncClient") as mock_ac:
            mock_ac.return_value.__aenter__ = AsyncMock(return_value=MagicMock(get=AsyncMock(return_value=mock_resp)))
            mock_ac.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await client.verify_token()

        assert result["login"] == "octocat"
        assert result["name"] == "The Octocat"
        assert result["avatar_url"] == "https://github.com/images/octocat.png"

    @pytest.mark.asyncio
    async def test_returns_scopes_as_list(self):
        client = _make_client()
        user_json = {"login": "octocat", "name": "Octocat", "avatar_url": ""}
        mock_resp = _mock_response(user_json, headers={"x-oauth-scopes": "repo, read:org, user"})

        with patch("httpx.AsyncClient") as mock_ac:
            mock_ac.return_value.__aenter__ = AsyncMock(return_value=MagicMock(get=AsyncMock(return_value=mock_resp)))
            mock_ac.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await client.verify_token()

        assert isinstance(result["scopes"], list)
        assert "repo" in result["scopes"]
        assert "read:org" in result["scopes"]

    @pytest.mark.asyncio
    async def test_returns_empty_scopes_when_header_missing(self):
        client = _make_client()
        user_json = {"login": "octocat", "name": "Octocat", "avatar_url": ""}
        mock_resp = _mock_response(user_json, headers={})

        with patch("httpx.AsyncClient") as mock_ac:
            mock_ac.return_value.__aenter__ = AsyncMock(return_value=MagicMock(get=AsyncMock(return_value=mock_resp)))
            mock_ac.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await client.verify_token()

        assert result["scopes"] == []

    @pytest.mark.asyncio
    async def test_calls_user_endpoint(self):
        client = _make_client()
        mock_get = AsyncMock(return_value=_mock_response({"login": "x", "name": "X", "avatar_url": ""}, headers={}))

        with patch("httpx.AsyncClient") as mock_ac:
            mock_session = MagicMock(get=mock_get)
            mock_ac.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_ac.return_value.__aexit__ = AsyncMock(return_value=False)
            await client.verify_token()

        mock_get.assert_called_once()
        call_url = mock_get.call_args[0][0]
        assert call_url.endswith("/user")


# ---------------------------------------------------------------------------
# list_repos
# ---------------------------------------------------------------------------


class TestListRepos:
    @pytest.mark.asyncio
    async def test_returns_list_of_repos(self):
        client = _make_client()
        repos_json = [
            {
                "full_name": "octocat/Hello-World",
                "html_url": "https://github.com/octocat/Hello-World",
                "description": "My first repo",
                "language": "Python",
                "default_branch": "main",
                "private": False,
            }
        ]
        mock_resp = _mock_response(repos_json)

        with patch("httpx.AsyncClient") as mock_ac:
            mock_ac.return_value.__aenter__ = AsyncMock(return_value=MagicMock(get=AsyncMock(return_value=mock_resp)))
            mock_ac.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await client.list_repos()

        assert len(result) == 1
        assert result[0]["full_name"] == "octocat/Hello-World"

    @pytest.mark.asyncio
    async def test_default_pagination_params(self):
        client = _make_client()
        mock_get = AsyncMock(return_value=_mock_response([]))

        with patch("httpx.AsyncClient") as mock_ac:
            mock_session = MagicMock(get=mock_get)
            mock_ac.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_ac.return_value.__aexit__ = AsyncMock(return_value=False)
            await client.list_repos()

        call_url = mock_get.call_args[0][0]
        assert "/user/repos" in call_url

    @pytest.mark.asyncio
    async def test_custom_pagination_params(self):
        client = _make_client()
        mock_get = AsyncMock(return_value=_mock_response([]))

        with patch("httpx.AsyncClient") as mock_ac:
            mock_session = MagicMock(get=mock_get)
            mock_ac.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_ac.return_value.__aexit__ = AsyncMock(return_value=False)
            await client.list_repos(page=2, per_page=50)

        call_kwargs = mock_get.call_args[1]
        params = call_kwargs.get("params", {})
        assert params.get("page") == 2
        assert params.get("per_page") == 50


# ---------------------------------------------------------------------------
# get_repo
# ---------------------------------------------------------------------------


class TestGetRepo:
    @pytest.mark.asyncio
    async def test_returns_repo_details(self):
        client = _make_client()
        repo_json = {
            "full_name": "octocat/Spoon-Knife",
            "html_url": "https://github.com/octocat/Spoon-Knife",
            "description": "A repository to test pull requests",
            "language": "HTML",
            "default_branch": "main",
            "private": False,
        }
        mock_resp = _mock_response(repo_json)

        with patch("httpx.AsyncClient") as mock_ac:
            mock_ac.return_value.__aenter__ = AsyncMock(return_value=MagicMock(get=AsyncMock(return_value=mock_resp)))
            mock_ac.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await client.get_repo("octocat", "Spoon-Knife")

        assert result["full_name"] == "octocat/Spoon-Knife"

    @pytest.mark.asyncio
    async def test_calls_correct_endpoint(self):
        client = _make_client()
        mock_get = AsyncMock(return_value=_mock_response({"full_name": "a/b"}))

        with patch("httpx.AsyncClient") as mock_ac:
            mock_session = MagicMock(get=mock_get)
            mock_ac.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_ac.return_value.__aexit__ = AsyncMock(return_value=False)
            await client.get_repo("myorg", "myrepo")

        call_url = mock_get.call_args[0][0]
        assert "/repos/myorg/myrepo" in call_url


# ---------------------------------------------------------------------------
# list_environments
# ---------------------------------------------------------------------------


class TestListEnvironments:
    @pytest.mark.asyncio
    async def test_returns_list_of_environments(self):
        client = _make_client()
        envs_json = {
            "environments": [
                {"id": 1, "name": "production", "html_url": "https://..."},
                {"id": 2, "name": "staging", "html_url": "https://..."},
            ]
        }
        mock_resp = _mock_response(envs_json)

        with patch("httpx.AsyncClient") as mock_ac:
            mock_ac.return_value.__aenter__ = AsyncMock(return_value=MagicMock(get=AsyncMock(return_value=mock_resp)))
            mock_ac.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await client.list_environments("octocat", "Hello-World")

        assert len(result) == 2
        assert result[0]["name"] == "production"

    @pytest.mark.asyncio
    async def test_calls_correct_endpoint(self):
        client = _make_client()
        mock_get = AsyncMock(return_value=_mock_response({"environments": []}))

        with patch("httpx.AsyncClient") as mock_ac:
            mock_session = MagicMock(get=mock_get)
            mock_ac.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_ac.return_value.__aexit__ = AsyncMock(return_value=False)
            await client.list_environments("owner", "repo")

        call_url = mock_get.call_args[0][0]
        assert "/repos/owner/repo/environments" in call_url


# ---------------------------------------------------------------------------
# get_latest_deployment
# ---------------------------------------------------------------------------


class TestGetLatestDeployment:
    @pytest.mark.asyncio
    async def test_returns_deployment_url_when_found(self):
        client = _make_client()
        deployments_json = [
            {"id": 1, "environment": "production", "statuses_url": "https://api.github.com/repos/o/r/deployments/1/statuses"}
        ]
        statuses_json = [
            {"state": "success", "environment_url": "https://prod.example.com"}
        ]
        mock_deploy_resp = _mock_response(deployments_json)
        mock_status_resp = _mock_response(statuses_json)

        call_count = 0

        async def mock_get(url, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return mock_deploy_resp
            return mock_status_resp

        with patch("httpx.AsyncClient") as mock_ac:
            mock_session = MagicMock(get=mock_get)
            mock_ac.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_ac.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await client.get_latest_deployment("owner", "repo", "production")

        assert result is not None

    @pytest.mark.asyncio
    async def test_returns_none_when_no_deployments(self):
        client = _make_client()
        mock_resp = _mock_response([])

        with patch("httpx.AsyncClient") as mock_ac:
            mock_ac.return_value.__aenter__ = AsyncMock(return_value=MagicMock(get=AsyncMock(return_value=mock_resp)))
            mock_ac.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await client.get_latest_deployment("owner", "repo", "production")

        assert result is None


# ---------------------------------------------------------------------------
# get_file_content
# ---------------------------------------------------------------------------


class TestGetFileContent:
    @pytest.mark.asyncio
    async def test_decodes_base64_content(self):
        client = _make_client()
        raw_content = "name: my-service\nversion: 1.0"
        encoded = base64.b64encode(raw_content.encode()).decode()
        file_json = {"content": encoded, "encoding": "base64"}
        mock_resp = _mock_response(file_json)

        with patch("httpx.AsyncClient") as mock_ac:
            mock_ac.return_value.__aenter__ = AsyncMock(return_value=MagicMock(get=AsyncMock(return_value=mock_resp)))
            mock_ac.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await client.get_file_content("owner", "repo", ".tinaa.yml")

        assert result == raw_content

    @pytest.mark.asyncio
    async def test_handles_base64_with_newlines(self):
        """GitHub adds newlines inside base64-encoded content."""
        client = _make_client()
        raw_content = "hello world"
        encoded = base64.b64encode(raw_content.encode()).decode()
        # Simulate GitHub's newline-padded base64
        encoded_with_newlines = "\n".join([encoded[i:i+60] for i in range(0, len(encoded), 60)]) + "\n"
        file_json = {"content": encoded_with_newlines, "encoding": "base64"}
        mock_resp = _mock_response(file_json)

        with patch("httpx.AsyncClient") as mock_ac:
            mock_ac.return_value.__aenter__ = AsyncMock(return_value=MagicMock(get=AsyncMock(return_value=mock_resp)))
            mock_ac.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await client.get_file_content("owner", "repo", "README.md")

        assert result == raw_content

    @pytest.mark.asyncio
    async def test_returns_none_on_404(self):
        client = _make_client()
        import httpx

        mock_resp = MagicMock()
        mock_resp.status_code = 404
        mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not Found", request=MagicMock(), response=mock_resp
        )

        with patch("httpx.AsyncClient") as mock_ac:
            mock_ac.return_value.__aenter__ = AsyncMock(return_value=MagicMock(get=AsyncMock(return_value=mock_resp)))
            mock_ac.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await client.get_file_content("owner", "repo", "nonexistent.yml")

        assert result is None

    @pytest.mark.asyncio
    async def test_includes_ref_when_provided(self):
        client = _make_client()
        raw_content = "content"
        encoded = base64.b64encode(raw_content.encode()).decode()
        mock_get = AsyncMock(return_value=_mock_response({"content": encoded}))

        with patch("httpx.AsyncClient") as mock_ac:
            mock_session = MagicMock(get=mock_get)
            mock_ac.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_ac.return_value.__aexit__ = AsyncMock(return_value=False)
            await client.get_file_content("owner", "repo", "file.txt", ref="main")

        call_kwargs = mock_get.call_args[1]
        params = call_kwargs.get("params", {})
        assert params.get("ref") == "main"


# ---------------------------------------------------------------------------
# list_directory
# ---------------------------------------------------------------------------


class TestListDirectory:
    @pytest.mark.asyncio
    async def test_returns_list_of_entries(self):
        client = _make_client()
        dir_json = [
            {"name": "src", "type": "dir", "path": "src"},
            {"name": "README.md", "type": "file", "path": "README.md"},
        ]
        mock_resp = _mock_response(dir_json)

        with patch("httpx.AsyncClient") as mock_ac:
            mock_ac.return_value.__aenter__ = AsyncMock(return_value=MagicMock(get=AsyncMock(return_value=mock_resp)))
            mock_ac.return_value.__aexit__ = AsyncMock(return_value=False)
            result = await client.list_directory("owner", "repo")

        assert len(result) == 2
        assert result[0]["name"] == "src"

    @pytest.mark.asyncio
    async def test_uses_root_by_default(self):
        client = _make_client()
        mock_get = AsyncMock(return_value=_mock_response([]))

        with patch("httpx.AsyncClient") as mock_ac:
            mock_session = MagicMock(get=mock_get)
            mock_ac.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_ac.return_value.__aexit__ = AsyncMock(return_value=False)
            await client.list_directory("owner", "repo")

        call_url = mock_get.call_args[0][0]
        assert "/repos/owner/repo/contents" in call_url

    @pytest.mark.asyncio
    async def test_uses_provided_path(self):
        client = _make_client()
        mock_get = AsyncMock(return_value=_mock_response([]))

        with patch("httpx.AsyncClient") as mock_ac:
            mock_session = MagicMock(get=mock_get)
            mock_ac.return_value.__aenter__ = AsyncMock(return_value=mock_session)
            mock_ac.return_value.__aexit__ = AsyncMock(return_value=False)
            await client.list_directory("owner", "repo", path="src/components")

        call_url = mock_get.call_args[0][0]
        assert "src/components" in call_url
