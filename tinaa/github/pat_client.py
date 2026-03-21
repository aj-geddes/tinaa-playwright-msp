"""GitHub client using Personal Access Token authentication."""

import base64

import httpx


class GitHubPATClient:
    """Lightweight GitHub client using PAT auth."""

    GITHUB_API = "https://api.github.com"

    def __init__(self, token: str) -> None:
        """Initialize with a GitHub Personal Access Token.

        Args:
            token: GitHub PAT (classic or fine-grained).
        """
        self._token = token
        self._headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

    async def verify_token(self) -> dict:
        """Verify the token is valid and return user info.

        Calls GET /user and reads the x-oauth-scopes response header.

        Returns:
            {"login": str, "name": str, "avatar_url": str, "scopes": list[str]}
        """
        url = f"{self.GITHUB_API}/user"
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=self._headers)
            resp.raise_for_status()
            data = resp.json()
            scopes_header = resp.headers.get("x-oauth-scopes", "")
            scopes = (
                [s.strip() for s in scopes_header.split(",") if s.strip()] if scopes_header else []
            )
            return {
                "login": data.get("login", ""),
                "name": data.get("name", ""),
                "avatar_url": data.get("avatar_url", ""),
                "scopes": scopes,
            }

    async def list_repos(self, page: int = 1, per_page: int = 30) -> list[dict]:
        """List repos accessible to the token.

        Calls GET /user/repos?sort=updated.

        Args:
            page: Page number for pagination (1-based).
            per_page: Number of repos per page (max 100).

        Returns:
            List of dicts with keys: full_name, html_url, description,
            language, default_branch, private.
        """
        url = f"{self.GITHUB_API}/user/repos"
        params = {"sort": "updated", "page": page, "per_page": per_page}
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=self._headers, params=params)
            resp.raise_for_status()
            repos = resp.json()
            return [
                {
                    "full_name": r.get("full_name", ""),
                    "html_url": r.get("html_url", ""),
                    "description": r.get("description", ""),
                    "language": r.get("language"),
                    "default_branch": r.get("default_branch", "main"),
                    "private": r.get("private", False),
                }
                for r in repos
            ]

    async def get_repo(self, owner: str, repo: str) -> dict:
        """Get repository details.

        Args:
            owner: Repository owner (user or organisation).
            repo: Repository name.

        Returns:
            Repository metadata dict.
        """
        url = f"{self.GITHUB_API}/repos/{owner}/{repo}"
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=self._headers)
            resp.raise_for_status()
            return resp.json()

    async def list_environments(self, owner: str, repo: str) -> list[dict]:
        """List deployment environments for a repository.

        Calls GET /repos/{owner}/{repo}/environments.

        Args:
            owner: Repository owner.
            repo: Repository name.

        Returns:
            List of environment dicts.
        """
        url = f"{self.GITHUB_API}/repos/{owner}/{repo}/environments"
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=self._headers)
            resp.raise_for_status()
            data = resp.json()
            return data.get("environments", [])

    async def get_latest_deployment(self, owner: str, repo: str, environment: str) -> dict | None:
        """Get the latest successful deployment for an environment.

        Args:
            owner: Repository owner.
            repo: Repository name.
            environment: Environment name (e.g., "production").

        Returns:
            Deployment dict with environment_url, or None if not found.
        """
        url = f"{self.GITHUB_API}/repos/{owner}/{repo}/deployments"
        params = {"environment": environment, "per_page": 1}
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=self._headers, params=params)
            resp.raise_for_status()
            deployments = resp.json()
            if not deployments:
                return None
            deployment = deployments[0]
            statuses_url = deployment.get("statuses_url", "")
            if not statuses_url:
                return None
            status_resp = await client.get(statuses_url, headers=self._headers)
            status_resp.raise_for_status()
            statuses = status_resp.json()
            for status in statuses:
                if status.get("state") == "success":
                    return {
                        "deployment_id": deployment.get("id"),
                        "environment": environment,
                        "environment_url": status.get("environment_url", ""),
                        "state": "success",
                    }
            return None

    async def get_file_content(
        self, owner: str, repo: str, path: str, ref: str | None = None
    ) -> str | None:
        """Read a file from the repository.

        Decodes base64-encoded content returned by the GitHub Contents API.
        GitHub adds newlines inside the base64 string; these are stripped
        before decoding.

        Args:
            owner: Repository owner.
            repo: Repository name.
            path: File path within the repository (e.g., ".tinaa.yml").
            ref: Optional git ref (branch, tag, or SHA).

        Returns:
            Decoded file content as a string, or None if the file does not exist.
        """
        url = f"{self.GITHUB_API}/repos/{owner}/{repo}/contents/{path}"
        params: dict = {}
        if ref is not None:
            params["ref"] = ref
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(url, headers=self._headers, params=params)
                resp.raise_for_status()
                data = resp.json()
                raw = data.get("content", "")
                return base64.b64decode(raw.replace("\n", "")).decode("utf-8")
        except httpx.HTTPStatusError as exc:
            if exc.response.status_code == 404:
                return None
            raise

    async def list_directory(self, owner: str, repo: str, path: str = "") -> list[dict]:
        """List directory contents in a repository.

        Args:
            owner: Repository owner.
            repo: Repository name.
            path: Directory path within the repository (empty string for root).

        Returns:
            List of content objects (files and subdirectories).
        """
        url = f"{self.GITHUB_API}/repos/{owner}/{repo}/contents/{path}"
        async with httpx.AsyncClient() as client:
            resp = await client.get(url, headers=self._headers)
            resp.raise_for_status()
            return resp.json()
