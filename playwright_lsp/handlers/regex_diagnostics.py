# Regex-based version of diagnostics.py for JavaScript
import re

def find_missing_awaits(code):
    """Find missing await keywords in Playwright test code using regex"""
    diagnostics = []
    
    # List of Playwright methods that should be awaited
    async_methods = [
        "goto", "click", "fill", "wait_for_selector", "wait_for_load_state", 
        "wait_for_navigation", "wait_for_function", "wait_for_url", 
        "screenshot", "type", "press", "check", "uncheck", "select_option",
        "evaluate", "evaluate_handle", "set_content", "focus", "hover", 
        "dispatch_event", "drag_and_drop"
    ]
    
    # Compile regex patterns
    # Pattern for method calls without await
    method_pattern = r'(?<!\bawait\s+)(?<!\.\s*then\s*\()(?<!\.\s*catch\s*\()(page|browser|context|element|locator)\.({})\s*\('.format('|'.join(async_methods))
    
    # Pattern for async function declaration
    async_pattern = r'\basync\b'
    
    # Split code into lines for accurate line numbers
    lines = code.split('\n')
    
    # Track if we're in an async function
    in_async_func = False
    brace_count = 0
    
    for line_num, line in enumerate(lines):
        # Check if this line contains an async function declaration
        if re.search(async_pattern, line):
            in_async_func = True
            brace_count += line.count('{')
        
        # Track braces to know when we leave the async function
        if in_async_func:
            brace_count += line.count('{')
            brace_count -= line.count('}')
            if brace_count <= 0:
                in_async_func = False
        
        # Only look for missing awaits inside async functions
        if in_async_func:
            # Find all method calls that should be awaited
            for match in re.finditer(method_pattern, line):
                obj_name = match.group(1)  # page, browser, etc.
                method_name = match.group(2)  # click, goto, etc.
                col = match.start()
                
                # Add a diagnostic for this missing await
                diagnostics.append({
                    "message": f"Missing 'await' for '{method_name}'",
                    "severity": 2,  # Warning severity
                    "range": {
                        "start": {"line": line_num, "character": col},
                        "end": {"line": line_num, "character": col + len(method_name) + len(obj_name) + 1}
                    }
                })
    
    return diagnostics
