"""
Tool loader for Tinaa Playwright MSP

This module loads all tools from the tools directory
"""

import importlib
import inspect
import logging
import os
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("tinaa-playwright-msp.tools")

class PlaywrightTool:
    """Base class for Playwright tools"""
    
    name: str = "base_tool"
    description: str = "Base tool class"
    
    @classmethod
    async def execute(cls, browser, page, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the tool with Playwright browser and page"""
        raise NotImplementedError("Tool must implement execute method")

def load_tools() -> Dict[str, PlaywrightTool]:
    """Load all tools from the tools directory"""
    tools = {}
    tools_dir = Path(__file__).parent
    
    # Get all Python files in the tools directory
    tool_files = [f for f in os.listdir(tools_dir) if f.endswith(".py") and f != "__init__.py" and f != "tool_loader.py"]
    
    for tool_file in tool_files:
        module_name = tool_file[:-3]  # Remove .py extension
        try:
            # Import the module
            module = importlib.import_module(f"tools.{module_name}")
            
            # Find all PlaywrightTool subclasses in the module
            for name, obj in inspect.getmembers(module):
                if (inspect.isclass(obj) and 
                    issubclass(obj, PlaywrightTool) and 
                    obj is not PlaywrightTool):
                    tools[obj.name] = obj
                    logger.info(f"Loaded tool: {obj.name}")
        except Exception as e:
            logger.error(f"Error loading tool {module_name}: {e}")
    
    return tools
