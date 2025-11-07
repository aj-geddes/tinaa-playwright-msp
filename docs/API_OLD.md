# TINAA API Documentation

## Overview

TINAA provides three different API interfaces for browser automation and testing:

1. **MCP (Model Context Protocol)** - For AI assistants like Claude
2. **HTTP REST API** - Traditional REST endpoints with WebSocket support
3. **LSP (Language Server Protocol)** - For IDE integration

> **✨ Recent Updates (2025-11-07)**
> The MCP server has been comprehensively refactored with:
> - ✅ Complete type hints (100% coverage)
> - ✅ Enhanced error handling and input validation
> - ✅ Comprehensive docstrings with examples
> - ✅ Improved progress reporting via Context
> - ✅ Better structured error responses
>
> See [MCP_IMPROVEMENTS.md](../MCP_IMPROVEMENTS.md) for complete details.

## Resources API

TINAA includes a comprehensive resources framework with 25 specialized resources following the gofastmcp.com v2.8.0 specification. All resources are accessible via HTTP endpoints:

### Resource Categories

| Category | Count | Description |
|----------|-------|-------------|
| Tools | 9 | CLI tools, scaffolding, CI/CD integration |
| Quickstarts | 4 | Getting started guides |
| Examples | 4 | Real-world test examples |
| Documentation | 3 | Best practices and guides |
| AI Prompts | 3 | Test generation and code review |
| Additional | 2 | Resource index and strategies |

### Resource Endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /resources/index.json` | Complete resource registry |
| `GET /resources/tools/{tool}.json` | Specific tool resource |
| `GET /resources/quickstarts/{guide}.json` | Quickstart guide |
| `GET /resources/examples/{example}.json` | Example test pattern |
| `GET /resources/docs/{doc}.json` | Documentation resource |
| `GET /resources/prompts/{prompt}.json` | AI prompt resource |

## MCP Tools API

The MCP interface is defined in `app/main.py` and provides the following tools:

### start_lsp_server

Starts the Playwright Language Server Protocol server.

```python
@mcp.tool()
async def start_lsp_server(tcp: bool = False, port: int = 8765) -> str
```

**Parameters:**
- `tcp` (bool): Use TCP mode instead of stdio
- `port` (int): Port number for TCP mode

**Returns:** Status message

---

### check_browser_connectivity

Tests browser automation connectivity and capabilities.

```python
@mcp.tool()
async def check_browser_connectivity(url: str = "https://example.com", ctx: Optional[Context] = None) -> dict[str, Any]
```

**Parameters:**
- `url` (str): URL to test connectivity with (default: "https://example.com")
- `ctx` (Optional[Context]): Execution context for progress reporting

**Returns:** Dictionary containing:
- `success` (bool): Whether browser automation is working
- `url` (str): The tested URL
- `title` (str): Page title
- `status` (int): HTTP status code
- `screenshot` (str): Base64-encoded PNG screenshot
- `error` (str): Error message if failed

**Use Cases:**
- Verify browser automation setup
- Test network connectivity
- Validate Playwright installation
- Troubleshooting browser issues

---

### navigate_to_url

Navigates the browser to a specified URL and captures page information.

```python
@mcp.tool()
async def navigate_to_url(url: str, ctx: Optional[Context] = None) -> dict[str, Any]
```

**Parameters:**
- `url` (str): The URL to navigate to (must start with http:// or https://)
- `ctx` (Optional[Context]): Execution context for progress reporting

**Returns:** Dictionary containing:
- `success` (bool): Whether navigation succeeded
- `url` (str): The requested URL
- `current_url` (str): Actual URL after redirects
- `title` (str): Page title
- `error` (str): Error message if failed

**Example:**
```python
result = await navigate_to_url("https://example.com")
print(result["title"])  # "Example Domain"
```

---

### take_page_screenshot

Takes a PNG screenshot of the current page.

```python
@mcp.tool()
async def take_page_screenshot(full_page: bool = False, ctx: Optional[Context] = None) -> dict[str, Any]
```

**Parameters:**
- `full_page` (bool): If True, captures entire page by scrolling. If False, captures only viewport (default: False)
- `ctx` (Optional[Context]): Execution context for progress reporting

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
- `username_selector` (str): CSS selector for username/email input field (required)
- `password_selector` (str): CSS selector for password input field (required)
- `submit_selector` (str): CSS selector for submit button (required)
- `username` (str): Username or email to enter (required)
- `password` (str): Password to enter (required)
- `ctx` (Optional[Context]): Execution context for progress reporting

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

### run_exploratory_test

Runs an exploratory test on a website using AI-driven heuristics.

```python
@mcp.tool()
async def run_exploratory_test(
    url: str,
    max_depth: int = 3,
    max_pages: int = 10,
    include_forms: bool = True,
    include_navigation: bool = True,
    check_errors: bool = True
) -> str
```

**Parameters:**
- `url` (str): Starting URL for the test
- `max_depth` (int): Maximum navigation depth
- `max_pages` (int): Maximum pages to visit
- `include_forms` (bool): Test form interactions
- `include_navigation` (bool): Test navigation elements
- `check_errors` (bool): Check for JavaScript errors

**Returns:** Detailed test report with findings

---

### run_accessibility_test

Runs accessibility tests based on WCAG standards.

```python
@mcp.tool()
async def run_accessibility_test(
    url: str,
    standard: str = "WCAG2.1-AA"
) -> str
```

**Parameters:**
- `url` (str): URL to test
- `standard` (str): Accessibility standard (WCAG2.1-A, WCAG2.1-AA, WCAG2.1-AAA)

**Returns:** Accessibility report with violations and recommendations

---

### run_responsive_test

Tests responsive design across multiple viewports.

```python
@mcp.tool()
async def run_responsive_test(
    url: str,
    viewports: list = None
) -> str
```

**Parameters:**
- `url` (str): URL to test
- `viewports` (list): List of viewport configurations

**Returns:** Responsive design analysis report

---

### run_security_test

Runs basic security tests on a website.

```python
@mcp.tool()
async def run_security_test(url: str) -> str
```

**Parameters:**
- `url` (str): URL to test

**Returns:** Security findings report

## HTTP REST API

The HTTP API is defined in `app/http_server.py` and provides the following endpoints:

### GET /

Root endpoint providing API information.

**Response:**
```json
{
  "message": "TINAA Playwright MSP API",
  "version": "1.0.0",
  "endpoints": [...]
}
```

---

### GET /health

Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T00:00:00Z"
}
```

---

### POST /test/connectivity

Tests browser connectivity.

**Request Body:** None required

**Response:**
```json
{
  "status": "success",
  "message": "Browser connectivity test successful"
}
```

---

### POST /navigate

Navigates to a specified URL.

**Request Body:**
```json
{
  "url": "https://example.com"
}
```

**Response:**
```json
{
  "status": "success",
  "url": "https://example.com",
  "title": "Example Domain"
}
```

---

### POST /screenshot

Takes a screenshot of the current page.

**Request Body:**
```json
{
  "name": "screenshot-name"
}
```

**Response:**
```json
{
  "status": "success",
  "screenshot": {
    "name": "screenshot-name",
    "timestamp": "2024-01-01T00:00:00Z"
  }
}
```

---

### POST /test/exploratory

Runs exploratory test with streaming progress updates.

**Request Body:**
```json
{
  "url": "https://example.com",
  "max_depth": 3,
  "max_pages": 10,
  "include_forms": true,
  "include_navigation": true,
  "check_errors": true
}
```

**Response:** Server-Sent Events stream with progress updates

---

### POST /test/accessibility

Runs accessibility test with streaming progress updates.

**Request Body:**
```json
{
  "url": "https://example.com",
  "standard": "WCAG2.1-AA"
}
```

**Response:** Server-Sent Events stream with progress updates

---

### POST /playbook/execute

Executes a test playbook.

**Request Body:**
```json
{
  "playbook": {
    "name": "Login Test",
    "steps": [
      {
        "action": "navigate",
        "url": "https://example.com/login"
      },
      {
        "action": "fill",
        "selector": "#username",
        "value": "testuser"
      }
    ]
  }
}
```

**Response:**
```json
{
  "status": "success",
  "results": [...]
}
```

---

### WebSocket /ws/{client_id}

WebSocket endpoint for real-time bidirectional communication.

**Connection URL:** `ws://localhost:8765/ws/{client_id}`

**Message Format:**
```json
{
  "type": "command",
  "action": "navigate",
  "params": {
    "url": "https://example.com"
  }
}
```

## Data Models

### Progress Update Model

Used for streaming test progress:

```python
class ProgressUpdate(BaseModel):
    category: str
    phase: str
    message: str
    data: Optional[Dict[str, Any]] = None
    timestamp: datetime
```

### Test Result Model

Common structure for test results:

```python
class TestResult(BaseModel):
    status: str  # "success", "warning", "error"
    findings: Dict[str, List[Dict[str, Any]]]
    summary: Dict[str, Any]
    screenshots: List[Dict[str, str]]
    duration: float
```

### Playbook Model

Structure for test playbooks:

```python
class PlaybookStep(BaseModel):
    action: str
    selector: Optional[str] = None
    value: Optional[str] = None
    url: Optional[str] = None
    wait: Optional[int] = None

class Playbook(BaseModel):
    name: str
    description: Optional[str] = None
    steps: List[PlaybookStep]
```

## Error Responses

All APIs use consistent error response format:

```json
{
  "error": {
    "type": "ValidationError",
    "message": "Invalid URL format",
    "details": {
      "field": "url",
      "reason": "URL must start with http:// or https://"
    }
  }
}
```

Common error types:
- `ValidationError` - Invalid input parameters
- `BrowserError` - Browser operation failed
- `TimeoutError` - Operation timed out
- `NotFoundError` - Resource not found
- `InternalError` - Server error

## Authentication

Currently, no authentication is required for any endpoints. In production environments, consider implementing:
- API key authentication
- JWT tokens
- OAuth 2.0

## Rate Limiting

No rate limiting is currently implemented. For production use, consider:
- Request throttling per IP
- Concurrent connection limits
- Resource usage quotas

## Examples

### Using MCP with Claude

```python
# This would be called by Claude through the MCP protocol
result = await run_exploratory_test(
    url="https://example.com",
    max_depth=2,
    include_forms=True
)
```

## Using HTTP API with Python

```python
import requests
import json

# Simple navigation
response = requests.post(
    "http://localhost:8765/navigate",
    json={"url": "https://example.com"}
)
print(response.json())

# Streaming test with SSE
import sseclient

response = requests.post(
    "http://localhost:8765/test/accessibility",
    json={"url": "https://example.com"},
    stream=True
)

client = sseclient.SSEClient(response)
for event in client.events():
    data = json.loads(event.data)
    print(f"Progress: {data['message']}")
```

## Using WebSocket with JavaScript

```javascript
const ws = new WebSocket('ws://localhost:8765/ws/client123');

ws.onopen = () => {
    ws.send(JSON.stringify({
        type: 'command',
        action: 'navigate',
        params: { url: 'https://example.com' }
    }));
};

ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('Received:', data);
};
```

## Best Practices

1. **Error Handling**: Always handle potential errors in responses
2. **Timeouts**: Set appropriate timeouts for long-running operations
3. **Streaming**: Use streaming endpoints for tests that may take time
4. **Resource Cleanup**: Ensure proper cleanup after test completion
5. **Validation**: Validate URLs and selectors before sending requests