---
layout: page
title: "Configuration Reference"
description: "Environment variables, .tinaa.yml per-repo configuration, and all settings available in TINAA MSP."
---

# Configuration Reference

TINAA MSP is configured through two mechanisms:

1. **Environment variables** — infrastructure-level settings (database URLs, API keys, ports)
2. **`.tinaa.yml`** — per-repository product configuration (quality gates, environments, alerts, testing behaviour)

![Settings page showing integration and system configuration options](../assets/screenshots/settings.png)

---

## Environment Variables

Set these in your `.env` file, Docker Compose `environment` block, or Kubernetes Secrets.

### Core Application

| Variable | Required | Default | Description |
|---|---|---|---|
| `TINAA_DATABASE_URL` | Yes | — | PostgreSQL connection string. Format: `postgresql+asyncpg://user:pass@host:5432/db` |
| `TINAA_REDIS_URL` | Yes | — | Redis connection string. Format: `redis://host:6379/0` |
| `TINAA_API_KEY` | Recommended | — | Master API key for authenticating REST API calls. Set `TINAA_API_KEY_REQUIRED=false` to disable auth (development only) |
| `TINAA_API_KEY_REQUIRED` | No | `true` | Set `false` to disable API key authentication (never in production) |
| `TINAA_MODE` | No | `api` | Server mode. `api` starts the REST API and dashboard. `worker` starts background job processors only. `all` starts both |
| `TINAA_PORT` | No | `8765` | Port the HTTP server listens on |
| `TINAA_HOST` | No | `0.0.0.0` | Interface to bind. Use `127.0.0.1` to restrict to localhost |
| `TINAA_CORS_ORIGINS` | No | `*` | Comma-separated list of allowed CORS origins. In production, set this to your dashboard domain |
| `TINAA_LOG_LEVEL` | No | `INFO` | Logging verbosity: `DEBUG`, `INFO`, `WARNING`, `ERROR` |

### GitHub Integration

| Variable | Required | Default | Description |
|---|---|---|---|
| `TINAA_GITHUB_APP_ID` | No | — | GitHub App ID (numeric string). Required for GitHub App authentication |
| `TINAA_GITHUB_PRIVATE_KEY` | No | — | Contents of the GitHub App private key PEM file. Include newlines |
| `TINAA_GITHUB_WEBHOOK_SECRET` | No | — | Secret used to verify incoming GitHub webhook signatures (`X-Hub-Signature-256`) |
| `TINAA_GITHUB_PAT` | No | — | Personal Access Token for PAT-based authentication (alternative to GitHub App) |

### Email / SMTP Alerts

| Variable | Required | Default | Description |
|---|---|---|---|
| `TINAA_SMTP_HOST` | No | — | SMTP server hostname |
| `TINAA_SMTP_PORT` | No | `587` | SMTP port (587 for STARTTLS, 465 for SSL) |
| `TINAA_SMTP_USERNAME` | No | — | SMTP authentication username |
| `TINAA_SMTP_PASSWORD` | No | — | SMTP authentication password |
| `TINAA_SMTP_USE_TLS` | No | `true` | Enable STARTTLS for SMTP connections |
| `TINAA_ALERT_EMAIL_FROM` | No | — | From address for alert emails |
| `TINAA_ALERT_EMAIL_TO` | No | — | Comma-separated list of recipient addresses |

### PagerDuty Alerts

| Variable | Required | Default | Description |
|---|---|---|---|
| `TINAA_PAGERDUTY_INTEGRATION_KEY` | No | — | PagerDuty Events API v2 integration key |

### Playwright / Browser

| Variable | Required | Default | Description |
|---|---|---|---|
| `TINAA_PLAYWRIGHT_BROWSER` | No | `chromium` | Default browser for playbook runs: `chromium`, `firefox`, `webkit` |
| `TINAA_PLAYWRIGHT_HEADLESS` | No | `true` | Run browser in headless mode. Set `false` for local debugging |
| `TINAA_PLAYWRIGHT_TIMEOUT_MS` | No | `30000` | Default step timeout in milliseconds |

### Example `.env` File

```bash
# Database
TINAA_DATABASE_URL=postgresql+asyncpg://tinaa:tinaa@localhost:5432/tinaa
TINAA_REDIS_URL=redis://localhost:6379/0

# API Security
TINAA_API_KEY=change-me-before-production
TINAA_API_KEY_REQUIRED=true
TINAA_CORS_ORIGINS=https://app.mycompany.com,https://tinaa.mycompany.com

# GitHub App
TINAA_GITHUB_APP_ID=123456
TINAA_GITHUB_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----
MIIEowIBAAK...
-----END RSA PRIVATE KEY-----"
TINAA_GITHUB_WEBHOOK_SECRET=a-long-random-secret

# Email alerts
TINAA_SMTP_HOST=smtp.sendgrid.net
TINAA_SMTP_PORT=587
TINAA_SMTP_USERNAME=apikey
TINAA_SMTP_PASSWORD=SG.xxxxxxxx
TINAA_ALERT_EMAIL_FROM=tinaa-alerts@mycompany.com
TINAA_ALERT_EMAIL_TO=oncall@mycompany.com,qa-team@mycompany.com

# Logging
TINAA_LOG_LEVEL=INFO
TINAA_MODE=api
```

---

## `.tinaa.yml` — Per-Repository Configuration

Place a `.tinaa.yml` file in the root of any repository that TINAA monitors. TINAA reads this file during codebase exploration and uses it to configure quality gates, environments, alerts, and testing behaviour specific to that product.

### Complete Annotated Example

```yaml
# .tinaa.yml
# ---------------------------------------------------------------
# Product identity
# ---------------------------------------------------------------
product_name: "Checkout Service"
team: "payments-team"
description: "Cart, payment processing, and order confirmation"
tags:
  - payments
  - customer-facing
  - critical

# ---------------------------------------------------------------
# Paths to exclude from codebase analysis and test generation
# ---------------------------------------------------------------
ignore_paths:
  - "tests/**"
  - "docs/**"
  - "scripts/**"
  - "**/__pycache__/**"

# ---------------------------------------------------------------
# Environments — maps to TINAA product environments
# ---------------------------------------------------------------
environments:
  - name: production
    url: "https://checkout.myapp.com"
    env_type: production
    monitoring:
      interval: "5m"           # how often to run synthetic checks
      endpoints:
        - path: "/"
          method: GET
          endpoint_type: page
          performance_budget_ms: 1000
          lcp_budget_ms: 2500
          cls_budget: 0.1
          expected_status: 200
        - path: "/checkout"
          method: GET
          endpoint_type: page
          performance_budget_ms: 1500
          lcp_budget_ms: 2500
          expected_status: 200
        - path: "/api/cart"
          method: GET
          endpoint_type: api
          performance_budget_ms: 200
          expected_status: 200
        - path: "/health"
          method: GET
          endpoint_type: health
          performance_budget_ms: 50
          expected_status: 200

  - name: staging
    url: "https://checkout-staging.myapp.com"
    env_type: staging
    monitoring:
      interval: "15m"
      endpoints:
        - path: "/"
          endpoint_type: page
          performance_budget_ms: 1000
        - path: "/checkout"
          endpoint_type: page
          performance_budget_ms: 2000

# ---------------------------------------------------------------
# Quality gates — block deployments below threshold
# ---------------------------------------------------------------
quality_gates:
  # Gate applied to all environments unless overridden
  default:
    min_score: 75
    no_critical_failures: true
    max_performance_regression_percent: 20
    max_new_accessibility_violations: 0

  # Stricter gate for production deployments
  production:
    min_score: 85
    no_critical_failures: true
    max_performance_regression_percent: 10
    max_new_accessibility_violations: 0

  # Looser gate for staging (allows iterative development)
  staging:
    min_score: 65
    no_critical_failures: true
    max_performance_regression_percent: 30
    max_new_accessibility_violations: 5

# ---------------------------------------------------------------
# Testing behaviour
# ---------------------------------------------------------------
testing:
  # Cron schedule for nightly full-suite runs (UTC)
  schedule: "0 2 * * *"    # 2am UTC every day

  # Run smoke suite on every deployment
  on_deploy: true

  # Run smoke suite as a GitHub Check Run on every PR
  on_pr: true

  # Browsers for cross-browser testing (playbook runs always use chromium by default)
  browsers:
    - chromium
    - firefox

  # Viewports to test (playbooks run once per viewport unless overridden)
  viewports:
    - name: desktop
      width: 1440
      height: 900
    - name: mobile
      width: 375
      height: 812

  # Run playbooks in parallel (requires more resources)
  parallel: false

  # Retry failed steps N times before marking as failed
  retries: 1

  # Per-step timeout in milliseconds
  timeout_ms: 30000

# ---------------------------------------------------------------
# Alerts — notification channels and rules
# ---------------------------------------------------------------
alerts:
  channels:
    - type: slack
      config:
        webhook_url: "${SLACK_WEBHOOK_URL}"
        channel: "#checkout-alerts"

    - type: pagerduty
      config:
        routing_key: "${PAGERDUTY_KEY}"
        severity_threshold: critical   # only critical alerts create PagerDuty incidents

    - type: email
      config:
        to:
          - oncall@mycompany.com
        from: tinaa-alerts@mycompany.com

  rules:
    # Fire when quality score drops by 10+ points
    - condition: quality_score_drop
      threshold:
        drop_amount: 10
      severity: warning
      channels: [slack]
      cooldown_minutes: 60

    # Fire when quality score falls below 70
    - condition: quality_score_below
      threshold:
        min_score: 70
      severity: critical
      channels: [slack, pagerduty, email]
      cooldown_minutes: 30

    # Fire when an endpoint goes down (3 consecutive failures)
    - condition: endpoint_down
      threshold:
        consecutive_failures: 3
      severity: critical
      channels: [slack, pagerduty]
      cooldown_minutes: 10

    # Fire when P95 response time exceeds 2 seconds
    - condition: endpoint_degraded
      threshold:
        max_response_time_ms: 2000
      severity: warning
      channels: [slack]
      cooldown_minutes: 30

    # Fire if a test suite has any failures
    - condition: test_suite_failure
      threshold:
        max_failures: 0
      severity: warning
      channels: [slack]
      cooldown_minutes: 60
```

### Configuration Reference by Section

#### `product_name`, `team`, `description`, `tags`

Metadata fields that appear in reports, GitHub issues, and alert messages. `tags` are free-form labels you can use to group or filter products.

#### `ignore_paths`

Glob patterns for paths that TINAA should skip during codebase exploration. Use this to exclude test files, generated code, and documentation from analysis.

#### `environments`

Defines the deployment environments TINAA monitors for this product. Each environment entry:

| Field | Type | Description |
|---|---|---|
| `name` | string | Environment name — must be unique within the product |
| `url` | string | Base URL for this environment |
| `env_type` | string | One of `production`, `staging`, `preview`, `development` |
| `monitoring.interval` | string | Check frequency. Human-readable: `30s`, `5m`, `15m`, `1h` |
| `monitoring.endpoints` | list | Endpoints to monitor within this environment |

Each endpoint in `monitoring.endpoints`:

| Field | Type | Description |
|---|---|---|
| `path` | string | URL path, e.g. `/checkout` |
| `method` | string | HTTP method (default: `GET`) |
| `endpoint_type` | string | `page`, `api`, or `health` |
| `performance_budget_ms` | integer | Response time budget. Score degrades linearly to zero at 2× |
| `lcp_budget_ms` | float | LCP budget in milliseconds |
| `cls_budget` | float | CLS budget (unitless score) |
| `expected_status` | integer | Expected HTTP status code (default: 200) |

#### `quality_gates`

Quality gate configurations keyed by environment name, with a `default` fallback. When a gate check is evaluated (on deployment or on PR), TINAA applies the gate matching the target environment. If no environment-specific gate exists, `default` is used.

| Field | Type | Description |
|---|---|---|
| `min_score` | float | Minimum composite quality score (0–100) required to pass |
| `no_critical_failures` | boolean | Block if any critical test failures exist |
| `max_performance_regression_percent` | float | Block if performance degraded by more than N% |
| `max_new_accessibility_violations` | integer | Block if new WCAG violations were introduced |

#### `testing`

Controls when and how playbooks run.

| Field | Type | Description |
|---|---|---|
| `schedule` | string | Cron expression for scheduled full-suite runs (UTC) |
| `on_deploy` | boolean | Run smoke suite after every deployment |
| `on_pr` | boolean | Run smoke suite as a GitHub Check Run on every PR |
| `browsers` | list | Browsers to use: `chromium`, `firefox`, `webkit` |
| `viewports` | list | Browser viewport sizes. Each entry needs `name`, `width`, `height` |
| `parallel` | boolean | Run playbooks concurrently |
| `retries` | integer | Retry failed steps N times before marking the step as failed |
| `timeout_ms` | integer | Default timeout per step in milliseconds |

#### `alerts.channels`

Notification channel definitions. Reference environment variables with `${VAR_NAME}` syntax — TINAA resolves these at startup.

| Channel type | Required config keys |
|---|---|
| `slack` | `webhook_url`, optionally `channel` |
| `email` | `to` (list), `from` |
| `webhook` | `url`, optionally `headers` (dict), `secret` |
| `pagerduty` | `routing_key`, optionally `severity_threshold` |

#### `alerts.rules`

Custom alert rules for this product. The `condition` field must be one of the supported `AlertConditionType` values (see [Alerts documentation](alerts.md)).

---

## Configuration Loading Order

TINAA resolves configuration in the following priority order (highest to lowest):

1. Environment variables (`TINAA_*`)
2. `.tinaa.yml` in the product's repository root
3. Product settings in the TINAA database (set via UI or API)
4. Built-in defaults

---

## Next Steps

- [Getting Started](getting-started.md) — install TINAA and set up the first product
- [GitHub Integration](integrations.md) — configure GitHub App credentials
- [Alerts](alerts.md) — set up notification channels
- [Quality Scores](quality-scores.md) — understand how quality gate thresholds affect deployment
