---
layout: page
title: "Architecture"
description: "System architecture, agent design, data flow, and technology stack for TINAA MSP v2.0"
---

# Architecture

TINAA MSP is an agent-based continuous quality platform. It fuses automated Playwright browser testing with application performance monitoring (APM) through a multi-agent architecture, delivering continuous quality intelligence across every deployment.

---

## System Overview

<div style="background:#1e293b; border:1px solid #334155; border-radius:12px; padding:32px 24px; margin:32px 0; overflow-x:auto;">

  <!-- Title -->
  <div style="text-align:center; margin-bottom:28px;">
    <span style="background:#3b82f6; color:#f8fafc; font-weight:700; font-size:1.1rem; padding:8px 24px; border-radius:6px; letter-spacing:0.5px;">TINAA MSP v2.0</span>
  </div>

  <!-- Row 1: External clients + Frontend -->
  <div style="display:flex; gap:16px; align-items:center; justify-content:center; flex-wrap:wrap; margin-bottom:20px;">
    <div style="background:#0f172a; border:1px solid #475569; border-radius:8px; padding:12px 20px; text-align:center; min-width:140px;">
      <div style="color:#94a3b8; font-size:0.75rem; text-transform:uppercase; letter-spacing:1px;">External</div>
      <div style="color:#f8fafc; font-weight:600;">Web Browser</div>
      <div style="color:#64748b; font-size:0.8rem;">(Dashboard)</div>
    </div>
    <div style="color:#3b82f6; font-size:1.2rem;">&#8594;</div>
    <div style="background:#1a2744; border:2px solid #3b82f6; border-radius:8px; padding:12px 20px; text-align:center; flex:1; max-width:420px;">
      <div style="color:#3b82f6; font-weight:700;">SPA Frontend</div>
      <div style="color:#94a3b8; font-size:0.85rem;">Web Components &middot; No Build Step</div>
    </div>
  </div>

  <!-- Arrow down -->
  <div style="text-align:center; color:#3b82f6; font-size:0.85rem; margin:8px 0;">&#9660; REST / WebSocket</div>

  <!-- Row 2: MCP client + FastAPI -->
  <div style="display:flex; gap:16px; align-items:center; justify-content:center; flex-wrap:wrap; margin-bottom:20px;">
    <div style="background:#0f172a; border:1px solid #475569; border-radius:8px; padding:12px 20px; text-align:center; min-width:140px;">
      <div style="color:#94a3b8; font-size:0.75rem; text-transform:uppercase; letter-spacing:1px;">External</div>
      <div style="color:#f8fafc; font-weight:600;">Claude / AI IDE</div>
      <div style="color:#64748b; font-size:0.8rem;">(MCP 2.0)</div>
    </div>
    <div style="color:#3b82f6; font-size:1.2rem;">&#8594;</div>
    <div style="background:#1a2744; border:2px solid #3b82f6; border-radius:8px; padding:12px 20px; text-align:center; flex:1; max-width:420px;">
      <div style="color:#3b82f6; font-weight:700;">FastAPI REST API</div>
      <div style="color:#94a3b8; font-size:0.85rem;">/api/v1/* &middot; /health &middot; /ws/*</div>
    </div>
  </div>

  <!-- Arrow down -->
  <div style="text-align:center; color:#3b82f6; font-size:0.85rem; margin:8px 0;">&#9660;</div>

  <!-- Row 3: GitHub + Orchestrator -->
  <div style="display:flex; gap:16px; align-items:center; justify-content:center; flex-wrap:wrap; margin-bottom:20px;">
    <div style="background:#0f172a; border:1px solid #475569; border-radius:8px; padding:12px 20px; text-align:center; min-width:140px;">
      <div style="color:#94a3b8; font-size:0.75rem; text-transform:uppercase; letter-spacing:1px;">External</div>
      <div style="color:#f8fafc; font-weight:600;">GitHub</div>
      <div style="color:#64748b; font-size:0.8rem;">Webhooks</div>
    </div>
    <div style="color:#f59e0b; font-size:0.85rem;">&#8212; webhook &#8594;</div>
    <div style="background:#1a2744; border:2px solid #f59e0b; border-radius:8px; padding:12px 20px; text-align:center; flex:1; max-width:420px;">
      <div style="color:#f59e0b; font-weight:700;">Orchestrator</div>
      <div style="color:#94a3b8; font-size:0.85rem;">Routes events to sub-agents</div>
    </div>
  </div>

  <!-- Arrow down -->
  <div style="text-align:center; color:#f59e0b; font-size:0.85rem; margin:8px 0;">&#9660; dispatches tasks</div>

  <!-- Row 4: Agent grid -->
  <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(150px, 1fr)); gap:12px; margin-bottom:24px;">
    <div style="background:#0f2a1a; border:1px solid #10b981; border-radius:8px; padding:14px 12px; text-align:center;">
      <div style="color:#10b981; font-weight:700; font-size:0.95rem;">Explorer</div>
      <div style="color:#6ee7b7; font-size:0.8rem;">Codebase intelligence</div>
    </div>
    <div style="background:#0f2a1a; border:1px solid #10b981; border-radius:8px; padding:14px 12px; text-align:center;">
      <div style="color:#10b981; font-weight:700; font-size:0.95rem;">Test Designer</div>
      <div style="color:#6ee7b7; font-size:0.8rem;">Playbook generation</div>
    </div>
    <div style="background:#0f2a1a; border:1px solid #10b981; border-radius:8px; padding:14px 12px; text-align:center;">
      <div style="color:#10b981; font-weight:700; font-size:0.95rem;">Test Runner</div>
      <div style="color:#6ee7b7; font-size:0.8rem;">Playwright execution</div>
    </div>
    <div style="background:#0f2a1a; border:1px solid #10b981; border-radius:8px; padding:14px 12px; text-align:center;">
      <div style="color:#10b981; font-weight:700; font-size:0.95rem;">APM Agent</div>
      <div style="color:#6ee7b7; font-size:0.8rem;">Metrics collection</div>
    </div>
    <div style="background:#0f2a1a; border:1px solid #10b981; border-radius:8px; padding:14px 12px; text-align:center;">
      <div style="color:#10b981; font-weight:700; font-size:0.95rem;">Analyst</div>
      <div style="color:#6ee7b7; font-size:0.8rem;">Correlation &amp; scoring</div>
    </div>
    <div style="background:#0f2a1a; border:1px solid #10b981; border-radius:8px; padding:14px 12px; text-align:center;">
      <div style="color:#10b981; font-weight:700; font-size:0.95rem;">Reporter</div>
      <div style="color:#6ee7b7; font-size:0.8rem;">Slack / Email / Webhook</div>
    </div>
  </div>

  <!-- Row 5: Data stores -->
  <div style="display:flex; gap:16px; justify-content:center; flex-wrap:wrap;">
    <div style="background:#1a1a2e; border:1px solid #6366f1; border-radius:8px; padding:14px 24px; text-align:center; flex:1; max-width:250px;">
      <div style="color:#6366f1; font-weight:700;">PostgreSQL</div>
      <div style="color:#a5b4fc; font-size:0.85rem;">+ TimescaleDB</div>
    </div>
    <div style="background:#2a1a1a; border:1px solid #ef4444; border-radius:8px; padding:14px 24px; text-align:center; flex:1; max-width:250px;">
      <div style="color:#ef4444; font-weight:700;">Redis</div>
      <div style="color:#fca5a5; font-size:0.85rem;">Cache / Queue</div>
    </div>
  </div>

</div>

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

<div style="background:#1e293b; border:1px solid #334155; border-radius:12px; padding:28px 24px; margin:32px 0; overflow-x:auto;">

  <!-- Step 1 -->
  <div style="display:flex; align-items:flex-start; gap:16px; margin-bottom:24px;">
    <div style="background:#3b82f6; color:#f8fafc; font-weight:700; width:36px; height:36px; border-radius:50%; display:flex; align-items:center; justify-content:center; flex-shrink:0;">1</div>
    <div style="flex:1;">
      <div style="color:#f8fafc; font-weight:700; margin-bottom:4px;">Product Registration</div>
      <div style="color:#94a3b8; font-size:0.9rem; line-height:1.6;">
        <code style="background:#0f172a; padding:2px 6px; border-radius:4px; color:#3b82f6;">POST /api/v1/products</code> (REST) or <code style="background:#0f172a; padding:2px 6px; border-radius:4px; color:#3b82f6;">register_product</code> (MCP)<br>
        &#8594; Orchestrator receives <code style="background:#0f172a; padding:2px 6px; border-radius:4px; color:#f59e0b;">product_registered</code> event<br>
        &#8594; Explorer scans repository &rarr; discovers routes, APIs, forms, journeys
      </div>
    </div>
  </div>

  <!-- Step 2 -->
  <div style="display:flex; align-items:flex-start; gap:16px; margin-bottom:24px;">
    <div style="background:#3b82f6; color:#f8fafc; font-weight:700; width:36px; height:36px; border-radius:50%; display:flex; align-items:center; justify-content:center; flex-shrink:0;">2</div>
    <div style="flex:1;">
      <div style="color:#f8fafc; font-weight:700; margin-bottom:4px;">Test Generation</div>
      <div style="color:#94a3b8; font-size:0.9rem; line-height:1.6;">
        Test Designer receives Explorer output<br>
        &#8594; Generates playbook definitions for each discovered journey<br>
        &#8594; PlaybookValidator checks steps<br>
        &#8594; Playbooks saved to database
      </div>
    </div>
  </div>

  <!-- Step 3 -->
  <div style="display:flex; align-items:flex-start; gap:16px; margin-bottom:24px;">
    <div style="background:#3b82f6; color:#f8fafc; font-weight:700; width:36px; height:36px; border-radius:50%; display:flex; align-items:center; justify-content:center; flex-shrink:0;">3</div>
    <div style="flex:1;">
      <div style="color:#f8fafc; font-weight:700; margin-bottom:4px;">Execution Trigger</div>
      <div style="color:#94a3b8; font-size:0.9rem; line-height:1.6;">
        GitHub deployment webhook &rarr; <code style="background:#0f172a; padding:2px 6px; border-radius:4px; color:#f59e0b;">deployment_detected</code><br>
        <em>or</em> Cron schedule &rarr; <code style="background:#0f172a; padding:2px 6px; border-radius:4px; color:#f59e0b;">schedule_triggered</code><br>
        <em>or</em> Manual API call &rarr; <code style="background:#0f172a; padding:2px 6px; border-radius:4px; color:#3b82f6;">POST /api/v1/test-runs</code><br>
        &#8594; Orchestrator dispatches to Test Runner
      </div>
    </div>
  </div>

  <!-- Step 4 -->
  <div style="display:flex; align-items:flex-start; gap:16px; margin-bottom:24px;">
    <div style="background:#3b82f6; color:#f8fafc; font-weight:700; width:36px; height:36px; border-radius:50%; display:flex; align-items:center; justify-content:center; flex-shrink:0;">4</div>
    <div style="flex:1;">
      <div style="color:#f8fafc; font-weight:700; margin-bottom:4px;">Test Execution</div>
      <div style="color:#94a3b8; font-size:0.9rem; line-height:1.6;">
        Test Runner loads playbook steps<br>
        &#8594; Playwright drives Chromium against target environment<br>
        &#8594; Each step: execute &rarr; capture screenshot / logs / metrics<br>
        &#8594; Live progress &rarr; WebSocket &rarr; Dashboard<br>
        &#8594; Results persisted to <code style="background:#0f172a; padding:2px 6px; border-radius:4px; color:#6366f1;">test_runs</code>, <code style="background:#0f172a; padding:2px 6px; border-radius:4px; color:#6366f1;">test_results</code> tables
      </div>
    </div>
  </div>

  <!-- Step 5 -->
  <div style="display:flex; align-items:flex-start; gap:16px; margin-bottom:24px;">
    <div style="background:#3b82f6; color:#f8fafc; font-weight:700; width:36px; height:36px; border-radius:50%; display:flex; align-items:center; justify-content:center; flex-shrink:0;">5</div>
    <div style="flex:1;">
      <div style="color:#f8fafc; font-weight:700; margin-bottom:4px;">APM Collection <span style="color:#64748b; font-weight:400;">(continuous, parallel)</span></div>
      <div style="color:#94a3b8; font-size:0.9rem; line-height:1.6;">
        APM Agent polls registered endpoints<br>
        &#8594; MetricDatapoints saved to TimescaleDB hypertable<br>
        &#8594; BaselineManager recomputes baselines<br>
        &#8594; AnomalyDetector compares to baseline<br>
        &#8594; If anomaly: <code style="background:#0f172a; padding:2px 6px; border-radius:4px; color:#f59e0b;">anomaly_detected</code> &rarr; Orchestrator &rarr; Reporter
      </div>
    </div>
  </div>

  <!-- Step 6 -->
  <div style="display:flex; align-items:flex-start; gap:16px; margin-bottom:24px;">
    <div style="background:#3b82f6; color:#f8fafc; font-weight:700; width:36px; height:36px; border-radius:50%; display:flex; align-items:center; justify-content:center; flex-shrink:0;">6</div>
    <div style="flex:1;">
      <div style="color:#f8fafc; font-weight:700; margin-bottom:4px;">Quality Scoring</div>
      <div style="color:#94a3b8; font-size:0.9rem; line-height:1.6;">
        Analyst receives test results + APM metrics<br>
        &#8594; QualityScorer computes weighted composite score<br>
        &#8594; QualityScoreSnapshot saved to database<br>
        &#8594; <code style="background:#0f172a; padding:2px 6px; border-radius:4px; color:#6366f1;">quality_score</code> updated on Product record
      </div>
    </div>
  </div>

  <!-- Step 7 -->
  <div style="display:flex; align-items:flex-start; gap:16px;">
    <div style="background:#10b981; color:#f8fafc; font-weight:700; width:36px; height:36px; border-radius:50%; display:flex; align-items:center; justify-content:center; flex-shrink:0;">7</div>
    <div style="flex:1;">
      <div style="color:#f8fafc; font-weight:700; margin-bottom:4px;">Reporting</div>
      <div style="color:#94a3b8; font-size:0.9rem; line-height:1.6;">
        Reporter delivers to configured channels<br>
        &#8594; Dashboard: <code style="background:#0f172a; padding:2px 6px; border-radius:4px; color:#10b981;">quality_update</code> pushed via WebSocket<br>
        &#8594; Alerts: alert rules evaluated &rarr; notifications sent<br>
        &#8594; API: <code style="background:#0f172a; padding:2px 6px; border-radius:4px; color:#3b82f6;">GET /api/v1/quality/{id}/report</code> returns full report
      </div>
    </div>
  </div>

</div>

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

<div style="background:#1e293b; border:1px solid #334155; border-radius:12px; padding:24px; margin:32px 0; overflow-x:auto;">

  <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(280px, 1fr)); gap:20px;">

    <!-- Organizations & Identity -->
    <div style="background:#0f172a; border:1px solid #475569; border-radius:8px; padding:16px;">
      <div style="color:#3b82f6; font-weight:700; font-size:0.85rem; text-transform:uppercase; letter-spacing:1px; margin-bottom:12px; padding-bottom:8px; border-bottom:1px solid #334155;">Organizations &amp; Identity</div>
      <div style="color:#f8fafc; font-family:monospace; font-size:0.9rem; line-height:2;">
        <div><span style="color:#10b981;">&#9679;</span> organizations</div>
      </div>
    </div>

    <!-- Products & Configuration -->
    <div style="background:#0f172a; border:1px solid #475569; border-radius:8px; padding:16px;">
      <div style="color:#f59e0b; font-weight:700; font-size:0.85rem; text-transform:uppercase; letter-spacing:1px; margin-bottom:12px; padding-bottom:8px; border-bottom:1px solid #334155;">Products &amp; Configuration</div>
      <div style="color:#f8fafc; font-family:monospace; font-size:0.9rem; line-height:2;">
        <div><span style="color:#10b981;">&#9679;</span> products</div>
        <div><span style="color:#10b981;">&#9679;</span> environments</div>
      </div>
    </div>

    <!-- Testing -->
    <div style="background:#0f172a; border:1px solid #475569; border-radius:8px; padding:16px;">
      <div style="color:#10b981; font-weight:700; font-size:0.85rem; text-transform:uppercase; letter-spacing:1px; margin-bottom:12px; padding-bottom:8px; border-bottom:1px solid #334155;">Testing</div>
      <div style="color:#f8fafc; font-family:monospace; font-size:0.9rem; line-height:2;">
        <div><span style="color:#10b981;">&#9679;</span> playbooks</div>
        <div><span style="color:#10b981;">&#9679;</span> test_runs</div>
        <div><span style="color:#10b981;">&#9679;</span> test_results</div>
        <div><span style="color:#10b981;">&#9679;</span> deployments</div>
      </div>
    </div>

    <!-- Monitoring & Metrics -->
    <div style="background:#0f172a; border:1px solid #475569; border-radius:8px; padding:16px;">
      <div style="color:#6366f1; font-weight:700; font-size:0.85rem; text-transform:uppercase; letter-spacing:1px; margin-bottom:12px; padding-bottom:8px; border-bottom:1px solid #334155;">Monitoring &amp; Metrics</div>
      <div style="color:#f8fafc; font-family:monospace; font-size:0.9rem; line-height:2;">
        <div><span style="color:#10b981;">&#9679;</span> endpoints</div>
        <div><span style="color:#10b981;">&#9679;</span> metric_datapoints <span style="color:#6366f1; font-size:0.75rem;">(hypertable)</span></div>
        <div><span style="color:#10b981;">&#9679;</span> metric_baselines</div>
      </div>
    </div>

    <!-- Quality & Alerting -->
    <div style="background:#0f172a; border:1px solid #475569; border-radius:8px; padding:16px;">
      <div style="color:#ef4444; font-weight:700; font-size:0.85rem; text-transform:uppercase; letter-spacing:1px; margin-bottom:12px; padding-bottom:8px; border-bottom:1px solid #334155;">Quality &amp; Alerting</div>
      <div style="color:#f8fafc; font-family:monospace; font-size:0.9rem; line-height:2;">
        <div><span style="color:#10b981;">&#9679;</span> quality_score_snapshots</div>
        <div><span style="color:#10b981;">&#9679;</span> alert_rules</div>
        <div><span style="color:#10b981;">&#9679;</span> alert_events</div>
      </div>
    </div>

  </div>
</div>

### Key relationships

<div style="background:#1e293b; border:1px solid #334155; border-radius:12px; padding:24px; margin:32px 0; overflow-x:auto;">
  <div style="color:#f8fafc; font-family:monospace; font-size:0.9rem; line-height:1.8;">

    <!-- Level 0 -->
    <div style="padding-left:0;">
      <span style="color:#3b82f6; font-weight:700;">organizations</span>
    </div>

    <!-- Level 1 -->
    <div style="padding-left:28px; border-left:2px solid #334155; margin-left:8px;">
      <div style="margin-left:12px; margin-top:4px;">
        <span style="color:#94a3b8;">&#9492;&#9472;&#9472;</span> <span style="color:#f59e0b; font-weight:700;">products</span> <span style="color:#475569; font-size:0.8rem;">(organization_id FK)</span>
      </div>

      <!-- Level 2: environments -->
      <div style="padding-left:28px; border-left:2px solid #334155; margin-left:44px;">
        <div style="margin-left:12px; margin-top:4px;">
          <span style="color:#94a3b8;">&#9500;&#9472;&#9472;</span> <span style="color:#10b981; font-weight:700;">environments</span> <span style="color:#475569; font-size:0.8rem;">(product_id FK)</span>
        </div>

        <!-- Level 3: under environments -->
        <div style="padding-left:28px; border-left:2px solid #334155; margin-left:44px;">
          <div style="margin-left:12px; margin-top:2px;">
            <span style="color:#94a3b8;">&#9500;&#9472;&#9472;</span> <span style="color:#e2e8f0;">endpoints</span> <span style="color:#475569; font-size:0.8rem;">(environment_id FK)</span>
          </div>
          <div style="padding-left:28px; margin-left:44px;">
            <div style="margin-left:12px; margin-top:2px;">
              <span style="color:#94a3b8;">&#9500;&#9472;&#9472;</span> <span style="color:#6366f1;">metric_datapoints</span> <span style="color:#475569; font-size:0.8rem;">(endpoint_id FK)</span>
            </div>
            <div style="margin-left:12px; margin-top:2px;">
              <span style="color:#94a3b8;">&#9492;&#9472;&#9472;</span> <span style="color:#6366f1;">metric_baselines</span> <span style="color:#475569; font-size:0.8rem;">(endpoint_id FK)</span>
            </div>
          </div>
          <div style="margin-left:12px; margin-top:2px;">
            <span style="color:#94a3b8;">&#9500;&#9472;&#9472;</span> <span style="color:#e2e8f0;">test_runs</span> <span style="color:#475569; font-size:0.8rem;">(environment_id FK)</span>
          </div>
          <div style="padding-left:28px; margin-left:44px;">
            <div style="margin-left:12px; margin-top:2px;">
              <span style="color:#94a3b8;">&#9492;&#9472;&#9472;</span> <span style="color:#e2e8f0;">test_results</span> <span style="color:#475569; font-size:0.8rem;">(test_run_id FK)</span>
            </div>
          </div>
          <div style="margin-left:12px; margin-top:2px;">
            <span style="color:#94a3b8;">&#9492;&#9472;&#9472;</span> <span style="color:#e2e8f0;">deployments</span> <span style="color:#475569; font-size:0.8rem;">(environment_id FK)</span>
          </div>
        </div>

        <!-- Level 2: playbooks -->
        <div style="margin-left:12px; margin-top:4px;">
          <span style="color:#94a3b8;">&#9500;&#9472;&#9472;</span> <span style="color:#10b981; font-weight:700;">playbooks</span> <span style="color:#475569; font-size:0.8rem;">(product_id FK)</span>
        </div>
        <div style="padding-left:28px; margin-left:44px;">
          <div style="margin-left:12px; margin-top:2px;">
            <span style="color:#94a3b8;">&#9492;&#9472;&#9472;</span> <span style="color:#e2e8f0;">test_runs</span> <span style="color:#475569; font-size:0.8rem;">(playbook_id FK, nullable)</span>
          </div>
        </div>

        <!-- Level 2: quality + alerts -->
        <div style="margin-left:12px; margin-top:4px;">
          <span style="color:#94a3b8;">&#9500;&#9472;&#9472;</span> <span style="color:#ef4444; font-weight:700;">quality_score_snapshots</span> <span style="color:#475569; font-size:0.8rem;">(product_id FK)</span>
        </div>
        <div style="margin-left:12px; margin-top:4px;">
          <span style="color:#94a3b8;">&#9492;&#9472;&#9472;</span> <span style="color:#ef4444; font-weight:700;">alert_rules</span> <span style="color:#475569; font-size:0.8rem;">(product_id FK)</span>
        </div>
        <div style="padding-left:28px; margin-left:44px;">
          <div style="margin-left:12px; margin-top:2px;">
            <span style="color:#94a3b8;">&#9492;&#9472;&#9472;</span> <span style="color:#e2e8f0;">alert_events</span> <span style="color:#475569; font-size:0.8rem;">(rule_id FK)</span>
          </div>
        </div>

      </div>
    </div>

  </div>
</div>

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

<div style="background:#1e293b; border:1px solid #334155; border-radius:12px; padding:20px 24px; margin:32px 0; overflow-x:auto;">
  <div style="color:#f8fafc; font-family:monospace; font-size:0.9rem; line-height:2;">
    <div><span style="color:#3b82f6; font-weight:700;">tinaa/frontend/</span></div>
    <div style="padding-left:20px;"><span style="color:#94a3b8;">&#9500;&#9472;&#9472;</span> <span style="color:#f59e0b;">index.html</span> <span style="color:#475569;">&mdash; dashboard shell</span></div>
    <div style="padding-left:20px;"><span style="color:#94a3b8;">&#9500;&#9472;&#9472;</span> <span style="color:#f59e0b;">products.html</span> <span style="color:#475569;">&mdash; products list page</span></div>
    <div style="padding-left:20px;"><span style="color:#94a3b8;">&#9492;&#9472;&#9472;</span> <span style="color:#3b82f6; font-weight:700;">assets/</span></div>
    <div style="padding-left:48px;"><span style="color:#94a3b8;">&#9500;&#9472;&#9472;</span> <span style="color:#f59e0b;">app.js</span> <span style="color:#475569;">&mdash; bootstrap and routing</span></div>
    <div style="padding-left:48px;"><span style="color:#94a3b8;">&#9500;&#9472;&#9472;</span> <span style="color:#3b82f6; font-weight:700;">components/</span></div>
    <div style="padding-left:76px;"><span style="color:#94a3b8;">&#9500;&#9472;&#9472;</span> <span style="color:#e2e8f0;">quality-card.js</span></div>
    <div style="padding-left:76px;"><span style="color:#94a3b8;">&#9500;&#9472;&#9472;</span> <span style="color:#e2e8f0;">metric-chart.js</span></div>
    <div style="padding-left:76px;"><span style="color:#94a3b8;">&#9500;&#9472;&#9472;</span> <span style="color:#e2e8f0;">test-run-table.js</span></div>
    <div style="padding-left:76px;"><span style="color:#94a3b8;">&#9492;&#9472;&#9472;</span> <span style="color:#e2e8f0;">alert-badge.js</span></div>
    <div style="padding-left:48px;"><span style="color:#94a3b8;">&#9492;&#9472;&#9472;</span> <span style="color:#3b82f6; font-weight:700;">styles/</span></div>
    <div style="padding-left:76px;"><span style="color:#94a3b8;">&#9500;&#9472;&#9472;</span> <span style="color:#e2e8f0;">main.css</span></div>
    <div style="padding-left:76px;"><span style="color:#94a3b8;">&#9492;&#9472;&#9472;</span> <span style="color:#e2e8f0;">components.css</span></div>
  </div>
</div>

### WebSocket integration

The frontend maintains a single persistent WebSocket connection per page load. The `ConnectionManager` on the server routes push messages back to each connected client by `client_id`. The dashboard subscribes to product-scoped events with:

```javascript
ws.send(JSON.stringify({ type: 'subscribe', product_id: productId }));
```

Updates are applied reactively — quality score cards update without page refresh when a `quality_update` message arrives.

---

## MCP Integration Architecture

TINAA MSP runs the FastMCP 2.0 server on the same port (`8765`) as the REST API, using a different transport path. AI assistants (Claude, Cursor, VS Code with MCP extensions) connect to the MCP endpoint and interact with TINAA through the 14 registered tools.

<div style="background:#1e293b; border:1px solid #334155; border-radius:12px; padding:28px 24px; margin:32px 0; overflow-x:auto;">

  <!-- Top: AI Assistant -->
  <div style="text-align:center; margin-bottom:16px;">
    <div style="display:inline-block; background:#0f172a; border:1px solid #475569; border-radius:8px; padding:12px 28px;">
      <div style="color:#f8fafc; font-weight:700;">AI Assistant</div>
      <div style="color:#94a3b8; font-size:0.85rem;">Claude / IDE</div>
    </div>
  </div>
  <div style="text-align:center; color:#3b82f6; font-size:0.85rem; margin:8px 0;">&#9660; MCP 2.0 protocol (stdio or HTTP/SSE)</div>

  <!-- Middle: FastMCP Server -->
  <div style="text-align:center; margin:16px 0;">
    <div style="display:inline-block; background:#1a2744; border:2px solid #3b82f6; border-radius:8px; padding:16px 28px;">
      <div style="color:#3b82f6; font-weight:700; font-size:1.05rem;">FastMCP Server</div>
      <div style="color:#64748b; font-size:0.85rem; margin-top:4px;">tinaa/mcp_server/server.py</div>
    </div>
  </div>

  <!-- MCP submodules -->
  <div style="display:flex; gap:12px; justify-content:center; flex-wrap:wrap; margin:16px 0;">
    <div style="background:#0f172a; border:1px solid #475569; border-radius:6px; padding:8px 16px; text-align:center;">
      <div style="color:#10b981; font-weight:600; font-size:0.9rem;">tools.py</div>
      <div style="color:#6ee7b7; font-size:0.8rem;">14 tool functions</div>
    </div>
    <div style="background:#0f172a; border:1px solid #475569; border-radius:6px; padding:8px 16px; text-align:center;">
      <div style="color:#10b981; font-weight:600; font-size:0.9rem;">resources.py</div>
      <div style="color:#6ee7b7; font-size:0.8rem;">Resource definitions</div>
    </div>
    <div style="background:#0f172a; border:1px solid #475569; border-radius:6px; padding:8px 16px; text-align:center;">
      <div style="color:#10b981; font-weight:600; font-size:0.9rem;">_mcp.py</div>
      <div style="color:#6ee7b7; font-size:0.8rem;">Shared instance</div>
    </div>
  </div>

  <div style="text-align:center; color:#3b82f6; font-size:0.85rem; margin:12px 0;">&#9660;</div>

  <!-- Bottom: Services Layer -->
  <div style="text-align:center; margin:16px 0 8px;">
    <div style="display:inline-block; background:#1a2744; border:2px solid #f59e0b; border-radius:8px; padding:12px 28px;">
      <div style="color:#f59e0b; font-weight:700;">Services Layer</div>
      <div style="color:#64748b; font-size:0.85rem;">tinaa/services.py</div>
    </div>
  </div>

  <div style="display:flex; gap:10px; justify-content:center; flex-wrap:wrap; margin-top:12px;">
    <span style="background:#0f172a; border:1px solid #334155; border-radius:4px; padding:4px 12px; color:#94a3b8; font-family:monospace; font-size:0.85rem;">RegistryService</span>
    <span style="background:#0f172a; border:1px solid #334155; border-radius:4px; padding:4px 12px; color:#94a3b8; font-family:monospace; font-size:0.85rem;">QualityScorer</span>
    <span style="background:#0f172a; border:1px solid #334155; border-radius:4px; padding:4px 12px; color:#94a3b8; font-family:monospace; font-size:0.85rem;">BaselineManager</span>
    <span style="background:#0f172a; border:1px solid #334155; border-radius:4px; padding:4px 12px; color:#94a3b8; font-family:monospace; font-size:0.85rem;">AnomalyDetector</span>
    <span style="background:#0f172a; border:1px solid #334155; border-radius:4px; padding:4px 12px; color:#94a3b8; font-family:monospace; font-size:0.85rem;">AlertEngine</span>
    <span style="background:#0f172a; border:1px solid #334155; border-radius:4px; padding:4px 12px; color:#94a3b8; font-family:monospace; font-size:0.85rem;">PlaybookValidator</span>
  </div>

</div>

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

The Orchestrator implements a lightweight event bus. Events flow in one direction: external trigger -> Orchestrator -> agent tasks -> results.

### Event lifecycle

<div style="background:#1e293b; border:1px solid #334155; border-radius:12px; padding:24px; margin:32px 0; overflow-x:auto;">

  <div style="display:flex; flex-direction:column; align-items:center; gap:8px;">

    <div style="background:#0f172a; border:1px solid #475569; border-radius:8px; padding:10px 24px; text-align:center;">
      <div style="color:#f8fafc; font-weight:600;">External trigger</div>
      <div style="color:#64748b; font-size:0.8rem;">webhook / API call / schedule</div>
    </div>

    <div style="color:#3b82f6;">&#9660;</div>

    <div style="background:#0f172a; border:1px solid #3b82f6; border-radius:8px; padding:10px 24px; text-align:center;">
      <code style="color:#3b82f6;">orchestrator.handle_event(event_type, payload)</code>
    </div>

    <div style="color:#3b82f6;">&#9660;</div>

    <div style="background:#0f172a; border:1px solid #f59e0b; border-radius:8px; padding:10px 24px; text-align:center;">
      <code style="color:#f59e0b;">_build_tasks_for_event()</code>
      <div style="color:#64748b; font-size:0.8rem;">maps event &rarr; AgentTask list</div>
    </div>

    <div style="color:#3b82f6;">&#9660;</div>

    <div style="background:#0f172a; border:1px solid #f59e0b; border-radius:8px; padding:10px 24px; text-align:center;">
      <code style="color:#f59e0b;">dispatch_task(task)</code>
      <div style="color:#64748b; font-size:0.8rem;">routes task to registered agent by name</div>
    </div>

    <div style="color:#3b82f6;">&#9660;</div>

    <div style="background:#0f172a; border:1px solid #10b981; border-radius:8px; padding:10px 24px; text-align:center;">
      <code style="color:#10b981;">agent.execute(task)</code>
      <div style="color:#64748b; font-size:0.8rem;">agent performs its work</div>
    </div>

    <div style="display:flex; gap:24px; margin-top:4px;">
      <div style="text-align:center;">
        <div style="color:#10b981;">&#9660;</div>
        <div style="background:#0f2a1a; border:1px solid #10b981; border-radius:6px; padding:8px 16px;">
          <div style="color:#10b981; font-weight:600;">SUCCESS</div>
          <div style="color:#6ee7b7; font-size:0.8rem;">status = completed</div>
        </div>
      </div>
      <div style="text-align:center;">
        <div style="color:#ef4444;">&#9660;</div>
        <div style="background:#2a0f0f; border:1px solid #ef4444; border-radius:6px; padding:8px 16px;">
          <div style="color:#ef4444; font-weight:600;">FAILURE</div>
          <div style="color:#fca5a5; font-size:0.8rem;">status = failed</div>
        </div>
      </div>
    </div>

  </div>
</div>

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
