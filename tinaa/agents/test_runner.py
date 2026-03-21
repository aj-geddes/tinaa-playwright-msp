"""
TestRunnerAgent — executes test playbooks using Playwright.
"""

from __future__ import annotations

import base64
import contextlib
import time
from typing import Any

from tinaa.agents.base import AgentTask, BaseAgent


class TestRunnerAgent(BaseAgent):
    """Executes Playwright-driven test playbooks against a target URL."""

    def __init__(self) -> None:
        super().__init__("test_runner")
        self._browser: Any = None
        self._playwright: Any = None

    # ------------------------------------------------------------------
    # BaseAgent._run dispatch
    # ------------------------------------------------------------------

    async def _run(self, task: AgentTask) -> Any:
        action = task.action

        if action == "run_playbook":
            return await self.run_playbook(
                task.params.get("playbook", {}),
                task.params.get("target_url", ""),
                task.params.get("collect_metrics", True),
            )

        if action == "run_suite":
            return await self._run_suite(task.params)

        raise ValueError(f"TestRunnerAgent has no handler for action '{action}'")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def run_playbook(
        self,
        playbook: dict,
        target_url: str,
        collect_metrics: bool = True,
    ) -> dict:
        """Execute a playbook against a target URL.

        Returns a structured result including step outcomes, duration,
        screenshots, and performance data when requested.
        """
        start_ms = _now_ms()
        step_results: list[dict] = []
        screenshots: list[dict] = []
        console_logs: list[str] = []
        network_requests: list[dict] = []
        assertions: list[dict] = []
        overall_status = "passed"

        steps = playbook.get("steps", [])

        if not steps:
            # Empty playbook — trivially passes
            return {
                "status": "passed",
                "steps": [],
                "duration_ms": _now_ms() - start_ms,
                "screenshots": [],
                "console_logs": [],
                "network_requests": [],
                "performance": {} if collect_metrics else None,
                "assertions": [],
            }

        await self._ensure_browser()
        context = None
        page = None
        performance: dict = {}

        try:
            context = await self._browser.new_context()
            page = await context.new_page()

            # Capture console output
            page.on("console", lambda msg: console_logs.append(f"[{msg.type}] {msg.text}"))

            # Capture network requests
            page.on(
                "response",
                lambda resp: network_requests.append(
                    {
                        "url": resp.url,
                        "status": resp.status,
                        "duration_ms": 0,
                    }
                ),
            )

            for step in steps:
                step_result = await self.execute_step(page, step)
                step_results.append(
                    {
                        "name": step.get("name", step.get("action", "unnamed")),
                        **step_result,
                    }
                )
                if step_result["status"] in ("failed", "error"):
                    overall_status = "failed"

                # Collect inline screenshots from screenshot steps
                if step.get("action") == "screenshot" and step_result.get("screenshot_data"):
                    screenshots.append(
                        {
                            "step": step.get("name", "screenshot"),
                            "data": step_result["screenshot_data"],
                        }
                    )

            # Harvest assertions from the playbook definition
            for assertion in playbook.get("assertions", []):
                assertions.append(
                    {
                        "name": assertion.get("name", "unnamed"),
                        "passed": overall_status == "passed",
                        "expected": assertion.get("value"),
                        "actual": None,
                    }
                )

            performance: dict = {}
            if collect_metrics:
                try:
                    web_vitals = await page.evaluate(
                        """() => {
                            const nav = performance.getEntriesByType('navigation')[0];
                            return {
                                TTFB: nav ? nav.responseStart - nav.requestStart : null,
                                domContentLoaded: nav ? nav.domContentLoadedEventEnd - nav.startTime : null,
                                pageLoad: nav ? nav.loadEventEnd - nav.startTime : null,
                            };
                        }"""
                    )
                    performance = {"web_vitals": web_vitals or {}, "resource_timing": {}}
                except Exception:
                    performance = {"web_vitals": {}, "resource_timing": {}}

        except Exception as exc:
            self.logger.error("Playbook execution error: %s", exc)
            overall_status = "error"
            step_results.append(
                {"name": "runner", "status": "error", "duration_ms": 0, "error": str(exc)}
            )
        finally:
            if page:
                with contextlib.suppress(Exception):
                    await page.close()
            if context:
                with contextlib.suppress(Exception):
                    await context.close()

        return {
            "status": overall_status,
            "steps": step_results,
            "duration_ms": _now_ms() - start_ms,
            "screenshots": screenshots,
            "console_logs": console_logs,
            "network_requests": network_requests,
            "performance": performance if collect_metrics else None,
            "assertions": assertions,
        }

    async def execute_step(self, page: Any, step: dict) -> dict:
        """Execute a single playbook step on a Playwright page.

        Supported actions: navigate, click, fill, type, wait, screenshot,
        assert_visible, assert_text, assert_url, evaluate, select,
        press_key, wait_for_navigation.

        Returns: {"status": str, "duration_ms": int, "error": str|None}
        """
        action = step.get("action", "")
        start = _now_ms()
        error_msg: str | None = None
        status = "passed"
        extra: dict = {}

        try:
            if action == "navigate":
                await page.goto(step["url"])

            elif action == "click":
                await page.click(step["selector"])

            elif action == "fill":
                await page.fill(step["selector"], step.get("value", ""))

            elif action == "type":
                await page.type(step["selector"], step.get("text", ""))

            elif action == "wait":
                state = step.get("state", "visible")
                await page.wait_for_selector(step["selector"], state=state)

            elif action == "screenshot":
                raw = await page.screenshot()
                if isinstance(raw, bytes):
                    extra["screenshot_data"] = base64.b64encode(raw).decode()
                else:
                    extra["screenshot_data"] = ""

            elif action == "assert_visible":
                visible = await page.is_visible(step["selector"])
                if not visible:
                    status = "failed"
                    error_msg = f"Selector '{step['selector']}' is not visible"

            elif action == "assert_text":
                actual = await page.inner_text(step["selector"])
                expected = step.get("text", "")
                if actual != expected:
                    status = "failed"
                    error_msg = f"Text mismatch: expected '{expected}', got '{actual}'"

            elif action == "assert_url":
                contains = step.get("contains", "")
                current_url: str = page.url
                if contains not in current_url:
                    status = "failed"
                    error_msg = f"URL '{current_url}' does not contain '{contains}'"

            elif action == "evaluate":
                await page.evaluate(step.get("script", "null"))

            elif action == "select":
                await page.select_option(step["selector"], step.get("value", ""))

            elif action == "press_key":
                await page.keyboard.press(step.get("key", ""))

            elif action == "wait_for_navigation":
                await page.wait_for_load_state("load")

            else:
                status = "error"
                error_msg = f"Unknown step action: '{action}'"

        except Exception as exc:
            status = "failed" if action.startswith("assert") else "error"
            error_msg = str(exc)

        duration = _now_ms() - start
        result = {"status": status, "duration_ms": duration, "error": error_msg}
        result.update(extra)
        return result

    async def _ensure_browser(self) -> None:
        """Lazily initialise the Playwright browser."""
        if self._browser is not None:
            return
        from playwright.async_api import async_playwright

        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=True)
        self.logger.info("Playwright Chromium browser launched")

    async def cleanup(self) -> None:
        """Close the browser and Playwright instance."""
        if self._browser:
            await self._browser.close()
            self._browser = None
        if self._playwright:
            await self._playwright.stop()
            self._playwright = None
        self.logger.info("Playwright browser closed")

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    async def _run_suite(self, params: dict) -> dict:
        """Execute a suite of playbooks (stub — no DB access)."""
        playbooks = params.get("playbooks", [])
        target_url = params.get("target_url", "")
        results = []
        for pb in playbooks:
            result = await self.run_playbook(pb, target_url)
            results.append(result)
        return {
            "suite_status": "passed" if all(r["status"] == "passed" for r in results) else "failed",
            "playbook_results": results,
            "total": len(results),
        }


def _now_ms() -> int:
    """Current wall-clock time in milliseconds."""
    return int(time.monotonic() * 1000)
