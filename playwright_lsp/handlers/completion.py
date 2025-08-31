# Simple version of completion.py that doesn't depend on pygls

# Define commonly used Playwright methods with descriptions and signature details
METHODS = [
    {
        "name": "goto",
        "description": "Navigate to a URL.",
        "signature": "goto(url: str, **kwargs) -> Response",
        "parameters": [
            {"name": "url", "type": "str", "description": "URL to navigate to"},
            {
                "name": "timeout",
                "type": "int",
                "description": "Maximum time in milliseconds",
            },
            {
                "name": "wait_until",
                "type": "str",
                "description": "When to consider navigation succeeded",
            },
        ],
    },
    {
        "name": "click",
        "description": "Click an element matching a selector.",
        "signature": "click(selector: str, **kwargs) -> None",
        "parameters": [
            {"name": "selector", "type": "str", "description": "Element selector"},
            {"name": "button", "type": "str", "description": "Mouse button to use"},
            {"name": "click_count", "type": "int", "description": "Number of clicks"},
        ],
    },
    {
        "name": "fill",
        "description": "Fill an input field.",
        "signature": "fill(selector: str, value: str, **kwargs) -> None",
        "parameters": [
            {
                "name": "selector",
                "type": "str",
                "description": "Input element selector",
            },
            {"name": "value", "type": "str", "description": "Value to fill"},
        ],
    },
    {
        "name": "locator",
        "description": "Return a Locator object.",
        "signature": "locator(selector: str) -> Locator",
        "parameters": [
            {"name": "selector", "type": "str", "description": "Element selector"}
        ],
    },
    {
        "name": "wait_for_selector",
        "description": "Wait for an element to appear.",
        "signature": "wait_for_selector(selector: str, **kwargs) -> ElementHandle",
        "parameters": [
            {"name": "selector", "type": "str", "description": "Element selector"},
            {
                "name": "timeout",
                "type": "int",
                "description": "Maximum time in milliseconds",
            },
            {"name": "state", "type": "str", "description": "Wait for element state"},
        ],
    },
    {
        "name": "screenshot",
        "description": "Take a screenshot.",
        "signature": "screenshot(**kwargs) -> bytes",
        "parameters": [
            {"name": "path", "type": "str", "description": "Path to save screenshot"},
            {"name": "full_page", "type": "bool", "description": "Capture full page"},
            {"name": "type", "type": "str", "description": "Image format (png/jpeg)"},
        ],
    },
    {
        "name": "type",
        "description": "Type text into a focused element.",
        "signature": "type(selector: str, text: str, **kwargs) -> None",
        "parameters": [
            {"name": "selector", "type": "str", "description": "Element selector"},
            {"name": "text", "type": "str", "description": "Text to type"},
            {
                "name": "delay",
                "type": "int",
                "description": "Delay between keystrokes in ms",
            },
        ],
    },
]


# Generate a list of completion items based on the methods
def get_playwright_completions():
    completion_items = []

    for method in METHODS:
        # Create detailed markdown documentation
        doc = f"### {method['name']}\n\n{method['description']}\n\n**Signature:** `{method['signature']}`\n\n**Parameters:**\n"

        # Add parameters documentation
        for param in method["parameters"]:
            doc += f"- `{param['name']}` ({param['type']}): {param['description']}\n"

        # Create completion item as a dictionary
        completion_items.append(
            {
                "label": method["name"],
                "kind": 2,  # Method kind
                "documentation": {"kind": "markdown", "value": doc},
                "detail": method["signature"],
            }
        )

    return completion_items
