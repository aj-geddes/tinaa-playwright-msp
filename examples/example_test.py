"""
Example Playwright test script.
This file demonstrates how TINAA LSP would provide assistance.
"""
from playwright.sync_api import Page


async def test_example(page: Page):
    # LSP will provide completion for 'goto'
    await page.goto("https://example.com")
    
    # LSP will provide hover documentation for 'click'
    await page.click("button.submit")
    
    # LSP will warn about missing 'await' here
    page.fill("input#search", "test query")
    
    # LSP will provide completion for 'locator'
    element = page.locator("div.results")
    
    # LSP will provide hover documentation for 'wait_for_selector'
    await page.wait_for_selector(".result-item")