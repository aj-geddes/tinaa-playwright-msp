#!/usr/bin/env python3
"""
TINAA AI Integration Module

Provides AI-powered features including:
- LLM integration for test generation and analysis
- AI provider management (OpenAI, Anthropic, Ollama)
- Intelligent playbook generation
- Project troubleshooting assistance
- Test optimization recommendations
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Any

import aiofiles

# AI Provider imports
try:
    import openai

    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

try:
    import anthropic

    ANTHROPIC_AVAILABLE = True
except ImportError:
    ANTHROPIC_AVAILABLE = False

logger = logging.getLogger("tinaa.ai_integration")


class AIProvider:
    """Base class for AI providers"""

    def __init__(self, provider_type: str, config: dict[str, Any]):
        self.provider_type = provider_type
        self.config = config
        self.client = None

    async def initialize(self):
        """Initialize the AI provider client"""
        raise NotImplementedError

    async def generate_completion(
        self, prompt: str, max_tokens: int = 1000, temperature: float = 0.1
    ) -> str:
        """Generate a text completion"""
        raise NotImplementedError

    async def analyze_code(self, code: str, context: str = "") -> dict[str, Any]:
        """Analyze code and provide insights"""
        raise NotImplementedError


class OpenAIProvider(AIProvider):
    """OpenAI integration"""

    def __init__(self, config: dict[str, Any]):
        super().__init__("openai", config)

    async def initialize(self):
        """Initialize OpenAI client"""
        if not OPENAI_AVAILABLE:
            raise Exception("OpenAI library not available")

        api_key = self.config.get("api_key")
        if not api_key:
            raise Exception("OpenAI API key not configured")

        self.client = openai.AsyncOpenAI(
            api_key=api_key,
            base_url=self.config.get("base_url", "https://api.openai.com/v1"),
        )

        logger.info("OpenAI provider initialized")

    async def generate_completion(
        self, prompt: str, max_tokens: int = 1000, temperature: float = 0.1
    ) -> str:
        """Generate completion using OpenAI"""
        try:
            response = await self.client.chat.completions.create(
                model=self.config.get("default_model", "gpt-4"),
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature,
            )

            return response.choices[0].message.content

        except Exception as e:
            logger.error(f"OpenAI completion failed: {e!s}")
            raise

    async def analyze_code(self, code: str, context: str = "") -> dict[str, Any]:
        """Analyze code using OpenAI"""
        prompt = f"""
        Analyze the following Playwright test code and provide insights:
        
        Context: {context}
        
        Code:
        ```typescript
        {code}
        ```
        
        Please provide:
        1. Code quality assessment
        2. Potential improvements
        3. Best practices recommendations
        4. Security considerations
        5. Performance optimizations
        
        Response format: JSON
        """

        response = await self.generate_completion(prompt, max_tokens=2000)

        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return {"analysis": response, "format": "text"}


class AnthropicProvider(AIProvider):
    """Anthropic Claude integration"""

    def __init__(self, config: dict[str, Any]):
        super().__init__("anthropic", config)

    async def initialize(self):
        """Initialize Anthropic client"""
        if not ANTHROPIC_AVAILABLE:
            raise Exception("Anthropic library not available")

        api_key = self.config.get("api_key")
        if not api_key:
            raise Exception("Anthropic API key not configured")

        self.client = anthropic.AsyncAnthropic(
            api_key=api_key, base_url=self.config.get("base_url")
        )

        logger.info("Anthropic provider initialized")

    async def generate_completion(
        self, prompt: str, max_tokens: int = 1000, temperature: float = 0.1
    ) -> str:
        """Generate completion using Anthropic Claude"""
        try:
            response = await self.client.messages.create(
                model=self.config.get("default_model", "claude-3-sonnet-20240229"),
                max_tokens=max_tokens,
                temperature=temperature,
                messages=[{"role": "user", "content": prompt}],
            )

            return response.content[0].text

        except Exception as e:
            logger.error(f"Anthropic completion failed: {e!s}")
            raise

    async def analyze_code(self, code: str, context: str = "") -> dict[str, Any]:
        """Analyze code using Anthropic Claude"""
        prompt = f"""
        As an expert in Playwright testing, analyze this code:
        
        Context: {context}
        
        Code:
        ```typescript
        {code}
        ```
        
        Provide a structured analysis including:
        - Code quality score (1-10)
        - Identified issues and their severity
        - Improvement suggestions
        - Best practices compliance
        - Maintainability assessment
        
        Format your response as valid JSON.
        """

        response = await self.generate_completion(prompt, max_tokens=2000)

        try:
            return json.loads(response)
        except json.JSONDecodeError:
            return {"analysis": response, "format": "text"}


class OllamaProvider(AIProvider):
    """Ollama local LLM integration"""

    def __init__(self, config: dict[str, Any]):
        super().__init__("ollama", config)

    async def initialize(self):
        """Initialize Ollama client"""
        # For Ollama, we'll use HTTP requests
        import aiohttp

        self.client = aiohttp.ClientSession()
        self.base_url = self.config.get("base_url", "http://localhost:11434")

        logger.info("Ollama provider initialized")

    async def generate_completion(
        self, prompt: str, max_tokens: int = 1000, temperature: float = 0.1
    ) -> str:
        """Generate completion using Ollama"""
        try:
            async with self.client.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.config.get("default_model", "codellama"),
                    "prompt": prompt,
                    "stream": False,
                    "options": {"num_predict": max_tokens, "temperature": temperature},
                },
            ) as response:
                result = await response.json()
                return result.get("response", "")

        except Exception as e:
            logger.error(f"Ollama completion failed: {e!s}")
            raise


class AIManager:
    """Central AI management system for TINAA"""

    def __init__(self, ai_cache_path: str = "/app/ai-cache"):
        self.ai_cache_path = Path(ai_cache_path)
        self.providers: dict[str, AIProvider] = {}
        self.active_provider: Optional[str ] = None

        # Try to create cache directory, ignore if permission denied
        try:
            self.ai_cache_path.mkdir(parents=True, exist_ok=True)
        except (PermissionError, OSError):
            # Fall back to temp directory if we can't create the requested path
            import tempfile
            self.ai_cache_path = Path(tempfile.gettempdir()) / "tinaa_ai_cache"
            try:
                self.ai_cache_path.mkdir(parents=True, exist_ok=True)
            except:
                pass  # Cache will be disabled

    async def initialize_from_secrets(self):
        """Initialize AI providers using secrets manager"""
        from app.secrets_manager import secrets_manager

        # Validate available secrets
        validation_results = await secrets_manager.validate_secrets()

        # Initialize OpenAI if available
        if validation_results.get("openai"):
            try:
                openai_config = await secrets_manager.get_ai_provider_config("openai")
                await self.add_provider("openai", "openai", openai_config)
                logger.info("Initialized OpenAI provider from secrets")
            except Exception as e:
                logger.warning(f"Failed to initialize OpenAI provider: {e}")

        # Initialize Anthropic if available
        if validation_results.get("anthropic"):
            try:
                anthropic_config = await secrets_manager.get_ai_provider_config(
                    "anthropic"
                )
                await self.add_provider("anthropic", "anthropic", anthropic_config)
                logger.info("Initialized Anthropic provider from secrets")
            except Exception as e:
                logger.warning(f"Failed to initialize Anthropic provider: {e}")

        # Initialize Ollama if available
        if validation_results.get("ollama"):
            try:
                ollama_config = await secrets_manager.get_ai_provider_config("ollama")
                await self.add_provider("ollama", "ollama", ollama_config)
                logger.info("Initialized Ollama provider from configuration")
            except Exception as e:
                logger.warning(f"Failed to initialize Ollama provider: {e}")

        if not self.providers:
            logger.warning("No AI providers could be initialized")

    async def add_provider(self, name: str, provider_type: str, config: dict[str, Any]):
        """Add and initialize an AI provider"""
        try:
            if provider_type == "openai":
                provider = OpenAIProvider(config)
            elif provider_type == "anthropic":
                provider = AnthropicProvider(config)
            elif provider_type == "ollama":
                provider = OllamaProvider(config)
            else:
                raise ValueError(f"Unsupported provider type: {provider_type}")

            await provider.initialize()
            self.providers[name] = provider

            # Set as active if it's the first provider
            if not self.active_provider:
                self.active_provider = name

            logger.info(f"Added AI provider: {name} ({provider_type})")

        except Exception as e:
            logger.error(f"Failed to add provider {name}: {e!s}")
            raise

    def set_active_provider(self, name: str):
        """Set the active AI provider"""
        if name not in self.providers:
            raise ValueError(f"Provider {name} not found")
        self.active_provider = name
        logger.info(f"Active AI provider set to: {name}")

    async def generate_playbook(
        self, project_context: dict[str, Any], requirements: str = ""
    ) -> dict[str, Any]:
        """Generate a test playbook using AI"""
        if not self.active_provider:
            raise Exception("No active AI provider configured")

        provider = self.providers[self.active_provider]

        prompt = f"""
        Generate a comprehensive Playwright test playbook for the following project:
        
        Project Context:
        {json.dumps(project_context, indent=2)}
        
        Additional Requirements:
        {requirements}
        
        Create a detailed test playbook that includes:
        1. Project setup and initialization steps
        2. Core functionality testing scenarios
        3. Edge cases and error handling
        4. Performance and accessibility checks
        5. Cross-browser compatibility tests
        
        Format the response as a valid JSON playbook with the following structure:
        {{
            "name": "Generated Test Playbook",
            "description": "AI-generated comprehensive test suite",
            "steps": [
                {{
                    "id": "step-1",
                    "action": "navigate",
                    "parameters": {{"url": "..."}},
                    "description": "...",
                    "expected_outcome": "..."
                }}
            ],
            "metadata": {{
                "estimated_duration": "...",
                "complexity": "...",
                "prerequisites": [...]
            }}
        }}
        """

        try:
            response = await provider.generate_completion(prompt, max_tokens=3000)
            playbook = json.loads(response)

            # Cache the generated playbook
            await self._cache_playbook(playbook, project_context.get("id"))

            return playbook

        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse AI-generated playbook: {e!s}")
            raise Exception("AI generated invalid playbook format")
        except Exception as e:
            logger.error(f"Playbook generation failed: {e!s}")
            raise

    async def troubleshoot_project(
        self, project_id: str, error_logs: list[str], test_results: dict[str, Any]
    ) -> dict[str, Any]:
        """Analyze project issues and provide troubleshooting guidance"""
        if not self.active_provider:
            raise Exception("No active AI provider configured")

        provider = self.providers[self.active_provider]

        prompt = f"""
        Analyze the following Playwright test project issues and provide troubleshooting guidance:
        
        Project ID: {project_id}
        
        Error Logs:
        {json.dumps(error_logs, indent=2)}
        
        Test Results:
        {json.dumps(test_results, indent=2)}
        
        Please provide:
        1. Root cause analysis of the issues
        2. Step-by-step troubleshooting guide
        3. Recommended fixes and improvements
        4. Prevention strategies for future issues
        5. Performance optimization suggestions
        
        Format response as JSON with structured troubleshooting data.
        """

        try:
            response = await provider.generate_completion(prompt, max_tokens=2500)

            troubleshooting_data = json.loads(response)

            # Cache troubleshooting results
            await self._cache_troubleshooting(project_id, troubleshooting_data)

            return troubleshooting_data

        except json.JSONDecodeError:
            return {"analysis": response, "format": "text"}
        except Exception as e:
            logger.error(f"Troubleshooting analysis failed: {e!s}")
            raise

    async def optimize_tests(
        self, project_id: str, test_files: list[dict[str, str]]
    ) -> dict[str, Any]:
        """Analyze test files and provide optimization recommendations"""
        if not self.active_provider:
            raise Exception("No active AI provider configured")

        provider = self.providers[self.active_provider]

        # Analyze each test file
        optimizations = []

        for test_file in test_files[:5]:  # Limit to 5 files for token efficiency
            file_analysis = await provider.analyze_code(
                test_file.get("content", ""),
                f"Playwright test file: {test_file.get('name', 'unknown')}",
            )

            optimizations.append(
                {"file": test_file.get("name"), "analysis": file_analysis}
            )

        # Generate overall optimization recommendations
        optimization_prompt = f"""
        Based on the analysis of Playwright test files, provide comprehensive optimization recommendations:
        
        File Analyses:
        {json.dumps(optimizations, indent=2)}
        
        Provide:
        1. Overall test suite optimization strategy
        2. Performance improvement recommendations
        3. Code quality enhancement suggestions
        4. Maintainability improvements
        5. Best practices implementation guide
        
        Format as structured JSON.
        """

        overall_recommendations = await provider.generate_completion(
            optimization_prompt, max_tokens=2000
        )

        result = {
            "project_id": project_id,
            "file_optimizations": optimizations,
            "overall_recommendations": overall_recommendations,
            "generated_at": datetime.now().isoformat(),
        }

        # Cache optimization results
        await self._cache_optimization(project_id, result)

        return result

    async def chat_completion(
        self, message: str, context: Optional[dict[str, Any] ] = None
    ) -> str:
        """Handle chat-style interactions with AI"""
        if not self.active_provider:
            raise Exception("No active AI provider configured")

        provider = self.providers[self.active_provider]

        # Build context-aware prompt
        system_context = """
        You are TINAA AI Assistant, an expert in Playwright testing and web automation.
        You help users create, optimize, and troubleshoot their testing projects.
        
        Provide clear, actionable advice focused on:
        - Playwright best practices
        - Test automation strategies
        - Debugging and troubleshooting
        - Performance optimization
        - Code quality improvement
        """

        if context:
            context_info = f"\nCurrent Context:\n{json.dumps(context, indent=2)}\n"
        else:
            context_info = ""

        full_prompt = f"{system_context}{context_info}\nUser Question: {message}"

        return await provider.generate_completion(full_prompt, max_tokens=1500)

    async def _cache_playbook(
        self, playbook: dict[str, Any], project_id: Optional[str ]
    ):
        """Cache generated playbook"""
        cache_file = (
            self.ai_cache_path
            / f"playbook_{project_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        async with aiofiles.open(cache_file, "w") as f:
            await f.write(json.dumps(playbook, indent=2))

    async def _cache_troubleshooting(self, project_id: str, data: dict[str, Any]):
        """Cache troubleshooting results"""
        cache_file = (
            self.ai_cache_path
            / f"troubleshooting_{project_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        async with aiofiles.open(cache_file, "w") as f:
            await f.write(json.dumps(data, indent=2))

    async def _cache_optimization(self, project_id: str, data: dict[str, Any]):
        """Cache optimization results"""
        cache_file = (
            self.ai_cache_path
            / f"optimization_{project_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
        async with aiofiles.open(cache_file, "w") as f:
            await f.write(json.dumps(data, indent=2))

    def get_provider_status(self) -> dict[str, Any]:
        """Get status of all AI providers"""
        return {
            "providers": {
                name: {
                    "type": provider.provider_type,
                    "active": name == self.active_provider,
                    "config": {
                        k: "***" if "key" in k.lower() else v
                        for k, v in provider.config.items()
                    },
                }
                for name, provider in self.providers.items()
            },
            "active_provider": self.active_provider,
            "cache_path": str(self.ai_cache_path),
        }
