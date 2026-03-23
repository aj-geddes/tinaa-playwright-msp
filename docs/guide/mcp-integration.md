---
layout: page
title: "Claude Code & MCP Integration"
description: "Use TINAA MSP tools directly from Claude Code and Claude Desktop via the Model Context Protocol."
---

# Claude Code and MCP Integration

TINAA MSP exposes a full [Model Context Protocol](https://modelcontextprotocol.io) (MCP) server that allows Claude Code and Claude Desktop to interact with your platform directly. Instead of switching between your IDE and the TINAA dashboard, you can check quality scores, run tests, and analyse metrics through a natural conversation with Claude.

---

## What Is MCP?

The Model Context Protocol (MCP) is an open protocol developed by Anthropic that defines a standard way for AI assistants to call external tools and read contextual resources. When a Claude-powered tool (like Claude Code) is configured with an MCP server, it can call that server's functions and incorporate the results directly into its responses.

TINAA's MCP server is built with [FastMCP](https://github.com/jlowin/fastmcp) and communicates over stdio (standard input/output), which is the default transport supported by Claude Desktop and Claude Code.

---

## Starting the MCP Server

Start the TINAA MCP server as a standalone process:

```bash
# From the TINAA MSP directory
python -m tinaa.mcp_server

# Or using the installed script entry point
tinaa-mcp
```

The server starts in stdio mode and is ready to accept MCP client connections. No network port is opened — communication happens entirely over stdin/stdout, which Claude Desktop and Claude Code manage automatically.

---

## Configuring Claude Desktop

Add TINAA to your Claude Desktop configuration file.

**macOS / Linux:** `~/.config/claude-desktop/claude_desktop_config.json`

**Windows:** `%APPDATA%\claude-desktop\claude_desktop_config.json`

```json
{
  "mcpServers": {
    "tinaa-msp": {
      "command": "python",
      "args": ["-m", "tinaa.mcp_server"],
      "cwd": "/path/to/tinaa-playwright-msp",
      "env": {
        "DATABASE_URL": "postgresql+asyncpg://tinaa:tinaa@localhost:5432/tinaa",
        "REDIS_URL": "redis://localhost:6379/0",
        "TINAA_API_KEY": "your-api-key"
      }
    }
  }
}
```

If TINAA is running in Docker and your Python environment is inside the container, use:

```json
{
  "mcpServers": {
    "tinaa-msp": {
      "command": "docker",
      "args": [
        "exec", "-i", "tinaa-playwright-msp-tinaa-1",
        "python", "-m", "tinaa.mcp_server"
      ]
    }
  }
}
```

Restart Claude Desktop after editing the configuration file. You will see the TINAA tools available in the tool picker.

---

## Configuring Claude Code

If you use Claude Code (the CLI tool), add TINAA to your project's `.claude/settings.json`:

```json
{
  "mcpServers": {
    "tinaa-msp": {
      "command": "python",
      "args": ["-m", "tinaa.mcp_server"],
      "cwd": "/path/to/tinaa-playwright-msp"
    }
  }
}
```

---

## All 14 MCP Tools

### `register_product`

Register a new application with TINAA for continuous quality monitoring.

**Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `name` | string | Yes | Human-readable product name |
| `repo_url` | string | Yes | Git repository URL |
| `environments` | object | Yes | Map of environment name to base URL |
| `description` | string | No | Optional description |

**Example:**

```
register_product(
  name="Checkout Service",
  repo_url="https://github.com/myorg/checkout-service",
  environments={
    "production": "https://checkout.myapp.com",
    "staging": "https://checkout-staging.myapp.com"
  },
  description="Cart, payment, and order confirmation"
)
```

---

### `list_products`

List all registered products, optionally filtered by status.

**Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `status` | string | No | Filter by `active`, `paused`, or `archived` |

**Example:**

```
list_products(status="active")
```

**Returns:** List of product summaries including name, slug, quality score, and environment count.

---

### `get_product_detail`

Get comprehensive details for a single product including environments, endpoints, quality score, and recent test runs.

**Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `product_id_or_slug` | string | Yes | Product ID (e.g. `prod-a1b2c3d4`) or slug (e.g. `checkout-service`) |

**Example:**

```
get_product_detail(product_id_or_slug="checkout-service")
```

---

### `get_quality_score`

Get the current quality score for a product with a full breakdown by component.

**Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `product_id_or_slug` | string | Yes | Product ID or slug |
| `environment` | string | No | Scope the score to a specific environment |

**Example:**

```
get_quality_score(
  product_id_or_slug="checkout-service",
  environment="production"
)
```

**Returns:** Composite score (0–100), grade, component breakdown, trend, and recommendations.

---

### `get_quality_report`

Generate a comprehensive quality report with trend analysis and top issues.

**Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `product_id_or_slug` | string | Yes | Product ID or slug |
| `environment` | string | No | Scope to a specific environment |

**Example:**

```
get_quality_report(
  product_id_or_slug="checkout-service",
  environment="production"
)
```

**Returns:** Quality score, 7-day and 30-day trends, test/performance/security/accessibility summaries, top issues, and recommendations.

---

### `run_playbook`

Execute a specific test playbook against an environment.

**Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `playbook_id_or_name` | string | Yes | Playbook ID or name (e.g. `checkout-regression`) |
| `environment` | string | No | Target environment (defaults to staging) |
| `target_url` | string | No | Override the base URL for this run |

**Example:**

```
run_playbook(
  playbook_id_or_name="checkout-regression",
  environment="staging"
)
```

**Returns:** Run ID, status, pass/fail counts, duration, and quality score impact.

---

### `run_suite`

Run all playbooks for a product/environment combination.

**Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `product_id_or_slug` | string | Yes | Product ID or slug |
| `environment` | string | No | Target environment (defaults to staging) |
| `suite_type` | string | No | One of `smoke`, `regression`, `accessibility`, `performance`, `security` (defaults to regression) |

**Example:**

```
run_suite(
  product_id_or_slug="checkout-service",
  environment="staging",
  suite_type="smoke"
)
```

**Returns:** Suite run ID, number of playbooks executed, pass/fail counts, duration, and updated quality score.

---

### `get_test_results`

Get recent test run results for a product.

**Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `product_id_or_slug` | string | Yes | Product ID or slug |
| `limit` | integer | No | Maximum results to return (default: 10) |
| `status` | string | No | Filter by `passed`, `failed`, `error`, or `running` |

**Example:**

```
get_test_results(
  product_id_or_slug="checkout-service",
  status="failed",
  limit=5
)
```

---

### `suggest_tests`

Get test suggestions based on codebase analysis and changed files.

**Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `product_id_or_slug` | string | Yes | Product ID or slug |
| `changed_files` | list[string] | No | List of changed file paths from the current diff |

**Example:**

```
suggest_tests(
  product_id_or_slug="checkout-service",
  changed_files=["src/checkout.py", "src/cart.py", "src/payment.py"]
)
```

**Returns:** Prioritised list of playbook suggestions with reasoning and affected journeys.

---

### `create_playbook`

Create a new test playbook for a product.

**Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `product_id_or_slug` | string | Yes | Product ID or slug |
| `name` | string | Yes | Human-readable playbook name |
| `steps` | list[dict] | Yes | Ordered list of action dicts |
| `assertions` | dict | No | Global assertion rules |
| `performance_gates` | dict | No | Performance thresholds |

**Example:**

```
create_playbook(
  product_id_or_slug="checkout-service",
  name="homepage-smoke",
  steps=[
    {"action": "navigate", "url": "https://staging.myapp.com"},
    {"action": "assert_visible", "selector": "h1"},
    {"action": "screenshot", "name": "homepage"}
  ],
  performance_gates={"lcp_ms": 2500, "cls": 0.1}
)
```

---

### `get_metrics`

Query APM metrics for a product or specific endpoint.

**Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `product_id_or_slug` | string | Yes | Product ID or slug |
| `endpoint_path` | string | No | Filter to a specific endpoint path |
| `metric_type` | string | No | One of `response_time`, `lcp`, `cls`, `availability`, `error_rate` |
| `hours` | integer | No | Lookback window in hours (default: 24) |

**Example:**

```
get_metrics(
  product_id_or_slug="checkout-service",
  metric_type="lcp",
  hours=6
)
```

**Returns:** Time-series data points, baseline P50/P95, current average, and trend direction.

---

### `configure_alerts`

Configure alert rules for a product.

**Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `product_id_or_slug` | string | Yes | Product ID or slug |
| `rules` | list[dict] | Yes | List of alert rule configurations |

**Example:**

```
configure_alerts(
  product_id_or_slug="checkout-service",
  rules=[
    {
      "type": "quality_score_drop",
      "threshold": 10,
      "channels": ["slack:#alerts"]
    },
    {
      "type": "endpoint_down",
      "threshold": 3,
      "channels": ["pagerduty"]
    }
  ]
)
```

---

### `get_deployments`

Get recent deployments for a product with their quality impact.

**Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `product_id_or_slug` | string | Yes | Product ID or slug |
| `environment` | string | No | Filter to a specific environment |
| `limit` | integer | No | Maximum deployments to return (default: 10) |

**Example:**

```
get_deployments(
  product_id_or_slug="checkout-service",
  environment="production",
  limit=5
)
```

---

### `explore_codebase`

Trigger codebase exploration to discover routes, endpoints, and user journeys.

**Parameters:**

| Parameter | Type | Required | Description |
|---|---|---|---|
| `product_id_or_slug` | string | Yes | Product ID or slug |

**Example:**

```
explore_codebase(product_id_or_slug="checkout-service")
```

**Returns:** Discovered routes, API endpoints, forms, and inferred user journeys.

---

## Example Workflow: "Check My App's Quality"

The following shows how a typical Claude conversation might unfold when a developer asks about their application's quality.

**Developer asks Claude:**
> "How is the checkout service doing quality-wise? Are there any regressions?"

**Claude calls TINAA tools:**

```
get_quality_score(product_id_or_slug="checkout-service", environment="production")
```

```
get_quality_report(product_id_or_slug="checkout-service")
```

**Claude responds:**

> The Checkout Service has a quality score of **87/100 (Grade A)** in production. Here is the breakdown:
>
> - Test Health: 91/100 — 94% pass rate, strong coverage
> - Performance: 84/100 — P95 response time is 420ms (budget: 500ms); LCP is 1.8s (good)
> - Security: 88/100 — All headers present, TLS grade A
> - Accessibility: 82/100 — 4 violations found
>
> The score is improving (+2 points over the last 7 days).
>
> **Top issues to address:**
> 1. 3 images on /checkout are missing alt text (accessibility, medium severity)
> 2. /api/search P95 response time is 520ms, exceeding the 500ms budget

---

## Example Workflow: "Run Smoke Tests Before Deploy"

**Developer asks Claude:**
> "I'm about to deploy to production. Can you run the smoke tests on staging first?"

**Claude calls TINAA tools:**

```
run_suite(
  product_id_or_slug="checkout-service",
  environment="staging",
  suite_type="smoke"
)
```

**Claude responds:**

> I ran the smoke suite on staging. Here are the results:
>
> - Suite: smoke
> - Duration: 28.4 seconds
> - Playbooks executed: 8
> - Passed: 7
> - Failed: 1
> - Quality score: 85
>
> **1 failure detected:** The `checkout-regression` playbook failed — `assert_url` expected a match for `/order-confirmation/[0-9]+` but got `/cart?error=payment_declined`.
>
> I would recommend investigating the payment flow on staging before deploying to production. Would you like me to look at the full test run details?

---

## Next Steps

- [Getting Started](getting-started.md) — install TINAA MSP
- [Playbooks](playbooks.md) — create playbooks that Claude can run via MCP
- [Quality Scores](quality-scores.md) — understand the scores Claude reports
- [Configuration Reference](configuration.md) — environment variables used by the MCP server
