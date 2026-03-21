# Managing Products

A **product** in TINAA MSP represents a web application or service you want to monitor and test. Products contain one or more **environments**, and each environment contains a set of **endpoints**. This hierarchy maps naturally to how teams deploy software: the same application runs in production, staging, and preview with different URLs but the same set of monitored paths.

---

## Product concepts

- **Product** — the top-level entity. Has a name, slug, optional GitHub repository URL, and a computed quality score.
- **Environment** — a deployment of the product at a specific base URL (e.g. `https://acme.example.com`). Environments have a type (`production`, `staging`, `development`, `preview`) and a monitoring interval.
- **Endpoint** — a specific URL path within an environment that TINAA monitors and tests (e.g. `/`, `/checkout`, `/api/health`).

---

## Creating a product

### Dashboard

1. Click **Products** in the left sidebar.
2. Click **New Product**.
3. Enter a **name** (required), optional **repository URL**, and optional **description**.
4. Click **Create Product**.

TINAA derives a URL-safe slug from the name. The slug appears in API paths and the `.tinaa.yml` configuration file.

### REST API

```bash
POST /api/v1/products
Content-Type: application/json
X-API-Key: <your-key>

{
  "name": "Acme Web App",
  "repository_url": "https://github.com/acme/webapp",
  "description": "Customer-facing e-commerce application"
}
```

Response includes `id` (UUID) and `slug`.

---

## Editing a product

### Dashboard

Open the product, click the **pencil icon** next to the product name, update the fields, and click **Save**.

### REST API

```bash
PATCH /api/v1/products/{product_id}
Content-Type: application/json

{
  "description": "Updated description",
  "repository_url": "https://github.com/acme/new-repo"
}
```

Only the fields you include are updated.

---

## Deleting a product

Deleting a product removes all associated environments, endpoints, playbooks, test runs, and metrics. This action is irreversible.

### Dashboard

Open the product, click **Settings**, scroll to the **Danger Zone**, and click **Delete Product**. Confirm with the product name.

### REST API

```bash
DELETE /api/v1/products/{product_id}
```

Returns HTTP 204 on success.

---

## Environment management

### Environment types

| Type | Purpose |
|------|---------|
| `production` | Live customer-facing environment. Monitoring is always active. Quality gates are enforced. |
| `staging` | Pre-production validation. Tests run automatically on every deployment. |
| `preview` | Ephemeral per-PR environments (e.g. Vercel preview URLs). |
| `development` | Local or dev server. Monitoring optional; useful during active development. |

### Adding an environment

```bash
POST /api/v1/products/{product_id}/environments
{
  "name": "staging",
  "base_url": "https://staging.acme.example.com",
  "env_type": "staging",
  "monitoring_interval_seconds": 300
}
```

Monitoring interval values:
- `60` — 1 minute (high-frequency, higher resource cost)
- `300` — 5 minutes (recommended default)
- `900` — 15 minutes
- `3600` — 1 hour (low-frequency, minimal cost)

---

## Endpoint configuration

### Endpoint types

| Type | Description | Performance metrics |
|------|-------------|---------------------|
| `page` | Full browser navigation. Captures Web Vitals (LCP, FCP, CLS, INP). | Yes — full Web Vitals |
| `api` | HTTP request only (no browser). Captures response time and status code. | Response time only |
| `health` | Lightweight liveness check. | Response time and status only |

### Adding an endpoint

```bash
POST /api/v1/products/{product_id}/environments/{env_id}/endpoints
{
  "path": "/checkout",
  "method": "GET",
  "endpoint_type": "page",
  "performance_budget_ms": 2000,
  "expected_status_code": 200
}
```

### Performance budgets

Set `performance_budget_ms` to enforce a response-time threshold. Endpoints exceeding their budget contribute negatively to the Performance component of the quality score. Recommended budgets:

| Endpoint type | Recommended budget |
|---------------|--------------------|
| Homepage / landing page | 2000 ms |
| Core user journey page | 2500 ms |
| API endpoint | 500 ms |
| Health check | 200 ms |

---

## .tinaa.yml configuration file

For code-first configuration, place a `.tinaa.yml` file in the root of your repository. TINAA reads this file during deployment triggers and uses it to override dashboard settings.

### Minimal example

```yaml
product_name: acme-web-app
team: platform

environments:
  - name: production
    url: https://acme.example.com
    env_type: production
    monitoring:
      interval: 5m
      endpoints:
        - path: /
          endpoint_type: page
          performance_budget_ms: 2000
        - path: /api/health
          endpoint_type: health
          performance_budget_ms: 200
```

### Full annotated example

```yaml
# Product identity
product_name: acme-web-app      # must match the slug in TINAA dashboard
team: platform-team
description: Customer-facing e-commerce platform
tags:
  - ecommerce
  - customer-facing

# Environments to monitor
environments:
  - name: production
    url: https://acme.example.com
    env_type: production
    monitoring:
      interval: 5m               # polling interval: 30s, 1m, 5m, 15m, 1h
      endpoints:
        - path: /
          endpoint_type: page
          performance_budget_ms: 2000
          lcp_budget_ms: 2500    # Largest Contentful Paint budget
          cls_budget: 0.1        # Cumulative Layout Shift budget
        - path: /products
          endpoint_type: page
          performance_budget_ms: 2500
        - path: /api/v1/products
          endpoint_type: api
          performance_budget_ms: 500
          expected_status: 200
        - path: /health
          endpoint_type: health
          performance_budget_ms: 200

  - name: staging
    url: https://staging.acme.example.com
    env_type: staging
    monitoring:
      interval: 15m
      endpoints:
        - path: /
          endpoint_type: page
          performance_budget_ms: 3000

# Quality gates — used for deployment decisions
quality_gates:
  default:
    min_score: 80                        # overall score must be >= 80
    no_critical_failures: true           # no test must have status=critical_failure
    max_performance_regression_percent: 20  # response time cannot regress >20%
    max_new_accessibility_violations: 0  # zero tolerance for new a11y violations

# Testing configuration
testing:
  on_deploy: true         # run on GitHub deployment events
  on_pr: true             # run on pull requests
  schedule: "0 3 * * *"  # nightly at 03:00 UTC (cron syntax)
  browsers:
    - chromium            # always included
    - firefox             # optional: add for cross-browser coverage
  viewports:
    - name: desktop
      width: 1440
      height: 900
    - name: mobile
      width: 375
      height: 812
  parallel: false         # set true to run playbooks concurrently
  retries: 1              # retry failed steps once before marking as failed
  timeout_ms: 30000       # per-step timeout in milliseconds

# Alert configuration
alerts:
  channels:
    - type: slack
      config:
        webhook_url: https://hooks.slack.com/services/xxx/yyy/zzz
    - type: pagerduty
      config:
        routing_key: abc123
        severity_threshold: critical
  rules:
    - name: quality-score-drop
      condition: quality_score_drop
      threshold: 10         # alert when score drops by 10+ points
      severity: warning
    - name: endpoint-down
      condition: endpoint_unavailable
      severity: critical
      cooldown_minutes: 5

# Paths to ignore during exploration and testing
ignore_paths:
  - /admin
  - /internal
  - "*.pdf"
```

### Configuration precedence

When both `.tinaa.yml` and dashboard settings exist, `.tinaa.yml` takes precedence for fields it declares. Use `merge_strategy: overlay` (default) to layer `.tinaa.yml` on top of dashboard settings, or `merge_strategy: replace` to let the file fully override them.
