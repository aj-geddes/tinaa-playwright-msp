"""
Example Playwright test script with intentional issues for testing the analyzer.
"""

from playwright.sync_api import Page


async def test_missing_await(page: Page):
    # This will be detected as missing await
    page.goto("https://example.com")

    # This is correct
    await page.click(".submit-button")

    # This will be detected as missing await
    page.fill("input#search", "test query")

    # This is correct
    element = page.locator(".results")

    # This is correct
    await page.wait_for_selector(".result-item")

    # This will be detected as missing await
    page.screenshot(path="screenshot.png")
