"""
Playwright Controller for Tinaa Playwright MSP

This module provides a controller for interacting with Playwright
"""

import asyncio
import base64
import logging
from typing import Any

from playwright.async_api import (
    Browser,
    BrowserContext,
    Page,
    Playwright,
    async_playwright,
)

logger = logging.getLogger("tinaa-playwright-msp.playwright-controller")


class PlaywrightController:
    """Controller for Playwright browser automation"""

    def __init__(self):
        self.playwright: Playwright | None = None
        self.browser: Browser | None = None
        self.context: BrowserContext | None = None
        self.page: Page | None = None
        self.is_initialized = False

        # Store screenshots for reporting
        self.screenshots: list[dict[str, Any]] = []

        # Store findings for reporting
        self.findings: dict[str, list[dict[str, Any]]] = {
            "high": [],
            "medium": [],
            "low": [],
            "info": [],
        }

    async def initialize(
        self,
        viewport_size: dict[str, int] = None,
        user_agent: str = None,
        locale: str = None,
    ) -> bool:
        """Initialize Playwright and browser"""
        try:
            # Launch Playwright
            self.playwright = await async_playwright().start()

            # Launch Chromium browser
            self.browser = await self.playwright.chromium.launch(
                headless=True,  # Run in headless mode (no visible browser window)
            )

            # Create browser context with viewport, user agent, locale
            context_params = {}

            if viewport_size:
                context_params["viewport"] = viewport_size

            if user_agent:
                context_params["user_agent"] = user_agent

            if locale:
                context_params["locale"] = locale

            self.context = await self.browser.new_context(**context_params)

            # Create page
            self.page = await self.context.new_page()

            # Set up page event listeners
            await self._setup_page_event_listeners()

            self.is_initialized = True
            logger.info("Playwright controller initialized")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize Playwright: {e}")
            return False

    async def _setup_page_event_listeners(self):
        """Set up event listeners for the page"""
        # Listen for console messages
        self.page.on(
            "console", lambda msg: logger.info(f"Console {msg.type}: {msg.text}")
        )

        # Listen for errors
        self.page.on("pageerror", lambda err: logger.error(f"Page error: {err}"))

        # Listen for dialogs (alerts, confirms, prompts)
        self.page.on(
            "dialog", lambda dialog: asyncio.create_task(self._handle_dialog(dialog))
        )

    async def _handle_dialog(self, dialog):
        """Handle browser dialogs (alerts, confirms, prompts)"""
        logger.info(f"Dialog: {dialog.type} - {dialog.message}")

        # Accept all dialogs by default
        await dialog.accept()

    async def close(self):
        """Close browser and Playwright"""
        if self.is_initialized:
            await self.context.close()
            await self.browser.close()
            await self.playwright.stop()

            self.page = None
            self.context = None
            self.browser = None
            self.playwright = None
            self.is_initialized = False

            logger.info("Playwright controller closed")

    async def navigate(self, url: str) -> bool:
        """Navigate to a URL"""
        if not self.is_initialized:
            logger.error("Playwright controller not initialized")
            return False

        try:
            response = await self.page.goto(url, wait_until="networkidle")
            logger.info(f"Navigated to {url}")

            # Take screenshot after navigation
            await self.take_screenshot("page_load")

            return response is not None and response.ok

        except Exception as e:
            logger.error(f"Failed to navigate to {url}: {e}")
            return False

    async def take_screenshot(
        self, name: str, selector: str = None, full_page: bool = False
    ) -> str | None:
        """Take a screenshot of the page or element"""
        if not self.is_initialized:
            logger.error("Playwright controller not initialized")
            return None

        try:
            if selector:
                # Take screenshot of specific element
                element = await self.page.query_selector(selector)
                if not element:
                    logger.error(f"Element not found: {selector}")
                    return None

                screenshot_bytes = await element.screenshot()
                screenshot_type = "element"
            else:
                # Take screenshot of the page
                screenshot_bytes = await self.page.screenshot(full_page=full_page)
                screenshot_type = "full_page" if full_page else "viewport"

            # Convert to base64
            screenshot_base64 = base64.b64encode(screenshot_bytes).decode("utf-8")

            # Add to screenshots list
            screenshot_info = {
                "name": name,
                "type": screenshot_type,
                "selector": selector,
                "data": screenshot_base64,
            }
            self.screenshots.append(screenshot_info)

            return screenshot_base64

        except Exception as e:
            logger.error(f"Failed to take screenshot: {e}")
            return None

    async def fill_form(
        self, fields: dict[str, str], submit_selector: str = None
    ) -> bool:
        """Fill a form with the given field values"""
        if not self.is_initialized:
            logger.error("Playwright controller not initialized")
            return False

        try:
            # Fill each field
            for selector, value in fields.items():
                await self.page.fill(selector, value)
                logger.info(f"Filled field {selector} with value")

            # Submit the form if a submit selector is provided
            if submit_selector:
                await self.page.click(submit_selector)
                logger.info(f"Clicked submit button: {submit_selector}")

                # Wait for navigation to complete
                await self.page.wait_for_load_state("networkidle")

                # Take screenshot after form submission
                await self.take_screenshot("form_submission")

            return True

        except Exception as e:
            logger.error(f"Failed to fill form: {e}")
            return False

    async def check_accessibility(self) -> dict[str, Any]:
        """Check accessibility of the page"""
        if not self.is_initialized:
            logger.error("Playwright controller not initialized")
            return {"error": "Playwright controller not initialized"}

        try:
            # Get accessibility snapshot
            snapshot = await self.page.accessibility.snapshot()

            # Run custom accessibility checks
            issues = await self._run_accessibility_checks()

            results = {"snapshot": snapshot, "issues": issues}

            # Add issues to findings
            for issue in issues:
                severity = issue.get("severity", "medium")
                self.findings[severity].append(
                    {
                        "type": "accessibility",
                        "description": issue.get("description", "Accessibility issue"),
                        "details": issue,
                    }
                )

            return results

        except Exception as e:
            logger.error(f"Failed to check accessibility: {e}")
            return {"error": str(e)}

    async def _run_accessibility_checks(self) -> list[dict[str, Any]]:
        """Run custom accessibility checks"""
        issues = []

        # Check for images without alt text
        no_alt_images = await self.page.evaluate(
            """
            () => {
                const images = Array.from(document.querySelectorAll('img'));
                return images
                    .filter(img => !img.hasAttribute('alt') || img.getAttribute('alt').trim() === '')
                    .map(img => ({
                        element: 'img',
                        src: img.getAttribute('src'),
                        location: {
                            x: img.getBoundingClientRect().x,
                            y: img.getBoundingClientRect().y
                        }
                    }));
            }
        """
        )

        for img in no_alt_images:
            issues.append(
                {
                    "type": "missing_alt_text",
                    "severity": "medium",
                    "description": "Image missing alt text",
                    "element": img,
                }
            )

        # Check for form inputs without labels
        unlabeled_inputs = await self.page.evaluate(
            """
            () => {
                const inputs = Array.from(document.querySelectorAll('input:not([type="hidden"]):not([type="submit"]):not([type="button"])'));
                return inputs
                    .filter(input => {
                        // Check for associated label
                        const id = input.getAttribute('id');
                        if (!id) return true; // No ID, can't have a label with 'for' attribute
                        
                        const hasLabel = document.querySelector(`label[for="${id}"]`);
                        const hasAriaLabel = input.hasAttribute('aria-label') && input.getAttribute('aria-label').trim() !== '';
                        const hasAriaLabelledBy = input.hasAttribute('aria-labelledby') && input.getAttribute('aria-labelledby').trim() !== '';
                        
                        return !hasLabel && !hasAriaLabel && !hasAriaLabelledBy;
                    })
                    .map(input => ({
                        element: 'input',
                        type: input.getAttribute('type') || 'text',
                        id: input.getAttribute('id'),
                        name: input.getAttribute('name'),
                        location: {
                            x: input.getBoundingClientRect().x,
                            y: input.getBoundingClientRect().y
                        }
                    }));
            }
        """
        )

        for input_el in unlabeled_inputs:
            issues.append(
                {
                    "type": "missing_label",
                    "severity": "medium",
                    "description": f"Input field missing label: {input_el.get('name') or input_el.get('id')}",
                    "element": input_el,
                }
            )

        # Additional accessibility checks can be added here

        return issues

    async def check_responsive_design(
        self, breakpoints: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """Check responsive design across multiple viewport sizes"""
        if not self.is_initialized:
            logger.error("Playwright controller not initialized")
            return {"error": "Playwright controller not initialized"}

        results = {"breakpoints": [], "issues": []}

        current_url = self.page.url

        for breakpoint in breakpoints:
            name = breakpoint.get("name", "Custom")
            width = breakpoint.get("width", 1280)
            height = breakpoint.get("height", 720)

            # Set viewport size
            await self.page.set_viewport_size({"width": width, "height": height})

            # Reload the page to ensure proper responsive behavior
            await self.page.goto(current_url, wait_until="networkidle")

            # Take screenshot at this breakpoint
            screenshot = await self.take_screenshot(f"breakpoint_{name}")

            # Check for layout issues
            layout_issues = await self._check_layout_issues()

            breakpoint_result = {
                "name": name,
                "width": width,
                "height": height,
                "screenshot": screenshot,
                "issues": layout_issues,
            }

            results["breakpoints"].append(breakpoint_result)

            # Add issues to the global issues list
            for issue in layout_issues:
                issue["breakpoint"] = name
                results["issues"].append(issue)

                # Add to findings
                self.findings["medium"].append(
                    {
                        "type": "responsive",
                        "description": f"Responsive issue at {name} breakpoint: {issue.get('description', 'Layout issue')}",
                        "details": issue,
                    }
                )

        return results

    async def _check_layout_issues(self) -> list[dict[str, Any]]:
        """Check for common layout issues"""
        issues = []

        # Check for horizontal overflow
        has_overflow = await self.page.evaluate(
            """
            () => {
                const body = document.body;
                const html = document.documentElement;
                const windowWidth = window.innerWidth;
                
                // Check if body or any direct children exceed viewport width
                const bodyWidth = body.scrollWidth;
                
                if (bodyWidth > windowWidth) {
                    return {
                        element: 'body',
                        bodyWidth: bodyWidth,
                        windowWidth: windowWidth,
                        difference: bodyWidth - windowWidth
                    };
                }
                
                // Check for elements that extend beyond viewport
                const allElements = Array.from(document.querySelectorAll('*'));
                const overflowingElements = allElements
                    .filter(el => {
                        const rect = el.getBoundingClientRect();
                        return rect.right > windowWidth + 5; // 5px tolerance
                    })
                    .map(el => ({
                        element: el.tagName.toLowerCase(),
                        class: el.className,
                        id: el.id,
                        width: el.getBoundingClientRect().width,
                        right: el.getBoundingClientRect().right,
                        windowWidth: windowWidth,
                        difference: el.getBoundingClientRect().right - windowWidth
                    }))
                    .slice(0, 5); // Limit to 5 examples
                
                return overflowingElements.length > 0 ? overflowingElements : null;
            }
        """
        )

        if has_overflow:
            if isinstance(has_overflow, dict):
                # Body overflow
                issues.append(
                    {
                        "type": "horizontal_overflow",
                        "severity": "medium",
                        "description": f"Page content overflows horizontally by {has_overflow.get('difference')}px",
                        "details": has_overflow,
                    }
                )
            elif isinstance(has_overflow, list):
                # Element overflow
                for element in has_overflow:
                    issues.append(
                        {
                            "type": "horizontal_overflow",
                            "severity": "medium",
                            "description": f"Element overflows horizontally by {element.get('difference')}px",
                            "details": element,
                        }
                    )

        # Check for tiny tap targets on mobile
        viewport_width = (await self.page.viewport_size())["width"]
        if viewport_width <= 768:  # Mobile viewport
            small_tap_targets = await self.page.evaluate(
                """
                () => {
                    const MIN_TAP_SIZE = 44; // Minimum recommended tap target size (pixels)
                    
                    // Get all interactive elements
                    const interactiveElements = Array.from(document.querySelectorAll('a, button, [role="button"], input, select, textarea'));
                    
                    return interactiveElements
                        .filter(el => {
                            const rect = el.getBoundingClientRect();
                            return (rect.width < MIN_TAP_SIZE || rect.height < MIN_TAP_SIZE) && 
                                   (rect.width > 0 && rect.height > 0); // Exclude hidden elements
                        })
                        .map(el => ({
                            element: el.tagName.toLowerCase(),
                            type: el.getAttribute('type'),
                            id: el.id,
                            class: el.className,
                            width: el.getBoundingClientRect().width,
                            height: el.getBoundingClientRect().height,
                            text: el.textContent.trim().substring(0, 20)
                        }))
                        .slice(0, 10); // Limit to 10 examples
                }
            """
            )

            for target in small_tap_targets:
                issues.append(
                    {
                        "type": "small_tap_target",
                        "severity": "medium",
                        "description": f"Tap target is too small: {target.get('width')}x{target.get('height')}px",
                        "details": target,
                    }
                )

        return issues

    async def test_login_form(
        self,
        username_selector: str,
        password_selector: str,
        submit_selector: str,
        username: str,
        password: str,
    ) -> dict[str, Any]:
        """Test a login form"""
        if not self.is_initialized:
            logger.error("Playwright controller not initialized")
            return {"error": "Playwright controller not initialized"}

        try:
            # Fill login form
            await self.fill_form(
                {username_selector: username, password_selector: password}
            )

            # Take screenshot before submission
            await self.take_screenshot("login_form_filled")

            # Submit the form
            await self.page.click(submit_selector)

            # Wait for navigation to complete
            await self.page.wait_for_load_state("networkidle")

            # Take screenshot after submission
            await self.take_screenshot("login_result")

            # Check for successful login
            # This is a simplified check - in reality, we'd need more sophisticated detection
            login_successful = await self._check_login_success()

            return {
                "success": login_successful,
                "current_url": self.page.url,
                "status": "login_successful" if login_successful else "login_failed",
            }

        except Exception as e:
            logger.error(f"Failed to test login form: {e}")
            return {"error": str(e)}

    async def _check_login_success(self) -> bool:
        """Check if login was successful"""
        # This is a simplified check - in reality, we'd need to adapt to different sites

        # Check for common logout links/buttons
        has_logout = await self.page.query_selector(
            'a:text("Logout"), a:text("Log out"), button:text("Logout"), button:text("Log out")'
        )
        if has_logout:
            return True

        # Check for common error messages
        has_error = await self.page.query_selector(
            'text="Invalid username", text="Invalid password", text="Login failed", text="Incorrect credentials"'
        )
        if has_error:
            return False

        # If we can't determine from obvious indicators, assume success if URL changed
        return True

    async def extract_form_fields(
        self, form_selector: str = None
    ) -> list[dict[str, Any]]:
        """Extract form fields from the page"""
        if not self.is_initialized:
            logger.error("Playwright controller not initialized")
            return []

        try:
            # Use JavaScript to extract form fields
            fields = await self.page.evaluate(
                f"""
                () => {{
                    const formEl = {f'document.querySelector("{form_selector}")' if form_selector else 'document.forms[0]'};
                    
                    if (!formEl) return [];
                    
                    return Array.from(formEl.elements)
                        .filter(el => el.tagName === 'INPUT' || el.tagName === 'SELECT' || el.tagName === 'TEXTAREA')
                        .filter(el => !['submit', 'button', 'image', 'reset', 'file', 'hidden'].includes(el.type))
                        .map(el => {{
                            const label = el.id ? document.querySelector(`label[for="${{el.id}}"]`) : null;
                            
                            return {{
                                type: el.type || 'text',
                                name: el.name,
                                id: el.id,
                                placeholder: el.placeholder,
                                label: label ? label.textContent.trim() : null,
                                required: el.required,
                                selector: el.id ? `#${{el.id}}` : `[name="${{el.name}}"]`,
                                tag: el.tagName.toLowerCase()
                            }};
                        }});
                }}
            """
            )

            return fields

        except Exception as e:
            logger.error(f"Failed to extract form fields: {e}")
            return []

    async def run_security_checks(self) -> dict[str, Any]:
        """Run basic security checks on the page"""
        if not self.is_initialized:
            logger.error("Playwright controller not initialized")
            return {"error": "Playwright controller not initialized"}

        results = {
            "transport_security": {},
            "content_security": {},
            "form_security": {},
            "issues": [],
        }

        try:
            # Check HTTPS
            current_url = self.page.url
            is_https = current_url.startswith("https://")
            results["transport_security"]["https"] = is_https

            if not is_https:
                self.findings["high"].append(
                    {
                        "type": "security",
                        "description": "Site is not using HTTPS",
                        "details": {"url": current_url},
                    }
                )
                results["issues"].append(
                    {
                        "severity": "high",
                        "description": "Site is not using HTTPS",
                        "recommendation": "Implement HTTPS for all pages",
                    }
                )

            # Check for security headers
            response = await self.page.goto(current_url)
            headers = response.headers

            # Check Content-Security-Policy
            has_csp = "content-security-policy" in headers
            results["content_security"]["csp"] = has_csp

            if not has_csp:
                self.findings["medium"].append(
                    {
                        "type": "security",
                        "description": "No Content Security Policy header",
                        "details": {"headers": list(headers.keys())},
                    }
                )
                results["issues"].append(
                    {
                        "severity": "medium",
                        "description": "No Content Security Policy header",
                        "recommendation": "Implement a Content Security Policy to prevent XSS attacks",
                    }
                )

            # Check X-Frame-Options
            has_x_frame_options = "x-frame-options" in headers
            results["content_security"]["x_frame_options"] = has_x_frame_options

            if not has_x_frame_options:
                self.findings["low"].append(
                    {
                        "type": "security",
                        "description": "No X-Frame-Options header",
                        "details": {"headers": list(headers.keys())},
                    }
                )
                results["issues"].append(
                    {
                        "severity": "low",
                        "description": "No X-Frame-Options header",
                        "recommendation": "Add X-Frame-Options header to prevent clickjacking attacks",
                    }
                )

            # Check for insecure form submission
            forms = await self.page.evaluate(
                """
                () => {
                    return Array.from(document.forms).map(form => ({
                        action: form.action,
                        method: form.method,
                        hasPassword: Array.from(form.elements).some(el => el.type === 'password')
                    }));
                }
            """
            )

            for form in forms:
                if form.get("hasPassword") and form.get("action", "").startswith(
                    "http:"
                ):
                    self.findings["high"].append(
                        {
                            "type": "security",
                            "description": "Password form submitting over HTTP",
                            "details": form,
                        }
                    )
                    results["issues"].append(
                        {
                            "severity": "high",
                            "description": "Password form submitting over HTTP",
                            "recommendation": "Use HTTPS for all forms with sensitive data",
                        }
                    )

            # More security checks can be added here

            return results

        except Exception as e:
            logger.error(f"Failed to run security checks: {e}")
            return {"error": str(e)}

    async def get_test_report(self, test_type: str, url: str) -> dict[str, Any]:
        """Generate a test report"""
        if not self.is_initialized:
            logger.error("Playwright controller not initialized")
            return {"error": "Playwright controller not initialized"}

        # Get browser and viewport info
        browser_info = await self.page.evaluate("() => navigator.userAgent")
        viewport_info = await self.page.viewport_size()

        # Format findings
        high_priority = [
            f"{i+1}. {issue['description']}"
            for i, issue in enumerate(self.findings["high"])
        ]
        medium_priority = [
            f"{i+1}. {issue['description']}"
            for i, issue in enumerate(self.findings["medium"])
        ]
        low_priority = [
            f"{i+1}. {issue['description']}"
            for i, issue in enumerate(self.findings["low"])
        ]

        # Generate recommendations based on findings
        recommendations = []
        if self.findings["high"]:
            recommendations.append("High Priority Fixes:")
            for issue in self.findings["high"]:
                if "recommendation" in issue:
                    recommendations.append(f"- {issue['recommendation']}")
                else:
                    recommendations.append(f"- Fix {issue['description']}")

        if self.findings["medium"]:
            recommendations.append("\nMedium Priority Improvements:")
            for issue in self.findings["medium"][:5]:  # Limit to top 5
                if "recommendation" in issue:
                    recommendations.append(f"- {issue['recommendation']}")
                else:
                    recommendations.append(f"- Address {issue['description']}")

        # Determine next steps
        next_steps = []
        if self.findings["high"] or self.findings["medium"]:
            next_steps.append(
                "1. Address the identified issues starting with high-priority items"
            )
            next_steps.append("2. Run focused tests on problematic areas after fixes")
        else:
            next_steps.append(
                "1. Run additional test types to ensure comprehensive coverage"
            )

        next_steps.append(
            "3. Consider implementing automated testing for regression prevention"
        )

        # Format screenshots for report
        screenshots_formatted = []
        for i, screenshot in enumerate(self.screenshots[:5]):  # Limit to 5 screenshots
            screenshots_formatted.append(
                f"{i+1}. {screenshot['name']} ({screenshot['type']})"
            )

        # Generate summary
        summary = f"Tested {url} using {test_type} methodology. "

        if (
            not self.findings["high"]
            and not self.findings["medium"]
            and not self.findings["low"]
        ):
            summary += "No issues were found."
        else:
            total_issues = (
                len(self.findings["high"])
                + len(self.findings["medium"])
                + len(self.findings["low"])
            )
            summary += f"Found {total_issues} issues ({len(self.findings['high'])} high, {len(self.findings['medium'])} medium, {len(self.findings['low'])} low priority)."

        # Assemble report
        report = {
            "test_type": test_type,
            "url": url,
            "summary": summary,
            "date": "2023-09-15",  # This would be the current date in production
            "browser": browser_info,
            "viewport": f"{viewport_info['width']}x{viewport_info['height']}",
            "device": "Desktop",  # This would be determined based on viewport and user agent
            "high_priority_issues": high_priority,
            "medium_priority_issues": medium_priority,
            "low_priority_issues": low_priority,
            "recommendations": recommendations,
            "screenshots": screenshots_formatted,
            "next_steps": next_steps,
            "raw_findings": self.findings,
            "raw_screenshots": self.screenshots,
        }

        return report
