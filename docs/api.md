---
layout: page
title: "API Reference"
description: "Complete REST API, MCP tools, and WebSocket reference for TINAA MSP v2.0"
---

# API Reference

TINAA MSP exposes three API surfaces: a **REST API** over HTTP, **14 MCP tools** via the FastMCP 2.0 protocol, and a **WebSocket** endpoint for real-time streaming. All REST endpoints are served on port `8765` and are prefixed with `/api/v1/`.

The interactive OpenAPI docs are available at `http://localhost:8765/api/docs` when the server is running.

---

## Authentication

When `TINAA_API_KEY` is configured, include the key in every request:

```
X-API-Key: <your-api-key>
```

Unauthenticated requests return `401 Unauthorized`.

---

## Base URL

```
http://localhost:8765
```

All REST endpoints below are relative to this base URL.

---

## Products API

### List products

```
GET /api/v1/products
```

Returns all products registered in the platform, optionally filtered.

**Query parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `status` | string | Filter by status: `active`, `paused`, or `archived` |
| `search` | string | Case-insensitive substring match on product name |
| `sort` | string | Sort field. Supported: `name`, `created_at`, `quality_score` |

**Response** `200 OK`

```json
[
  {
    "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "name": "Checkout Service",
    "slug": "checkout-service",
    "repository_url": "https://github.com/example/checkout-service",
    "description": "Handles cart and payment flows",
    "quality_score": 87.4,
    "status": "active",
    "created_at": "2026-01-15T10:23:44.123456+00:00"
  }
]
```

**Example**

```bash
curl -s http://localhost:8765/api/v1/products?status=active \
  -H "X-API-Key: $TINAA_API_KEY" | jq .
```

---

### Register a product

```
POST /api/v1/products
```

Registers a new product for quality management.

**Request body**

```json
{
  "name": "Checkout Service",
  "description": "Handles cart and payment flows",
  "repository_url": "https://github.com/example/checkout-service",
  "environments": {
    "production": "https://checkout.example.com",
    "staging": "https://staging-checkout.example.com"
  }
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | yes | Human-readable product name |
| `description` | string | no | Optional description |
| `repository_url` | string | no | Git repository URL |
| `environments` | object | no | Map of environment name to base URL |

**Response** `201 Created`

```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "name": "Checkout Service",
  "slug": "checkout-service",
  "repository_url": "https://github.com/example/checkout-service",
  "description": "Handles cart and payment flows",
  "quality_score": null,
  "status": "active",
  "environments": [
    {"name": "production", "base_url": "https://checkout.example.com", "env_type": "production"},
    {"name": "staging", "base_url": "https://staging-checkout.example.com", "env_type": "production"}
  ],
  "created_at": "2026-03-23T09:00:00.000000+00:00"
}
```

**Example**

```bash
curl -s -X POST http://localhost:8765/api/v1/products \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $TINAA_API_KEY" \
  -d '{
    "name": "Checkout Service",
    "repository_url": "https://github.com/example/checkout",
    "environments": {"production": "https://checkout.example.com"}
  }' | jq .
```

---

### Get product details

```
GET /api/v1/products/{id}
```

Returns full product details. The `{id}` segment accepts either a UUID or the product slug.

**Path parameters**

| Parameter | Description |
|-----------|-------------|
| `id` | Product UUID or slug |

**Response** `200 OK`

```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "name": "Checkout Service",
  "slug": "checkout-service",
  "repository_url": "https://github.com/example/checkout-service",
  "description": "Handles cart and payment flows",
  "quality_score": 87.4,
  "status": "active",
  "environments": null,
  "created_at": "2026-01-15T10:23:44.123456+00:00"
}
```

**Example**

```bash
curl -s http://localhost:8765/api/v1/products/checkout-service \
  -H "X-API-Key: $TINAA_API_KEY" | jq .
```

---

### Update product

```
PUT /api/v1/products/{id}
```

Partially updates product fields (PATCH semantics — omitted fields are unchanged).

**Request body**

```json
{
  "name": "Checkout Service v2",
  "status": "paused",
  "description": "Updated description"
}
```

**Response** `200 OK` — updated product object (same shape as GET).

**Example**

```bash
curl -s -X PUT http://localhost:8765/api/v1/products/checkout-service \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $TINAA_API_KEY" \
  -d '{"status": "paused"}' | jq .
```

---

### Delete product

```
DELETE /api/v1/products/{id}
```

Permanently deletes a product and all associated data (cascading).

**Response** `204 No Content`

**Example**

```bash
curl -s -X DELETE http://localhost:8765/api/v1/products/checkout-service \
  -H "X-API-Key: $TINAA_API_KEY"
```

---

### List environments

```
GET /api/v1/products/{id}/environments
```

Returns all environments registered for a product.

**Response** `200 OK`

```json
[
  {
    "id": "7a1b3c5d-9e2f-4a8b-b6d0-1c2e3f4a5b6c",
    "product_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "name": "production",
    "base_url": "https://checkout.example.com",
    "env_type": "production",
    "monitoring_interval_seconds": 300,
    "is_active": true,
    "created_at": "2026-01-15T10:23:44.123456+00:00"
  }
]
```

**Example**

```bash
curl -s "http://localhost:8765/api/v1/products/checkout-service/environments" \
  -H "X-API-Key: $TINAA_API_KEY" | jq .
```

---

### Add environment

```
POST /api/v1/products/{id}/environments
```

Adds a new deployment environment to a product.

**Request body**

```json
{
  "name": "staging",
  "url": "https://staging.checkout.example.com",
  "type": "staging"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | yes | Environment name (e.g. `production`, `staging`) |
| `url` | string | yes | Base URL for the environment |
| `type` | string | no | Environment type. One of `production`, `staging`, `preview`. Defaults to `staging` |

**Response** `201 Created` — environment object.

**Example**

```bash
curl -s -X POST "http://localhost:8765/api/v1/products/checkout-service/environments" \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $TINAA_API_KEY" \
  -d '{"name": "staging", "url": "https://staging.checkout.example.com", "type": "staging"}' | jq .
```

---

## Playbooks API

### List playbooks

```
GET /api/v1/playbooks
```

Returns all playbooks, optionally scoped to a product or suite type.

**Query parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `product_id` | UUID | Filter by product |
| `suite_type` | string | Filter by suite type: `smoke`, `regression`, `accessibility`, `security`, `full` |

**Response** `200 OK`

```json
[
  {
    "id": "pb-a1b2c3d4",
    "name": "checkout-regression",
    "product_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "suite_type": "regression",
    "step_count": 14,
    "status": "active",
    "last_run_at": "2026-03-23T08:00:00.000000+00:00",
    "created_at": "2026-01-20T12:00:00.000000+00:00"
  }
]
```

**Example**

```bash
curl -s "http://localhost:8765/api/v1/playbooks?product_id=3fa85f64-5717-4562-b3fc-2c963f66afa6" \
  -H "X-API-Key: $TINAA_API_KEY" | jq .
```

---

### Create playbook

```
POST /api/v1/playbooks
```

Creates a new test playbook.

**Request body**

```json
{
  "name": "checkout-smoke",
  "product_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "suite_type": "smoke",
  "steps": [
    {"action": "navigate", "url": "https://checkout.example.com"},
    {"action": "click", "selector": "#add-to-cart"},
    {"action": "click", "selector": "#checkout-btn"},
    {"action": "assert_text", "selector": "h1", "text": "Order Confirmed"}
  ]
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | string | yes | Playbook name |
| `product_id` | UUID | yes | Owning product |
| `suite_type` | string | yes | `smoke`, `regression`, `accessibility`, `security`, or `full` |
| `steps` | array | yes | Ordered list of action objects |

**Supported step actions**

| Action | Required params | Description |
|--------|----------------|-------------|
| `navigate` | `url` | Navigate to a URL |
| `click` | `selector` | Click an element |
| `fill` | `selector`, `value` | Fill a form field |
| `assert_text` | `selector`, `text` | Assert element text |
| `assert_url` | `pattern` | Assert URL matches pattern |
| `screenshot` | — | Capture a screenshot |
| `wait` | `ms` | Wait N milliseconds |

**Response** `201 Created`

```json
{
  "id": "pb-a1b2c3d4",
  "name": "checkout-smoke",
  "product_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "suite_type": "smoke",
  "step_count": 4,
  "status": "active",
  "validation_errors": [],
  "created_at": "2026-03-23T09:00:00.000000+00:00"
}
```

**Example**

```bash
curl -s -X POST http://localhost:8765/api/v1/playbooks \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $TINAA_API_KEY" \
  -d '{
    "name": "checkout-smoke",
    "product_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "suite_type": "smoke",
    "steps": [
      {"action": "navigate", "url": "https://checkout.example.com"},
      {"action": "assert_text", "selector": "h1", "text": "Checkout"}
    ]
  }' | jq .
```

---

### Get playbook

```
GET /api/v1/playbooks/{id}
```

Returns playbook details including all steps.

**Response** `200 OK` — full playbook object with `steps` array.

**Example**

```bash
curl -s http://localhost:8765/api/v1/playbooks/pb-a1b2c3d4 \
  -H "X-API-Key: $TINAA_API_KEY" | jq .
```

---

### Execute playbook

```
POST /api/v1/playbooks/{id}/run
```

Triggers an immediate execution of the playbook.

**Request body** (optional)

```json
{
  "environment": "staging",
  "target_url": "https://staging.checkout.example.com"
}
```

**Response** `202 Accepted`

```json
{
  "run_id": "run-8f3a2b1c",
  "playbook_id": "pb-a1b2c3d4",
  "status": "queued",
  "environment": "staging",
  "started_at": "2026-03-23T09:05:00.000000+00:00"
}
```

**Example**

```bash
curl -s -X POST http://localhost:8765/api/v1/playbooks/pb-a1b2c3d4/run \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $TINAA_API_KEY" \
  -d '{"environment": "staging"}' | jq .
```

---

## Test Runs API

### List test runs

```
GET /api/v1/test-runs
```

Returns test run history with optional filters.

**Query parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `product_id` | UUID | Filter by product |
| `status` | string | Filter by status: `queued`, `running`, `passed`, `failed`, `error`, `cancelled` |
| `limit` | integer | Maximum results to return (default: 20, max: 100) |

**Response** `200 OK`

```json
[
  {
    "id": "run-8f3a2b1c",
    "product_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "environment_id": "7a1b3c5d-9e2f-4a8b-b6d0-1c2e3f4a5b6c",
    "playbook_id": "pb-a1b2c3d4",
    "trigger": "manual",
    "status": "passed",
    "started_at": "2026-03-23T08:00:00.000000+00:00",
    "completed_at": "2026-03-23T08:00:42.500000+00:00",
    "duration_ms": 42500,
    "results_summary": {
      "total": 14,
      "passed": 14,
      "failed": 0,
      "skipped": 0
    },
    "quality_score_before": 85.0,
    "quality_score_after": 87.4,
    "created_at": "2026-03-23T08:00:00.000000+00:00"
  }
]
```

**Example**

```bash
curl -s "http://localhost:8765/api/v1/test-runs?status=failed&limit=10" \
  -H "X-API-Key: $TINAA_API_KEY" | jq .
```

---

### Get test run details

```
GET /api/v1/test-runs/{id}
```

Returns full details for a single test run including per-step results.

**Response** `200 OK`

```json
{
  "id": "run-8f3a2b1c",
  "product_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "environment_id": "7a1b3c5d-9e2f-4a8b-b6d0-1c2e3f4a5b6c",
  "playbook_id": "pb-a1b2c3d4",
  "trigger": "deployment",
  "status": "failed",
  "started_at": "2026-03-23T08:00:00.000000+00:00",
  "completed_at": "2026-03-23T08:00:38.200000+00:00",
  "duration_ms": 38200,
  "commit_sha": "a1b2c3d4e5f6",
  "deployment_url": "https://checkout.example.com",
  "results_summary": {
    "total": 14,
    "passed": 12,
    "failed": 2,
    "skipped": 0
  },
  "quality_score_before": 87.4,
  "quality_score_after": 84.1,
  "error_message": null,
  "artifacts_url": "https://storage.example.com/artifacts/run-8f3a2b1c",
  "created_at": "2026-03-23T08:00:00.000000+00:00"
}
```

**Example**

```bash
curl -s http://localhost:8765/api/v1/test-runs/run-8f3a2b1c \
  -H "X-API-Key: $TINAA_API_KEY" | jq .
```

---

### Trigger a test run

```
POST /api/v1/test-runs
```

Manually triggers a test run for a product.

**Request body**

```json
{
  "product_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "environment_id": "7a1b3c5d-9e2f-4a8b-b6d0-1c2e3f4a5b6c",
  "playbook_id": "pb-a1b2c3d4",
  "trigger": "manual",
  "commit_sha": "a1b2c3d4e5f6"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `product_id` | UUID | yes | Target product |
| `environment_id` | UUID | yes | Target environment |
| `playbook_id` | UUID | no | Specific playbook (omit for full suite) |
| `trigger` | string | yes | `manual`, `deployment`, `schedule`, `pr`, or `anomaly` |
| `commit_sha` | string | no | Associated Git commit SHA |

**Response** `202 Accepted`

```json
{
  "id": "run-9d4e5f6a",
  "status": "queued",
  "product_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "environment_id": "7a1b3c5d-9e2f-4a8b-b6d0-1c2e3f4a5b6c",
  "trigger": "manual",
  "created_at": "2026-03-23T09:10:00.000000+00:00"
}
```

**Example**

```bash
curl -s -X POST http://localhost:8765/api/v1/test-runs \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $TINAA_API_KEY" \
  -d '{
    "product_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "environment_id": "7a1b3c5d-9e2f-4a8b-b6d0-1c2e3f4a5b6c",
    "trigger": "manual"
  }' | jq .
```

---

## Metrics API

### Query metrics

```
GET /api/v1/metrics
```

Returns time-series performance metrics for a product or endpoint.

**Query parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `product_id` | UUID | Required. Product to query |
| `metric_type` | string | `response_time`, `ttfb`, `fcp`, `lcp`, `cls`, `inp`, `availability`, `error_rate`. Returns all when omitted |
| `time_range` | string | Lookback window: `1h`, `6h`, `24h`, `7d`, `30d`. Default: `24h` |
| `endpoint_path` | string | Scope to a specific endpoint path (e.g. `/api/checkout`) |

**Response** `200 OK`

```json
{
  "product_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "metric_type": "response_time",
  "time_range": "24h",
  "data_points": [
    {"timestamp": "2026-03-22T09:00:00+00:00", "value": 312.0},
    {"timestamp": "2026-03-22T10:00:00+00:00", "value": 298.0},
    {"timestamp": "2026-03-22T11:00:00+00:00", "value": 340.0}
  ],
  "baseline": {
    "p50": 220.0,
    "p90": 450.0,
    "p99": 900.0,
    "mean": 235.0
  },
  "current_avg": 316.7,
  "trend": "stable"
}
```

**Example**

```bash
curl -s "http://localhost:8765/api/v1/metrics?product_id=3fa85f64-5717-4562-b3fc-2c963f66afa6&metric_type=lcp&time_range=7d" \
  -H "X-API-Key: $TINAA_API_KEY" | jq .
```

---

### Get baselines

```
GET /api/v1/metrics/baselines
```

Returns computed baseline statistics for a product.

**Query parameters**: `product_id` (required), `metric_type` (optional).

**Response** `200 OK`

```json
{
  "product_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "baselines": [
    {
      "metric_type": "response_time",
      "p50": 220.0,
      "p90": 450.0,
      "p99": 900.0,
      "mean": 235.0,
      "std_dev": 68.2,
      "sample_count": 1440,
      "computed_at": "2026-03-23T00:00:00.000000+00:00"
    }
  ]
}
```

**Example**

```bash
curl -s "http://localhost:8765/api/v1/metrics/baselines?product_id=3fa85f64-5717-4562-b3fc-2c963f66afa6" \
  -H "X-API-Key: $TINAA_API_KEY" | jq .
```

---

### Get detected anomalies

```
GET /api/v1/metrics/anomalies
```

Returns metrics anomalies detected by the APM agent.

**Query parameters**: `product_id` (required), `hours` (default: `24`).

**Response** `200 OK`

```json
{
  "product_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "anomalies": [
    {
      "id": "anom-3c4d5e6f",
      "metric_type": "response_time",
      "endpoint_path": "/api/search",
      "detected_at": "2026-03-23T07:42:00.000000+00:00",
      "severity": "warning",
      "current_value": 1240.0,
      "baseline_p99": 900.0,
      "deviation_pct": 37.8,
      "description": "P95 response time 37.8% above baseline on /api/search"
    }
  ]
}
```

**Example**

```bash
curl -s "http://localhost:8765/api/v1/metrics/anomalies?product_id=3fa85f64-5717-4562-b3fc-2c963f66afa6" \
  -H "X-API-Key: $TINAA_API_KEY" | jq .
```

---

## Quality API

### Get quality score

```
GET /api/v1/quality/{product_id}
```

Returns the current composite quality score with component breakdown.

**Path parameters**

| Parameter | Description |
|-----------|-------------|
| `product_id` | Product UUID or slug |

**Query parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `environment` | string | Scope to a specific environment. Returns aggregate when omitted |

**Response** `200 OK`

```json
{
  "product_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "environment": "production",
  "score": 87.4,
  "components": {
    "test_health": {
      "score": 91.0,
      "weight": 0.35,
      "pass_rate": 0.94,
      "flakiness_rate": 0.02
    },
    "performance_health": {
      "score": 84.0,
      "weight": 0.30,
      "p95_ms": 420,
      "lcp_ms": 1800,
      "slo_compliance": 0.98
    },
    "security_posture": {
      "score": 88.0,
      "weight": 0.20,
      "open_findings": 2,
      "critical": 0,
      "high": 0
    },
    "accessibility": {
      "score": 82.0,
      "weight": 0.15,
      "violations": 4,
      "warnings": 11,
      "wcag_level": "AA"
    }
  },
  "trend": "improving",
  "recommendations": [
    "Fix 4 accessibility violations on /checkout to gain +3 points.",
    "Reduce P95 response time below 400 ms to meet SLO."
  ],
  "computed_at": "2026-03-23T09:00:00.000000+00:00"
}
```

**Example**

```bash
curl -s "http://localhost:8765/api/v1/quality/checkout-service?environment=production" \
  -H "X-API-Key: $TINAA_API_KEY" | jq .
```

---

### Quality score history

```
GET /api/v1/quality/{product_id}/history
```

Returns historical quality scores for trend analysis.

**Query parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `days` | integer | Lookback window in days. Default: `30` |
| `environment` | string | Scope to a specific environment |

**Response** `200 OK`

```json
{
  "product_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "history": [
    {"date": "2026-02-22", "score": 82.1, "environment": "production"},
    {"date": "2026-03-01", "score": 84.5, "environment": "production"},
    {"date": "2026-03-15", "score": 86.0, "environment": "production"},
    {"date": "2026-03-23", "score": 87.4, "environment": "production"}
  ],
  "trend_7d": 1.4,
  "trend_30d": 5.3
}
```

**Example**

```bash
curl -s "http://localhost:8765/api/v1/quality/checkout-service/history?days=30" \
  -H "X-API-Key: $TINAA_API_KEY" | jq .
```

---

### Full quality report

```
GET /api/v1/quality/{product_id}/report
```

Generates a comprehensive quality report aggregating all subsystems.

**Response** `200 OK`

```json
{
  "product_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "environment": "all",
  "generated_at": "2026-03-23T09:00:00.000000+00:00",
  "quality_score": 87.4,
  "trend_7d": 1.4,
  "trend_30d": 5.3,
  "test_summary": {
    "total_runs": 124,
    "pass_rate": 0.94,
    "flaky_playbooks": 1,
    "avg_duration_ms": 4200
  },
  "performance_summary": {
    "p50_ms": 210,
    "p95_ms": 420,
    "p99_ms": 890,
    "lcp_ms": 1800,
    "cls": 0.08,
    "slo_compliance": 0.98
  },
  "security_summary": {
    "open_findings": 2,
    "critical": 0,
    "high": 0,
    "medium": 2,
    "last_scan_at": "2026-03-23T06:00:00.000000+00:00"
  },
  "accessibility_summary": {
    "violations": 4,
    "warnings": 11,
    "wcag_level": "AA",
    "score": 82
  },
  "top_issues": [
    {
      "severity": "medium",
      "type": "accessibility",
      "description": "Missing alt text on 3 images in /checkout"
    },
    {
      "severity": "medium",
      "type": "performance",
      "description": "P95 response time exceeds 400 ms SLO on /api/search"
    }
  ],
  "recommendations": [
    "Add alt text to images on /checkout to fix 3 accessibility violations.",
    "Optimise /api/search query to bring P95 below 400 ms.",
    "Schedule nightly full suite run to catch regressions earlier."
  ]
}
```

**Example**

```bash
curl -s http://localhost:8765/api/v1/quality/checkout-service/report \
  -H "X-API-Key: $TINAA_API_KEY" | jq .
```

---

## Alerts API

### List alerts

```
GET /api/v1/alerts
```

Returns active and historical alert events.

**Query parameters**

| Parameter | Type | Description |
|-----------|------|-------------|
| `severity` | string | Filter by severity: `critical`, `warning`, or `info` |
| `status` | string | Filter by status: `open`, `acknowledged`, `resolved` |
| `product_id` | UUID | Filter by product |
| `limit` | integer | Max results to return (default: 50) |

**Response** `200 OK`

```json
[
  {
    "id": "alert-1a2b3c4d",
    "product_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "rule_id": "rule-5e6f7a8b",
    "condition_type": "performance_regression",
    "severity": "warning",
    "status": "open",
    "title": "P95 response time spike on /api/search",
    "description": "Response time 37.8% above baseline — P95: 1240 ms vs baseline: 900 ms",
    "triggered_at": "2026-03-23T07:42:00.000000+00:00",
    "acknowledged_at": null,
    "resolved_at": null
  }
]
```

**Example**

```bash
curl -s "http://localhost:8765/api/v1/alerts?severity=critical&status=open" \
  -H "X-API-Key: $TINAA_API_KEY" | jq .
```

---

### Create alert rule

```
POST /api/v1/alerts/rules
```

Creates a new alert rule for automated monitoring.

**Request body**

```json
{
  "product_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "name": "Quality drop alert",
  "condition_type": "quality_score_drop",
  "severity": "warning",
  "threshold": {"value": 10},
  "channels": ["slack:#engineering-alerts", "email:team@example.com"],
  "enabled": true
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `product_id` | UUID | yes | Product to monitor |
| `name` | string | yes | Human-readable rule name |
| `condition_type` | string | yes | `quality_score_drop`, `test_failure`, `performance_regression`, `endpoint_down`, or `security_issue` |
| `severity` | string | yes | `critical`, `warning`, or `info` |
| `threshold` | object | yes | Condition-specific threshold values |
| `channels` | array | no | Notification channels |
| `enabled` | boolean | no | Whether the rule is active (default: `true`) |

**Response** `201 Created` — created rule object.

**Example**

```bash
curl -s -X POST http://localhost:8765/api/v1/alerts/rules \
  -H "Content-Type: application/json" \
  -H "X-API-Key: $TINAA_API_KEY" \
  -d '{
    "product_id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
    "name": "Quality drop alert",
    "condition_type": "quality_score_drop",
    "severity": "warning",
    "threshold": {"value": 10}
  }' | jq .
```

---

### Acknowledge alert

```
PUT /api/v1/alerts/{id}/acknowledge
```

Marks an alert as acknowledged, suppressing repeat notifications.

**Response** `200 OK`

```json
{
  "id": "alert-1a2b3c4d",
  "status": "acknowledged",
  "acknowledged_at": "2026-03-23T09:15:00.000000+00:00"
}
```

**Example**

```bash
curl -s -X PUT http://localhost:8765/api/v1/alerts/alert-1a2b3c4d/acknowledge \
  -H "X-API-Key: $TINAA_API_KEY" | jq .
```

---

### Resolve alert

```
PUT /api/v1/alerts/{id}/resolve
```

Marks an alert as resolved.

**Response** `200 OK`

```json
{
  "id": "alert-1a2b3c4d",
  "status": "resolved",
  "resolved_at": "2026-03-23T09:30:00.000000+00:00"
}
```

**Example**

```bash
curl -s -X PUT http://localhost:8765/api/v1/alerts/alert-1a2b3c4d/resolve \
  -H "X-API-Key: $TINAA_API_KEY" | jq .
```

---

## Webhooks API

### GitHub webhook receiver

```
POST /api/v1/webhooks/github
```

Receives GitHub webhook events and triggers automated test runs on deployment events and PR updates.

TINAA processes the following GitHub event types:

| GitHub event | Action | TINAA behaviour |
|-------------|--------|-----------------|
| `deployment_status` | `success` | Triggers regression test run against deployment URL |
| `pull_request` | `opened`, `synchronize` | Triggers smoke test run on PR environment |
| `push` | `main` branch | Triggers scheduled suite on production environment |

**Headers required by GitHub**

```
X-GitHub-Event: deployment_status
X-Hub-Signature-256: sha256=<hmac-sha256>
Content-Type: application/json
```

The webhook secret is configured via `GITHUB_WEBHOOK_SECRET`. TINAA validates the HMAC-SHA256 signature on every request.

**Response** `200 OK`

```json
{
  "status": "accepted",
  "event": "deployment_status",
  "run_id": "run-9d4e5f6a"
}
```

**Example** (simulating a GitHub delivery)

```bash
curl -s -X POST http://localhost:8765/api/v1/webhooks/github \
  -H "Content-Type: application/json" \
  -H "X-GitHub-Event: deployment_status" \
  -H "X-Hub-Signature-256: sha256=<computed-hmac>" \
  -d @github_event_payload.json | jq .
```

---

## Health Endpoints

### Health check

```
GET /health
```

Returns service health status. Used as a liveness probe by Docker and Kubernetes.

**Response** `200 OK`

```json
{
  "status": "healthy",
  "version": "2.0.0",
  "timestamp": "2026-03-23T09:00:00.000000+00:00"
}
```

**Example**

```bash
curl -s http://localhost:8765/health | jq .
```

---

### Readiness probe

```
GET /health/ready
```

Returns readiness status — checks database and Redis connectivity. Used as a readiness probe by Kubernetes.

**Response** `200 OK`

```json
{
  "status": "ready",
  "checks": {
    "database": "ok",
    "redis": "ok"
  },
  "timestamp": "2026-03-23T09:00:00.000000+00:00"
}
```

Returns `503 Service Unavailable` when any dependency is not reachable.

**Example**

```bash
curl -s http://localhost:8765/health/ready | jq .
```

---

## Error Responses

All error responses follow a consistent shape:

```json
{
  "detail": "Product 'unknown-slug' not found"
}
```

| Status | Meaning |
|--------|---------|
| `400 Bad Request` | Invalid request body or business logic violation |
| `401 Unauthorized` | Missing or invalid API key |
| `404 Not Found` | Resource does not exist |
| `422 Unprocessable Entity` | Request body failed validation |
| `503 Service Unavailable` | Upstream dependency (database, Redis) unreachable |

---

## MCP Tools

TINAA exposes 14 tools over the FastMCP 2.0 protocol. Connect to the MCP server at port `8765` (same process, same port, different transport).

### Tool index

| # | Tool name | Description |
|---|-----------|-------------|
| 1 | `register_product` | Register a new product for quality management |
| 2 | `list_products` | List all products, optionally filtered by status |
| 3 | `get_product` | Get detailed product info, environments, and recent runs |
| 4 | `get_quality_score` | Get current quality score with component breakdown |
| 5 | `run_playbook` | Execute a specific playbook against an environment |
| 6 | `run_suite` | Run all playbooks for a product/environment |
| 7 | `get_metrics` | Query APM metrics with baseline comparison |
| 8 | `get_test_results` | Get recent test run results |
| 9 | `suggest_tests` | Get test suggestions based on changed files |
| 10 | `create_playbook` | Create a new test playbook |
| 11 | `get_quality_report` | Generate a comprehensive quality report |
| 12 | `configure_alerts` | Configure alert rules for a product |
| 13 | `get_deployments` | Get recent deployments with quality impact |
| 14 | `explore_codebase` | Trigger codebase exploration to discover routes and journeys |

---

### register_product

Registers a new product and associates it with deployment environments.

**Parameters**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `name` | string | yes | Human-readable product name |
| `repo_url` | string | yes | Git repository URL |
| `environments` | object | yes | Map of env name to base URL |
| `description` | string | no | Product description |

**Returns** `dict` — `product_id`, `slug`, `name`, `repo_url`, `environments`, `description`, `status`, `quality_score`, `created_at`

---

### list_products

**Parameters**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `status` | string | no | Filter by `active`, `paused`, or `archived` |

**Returns** `list[dict]` — each item contains `product_id`, `slug`, `name`, `status`, `quality_score`, `environment_count`, `last_run_at`

---

### get_product

**Parameters**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `product_id_or_slug` | string | yes | Product UUID or slug |

**Returns** `dict` — `product_id`, `slug`, `name`, `repo_url`, `environments`, `endpoints`, `quality_score`, `recent_test_runs`, `created_at`, `updated_at`

---

### get_quality_score

**Parameters**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `product_id_or_slug` | string | yes | Product UUID or slug |
| `environment` | string | no | Environment scope |

**Returns** `dict` — `score`, `test_health`, `performance_health`, `security_posture`, `accessibility`, `trend`, `recommendations`

---

### run_playbook

**Parameters**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `playbook_id_or_name` | string | yes | Playbook UUID or name |
| `environment` | string | no | Target environment name |
| `target_url` | string | no | Override base URL for this run |

**Returns** `dict` — `run_id`, `playbook_name`, `environment`, `status`, `results_summary`, `duration_ms`, `quality_score_impact`, `started_at`

---

### run_suite

**Parameters**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `product_id_or_slug` | string | yes | Product UUID or slug |
| `environment` | string | no | Target environment (default: `staging`) |
| `suite_type` | string | no | `regression`, `smoke`, `full`, `security`, `accessibility` (default: `regression`) |

**Returns** `dict` — `run_id`, `playbooks_executed`, `passed`, `failed`, `quality_score`

---

### get_metrics

**Parameters**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `product_id_or_slug` | string | yes | Product UUID or slug |
| `endpoint_path` | string | no | Filter to specific endpoint |
| `metric_type` | string | no | `response_time`, `lcp`, `cls`, `availability`, `error_rate` |
| `hours` | integer | no | Lookback window in hours (default: `24`) |

**Returns** `dict` — `metrics` (list of `{timestamp, value}`), `baseline`, `current_avg`, `trend`

---

### get_test_results

**Parameters**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `product_id_or_slug` | string | yes | Product UUID or slug |
| `limit` | integer | no | Max results (default: `10`) |
| `status` | string | no | Filter by `passed`, `failed`, `error`, `running` |

**Returns** `list[dict]` — each item: `run_id`, `playbook_name`, `status`, `duration_ms`, `passed`, `failed`, `timestamp`

---

### suggest_tests

**Parameters**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `product_id_or_slug` | string | yes | Product UUID or slug |
| `changed_files` | list[string] | no | Changed file paths from the current diff |

**Returns** `list[dict]` — each item: `playbook_name`, `reason`, `priority` (`high`/`medium`/`low`), `affected_journeys`

---

### create_playbook

**Parameters**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `product_id_or_slug` | string | yes | Product UUID or slug |
| `name` | string | yes | Playbook name |
| `steps` | list[dict] | yes | Ordered list of action dicts |
| `assertions` | dict | no | Assertion rules |
| `performance_gates` | dict | no | Performance thresholds (e.g. `{"lcp_ms": 2500}`) |

**Returns** `dict` — `playbook_id`, `name`, `step_count`, `validation_errors`, `status`, `created_at`

---

### get_quality_report

**Parameters**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `product_id_or_slug` | string | yes | Product UUID or slug |
| `environment` | string | no | Environment scope |

**Returns** `dict` — `quality_score`, `trend_7d`, `trend_30d`, `test_summary`, `performance_summary`, `security_summary`, `accessibility_summary`, `top_issues`, `recommendations`

---

### configure_alerts

**Parameters**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `product_id_or_slug` | string | yes | Product UUID or slug |
| `rules` | list[dict] | yes | Alert rule objects |

**Returns** `dict` — `status`, `rules_configured`, `errors`

---

### get_deployments

**Parameters**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `product_id_or_slug` | string | yes | Product UUID or slug |
| `environment` | string | no | Filter by environment |
| `limit` | integer | no | Max results (default: `10`) |

**Returns** `list[dict]` — each item: `deployment_id`, `environment`, `commit_sha`, `url`, `quality_score_delta`, `test_results_summary`, `deployed_at`

---

### explore_codebase

**Parameters**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `product_id_or_slug` | string | yes | Product UUID or slug |

**Returns** `dict` — `routes`, `apis`, `forms`, `user_journeys`

---

## WebSocket

### Real-time test execution streaming

```
WS /ws/{client_id}
```

Establishes a persistent WebSocket connection for real-time updates. The `{client_id}` can be any identifier you choose — it is used to route server-push messages back to the correct connection.

**Connection example** (JavaScript)

```javascript
const ws = new WebSocket('ws://localhost:8765/ws/my-client-001');

ws.onmessage = (event) => {
  const msg = JSON.parse(event.data);
  console.log('Received:', msg);
};

// Subscribe to a product's events
ws.send(JSON.stringify({
  type: 'subscribe',
  product_id: '3fa85f64-5717-4562-b3fc-2c963f66afa6'
}));
```

**Client message types** (sent from browser to server)

| `type` | Additional fields | Description |
|--------|------------------|-------------|
| `ping` | — | Keepalive check; server replies with `{"type": "pong"}` |
| `subscribe` | `product_id` | Subscribe to events for a product |

**Server push message types** (sent from server to browser)

| `type` | Additional fields | Description |
|--------|------------------|-------------|
| `pong` | — | Response to `ping` |
| `subscribed` | `product_id` | Confirms subscription |
| `test_progress` | `run_id`, `progress` | Live test step progress during a run |
| `quality_update` | `product_id`, `score`, `delta` | Quality score changed |
| `alert` | `alert_id`, `severity`, `title` | Alert triggered |
| `deployment` | `deployment_id`, `commit_sha`, `environment` | Deployment event received |

**Test progress payload example**

```json
{
  "type": "test_progress",
  "run_id": "run-8f3a2b1c",
  "progress": {
    "step_index": 7,
    "step_name": "click #checkout-btn",
    "status": "passed",
    "duration_ms": 450,
    "total_steps": 14,
    "steps_completed": 7
  }
}
```
