#!/usr/bin/env python3
"""
TINAA Secrets Manager

Handles secure retrieval of API keys and sensitive configuration from:
- Kubernetes secrets
- Environment variables
- Local configuration files (for development)
"""

import base64
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger("tinaa.secrets_manager")


class SecretsManager:
    """Secure secrets management for TINAA"""

    def __init__(self):
        self.is_kubernetes = self._detect_kubernetes_environment()
        self.secrets_cache: dict[str, str] = {}

    def _detect_kubernetes_environment(self) -> bool:
        """Detect if running in Kubernetes environment"""
        return (
            os.path.exists("/var/run/secrets/kubernetes.io/serviceaccount")
            or os.getenv("KUBERNETES_SERVICE_HOST") is not None
        )

    async def get_secret(self, secret_name: str, key: str) -> str | None:
        """
        Get a secret value by name and key

        Args:
            secret_name: Name of the secret (e.g., 'tinaa-openai-secret')
            key: Key within the secret (e.g., 'api-key')

        Returns:
            Secret value or None if not found
        """
        cache_key = f"{secret_name}:{key}"

        # Check cache first
        if cache_key in self.secrets_cache:
            return self.secrets_cache[cache_key]

        secret_value = None

        if self.is_kubernetes:
            secret_value = await self._get_kubernetes_secret(secret_name, key)

        # Fallback to environment variables
        if not secret_value:
            secret_value = self._get_environment_secret(secret_name, key)

        # Cache the secret (in memory only)
        if secret_value:
            self.secrets_cache[cache_key] = secret_value
            logger.info(f"Successfully retrieved secret: {secret_name}:{key}")
        else:
            logger.warning(f"Secret not found: {secret_name}:{key}")

        return secret_value

    async def _get_kubernetes_secret(self, secret_name: str, key: str) -> str | None:
        """Get secret from Kubernetes secrets"""
        try:
            # Kubernetes mounts secrets as files in /var/run/secrets/
            secret_path = Path(f"/var/run/secrets/{secret_name}/{key}")

            if secret_path.exists():
                with open(secret_path) as f:
                    return f.read().strip()

            # Alternative: try mounted secrets in common locations
            alt_paths = [
                Path(f"/etc/secrets/{secret_name}/{key}"),
                Path(f"/secrets/{secret_name}/{key}"),
                Path(f"/var/secrets/{secret_name}/{key}"),
            ]

            for alt_path in alt_paths:
                if alt_path.exists():
                    with open(alt_path) as f:
                        return f.read().strip()

            # If direct file access fails, try kubectl approach (requires service account)
            return await self._get_secret_via_kubernetes_api(secret_name, key)

        except Exception as e:
            logger.error(f"Failed to get Kubernetes secret {secret_name}:{key}: {e!s}")
            return None

    async def _get_secret_via_kubernetes_api(
        self, secret_name: str, key: str
    ) -> str | None:
        """Get secret via Kubernetes API (requires appropriate RBAC)"""
        try:

            import aiohttp

            # Read service account token
            token_path = "/var/run/secrets/kubernetes.io/serviceaccount/token"
            if not os.path.exists(token_path):
                return None

            with open(token_path) as f:
                token = f.read().strip()

            # Get namespace
            namespace_path = "/var/run/secrets/kubernetes.io/serviceaccount/namespace"
            if os.path.exists(namespace_path):
                with open(namespace_path) as f:
                    namespace = f.read().strip()
            else:
                namespace = os.getenv("KUBERNETES_NAMESPACE", "default")

            # Kubernetes API server
            k8s_host = os.getenv("KUBERNETES_SERVICE_HOST")
            k8s_port = os.getenv("KUBERNETES_SERVICE_PORT", "443")

            if not k8s_host:
                return None

            # Make API request
            api_url = f"https://{k8s_host}:{k8s_port}/api/v1/namespaces/{namespace}/secrets/{secret_name}"

            headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}

            async with aiohttp.ClientSession() as session:
                async with session.get(api_url, headers=headers, ssl=False) as response:
                    if response.status == 200:
                        secret_data = await response.json()

                        # Kubernetes secrets are base64 encoded
                        encoded_value = secret_data.get("data", {}).get(key)
                        if encoded_value:
                            return base64.b64decode(encoded_value).decode("utf-8")

        except Exception as e:
            logger.error(f"Failed to get secret via K8s API {secret_name}:{key}: {e!s}")

        return None

    def _get_environment_secret(self, secret_name: str, key: str) -> str | None:
        """Get secret from environment variables"""

        # Map secret names and keys to Vault environment variable patterns
        vault_mappings = {
            ("tinaa-anthropic-secret", "api-key"): "TINAA_ANTHROPIC_API_KEY",
            ("tinaa-anthropic-secret", "base-url"): "TINAA_ANTHROPIC_BASE_URL",
            (
                "tinaa-anthropic-secret",
                "default-model",
            ): "TINAA_ANTHROPIC_DEFAULT_MODEL",
            ("tinaa-openai-secret", "api-key"): "TINAA_OPENAI_API_KEY",
            ("tinaa-openai-secret", "base-url"): "TINAA_OPENAI_BASE_URL",
            ("tinaa-openai-secret", "default-model"): "TINAA_OPENAI_DEFAULT_MODEL",
            ("tinaa-git-pat-secret", "token"): "TINAA_GIT_PAT",
            ("tinaa-git-pat-secret", "username"): "TINAA_GIT_USERNAME",
            ("tinaa-git-app-secret", "app-id"): "TINAA_GIT_APP_ID",
            (
                "tinaa-git-app-secret",
                "installation-id",
            ): "TINAA_GIT_APP_INSTALLATION_ID",
            ("tinaa-git-app-secret", "private-key"): "TINAA_GIT_APP_PRIVATE_KEY",
        }

        # Check Vault-style environment variable first
        vault_env = vault_mappings.get((secret_name, key))
        if vault_env:
            value = os.getenv(vault_env)
            if value:
                logger.info(f"Found secret in Vault environment: {vault_env}")
                return value

        # Try other environment variable naming conventions as fallback
        env_names = [
            f"{secret_name.upper().replace('-', '_')}_{key.upper().replace('-', '_')}",
            f"{secret_name.upper()}_{key.upper()}",
            f"TINAA_{secret_name.upper().replace('-', '_')}_{key.upper().replace('-', '_')}",
            f"TINAA_{key.upper().replace('-', '_')}",
            key.upper().replace("-", "_"),
        ]

        for env_name in env_names:
            value = os.getenv(env_name)
            if value:
                logger.info(f"Found secret in environment: {env_name}")
                return value

        return None

    async def get_ai_provider_config(self, provider_name: str) -> dict[str, Any]:
        """
        Get AI provider configuration with secrets

        Args:
            provider_name: Name of the AI provider (openai, anthropic, etc.)

        Returns:
            Configuration dictionary with API keys resolved
        """
        config = {}

        if provider_name == "openai":
            api_key = await self.get_secret("tinaa-openai-secret", "api-key")
            if not api_key:
                api_key = await self.get_secret("openai-secret", "api-key")

            if api_key:
                # Try to get additional config from secrets first
                base_url = await self.get_secret("tinaa-openai-secret", "base-url")
                default_model = await self.get_secret(
                    "tinaa-openai-secret", "default-model"
                )

                config = {
                    "api_key": api_key,
                    "base_url": base_url
                    or os.getenv("TINAA_OPENAI_BASE_URL")
                    or os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1"),
                    "default_model": default_model
                    or os.getenv("TINAA_OPENAI_DEFAULT_MODEL")
                    or os.getenv("OPENAI_DEFAULT_MODEL", "gpt-4"),
                    "max_tokens": int(
                        os.getenv("TINAA_OPENAI_MAX_TOKENS")
                        or os.getenv("OPENAI_MAX_TOKENS", "4096")
                    ),
                    "temperature": float(
                        os.getenv("TINAA_OPENAI_TEMPERATURE")
                        or os.getenv("OPENAI_TEMPERATURE", "0.1")
                    ),
                }

        elif provider_name == "anthropic":
            api_key = await self.get_secret("tinaa-anthropic-secret", "api-key")
            if not api_key:
                api_key = await self.get_secret("anthropic-secret", "api-key")

            if api_key:
                # Try to get additional config from secrets first
                base_url = await self.get_secret("tinaa-anthropic-secret", "base-url")
                default_model = await self.get_secret(
                    "tinaa-anthropic-secret", "default-model"
                )

                config = {
                    "api_key": api_key,
                    "base_url": base_url
                    or os.getenv("TINAA_ANTHROPIC_BASE_URL")
                    or os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com"),
                    "default_model": default_model
                    or os.getenv("TINAA_ANTHROPIC_DEFAULT_MODEL")
                    or os.getenv("ANTHROPIC_DEFAULT_MODEL", "claude-3-sonnet-20240229"),
                    "max_tokens": int(
                        os.getenv("TINAA_ANTHROPIC_MAX_TOKENS")
                        or os.getenv("ANTHROPIC_MAX_TOKENS", "4096")
                    ),
                    "temperature": float(
                        os.getenv("TINAA_ANTHROPIC_TEMPERATURE")
                        or os.getenv("ANTHROPIC_TEMPERATURE", "0.1")
                    ),
                }

        elif provider_name == "ollama":
            # Ollama typically doesn't need API keys
            config = {
                "base_url": os.getenv("OLLAMA_BASE_URL", "http://ollama:11434"),
                "default_model": os.getenv("OLLAMA_DEFAULT_MODEL", "codellama"),
            }

        return config

    async def validate_secrets(self) -> dict[str, bool]:
        """
        Validate that required secrets are available

        Returns:
            Dictionary of provider -> availability
        """
        validation_results = {}

        # Check OpenAI
        openai_config = await self.get_ai_provider_config("openai")
        validation_results["openai"] = bool(openai_config.get("api_key"))

        # Check Anthropic
        anthropic_config = await self.get_ai_provider_config("anthropic")
        validation_results["anthropic"] = bool(anthropic_config.get("api_key"))

        # Check Ollama (always available if configured)
        ollama_config = await self.get_ai_provider_config("ollama")
        validation_results["ollama"] = bool(ollama_config.get("base_url"))

        logger.info(f"Secret validation results: {validation_results}")
        return validation_results

    def get_database_config(self) -> dict[str, Any]:
        """Get database configuration from environment/secrets"""
        db_type = os.getenv("TINAA_DB_TYPE", "sqlite")

        if db_type == "sqlite":
            return {
                "type": "sqlite",
                "path": os.getenv(
                    "TINAA_DB_PATH",
                    os.path.join(tempfile.gettempdir(), "workspace", "tinaa.db"),
                ),
            }
        if db_type == "postgresql":
            return {
                "type": "postgresql",
                "host": os.getenv("POSTGRES_HOST", "localhost"),
                "port": int(os.getenv("POSTGRES_PORT", "5432")),
                "database": os.getenv("POSTGRES_DB", "tinaa"),
                "username": os.getenv("POSTGRES_USER", "tinaa"),
                "password": os.getenv("POSTGRES_PASSWORD", ""),
                "ssl_mode": os.getenv("POSTGRES_SSL_MODE", "prefer"),
            }

        import os
        import tempfile

        return {
            "type": "sqlite",
            "path": os.path.join(tempfile.gettempdir(), "tinaa.db"),
        }

    def clear_cache(self):
        """Clear the secrets cache (for security)"""
        self.secrets_cache.clear()
        logger.info("Secrets cache cleared")

    async def get_git_config(self, auth_type: str = "auto") -> dict[str, Any]:
        """
        Get git configuration with credentials

        Args:
            auth_type: Type of authentication ("pat", "github_app", "auto")

        Returns:
            Git configuration dictionary
        """
        config = {"auth_type": None, "credentials": {}}

        if auth_type == "auto":
            # Auto-detect available authentication method
            pat_config = await self._get_git_pat_config()
            if pat_config:
                config.update(pat_config)
                config["auth_type"] = "pat"
            else:
                github_app_config = await self._get_github_app_config()
                if github_app_config:
                    config.update(github_app_config)
                    config["auth_type"] = "github_app"
        elif auth_type == "pat":
            pat_config = await self._get_git_pat_config()
            if pat_config:
                config.update(pat_config)
                config["auth_type"] = "pat"
        elif auth_type == "github_app":
            github_app_config = await self._get_github_app_config()
            if github_app_config:
                config.update(github_app_config)
                config["auth_type"] = "github_app"

        return config

    async def _get_git_pat_config(self) -> dict[str, Any] | None:
        """Get Personal Access Token configuration"""
        # Try to get PAT from secrets
        pat_token = await self.get_secret("tinaa-git-secret", "pat-token")
        if not pat_token:
            pat_token = await self.get_secret("git-secret", "token")
        if not pat_token:
            pat_token = await self.get_secret("github-secret", "token")

        username = await self.get_secret("tinaa-git-secret", "username")
        if not username:
            username = os.getenv("GIT_USERNAME", "git")

        if pat_token:
            return {
                "credentials": {"username": username, "token": pat_token},
                "clone_url_format": "https://{username}:{token}@github.com/{repo}.git",
            }

        return None

    async def _get_github_app_config(self) -> dict[str, Any] | None:
        """Get GitHub App authentication configuration"""
        app_id = await self.get_secret("tinaa-github-app-secret", "app-id")
        private_key = await self.get_secret("tinaa-github-app-secret", "private-key")
        installation_id = await self.get_secret(
            "tinaa-github-app-secret", "installation-id"
        )

        # Fallback to alternative secret names
        if not app_id:
            app_id = await self.get_secret("github-app-secret", "app-id")
        if not private_key:
            private_key = await self.get_secret("github-app-secret", "private-key")
        if not installation_id:
            installation_id = await self.get_secret(
                "github-app-secret", "installation-id"
            )

        if app_id and private_key and installation_id:
            return {
                "credentials": {
                    "app_id": app_id,
                    "private_key": private_key,
                    "installation_id": installation_id,
                },
                "requires_token_generation": True,
            }

        return None

    async def has_secret(self, secret_name: str, key: str) -> bool:
        """
        Check if a secret exists without retrieving its value

        Args:
            secret_name: Name of the secret
            key: Key within the secret

        Returns:
            True if secret exists, False otherwise
        """
        secret_value = await self.get_secret(secret_name, key)
        return secret_value is not None

    async def create_or_update_secret(
        self, secret_name: str, data: dict[str, str]
    ) -> bool:
        """
        Create or update a Kubernetes secret

        Args:
            secret_name: Name of the secret to create/update
            data: Dictionary of key-value pairs to store

        Returns:
            True if successful, False otherwise
        """
        try:
            if self.is_kubernetes:
                return await self._create_kubernetes_secret(secret_name, data)
            # In non-Kubernetes environments, store as environment variables
            for key, value in data.items():
                env_name = f"{secret_name.upper().replace('-', '_')}_{key.upper().replace('-', '_')}"
                os.environ[env_name] = value
                logger.info(f"Set environment variable: {env_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to create/update secret {secret_name}: {e!s}")
            return False

    async def _create_kubernetes_secret(
        self, secret_name: str, data: dict[str, str]
    ) -> bool:
        """Create or update a Kubernetes secret via API"""
        try:
            import aiohttp

            # Read service account token
            token_path = "/var/run/secrets/kubernetes.io/serviceaccount/token"
            if not os.path.exists(token_path):
                logger.error("Service account token not found")
                return False

            with open(token_path) as f:
                token = f.read().strip()

            # Get namespace
            namespace_path = "/var/run/secrets/kubernetes.io/serviceaccount/namespace"
            if os.path.exists(namespace_path):
                with open(namespace_path) as f:
                    namespace = f.read().strip()
            else:
                namespace = os.getenv("KUBERNETES_NAMESPACE", "default")

            # Kubernetes API server
            k8s_host = os.getenv("KUBERNETES_SERVICE_HOST")
            k8s_port = os.getenv("KUBERNETES_SERVICE_PORT", "443")

            if not k8s_host:
                logger.error("Kubernetes API server not found")
                return False

            # Encode data for Kubernetes secret
            encoded_data = {}
            for key, value in data.items():
                # Replace underscores with hyphens for Kubernetes convention
                k8s_key = key.replace("_", "-")
                encoded_data[k8s_key] = base64.b64encode(value.encode("utf-8")).decode(
                    "utf-8"
                )

            # Create secret payload
            secret_payload = {
                "apiVersion": "v1",
                "kind": "Secret",
                "metadata": {
                    "name": secret_name,
                    "namespace": namespace,
                    "labels": {"app": "tinaa", "created-by": "tinaa-settings-api"},
                },
                "type": "Opaque",
                "data": encoded_data,
            }

            # API URL
            api_url = f"https://{k8s_host}:{k8s_port}/api/v1/namespaces/{namespace}/secrets/{secret_name}"

            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            }

            async with aiohttp.ClientSession() as session:
                # Try to update existing secret first
                async with session.put(
                    api_url, json=secret_payload, headers=headers, ssl=False
                ) as response:
                    if response.status in [200, 201]:
                        logger.info(
                            f"Successfully updated Kubernetes secret: {secret_name}"
                        )
                        # Clear cache for this secret
                        keys_to_remove = [
                            k
                            for k in self.secrets_cache.keys()
                            if k.startswith(f"{secret_name}:")
                        ]
                        for k in keys_to_remove:
                            del self.secrets_cache[k]
                        return True
                    if response.status == 404:
                        # Secret doesn't exist, create it
                        create_url = f"https://{k8s_host}:{k8s_port}/api/v1/namespaces/{namespace}/secrets"
                        async with session.post(
                            create_url, json=secret_payload, headers=headers, ssl=False
                        ) as create_response:
                            if create_response.status in [200, 201]:
                                logger.info(
                                    f"Successfully created Kubernetes secret: {secret_name}"
                                )
                                return True
                            error_text = await create_response.text()
                            logger.error(
                                f"Failed to create secret {secret_name}: {create_response.status} - {error_text}"
                            )
                            return False
                    else:
                        error_text = await response.text()
                        logger.error(
                            f"Failed to update secret {secret_name}: {response.status} - {error_text}"
                        )
                        return False

        except Exception as e:
            logger.error(f"Exception creating Kubernetes secret {secret_name}: {e!s}")
            return False

    async def validate_git_access(self) -> dict[str, Any]:
        """
        Validate git access with available credentials

        Returns:
            Validation results for different auth methods
        """
        validation_results = {
            "pat_available": False,
            "github_app_available": False,
            "recommended_auth": None,
        }

        # Check PAT availability
        pat_config = await self._get_git_pat_config()
        validation_results["pat_available"] = bool(pat_config)

        # Check GitHub App availability
        github_app_config = await self._get_github_app_config()
        validation_results["github_app_available"] = bool(github_app_config)

        # Determine recommended auth method
        if validation_results["github_app_available"]:
            validation_results["recommended_auth"] = "github_app"
        elif validation_results["pat_available"]:
            validation_results["recommended_auth"] = "pat"
        else:
            validation_results["recommended_auth"] = None

        logger.info(f"Git access validation: {validation_results}")
        return validation_results

    def get_environment_info(self) -> dict[str, Any]:
        """Get information about the current environment"""
        return {
            "is_kubernetes": self.is_kubernetes,
            "kubernetes_service_host": os.getenv("KUBERNETES_SERVICE_HOST"),
            "kubernetes_namespace": os.getenv("KUBERNETES_NAMESPACE"),
            "has_service_account": os.path.exists(
                "/var/run/secrets/kubernetes.io/serviceaccount/token"
            ),
            "environment_variables": {
                "TINAA_MODE": os.getenv("TINAA_MODE"),
                "WORKSPACE_PATH": os.getenv("WORKSPACE_PATH"),
                "AI_CACHE_PATH": os.getenv("AI_CACHE_PATH"),
                "TEMPLATES_PATH": os.getenv("TEMPLATES_PATH"),
                "GIT_USERNAME": os.getenv("GIT_USERNAME"),
            },
        }


# Global secrets manager instance
secrets_manager = SecretsManager()


# Convenience functions
async def get_openai_config() -> dict[str, Any]:
    """Get OpenAI configuration with API key"""
    return await secrets_manager.get_ai_provider_config("openai")


async def get_anthropic_config() -> dict[str, Any]:
    """Get Anthropic configuration with API key"""
    return await secrets_manager.get_ai_provider_config("anthropic")


async def get_ollama_config() -> dict[str, Any]:
    """Get Ollama configuration"""
    return await secrets_manager.get_ai_provider_config("ollama")
