#!/usr/bin/env python3
"""
TINAA Git Authentication Module

Handles secure git authentication for repository cloning and operations
supporting both Personal Access Tokens (PAT) and GitHub App authentication.
"""

import logging
import time
from datetime import datetime, timedelta
from typing import Any

import aiohttp
import git
import jwt
from git.exc import GitCommandError

from app.secrets_manager import secrets_manager

logger = logging.getLogger("tinaa.git_auth")


class GitAuthenticator:
    """Handles git authentication with multiple methods"""

    def __init__(self):
        self.token_cache: dict[str, dict[str, Any]] = {}

    async def get_authenticated_clone_url(
        self, repository_url: str, auth_type: str = "auto"
    ) -> tuple[str, dict[str, Any]]:
        """
        Get an authenticated clone URL for the repository

        Args:
            repository_url: Original repository URL
            auth_type: Authentication type ("pat", "github_app", "auto")

        Returns:
            Tuple of (authenticated_url, auth_info)
        """
        git_config = await secrets_manager.get_git_config(auth_type)

        if not git_config.get("auth_type"):
            raise Exception("No git authentication configured")

        if git_config["auth_type"] == "pat":
            return await self._get_pat_clone_url(repository_url, git_config)
        if git_config["auth_type"] == "github_app":
            return await self._get_github_app_clone_url(repository_url, git_config)
        raise Exception(f"Unsupported auth type: {git_config['auth_type']}")

    async def _get_pat_clone_url(
        self, repository_url: str, git_config: dict[str, Any]
    ) -> tuple[str, dict[str, Any]]:
        """Get clone URL with Personal Access Token authentication"""
        credentials = git_config["credentials"]
        username = credentials["username"]
        token = credentials["token"]

        # Parse repository URL to extract owner/repo
        repo_info = self._parse_repository_url(repository_url)

        if repo_info["provider"] == "github":
            authenticated_url = f"https://{username}:{token}@github.com/{repo_info['owner']}/{repo_info['repo']}.git"
        elif repo_info["provider"] == "gitlab":
            authenticated_url = f"https://{username}:{token}@gitlab.com/{repo_info['owner']}/{repo_info['repo']}.git"
        else:
            # Generic git provider
            authenticated_url = repository_url.replace(
                "https://", f"https://{username}:{token}@"
            )

        auth_info = {
            "method": "pat",
            "username": username,
            "expires_at": None,  # PATs don't expire automatically
        }

        return authenticated_url, auth_info

    async def _get_github_app_clone_url(
        self, repository_url: str, git_config: dict[str, Any]
    ) -> tuple[str, dict[str, Any]]:
        """Get clone URL with GitHub App authentication"""
        credentials = git_config["credentials"]

        # Generate installation access token
        access_token = await self._get_github_app_token(credentials)

        repo_info = self._parse_repository_url(repository_url)
        if repo_info["provider"] != "github":
            raise Exception(
                "GitHub App authentication only supports GitHub repositories"
            )

        authenticated_url = f"https://x-access-token:{access_token['token']}@github.com/{repo_info['owner']}/{repo_info['repo']}.git"

        auth_info = {
            "method": "github_app",
            "app_id": credentials["app_id"],
            "installation_id": credentials["installation_id"],
            "token": access_token["token"],
            "expires_at": access_token["expires_at"],
        }

        return authenticated_url, auth_info

    async def _get_github_app_token(
        self, credentials: dict[str, str]
    ) -> dict[str, Any]:
        """Generate GitHub App installation access token"""
        app_id = credentials["app_id"]
        private_key = credentials["private_key"]
        installation_id = credentials["installation_id"]

        # Check cache first
        cache_key = f"github_app_{app_id}_{installation_id}"
        if cache_key in self.token_cache:
            cached_token = self.token_cache[cache_key]
            # Check if token is still valid (with 5 minute buffer)
            if datetime.fromisoformat(
                cached_token["expires_at"]
            ) > datetime.now() + timedelta(minutes=5):
                logger.info("Using cached GitHub App token")
                return cached_token

        # Generate JWT for GitHub App authentication
        now = int(time.time())
        payload = {
            "iat": now - 60,  # Issued 1 minute ago
            "exp": now + (10 * 60),  # Expires in 10 minutes
            "iss": app_id,
        }

        jwt_token = jwt.encode(payload, private_key, algorithm="RS256")

        # Get installation access token
        async with aiohttp.ClientSession() as session:
            headers = {
                "Authorization": f"Bearer {jwt_token}",
                "Accept": "application/vnd.github.v3+json",
            }

            url = f"https://api.github.com/app/installations/{installation_id}/access_tokens"

            async with session.post(url, headers=headers) as response:
                if response.status != 201:
                    error_text = await response.text()
                    raise Exception(
                        f"Failed to get GitHub App token: {response.status} - {error_text}"
                    )

                token_data = await response.json()

        # Parse expiration time
        expires_at = datetime.fromisoformat(
            token_data["expires_at"].replace("Z", "+00:00")
        )

        token_info = {
            "token": token_data["token"],
            "expires_at": expires_at.isoformat(),
        }

        # Cache the token
        self.token_cache[cache_key] = token_info

        logger.info(f"Generated new GitHub App token, expires at {expires_at}")
        return token_info

    def _parse_repository_url(self, repository_url: str) -> dict[str, str]:
        """Parse repository URL to extract provider, owner, and repo name"""
        if "github.com" in repository_url:
            provider = "github"
        elif "gitlab.com" in repository_url:
            provider = "gitlab"
        else:
            provider = "unknown"

        # Extract owner/repo from URL
        if repository_url.endswith(".git"):
            url = repository_url[:-4]
        else:
            url = repository_url

        if url.startswith("https://"):
            url = url[8:]
        elif url.startswith("http://"):
            url = url[7:]

        # Remove domain
        if "/" in url:
            path = url.split("/", 1)[1]
        else:
            raise Exception(f"Invalid repository URL: {repository_url}")

        parts = path.split("/")
        if len(parts) >= 2:
            owner = parts[0]
            repo = parts[1]
        else:
            raise Exception(f"Cannot parse owner/repo from URL: {repository_url}")

        return {
            "provider": provider,
            "owner": owner,
            "repo": repo,
            "full_name": f"{owner}/{repo}",
        }

    async def clone_repository(
        self,
        repository_url: str,
        destination_path: str,
        auth_type: str = "auto",
        branch: str | None = None,
    ) -> dict[str, Any]:
        """
        Clone a repository with authentication

        Args:
            repository_url: Repository URL to clone
            destination_path: Local path to clone to
            auth_type: Authentication type to use
            branch: Optional specific branch to clone

        Returns:
            Clone operation result
        """
        try:
            logger.info(f"Cloning repository {repository_url} to {destination_path}")

            # Get authenticated clone URL
            auth_url, auth_info = await self.get_authenticated_clone_url(
                repository_url, auth_type
            )

            # Prepare clone options
            clone_kwargs = {
                "to_path": destination_path,
                "depth": 1,  # Shallow clone for efficiency
            }

            if branch:
                clone_kwargs["branch"] = branch

            # Perform the clone operation
            repo = git.Repo.clone_from(auth_url, **clone_kwargs)

            # Get repository information
            repo_info = {
                "success": True,
                "repository_url": repository_url,
                "destination_path": destination_path,
                "branch": repo.active_branch.name,
                "commit_hash": repo.head.commit.hexsha,
                "commit_message": repo.head.commit.message.strip(),
                "author": str(repo.head.commit.author),
                "auth_method": auth_info["method"],
                "cloned_at": datetime.now().isoformat(),
            }

            logger.info(f"Successfully cloned repository to {destination_path}")
            return repo_info

        except GitCommandError as e:
            error_msg = f"Git clone failed: {e!s}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "repository_url": repository_url,
                "destination_path": destination_path,
            }
        except Exception as e:
            error_msg = f"Clone operation failed: {e!s}"
            logger.error(error_msg)
            return {
                "success": False,
                "error": error_msg,
                "repository_url": repository_url,
                "destination_path": destination_path,
            }

    async def fetch_repository_info(
        self, repository_url: str, auth_type: str = "auto"
    ) -> dict[str, Any]:
        """
        Fetch repository information without cloning

        Args:
            repository_url: Repository URL
            auth_type: Authentication type

        Returns:
            Repository information
        """
        try:
            repo_info = self._parse_repository_url(repository_url)

            if repo_info["provider"] == "github":
                return await self._fetch_github_repo_info(repo_info, auth_type)
            if repo_info["provider"] == "gitlab":
                return await self._fetch_gitlab_repo_info(repo_info, auth_type)
            return {
                "success": False,
                "error": "Repository info fetching not supported for this provider",
            }

        except Exception as e:
            logger.error(f"Failed to fetch repository info: {e!s}")
            return {"success": False, "error": str(e)}

    async def _fetch_github_repo_info(
        self, repo_info: dict[str, str], auth_type: str
    ) -> dict[str, Any]:
        """Fetch GitHub repository information via API"""
        try:
            git_config = await secrets_manager.get_git_config(auth_type)

            headers = {"Accept": "application/vnd.github.v3+json"}

            # Add authentication header if available
            if git_config.get("auth_type") == "pat":
                token = git_config["credentials"]["token"]
                headers["Authorization"] = f"token {token}"
            elif git_config.get("auth_type") == "github_app":
                app_token = await self._get_github_app_token(git_config["credentials"])
                headers["Authorization"] = f"token {app_token['token']}"

            url = f"https://api.github.com/repos/{repo_info['full_name']}"

            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        return {
                            "success": True,
                            "name": data["name"],
                            "full_name": data["full_name"],
                            "description": data.get("description", ""),
                            "language": data.get("language"),
                            "default_branch": data["default_branch"],
                            "private": data["private"],
                            "stars": data["stargazers_count"],
                            "forks": data["forks_count"],
                            "last_updated": data["updated_at"],
                            "clone_url": data["clone_url"],
                            "ssh_url": data["ssh_url"],
                        }
                    error_text = await response.text()
                    return {
                        "success": False,
                        "error": f"GitHub API error: {response.status} - {error_text}",
                    }

        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _fetch_gitlab_repo_info(
        self, repo_info: dict[str, str], auth_type: str
    ) -> dict[str, Any]:
        """Fetch GitLab repository information via API"""
        # This would implement GitLab API access similar to GitHub
        return {"success": False, "error": "GitLab API integration not yet implemented"}

    def clear_token_cache(self):
        """Clear the token cache"""
        self.token_cache.clear()
        logger.info("Git token cache cleared")

    async def validate_git_credentials(self, auth_type: str = "auto") -> dict[str, Any]:
        """
        Validate git credentials by testing access

        Args:
            auth_type: Authentication type to validate

        Returns:
            Validation results
        """
        try:
            git_config = await secrets_manager.get_git_config(auth_type)

            if not git_config.get("auth_type"):
                return {"valid": False, "error": "No git authentication configured"}

            # Test with a known public repository
            test_repo = "https://github.com/octocat/Hello-World"

            try:
                auth_url, auth_info = await self.get_authenticated_clone_url(
                    test_repo, auth_type
                )

                # Test repository access without actually cloning
                repo_info = await self.fetch_repository_info(test_repo, auth_type)

                if repo_info.get("success"):
                    return {
                        "valid": True,
                        "auth_method": auth_info["method"],
                        "test_repository": test_repo,
                        "details": auth_info,
                    }
                return {
                    "valid": False,
                    "error": repo_info.get("error", "Unknown error"),
                    "auth_method": auth_info["method"],
                }

            except Exception as e:
                return {
                    "valid": False,
                    "error": str(e),
                    "auth_method": git_config["auth_type"],
                }

        except Exception as e:
            return {"valid": False, "error": str(e)}


# Global git authenticator instance
git_authenticator = GitAuthenticator()


# Convenience functions
async def clone_repository(
    repository_url: str, destination_path: str, **kwargs
) -> dict[str, Any]:
    """Convenience function for cloning repositories"""
    return await git_authenticator.clone_repository(
        repository_url, destination_path, **kwargs
    )


async def get_repository_info(repository_url: str, **kwargs) -> dict[str, Any]:
    """Convenience function for getting repository information"""
    return await git_authenticator.fetch_repository_info(repository_url, **kwargs)
