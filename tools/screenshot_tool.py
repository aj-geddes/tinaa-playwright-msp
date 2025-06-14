"""
Screenshot Tool - Takes screenshots of web pages
"""

from typing import Dict, Any
from .tool_loader import PlaywrightTool

class ScreenshotTool(PlaywrightTool):
    """Tool for taking screenshots of web pages"""
    
    name = "screenshot"
    description = "Takes a screenshot of the current page or a specified element"
    
    @classmethod
    async def execute(cls, browser, page, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Take a screenshot of the page or element
        
        Args:
            browser: Playwright browser instance
            page: Playwright page instance
            params: Dictionary with parameters:
                - selector (optional): CSS selector for an element to screenshot
                - full_page (optional): Whether to take a full page screenshot
                
        Returns:
            Dictionary with screenshot data
        """
        selector = params.get("selector")
        full_page = params.get("full_page", False)
        
        if selector:
            # Take screenshot of specific element
            element = await page.query_selector(selector)
            if not element:
                return {
                    "status": "error",
                    "message": f"Element not found: {selector}"
                }
            
            screenshot = await element.screenshot()
        else:
            # Take screenshot of the page
            screenshot = await page.screenshot(full_page=full_page)
        
        # Convert bytes to base64 for transmission
        import base64
        screenshot_base64 = base64.b64encode(screenshot).decode("utf-8")
        
        return {
            "status": "success",
            "screenshot": screenshot_base64,
            "type": "image/png",
            "full_page": full_page,
            "selector": selector
        }
