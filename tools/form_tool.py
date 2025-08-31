"""
Form Tool - Interacts with forms on web pages
"""

from typing import Any

from .tool_loader import PlaywrightTool


class FormTool(PlaywrightTool):
    """Tool for interacting with forms on web pages"""

    name = "form"
    description = "Fills and submits forms on web pages"

    @classmethod
    async def execute(cls, browser, page, params: dict[str, Any]) -> dict[str, Any]:
        """
        Fill and optionally submit a form

        Args:
            browser: Playwright browser instance
            page: Playwright page instance
            params: Dictionary with parameters:
                - form_selector (optional): CSS selector for the form
                - fields: Dictionary mapping field selectors to values
                - submit (optional): Whether to submit the form after filling
                - submit_selector (optional): CSS selector for the submit button

        Returns:
            Dictionary with form submission result
        """
        form_selector = params.get("form_selector")
        fields = params.get("fields", {})
        submit = params.get("submit", False)
        submit_selector = params.get("submit_selector")

        if not fields:
            return {
                "status": "error",
                "message": "No fields specified for form filling",
            }

        # Check if form exists if selector provided
        if form_selector:
            form = await page.query_selector(form_selector)
            if not form:
                return {
                    "status": "error",
                    "message": f"Form not found: {form_selector}",
                }

        # Fill the form fields
        filled_fields = []
        failed_fields = []

        for selector, value in fields.items():
            try:
                await page.fill(selector, value)
                filled_fields.append(selector)
            except Exception as e:
                failed_fields.append({"selector": selector, "error": str(e)})

        # Submit the form if requested
        if submit:
            if submit_selector:
                try:
                    await page.click(submit_selector)
                except Exception as e:
                    return {
                        "status": "error",
                        "message": f"Failed to click submit button: {e!s}",
                        "filled_fields": filled_fields,
                        "failed_fields": failed_fields,
                    }
            else:
                # Try to find a submit button in the form
                if form_selector:
                    submit_button = await page.query_selector(
                        f"{form_selector} [type=submit]"
                    )
                else:
                    submit_button = await page.query_selector("[type=submit]")

                if submit_button:
                    await submit_button.click()
                # Try to submit the form via JavaScript
                elif form_selector:
                    await page.evaluate(
                        f"document.querySelector('{form_selector}').submit()"
                    )
                else:
                    return {
                        "status": "error",
                        "message": "Could not find a way to submit the form",
                        "filled_fields": filled_fields,
                        "failed_fields": failed_fields,
                    }

        return {
            "status": "success",
            "filled_fields": filled_fields,
            "failed_fields": failed_fields,
            "submitted": submit,
        }
