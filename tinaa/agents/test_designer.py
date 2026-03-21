"""
TestDesignerAgent — designs test playbooks from application models.
"""

from __future__ import annotations

from typing import Any

from tinaa.agents.base import AgentTask, BaseAgent

# Priority ordering for journey classification
_PRIORITY_KEYWORDS: list[tuple[str, str]] = [
    ("auth", "critical"),
    ("login", "critical"),
    ("payment", "critical"),
    ("checkout", "critical"),
    ("register", "high"),
    ("signup", "high"),
    ("profile", "high"),
    ("dashboard", "high"),
    ("search", "medium"),
    ("contact", "low"),
]

# Default performance thresholds (ms)
_DEFAULT_PERF_GATE_MS = 3000
_CRITICAL_PERF_GATE_MS = 1500


class TestDesignerAgent(BaseAgent):
    """Generates Playwright-ready test playbooks from application models."""

    def __init__(self) -> None:
        super().__init__("test_designer")

    # ------------------------------------------------------------------
    # BaseAgent._run dispatch
    # ------------------------------------------------------------------

    async def _run(self, task: AgentTask) -> Any:
        action = task.action

        if action == "generate_playbooks":
            return await self.generate_playbooks(
                task.params.get("app_model", {}),
                task.params.get("product_config"),
            )

        if action == "update_playbook":
            return await self._update_playbook(task.params)

        if action == "suggest_tests":
            return await self.suggest_tests_for_diff(
                task.params.get("diff_analysis", {}),
                task.params.get("existing_playbooks", []),
            )

        raise ValueError(f"TestDesignerAgent has no handler for action '{action}'")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def generate_playbooks(
        self, app_model: dict, product_config: dict | None = None
    ) -> list[dict]:
        """Generate test playbooks from an application model.

        Produces one playbook per user journey plus dedicated auth and API
        playbooks when flows are detected.
        """
        playbooks: list[dict] = []
        config = product_config or {}

        for journey in app_model.get("user_journeys", []):
            pb = self._playbook_from_journey(journey, config)
            playbooks.append(pb)

        for auth_flow in app_model.get("auth_flows", []):
            pb = await self.generate_auth_playbook(auth_flow)
            playbooks.append(pb)

        for endpoint in app_model.get("api_endpoints", []):
            if endpoint.get("method") in ("POST", "PUT", "DELETE"):
                pb = await self.generate_crud_playbook(endpoint)
                playbooks.append(pb)

        return playbooks

    async def generate_auth_playbook(self, auth_flow: dict) -> dict:
        """Generate a playbook for testing an authentication flow.

        Covers login, invalid credentials, and session assertions.
        """
        login_page = auth_flow.get("login_page", "/login")
        fields = auth_flow.get("fields", ["email", "password"])
        flow_type = auth_flow.get("type", "form")

        steps: list[dict] = [
            {"action": "navigate", "url": login_page, "name": "Navigate to login page"},
        ]

        for field_name in fields:
            selector = f"[name='{field_name}'], #{field_name}, input[type='{self._field_type(field_name)}']"
            steps.append(
                {
                    "action": "fill",
                    "selector": selector,
                    "value": self._placeholder_value(field_name),
                    "name": f"Fill {field_name}",
                }
            )

        steps += [
            {
                "action": "click",
                "selector": "button[type='submit'], input[type='submit'], .login-btn, .submit-btn",
                "name": "Submit login form",
            },
            {
                "action": "wait_for_navigation",
                "timeout": 5000,
                "name": "Wait for redirect after login",
            },
            {
                "action": "assert_url",
                "contains": "/dashboard",
                "name": "Assert redirected to dashboard",
            },
        ]

        invalid_steps: list[dict] = [
            {"action": "navigate", "url": login_page, "name": "Navigate to login page (invalid)"},
            {
                "action": "fill",
                "selector": "[name='email'], #email",
                "value": "bad@bad.com",
                "name": "Fill invalid email",
            },
            {
                "action": "fill",
                "selector": "[name='password'], #password",
                "value": "wrongpassword",
                "name": "Fill invalid password",
            },
            {
                "action": "click",
                "selector": "button[type='submit']",
                "name": "Submit invalid credentials",
            },
            {
                "action": "assert_visible",
                "selector": ".error, .alert, [role='alert']",
                "name": "Assert error message shown",
            },
        ]

        return {
            "name": "Authentication Flow",
            "description": "Tests login, invalid credentials, and session persistence",
            "priority": "critical",
            "steps": steps,
            "alternate_steps": {"invalid_credentials": invalid_steps},
            "assertions": [
                {"name": "Login page accessible", "type": "url_accessible"},
                {"name": "Redirect after login", "type": "url_contains", "value": "/dashboard"},
            ],
            "performance_gates": {"navigate": _CRITICAL_PERF_GATE_MS},
            "source": "auto_generated",
            "flow_type": flow_type,
        }

    async def generate_crud_playbook(self, api_endpoint: dict) -> dict:
        """Generate a playbook for CRUD API testing."""
        path = api_endpoint.get("path", "/api/resource")
        method = api_endpoint.get("method", "POST")
        handler = api_endpoint.get("handler", "resource")

        steps: list[dict] = [
            {
                "action": "navigate",
                "url": path.rstrip("/"),
                "name": f"Navigate to {path}",
            },
            {
                "action": "assert_visible",
                "selector": "body",
                "name": "Assert page body visible",
            },
        ]

        if method in ("POST", "PUT"):
            steps.append(
                {
                    "action": "evaluate",
                    "script": "return document.title",
                    "name": f"Verify {handler} page loaded",
                }
            )

        return {
            "name": f"CRUD Test: {handler.title()} ({method})",
            "description": f"Tests {method} operations on {path}",
            "priority": "high",
            "steps": steps,
            "assertions": [
                {"name": "Endpoint accessible", "type": "status_ok"},
            ],
            "performance_gates": {"response": _DEFAULT_PERF_GATE_MS},
            "source": "auto_generated",
            "endpoint": path,
            "method": method,
        }

    async def suggest_tests_for_diff(
        self, diff_analysis: dict, existing_playbooks: list[dict]
    ) -> list[dict]:
        """Suggest new or modified tests based on diff analysis."""
        suggestions: list[dict] = []

        affected_routes = diff_analysis.get("affected_routes", [])
        affected_journeys = diff_analysis.get("affected_journeys", [])
        risk_level = diff_analysis.get("risk_level", "low")
        existing_names = {pb.get("name", "") for pb in existing_playbooks}

        for route in affected_routes:
            playbook_name = f"Smoke Test: {route}"
            suggestion_type = "modify" if playbook_name in existing_names else "new"
            priority = self._route_priority(route, risk_level)
            suggestions.append(
                {
                    "type": suggestion_type,
                    "playbook_name": playbook_name,
                    "reason": f"Route {route} was modified",
                    "priority": priority,
                    "affected_journey": route,
                    "suggested_steps": [
                        {"action": "navigate", "url": route},
                        {"action": "assert_visible", "selector": "main, #app, .content"},
                    ],
                }
            )

        for journey in affected_journeys:
            playbook_name = f"Regression: {journey}"
            suggestion_type = "modify" if playbook_name in existing_names else "new"
            suggestions.append(
                {
                    "type": suggestion_type,
                    "playbook_name": playbook_name,
                    "reason": f"Journey '{journey}' may be affected by changes",
                    "priority": "high" if risk_level == "high" else "medium",
                    "affected_journey": journey,
                    "suggested_steps": [],
                }
            )

        if risk_level == "high" and not suggestions:
            suggestions.append(
                {
                    "type": "new",
                    "playbook_name": "Full Regression Suite",
                    "reason": "High-risk change detected",
                    "priority": "critical",
                    "affected_journey": "all",
                    "suggested_steps": [],
                }
            )

        return suggestions

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _playbook_from_journey(self, journey: dict, config: dict) -> dict:
        """Convert a user journey descriptor into a playbook dict."""
        name = journey.get("name", "Unnamed Journey")
        steps_desc = journey.get("steps", [])
        priority = journey.get("priority", "medium")

        steps: list[dict] = []
        for step_text in steps_desc:
            step = self._step_from_description(str(step_text))
            if step:
                steps.append(step)

        perf_gate = _CRITICAL_PERF_GATE_MS if priority == "critical" else _DEFAULT_PERF_GATE_MS

        return {
            "name": f"Journey: {name}",
            "description": f"Auto-generated playbook for user journey: {name}",
            "priority": priority,
            "steps": steps,
            "assertions": [{"name": "Journey completes", "type": "no_errors"}],
            "performance_gates": {"page_load": perf_gate},
            "source": "auto_generated",
        }

    def _step_from_description(self, description: str) -> dict | None:
        """Convert a natural-language step description into a step dict."""
        lower = description.lower()

        if "navigate" in lower or "open" in lower or "go to" in lower:
            url = self._extract_url_from_description(description)
            return {"action": "navigate", "url": url, "name": description}

        if "fill" in lower or "enter" in lower or "type" in lower:
            return {"action": "fill", "selector": "input", "value": "", "name": description}

        if "click" in lower or "submit" in lower or "press" in lower:
            return {"action": "click", "selector": "button", "name": description}

        if "assert" in lower or "verify" in lower or "check" in lower:
            return {"action": "assert_visible", "selector": "body", "name": description}

        if "wait" in lower:
            return {"action": "wait", "selector": "body", "state": "visible", "name": description}

        return None

    def _extract_url_from_description(self, description: str) -> str:
        """Extract a URL or path from a step description string."""
        words = description.split()
        for word in words:
            if word.startswith("/") or word.startswith("http"):
                return word
        return "/"

    @staticmethod
    def _field_type(field_name: str) -> str:
        """Map a form field name to its HTML input type."""
        field_name_lower = field_name.lower()
        if "password" in field_name_lower:
            return "password"
        if "email" in field_name_lower:
            return "email"
        if "phone" in field_name_lower or "tel" in field_name_lower:
            return "tel"
        return "text"

    @staticmethod
    def _placeholder_value(field_name: str) -> str:
        """Return a safe placeholder test value for a form field."""
        field_name_lower = field_name.lower()
        if "password" in field_name_lower:
            return "Test@Password123!"
        if "email" in field_name_lower:
            return "testuser@example.com"
        if "username" in field_name_lower or "user" in field_name_lower:
            return "testuser"
        if "name" in field_name_lower:
            return "Test User"
        return "test_value"

    @staticmethod
    def _route_priority(route: str, risk_level: str) -> str:
        """Determine test priority for a route based on keywords and risk."""
        lower = route.lower()
        for keyword, priority in _PRIORITY_KEYWORDS:
            if keyword in lower:
                return priority
        if risk_level == "high":
            return "high"
        return "medium"

    async def _update_playbook(self, params: dict) -> dict:
        """Stub: update an existing playbook with new steps."""
        playbook = params.get("playbook", {})
        updates = params.get("updates", {})
        playbook.update(updates)
        return playbook
