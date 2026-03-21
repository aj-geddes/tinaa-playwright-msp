# Architecture

TINAA MSP is a Python-based service platform composed of a FastAPI REST API, an MCP (Model Context Protocol) server, a set of AI-powered agents, a PostgreSQL/TimescaleDB database, a Redis queue, and a pool of Playwright browser workers.

---

## System architecture diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                         External clients                        │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────┐   │
│  │  Dashboard   │  │  Claude Code │  │  CI/CD / GitHub    │   │
│  │  (browser)   │  │  (MCP client)│  │  (webhooks + API)  │   │
│  └──────┬───────┘  └──────┬───────┘  └────────┬───────────┘   │
└─────────┼─────────────────┼───────────────────┼───────────────-┘
          │  HTTP/WS        │  MCP              │  HTTP
          ▼                 ▼                   ▼
┌─────────────────┐  ┌─────────────┐  ┌─────────────────┐
│  FastAPI        │  │  MCP Server │  │  Webhook Handler│
│  REST API       │  │  (port 8080)│  │  (/api/v1/webhooks)
│  (port 8765)    │  └──────┬──────┘  └────────┬────────┘
└────────┬────────┘         │                  │
         │                  └──────────────────┘
         │                         │
         ▼                         ▼
┌────────────────────────────────────────────────────────────┐
│                    Service Layer                            │
│  ┌───────────────┐  ┌──────────────┐  ┌─────────────────┐ │
│  │ Registry Svc  │  │  Quality Svc │  │  APM / Metrics  │ │
│  │ (products,    │  │  (scorer,    │  │  (baselines,    │ │
│  │  envs, endpts)│  │   gates,     │  │   anomalies)    │ │
│  └───────────────┘  │   trends)    │  └─────────────────┘ │
│  ┌───────────────┐  └──────────────┘  ┌─────────────────┐ │
│  │  Alert Engine │                     │  GitHub Client  │ │
│  │  (rules,      │                     │  (deployments,  │ │
│  │   channels)   │                     │   checks)       │ │
│  └───────────────┘                     └─────────────────┘ │
└────────────────────────────────────────────────────────────┘
         │                         │
         ▼                         ▼
┌──────────────────┐  ┌────────────────────────────────────────┐
│  Redis (queue)   │  │           Agent Orchestrator           │
│  - test run jobs │  │  ┌──────────┐  ┌──────────────────┐   │
│  - monitoring    │  │  │ Explorer │  │  Test Designer   │   │
│    schedule      │  │  │ (crawl)  │  │  (playbook gen)  │   │
└──────────────────┘  │  └──────────┘  └──────────────────┘   │
                       │  ┌──────────┐  ┌──────────────────┐   │
                       │  │  Runner  │  │  Analyst         │   │
                       │  │(playbook │  │ (quality scoring,│   │
                       │  │ executor)│  │  recommendations)│   │
                       │  └──────────┘  └──────────────────┘   │
                       │  ┌──────────┐  ┌──────────────────┐   │
                       │  │ Reporter │  │  Base Agent      │   │
                       │  │(results) │  │  (shared logic)  │   │
                       │  └──────────┘  └──────────────────┘   │
                       └────────────────────────────────────────┘
                                         │
                                         ▼
                       ┌────────────────────────────────────────┐
                       │       Playwright Browser Pool          │
                       │  ┌──────────┐  ┌──────────────────┐   │
                       │  │ Chromium │  │  Firefox         │   │
                       │  │ (default)│  │  (optional)      │   │
                       │  └──────────┘  └──────────────────┘   │
                       └────────────────────────────────────────┘
                                         │
         ┌───────────────────────────────┘
         ▼
┌────────────────────────────────────────────────────────────┐
│                      Database Layer                        │
│  ┌─────────────────────────────────────────────────────┐  │
│  │  PostgreSQL 15 + TimescaleDB                        │  │
│  │  Regular tables: products, environments, endpoints, │  │
│  │    playbooks, test_runs, alerts, organisations      │  │
│  │  Hypertables: endpoint_metrics, web_vitals          │  │
│  └─────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────┘
```

---

## Component descriptions

### FastAPI REST API (tinaa/api/)

The primary user-facing HTTP interface. Built with FastAPI 0.115+ and served by Uvicorn. Handles all CRUD operations, test run triggering, metric queries, and webhook reception. Exposes OpenAPI docs at `/api/docs`.

Key modules:
- `routes/products.py` — product, environment, and endpoint CRUD
- `routes/playbooks.py` — playbook CRUD and execution trigger
- `routes/test_runs.py` — test run management
- `routes/metrics.py` — time-series metric queries
- `routes/quality.py` — quality score computation and history
- `routes/webhooks.py` — GitHub webhook receiver
- `routes/docs.py` — built-in documentation serving
- `middleware.py` — API key auth, request logging, response timing

### MCP Server (tinaa/mcp_server/)

FastMCP-based server exposing TINAA capabilities to Claude Code and other MCP clients. Provides tools for registering products, running tests, and querying quality scores via natural language. Runs on port 8080.

### Agents (tinaa/agents/)

AI-powered agents that perform higher-level tasks:

| Agent | Responsibility |
|-------|---------------|
| `orchestrator.py` | Coordinates agent execution, manages state |
| `explorer.py` | Crawls target applications to discover user journeys |
| `test_designer.py` | Generates playbook YAML from discovered journeys |
| `test_runner.py` | Executes playbooks via Playwright, collects results |
| `analyst.py` | Computes quality scores, detects regressions, generates recommendations |
| `reporter.py` | Formats test results for GitHub checks, dashboard display |
| `base.py` | Shared agent state, logging, and communication |

### Quality Engine (tinaa/quality/)

Pure Python scoring engine, no external dependencies:

- `scorer.py` — `QualityScorer` class computing the 0–100 composite score
- `gates.py` — deployment gate pass/fail evaluation
- `trends.py` — historical score trend analysis

### Registry Service (tinaa/registry/)

CRUD service for products, environments, and endpoints. Interacts with the database via SQLAlchemy async sessions.

### APM / Metrics (tinaa/apm/)

Continuous monitoring loop that polls endpoints, records metrics to TimescaleDB, runs anomaly detection against baselines, and triggers alert evaluations.

### Alert Engine (tinaa/alerts/)

Rule-based alerting system:
- `rules.py` — alert rule evaluation against metric and test data
- `engine.py` — alert lifecycle management (trigger, acknowledge, resolve)
- `channels.py` — delivery handlers for Slack, email, PagerDuty, GitHub Issues, webhooks

### Database (tinaa/database/)

SQLAlchemy 2.0 async ORM with two backends:
- PostgreSQL + TimescaleDB (production): connection pooling via asyncpg
- SQLite (development): via aiosqlite

Alembic manages schema migrations.

---

## Data flow: test run

```
1. Trigger (API POST / webhook / schedule / anomaly)
       │
       ▼
2. API validates request, creates TestRun record (status: queued)
       │
       ▼
3. Orchestrator picks up job from Redis queue
       │
       ▼
4. Runner agent instantiates Playwright browser
       │
       ▼
5. Each playbook step executed:
   a. Action performed (navigate, click, fill, assert)
   b. Step result recorded (status, duration, screenshot)
   c. Performance metrics captured (Web Vitals via browser API)
       │
       ▼
6. Results stored in database (test_run_results, endpoint_metrics)
       │
       ▼
7. Analyst agent computes updated quality score
       │
       ▼
8. GitHub check / deployment status posted (if GitHub integration active)
       │
       ▼
9. Alert engine evaluates rules against new quality score
       │
       ▼
10. Notifications sent to configured channels (if rules match)
        │
        ▼
11. Dashboard WebSocket push notifies connected clients
```

---

## Technology stack summary

| Layer | Technology | Version |
|-------|-----------|---------|
| Web framework | FastAPI | 0.115+ |
| ASGI server | Uvicorn | 0.30+ |
| Data validation | Pydantic | 2.0+ |
| MCP framework | FastMCP | 2.0+ |
| Database ORM | SQLAlchemy (async) | 2.0+ |
| Database | PostgreSQL + TimescaleDB | 15 + 2.x |
| Development DB | SQLite via aiosqlite | 3.x |
| Async PostgreSQL driver | asyncpg | 0.29+ |
| Cache / Queue | Redis | 7+ |
| Browser automation | Playwright | 1.46+ |
| HTTP client | httpx | 0.27+ |
| Auth (JWT) | PyJWT + cryptography | 2.8+ / 42+ |
| Config format | YAML (pyyaml) | 6.0+ |
| Schema migrations | Alembic | 1.13+ |
| Python version | CPython | 3.11 / 3.12 |
