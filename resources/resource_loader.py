"""
Resource loader for Tinaa Playwright MSP

This module loads resources for QA testing
"""

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger("tinaa-playwright-msp.resources")


class ResourceLoader:
    """Class for loading and managing resources"""

    def __init__(self):
        self.resources_dir = Path(__file__).parent
        self.resources = {
            "testing_strategies": {},
            "heuristics": {},
            "accessibility_guidelines": {},
            "test_patterns": {},
            "credentials": {},
        }

        self.load_resources()

    def load_resources(self):
        """Load all resources from the resources directory"""
        # Load testing strategies
        self._load_json_resource("testing_strategies.json", "testing_strategies")

        # Load heuristics
        self._load_json_resource("heuristics.json", "heuristics")

        # Load accessibility guidelines
        self._load_json_resource(
            "accessibility_guidelines.json", "accessibility_guidelines"
        )

        # Load test patterns
        self._load_json_resource("test_patterns.json", "test_patterns")

        # Load credentials (if exists)
        creds_path = self.resources_dir / "credentials.json"
        if creds_path.exists():
            self._load_json_resource("credentials.json", "credentials")
            logger.info("Loaded credentials")
        else:
            logger.info("No credentials file found")

    def _load_json_resource(self, filename: str, resource_key: str):
        """Load a JSON resource file"""
        try:
            with open(self.resources_dir / filename) as f:
                self.resources[resource_key] = json.load(f)
            logger.info(f"Loaded {filename}")
        except Exception as e:
            logger.error(f"Error loading {filename}: {e}")

    def get_resource(self, resource_type: str) -> dict[str, Any]:
        """Get a specific type of resource"""
        return self.resources.get(resource_type, {})

    def get_testing_strategy(self, strategy_name: str) -> dict[str, Any] | None:
        """Get a specific testing strategy"""
        return self.resources.get("testing_strategies", {}).get(strategy_name)

    def get_heuristic(self, heuristic_name: str) -> dict[str, Any] | None:
        """Get a specific heuristic"""
        return self.resources.get("heuristics", {}).get(heuristic_name)

    def get_credentials(self, site_name: str) -> dict[str, str] | None:
        """Get credentials for a specific site"""
        return self.resources.get("credentials", {}).get(site_name)

    def save_credentials(self, site_name: str, credentials: dict[str, str]) -> bool:
        """Save credentials for a site"""
        try:
            # Update in-memory credentials
            if "credentials" not in self.resources:
                self.resources["credentials"] = {}

            self.resources["credentials"][site_name] = credentials

            # Save to file
            creds_path = self.resources_dir / "credentials.json"
            with open(creds_path, "w") as f:
                json.dump(self.resources["credentials"], f, indent=2)

            logger.info(f"Saved credentials for {site_name}")
            return True
        except Exception as e:
            logger.error(f"Error saving credentials for {site_name}: {e}")
            return False


# Create a global instance of the resource loader
resource_loader = ResourceLoader()


def get_resource_loader() -> ResourceLoader:
    """Get the global resource loader instance"""
    return resource_loader
