# Simple version of diagnostics.py that doesn't depend on pygls
import ast


# Visitor class to find Playwright calls missing 'await'
class AwaitVisitor(ast.NodeVisitor):
    def __init__(self):
        self.diagnostics = []

    def visit_Call(self, node):
        if isinstance(node.func, ast.Attribute):
            # List of Playwright methods that should be awaited
            async_methods = {
                "goto", "click", "fill", "wait_for_selector", "wait_for_load_state", 
                "wait_for_navigation", "wait_for_function", "wait_for_url", 
                "screenshot", "type", "press", "check", "uncheck", "select_option",
                "evaluate", "evaluate_handle", "set_content", "focus", "hover", 
                "dispatch_event", "drag_and_drop"
            }
            
            if node.func.attr in async_methods:
                # Check if this call is awaited
                parent = getattr(node, 'parent', None)
                is_awaited = isinstance(parent, ast.Await)
                
                # Check if this call is part of a variable assignment
                # This could be a case where the result is saved for later use
                is_assigned = isinstance(parent, ast.Assign) or isinstance(parent, ast.AnnAssign)
                
                # Report only if not awaited and not assigned
                if not is_awaited and not is_assigned:
                    self.diagnostics.append((node.func.attr, node.lineno, node.col_offset))
                    
        self.generic_visit(node)

# Parse source code and report missing 'await' for async Playwright calls
def find_missing_awaits(code):
    diagnostics = []
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return diagnostics

    # Attach parent references to AST nodes
    for node in ast.walk(tree):
        for child in ast.iter_child_nodes(node):
            child.parent = node

    visitor = AwaitVisitor()
    visitor.visit(tree)

    for method, line, col in visitor.diagnostics:
        # Create a diagnostic dictionary instead of using Diagnostic class
        diagnostics.append({
            "message": f"Missing 'await' for '{method}'",
            "severity": 2,  # Warning severity
            "range": {
                "start": {"line": line - 1, "character": col},
                "end": {"line": line - 1, "character": col + len(method)}
            }
        })
    return diagnostics