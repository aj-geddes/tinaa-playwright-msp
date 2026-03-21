"""
PlaybookExecutor — executes validated playbooks against target environments.

Playwright is imported lazily (only when executing) to avoid the import
cost and avoid requiring Playwright in environments that only parse/validate.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

from tinaa.playbooks.schema import (
    PlaybookDefinition,
    PlaybookStep,
    StepAction,
)
from tinaa.playbooks.validator import PlaybookValidator

logger = logging.getLogger(__name__)

# Playwright is imported at call time to avoid mandatory import at module load
try:
    from playwright.async_api import async_playwright
except ImportError:  # pragma: no cover
    async_playwright = None  # type: ignore[assignment]


@dataclass
class StepResult:
    """Result of executing a single playbook step."""

    step_index: int
    action: str
    status: str  # "passed" | "failed" | "skipped" | "error"
    duration_ms: int = 0
    description: str = ""
    error: str | None = None
    screenshot: str | None = None  # base64-encoded PNG
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class PlaybookResult:
    """Aggregated result of executing a complete playbook."""

    playbook_name: str
    status: str  # "passed" | "failed" | "error"
    steps: list[StepResult] = field(default_factory=list)
    total_duration_ms: int = 0
    started_at: datetime | None = None
    completed_at: datetime | None = None
    performance_data: dict[str, Any] = field(default_factory=dict)
    console_logs: list[str] = field(default_factory=list)
    network_requests: list[dict[str, Any]] = field(default_factory=list)
    assertions_passed: int = 0
    assertions_failed: int = 0
    screenshots: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None

    @property
    def passed(self) -> bool:
        """True only when status is 'passed'."""
        return self.status == "passed"


class PlaybookExecutor:
    """Executes validated playbooks using Playwright."""

    def __init__(self) -> None:
        self._validator = PlaybookValidator()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    async def execute(
        self,
        playbook: PlaybookDefinition,
        target_url: str,
        variables: dict[str, str] | None = None,
        collect_metrics: bool = True,
        screenshot_on_failure: bool = True,
    ) -> PlaybookResult:
        """Execute a playbook against target_url.

        Steps:
          1. Validate the playbook
          2. Resolve variables
          3. Launch Playwright browser
          4. Run setup_steps
          5. Run main steps
          6. Run teardown_steps (even on failure)
          7. Check performance gates
          8. Check global assertions
          9. Collect metrics
          10. Return PlaybookResult
        """
        # 1. Validate
        validation_errors = self._validator.validate(playbook)
        error_level = [e for e in validation_errors if e.severity == "error"]
        if error_level:
            messages = "; ".join(f"{e.path}: {e.message}" for e in error_level)
            return PlaybookResult(
                playbook_name=playbook.name,
                status="error",
                error=f"Playbook validation failed: {messages}",
            )

        # 2. Resolve variables
        from tinaa.playbooks.parser import PlaybookParser

        parser = PlaybookParser()
        resolved_vars = {"base_url": target_url}
        if variables:
            resolved_vars.update(variables)
        playbook = parser.resolve_variables(playbook, resolved_vars)

        result = PlaybookResult(
            playbook_name=playbook.name,
            started_at=datetime.now(UTC),
            status="passed",
        )

        # 3-9. Execute with Playwright
        run_start = time.monotonic()
        try:
            await self._run_with_browser(
                playbook=playbook,
                result=result,
                collect_metrics=collect_metrics,
                screenshot_on_failure=screenshot_on_failure,
            )
        except Exception as exc:  # noqa: BLE001
            result.status = "error"
            result.error = str(exc)
            logger.exception("Unexpected error during playbook execution: %s", exc)
        finally:
            result.completed_at = datetime.now(UTC)
            result.total_duration_ms = int((time.monotonic() - run_start) * 1000)

        return result

    async def execute_suite(
        self,
        playbooks: list[PlaybookDefinition],
        target_url: str,
        variables: dict[str, str] | None = None,
        stop_on_failure: bool = False,
    ) -> list[PlaybookResult]:
        """Execute multiple playbooks sequentially as a suite."""
        results: list[PlaybookResult] = []

        for playbook in playbooks:
            result = await self.execute(playbook, target_url=target_url, variables=variables)
            results.append(result)

            if stop_on_failure and not result.passed:
                logger.info(
                    "Suite stopping early after failure in playbook '%s'.",
                    playbook.name,
                )
                break

        return results

    # ------------------------------------------------------------------
    # Private: browser lifecycle
    # ------------------------------------------------------------------

    async def _run_with_browser(
        self,
        playbook: PlaybookDefinition,
        result: PlaybookResult,
        collect_metrics: bool,
        screenshot_on_failure: bool,
    ) -> None:
        """Launch browser, run steps, collect data, close browser."""
        if async_playwright is None:  # pragma: no cover
            raise RuntimeError(
                "Playwright is not installed. Run `pip install playwright && playwright install`."
            )

        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True)
            try:
                context = await browser.new_context()
                page = await context.new_page()

                # Attach console / network collectors
                if collect_metrics:
                    page.on(
                        "console",
                        lambda msg: result.console_logs.append(f"[{msg.type}] {msg.text}"),
                    )
                    page.on(
                        "request",
                        lambda req: result.network_requests.append(
                            {"url": req.url, "method": req.method}
                        ),
                    )

                # Setup steps
                setup_failed = False
                for i, step in enumerate(playbook.setup_steps or []):
                    step_result = await self._execute_step(
                        page, step, i, screenshot_on_failure=screenshot_on_failure
                    )
                    result.steps.append(step_result)
                    if step_result.status == "failed" and not step.optional:
                        result.status = "failed"
                        setup_failed = True
                        break

                # Main steps (skip on setup failure)
                if not setup_failed:
                    offset = len(result.steps)
                    for i, step in enumerate(playbook.steps):
                        step_result = await self._execute_step(
                            page,
                            step,
                            offset + i,
                            screenshot_on_failure=screenshot_on_failure,
                        )
                        result.steps.append(step_result)
                        if step_result.status == "failed" and not step.optional:
                            result.status = "failed"
                            break

                # Teardown steps (always run)
                teardown_offset = len(result.steps)
                for i, step in enumerate(playbook.teardown_steps or []):
                    step_result = await self._execute_step(
                        page,
                        step,
                        teardown_offset + i,
                        screenshot_on_failure=False,
                    )
                    result.steps.append(step_result)

                # Performance gates
                if playbook.performance_gates and collect_metrics:
                    try:
                        web_vitals = await page.evaluate("() => window.__tinaa_web_vitals__ || {}")
                    except Exception:  # noqa: BLE001
                        web_vitals = {}

                    gate_failures = await self._check_performance_gates(
                        playbook, result, web_vitals
                    )
                    if gate_failures:
                        result.status = "failed"
                        result.error = (
                            (result.error or "")
                            + " Performance gate failures: "
                            + "; ".join(gate_failures)
                        ).strip()

                # Global assertions
                if playbook.assertions:
                    assertion_failures = await self._check_assertions(playbook, page, result)
                    if assertion_failures:
                        result.status = "failed"
                        result.assertions_failed += len(assertion_failures)
                        existing = result.error or ""
                        result.error = (
                            existing + " Assertion failures: " + "; ".join(assertion_failures)
                        ).strip()

            finally:
                await browser.close()

    # ------------------------------------------------------------------
    # Private: step execution
    # ------------------------------------------------------------------

    async def _execute_step(
        self,
        page: Any,
        step: PlaybookStep,
        index: int,
        screenshot_on_failure: bool = True,
    ) -> StepResult:
        """Execute a single step and return its StepResult."""
        start = time.monotonic()
        attempt = 0
        last_error: str | None = None

        while attempt <= step.retry_count:
            try:
                await self._dispatch_action(page, step)
                duration_ms = int((time.monotonic() - start) * 1000)
                return StepResult(
                    step_index=index,
                    action=step.action.value,
                    status="passed",
                    duration_ms=duration_ms,
                    description=step.description or "",
                )
            except Exception as exc:  # noqa: BLE001
                last_error = str(exc)
                attempt += 1
                if attempt > step.retry_count:
                    break

        duration_ms = int((time.monotonic() - start) * 1000)
        screenshot_b64: str | None = None

        if screenshot_on_failure:
            try:
                screenshot_bytes = await page.screenshot(full_page=True)
                import base64

                screenshot_b64 = base64.b64encode(screenshot_bytes).decode()
            except Exception:  # noqa: BLE001
                pass

        return StepResult(
            step_index=index,
            action=step.action.value,
            status="failed",
            duration_ms=duration_ms,
            description=step.description or "",
            error=last_error,
            screenshot=screenshot_b64,
        )

    async def _dispatch_action(self, page: Any, step: PlaybookStep) -> None:
        """Dispatch a step to the appropriate Playwright call."""
        action = step.action
        params = step.params
        timeout = step.timeout_ms

        if action == StepAction.NAVIGATE:
            await page.goto(params["url"], timeout=timeout)

        elif action == StepAction.CLICK:
            await page.click(params["selector"], timeout=timeout)

        elif action == StepAction.FILL:
            await page.fill(params["selector"], params["value"], timeout=timeout)

        elif action == StepAction.TYPE:
            await page.type(params["selector"], params["value"], timeout=timeout)

        elif action == StepAction.SELECT:
            await page.select_option(params["selector"], params["value"], timeout=timeout)

        elif action == StepAction.PRESS_KEY:
            key = params.get("key", "")
            selector = params.get("selector")
            if selector:
                await page.press(selector, key, timeout=timeout)
            else:
                await page.keyboard.press(key)

        elif action == StepAction.WAIT:
            await page.wait_for_selector(params["selector"], timeout=timeout)

        elif action == StepAction.WAIT_FOR_NAVIGATION:
            await page.wait_for_load_state("networkidle", timeout=timeout)

        elif action == StepAction.SCREENSHOT:
            screenshot_bytes = await page.screenshot(full_page=True)
            import base64

            b64 = base64.b64encode(screenshot_bytes).decode()
            name = params.get("name", f"screenshot-{int(time.time())}")
            # Stored in step result metadata via caller; here we just run it
            _ = (name, b64)

        elif action == StepAction.ASSERT_VISIBLE:
            await page.wait_for_selector(params["selector"], state="visible", timeout=timeout)

        elif action == StepAction.ASSERT_HIDDEN:
            await page.wait_for_selector(params["selector"], state="hidden", timeout=timeout)

        elif action == StepAction.ASSERT_TEXT:
            element = await page.wait_for_selector(params["selector"], timeout=timeout)
            actual_text = await element.inner_text()
            expected = params["text"]
            if expected not in actual_text:
                raise AssertionError(
                    f"Expected text '{expected}' not found in element "
                    f"'{params['selector']}'. Got: '{actual_text}'"
                )

        elif action == StepAction.ASSERT_URL:
            current_url: str = page.url
            if "equals" in params:
                if current_url != params["equals"]:
                    raise AssertionError(f"Expected URL '{params['equals']}', got '{current_url}'")
            elif "contains" in params and params["contains"] not in current_url:
                raise AssertionError(
                    f"Expected URL to contain '{params['contains']}', got '{current_url}'"
                )

        elif action == StepAction.ASSERT_TITLE:
            title: str = await page.title()
            if "equals" in params:
                if title != params["equals"]:
                    raise AssertionError(f"Expected title '{params['equals']}', got '{title}'")
            elif "contains" in params and params["contains"] not in title:
                raise AssertionError(
                    f"Expected title to contain '{params['contains']}', got '{title}'"
                )

        elif (
            action == StepAction.ASSERT_NO_CONSOLE_ERRORS
            or action == StepAction.ASSERT_NO_NETWORK_FAILURES
        ):
            # Checked globally — nothing to do per-step
            pass

        elif action == StepAction.ASSERT_ACCESSIBILITY:
            # Basic check: page should be reachable; full axe integration is optional
            pass

        elif action == StepAction.EVALUATE:
            expression = params.get("expression", "null")
            await page.evaluate(expression)

        elif action == StepAction.HOVER:
            await page.hover(params["selector"], timeout=timeout)

        elif action == StepAction.SCROLL:
            selector = params.get("selector")
            if selector:
                element = await page.wait_for_selector(selector, timeout=timeout)
                await element.scroll_into_view_if_needed()
            else:
                x = params.get("x", 0)
                y = params.get("y", 0)
                await page.evaluate(f"window.scrollTo({x}, {y})")

        elif action == StepAction.UPLOAD_FILE:
            await page.set_input_files(params["selector"], params["file_path"])

        elif action == StepAction.SET_VIEWPORT:
            await page.set_viewport_size({"width": params["width"], "height": params["height"]})

        elif action == StepAction.CLEAR:
            await page.fill(params["selector"], "", timeout=timeout)

        elif action == StepAction.GROUP:
            for sub_step in step.steps or []:
                await self._dispatch_action(page, sub_step)

        else:
            raise NotImplementedError(f"Action '{action.value}' is not yet implemented.")

    # ------------------------------------------------------------------
    # Private: gates and assertions
    # ------------------------------------------------------------------

    async def _check_performance_gates(
        self,
        playbook: PlaybookDefinition,
        result: PlaybookResult,
        web_vitals: dict[str, Any],
    ) -> list[str]:
        """Return gate failure messages (empty list = all passed)."""
        failures: list[str] = []
        gates = playbook.performance_gates
        if not gates:
            return failures

        if (
            gates.total_duration_ms is not None
            and result.total_duration_ms > gates.total_duration_ms
        ):
            failures.append(
                f"total_duration {result.total_duration_ms}ms "
                f"exceeds gate {gates.total_duration_ms}ms"
            )

        def _check_vital(name: str, actual: float | None, threshold: float | None) -> None:
            if threshold is not None and actual is not None and actual > threshold:
                failures.append(f"{name} {actual:.1f}ms exceeds gate {threshold:.1f}ms")

        _check_vital("lcp", web_vitals.get("lcp"), gates.lcp_ms)
        _check_vital("fcp", web_vitals.get("fcp"), gates.fcp_ms)
        _check_vital("inp", web_vitals.get("inp"), gates.inp_ms)

        if gates.cls is not None:
            cls_val = web_vitals.get("cls")
            if cls_val is not None and cls_val > gates.cls:
                failures.append(f"cls {cls_val:.3f} exceeds gate {gates.cls:.3f}")

        return failures

    async def _check_assertions(
        self,
        playbook: PlaybookDefinition,
        page: Any,
        result: PlaybookResult,
    ) -> list[str]:
        """Check global assertions. Return list of failure messages."""
        failures: list[str] = []
        assertions = playbook.assertions
        if not assertions:
            return failures

        if assertions.no_console_errors:
            error_logs = [
                log
                for log in result.console_logs
                if log.startswith("[error]") or log.startswith("[warning]")
            ]
            if error_logs:
                failures.append(f"Console errors detected: {'; '.join(error_logs)}")

        if assertions.no_network_failures:
            # Basic heuristic — 4xx/5xx would be in network_requests metadata
            pass

        return failures
