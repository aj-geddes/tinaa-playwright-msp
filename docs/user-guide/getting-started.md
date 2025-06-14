# Getting Started with TINAA

Welcome to TINAA! This guide will help you get started with AI-powered browser automation and testing.

## Prerequisites

Before you begin, ensure you have:
- TINAA running ([Installation Guide](installation.md))
- A web application to test
- Basic knowledge of HTTP APIs or MCP integration

## Your First Test

### Step 1: Verify TINAA is Running

```bash
curl http://localhost:8765/health
```

Expected response:
```json
{
  "status": "healthy",
  "version": "1.0.0"
}
```

### Step 2: Run an Exploratory Test

Execute an AI-guided exploratory test on your application:

```bash
curl -X POST http://localhost:8765/test/exploratory \
  -H "Content-Type: application/json" \
  -d '{
    "action": "exploratory",
    "parameters": {
      "url": "https://your-app.com",
      "focus_area": "forms"
    }
  }'
```

### Step 3: Check Accessibility

Run an accessibility audit:

```bash
curl -X POST http://localhost:8765/test/accessibility \
  -H "Content-Type: application/json" \
  -d '{
    "action": "accessibility",
    "parameters": {
      "url": "https://your-app.com",
      "standard": "WCAG2AA"
    }
  }'
```

## Using with Claude Desktop

If you're using TINAA with Claude Desktop:

1. Configure Claude Desktop to use TINAA as an MCP server
2. Ask Claude to:
   - "Navigate to my website and take a screenshot"
   - "Check the accessibility of my login page"
   - "Perform exploratory testing on my checkout flow"

## Understanding Test Results

TINAA provides detailed test results including:
- Test execution logs
- Screenshots of key interactions
- Accessibility violations found
- Performance metrics
- Recommendations for improvements

## Real-time Progress Tracking

Connect via WebSocket to see live test progress:

```javascript
const ws = new WebSocket('ws://localhost:8765/ws');

ws.onmessage = (event) => {
  const progress = JSON.parse(event.data);
  console.log(`${progress.action}: ${progress.status}`);
};
```

## Next Steps

- [Test Execution Guide](test-execution.md)
- [Best Practices](best-practices.md)
- [API Reference](../API.md)

## Getting Help

- [FAQ](../support/faq.md)
- [Community Support](../support/community.md)
- [Troubleshooting](../TROUBLESHOOTING.md)