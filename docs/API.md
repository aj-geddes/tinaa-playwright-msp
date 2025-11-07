# TINAA API Documentation

## Overview

TINAA provides three different API interfaces for browser automation and testing:

1. **MCP (Model Context Protocol)** - For AI assistants like Claude
2. **HTTP REST API** - Traditional REST endpoints with WebSocket support
3. **LSP (Language Server Protocol)** - For IDE integration

> **⚠️ Documentation Updated (2025-11-07)**
> This documentation has been corrected to match the actual implementation.
> Previous version had significant discrepancies. See [API_AUDIT_REPORT.md](API_AUDIT_REPORT.md) for details.

---

## MCP Tools API

TINAA provides **15 MCP tools** for browser automation and testing. All tools are defined in `app/main.py` and `app/mcp_handler.py`.

### Tool Categories

| Category | Tools | Count |
|----------|-------|-------|
| **Diagnostics** | start_lsp_server, check_browser_connectivity, analyze_script | 3 |
| **Navigation** | navigate_to_url | 1 |
| **Screenshots** | take_page_screenshot, take_element_screenshot | 2 |
| **Form Automation** | fill_login_form, detect_form_fields, fill_form_fields | 3 |
| **Testing** | run_exploratory_test, run_accessibility_test, run_responsive_test, run_security_test | 4 |
| **Reporting** | generate_test_report, prompt_for_credentials | 2 |

---

## Diagnostic Tools

### start_lsp_server

Starts the Playwright Language Server Protocol server for IDE integration.

```python
@mcp.tool()
async def start_lsp_server(
    tcp: bool = False,
    port: int = 8765,
    ctx: Optional[Context] = None
) -> str
```

**Parameters:**
- `tcp` (bool): Use TCP mode instead of stdio (default: False)
- `port` (int): Port number for TCP mode (default: 8765)
- `ctx` (Optional[Context]): Execution context

**Returns:** Status message string

**Example:**
```python
result = await start_lsp_server(tcp=True, port=8765)
print(result)  # "LSP server started successfully"
```

---

### check_browser_connectivity

Tests browser automation connectivity and capabilities.

```python
@mcp.tool()
async def check_browser_connectivity(
    url: str = "https://example.com",
    ctx: Optional[Context] = None
) -> dict[str, Any]
```

**Parameters:**
- `url` (str): URL to test connectivity with (default: "https://example.com")
- `ctx` (Optional[Context]): Execution context

**Returns:** Dictionary containing:
- `success` (bool): Whether browser automation is working
- `url` (str): The tested URL
- `title` (str): Page title
- `status` (int): HTTP status code
- `screenshot` (str): Base64-encoded PNG screenshot
- `error` (str): Error message if failed

**Example:**
```python
result = await check_browser_connectivity("https://playwright.dev")
if result["success"]:
    print(f"✓ Browser working - Title: {result['title']}")
    print(f"  HTTP Status: {result['status']}")
```

---

### analyze_script

Analyzes a Playwright test script for common issues and improvement opportunities.

```python
@mcp.tool()
async def analyze_script(
    script_path: str,
    ctx: Optional[Context] = None
) -> dict
```

**Parameters:**
- `script_path` (str): Absolute path to the Playwright test script file
- `ctx` (Optional[Context]): Execution context

**Returns:** Dictionary containing:
- `script_path` (str): Path to analyzed script
- `issues_found` (int): Number of issues detected
- `diagnostics` (list): List of issues with line numbers, messages, and severity
- `error` (str): Error message if failed

**Example:**
```python
result = await analyze_script("/workspace/tests/login.spec.ts")
print(f"Found {result['issues_found']} issues")
for issue in result['diagnostics']:
    print(f"Line {issue['line']}: {issue['message']}")
```

---

## Navigation Tools

### navigate_to_url

Navigates the browser to a specified URL and captures page information.

```python
@mcp.tool()
async def navigate_to_url(
    url: str,
    ctx: Optional[Context] = None
) -> dict[str, Any]
```

**Parameters:**
- `url` (str): The URL to navigate to (must start with http:// or https://)
- `ctx` (Optional[Context]): Execution context

**Returns:** Dictionary containing:
- `success` (bool): Whether navigation succeeded
- `url` (str): The requested URL
- `current_url` (str): Actual URL after redirects
- `title` (str): Page title
- `error` (str): Error message if failed

**Example:**
```python
result = await navigate_to_url("https://example.com")
if result["success"]:
    print(f"Navigated to: {result['title']}")
```

---

## Screenshot Tools

### take_page_screenshot

Takes a PNG screenshot of the current page.

```python
@mcp.tool()
async def take_page_screenshot(
    full_page: bool = False,
    ctx: Optional[Context] = None
) -> dict[str, Any]
```

**Parameters:**
- `full_page` (bool): If True, captures entire page by scrolling. If False, captures only viewport (default: False)
- `ctx` (Optional[Context]): Execution context

**Returns:** Dictionary containing:
- `success` (bool): Whether screenshot was captured
- `screenshot` (str): Base64-encoded PNG image data
- `type` (str): MIME type ("image/png")
- `full_page` (bool): Whether full page was captured
- `error` (str): Error message if failed

**Example:**
```python
result = await take_page_screenshot(full_page=True)
if result["success"]:
    import base64
    with open("screenshot.png", "wb") as f:
        f.write(base64.b64decode(result["screenshot"]))
```

---

### take_element_screenshot

Takes a screenshot of a specific element on the page.

```python
@mcp.tool()
async def take_element_screenshot(
    selector: str,
    ctx: Optional[Context] = None
) -> dict[str, Any]
```

**Parameters:**
- `selector` (str): CSS selector for the target element (e.g., "#main-content", ".header")
- `ctx` (Optional[Context]): Execution context

**Returns:** Dictionary containing:
- `success` (bool): Whether screenshot was captured
- `screenshot` (str): Base64-encoded PNG image data of the element
- `type` (str): MIME type ("image/png")
- `selector` (str): The CSS selector used
- `error` (str): Error message if failed

**Example:**
```python
result = await take_element_screenshot("#main-content")
if result["success"]:
    print(f"Captured element: {result['selector']}")
```

---

## Form Automation Tools

### fill_login_form

Fills and submits a login form with credentials.

```python
@mcp.tool()
async def fill_login_form(
    username_selector: str,
    password_selector: str,
    submit_selector: str,
    username: str,
    password: str,
    ctx: Optional[Context] = None
) -> dict[str, Any]
```

**Parameters:**
- `username_selector` (str): CSS selector for username/email input field
- `password_selector` (str): CSS selector for password input field
- `submit_selector` (str): CSS selector for submit button
- `username` (str): Username or email to enter
- `password` (str): Password to enter
- `ctx` (Optional[Context]): Execution context

**Returns:** Dictionary containing:
- `success` (bool): Whether form was filled and submitted
- `username_selector` (str): Username field selector used
- `password_selector` (str): Password field selector used
- `submit_selector` (str): Submit button selector used
- `url_after_submit` (str): URL after form submission
- `error` (str): Error message if failed

**Example:**
```python
result = await fill_login_form(
    username_selector="#username",
    password_selector="#password",
    submit_selector="button[type='submit']",
    username="testuser",
    password="testpass123"
)
print(result["success"])  # True
```

**Note:** For security testing purposes only. Never use real credentials in tests.

---

### detect_form_fields

Detects and analyzes form fields on the current page.

```python
@mcp.tool()
async def detect_form_fields(
    form_selector: Optional[str] = None,
    ctx: Optional[Context] = None
) -> dict[str, Any]
```

**Parameters:**
- `form_selector` (Optional[str]): CSS selector for a specific form. If None, detects all forms
- `ctx` (Optional[Context]): Execution context

**Returns:** Dictionary containing:
- `success` (bool): Whether fields were detected
- `fields` (list): List of detected form fields with metadata
- `count` (int): Number of fields detected
- `form_selector` (str): The form selector used
- `error` (str): Error message if failed

**Example:**
```python
await navigate_to_url("https://example.com/contact")
result = await detect_form_fields()
if result["success"]:
    print(f"Found {result['count']} form fields")
    for field in result['fields']:
        print(f"  - {field['name']}: {field['type']}")
```

---

### fill_form_fields

Fills multiple form fields on the current page.

```python
@mcp.tool()
async def fill_form_fields(
    fields: dict[str, str],
    submit_selector: Optional[str] = None,
    ctx: Optional[Context] = None
) -> dict[str, Any]
```

**Parameters:**
- `fields` (dict[str, str]): Dictionary mapping field selectors to values
- `submit_selector` (Optional[str]): CSS selector for submit button (optional)
- `ctx` (Optional[Context]): Execution context

**Returns:** Dictionary containing:
- `success` (bool): Whether form was filled successfully
- `fields_filled` (list): List of field selectors that were filled
- `submitted` (bool): Whether form was submitted
- `error` (str): Error message if failed

**Example:**
```python
result = await fill_form_fields(
    fields={
        "#name": "John Doe",
        "#email": "john@example.com",
        "#message": "Test message"
    },
    submit_selector="button[type='submit']"
)
if result["success"]:
    print(f"Filled {len(result['fields_filled'])} fields")
```

---

## Testing Tools

> **⚠️ Important Usage Pattern**
>
> All testing tools operate on the **currently loaded page**. You must call `navigate_to_url()` first:
>
> ```python
> # Step 1: Navigate to the page
> await navigate_to_url("https://example.com")
>
> # Step 2: Run tests
> result = await run_accessibility_test()
> ```

### run_exploratory_test

Runs an exploratory test on the current page with AI-guided testing strategies.

```python
@mcp.tool()
async def run_exploratory_test(
    url: str,
    focus_area: str = "general",
    ctx: Optional[Context] = None
) -> dict[str, Any]
```

**Parameters:**
- `url` (str): URL to navigate to and test
- `focus_area` (str): Testing focus area - "general", "forms", "navigation", "login", etc. (default: "general")
- `ctx` (Optional[Context]): Execution context

**Returns:** Dictionary containing:
- `success` (bool): Whether test completed successfully
- `prompt` (str): Generated test prompt with strategies
- `url` (str): The tested URL
- `focus_area` (str): The focus area used
- `initial_screenshot` (str): Base64-encoded initial page screenshot
- `title` (str): Page title
- `testing_strategies` (dict): Recommended testing strategies from resources
- `heuristics` (list): Testing heuristics applied
- `error` (str): Error message if failed

**Example:**
```python
result = await run_exploratory_test(
    url="https://example.com",
    focus_area="forms"
)
if result["success"]:
    print(f"Testing: {result['title']}")
    print(f"Focus: {result['focus_area']}")
```

---

### run_accessibility_test

Runs WCAG accessibility tests on the current page.

```python
@mcp.tool()
async def run_accessibility_test(
    ctx: Optional[Context] = None
) -> dict[str, Any]
```

**Parameters:**
- `ctx` (Optional[Context]): Execution context

**Returns:** Dictionary containing:
- `success` (bool): Whether test completed successfully
- `results` (dict): Detailed accessibility test results
- `guidelines` (list): Accessibility guidelines checked
- `issues_count` (int): Number of issues found
- `error` (str): Error message if failed

**Usage Pattern:**
```python
# Must navigate first!
await navigate_to_url("https://example.com")

# Then run the test
result = await run_accessibility_test()
if result["success"]:
    print(f"Found {result['issues_count']} accessibility issues")
```

---

### run_responsive_test

Tests responsive design across multiple viewport sizes on the current page.

```python
@mcp.tool()
async def run_responsive_test(
    ctx: Optional[Context] = None
) -> dict[str, Any]
```

**Parameters:**
- `ctx` (Optional[Context]): Execution context

**Returns:** Dictionary containing:
- `success` (bool): Whether test completed successfully
- `results` (dict): Responsive design test results
- `breakpoints_tested` (list): List of viewport breakpoint names tested
- `issues_count` (int): Number of responsive issues found
- `error` (str): Error message if failed

**Usage Pattern:**
```python
# Must navigate first!
await navigate_to_url("https://example.com")

# Then run the test
result = await run_responsive_test()
if result["success"]:
    print(f"Tested {len(result['breakpoints_tested'])} viewports")
    print(f"Found {result['issues_count']} responsive issues")
```

**Note:** Uses predefined breakpoints from resources (Mobile Small, Mobile Large, Tablet, Desktop).

---

### run_security_test

Runs basic security tests on the current page.

```python
@mcp.tool()
async def run_security_test(
    ctx: Optional[Context] = None
) -> dict[str, Any]
```

**Parameters:**
- `ctx` (Optional[Context]): Execution context

**Returns:** Dictionary containing:
- `success` (bool): Whether test completed successfully
- `results` (dict): Security test results
- `issues_count` (int): Number of security issues found
- `error` (str): Error message if failed

**Usage Pattern:**
```python
# Must navigate first!
await navigate_to_url("https://example.com")

# Then run the test
result = await run_security_test()
if result["success"]:
    print(f"Found {result['issues_count']} security issues")
```

---

## Reporting Tools

### generate_test_report

Generates a formatted test report for completed tests.

```python
@mcp.tool()
async def generate_test_report(
    test_type: str,
    url: str,
    ctx: Optional[Context] = None
) -> dict[str, Any]
```

**Parameters:**
- `test_type` (str): Type of test report - "exploratory", "accessibility", "responsive", "security"
- `url` (str): URL that was tested
- `ctx` (Optional[Context]): Execution context

**Returns:** Dictionary containing:
- `success` (bool): Whether report was generated
- `report` (dict): Raw report data with structured findings
- `formatted_report` (str): Human-readable formatted report text
- `error` (str): Error message if failed

**Example:**
```python
# After running tests
await navigate_to_url("https://example.com")
await run_accessibility_test()

# Generate report
result = await generate_test_report("accessibility", "https://example.com")
if result["success"]:
    print(result["formatted_report"])
```

---

### prompt_for_credentials

Prompts for user credentials for authentication testing.

```python
@mcp.tool()
async def prompt_for_credentials(
    site: str,
    username_field: Optional[str] = None,
    password_field: Optional[str] = None,
    ctx: Optional[Context] = None
) -> dict[str, Any]
```

**Parameters:**
- `site` (str): Site name requiring authentication
- `username_field` (Optional[str]): CSS selector for username field
- `password_field` (Optional[str]): CSS selector for password field
- `ctx` (Optional[Context]): Execution context

**Returns:** Dictionary containing:
- `credential_prompt` (dict): Prompt information with:
  - `site` (str): Site requiring authentication
  - `username_field` (str): Username field selector
  - `password_field` (str): Password field selector
  - `message` (str): Prompt message for user

**Example:**
```python
result = await prompt_for_credentials(
    site="Example Corp",
    username_field="#username",
    password_field="#password"
)
print(result["credential_prompt"]["message"])
```

---

## Complete Tool Reference

### All 15 MCP Tools

| # | Tool Name | Category | Parameters | Returns |
|---|-----------|----------|------------|---------|
| 1 | start_lsp_server | Diagnostic | tcp, port | str |
| 2 | check_browser_connectivity | Diagnostic | url | dict |
| 3 | analyze_script | Diagnostic | script_path | dict |
| 4 | navigate_to_url | Navigation | url | dict |
| 5 | take_page_screenshot | Screenshot | full_page | dict |
| 6 | take_element_screenshot | Screenshot | selector | dict |
| 7 | fill_login_form | Form | 5 params | dict |
| 8 | detect_form_fields | Form | form_selector | dict |
| 9 | fill_form_fields | Form | fields, submit_selector | dict |
| 10 | run_exploratory_test | Testing | url, focus_area | dict |
| 11 | run_accessibility_test | Testing | (none) | dict |
| 12 | run_responsive_test | Testing | (none) | dict |
| 13 | run_security_test | Testing | (none) | dict |
| 14 | generate_test_report | Reporting | test_type, url | dict |
| 15 | prompt_for_credentials | Reporting | site, fields | dict |

---

## Common Usage Patterns

### Pattern 1: Basic Page Testing

```python
# Navigate and capture
await navigate_to_url("https://example.com")
screenshot = await take_page_screenshot(full_page=True)

# Run tests
accessibility = await run_accessibility_test()
responsive = await run_responsive_test()
security = await run_security_test()

# Generate report
report = await generate_test_report("accessibility", "https://example.com")
print(report["formatted_report"])
```

### Pattern 2: Form Testing

```python
# Navigate to page with form
await navigate_to_url("https://example.com/contact")

# Detect fields
fields = await detect_form_fields()
print(f"Found {fields['count']} fields")

# Fill and submit
result = await fill_form_fields(
    fields={
        "#name": "Test User",
        "#email": "test@example.com"
    },
    submit_selector="button[type='submit']"
)
```

### Pattern 3: Login Testing

```python
# Navigate to login page
await navigate_to_url("https://example.com/login")

# Take before screenshot
before = await take_page_screenshot()

# Fill login form
result = await fill_login_form(
    username_selector="#username",
    password_selector="#password",
    submit_selector="#login-button",
    username="testuser",
    password="testpass"
)

# Take after screenshot
after = await take_page_screenshot()
```

---

## Error Handling

All tools return consistent error structures:

```python
{
    "success": False,
    "error": "Error message describing what went wrong",
    # ... other context-specific fields
}
```

**Best Practice:**
```python
result = await navigate_to_url("https://example.com")
if not result["success"]:
    print(f"Error: {result['error']}")
    # Handle error
else:
    # Continue with tests
    pass
```

---

## Context Parameter

All tools accept an optional `ctx: Optional[Context]` parameter provided by FastMCP for progress reporting. This is automatically provided when called through MCP protocol and doesn't need to be specified by users.

---

## See Also

- **[MCP_IMPROVEMENTS.md](MCP_IMPROVEMENTS.md)** - Recent refactoring improvements
- **[API_AUDIT_REPORT.md](API_AUDIT_REPORT.md)** - Detailed audit findings
- **[TESTING_GUIDE.md](TESTING_GUIDE.md)** - Testing procedures
- **[DEVELOPER_GUIDE.md](DEVELOPER_GUIDE.md)** - Advanced integration

---

**Documentation Version:** 2.0 (Corrected)
**Last Updated:** 2025-11-07
**Status:** ✅ Verified against implementation
