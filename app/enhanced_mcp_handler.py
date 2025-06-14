#!/usr/bin/env python3
"""
Enhanced MCP handler with progress tracking integration
"""
import asyncio
import json
from typing import Dict, Any, Optional, Callable
from datetime import datetime
import logging

from progress_tracker import (
    ProgressTracker, 
    ExploratoryTestProgress,
    AccessibilityTestProgress,
    ProgressContext
)

# Import original handlers
from mcp_handler import (
    navigate_to_url as _navigate,
    take_page_screenshot as _screenshot,
    take_element_screenshot as _element_screenshot,
    fill_login_form as _fill_login,
    detect_form_fields as _detect_forms,
    fill_form_fields as _fill_forms,
    run_exploratory_test as _exploratory_test,
    run_accessibility_test as _accessibility_test,
    run_responsive_test as _responsive_test,
    run_security_test as _security_test,
    generate_test_report as _generate_report,
    prompt_for_credentials as _prompt_for_credentials,
    get_controller
)

logger = logging.getLogger("tinaa-enhanced")

# Global progress callback registry
_progress_callbacks: Dict[str, Callable] = {}

def register_progress_callback(client_id: str, callback: Callable):
    """Register a progress callback for a client"""
    _progress_callbacks[client_id] = callback

def unregister_progress_callback(client_id: str):
    """Unregister a progress callback for a client"""
    if client_id in _progress_callbacks:
        del _progress_callbacks[client_id]

async def get_progress_tracker(client_id: Optional[str] = None) -> ProgressTracker:
    """Get a progress tracker with appropriate callback"""
    callback = None
    if client_id and client_id in _progress_callbacks:
        callback = _progress_callbacks[client_id]
    return ProgressTracker(callback)

# Enhanced handlers with progress tracking

async def handle_navigate_to_url(url: str, client_id: Optional[str] = None) -> str:
    """Navigate to URL with progress tracking"""
    tracker = await get_progress_tracker(client_id)
    
    async with ProgressContext(tracker, "Navigation", total_steps=3) as ctx:
        await ctx.step(f"Preparing to navigate to {url}")
        
        result = await _navigate(url)
        
        await ctx.step("Navigation completed")
        await ctx.step("Page loaded and ready")
    
    return result

async def handle_run_exploratory_test(client_id: Optional[str] = None) -> str:
    """Run exploratory test with detailed progress tracking"""
    callback = _progress_callbacks.get(client_id) if client_id else None
    tracker = ExploratoryTestProgress(callback)
    
    try:
        # Get current page info
        controller = get_controller()
        page = controller.page if controller else None
        if page:
            url = page.url
            await tracker.navigation_started(url)
        
        await tracker.page_loaded()
        await tracker.analyzing_structure()
        
        # Simulate progress during test execution
        # In real implementation, this would hook into the actual test logic
        async def progress_wrapper():
            # Start the actual test
            test_task = asyncio.create_task(_exploratory_test())
            
            # Simulate progress updates
            elements_to_test = 10  # This would come from actual page analysis
            await tracker.testing_interactions(elements_to_test)
            
            for i in range(elements_to_test):
                if test_task.done():
                    break
                    
                await asyncio.sleep(0.5)  # Simulate testing time
                await tracker.element_tested(
                    f"element-{i}", 
                    i + 1, 
                    elements_to_test
                )
            
            # Wait for test to complete
            result = await test_task
            
            await tracker.generating_report()
            
            # Parse findings count from result
            findings_count = 0
            try:
                if "findings" in result:
                    findings_count = result.count("Finding:")
            except:
                pass
            
            await tracker.test_completed(findings_count)
            
            return result
        
        return await progress_wrapper()
        
    except Exception as e:
        await tracker.error(f"Exploratory test failed: {str(e)}")
        raise

async def handle_run_accessibility_test(client_id: Optional[str] = None) -> str:
    """Run accessibility test with detailed progress tracking"""
    callback = _progress_callbacks.get(client_id) if client_id else None
    tracker = AccessibilityTestProgress(callback)
    
    try:
        await tracker.info("Starting accessibility test", progress=10)
        await tracker.checking_wcag_compliance("2.1 AA")
        
        # Start the actual test asynchronously
        test_task = asyncio.create_task(_accessibility_test())
        
        # Simulate progress updates
        await asyncio.sleep(0.5)
        await tracker.testing_keyboard_navigation()
        
        await asyncio.sleep(0.5)
        await tracker.checking_aria_labels()
        
        await asyncio.sleep(0.5)
        await tracker.testing_color_contrast()
        
        # Wait for test completion
        result = await test_task
        
        # Parse results for issues
        if "missing alt text" in result.lower():
            await tracker.accessibility_issue_found("Missing alt text", "high")
        if "color contrast" in result.lower():
            await tracker.accessibility_issue_found("Low color contrast", "medium")
        
        await tracker.success("Accessibility test completed", progress=100)
        
        return result
        
    except Exception as e:
        await tracker.error(f"Accessibility test failed: {str(e)}")
        raise

async def handle_run_responsive_test(client_id: Optional[str] = None) -> str:
    """Run responsive test with progress tracking"""
    tracker = await get_progress_tracker(client_id)
    
    viewports = ["mobile", "tablet", "desktop"]
    
    async with ProgressContext(tracker, "Responsive Testing", total_steps=len(viewports)) as ctx:
        for viewport in viewports:
            await ctx.step(f"Testing {viewport} viewport")
            await asyncio.sleep(0.3)  # Simulate test time
        
        result = await _responsive_test()
        
    return result

async def handle_fill_form_fields(fields: Dict[str, str], client_id: Optional[str] = None) -> str:
    """Fill form fields with progress tracking"""
    tracker = await get_progress_tracker(client_id)
    
    field_count = len(fields)
    
    async with ProgressContext(tracker, "Form Filling", total_steps=field_count + 1) as ctx:
        await ctx.step("Analyzing form structure")
        
        # In real implementation, this would track each field as it's filled
        for field_name in fields:
            await ctx.step(f"Filling field: {field_name}")
        
        result = await _fill_forms(fields)
        
    return result

# Playbook execution with progress tracking

class PlaybookExecutor:
    """Execute playbooks with detailed progress tracking"""
    
    def __init__(self, client_id: str):
        self.client_id = client_id
        self.tracker = None
        
    async def execute(self, playbook: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a complete playbook"""
        callback = _progress_callbacks.get(self.client_id)
        self.tracker = ProgressTracker(callback)
        
        playbook_name = playbook.get("name", "Unnamed Playbook")
        steps = playbook.get("steps", [])
        
        await self.tracker.start_phase(f"Executing: {playbook_name}", len(steps))
        
        results = []
        
        for i, step in enumerate(steps):
            step_id = step.get("id", f"step-{i}")
            action = step.get("action")
            params = step.get("parameters", {})
            
            await self.tracker.info(
                f"Executing step {i+1}/{len(steps)}: {action}",
                progress=(i / len(steps)) * 100
            )
            
            try:
                result = await self._execute_step(action, params)
                results.append({
                    "step_id": step_id,
                    "action": action,
                    "status": "success",
                    "result": result
                })
                
                await self.tracker.success(f"Step {i+1} completed successfully")
                
            except Exception as e:
                await self.tracker.error(f"Step {i+1} failed: {str(e)}")
                results.append({
                    "step_id": step_id,
                    "action": action,
                    "status": "error",
                    "error": str(e)
                })
                
                # Decide whether to continue or abort
                if playbook.get("stop_on_error", True):
                    break
        
        await self.tracker.complete_phase(playbook_name)
        
        return {
            "playbook_id": playbook.get("id"),
            "name": playbook_name,
            "status": "completed",
            "results": results,
            "summary": self.tracker.get_summary()
        }
    
    async def _execute_step(self, action: str, params: Dict[str, Any]) -> Any:
        """Execute a single playbook step"""
        # Map actions to enhanced handlers
        action_map = {
            "navigate": lambda: handle_navigate_to_url(
                params.get("url"), self.client_id
            ),
            "screenshot": lambda: handle_take_page_screenshot(
                params.get("full_page", True), self.client_id
            ),
            "fill_form": lambda: handle_fill_form_fields(
                params.get("fields", {}), self.client_id
            ),
            "test_exploratory": lambda: handle_run_exploratory_test(self.client_id),
            "test_accessibility": lambda: handle_run_accessibility_test(self.client_id),
            "test_responsive": lambda: handle_run_responsive_test(self.client_id),
            "test_security": lambda: handle_run_security_test(self.client_id),
        }
        
        if action not in action_map:
            raise ValueError(f"Unknown action: {action}")
        
        return await action_map[action]()

# Additional wrapper functions for other handlers

async def handle_take_page_screenshot(full_page: bool = True, client_id: Optional[str] = None) -> str:
    """Take page screenshot with progress tracking"""
    tracker = await get_progress_tracker(client_id)
    
    async with ProgressContext(tracker, "Screenshot Capture") as ctx:
        await ctx.step("Preparing screenshot")
        result = await _screenshot(full_page)
        await ctx.step("Screenshot captured successfully")
    
    return result

async def handle_run_security_test(client_id: Optional[str] = None) -> str:
    """Run security test with progress tracking"""
    tracker = await get_progress_tracker(client_id)
    
    async with ProgressContext(tracker, "Security Testing", total_steps=4) as ctx:
        await ctx.step("Checking HTTPS configuration")
        await ctx.step("Analyzing security headers")
        await ctx.step("Testing form submissions")
        await ctx.step("Checking for common vulnerabilities")
        
        result = await _security_test()
    
    return result

async def handle_generate_test_report(client_id: Optional[str] = None) -> str:
    """Generate test report with progress tracking"""
    tracker = await get_progress_tracker(client_id)
    
    async with ProgressContext(tracker, "Report Generation", total_steps=3) as ctx:
        await ctx.step("Collecting test results")
        await ctx.step("Analyzing findings")
        await ctx.step("Generating report")
        
        result = await _generate_report()
    
    return result