#!/usr/bin/env python3
"""
TINAA Settings API

Secure API endpoints for managing user credentials and configuration.
Handles Kubernetes secret creation and validation.
"""

import json
import logging
import base64
from typing import Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel, Field
from app.secrets_manager import SecretsManager
from app.ai_integration import AIManager
from app.git_auth import GitAuthenticator
import asyncio

logger = logging.getLogger("tinaa.settings_api")

# Initialize router
router = APIRouter(prefix="/api/v1/settings", tags=["settings"])

# Initialize managers
secrets_manager = SecretsManager()
ai_manager = AIManager()
git_authenticator = GitAuthenticator()

class AIProviderConfig(BaseModel):
    enabled: bool = False
    apiKey: Optional[str] = None
    baseUrl: Optional[str] = None
    defaultModel: Optional[str] = None

class GitPATConfig(BaseModel):
    enabled: bool = False
    token: Optional[str] = None
    username: str = "git"

class GitHubAppConfig(BaseModel):
    enabled: bool = False
    appId: Optional[str] = None
    installationId: Optional[str] = None
    privateKey: Optional[str] = None

class GitConfig(BaseModel):
    pat: Optional[GitPATConfig] = None
    githubApp: Optional[GitHubAppConfig] = None

class CredentialConfig(BaseModel):
    openai: Optional[AIProviderConfig] = None
    anthropic: Optional[AIProviderConfig] = None
    ollama: Optional[AIProviderConfig] = None
    git: Optional[GitConfig] = None

class TestCredentialRequest(BaseModel):
    provider: str
    credType: Optional[str] = None
    config: Dict[str, Any]

@router.get("/credentials")
async def get_current_credentials() -> Dict[str, Any]:
    """
    Get current credential configuration (without sensitive values).
    
    Returns the current configuration with API keys and tokens masked
    for security. Shows which providers are enabled and configured.
    """
    try:
        # Get current configuration from secrets
        config = {
            "openai": {
                "enabled": await secrets_manager.has_secret("tinaa-openai-secret", "api_key"),
                "baseUrl": await secrets_manager.get_secret("tinaa-openai-secret", "base_url") or "https://api.openai.com/v1",
                "defaultModel": await secrets_manager.get_secret("tinaa-openai-secret", "default_model") or "gpt-4",
                "apiKey": "••••••••" if await secrets_manager.has_secret("tinaa-openai-secret", "api_key") else ""
            },
            "anthropic": {
                "enabled": await secrets_manager.has_secret("tinaa-anthropic-secret", "api_key"),
                "baseUrl": await secrets_manager.get_secret("tinaa-anthropic-secret", "base_url") or "https://api.anthropic.com",
                "defaultModel": await secrets_manager.get_secret("tinaa-anthropic-secret", "default_model") or "claude-3-sonnet-20240229",
                "apiKey": "••••••••" if await secrets_manager.has_secret("tinaa-anthropic-secret", "api_key") else ""
            },
            "ollama": {
                "enabled": await secrets_manager.has_secret("tinaa-ollama-secret", "base_url"),
                "baseUrl": await secrets_manager.get_secret("tinaa-ollama-secret", "base_url") or "http://ollama:11434",
                "defaultModel": await secrets_manager.get_secret("tinaa-ollama-secret", "default_model") or "llama2"
            },
            "git": {
                "pat": {
                    "enabled": await secrets_manager.has_secret("tinaa-git-pat-secret", "token"),
                    "username": await secrets_manager.get_secret("tinaa-git-pat-secret", "username") or "git",
                    "token": "••••••••" if await secrets_manager.has_secret("tinaa-git-pat-secret", "token") else ""
                },
                "githubApp": {
                    "enabled": await secrets_manager.has_secret("tinaa-git-app-secret", "app_id"),
                    "appId": await secrets_manager.get_secret("tinaa-git-app-secret", "app_id") or "",
                    "installationId": await secrets_manager.get_secret("tinaa-git-app-secret", "installation_id") or "",
                    "privateKey": "••••••••" if await secrets_manager.has_secret("tinaa-git-app-secret", "private_key") else ""
                }
            }
        }
        
        return config
        
    except Exception as e:
        logger.error(f"Error loading credentials config: {e}")
        raise HTTPException(status_code=500, detail="Failed to load credentials configuration")

@router.post("/credentials")
async def save_credentials(config: CredentialConfig) -> Dict[str, Any]:
    """
    Save credential configuration to Kubernetes secrets.
    
    Securely stores all provided credentials as encrypted Kubernetes secrets
    in the current namespace. Each provider gets its own secret for isolation.
    """
    try:
        saved_secrets = []
        
        # Save OpenAI credentials
        if config.openai and config.openai.enabled and config.openai.apiKey:
            await secrets_manager.create_or_update_secret(
                "tinaa-openai-secret",
                {
                    "api_key": config.openai.apiKey,
                    "base_url": config.openai.baseUrl or "https://api.openai.com/v1",
                    "default_model": config.openai.defaultModel or "gpt-4"
                }
            )
            saved_secrets.append("OpenAI")
            logger.info("OpenAI credentials saved to Kubernetes secret")
        
        # Save Anthropic credentials
        if config.anthropic and config.anthropic.enabled and config.anthropic.apiKey:
            await secrets_manager.create_or_update_secret(
                "tinaa-anthropic-secret",
                {
                    "api_key": config.anthropic.apiKey,
                    "base_url": config.anthropic.baseUrl or "https://api.anthropic.com",
                    "default_model": config.anthropic.defaultModel or "claude-3-sonnet-20240229"
                }
            )
            saved_secrets.append("Anthropic")
            logger.info("Anthropic credentials saved to Kubernetes secret")
        
        # Save Ollama configuration
        if config.ollama and config.ollama.enabled and config.ollama.baseUrl:
            await secrets_manager.create_or_update_secret(
                "tinaa-ollama-secret",
                {
                    "base_url": config.ollama.baseUrl,
                    "default_model": config.ollama.defaultModel or "llama2"
                }
            )
            saved_secrets.append("Ollama")
            logger.info("Ollama configuration saved to Kubernetes secret")
        
        # Save Git PAT credentials
        if config.git and config.git.pat and config.git.pat.enabled and config.git.pat.token:
            await secrets_manager.create_or_update_secret(
                "tinaa-git-pat-secret",
                {
                    "token": config.git.pat.token,
                    "username": config.git.pat.username or "git"
                }
            )
            saved_secrets.append("Git PAT")
            logger.info("Git PAT credentials saved to Kubernetes secret")
        
        # Save GitHub App credentials
        if (config.git and config.git.githubApp and config.git.githubApp.enabled and 
            config.git.githubApp.appId and config.git.githubApp.privateKey):
            await secrets_manager.create_or_update_secret(
                "tinaa-git-app-secret",
                {
                    "app_id": config.git.githubApp.appId,
                    "installation_id": config.git.githubApp.installationId or "",
                    "private_key": config.git.githubApp.privateKey
                }
            )
            saved_secrets.append("GitHub App")
            logger.info("GitHub App credentials saved to Kubernetes secret")
        
        # Reinitialize managers to pick up new credentials
        await ai_manager.initialize_from_secrets()
        await git_authenticator.initialize_from_secrets()
        
        return {
            "success": True,
            "message": f"Credentials saved successfully for: {', '.join(saved_secrets)}",
            "saved_providers": saved_secrets
        }
        
    except Exception as e:
        logger.error(f"Error saving credentials: {e}")
        raise HTTPException(status_code=500, detail=f"Failed to save credentials: {str(e)}")

@router.post("/test-credential")
async def test_credential(request: TestCredentialRequest) -> Dict[str, Any]:
    """
    Test a credential configuration before saving.
    
    Validates that the provided credentials work correctly by attempting
    to connect to the respective service. Does not save the credentials.
    """
    try:
        provider = request.provider
        cred_type = request.credType
        config_data = request.config
        
        if provider == "openai":
            return await _test_openai_credentials(config_data)
        elif provider == "anthropic":
            return await _test_anthropic_credentials(config_data)
        elif provider == "ollama":
            return await _test_ollama_credentials(config_data)
        elif provider == "git":
            if cred_type == "pat":
                return await _test_git_pat_credentials(config_data.get("pat", {}))
            elif cred_type == "githubApp":
                return await _test_github_app_credentials(config_data.get("githubApp", {}))
        
        raise HTTPException(status_code=400, detail=f"Unknown provider: {provider}")
        
    except Exception as e:
        logger.error(f"Error testing credential for {provider}: {e}")
        return {
            "success": False,
            "message": f"Failed to test credential: {str(e)}"
        }

async def _test_openai_credentials(config: Dict[str, Any]) -> Dict[str, Any]:
    """Test OpenAI API credentials"""
    try:
        api_key = config.get("apiKey")
        base_url = config.get("baseUrl", "https://api.openai.com/v1")
        
        if not api_key:
            return {"success": False, "message": "API key is required"}
        
        # Create temporary AI manager for testing
        from ai_integration import OpenAIProvider
        provider = OpenAIProvider(api_key=api_key, base_url=base_url)
        
        # Test with a simple completion
        result = await provider.chat_completion("Hello, respond with just 'OK' to confirm connection.")
        
        if result and "OK" in result.upper():
            return {"success": True, "message": "OpenAI connection successful"}
        else:
            return {"success": False, "message": "OpenAI API responded but with unexpected result"}
            
    except Exception as e:
        return {"success": False, "message": f"OpenAI connection failed: {str(e)}"}

async def _test_anthropic_credentials(config: Dict[str, Any]) -> Dict[str, Any]:
    """Test Anthropic API credentials"""
    try:
        api_key = config.get("apiKey")
        base_url = config.get("baseUrl", "https://api.anthropic.com")
        
        if not api_key:
            return {"success": False, "message": "API key is required"}
        
        # Create temporary AI manager for testing
        from ai_integration import AnthropicProvider
        provider = AnthropicProvider(api_key=api_key, base_url=base_url)
        
        # Test with a simple completion
        result = await provider.chat_completion("Hello, respond with just 'OK' to confirm connection.")
        
        if result and "OK" in result.upper():
            return {"success": True, "message": "Anthropic connection successful"}
        else:
            return {"success": False, "message": "Anthropic API responded but with unexpected result"}
            
    except Exception as e:
        return {"success": False, "message": f"Anthropic connection failed: {str(e)}"}

async def _test_ollama_credentials(config: Dict[str, Any]) -> Dict[str, Any]:
    """Test Ollama connection"""
    try:
        base_url = config.get("baseUrl", "http://ollama:11434")
        
        if not base_url:
            return {"success": False, "message": "Base URL is required"}
        
        # Create temporary AI manager for testing
        from ai_integration import OllamaProvider
        provider = OllamaProvider(base_url=base_url)
        
        # Test connection by listing available models
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{base_url}/api/tags")
            if response.status_code == 200:
                models = response.json().get("models", [])
                return {
                    "success": True, 
                    "message": f"Ollama connection successful, {len(models)} models available"
                }
            else:
                return {"success": False, "message": f"Ollama returned status {response.status_code}"}
            
    except Exception as e:
        return {"success": False, "message": f"Ollama connection failed: {str(e)}"}

async def _test_git_pat_credentials(config: Dict[str, Any]) -> Dict[str, Any]:
    """Test Git PAT credentials"""
    try:
        token = config.get("token")
        username = config.get("username", "git")
        
        if not token:
            return {"success": False, "message": "Token is required"}
        
        # Test by accessing GitHub API
        import httpx
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "TINAA-Testing"
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get("https://api.github.com/user", headers=headers)
            
            if response.status_code == 200:
                user_data = response.json()
                return {
                    "success": True, 
                    "message": f"GitHub PAT valid for user: {user_data.get('login', 'unknown')}"
                }
            elif response.status_code == 401:
                return {"success": False, "message": "Invalid GitHub PAT token"}
            else:
                return {"success": False, "message": f"GitHub API returned status {response.status_code}"}
            
    except Exception as e:
        return {"success": False, "message": f"GitHub PAT test failed: {str(e)}"}

async def _test_github_app_credentials(config: Dict[str, Any]) -> Dict[str, Any]:
    """Test GitHub App credentials"""
    try:
        app_id = config.get("appId")
        installation_id = config.get("installationId")
        private_key = config.get("privateKey")
        
        if not all([app_id, installation_id, private_key]):
            return {"success": False, "message": "App ID, Installation ID, and Private Key are required"}
        
        # Create temporary authenticator for testing
        test_auth = GitAuthenticator()
        
        # Test by getting an installation access token
        result = await test_auth._get_github_app_token(
            app_id=app_id,
            installation_id=installation_id,
            private_key=private_key
        )
        
        if result.get("success"):
            return {"success": True, "message": "GitHub App credentials valid"}
        else:
            return {"success": False, "message": result.get("error", "GitHub App authentication failed")}
            
    except Exception as e:
        return {"success": False, "message": f"GitHub App test failed: {str(e)}"}

@router.get("/provider-status")
async def get_provider_status() -> Dict[str, Any]:
    """
    Get the current status of all configured providers.
    
    Returns the connection status and availability of each configured
    AI provider and Git authentication method.
    """
    try:
        status = {
            "ai_providers": {},
            "git_auth": {},
            "last_checked": None
        }
        
        # Check AI provider status
        await ai_manager.initialize_from_secrets()
        
        if ai_manager.providers.get("openai"):
            status["ai_providers"]["openai"] = {
                "configured": True,
                "active": ai_manager.active_provider == "openai",
                "model": ai_manager.providers["openai"].default_model
            }
        
        if ai_manager.providers.get("anthropic"):
            status["ai_providers"]["anthropic"] = {
                "configured": True,
                "active": ai_manager.active_provider == "anthropic",
                "model": ai_manager.providers["anthropic"].default_model
            }
        
        if ai_manager.providers.get("ollama"):
            status["ai_providers"]["ollama"] = {
                "configured": True,
                "active": ai_manager.active_provider == "ollama",
                "model": ai_manager.providers["ollama"].default_model
            }
        
        # Check Git authentication status
        git_status = await git_authenticator.validate_git_credentials()
        status["git_auth"] = git_status
        
        import datetime
        status["last_checked"] = datetime.datetime.now().isoformat()
        
        return status
        
    except Exception as e:
        logger.error(f"Error getting provider status: {e}")
        raise HTTPException(status_code=500, detail="Failed to get provider status")

# Add the router to the main app
def setup_settings_api(app):
    """Setup settings API routes in the main FastAPI app"""
    app.include_router(router)
    logger.info("Settings API routes registered successfully")