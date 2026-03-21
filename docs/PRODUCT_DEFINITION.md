# TINAA Managed Service Platform — Product Definition

## Testing Intelligence Network Automation Assistant

> Register your products. TINAA autonomously tests, monitors, and improves the quality of your applications — continuously.

---

## What TINAA Is

TINAA MSP is an **agent-based continuous quality platform** that fuses two traditionally separate disciplines — **Testing** and **Application Performance Monitoring (APM)** — into a single managed service.

You register your products and their deployed environments. TINAA explores your codebase, designs tests, monitors your endpoints, collects performance metrics, and continuously evolves its quality coverage as your application changes. It reports results through GitHub, Claude Code, dashboards, and alerts.

**TINAA is not a test runner.** It is a quality management agent that owns the ongoing health of your products.

---

## How TINAA Differs from Existing Solutions

| Capability | Datadog / New Relic | Cypress Cloud / Playwright | GitHub Actions | TINAA MSP |
|---|---|---|---|---|
| APM metrics collection | Yes | No | No | **Yes** |
| Functional test execution | No | Yes | Runs your scripts | **Yes — auto-generated** |
| Codebase understanding | No | No | No | **Yes — agent explores repos** |
| Auto test generation | No | No | No | **Yes** |
| Deployment-aware | Partial | No | Yes | **Yes — gates deployments** |
| Quality scoring | Partial (SLOs) | No | No | **Yes — composite score** |
| Continuous evolution | Manual dashboards | Manual test maintenance | Manual workflow files | **Autonomous** |

---

## Core Concepts

### Product

A **Product** is TINAA's first-class entity. It represents a deployable application whose quality TINAA manages. Everything — tests, metrics, reports, alerts — is organized around Products.

```
Product: "Acme Web App"
├── Repository: github.com/acme/webapp
├── Environments:
│   ├── Production:  https://app.acme.com
│   ├── Staging:     https://staging.acme.com
│   └── Preview:     (auto-discovered from PR deployments)
├── Endpoints:
│   ├── /            (homepage)
│   ├── /login       (auth flow)
│   ├── /dashboard   (authenticated, data-heavy)
│   ├── /api/v1/*    (REST API)
│   └── /health      (health check)
├── Playbooks:       (auto-generated + custom)
├── Quality Score:    87/100
└── Alert Rules:     (quality gate thresholds)
```

### Environment

Each Product has **Environments** — deployed instances at specific URLs. TINAA discovers these through:

- **Manual registration**: You tell TINAA your production and staging URLs
- **GitHub Deployments API**: TINAA watches `deployment_status` webhooks to auto-discover preview URLs from Vercel, Netlify, Render, etc.
- **GitHub Environments API**: TINAA reads environment configurations for secret-free metadata

### Endpoint

An **Endpoint** is a specific URL path within an Environment that TINAA monitors and tests. Each endpoint has:

- Health status (up/down/degraded)
- Performance baselines (response time p50/p95/p99)
- Test coverage (which playbooks exercise this endpoint)
- Metric history (time-series performance data)

### Playbook

A **Playbook** is a declarative test plan. TINAA auto-generates playbooks by exploring your codebase, but you can also author them manually or refine TINAA's suggestions.

```yaml
playbook:
  name: "Login Flow - Happy Path"
  product: acme-webapp
  priority: critical
  triggers:
    - on_deploy: [staging, production]
    - schedule: "every 15 minutes"
    - on_change: ["src/auth/**", "src/pages/login/**"]

  steps:
    - navigate: "${environment.base_url}/login"
    - assert_visible: "[data-testid='login-form']"
    - fill:
        "[name='email']": "${credentials.test_user.email}"
        "[name='password']": "${credentials.test_user.password}"
    - click: "[type='submit']"
    - wait_for_navigation: { timeout: 5000 }
    - assert_url_contains: "/dashboard"
    - assert_visible: "[data-testid='user-menu']"

  performance_gates:
    total_duration: "< 4s"
    lcp: "< 2.5s"
    cls: "< 0.1"

  assertions:
    - no_console_errors: true
    - no_network_failures: true
    - accessibility_violations: 0
```

### Quality Score

TINAA's signature metric. A composite **0–100 score** per product that fuses testing and APM data:

| Component | Weight | What It Measures |
|---|---|---|
| **Test Health** | 40% | Pass rate, coverage breadth, test freshness, regression detection |
| **Performance Health** | 30% | Response times vs baselines, Web Vitals, availability, error rates |
| **Security Posture** | 15% | Security headers, TLS health, auth flow integrity |
| **Accessibility** | 15% | WCAG conformance, issue severity trending |

Quality Score drives decisions:
- **Deployment gates**: "Don't promote to production if score < 80"
- **Trend alerts**: "Score dropped 15 points after last deploy — here's why"
- **Prioritization**: "Focus on these 3 issues to recover 12 points"

---

## The Seven Pillars

### 1. Product Registry & Environment Awareness

TINAA maintains a registry of all products and their deployed environments. The registry is the foundation — every test run, metric collection, and report is anchored to a product and environment.

**GitHub Integration** (GitHub App):
- Reads repository structure, code, and configuration
- Watches `deployment_status` webhooks for new deployments and preview URLs
- Creates Check Runs on PRs with test results and performance impact
- Implements Deployment Protection Rules to gate production deploys
- Comments on PRs with test suggestions for changed code
- Creates Issues for discovered regressions

**Environment Discovery**:
- Manual: Register base URLs for production, staging
- Automatic: Preview URLs from Vercel (`<project>-git-<branch>.vercel.app`), Netlify (`deploy-preview-<PR#>--<site>.netlify.app`), or any platform that creates GitHub deployments
- Dynamic: TINAA reads `deployment_status.target_url` from webhook payloads

### 2. Autonomous Codebase Intelligence

When a product is registered, TINAA's **Explorer Agent** clones the repo and builds an application model:

**Discovery**:
- Routes and pages (React Router, Next.js pages, Flask routes, Express endpoints)
- API endpoints and contracts (OpenAPI specs, GraphQL schemas, REST patterns)
- Forms, auth flows, CRUD operations
- Component hierarchy and data flow
- Database schema (if accessible)
- Existing test coverage and gaps

**Continuous Updates**:
- PR opened → analyze diff → identify affected user journeys → suggest new tests
- New route detected → generate exploratory test coverage
- API contract changed → update API test playbooks
- Dependency updated → flag for regression testing

### 3. APM — Application Performance Monitoring

TINAA collects performance data through two mechanisms:

**Synthetic Monitoring** (proactive):
- Scheduled Playwright runs against production endpoints
- Page load timing: TTFB, FCP, LCP, TTI, CLS, FID/INP
- API response times, status codes, error rates
- Availability/uptime tracking
- SSL certificate expiry monitoring
- DNS resolution timing

**Test-Embedded Metrics** (during test execution):
- Every test run captures a full performance profile
- Network waterfall: all requests, timing, sizes, failures
- Console output: errors, warnings, logs
- JavaScript exceptions with stack traces
- Resource loading: broken images, failed scripts, missing fonts
- Memory and CPU patterns (where available)

**Baseline Management**:
- TINAA establishes performance baselines per endpoint per environment
- "Login API responds in 180ms p50, 340ms p95 under normal conditions"
- Regressions detected automatically: "After deploy #47, login p95 increased from 340ms to 890ms"
- Baselines auto-adjust when intentional changes are confirmed

**The Fusion** — where Testing meets APM:
- A test **fails** if response time exceeds baseline by configurable threshold
- APM anomalies **trigger** targeted test runs ("endpoint X is slow, run tests that exercise it")
- Test results include performance annotations ("passed in 1.2s — 15% slower than baseline")
- Correlation engine: "Deploy #47 caused 40% LCP regression on /dashboard AND 2 accessibility test failures"

### 4. Continuous Quality Loop

The lifecycle that makes TINAA a **managed service**, not a tool:

```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│  ONBOARD │────▶│ OBSERVE  │────▶│  REACT   │────▶│  EVOLVE  │────▶│  REPORT  │
│          │     │          │     │          │     │          │     │          │
│ Register │     │ Monitor  │     │ Deploy   │     │ Code     │     │ Quality  │
│ product  │     │ endpoints│     │ detected │     │ changed  │     │ score &  │
│ Connect  │     │ Collect  │     │ Run tests│     │ Update   │     │ trends   │
│ GitHub   │     │ metrics  │     │ Compare  │     │ tests    │     │ Alerts   │
│ Scan     │     │ Detect   │     │ baselines│     │ Adapt    │     │ Insights │
│ codebase │     │ anomalies│     │ Gate     │     │ baselines│     │          │
│ Generate │     │ Track    │     │ deploys  │     │ Prioritize│    │          │
│ baseline │     │ baselines│     │          │     │          │     │          │
└──────────┘     └──────────┘     └──────────┘     └──────────┘     └──────────┘
      │                                                                    │
      └────────────────────── continuous cycle ────────────────────────────┘
```

1. **ONBOARD**: Register product, connect GitHub, discover environments, initial codebase scan, generate baseline playbooks, establish performance baselines
2. **OBSERVE**: Continuous synthetic monitoring, collect APM metrics, detect anomalies, track baselines, watch for deployment events
3. **REACT**: Deployment detected → run relevant test suites → compare performance against baselines → report via GitHub Checks → gate deployments if configured
4. **EVOLVE**: Codebase changed → analyze diffs → update/create tests → re-prioritize suites → adapt baselines → flag coverage gaps
5. **REPORT**: Quality score updates, trend analysis, coverage dashboards, performance reports, actionable recommendations, alerts

### 5. Agent Architecture

TINAA is powered by a team of specialized AI agents built on the Claude Agent SDK:

```
┌─────────────────────────────────────────────────────────────┐
│                    TINAA ORCHESTRATOR                        │
│         (Lead Agent — routes work, coordinates)              │
├─────────┬──────────┬──────────┬─────────┬─────────┬────────┤
│Explorer │  Test    │  Test    │  APM    │ Analyst │Reporter│
│ Agent   │ Designer │ Runner   │ Agent   │ Agent   │ Agent  │
│         │  Agent   │  Agent   │         │         │        │
│ Explores│ Generates│ Executes │ Collects│Correlates│Delivers│
│ repos,  │ playbooks│ playbooks│ metrics,│ data,   │ results│
│ maps    │ from     │ against  │ monitors│ finds   │ via    │
│ app     │ codebase │ target   │ health, │ patterns│ GitHub,│
│ model   │ analysis │ envs via │ profiles│ scores  │ Slack, │
│         │          │Playwright│ perf    │ quality │ alerts │
└─────────┴──────────┴──────────┴─────────┴─────────┴────────┘
```

**Explorer Agent**
- Tools: GitHub API, file reading, code parsing
- Input: Repository URL + access token
- Output: Application model — routes, components, APIs, forms, auth flows, data models
- Triggers: Product registration, PR merged, branch updated

**Test Designer Agent**
- Tools: Application model, existing playbooks, code diffs
- Input: Application model + change context
- Output: Declarative playbook YAML files
- Triggers: Explorer discovers new journeys, code changes detected, coverage gaps identified

**Test Runner Agent**
- Tools: Playwright MCP (navigate, click, fill, screenshot, evaluate, network capture)
- Input: Playbook + target environment URL
- Output: Test results with evidence (screenshots, traces, network data, console logs)
- Triggers: Deployment events, schedules, manual requests, anomaly-triggered

**APM Agent**
- Tools: HTTP clients, Playwright (for synthetic monitoring), metrics storage
- Input: Endpoint registry, monitoring schedules
- Output: Time-series metrics, baselines, anomaly alerts
- Triggers: Continuous (scheduled intervals), deployment events

**Analyst Agent**
- Tools: Query access to all results and metrics databases
- Input: Test results + APM data + historical trends
- Output: Quality scores, regression analysis, trend reports, root cause hypotheses, recommendations
- Triggers: After test runs, after metric collection, on quality score changes

**Reporter Agent**
- Tools: GitHub Checks API, GitHub Issues API, Slack/email integrations
- Input: Analysis results + delivery targets
- Output: Check runs on PRs, deployment gate decisions, alert notifications, dashboard data
- Triggers: Analyst produces results, alert thresholds breached

### 6. Multi-Surface Access

TINAA works wherever you work:

**Claude Code (CLI — Primary Developer Interface)**
```bash
# Register TINAA as MCP server
claude mcp add --transport http tinaa https://tinaa.yourcompany.com/mcp

# Then in Claude Code:
> "Register my-app for testing. The repo is github.com/acme/webapp,
>  production is at app.acme.com, staging is staging.acme.com"

> "What's the quality status of my-app?"

> "Run the login flow tests against staging"

> "Why did the quality score drop after the last deploy?"
```

MCP tools exposed to Claude Code:
- `register_product` — onboard a new product
- `list_products` — show all managed products
- `get_quality_score` — current quality score + breakdown
- `run_playbook` — execute a specific test playbook
- `run_suite` — execute all tests for a product/environment
- `get_metrics` — query APM data for an endpoint
- `get_test_results` — query historical test results
- `suggest_tests` — get test suggestions for a code change
- `create_playbook` — author a new playbook
- `get_quality_report` — full quality report for a product

**GitHub (GitHub App — CI/CD Interface)**
- PR Check Runs: Test results + performance delta for changed code
- Deployment Protection Rules: TINAA gates production deploys based on quality score
- PR Comments: "This PR changes the login flow. TINAA suggests adding a test for the new 2FA step."
- Issue Creation: "Regression detected: /dashboard LCP increased 45% after commit abc123"

**HTTP API (Programmatic / Dashboard Interface)**
- REST API for all TINAA operations
- WebSocket streaming for real-time test execution
- Dashboard UI: product overview, quality trends, test results, APM metrics
- Webhook outbound: Slack, PagerDuty, email, custom

**Claude API (Headless / Enterprise / CI)**
```python
# Via Anthropic Messages API with MCP Connector
response = client.beta.messages.create(
    model="claude-opus-4-6",
    messages=[{"role": "user", "content": "Run regression tests for acme-webapp on staging"}],
    mcp_servers=[{
        "type": "url",
        "url": "https://tinaa.yourcompany.com/mcp",
        "name": "tinaa",
        "authorization_token": "Bearer <token>"
    }],
    tools=[{"type": "mcp_toolset", "mcp_server_name": "tinaa"}],
    betas=["mcp-client-2025-11-20"]
)
```

**Enterprise Managed Deployment**
- `managed-mcp.json` for IT-controlled TINAA server configuration
- OAuth 2.1 / SAML SSO for authentication
- Organization-level tenant isolation
- Audit logging for SOC2 compliance
- Role-based access control (admin, developer, viewer)

### 7. Data Architecture

**Core Entities**:

```
Organization
├── Users (with roles)
├── Products
│   ├── Environments
│   │   ├── Endpoints
│   │   │   ├── HealthChecks (scheduled)
│   │   │   ├── MetricSeries (time-series)
│   │   │   └── MetricBaselines (established norms)
│   │   └── Deployments
│   │       ├── commit_sha
│   │       ├── preview_url
│   │       ├── triggered_test_runs
│   │       └── quality_score_delta
│   ├── ApplicationModel (from Explorer Agent)
│   │   ├── Routes
│   │   ├── Components
│   │   ├── APIEndpoints
│   │   └── UserJourneys
│   ├── Playbooks
│   │   ├── Steps
│   │   ├── Assertions
│   │   ├── PerformanceGates
│   │   └── Triggers
│   ├── TestRuns
│   │   ├── TestResults
│   │   │   ├── status (pass/fail/skip)
│   │   │   ├── duration
│   │   │   ├── screenshots
│   │   │   ├── traces
│   │   │   ├── network_data
│   │   │   └── performance_profile
│   │   └── QualityScoreSnapshot
│   ├── QualityScore (current)
│   └── AlertRules
└── Integrations
    ├── GitHub App installation
    ├── Slack workspace
    └── Custom webhooks
```

**Storage Strategy**:

| Store | Purpose | Technology |
|---|---|---|
| Relational | Products, environments, playbooks, configs, users | PostgreSQL |
| Time-Series | APM metrics, response times, Web Vitals, availability | TimescaleDB (PostgreSQL extension) |
| Object Store | Screenshots, traces, test artifacts, reports | S3 / MinIO |
| Cache | Real-time state, session data, hot metrics | Redis |
| Queue | Event processing, agent task distribution | Redis Streams or NATS |

---

## Metric Categories

### Testing Metrics (Collected During Test Runs)

| Metric | Description | Collection Method |
|---|---|---|
| Pass Rate | % of tests passing | Playbook execution results |
| Coverage Breadth | % of discovered user journeys with tests | Explorer vs Playbook mapping |
| Test Freshness | Days since playbook last updated vs code last changed | Git history comparison |
| Regression Rate | New failures per deployment | Cross-deployment result comparison |
| Flake Rate | Tests that pass/fail inconsistently | Statistical analysis of repeated runs |
| Mean Time to Detect | Time between regression introduction and detection | Deployment timestamp vs alert timestamp |

### APM Metrics (Collected Continuously)

| Metric | Description | Collection Method |
|---|---|---|
| TTFB | Time to First Byte | Playwright `performance.timing` |
| FCP | First Contentful Paint | Web Vitals API during synthetic runs |
| LCP | Largest Contentful Paint | Web Vitals API during synthetic runs |
| CLS | Cumulative Layout Shift | Web Vitals API during synthetic runs |
| INP | Interaction to Next Paint | Web Vitals API during synthetic runs |
| Response Time p50/p95/p99 | API endpoint latency distribution | HTTP probe results |
| Error Rate | % of requests returning 4xx/5xx | HTTP probe + test run network capture |
| Availability | % uptime over time window | Scheduled health checks |
| DNS Resolution Time | DNS lookup latency | Network timing API |
| TLS Handshake Time | TLS negotiation latency | Network timing API |

### Security Metrics (Collected During Security Scans)

| Metric | Description | Collection Method |
|---|---|---|
| Security Header Score | Compliance with recommended headers | Response header analysis |
| TLS Grade | Certificate validity, protocol version, cipher strength | TLS probe |
| CSP Coverage | Content Security Policy strictness | CSP header parsing |
| Mixed Content | HTTP resources on HTTPS pages | Network capture during page load |
| Cookie Flags | Secure, HttpOnly, SameSite on auth cookies | Cookie inspection |

### Accessibility Metrics (Collected During Accessibility Scans)

| Metric | Description | Collection Method |
|---|---|---|
| WCAG Violations | Count by severity (critical, serious, moderate, minor) | axe-core or Playwright accessibility API |
| Conformance Level | A, AA, or AAA compliance | Rule-based evaluation |
| Keyboard Navigability | All interactive elements reachable by keyboard | Automated keyboard traversal |
| Color Contrast Ratio | Text contrast against background | Computed style analysis |
| Alt Text Coverage | % of images with meaningful alt text | DOM inspection |

---

## User Journeys

### Journey 1: Onboarding a Product

```
Developer (via Claude Code):
  "Register acme-webapp for testing.
   Repo: github.com/acme/webapp
   Production: https://app.acme.com
   Staging: https://staging.acme.com"

TINAA:
  1. Creates Product entry in registry
  2. Installs/verifies GitHub App on the repo
  3. Explorer Agent clones and scans the codebase
  4. Discovers 14 routes, 6 API endpoints, 3 forms, 1 auth flow
  5. Test Designer generates 8 playbooks covering critical paths
  6. APM Agent runs initial synthetic monitoring baseline
  7. Reports: "Onboarded acme-webapp. Quality Score: 74/100.
     Generated 8 playbooks. 3 endpoints missing security headers.
     Login LCP is 3.2s (above 2.5s threshold).
     Ready for continuous monitoring."
```

### Journey 2: PR with Preview Deployment

```
GitHub webhook: deployment_status (success) for PR #42
  Preview URL: https://acme-webapp-pr-42.vercel.app

TINAA:
  1. Receives deployment webhook with preview URL
  2. Analyzes PR diff: changes to src/pages/checkout.tsx
  3. Identifies affected playbooks: "Checkout Flow", "Cart Management"
  4. Runs affected playbooks against preview URL
  5. Collects performance metrics for changed pages
  6. Compares against staging baselines
  7. Creates GitHub Check Run:
     ✅ Checkout Flow — passed (2.1s, baseline 2.3s)
     ✅ Cart Management — passed
     ⚠️ Performance: Checkout page LCP improved 12% (nice!)
     ❌ Accessibility: New button missing aria-label
  8. Comments on PR: "Found 1 accessibility issue in your changes.
     Line 47 of checkout.tsx: <button> missing aria-label."
```

### Journey 3: Production Anomaly Detection

```
APM Agent (continuous monitoring):
  Detects: /api/v1/orders response time p95 jumped from 200ms to 1400ms

TINAA:
  1. Alert triggered: performance anomaly on /api/v1/orders
  2. Runs targeted test suite exercising the orders API
  3. Tests pass functionally but performance gates fail
  4. Analyst Agent correlates: "Anomaly started 12 minutes after deploy #89
     (commit abc123). The deploy changed src/services/orders.py."
  5. Creates GitHub Issue: "Performance regression: /api/v1/orders p95
     latency increased 7x after deploy #89. Suspect commit abc123."
  6. Sends Slack alert to #acme-webapp-alerts
  7. Quality Score drops from 87 to 71
```

### Journey 4: Enterprise CI Pipeline

```yaml
# .github/workflows/quality-gate.yml
name: TINAA Quality Gate
on: [deployment_status]

jobs:
  quality-check:
    if: github.event.deployment_status.state == 'success'
    runs-on: ubuntu-latest
    steps:
      - name: Run TINAA Quality Gate
        uses: tinaa-msp/quality-gate-action@v1
        with:
          tinaa-url: ${{ secrets.TINAA_URL }}
          tinaa-token: ${{ secrets.TINAA_TOKEN }}
          product: acme-webapp
          environment: staging
          target-url: ${{ github.event.deployment_status.target_url }}
          min-quality-score: 80
          fail-on-regression: true
```

---

## Implementation Phases

### Phase 1: Foundation — Product Registry & GitHub Integration
- Product/Environment/Endpoint data model + PostgreSQL storage
- GitHub App: installation flow, webhook receiver (push, deployment_status, pull_request)
- MCP server with product management tools (register, list, configure)
- HTTP API with basic CRUD for products and environments
- Health check monitoring (scheduled HTTP probes)

### Phase 2: APM Layer — Metrics & Monitoring
- Synthetic monitoring engine (scheduled Playwright runs collecting Web Vitals)
- TimescaleDB for time-series metric storage
- Endpoint profiling (response time, headers, status codes)
- Baseline establishment and anomaly detection
- Performance-annotated test results
- Alert system (threshold-based, trend-based)

### Phase 3: Codebase Intelligence — Explorer & Test Designer
- Explorer Agent: codebase scanning, route discovery, API extraction
- Application model data structure
- Test Designer Agent: playbook generation from application model
- Code change analysis (diff → affected journeys → relevant tests)
- PR integration: test suggestions, check runs

### Phase 4: Quality Engine — Score, Gates, & Loop
- Quality Score computation engine
- Deployment Protection Rules (GitHub integration)
- Continuous quality loop automation
- Analyst Agent: correlation, trends, root cause analysis
- Reporter Agent: multi-channel delivery (GitHub, Slack, email)

### Phase 5: Enterprise — Scale & Compliance
- Multi-tenant organization model
- OAuth 2.1 / SAML SSO
- Role-based access control
- Audit logging
- Enterprise managed MCP deployment (`managed-mcp.json`)
- SOC2 compliance features

---

## Technical Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        ACCESS LAYER                                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────────┐   │
│  │Claude    │  │GitHub    │  │HTTP API  │  │Claude API        │   │
│  │Code MCP  │  │App       │  │+ Dashboard│  │(MCP Connector)  │   │
│  │(stdio/   │  │(Webhooks │  │(REST +   │  │(Headless/CI/    │   │
│  │ HTTP)    │  │ + API)   │  │ WebSocket)│  │ Enterprise)     │   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  └────────┬────────┘   │
│       │              │             │                  │             │
├───────┴──────────────┴─────────────┴──────────────────┴─────────────┤
│                     ORCHESTRATION LAYER                              │
│  ┌──────────────────────────────────────────────────────────────┐   │
│  │              TINAA Orchestrator (Lead Agent)                  │   │
│  │  Routes events → Coordinates agents → Manages lifecycle      │   │
│  └──────────────────────────────────────────────────────────────┘   │
│  ┌─────────┐ ┌──────────┐ ┌─────────┐ ┌─────┐ ┌───────┐ ┌──────┐│
│  │Explorer │ │Test      │ │Test     │ │APM  │ │Analyst│ │Report││
│  │Agent    │ │Designer  │ │Runner   │ │Agent│ │Agent  │ │Agent ││
│  └─────────┘ └──────────┘ └─────────┘ └─────┘ └───────┘ └──────┘│
├──────────────────────────────────────────────────────────────────────┤
│                       CORE SERVICES                                  │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────────────┐   │
│  │Product        │  │Quality        │  │Alert                  │   │
│  │Registry       │  │Score Engine   │  │Engine                 │   │
│  └───────────────┘  └───────────────┘  └───────────────────────┘   │
│  ┌───────────────┐  ┌───────────────┐  ┌───────────────────────┐   │
│  │Playbook       │  │Baseline       │  │Event                  │   │
│  │Engine         │  │Manager        │  │Processor              │   │
│  └───────────────┘  └───────────────┘  └───────────────────────┘   │
├──────────────────────────────────────────────────────────────────────┤
│                      EXECUTION LAYER                                 │
│  ┌───────────────────────────────────────────────────────────────┐  │
│  │  Playwright Browser Pool (headless Chromium instances)        │  │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐        │  │
│  │  │Session 1│  │Session 2│  │Session 3│  │Session N│        │  │
│  │  │(test)   │  │(monitor)│  │(test)   │  │(monitor)│        │  │
│  │  └─────────┘  └─────────┘  └─────────┘  └─────────┘        │  │
│  └───────────────────────────────────────────────────────────────┘  │
├──────────────────────────────────────────────────────────────────────┤
│                       DATA LAYER                                     │
│  ┌──────────┐  ┌─────────────┐  ┌──────────┐  ┌───────────────┐   │
│  │PostgreSQL│  │TimescaleDB  │  │S3 / MinIO│  │Redis          │   │
│  │(entities)│  │(metrics)    │  │(artifacts)│  │(cache + queue)│   │
│  └──────────┘  └─────────────┘  └──────────┘  └───────────────┘   │
└──────────────────────────────────────────────────────────────────────┘
```

---

## Configuration: `.tinaa.yml`

Products can be configured via a `.tinaa.yml` file in the repository root:

```yaml
product:
  name: acme-webapp
  team: platform-engineering

environments:
  production:
    url: https://app.acme.com
    monitoring:
      interval: 5m
      endpoints:
        - path: /
          performance_budget: { lcp: 2.5s, cls: 0.1 }
        - path: /api/health
          expected_status: 200
          max_response_time: 500ms
  staging:
    url: https://staging.acme.com
    monitoring:
      interval: 15m

quality_gates:
  deploy_to_production:
    min_score: 80
    no_critical_failures: true
    max_performance_regression: 20%

testing:
  schedule: "*/30 * * * *"  # every 30 minutes
  on_deploy: true
  on_pr: true
  browsers: [chromium]
  viewports:
    - { name: desktop, width: 1440, height: 900 }
    - { name: mobile, width: 375, height: 812 }

alerts:
  slack: "#acme-alerts"
  pagerduty:
    service_key: "${PAGERDUTY_KEY}"
    severity_threshold: critical
```

---

## What "Managed" Means

| Traditional Testing | TINAA MSP |
|---|---|
| You write tests | TINAA proposes tests from codebase analysis |
| You maintain tests when code changes | TINAA detects changes and updates tests |
| You set up monitoring dashboards | TINAA instruments monitoring automatically |
| You interpret test results | TINAA correlates results with APM data and explains |
| You decide what to test | TINAA prioritizes by risk, change frequency, and impact |
| Tests run when triggered | Tests run continuously + on every deployment |
| Pass/fail binary | Quality Score with weighted dimensions |
| Separate tools for testing and APM | Unified platform — test failures and perf regressions in one view |
| Manual regression detection | Automated cross-deployment comparison |

**You manage your products. TINAA manages their quality.**
