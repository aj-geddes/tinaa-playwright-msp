# Getting Started with TINAA MSP

This guide walks you through registering your first product, adding environments, monitoring endpoints, running your first test, and reading your initial quality score.

---

## Step 1 — Register your first product

### Option A: Dashboard

1. Open the TINAA dashboard and click **Products** in the left sidebar.
2. Click **New Product** (top-right button).
3. Fill in the form:
   - **Product name** — a human-readable name, e.g. `Acme Web App`.
   - **Repository URL** *(optional)* — your GitHub repository, e.g. `https://github.com/acme/webapp`. Connecting a repo enables GitHub deployment integration.
   - **Description** *(optional)* — a short description for your team.
4. Click **Create Product**.

TINAA assigns a URL-safe slug (e.g. `acme-web-app`) that is used in API paths and `.tinaa.yml` configuration.

### Option B: Claude Code MCP (terminal)

If you have the TINAA MCP server running, use natural language from your terminal:

```
> register product "Acme Web App" at https://github.com/acme/webapp
```

Or use the MCP tool directly:

```
tinaa register_product --name "Acme Web App" --repository_url "https://github.com/acme/webapp"
```

### Option C: REST API

```bash
curl -X POST http://localhost:8765/api/v1/products \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $TINAA_API_KEY" \
  -d '{
    "name": "Acme Web App",
    "repository_url": "https://github.com/acme/webapp",
    "description": "Customer-facing e-commerce application"
  }'
```

The response includes the product `id` (UUID) and `slug`, which you will use in subsequent steps.

---

## Step 2 — Add environments

Each product has one or more environments. A typical setup has `production` and `staging`; you can also add `preview` and `development`.

### Dashboard

1. Open your product, click the **Environments** tab.
2. Click **Add Environment**.
3. Fill in:
   - **Name** — e.g. `production`.
   - **Base URL** — e.g. `https://acme.example.com`.
   - **Type** — choose from `production`, `staging`, `development`, or `preview`.
   - **Monitoring interval** — how often TINAA polls your endpoints (default: 5 minutes).
4. Click **Save**.

### REST API

```bash
# Replace $PRODUCT_ID with the UUID from Step 1
curl -X POST http://localhost:8765/api/v1/products/$PRODUCT_ID/environments \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $TINAA_API_KEY" \
  -d '{
    "name": "production",
    "base_url": "https://acme.example.com",
    "env_type": "production",
    "monitoring_interval_seconds": 300
  }'
```

---

## Step 3 — Add endpoints to monitor

Endpoints are the specific URLs that TINAA probes during monitoring and testing. Register at least a homepage, a key user journey page, and a health check.

### Endpoint types

| Type | When to use |
|------|-------------|
| `page` | HTML pages rendered in a browser |
| `api` | JSON API endpoints (no browser rendering) |
| `health` | `/health` or `/ping` liveness probes |

### Dashboard

1. Open your environment, click **Add Endpoint**.
2. Enter the **path** relative to the base URL (e.g. `/`, `/products`, `/api/health`).
3. Select the **type** and optionally set a **performance budget** (milliseconds).
4. Click **Save**.

### REST API

```bash
curl -X POST http://localhost:8765/api/v1/products/$PRODUCT_ID/environments/$ENV_ID/endpoints \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $TINAA_API_KEY" \
  -d '{
    "path": "/",
    "method": "GET",
    "endpoint_type": "page",
    "performance_budget_ms": 2000,
    "expected_status_code": 200
  }'
```

---

## Step 4 — Run your first test

### Manual test run via dashboard

1. Navigate to your product's **Test Runs** tab.
2. Click **Run Tests**.
3. Select the environment (`production` or `staging`) and the playbooks to execute.
4. Click **Start Run**.

TINAA spawns a Playwright browser session, executes each playbook step, captures screenshots on failure, and records performance metrics.

### Auto-discovery run

If no playbooks exist yet, you can trigger an **Explorer run** which uses the TINAA Explorer agent to crawl your site and auto-generate playbooks:

1. Click **Auto-discover playbooks** from the product overview.
2. TINAA crawls your homepage, follows navigation links, and creates playbook YAML files covering each discovered user journey.
3. Review and refine the generated playbooks in the **Playbooks** tab.

### Via API

```bash
curl -X POST http://localhost:8765/api/v1/test-runs \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $TINAA_API_KEY" \
  -d '{
    "product_id": "'$PRODUCT_ID'",
    "environment": "staging",
    "trigger": "manual"
  }'
```

---

## Step 5 — Understand your quality score

After the first test run completes, TINAA calculates your **Quality Score** — a 0–100 number summarising product health across four dimensions:

| Component | Weight | What it measures |
|-----------|--------|-----------------|
| Test Health | 40% | Pass rate, test coverage breadth, freshness, regression management |
| Performance | 30% | Web Vitals (LCP, FCP, CLS), endpoint response times, availability, error rate |
| Security | 15% | HTTPS, security headers, TLS grade, mixed content |
| Accessibility | 15% | WCAG violations, alt text, keyboard navigation |

Your score appears as a badge on the product overview and maps to a letter grade:

| Score | Grade | Meaning |
|-------|-------|---------|
| 95–100 | A+ | Excellent — deploy with confidence |
| 85–94 | A | Good — minor improvements available |
| 70–84 | B | Acceptable — some issues to address |
| 55–69 | C | Needs attention |
| 40–54 | D | Significant problems |
| 0–39 | F | Critical issues blocking quality gate |

The quality score panel also shows **recommendations** — specific, actionable items for each component scoring below 80. Start with the highest-impact recommendation first.

---

## Next steps

- Write custom test playbooks: [Test Playbooks](playbooks.md)
- Configure alert rules: [Alerts & Notifications](alerts.md)
- Set up GitHub deployment protection: [Admin — GitHub Integration](../admin/github-integration.md)
- Understand how scores are calculated: [Quality Scores](quality-scores.md)
