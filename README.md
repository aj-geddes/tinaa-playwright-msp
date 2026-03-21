# TINAA MSP

**Testing Intelligence Network Automation Assistant — Managed Service Platform**

[![CI](https://github.com/aj-geddes/tinaa-playwright-msp/actions/workflows/ci.yml/badge.svg)](https://github.com/aj-geddes/tinaa-playwright-msp/actions/workflows/ci.yml)
[![License](https://img.shields.io/github/license/aj-geddes/tinaa-playwright-msp?style=flat-square)](https://github.com/aj-geddes/tinaa-playwright-msp/blob/main/LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue?style=flat-square&logo=python&logoColor=white)](https://www.python.org)

An agent-based continuous quality platform that fuses **automated testing** with **application performance monitoring** into a single managed service. Register your products, and TINAA autonomously tests, monitors, and improves the quality of your applications — continuously.

## What TINAA Does

- **Product Registry** — Register your applications with their deployed environments (production, staging, preview) and endpoints
- **Codebase Intelligence** — AI agents explore your repos to discover routes, APIs, forms, and user journeys
- **Auto-Generated Tests** — Declarative playbooks are generated from codebase analysis and executed via Playwright
- **APM Monitoring** — Continuous synthetic monitoring captures Web Vitals, response times, availability, and error rates
- **Quality Score** — A composite 0–100 score combining test health (40%), performance (30%), security (15%), and accessibility (15%)
- **Deployment Gates** — Block production deploys when quality score drops below threshold via GitHub Deployment Protection Rules
- **Alerts** — Notify teams through Slack, Microsoft Teams, PagerDuty, email, or webhooks when quality degrades
- **GitHub Integration** — Check Runs on PRs, deployment awareness via webhooks, repo import via PAT or GitHub App

## Architecture

```
Access Layer:     Claude Code (MCP)  |  GitHub App  |  REST API + Dashboard  |  Claude API
                         │                  │                   │                    │
Orchestration:           └──────────────────┴───────────────────┴────────────────────┘
                                        TINAA Orchestrator
                    ┌──────────┬──────────┬──────────┬─────────┬────────┐
Agents:           Explorer  Designer   Runner    APM    Analyst  Reporter

Core Services:    Registry  |  Quality Scorer  |  Playbook Engine  |  Alert Engine

Execution:        Playwright Browser Pool (headless Chromium)

Data:             PostgreSQL (TimescaleDB)  |  Redis  |  S3/MinIO
```

### Modules

| Module | Purpose |
|---|---|
| `tinaa/models/` | 13 SQLAlchemy ORM tables with Pydantic v2 schemas |
| `tinaa/registry/` | Product, environment, and endpoint CRUD |
| `tinaa/github/` | GitHub App + PAT client, webhooks, Checks API, deployment tracking |
| `tinaa/mcp_server/` | 14 MCP tools + 4 resources for Claude Code |
| `tinaa/apm/` | Synthetic monitoring, Web Vitals, baselines, anomaly detection |
| `tinaa/agents/` | Orchestrator + 6 specialized agents |
| `tinaa/quality/` | Composite quality scorer, deployment gates, trend analysis |
| `tinaa/playbooks/` | YAML/JSON playbook parser, validator, Playwright executor |
| `tinaa/api/` | FastAPI REST + WebSocket, 9 route modules |
| `tinaa/alerts/` | Alert engine with Slack, Teams, PagerDuty, email, webhook channels |
| `tinaa/config/` | `.tinaa.yml` parser with env var resolution |
| `tinaa/frontend/` | Accessible dark-mode dashboard (Web Components, Tailwind CSS) |

## Quick Start

### Docker Compose

```bash
git clone https://github.com/aj-geddes/tinaa-playwright-msp.git
cd tinaa-playwright-msp
cp .env.example .env
docker compose up -d
```

TINAA will be available at `http://localhost:8765` with PostgreSQL (TimescaleDB) and Redis.

### Development

```bash
# Install dependencies
pip install -e ".[dev]"
playwright install chromium --with-deps

# Run database migrations
python -m alembic upgrade head

# Start the API server with hot reload
uvicorn tinaa.api.app:create_app --factory --reload --port 8765

# Run tests
pytest tests/unit/ -q
```

### Claude Code (MCP)

```bash
claude mcp add --transport http tinaa http://localhost:8765/mcp
```

Then in Claude Code:
```
> Register my-app for testing. Repo is github.com/acme/webapp,
  production is at app.acme.com, staging is staging.acme.com

> What's the quality score for my-app?

> Run the login flow tests against staging
```

### Kubernetes

```bash
kubectl apply -f k8s/
```

Deploys TINAA with PostgreSQL, Redis, and NGINX ingress.

## Configuration

Products can be configured via `.tinaa.yml` in the repository root:

```yaml
product:
  name: my-app
  team: platform

environments:
  production:
    url: https://app.example.com
    monitoring:
      interval: 5m
      endpoints:
        - path: /
          lcp: 2500
        - path: /api/health
          expected_status: 200
          max_response_time: 500ms
  staging:
    url: https://staging.example.com

quality_gates:
  deploy_to_production:
    min_score: 80
    no_critical_failures: true

alerts:
  channels:
    - type: slack
      channel: "#alerts"
```

## Quality Score

| Component | Weight | What It Measures |
|---|---|---|
| Test Health | 40% | Pass rate, coverage breadth, test freshness, regression detection |
| Performance | 30% | Web Vitals (LCP, FCP, CLS, INP), response times, availability |
| Security | 15% | HTTPS, security headers, TLS grade, cookie/form security |
| Accessibility | 15% | WCAG 2.1 AA violations, alt text, labels, keyboard navigation |

Grades: **A+** >= 95, **A** >= 85, **B** >= 70, **C** >= 55, **D** >= 40, **F** < 40

## Documentation

Built-in documentation is available at `/docs` in the dashboard, covering:

- **[User Guide](tinaa/frontend/static/docs/user/)** — Getting started, products, playbooks, quality scores, metrics, alerts
- **[Admin Guide](tinaa/frontend/static/docs/admin/)** — Installation, configuration, GitHub integration, authentication
- **[Operations Guide](tinaa/frontend/static/docs/operations/)** — Architecture, deployment, monitoring, scaling, security, runbooks

## Tech Stack

- **Python 3.11+** with FastAPI, SQLAlchemy 2.0 (async), Pydantic v2
- **Playwright** for browser automation and synthetic monitoring
- **FastMCP** for Model Context Protocol (Claude Code integration)
- **PostgreSQL** with TimescaleDB for time-series metrics
- **Redis** for caching and queues
- **Tailwind CSS** + Web Components for the frontend

## Contributing

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Lint
ruff check tinaa/
ruff format tinaa/

# Test (1,400+ tests)
pytest tests/unit/ -q

# Full CI check
make lint test
```

## License

[MIT](LICENSE)
