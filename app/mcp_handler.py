"""
MCP Function Handler for Tinaa Playwright MSP

This module connects MCP functions with the Playwright controller.
Provides all the core tools for browser automation and testing.
"""

import logging
from typing import Any, Optional

# Import from fastmcp 2.8.0
# Using the decorator pattern from FastMCP
from fastmcp import Context

# Import from local modules
from playwright_controller.controller import PlaywrightController
from prompts import (
    EXPLORATORY_TEST_PROMPT,
    TEST_REPORT_TEMPLATE,
)
from resources import get_resource_loader

logger = logging.getLogger("tinaa-playwright-msp.mcp-handler")

# Global controller instance
controller: PlaywrightController | None = None


async def get_controller() -> PlaywrightController:
    """
    Get or create a Playwright controller instance.

    Returns:
        PlaywrightController: An initialized Playwright controller

    Raises:
        RuntimeError: If controller initialization fails
    """
    global controller

    if controller is None or not controller.is_initialized:
        controller = PlaywrightController()
        success = await controller.initialize()
        if not success:
            raise RuntimeError("Failed to initialize Playwright controller")

    return controller


# We'll use the main mcp instance from app.main instead of creating our own
# This will be imported after app.main initializes it


async def navigate_to_url(url: str, ctx: Optional[Context] = None) -> dict[str, Any]:
    """
    Navigate to a specified URL in the browser.

    This tool opens a webpage in the browser and waits for it to load.
    It captures the final URL (after any redirects) and page title.

    Args:
        url: The URL to navigate to (must start with http:// or https://)
        ctx: The execution context for progress reporting (optional)

    Returns:
        Dictionary containing:
        - success: Boolean indicating if navigation succeeded
        - url: The requested URL
        - current_url: The actual URL after navigation and redirects
        - title: The page title (if available)
        - error: Error message if navigation failed

    Example:
        >>> result = await navigate_to_url("https://example.com")
        >>> print(result["title"])
        "Example Domain"
    """
    try:
        if ctx:
            await ctx.info(f"Navigating to URL: {url}")

        # Validate URL format
        if not url.startswith(('http://', 'https://')):
            error_msg = "URL must start with http:// or https://"
            if ctx:
                await ctx.error(error_msg)
            return {"success": False, "url": url, "error": error_msg}

        controller = await get_controller()
        success = await controller.navigate(url)

        result = {
            "success": success,
            "url": url,
            "current_url": controller.page.url if success and controller.page else None,
            "title": await controller.page.title() if success and controller.page else None,
        }

        if ctx:
            if success:
                await ctx.success(f"Successfully navigated to {url}")
            else:
                await ctx.error(f"Failed to navigate to {url}")

        return result
    except Exception as e:
        logger.error(f"Error in navigate_to_url: {e}", exc_info=True)
        if ctx:
            await ctx.error(f"Error: {e!s}")
        return {"success": False, "url": url, "error": str(e)}


async def take_page_screenshot(
    full_page: bool = False, ctx: Optional[Context] = None
) -> dict[str, Any]:
    """
    Take a screenshot of the current page.

    Captures a PNG screenshot of either the visible viewport or the entire page
    including content that requires scrolling.

    Args:
        full_page: If True, captures the entire page by scrolling.
                   If False, captures only the visible viewport (default: False)
        ctx: The execution context for progress reporting (optional)

    Returns:
        Dictionary containing:
        - success: Boolean indicating if screenshot was captured
        - screenshot: Base64-encoded PNG image data
        - type: MIME type (always "image/png")
        - full_page: Boolean indicating if full page was captured
        - error: Error message if screenshot failed

    Example:
        >>> result = await take_page_screenshot(full_page=True)
        >>> if result["success"]:
        ...     with open("screenshot.png", "wb") as f:
        ...         f.write(base64.b64decode(result["screenshot"]))
    """
    try:
        if ctx:
            await ctx.info(
                f"Taking {'full page' if full_page else 'viewport'} screenshot"
            )

        controller = await get_controller()
        screenshot = await controller.take_screenshot(
            "user_requested", full_page=full_page
        )

        result = {
            "success": screenshot is not None,
            "screenshot": screenshot,
            "type": "image/png",
            "full_page": full_page,
        }

        if ctx:
            if screenshot:
                await ctx.success("Screenshot captured successfully")
            else:
                await ctx.error("Failed to capture screenshot")

        return result
    except Exception as e:
        logger.error(f"Error in take_page_screenshot: {e}", exc_info=True)
        if ctx:
            await ctx.error(f"Error: {e!s}")
        return {"success": False, "error": str(e)}


async def take_element_screenshot(selector: str, ctx: Optional[Context] = None) -> dict[str, Any]:
    """
    Take a screenshot of a specific element on the page.

    Captures a PNG screenshot of a single element identified by a CSS selector.
    The element will be scrolled into view if necessary before capture.

    Args:
        selector: CSS selector for the target element (e.g., "#login-button", ".header")
        ctx: The execution context for progress reporting (optional)

    Returns:
        Dictionary containing:
        - success: Boolean indicating if screenshot was captured
        - screenshot: Base64-encoded PNG image data of the element
        - type: MIME type (always "image/png")
        - selector: The CSS selector that was used
        - error: Error message if screenshot failed

    Example:
        >>> result = await take_element_screenshot("#main-content")
        >>> if result["success"]:
        ...     print(f"Captured element: {result['selector']}")
    """
    try:
        if ctx:
            await ctx.info(f"Taking screenshot of element: {selector}")

        # Validate selector
        if not selector or not selector.strip():
            error_msg = "Selector cannot be empty"
            if ctx:
                await ctx.error(error_msg)
            return {"success": False, "selector": selector, "error": error_msg}

        controller = await get_controller()
        screenshot = await controller.take_screenshot(
            "user_requested_element", selector=selector
        )

        result = {
            "success": screenshot is not None,
            "screenshot": screenshot,
            "type": "image/png",
            "selector": selector,
        }

        if ctx:
            if screenshot:
                await ctx.success("Element screenshot captured successfully")
            else:
                await ctx.error("Failed to capture element screenshot")

        return result
    except Exception as e:
        logger.error(f"Error in take_element_screenshot: {e}", exc_info=True)
        if ctx:
            await ctx.error(f"Error: {e!s}")
        return {"success": False, "selector": selector, "error": str(e)}


async def fill_login_form(
    username_selector: str,
    password_selector: str,
    submit_selector: str,
    username: str,
    password: str,
    ctx: Optional[Context] = None,
) -> dict[str, Any]:
    """
    Fill and submit a login form with credentials.

    This tool fills in username and password fields and submits the form.
    It's useful for testing authentication workflows.

    Args:
        username_selector: CSS selector for username/email input field
        password_selector: CSS selector for password input field
        submit_selector: CSS selector for submit button
        username: Username or email to enter
        password: Password to enter
        ctx: The execution context for progress reporting (optional)

    Returns:
        Dictionary containing:
        - success: Boolean indicating if form was filled and submitted
        - username_selector: The username field selector used
        - password_selector: The password field selector used
        - submit_selector: The submit button selector used
        - url_after_submit: The URL after form submission
        - error: Error message if operation failed

    Example:
        >>> result = await fill_login_form(
        ...     username_selector="#username",
        ...     password_selector="#password",
        ...     submit_selector="button[type='submit']",
        ...     username="testuser",
        ...     password="testpass123"
        ... )
        >>> print(result["success"])
        True

    Note:
        For security testing purposes only. Never use real credentials in tests.
    """
    try:
        if ctx:
            await ctx.info(f"Filling login form with username: {username}")

        # Validate inputs
        if not all([username_selector, password_selector, submit_selector, username, password]):
            error_msg = "All parameters (selectors, username, and password) are required"
            if ctx:
                await ctx.error(error_msg)
            return {"success": False, "error": error_msg}

        controller = await get_controller()
        result = await controller.test_login_form(
            username_selector=username_selector,
            password_selector=password_selector,
            submit_selector=submit_selector,
            username=username,
            password=password,
        )

        if ctx:
            if result.get("success", False):
                await ctx.success("Login form submitted successfully")
            else:
                await ctx.warning("Login form submitted but may not have succeeded")

        return result
    except Exception as e:
        logger.error(f"Error in fill_login_form: {e}", exc_info=True)
        if ctx:
            await ctx.error(f"Error: {e!s}")
        return {"success": False, "error": str(e)}


async def detect_form_fields(
    form_selector: Optional[str] = None, ctx: Optional[Context] = None
) -> dict[str, Any]:
    """
    Detect form fields on the current page

    Args:
        form_selector: Optional CSS selector for the form
        ctx: The execution context

    Returns:
        Dictionary with form fields
    """
    try:
        if ctx:
            await ctx.info(
                f"Detecting form fields{' in ' + form_selector if form_selector else ''}"
            )

        controller = await get_controller()
        fields = await controller.extract_form_fields(form_selector)

        result = {
            "success": len(fields) > 0,
            "fields": fields,
            "count": len(fields),
            "form_selector": form_selector,
        }

        if ctx:
            if fields:
                await ctx.success(f"Detected {len(fields)} form fields")
            else:
                await ctx.warning("No form fields detected")

        return result
    except Exception as e:
        logger.error(f"Error in detect_form_fields: {e}")
        if ctx:
            await ctx.error(f"Error: {e!s}")
        return {"error": str(e)}


async def fill_form_fields(
    fields: dict[str, str], submit_selector: Optional[str] = None, ctx: Optional[Context] = None
) -> dict[str, Any]:
    """
    Fill form fields on the current page

    Args:
        fields: Dictionary mapping field selectors to values
        submit_selector: Optional CSS selector for submit button
        ctx: The execution context

    Returns:
        Dictionary with form submission result
    """
    try:
        if ctx:
            await ctx.info(f"Filling {len(fields)} form fields")

        controller = await get_controller()
        success = await controller.fill_form(fields, submit_selector)

        result = {
            "success": success,
            "fields_filled": list(fields.keys()),
            "submitted": submit_selector is not None,
        }

        if ctx:
            if success:
                await ctx.success(
                    f"Form filled successfully{' and submitted' if submit_selector else ''}"
                )
            else:
                await ctx.error("Failed to fill form completely")

        return result
    except Exception as e:
        logger.error(f"Error in fill_form_fields: {e}")
        if ctx:
            await ctx.error(f"Error: {e!s}")
        return {"error": str(e)}


async def run_accessibility_test(ctx: Optional[Context] = None) -> dict[str, Any]:
    """
    Run accessibility tests on the current page

    Args:
        ctx: The execution context

    Returns:
        Dictionary with accessibility test results
    """
    try:
        if ctx:
            await ctx.info("Running accessibility tests...")

        controller = await get_controller()
        results = await controller.check_accessibility()

        # Get accessibility guidelines from resources
        resource_loader = get_resource_loader()
        guidelines = resource_loader.get_resource("accessibility_guidelines")

        issues_count = len(results.get("issues", []))

        result = {
            "success": "error" not in results,
            "results": results,
            "guidelines": guidelines.get("common_checks", []),
            "issues_count": issues_count,
        }

        if ctx:
            if "error" not in results:
                if issues_count > 0:
                    await ctx.warning(f"Found {issues_count} accessibility issues")
                else:
                    await ctx.success("No accessibility issues found")
            else:
                await ctx.error("Error running accessibility tests")

        return result
    except Exception as e:
        logger.error(f"Error in run_accessibility_test: {e}")
        if ctx:
            await ctx.error(f"Error: {e!s}")
        return {"error": str(e)}


async def run_responsive_test(ctx: Optional[Context] = None) -> dict[str, Any]:
    """
    Run responsive design tests on the current page

    Args:
        ctx: The execution context

    Returns:
        Dictionary with responsive test results
    """
    try:
        if ctx:
            await ctx.info("Running responsive design tests...")

        controller = await get_controller()

        # Get responsive breakpoints from resources
        resource_loader = get_resource_loader()
        testing_strategies = resource_loader.get_resource("testing_strategies")
        breakpoints = testing_strategies.get("responsive", {}).get(
            "breakpoints",
            [
                {"name": "Mobile Small", "width": 320, "height": 568},
                {"name": "Mobile Large", "width": 414, "height": 736},
                {"name": "Tablet", "width": 768, "height": 1024},
                {"name": "Desktop", "width": 1366, "height": 768},
            ],
        )

        if ctx:
            await ctx.info(f"Testing {len(breakpoints)} viewport sizes")

        results = await controller.check_responsive_design(breakpoints)

        issues_count = len(results.get("issues", []))

        result = {
            "success": "error" not in results,
            "results": results,
            "breakpoints_tested": [bp["name"] for bp in breakpoints],
            "issues_count": issues_count,
        }

        if ctx:
            if "error" not in results:
                if issues_count > 0:
                    await ctx.warning(f"Found {issues_count} responsive design issues")
                else:
                    await ctx.success("No responsive design issues found")
            else:
                await ctx.error("Error running responsive design tests")

        return result
    except Exception as e:
        logger.error(f"Error in run_responsive_test: {e}")
        if ctx:
            await ctx.error(f"Error: {e!s}")
        return {"error": str(e)}


async def run_security_test(ctx: Optional[Context] = None) -> dict[str, Any]:
    """
    Run basic security tests on the current page

    Args:
        ctx: The execution context

    Returns:
        Dictionary with security test results
    """
    try:
        if ctx:
            await ctx.info("Running security tests...")

        controller = await get_controller()
        results = await controller.run_security_checks()

        issues_count = len(results.get("issues", []))

        result = {
            "success": "error" not in results,
            "results": results,
            "issues_count": issues_count,
        }

        if ctx:
            if "error" not in results:
                if issues_count > 0:
                    await ctx.warning(f"Found {issues_count} security issues")
                else:
                    await ctx.success("No security issues found")
            else:
                await ctx.error("Error running security tests")

        return result
    except Exception as e:
        logger.error(f"Error in run_security_test: {e}")
        if ctx:
            await ctx.error(f"Error: {e!s}")
        return {"error": str(e)}


async def generate_test_report(
    test_type: str, url: str, ctx: Optional[Context] = None
) -> dict[str, Any]:
    """
    Generate a test report

    Args:
        test_type: Type of test ("exploratory", "accessibility", etc.)
        url: URL that was tested
        ctx: The execution context

    Returns:
        Dictionary with test report
    """
    try:
        if ctx:
            await ctx.info(f"Generating {test_type} test report for {url}...")

        controller = await get_controller()
        report = await controller.get_test_report(test_type, url)

        # Format the report using the template
        formatted_report = TEST_REPORT_TEMPLATE.format(
            test_type=report["test_type"],
            url=report["url"],
            summary=report["summary"],
            date=report["date"],
            browser=report["browser"],
            viewport=report["viewport"],
            device=report["device"],
            high_priority_issues=(
                "\n".join(report["high_priority_issues"])
                if report["high_priority_issues"]
                else "None found"
            ),
            medium_priority_issues=(
                "\n".join(report["medium_priority_issues"])
                if report["medium_priority_issues"]
                else "None found"
            ),
            low_priority_issues=(
                "\n".join(report["low_priority_issues"])
                if report["low_priority_issues"]
                else "None found"
            ),
            recommendations=(
                "\n".join(report["recommendations"])
                if report["recommendations"]
                else "No specific recommendations"
            ),
            screenshots=(
                "\n".join(report["screenshots"])
                if report["screenshots"]
                else "No screenshots captured"
            ),
            next_steps="\n".join(report["next_steps"]),
        )

        result = {
            "success": "error" not in report,
            "report": report,
            "formatted_report": formatted_report,
        }

        if ctx:
            if "error" not in report:
                await ctx.success("Test report generated successfully")
            else:
                await ctx.error("Error generating test report")

        return result
    except Exception as e:
        logger.error(f"Error in generate_test_report: {e}")
        if ctx:
            await ctx.error(f"Error: {e!s}")
        return {"error": str(e)}


async def prompt_for_credentials(
    site: str,
    username_field: Optional[str] = None,
    password_field: Optional[str] = None,
    ctx: Optional[Context] = None,
) -> dict[str, Any]:
    """
    Prompt the user for credentials

    Args:
        site: Site requiring authentication
        username_field: Selector for username field
        password_field: Selector for password field
        ctx: The execution context

    Returns:
        Dictionary with credential prompt
    """
    if ctx:
        await ctx.info(f"Requesting credentials for {site}...")

    return {
        "credential_prompt": {
            "site": site,
            "username_field": username_field,
            "password_field": password_field,
            "message": f"Please provide credentials for {site}",
        }
    }


async def run_exploratory_test(
    url: str, focus_area: str = "general", ctx: Optional[Context] = None
) -> dict[str, Any]:
    """
    Run an exploratory test on a website

    Args:
        url: URL to test
        focus_area: Area to focus on
        ctx: The execution context

    Returns:
        Dictionary with test prompt and initial results
    """
    try:
        if ctx:
            await ctx.info(
                f"Starting exploratory test on {url} (focus: {focus_area})..."
            )

        # Navigate to the URL
        controller = await get_controller()
        await controller.navigate(url)

        if ctx:
            await ctx.info("Taking initial screenshots...")

        # Take screenshots
        await controller.take_screenshot("initial_view", full_page=True)

        # Get testing strategies from resources
        resource_loader = get_resource_loader()
        testing_strategies = resource_loader.get_resource("testing_strategies")
        heuristics = resource_loader.get_resource("heuristics")

        # Format the prompt
        prompt = EXPLORATORY_TEST_PROMPT.format(url=url, focus_area=focus_area)

        title = await controller.page.title()

        if ctx:
            await ctx.success(f"Exploratory test setup complete for '{title}'")

        # Return the prompt and initial observations
        return {
            "success": True,
            "prompt": prompt,
            "url": url,
            "focus_area": focus_area,
            "initial_screenshot": (
                controller.screenshots[-1]["data"] if controller.screenshots else None
            ),
            "title": title,
            "testing_strategies": testing_strategies.get("exploratory", {}),
            "heuristics": heuristics.get("FEW HICCUPPS", {}).get("heuristics", []),
        }
    except Exception as e:
        logger.error(f"Error in run_exploratory_test: {e}")
        if ctx:
            await ctx.error(f"Error: {e!s}")
        return {"error": str(e)}


# Dictionary of functions to register with the main MCP instance
functions_to_register = {
    "navigate_to_url": navigate_to_url,
    "take_page_screenshot": take_page_screenshot,
    "take_element_screenshot": take_element_screenshot,
    "fill_login_form": fill_login_form,
    "detect_form_fields": detect_form_fields,
    "fill_form_fields": fill_form_fields,
    "run_accessibility_test": run_accessibility_test,
    "run_responsive_test": run_responsive_test,
    "run_security_test": run_security_test,
    "generate_test_report": generate_test_report,
    "prompt_for_credentials": prompt_for_credentials,
    "run_exploratory_test": run_exploratory_test,
}
