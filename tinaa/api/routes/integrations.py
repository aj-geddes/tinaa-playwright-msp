"""API routes for managing external integrations (GitHub, alerts, etc.)."""

import logging

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from tinaa.github.pat_client import GitHubPATClient
from tinaa.services import ServiceContainer, get_services

log = logging.getLogger(__name__)

router = APIRouter(prefix="/integrations")

# ---------------------------------------------------------------------------
# In-process credential store (replaced by encrypted DB in production)
# ---------------------------------------------------------------------------

_CREDENTIAL_STORE: dict = {}


def _get_saved_pat() -> str | None:
    """Return the saved GitHub PAT, or None if not configured."""
    return _CREDENTIAL_STORE.get("github_pat")


def _save_pat(token: str) -> None:
    """Persist the GitHub PAT in the in-process store."""
    _CREDENTIAL_STORE["github_pat"] = token
    _CREDENTIAL_STORE["github_type"] = "pat"


def _get_saved_app() -> dict | None:
    """Return the saved GitHub App config, or None if not configured."""
    return _CREDENTIAL_STORE.get("github_app")


def _save_app(app_id: str, private_key: str, webhook_secret: str) -> None:
    """Persist GitHub App credentials in the in-process store."""
    _CREDENTIAL_STORE["github_app"] = {
        "app_id": app_id,
        "private_key": private_key,
        "webhook_secret": webhook_secret,
    }
    _CREDENTIAL_STORE["github_type"] = "app"


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class GitHubPATSetup(BaseModel):
    """Request body for GitHub PAT operations."""

    token: str


class GitHubAppSetup(BaseModel):
    """Request body for GitHub App configuration."""

    app_id: str
    private_key: str
    webhook_secret: str


class GitHubRepoImport(BaseModel):
    """Request body for importing a GitHub repository as a TINAA product."""

    repo_full_name: str
    environments: dict[str, str] | None = None


# ---------------------------------------------------------------------------
# GitHub PAT endpoints
# ---------------------------------------------------------------------------


@router.post("/github/pat/verify")
async def verify_github_pat(request: GitHubPATSetup) -> dict:
    """Verify a GitHub PAT and return user info plus available repos.

    Args:
        request: Contains the token to verify.

    Returns:
        {"valid": bool, "user": {...}, "repos": [...], "scopes": [...]}

    Raises:
        HTTPException 400: Token is invalid or rejected by GitHub.
    """
    gh = GitHubPATClient(token=request.token)
    try:
        user = await gh.verify_token()
        repos = await gh.list_repos(per_page=30)
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"GitHub rejected the token: HTTP {exc.response.status_code}",
        ) from exc
    return {
        "valid": True,
        "user": user,
        "repos": repos,
        "scopes": user.get("scopes", []),
    }


@router.post("/github/pat/save")
async def save_github_pat(request: GitHubPATSetup) -> dict:
    """Save a GitHub PAT after verifying it is valid.

    Stores in the in-process credential store (use encrypted DB in production).

    Args:
        request: Contains the token to save.

    Returns:
        {"saved": true, "user": {...}}

    Raises:
        HTTPException 400: Token is invalid.
    """
    gh = GitHubPATClient(token=request.token)
    try:
        user = await gh.verify_token()
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=400,
            detail=f"GitHub rejected the token: HTTP {exc.response.status_code}",
        ) from exc
    _save_pat(request.token)
    log.info("GitHub PAT saved for user %s", user.get("login"))
    return {"saved": True, "user": user}


# ---------------------------------------------------------------------------
# GitHub repo endpoints
# ---------------------------------------------------------------------------


@router.get("/github/repos")
async def list_github_repos(page: int = 1) -> list[dict]:
    """List repositories accessible via saved GitHub credentials.

    Args:
        page: Pagination page number (1-based).

    Returns:
        List of repo dicts with name, URL, language, last updated.

    Raises:
        HTTPException 404: No GitHub credentials configured.
    """
    token = _get_saved_pat()
    if not token:
        raise HTTPException(
            status_code=404,
            detail="GitHub integration not configured. Save a PAT first.",
        )
    gh = GitHubPATClient(token=token)
    return await gh.list_repos(page=page)


@router.post("/github/repos/import")
async def import_github_repo(
    request: GitHubRepoImport,
    services: ServiceContainer = Depends(get_services),  # noqa: B008
) -> dict:
    """Import a GitHub repository as a TINAA product.

    Steps:
    1. Fetch repo details from GitHub.
    2. Check for .tinaa.yml configuration file.
    3. Create a product entry in the product registry.
    4. Auto-discover deployment environments from the GitHub Environments API.
    5. Return the created product.

    Args:
        request: Contains repo_full_name ("owner/repo") and optional environments.
        services: Injected service container.

    Returns:
        Created product dict.

    Raises:
        HTTPException 400: Invalid repo name format.
        HTTPException 404: No GitHub credentials configured.
    """
    token = _get_saved_pat()
    if not token:
        raise HTTPException(
            status_code=404,
            detail="GitHub integration not configured. Save a PAT first.",
        )

    parts = request.repo_full_name.split("/")
    if len(parts) != 2:
        raise HTTPException(
            status_code=400,
            detail="repo_full_name must be in 'owner/repo' format.",
        )
    owner, repo_name = parts

    gh = GitHubPATClient(token=token)

    try:
        repo = await gh.get_repo(owner, repo_name)
    except httpx.HTTPStatusError as exc:
        raise HTTPException(
            status_code=exc.response.status_code,
            detail=f"GitHub repo not found or inaccessible: {request.repo_full_name}",
        ) from exc

    tinaa_config = await gh.get_file_content(owner, repo_name, ".tinaa.yml")

    gh_environments = await gh.list_environments(owner, repo_name)

    environments: dict[str, str] = request.environments or {}
    if not environments:
        for env in gh_environments:
            env_name = env.get("name", "")
            if env_name:
                deployment = await gh.get_latest_deployment(owner, repo_name, env_name)
                if deployment and deployment.get("environment_url"):
                    environments[env_name] = deployment["environment_url"]

    product = await services.registry.create_product(
        name=repo_name,
        repository_url=repo.get("html_url", ""),
        description=repo.get("description", "") or "",
        environments=environments or None,
    )

    log.info("Imported GitHub repo %s as product %s", request.repo_full_name, product.id)
    return {
        "imported": True,
        "product_id": str(product.id),
        "product_name": product.name,
        "product_slug": product.slug,
        "repository_url": repo.get("html_url", ""),
        "tinaa_config_found": tinaa_config is not None,
        "environments_discovered": list(environments.keys()),
    }


# ---------------------------------------------------------------------------
# GitHub status and configuration endpoints
# ---------------------------------------------------------------------------


@router.get("/github/status")
async def github_integration_status() -> dict:
    """Check current GitHub integration configuration status.

    Returns:
        {"configured": bool, "type": "pat"|"app"|null, "user": {...}|null}
    """
    integration_type = _CREDENTIAL_STORE.get("github_type")
    if not integration_type:
        return {"configured": False, "type": None, "user": None}

    user_info = None
    if integration_type == "pat":
        token = _get_saved_pat()
        if token:
            try:
                gh = GitHubPATClient(token=token)
                user_info = await gh.verify_token()
            except httpx.HTTPStatusError:
                return {"configured": False, "type": None, "user": None}

    return {
        "configured": True,
        "type": integration_type,
        "user": user_info,
    }


@router.post("/github/app/setup")
async def setup_github_app(request: GitHubAppSetup) -> dict:
    """Configure GitHub App credentials.

    Stores the App ID, private key PEM, and webhook secret for use by the
    GitHub App integration layer.

    Args:
        request: Contains app_id, private_key (PEM content), and webhook_secret.

    Returns:
        {"configured": true, "app_id": str}
    """
    _save_app(
        app_id=request.app_id,
        private_key=request.private_key,
        webhook_secret=request.webhook_secret,
    )
    log.info("GitHub App configured with app_id=%s", request.app_id)
    return {"configured": True, "app_id": request.app_id}


# ---------------------------------------------------------------------------
# Setup guide
# ---------------------------------------------------------------------------


@router.get("/github/setup-guide")
async def github_setup_guide() -> dict:
    """Return step-by-step setup instructions for PAT and GitHub App modes.

    Returns structured content the UI can render as a setup wizard.
    """
    return {
        "pat": {
            "title": "Personal Access Token (Recommended for getting started)",
            "steps": [
                {
                    "step": 1,
                    "title": "Go to GitHub Settings",
                    "description": (
                        "Navigate to GitHub → Settings → Developer Settings → "
                        "Personal Access Tokens → Fine-grained tokens"
                    ),
                    "url": "https://github.com/settings/tokens?type=beta",
                },
                {
                    "step": 2,
                    "title": "Create a new token",
                    "description": (
                        "Click 'Generate new token'. Give it a descriptive name like 'TINAA MSP'."
                    ),
                },
                {
                    "step": 3,
                    "title": "Set permissions",
                    "description": (
                        "Select the repositories you want TINAA to manage. Under permissions, "
                        "enable: Contents (read), Deployments (read), Environments (read), "
                        "Pull Requests (read)."
                    ),
                },
                {
                    "step": 4,
                    "title": "Copy and paste",
                    "description": "Copy the generated token and paste it below.",
                },
            ],
            "required_permissions": [
                "contents:read",
                "deployments:read",
                "environments:read",
                "pull_requests:read",
            ],
        },
        "app": {
            "title": "GitHub App (Recommended for organizations)",
            "steps": [
                {
                    "step": 1,
                    "title": "Create a GitHub App",
                    "description": (
                        "Go to your organization settings → Developer Settings → "
                        "GitHub Apps → New GitHub App."
                    ),
                },
                {
                    "step": 2,
                    "title": "Configure the app",
                    "description": (
                        "Set Homepage URL to your TINAA instance URL. "
                        "Set Webhook URL to https://your-tinaa.com/api/v1/webhooks/github."
                    ),
                },
                {
                    "step": 3,
                    "title": "Set permissions",
                    "description": (
                        "Repository permissions: Contents (read), Deployments (read/write), "
                        "Checks (read/write), Pull Requests (read), Environments (read)."
                    ),
                },
                {
                    "step": 4,
                    "title": "Subscribe to events",
                    "description": (
                        "Subscribe to: deployment_status, pull_request, push, check_suite."
                    ),
                },
                {
                    "step": 5,
                    "title": "Generate private key",
                    "description": (
                        "After creating the app, generate a private key and download the PEM file."
                    ),
                },
                {
                    "step": 6,
                    "title": "Enter credentials",
                    "description": (
                        "Enter the App ID, paste the private key content, "
                        "and the webhook secret below."
                    ),
                },
            ],
            "required_permissions": [
                "contents:read",
                "deployments:read+write",
                "checks:read+write",
                "pull_requests:read",
                "environments:read",
            ],
        },
    }
