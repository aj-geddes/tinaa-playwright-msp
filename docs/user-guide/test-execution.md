# Test Execution Guide

Learn how to leverage TINAA's AI-powered test execution and browser automation capabilities.

## Overview

TINAA provides intelligent browser automation through MCP (Model Context Protocol) integration, enabling AI assistants like Claude to execute Playwright tests and perform browser automation tasks.

## Test Execution Methods

### Via HTTP API

Execute predefined test types through the HTTP API:

```bash
# Exploratory Testing
curl -X POST http://localhost:8765/test/exploratory \
  -H "Content-Type: application/json" \
  -d '{
    "action": "exploratory",
    "parameters": {
      "url": "https://example.com",
      "focus_area": "navigation"
    }
  }'

# Accessibility Testing
curl -X POST http://localhost:8765/test/accessibility \
  -H "Content-Type: application/json" \
  -d '{
    "action": "accessibility",
    "parameters": {
      "url": "https://example.com",
      "standard": "WCAG2AA"
    }
  }'
```

### Via MCP Integration

When integrated with Claude Desktop, TINAA provides these tools:

- `navigate_to_url` - Navigate browser to any URL
- `take_page_screenshot` - Capture screenshots
- `click_element` - Interact with page elements
- `fill_form_field` - Fill form inputs
- `run_exploratory_test` - Execute AI-guided exploratory tests
- `check_page_accessibility` - Run accessibility audits

## Available Test Types

### 1. Exploratory Testing

TINAA uses AI heuristics to explore your application:

```json
{
  "action": "exploratory",
  "parameters": {
    "url": "https://example.com",
    "depth": 3,
    "focus_area": "forms"
  }
}
```

### 2. Accessibility Testing

Validate WCAG compliance:

```json
{
  "action": "accessibility", 
  "parameters": {
    "url": "https://example.com",
    "standard": "WCAG2AA",
    "includeWarnings": true
  }
}
```

### 3. Responsive Testing

Test across multiple viewports:

```json
{
  "action": "responsive",
  "parameters": {
    "url": "https://example.com",
    "viewports": ["mobile", "tablet", "desktop"]
  }
}
```

### 4. Security Testing

Basic security checks:

```json
{
  "action": "security",
  "parameters": {
    "url": "https://example.com",
    "checks": ["https", "headers", "forms"]
  }
}
```

## Test Patterns and Resources

TINAA includes predefined test patterns located in `/resources/`:

- **Test Patterns** (`test_patterns.json`) - Common testing scenarios
- **Accessibility Rules** (`accessibility_rules.json`) - WCAG compliance rules
- **Security Patterns** (`security_test_patterns.json`) - Security check definitions
- **Exploratory Heuristics** (`exploratory_heuristics.json`) - AI exploration rules

## Writing Custom Test Scripts

TINAA can analyze and execute custom Playwright scripts:

```javascript
// my-test.js
const { test, expect } = require('@playwright/test');

test('my custom test', async ({ page }) => {
  await page.goto('https://example.com');
  await expect(page).toHaveTitle(/Example/);
});
```

Analyze your script:
```bash
tina analyze my-test.js
```

## Integration with AI Assistants

When used with Claude Desktop, you can:

1. Ask Claude to navigate to websites
2. Request screenshots of specific pages
3. Have Claude perform exploratory testing
4. Get accessibility reports
5. Execute custom test scenarios

Example prompts:
- "Navigate to example.com and take a screenshot"
- "Check the accessibility of this login form"
- "Perform exploratory testing on the checkout flow"

## Real-time Progress Tracking

TINAA provides WebSocket connections for real-time test progress:

```javascript
const ws = new WebSocket('ws://localhost:8765/ws');

ws.on('message', (data) => {
  const progress = JSON.parse(data);
  console.log(`${progress.action}: ${progress.status}`);
});
```

## Related Resources

- [Getting Started](getting-started.md)
- [API Reference](../API.md)
- [Best Practices](best-practices.md)