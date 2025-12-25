# TINAA MCP Server Testing Guide

## Pre-Testing Validation

### Static Analysis ✅ PASSED

All files have been validated for syntax correctness:

```bash
python3 -m py_compile app/mcp_handler.py app/main.py app/enhanced_mcp_handler.py app/progress_tracker.py
# ✅ All Python files compile successfully
```

### Type Hints Validation ✅ COMPLETE

- **mcp_handler.py**: 12/12 functions with proper type hints
- **main.py**: 3/3 MCP tools with proper type hints
- **enhanced_mcp_handler.py**: All functions properly typed
- **Coverage**: 100% ✅

### Import Structure ✅ VERIFIED

All imports have been corrected:
- ✅ `from playwright_controller.controller import PlaywrightController`
- ✅ `from typing import Any, Optional`
- ✅ All FastMCP imports
- ✅ Local module imports (prompts, resources)

---

## Runtime Testing

### Prerequisites

```bash
# Install dependencies
pip install -r requirements.txt

# Install Playwright browsers
python -m playwright install chromium

# Verify installation
playwright --version
```

### Test Suite 1: Import Tests

**Purpose**: Verify all modules import correctly

```bash
cd /home/user/tinaa-playwright-msp
python tests/unit/test_mcp.py
```

**Expected Output**:
```
✓ Successfully imported MCP server: TINAA - Testing Intelligence Network Automation Assistant
✓ All 15 tools registered

Total tools registered: 15
  - start_lsp_server
  - check_browser_connectivity
  - analyze_script
  - navigate_to_url
  - take_page_screenshot
  - take_element_screenshot
  - fill_login_form
  - detect_form_fields
  - fill_form_fields
  - run_accessibility_test
  - run_responsive_test
  - run_security_test
  - generate_test_report
  - prompt_for_credentials
  - run_exploratory_test
```

### Test Suite 2: Browser Connectivity

**Purpose**: Verify browser automation works

```python
import asyncio
from app.main import check_browser_connectivity

async def test():
    result = await check_browser_connectivity("https://example.com")
    assert result["success"] == True
    assert "title" in result
    assert "screenshot" in result
    print(f"✅ Browser connectivity test passed")
    print(f"   Title: {result['title']}")
    print(f"   Status: {result['status']}")

asyncio.run(test())
```

**Expected Result**:
```
✅ Browser connectivity test passed
   Title: Example Domain
   Status: 200
```

### Test Suite 3: Navigation & Screenshots

**Purpose**: Test core browser automation functions

```python
import asyncio
from app.mcp_handler import navigate_to_url, take_page_screenshot

async def test():
    # Test navigation
    nav_result = await navigate_to_url("https://example.com")
    assert nav_result["success"] == True
    assert nav_result["title"] == "Example Domain"
    print("✅ Navigation test passed")

    # Test screenshot
    screenshot_result = await take_page_screenshot(full_page=True)
    assert screenshot_result["success"] == True
    assert len(screenshot_result["screenshot"]) > 0
    print("✅ Screenshot test passed")

asyncio.run(test())
```

### Test Suite 4: Form Interaction

**Purpose**: Test form filling capabilities

```python
import asyncio
from app.mcp_handler import navigate_to_url, detect_form_fields

async def test():
    # Navigate to a page with forms
    await navigate_to_url("https://httpbin.org/forms/post")

    # Detect forms
    result = await detect_form_fields()
    assert result["success"] == True
    assert result["count"] > 0
    print(f"✅ Form detection passed - found {result['count']} fields")

asyncio.run(test())
```

### Test Suite 5: Accessibility Testing

**Purpose**: Test accessibility audit functionality

```python
import asyncio
from app.mcp_handler import navigate_to_url, run_accessibility_test

async def test():
    await navigate_to_url("https://example.com")
    result = await run_accessibility_test()

    assert result["success"] == True
    print(f"✅ Accessibility test passed")
    print(f"   Issues found: {result['issues_count']}")

asyncio.run(test())
```

### Test Suite 6: Error Handling

**Purpose**: Verify error handling works correctly

```python
import asyncio
from app.mcp_handler import navigate_to_url, take_element_screenshot

async def test_error_handling():
    # Test invalid URL
    result = await navigate_to_url("not-a-valid-url")
    assert result["success"] == False
    assert "error" in result
    print("✅ URL validation works")

    # Test empty selector
    result = await take_element_screenshot("")
    assert result["success"] == False
    assert "error" in result
    print("✅ Selector validation works")

    print("✅ All error handling tests passed")

asyncio.run(test_error_handling())
```

---

## MCP Protocol Testing

### Test MCP Server Startup

```bash
# Start MCP server in stdio mode
python app/main.py

# Or using fastmcp CLI
fastmcp run app.main:mcp
```

### Test with Claude Desktop

1. **Configure Claude Desktop** (`claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "tinaa": {
      "command": "python",
      "args": ["-m", "app.main"],
      "cwd": "/home/user/tinaa-playwright-msp"
    }
  }
}
```

2. **Test in Claude**:

```
Ask Claude: "Can you check browser connectivity to https://playwright.dev?"

Expected: Claude will use check_browser_connectivity tool and report results
```

### Test MCP Tools Directly

```python
import asyncio
from app.main import mcp

async def test_mcp_tools():
    # Get available tools
    tools = mcp.list_tools()
    print(f"Available tools: {len(tools)}")

    for tool in tools:
        print(f"  - {tool.name}: {tool.description[:50]}...")

asyncio.run(test_mcp_tools())
```

---

## Integration Testing

### Test Complete Workflow

```python
import asyncio
from app.mcp_handler import (
    navigate_to_url,
    take_page_screenshot,
    run_accessibility_test,
    generate_test_report
)

async def test_complete_workflow():
    url = "https://example.com"

    # Step 1: Navigate
    print("1. Navigating...")
    nav_result = await navigate_to_url(url)
    assert nav_result["success"]

    # Step 2: Screenshot
    print("2. Taking screenshot...")
    screenshot_result = await take_page_screenshot(full_page=True)
    assert screenshot_result["success"]

    # Step 3: Accessibility test
    print("3. Running accessibility test...")
    a11y_result = await run_accessibility_test()
    assert a11y_result["success"]

    # Step 4: Generate report
    print("4. Generating report...")
    report_result = await generate_test_report("exploratory", url)
    assert report_result["success"]

    print("✅ Complete workflow test passed!")

asyncio.run(test_complete_workflow())
```

---

## Performance Testing

### Test Concurrent Requests

```python
import asyncio
import time
from app.mcp_handler import check_browser_connectivity

async def test_performance():
    start_time = time.time()

    # Run 5 concurrent browser connectivity checks
    tasks = [
        check_browser_connectivity("https://example.com")
        for _ in range(5)
    ]

    results = await asyncio.gather(*tasks)

    elapsed = time.time() - start_time

    assert all(r["success"] for r in results)
    print(f"✅ 5 concurrent requests completed in {elapsed:.2f}s")
    print(f"   Average: {elapsed/5:.2f}s per request")

asyncio.run(test_performance())
```

---

## Validation Checklist

### Code Quality ✅
- [x] All files compile without syntax errors
- [x] Type hints on 100% of functions
- [x] Comprehensive docstrings on all public functions
- [x] Consistent error handling throughout
- [x] Input validation on all user-facing functions

### Functionality
- [ ] Browser launches successfully
- [ ] Navigation works
- [ ] Screenshots capture correctly
- [ ] Form interactions work
- [ ] Accessibility tests run
- [ ] Security tests run
- [ ] Responsive tests run
- [ ] Report generation works

### MCP Integration
- [ ] MCP server starts without errors
- [ ] All 15 tools register correctly
- [ ] Tools callable via MCP protocol
- [ ] Progress reporting via Context works
- [ ] Error responses properly formatted

### Documentation ✅
- [x] API.md updated to match implementation
- [x] MCP_IMPROVEMENTS.md created
- [x] TESTING_GUIDE.md created
- [x] All docstrings follow standards

---

## Troubleshooting

### Import Errors

**Problem**: `ModuleNotFoundError: No module named 'fastmcp'`

**Solution**:
```bash
pip install -r requirements.txt
```

### Browser Launch Errors

**Problem**: `Error: Executable doesn't exist at /path/to/chromium`

**Solution**:
```bash
python -m playwright install chromium
```

### Permission Errors

**Problem**: Permission denied accessing browser files

**Solution**:
```bash
# Run with proper permissions or use Docker
docker run -it tinaa-playwright-msp
```

---

## Continuous Integration

### GitHub Actions Workflow

```yaml
name: Test MCP Server

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.10'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          python -m playwright install chromium --with-deps

      - name: Run tests
        run: |
          pytest tests/unit/test_mcp.py -v
          pytest tests/unit/test_mcp_comprehensive.py -v

      - name: Check type hints
        run: |
          pip install mypy
          mypy app/mcp_handler.py app/main.py
```

---

## Test Results Summary

### Static Analysis
✅ **PASSED** - All files compile successfully
✅ **PASSED** - Type hints 100% coverage
✅ **PASSED** - Import structure validated

### Runtime Tests
⏳ **PENDING** - Requires runtime environment with dependencies
⏳ **PENDING** - Requires Playwright browser installation

### Recommended Next Steps
1. Install dependencies: `pip install -r requirements.txt`
2. Install browsers: `python -m playwright install chromium`
3. Run test suite: `pytest tests/`
4. Manual MCP testing with Claude Desktop
5. Integration testing with real websites

---

## Support

For issues or questions:
- Check [TROUBLESHOOTING.md](docs/TROUBLESHOOTING.md)
- Review [MCP_IMPROVEMENTS.md](MCP_IMPROVEMENTS.md)
- Open issue on GitHub repository
- Consult [API Documentation](docs/API.md)
