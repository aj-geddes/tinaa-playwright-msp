#!/usr/bin/env python3
"""
Settings API for TINAA - Configuration and preferences management
"""
import json
import logging
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

logger = logging.getLogger("tinaa-settings")


class BrowserSettings(BaseModel):
    """Browser configuration settings."""
    headless: bool = Field(True, description="Run browser in headless mode")
    timeout: int = Field(30000, description="Default timeout in milliseconds")
    viewport_width: int = Field(1280, description="Default viewport width")
    viewport_height: int = Field(720, description="Default viewport height")
    user_agent: Optional[str] = Field(None, description="Custom user agent string")
    locale: str = Field("en-US", description="Browser locale")


class TestSettings(BaseModel):
    """Test execution settings."""
    screenshot_on_failure: bool = Field(True, description="Capture screenshots on test failures")
    video_recording: bool = Field(False, description="Record videos of test execution")
    retry_failures: bool = Field(True, description="Retry failed tests")
    max_retries: int = Field(2, description="Maximum number of retries")
    parallel_tests: int = Field(1, description="Number of parallel test executions")


class ReportSettings(BaseModel):
    """Test report settings."""
    format: str = Field("html", description="Report format (html, json, markdown)")
    include_screenshots: bool = Field(True, description="Include screenshots in reports")
    include_traces: bool = Field(False, description="Include execution traces")
    output_dir: str = Field("reports", description="Output directory for reports")


class Settings(BaseModel):
    """Complete TINAA settings."""
    browser: BrowserSettings = Field(default_factory=BrowserSettings)
    testing: TestSettings = Field(default_factory=TestSettings)
    reporting: ReportSettings = Field(default_factory=ReportSettings)


class SettingsManager:
    """Manages application settings persistence and retrieval."""

    def __init__(self, settings_file: Optional[str] = None):
        """
        Initialize settings manager.

        Args:
            settings_file: Path to settings JSON file. If None, uses default location.
        """
        if settings_file:
            self.settings_path = Path(settings_file)
        else:
            # Use default location in user's home directory
            config_dir = Path.home() / ".tinaa"
            config_dir.mkdir(exist_ok=True)
            self.settings_path = config_dir / "settings.json"

        self._settings: Optional[Settings] = None
        logger.info(f"Settings manager initialized: {self.settings_path}")

    def load(self) -> Settings:
        """
        Load settings from file.

        Returns:
            Settings object

        If settings file doesn't exist, returns default settings.
        """
        try:
            if self.settings_path.exists():
                with open(self.settings_path, "r") as f:
                    data = json.load(f)
                    self._settings = Settings(**data)
                    logger.info("Settings loaded from file")
            else:
                self._settings = Settings()
                logger.info("Using default settings (file not found)")

            return self._settings

        except Exception as e:
            logger.error(f"Failed to load settings: {e}", exc_info=True)
            # Return defaults on error
            return Settings()

    def save(self, settings: Settings) -> bool:
        """
        Save settings to file.

        Args:
            settings: Settings object to save

        Returns:
            True if saved successfully, False otherwise
        """
        try:
            # Ensure directory exists
            self.settings_path.parent.mkdir(parents=True, exist_ok=True)

            # Save to file
            with open(self.settings_path, "w") as f:
                json.dump(settings.model_dump(), f, indent=2)

            self._settings = settings
            logger.info("Settings saved to file")
            return True

        except Exception as e:
            logger.error(f"Failed to save settings: {e}", exc_info=True)
            return False

    def get(self) -> Settings:
        """
        Get current settings.

        Returns:
            Current Settings object. Loads from file if not already loaded.
        """
        if self._settings is None:
            return self.load()
        return self._settings

    def update(self, updates: dict[str, Any]) -> Settings:
        """
        Update specific settings values.

        Args:
            updates: Dictionary of setting paths and new values
                    e.g., {"browser.headless": False, "testing.max_retries": 3}

        Returns:
            Updated Settings object
        """
        current = self.get()
        current_dict = current.model_dump()

        # Apply updates
        for key, value in updates.items():
            keys = key.split(".")
            d = current_dict
            for k in keys[:-1]:
                d = d.setdefault(k, {})
            d[keys[-1]] = value

        # Create new settings object
        updated = Settings(**current_dict)
        self.save(updated)

        return updated


# Global settings manager instance
_settings_manager: Optional[SettingsManager] = None


def get_settings_manager() -> SettingsManager:
    """Get the global settings manager instance."""
    global _settings_manager
    if _settings_manager is None:
        _settings_manager = SettingsManager()
    return _settings_manager


def setup_settings_api(app) -> None:
    """
    Set up settings API endpoints in FastAPI app.

    Args:
        app: FastAPI application instance
    """
    router = APIRouter(prefix="/api/settings", tags=["settings"])

    @router.get("/")
    async def get_settings() -> Settings:
        """Get current settings."""
        manager = get_settings_manager()
        return manager.get()

    @router.put("/")
    async def update_settings(settings: Settings) -> dict[str, Any]:
        """Update all settings."""
        manager = get_settings_manager()
        success = manager.save(settings)

        if success:
            return {
                "success": True,
                "message": "Settings updated successfully",
                "settings": settings
            }
        else:
            raise HTTPException(status_code=500, detail="Failed to save settings")

    @router.patch("/")
    async def patch_settings(updates: dict[str, Any]) -> dict[str, Any]:
        """Update specific settings values."""
        try:
            manager = get_settings_manager()
            updated = manager.update(updates)

            return {
                "success": True,
                "message": "Settings updated successfully",
                "settings": updated
            }
        except Exception as e:
            raise HTTPException(
                status_code=400,
                detail=f"Failed to update settings: {str(e)}"
            )

    @router.post("/reset")
    async def reset_settings() -> dict[str, Any]:
        """Reset settings to defaults."""
        manager = get_settings_manager()
        defaults = Settings()
        manager.save(defaults)

        return {
            "success": True,
            "message": "Settings reset to defaults",
            "settings": defaults
        }

    @router.get("/browser")
    async def get_browser_settings() -> BrowserSettings:
        """Get browser settings."""
        manager = get_settings_manager()
        return manager.get().browser

    @router.get("/testing")
    async def get_test_settings() -> TestSettings:
        """Get test settings."""
        manager = get_settings_manager()
        return manager.get().testing

    @router.get("/reporting")
    async def get_report_settings() -> ReportSettings:
        """Get report settings."""
        manager = get_settings_manager()
        return manager.get().reporting

    # Add router to app
    app.include_router(router)
    logger.info("Settings API endpoints registered")
