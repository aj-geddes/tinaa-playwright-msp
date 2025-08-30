#!/usr/bin/env python3
"""
TINAA - Testing Intelligence Network Automation Assistant - MCP Integration with Playwright
"""
import io
import logging
import os
import threading
from contextlib import redirect_stderr, redirect_stdout
from typing import Any

from fastmcp import Context, FastMCP

# Configure logging to use a file instead of stdout to avoid breaking MCP
os.makedirs("logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler("logs/app_main.log"),
    ],
)
logger = logging.getLogger("tinaa-mcp")

# Initialize the MCP server
mcp = FastMCP("TINAA - Testing Intelligence Network Automation Assistant")

# We'll import and register the handler functions after defining mcp


@mcp.tool()
async def start_lsp_server(
    tcp: bool = False, port: int = 8765, ctx: Context = None
) -> str:
    """
    Start TINAA's Playwright Language Server Protocol (LSP) server for IDE integration.

    Launches a Playwright LSP server that provides intelligent code completion, diagnostics,
    and hover information for Playwright test code directly in your IDE.

    Args:
        tcp: Whether to use TCP mode (True) instead of stdio mode (False). TCP mode is recommended for MCP integration
        port: Port number for TCP mode server (default: 8765)
        ctx: Execution context (automatically provided by FastMCP)

    Returns:
        Status message indicating success or failure of server startup

    Note:
        - TCP mode is required for MCP integration with IDEs
        - The LSP server provides Playwright-specific IntelliSense and error detection
        - Server runs in a background thread to avoid blocking MCP operations

    Example:
        >>> result = await start_lsp_server(tcp=True, port=8765)
        >>> print(result)
        "LSP server started successfully"
    """
    if ctx:
        await ctx.info("Starting Playwright LSP server...")

    logger.info(f"Starting LSP server (TCP: {tcp}, Port: {port})")

    # Capture stdout/stderr to prevent it from breaking MCP JSON
    with io.StringIO() as buf, redirect_stdout(buf), redirect_stderr(buf):
        try:
            if tcp:
                if ctx:
                    await ctx.info(f"Using TCP mode on port {port}")

                # Import here to avoid any accidental stdout
                from playwright_lsp.server import server as lsp_server

                # Start in a separate thread to not block
                def start_server():
                    try:
                        with redirect_stdout(
                            open("logs/lsp_server.log", "w")
                        ), redirect_stderr(open("logs/lsp_server_error.log", "w")):
                            lsp_server.start_tcp("localhost", port)
                    except Exception as e:
                        logger.error(f"Error in LSP server thread: {e}")

                thread = threading.Thread(target=start_server, daemon=True)
                thread.start()

                logger.info("LSP server started in background thread")
                return "LSP server started successfully"
            if ctx:
                await ctx.info("Using standard IO mode")
            # We can't really use this mode from MCP
            return "Standard IO mode not supported for MCP integration. Use TCP mode instead."
        except Exception as e:
            error_msg = f"Failed to start LSP server: {e!s}"
            logger.error(error_msg)
            if ctx:
                await ctx.error(error_msg)
            return error_msg


@mcp.tool()
async def test_browser_connectivity(
    url: str = "https://example.com", ctx: Context = None
) -> dict[str, Any]:
    """
    Test TINAA's browser automation capabilities by visiting a URL and capturing basic information.

    Verifies that Playwright browser automation is working correctly by navigating to a URL,
    capturing the page title, taking a screenshot, and reporting the results.

    Args:
        url: The URL to visit for testing browser connectivity (default: "https://example.com")
        ctx: Execution context (automatically provided by FastMCP)

    Returns:
        Dictionary containing:
        - success: Boolean indicating if the test passed
        - url: The URL that was tested
        - title: Page title from the visited URL
        - status: HTTP status code of the response
        - screenshot: Base64-encoded screenshot of the page
        - error: Error message if the test failed

    This tool is useful for:
        - Verifying TINAA's browser automation setup
        - Testing network connectivity and proxy settings
        - Validating that Playwright can launch browsers successfully
        - Getting a quick visual confirmation of a webpage

    Example:
        >>> result = await test_browser_connectivity("https://playwright.dev")
        >>> print(f"Page title: {result['title']}")
        "Page title: Playwright"
        >>> print(f"Success: {result['success']}")
        "Success: True"
    """
    if ctx:
        await ctx.info(f"Testing browser connectivity to {url}...")

    try:
        from playwright.async_api import async_playwright

        async with async_playwright() as p:
            # Launch browser
            browser = await p.chromium.launch()

            # Create new page
            page = await browser.new_page()

            # Visit URL
            response = await page.goto(url)

            # Get page information
            title = await page.title()
            status = response.status if response else None

            # Take a screenshot
            screenshot_bytes = await page.screenshot()
            import base64

            screenshot_base64 = base64.b64encode(screenshot_bytes).decode("utf-8")

            # Close browser
            await browser.close()

            result = {
                "success": True,
                "url": url,
                "title": title,
                "status": status,
                "screenshot": screenshot_base64,
            }

            if ctx:
                await ctx.success(
                    f"Successfully connected to {url}, page title: {title}"
                )

            return result

    except Exception as e:
        error_msg = f"Browser connectivity test failed: {e!s}"
        logger.error(error_msg)

        if ctx:
            await ctx.error(error_msg)

        return {"success": False, "url": url, "error": str(e)}


@mcp.tool()
async def analyze_script(script_path: str, ctx: Context = None) -> dict:
    """
    Analyze a Playwright test script for common issues, errors, and improvement opportunities.

    Performs static analysis on your Playwright test code to identify missing await statements,
    syntax issues, and potential improvements. Uses TINAA's built-in diagnostics engine.

    Args:
        script_path: Absolute path to the Playwright test script file to analyze (e.g., "/path/to/test.spec.ts")
        ctx: Execution context (automatically provided by FastMCP)

    Returns:
        Dictionary containing:
        - script_path: The path to the analyzed script
        - issues_found: Number of issues detected
        - diagnostics: List of specific issues with details including:
          - message: Description of the issue
          - line: Line number where the issue occurs
          - character: Character position on the line
          - severity: Issue severity level ("Warning", "Error", "Info")
        - suggestions: Recommended fixes for identified issues

    Common issues detected:
        - Missing await statements for async Playwright operations
        - Incorrect selector usage
        - Potential timing issues
        - Best practice violations

    Example:
        >>> analysis = await analyze_script("/workspace/tests/login.spec.ts")
        >>> print(f"Found {analysis['issues_found']} issues")
        "Found 3 issues"
        >>> for issue in analysis['diagnostics']:
        ...     print(f"Line {issue['line']}: {issue['message']}")
        "Line 15: Missing await before page.click()"
        "Line 22: Consider using page.waitForSelector()"
    """
    if ctx:
        await ctx.info(f"Analyzing script: {script_path}")

    logger.info(f"Analyzing script: {script_path}")

    try:
        with open(script_path) as f:
            content = f.read()

        # Use regex-based diagnostics
        from playwright_lsp.handlers.regex_diagnostics import find_missing_awaits

        diagnostics = find_missing_awaits(content)

        result = {
            "script_path": script_path,
            "issues_found": len(diagnostics),
            "diagnostics": [
                {
                    "message": diag["message"],
                    "line": diag["range"]["start"]["line"] + 1,
                    "character": diag["range"]["start"]["character"],
                    "severity": "Warning",
                }
                for diag in diagnostics
            ],
        }

        logger.info(f"Analysis complete. Found {len(diagnostics)} issues.")
        if ctx:
            await ctx.info(f"Analysis complete. Found {len(diagnostics)} issues.")

        return result
    except Exception as e:
        error_msg = f"Failed to analyze script: {e!s}"
        logger.error(f"Error: {error_msg}")
        if ctx:
            await ctx.error(error_msg)
        return {"error": error_msg}


@mcp.resource("playwright://docs/{method}")
def get_playwright_docs(method: str) -> str:
    """
    Get documentation for a Playwright method.

    Args:
        method: Name of the Playwright method

    Returns:
        Documentation for the method
    """
    # Basic documentation for common Playwright methods
    playwright_docs = {
        "goto": "Navigates to the URL and waits for the page to load.",
        "click": "Clicks on an element matching the selector.",
        "fill": "Fills a form field with the provided value.",
        "wait_for_selector": "Waits for an element matching the selector to appear.",
        "screenshot": "Takes a screenshot of the page or an element.",
        "type": "Types text into the focused element.",
        "press": "Presses a key on the keyboard.",
        "check": "Checks a checkbox or radio button.",
        "uncheck": "Unchecks a checkbox.",
        "select_option": "Selects an option in a dropdown.",
        "evaluate": "Evaluates JavaScript in the page context.",
        "evaluate_handle": "Evaluates JavaScript and returns a JSHandle.",
        "set_content": "Sets the HTML content of the page.",
        "focus": "Focuses an element matching the selector.",
        "hover": "Hovers over an element matching the selector.",
        "dispatch_event": "Dispatches an event on an element.",
        "drag_and_drop": "Performs a drag and drop operation.",
    }

    return playwright_docs.get(method, f"Documentation for {method} not found.")


# Import handler functions and register them
from app.mcp_handler import (
    detect_form_fields,
    fill_form_fields,
    fill_login_form,
    generate_test_report,
    navigate_to_url,
    prompt_for_credentials,
    run_accessibility_test,
    run_exploratory_test,
    run_responsive_test,
    run_security_test,
    take_element_screenshot,
    take_page_screenshot,
)

# Register all handler functions with our mcp instance
for func in [
    navigate_to_url,
    take_page_screenshot,
    take_element_screenshot,
    fill_login_form,
    detect_form_fields,
    fill_form_fields,
    run_accessibility_test,
    run_responsive_test,
    run_security_test,
    generate_test_report,
    prompt_for_credentials,
    run_exploratory_test,
]:
    mcp.tool()(func)

# Log successful initialization
logger.info("MCP server initialized with Playwright browser tools")
