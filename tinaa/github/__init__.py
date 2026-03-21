"""
TINAA GitHub App Integration.

Provides GitHub App authentication, webhook handling, check runs,
and deployment tracking for the TINAA managed service platform.
"""

from tinaa.github.app import TINAAGitHubApp
from tinaa.github.checks import ChecksManager
from tinaa.github.client import GitHubClient
from tinaa.github.deployments import DeploymentTracker
from tinaa.github.webhooks import WebhookHandler

__all__ = [
    "TINAAGitHubApp",
    "ChecksManager",
    "GitHubClient",
    "DeploymentTracker",
    "WebhookHandler",
]
