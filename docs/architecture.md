---
layout: page
title: "Architecture"
description: "System architecture, agent design, data flow, and technology stack for TINAA MSP v2.0"
---

# Architecture

TINAA MSP is an agent-based continuous quality platform. It fuses automated Playwright browser testing with application performance monitoring (APM) through a multi-agent architecture, delivering continuous quality intelligence across every deployment.

---

## System Overview

```
                             ┌─────────────────────────────────────────────┐
                             │              TINAA MSP v2.0                 │
                             │                                             │
  ┌──────────────┐           │  ┌──────────────────────────────────────┐  │
  │  Web Browser │◄──────────┼──│         SPA Frontend                │  │
  │  (Dashboard) │           │  │   Web Components · No Build Step    │  │
  └──────────────┘           │  └──────────────┬───────────────────────┘  │
                             │                 │ REST / WebSocket          │
  ┌──────────────┐           │  ┌──────────────▼───────────────────────┐  │
  │  Claude / AI │◄──────────┼──│        FastAPI REST API             │  │
  │  IDE (MCP)   │   MCP 2.0 │  │    /api/v1/* · /health · /ws/*      │  │
  └──────────────┘           │  └──────────────┬───────────────────────┘  │
                             │                 │                           │
  ┌──────────────┐           │  ┌──────────────▼───────────────────────┐  │
  │   GitHub     │──webhook──┼──│          Orchestrator               │  │
  │   Webhooks   │           │  │   Routes events to sub-agents       │  │
  └──────────────┘           │  └────┬──────┬──────┬──────┬───────────┘  │
                             │       │      │      │      │               │
                             │   ┌───▼──┐ ┌─▼───┐ │  ┌───▼──────────┐   │
                             │   │Explo-│ │Test │ │  │   APM Agent  │   │
                             │   │rer   │ │Desig│ │  │(Metrics coll.)│  │
                             │   └──────┘ └──┬──┘ │  └──────────────┘   │
                             │               │    │                       │
                             │          ┌────▼──┐ │  ┌──────────────┐   │
                             │          │ Test  │ │  │   Analyst    │   │
                             │          │Runner │ │  │(Correlation/ │   │
                             │          │(PW)   │ │  │  Scoring)    │   │
                             │          └───────┘ │  └──────────────┘   │
                             │                    │                       │
                             │               ┌────▼──────────────────┐   │
                             │               │       Reporter         │   │
                             │               │  Slack/Email/Webhook   │   │
                             │               └───────────────────────┘   │
                             │                                             │
                             │  ┌───────────────┐  ┌───────────────────┐ │
                             │  │  PostgreSQL   │  │       Redis       │ │
                             │  │ + TimescaleDB │  │  (cache / queue)  │ │
                             │  └───────────────┘  └───────────────────┘ │
                             └─────────────────────────────────────────────┘
```

---

## Agent-Based Architecture

TINAA MSP is built around seven purpose-specific agents that communicate through an event-driven orchestration layer. Each agent has a single well-defined responsibility and is independently testable.

### Orchestrator

**File:** `tinaa/agents/orchestrator.py`

The Orchestrator is the lead agent. It receives external events, translates them into `AgentTask` objects, and dispatches work to the appropriate sub-agent. No business logic lives in the orchestrator — it is purely a router and task dispatcher.

**Events handled**

| Event type | Trigger | Agents invoked |
|-----------|---------|----------------|
| `product_registered` | New product added via API or MCP | Explorer |
| `deployment_detected` | GitHub deployment webhook received | Test Runner, APM Agent |
| `pr_opened` | GitHub pull request opened or updated | Test Designer, Test Runner |
| `schedule_triggered` | Cron-based periodic scan | APM Agent, Test Runner |
| `anomaly_detected` | APM Agent flags a metric anomaly | Analyst, Reporter |
| `manual_request` | User-triggered run via API or MCP | Test Runner |

Sub-agents register themselves with `orchestrator.register_agent(agent)`. Additional event handlers can be added with `orchestrator.on_event(event_type, handler)`.

---

### Explorer

**File:** `tinaa/agents/explorer.py`

The Explorer provides codebase intelligence. When a product is first registered — or when triggered manually — the Explorer clones or reads the repository and builds a map of:

- HTTP routes and API endpoints
- HTML forms and their fields
- Inferred user journeys (sequences of pages that form a complete workflow)
- Authentication boundaries

This information populates the product's endpoint registry and seeds test suggestions. The Explorer output is the primary input for the Test Designer.

---

### Test Designer

**File:** `tinaa/agents/test_designer.py`

The Test Designer generates Playwright playbooks from Explorer output or changed-file diffs. Given a list of routes, user journeys, or modified files, it produces structured playbook definitions with:

- Ordered step sequences (`navigate`, `click`, `fill`, `assert_text`, etc.)
- Assertion rules for expected state
- Performance gates (LCP, CLS thresholds)
- Tagging by suite type (`smoke`, `regression`, `accessibility`)

Playbooks are validated by the `PlaybookValidator` before being saved.

---

### Test Runner

**File:** `tinaa/agents/test_runner.py`

The Test Runner executes playbooks against target environments using Microsoft Playwright. It drives Chromium in headless mode and captures:

- Pass/fail status for every step
- Step-level screenshots on failure
- Browser console logs
- Network request/response pairs
- Core Web Vitals (LCP, CLS, INP) via the CDP performance API

Execution results are persisted to `test_runs` and `test_results` tables. Live step progress is pushed to connected WebSocket clients via `ConnectionManager`.

---

### APM Agent

**File:** `tinaa/agents/analyst.py` (shared with Analyst)

The APM Agent continuously monitors registered endpoints by polling their URLs and recording `MetricDatapoint` records for:

- Response time (P50, P95, P99)
- Time to First Byte (TTFB)
- First Contentful Paint (FCP)
- Largest Contentful Paint (LCP)
- Cumulative Layout Shift (CLS)
- Availability
- Error rate
- HTTP status codes

The `BaselineManager` computes statistical baselines from historical data (minimum 30 samples). The `AnomalyDetector` fires an `anomaly_detected` event when a metric deviates beyond a configured number of standard deviations from baseline.

---

### Analyst

**File:** `tinaa/agents/analyst.py`

The Analyst correlates test results, APM metrics, security findings, and accessibility scores to produce the composite **Quality Score**. The score is computed by `QualityScorer` using a weighted formula:

| Component | Weight | Inputs |
|-----------|--------|--------|
| Test health | 35% | Pass rate, flakiness rate, run frequency |
| Performance health | 30% | P95 response time, LCP, SLO compliance |
| Security posture | 20% | Open findings by severity, last scan age |
| Accessibility | 15% | WCAG violations, warnings, coverage |

The Analyst also identifies trends (7-day and 30-day) and generates prioritised recommendations.

---

### Reporter

**File:** `tinaa/agents/reporter.py`

The Reporter delivers quality intelligence to humans through multiple channels:

- **Dashboard** — quality scores, trends, and issue lists rendered by the SPA
- **WebSocket** — live push of test progress, quality updates, alerts
- **Alert engine** — fires configured alert rules and delivers notifications
- **API responses** — quality reports available via `GET /api/v1/quality/{id}/report`

---

## Data Flow

The end-to-end lifecycle from product registration to quality report:

```
1. Product Registration
   └─ POST /api/v1/products (REST) or register_product (MCP)
      └─ Orchestrator receives product_registered event
         └─ Explorer scans repository → discovers routes, APIs, forms, journeys

2. Test Generation
   └─ Test Designer receives Explorer output
      └─ Generates playbook definitions for each discovered journey
         └─ PlaybookValidator checks steps
            └─ Playbooks saved to database

3. Execution Trigger
   └─ GitHub deployment webhook → deployment_detected event
      OR  Cron schedule → schedule_triggered event
      OR  Manual API call → POST /api/v1/test-runs
         └─ Orchestrator dispatches to Test Runner

4. Test Execution
   └─ Test Runner loads playbook steps
      └─ Playwright drives Chromium against target environment
         └─ Each step: execute → capture screenshot / logs / metrics
            └─ Live progress → WebSocket → Dashboard
               └─ Results persisted → test_runs, test_results tables

5. APM Collection (continuous, parallel to test execution)
   └─ APM Agent polls registered endpoints
      └─ MetricDatapoints saved to TimescaleDB hypertable
         └─ BaselineManager recomputes baselines
            └─ AnomalyDetector compares to baseline
               └─ If anomaly: anomaly_detected event → Orchestrator → Reporter

6. Quality Scoring
   └─ Analyst receives test results + APM metrics
      └─ QualityScorer computes weighted composite score
         └─ QualityScoreSnapshot saved to database
            └─ quality_score updated on Product record

7. Reporting
   └─ Reporter delivers to configured channels
      └─ Dashboard: quality_update pushed via WebSocket
         └─ Alerts: alert rules evaluated → notifications sent
            └─ API: GET /api/v1/quality/{id}/report returns full report
```

---

## Technology Stack

| Layer | Technology | Version | Purpose |
|-------|-----------|---------|---------|
| Language | Python | 3.11+ | Application runtime |
| Web framework | FastAPI | 0.115+ | REST API, WebSocket |
| ASGI server | Uvicorn | 0.30+ | Production server |
| Data validation | Pydantic | 2.x | Request/response schemas |
| ORM | SQLAlchemy | 2.0 | Database models, async queries |
| Migrations | Alembic | 1.13+ | Schema versioning |
| Primary database | PostgreSQL | 16 | Relational data store |
| Time-series extension | TimescaleDB | 2.x | Hypertables for metrics |
| Cache / queue | Redis | 7 | Response caching, task queuing |
| Browser automation | Playwright | 1.46+ | Test execution (Chromium) |
| MCP protocol | FastMCP | 2.0+ | AI / IDE integration |
| Container runtime | Docker | 24+ | Packaging and deployment |
| Orchestration | Kubernetes | 1.28+ | Production cluster deployment |
| Frontend | Vanilla JS | ES2022 | SPA (no build step) |
| HTTP client | httpx | 0.27+ | Outbound HTTP requests |
| Auth | PyJWT + cryptography | 2.8+ / 42+ | API key and JWT validation |

---

## Database Schema

TINAA MSP manages thirteen tables across three logical groups.

### Schema overview

```
Organizations & Identity
  organizations          - top-level tenant container

Products & Configuration
  products               - registered software products
  environments           - deployment environments per product

Testing
  playbooks              - test playbook definitions (steps as JSON)
  test_runs              - individual playbook execution records
  test_results           - per-step outcomes within a test run
  deployments            - deployment events that trigger test runs

Monitoring & Metrics
  endpoints              - discovered HTTP endpoints per environment
  metric_datapoints      - raw APM observations (TimescaleDB hypertable)
  metric_baselines       - computed statistical baselines per endpoint

Quality & Alerting
  quality_score_snapshots - point-in-time quality score records
  alert_rules            - configured alert conditions per product
  alert_events           - fired alert instances
```

### Key relationships

```
organizations
    └── products (organization_id FK)
          ├── environments (product_id FK)
          │     ├── endpoints (environment_id FK)
          │     │     ├── metric_datapoints (endpoint_id FK)
          │     │     └── metric_baselines (endpoint_id FK)
          │     ├── test_runs (environment_id FK)
          │     │     └── test_results (test_run_id FK)
          │     └── deployments (environment_id FK)
          ├── playbooks (product_id FK)
          │     └── test_runs (playbook_id FK, nullable)
          ├── quality_score_snapshots (product_id FK)
          └── alert_rules (product_id FK)
                └── alert_events (rule_id FK)
```

### TimescaleDB hypertable

`metric_datapoints` is a TimescaleDB hypertable partitioned by the `timestamp` column. This provides:

- Automatic chunk management for time-series workloads
- Native compression after a configurable interval
- Efficient time-range queries with chunk exclusion
- `time_bucket()` functions for downsampling

The TimescaleDB extension is installed automatically when the database is first created using the `timescale/timescaledb:latest-pg16` Docker image.

---

## Frontend Architecture

The dashboard is a single-page application built with vanilla JavaScript and Web Components. It requires no build step, no `npm install`, and no bundler — the HTML, CSS, and JavaScript are served directly by FastAPI as static files.

### Design principles

- **Zero dependencies** — standard browser APIs only; no React, Vue, or Angular
- **Web Components** — custom elements encapsulate dashboard widgets
- **ES modules** — native `import`/`export` syntax, no transpilation needed
- **Progressive enhancement** — dashboard degrades gracefully without JavaScript

### File layout

```
tinaa/frontend/
  index.html          - dashboard shell
  products.html       - products list page
  assets/
    app.js            - application bootstrap and routing
    components/       - Web Component definitions
      quality-card.js
      metric-chart.js
      test-run-table.js
      alert-badge.js
    styles/
      main.css
      components.css
```

### WebSocket integration

The frontend maintains a single persistent WebSocket connection per page load. The `ConnectionManager` on the server routes push messages back to each connected client by `client_id`. The dashboard subscribes to product-scoped events with:

```javascript
ws.send(JSON.stringify({ type: 'subscribe', product_id: productId }));
```

Updates are applied reactively — quality score cards update without page refresh when a `quality_update` message arrives.

---

## MCP Integration Architecture

TINAA MSP runs the FastMCP 2.0 server on the same port (`8765`) as the REST API, using a different transport path. AI assistants (Claude, Cursor, VS Code with MCP extensions) connect to the MCP endpoint and interact with TINAA through the 14 registered tools.

```
AI Assistant (Claude / IDE)
        │
        │  MCP 2.0 protocol (stdio or HTTP/SSE)
        ▼
FastMCP Server (tinaa/mcp_server/server.py)
        │
        ├── tools.py         ← 14 tool functions registered via add_tool()
        ├── resources.py     ← static resource definitions
        └── _mcp.py          ← shared FastMCP instance
        │
        ▼
Services Layer (tinaa/services.py)
        │
        ├── RegistryService  ← product CRUD
        ├── QualityScorer    ← composite score calculation
        ├── BaselineManager  ← statistical baselines
        ├── AnomalyDetector  ← anomaly detection
        ├── AlertEngine      ← alert rule evaluation
        └── PlaybookValidator← step validation
```

Tools are plain `async` functions decorated with standard Python type annotations. FastMCP generates the JSON schema for each tool's parameter list from the type hints and docstrings. This means every MCP tool is also directly callable in unit tests without going through the protocol wrapper.

### MCP server mode

Start in MCP-only mode (no REST API) with:

```bash
TINAA_MODE=mcp uvicorn tinaa.api.app:app --host 0.0.0.0 --port 8765
```

Or in Docker:

```bash
docker run -e TINAA_MODE=mcp ghcr.io/aj-geddes/tinaa-playwright-msp:latest
```

---

## Event-Driven Architecture

The Orchestrator implements a lightweight event bus. Events flow in one direction: external trigger → Orchestrator → agent tasks → results.

### Event lifecycle

```
External trigger (webhook / API call / schedule)
        │
        ▼
orchestrator.handle_event(event_type, payload)
        │
        ▼
_build_tasks_for_event()     ← maps event → AgentTask list
        │
        ▼
dispatch_task(task)          ← routes task to registered agent by name
        │
        ▼
agent.execute(task)          ← agent performs its work
        │
        ├── SUCCESS → task.status = completed
        └── FAILURE → task.status = failed, task.error_message set
```

### Registering a custom handler

```python
from tinaa.agents.orchestrator import Orchestrator, DEPLOYMENT_DETECTED

orchestrator = Orchestrator()

@orchestrator.on_event(DEPLOYMENT_DETECTED)
async def notify_slack(payload: dict) -> None:
    # custom side-effect after deployment detected
    await slack_client.post(channel="#releases", text=f"Deployed {payload['commit_sha']}")
```

### Extending with new agents

1. Subclass `BaseAgent` from `tinaa/agents/base.py`
2. Implement `execute(task: AgentTask) -> AgentTask`
3. Register with `orchestrator.register_agent(MyAgent())`
4. Add a new event constant and task builder in `orchestrator._build_tasks_for_event()`

The base class provides structured logging, status tracking, and error handling so custom agents only need to implement their core logic.

---

## Security Architecture

TINAA MSP follows a defence-in-depth approach:

| Layer | Control |
|-------|---------|
| Network | Kubernetes NetworkPolicy restricts pod-to-pod traffic; Ingress enforces TLS |
| Authentication | API key via `X-API-Key` header; HMAC-SHA256 webhook signature validation |
| Input validation | Pydantic v2 validates all request bodies at the API boundary |
| Database | SQLAlchemy parameterised queries prevent SQL injection |
| Secrets | Kubernetes Secrets / environment variables; never hardcoded or logged |
| Dependencies | `pip audit` / `safety` scans in CI; Dependabot auto-updates |

GitHub webhook payloads are validated against `GITHUB_WEBHOOK_SECRET` using HMAC-SHA256 before any processing begins. Requests with an invalid or missing signature return `401 Unauthorized`.
