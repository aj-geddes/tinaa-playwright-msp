"""
Accessibility Tool - Checks web page accessibility
"""

from typing import Any

from .tool_loader import PlaywrightTool


class AccessibilityTool(PlaywrightTool):
    """Tool for checking web page accessibility"""
    
    name = "accessibility"
    description = "Analyzes the current page for accessibility issues"
    
    @classmethod
    async def execute(cls, browser, page, params: dict[str, Any]) -> dict[str, Any]:
        """
        Analyze page for accessibility issues
        
        Args:
            browser: Playwright browser instance
            page: Playwright page instance
            params: Dictionary with parameters:
                - selector (optional): CSS selector to limit the scope of analysis
                
        Returns:
            Dictionary with accessibility data
        """
        selector = params.get("selector")
        
        # Get the accessibility snapshot
        if selector:
            element = await page.query_selector(selector)
            if not element:
                return {
                    "status": "error",
                    "message": f"Element not found: {selector}"
                }
            snapshot = await page.accessibility.snapshot(root=element)
        else:
            snapshot = await page.accessibility.snapshot()
        
        # Run basic accessibility checks
        issues = await cls._analyze_accessibility(page, selector)
        
        return {
            "status": "success",
            "snapshot": snapshot,
            "issues": issues,
            "selector": selector
        }
    
    @classmethod
    async def _analyze_accessibility(cls, page, selector: str = None) -> list[dict[str, Any]]:
        """Analyze the page for common accessibility issues"""
        issues = []
        
        # Check for images without alt text
        img_selector = f"{selector} img" if selector else "img"
        images = await page.query_selector_all(img_selector)
        
        for img in images:
            alt = await img.get_attribute("alt")
            if alt is None or alt.strip() == "":
                src = await img.get_attribute("src") or "unknown"
                issues.append({
                    "type": "missing_alt_text",
                    "element": "img",
                    "src": src,
                    "recommendation": "Add descriptive alt text to this image"
                })
        
        # Check for form inputs without labels
        input_selector = f"{selector} input" if selector else "input"
        inputs = await page.query_selector_all(input_selector)
        
        for input_el in inputs:
            input_id = await input_el.get_attribute("id")
            input_type = await input_el.get_attribute("type")
            
            # Skip hidden inputs and submit buttons
            if input_type in ["hidden", "submit", "button"]:
                continue
                
            if input_id:
                # Check if there's a label with a matching "for" attribute
                label = await page.query_selector(f'label[for="{input_id}"]')
                if not label:
                    issues.append({
                        "type": "missing_label",
                        "element": "input",
                        "id": input_id,
                        "type": input_type,
                        "recommendation": f"Add a label with for=\"{input_id}\" for this input"
                    })
        
        # Check for color contrast (simplified)
        # A comprehensive check would require more complex analysis
        
        return issues
