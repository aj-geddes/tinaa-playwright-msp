"""
GitHub API client using GitHub App authentication.

Handles JWT generation, installation token exchange, and authenticated
API requests on behalf of a GitHub App installation.
"""

import base64
import time
from typing import Any

import httpx
import jwt

GITHUB_API_BASE = "https://api.github.com"
JWT_ISSUED_AT_OFFSET = 60  # seconds in the past (clock skew tolerance)
JWT_EXPIRY_SECONDS = 600  # 10 minutes (GitHub maximum)


class GitHubClient:
    """Async GitHub API client using GitHub App authentication."""

    def __init__(self, app_id: str, private_key: str) -> None:
        """Initialize with GitHub App credentials.

        Args:
            app_id: GitHub App ID.
            private_key: PEM private key content.
        """
        self.app_id = app_id
        self.private_key = private_key

    def _generate_jwt(self) -> str:
        """Generate a JWT for GitHub App authentication.

        Returns:
            Signed RS256 JWT string.

        The payload fields are:
        - iss: app_id
        - iat: now - 60  (back-dated by 60s for clock skew)
        - exp: now + 600  (10-minute maximum per GitHub docs)
        """
        now = int(time.time())
        payload: dict[str, Any] = {
            "iss": self.app_id,
            "iat": now - JWT_ISSUED_AT_OFFSET,
            "exp": now + JWT_EXPIRY_SECONDS,
        }
        return jwt.encode(payload, self.private_key, algorithm="RS256")

    async def get_installation_token(self, installation_id: int) -> str:
        """Exchange a JWT for an installation access token.

        Args:
            installation_id: The GitHub App installation ID.

        Returns:
            Installation access token string.
        """
        url = f"{GITHUB_API_BASE}/app/installations/{installation_id}/access_tokens"
        jwt_token = self._generate_jwt()
        headers = {
            "Authorization": f"Bearer {jwt_token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        async with httpx.AsyncClient() as client:
            response = await client.post(url, headers=headers)
            response.raise_for_status()
            return response.json()["token"]

    async def _request(
        self,
        method: str,
        url: str,
        installation_id: int,
        **kwargs: Any,
    ) -> Any:
        """Make an authenticated API request using an installation token.

        Args:
            method: HTTP method (GET, POST, PATCH, etc.).
            url: Full URL to request.
            installation_id: Installation ID for token exchange.
            **kwargs: Additional arguments passed to httpx.

        Returns:
            Parsed JSON response.
        """
        token = await self.get_installation_token(installation_id)
        headers = kwargs.pop("headers", {})
        headers.update(
            {
                "Authorization": f"token {token}",
                "Accept": "application/vnd.github+json",
                "X-GitHub-Api-Version": "2022-11-28",
            }
        )
        async with httpx.AsyncClient() as client:
            response = await client.request(method, url, headers=headers, **kwargs)
            response.raise_for_status()
            return response.json()

    async def get_repository(self, installation_id: int, owner: str, repo: str) -> dict[str, Any]:
        """Fetch repository metadata.

        Args:
            installation_id: Installation ID.
            owner: Repository owner (user or organisation).
            repo: Repository name.

        Returns:
            GitHub repository object.
        """
        url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}"
        return await self._request("GET", url, installation_id)

    async def get_file_content(
        self,
        installation_id: int,
        owner: str,
        repo: str,
        path: str,
        ref: str | None = None,
    ) -> str:
        """Fetch and decode the content of a file from a repository.

        Args:
            installation_id: Installation ID.
            owner: Repository owner.
            repo: Repository name.
            path: File path within the repository.
            ref: Optional git ref (branch, tag, or SHA).

        Returns:
            Decoded file content as a string.
        """
        url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/contents/{path}"
        if ref is not None:
            url = f"{url}?ref={ref}"
        data = await self._request("GET", url, installation_id)
        raw = data["content"]
        # GitHub adds newlines inside the base64 string
        return base64.b64decode(raw.replace("\n", "")).decode("utf-8")

    async def list_directory(
        self,
        installation_id: int,
        owner: str,
        repo: str,
        path: str = "",
        ref: str | None = None,
    ) -> list[dict[str, Any]]:
        """List the contents of a directory in a repository.

        Args:
            installation_id: Installation ID.
            owner: Repository owner.
            repo: Repository name.
            path: Directory path (empty string for root).
            ref: Optional git ref.

        Returns:
            List of content objects (files and directories).
        """
        url = f"{GITHUB_API_BASE}/repos/{owner}/{repo}/contents/{path}"
        if ref is not None:
            url = f"{url}?ref={ref}"
        result = await self._request("GET", url, installation_id)
        return result
