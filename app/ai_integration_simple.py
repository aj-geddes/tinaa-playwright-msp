#!/usr/bin/env python3
"""
TINAA AI Integration Module (Simplified)

Provides AI-powered features using Anthropic Claude API.
"""

import logging
import os
from typing import Optional, Any

try:
    import anthropic

    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

logger = logging.getLogger("tinaa.ai_integration")


class AIManager:
    """Simplified AI Manager for TINAA"""

    def __init__(self):
        self.providers = {}
        self.active_provider = None
        self.initialized = False

    async def initialize_from_secrets(self):
        """Initialize AI providers from environment variables"""
        # Check for Anthropic credentials
        api_key = os.getenv("TINAA_ANTHROPIC_API_KEY")
        base_url = os.getenv("TINAA_ANTHROPIC_BASE_URL", "https://api.anthropic.com")
        model = os.getenv("TINAA_ANTHROPIC_DEFAULT_MODEL", "claude-3-5-sonnet-20241022")

        if api_key and ANTHROPIC_AVAILABLE:
            try:
                self.providers["anthropic"] = {
                    "client": anthropic.Anthropic(api_key=api_key, base_url=base_url),
                    "model": model,
                    "type": "anthropic",
                }
                self.active_provider = "anthropic"
                logger.info("Anthropic provider initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Anthropic provider: {e}")

        # Check for OpenAI credentials (for future use)
        openai_key = os.getenv("TINAA_OPENAI_API_KEY")
        if openai_key:
            logger.info(
                "OpenAI credentials found but provider not implemented in simplified version"
            )

        self.initialized = True
        return self.active_provider is not None

    async def chat_completion(
        self,
        prompt: str,
        system_prompt: Optional[str ] = None,
        max_tokens: int = 4000,
        temperature: float = 0.7,
    ) -> Optional[str ]:
        """Generate a chat completion using the active provider"""

        if not self.active_provider:
            logger.error("No active AI provider available")
            return None

        provider = self.providers[self.active_provider]

        try:
            if provider["type"] == "anthropic":
                # Prepare messages
                messages = []
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})
                messages.append({"role": "user", "content": prompt})

                # Create completion using Anthropic API
                response = provider["client"].messages.create(
                    model=provider["model"],
                    max_tokens=max_tokens,
                    temperature=temperature,
                    messages=messages,
                )

                # Extract the response text
                if response.content:
                    return response.content[0].text
                return None

        except Exception as e:
            logger.error(
                f"Error generating completion with {self.active_provider}: {e}"
            )
            return None

    def get_active_provider_info(self) -> dict[str, Any]:
        """Get information about the active provider"""
        if not self.active_provider:
            return {"active": False}

        provider = self.providers[self.active_provider]
        return {
            "active": True,
            "provider": self.active_provider,
            "model": provider.get("model", "unknown"),
            "type": provider["type"],
        }


# Global AI manager instance
_ai_manager = None


async def get_ai_manager() -> AIManager:
    """Get or create the global AI manager instance"""
    global _ai_manager
    if _ai_manager is None:
        _ai_manager = AIManager()
        await _ai_manager.initialize_from_secrets()
    return _ai_manager
