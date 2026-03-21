/**
 * docs.js — Documentation page.
 *
 * Renders:
 * - Three-tab layout: User Guide | Admin Guide | Operations Guide
 * - Markdown content via tinaa-docs-viewer component
 * - Table of contents (auto-generated in the component)
 * - Doc search
 */

const DOC_CONTENT = {
  user: `# TINAA MSP User Guide

## Overview

TINAA MSP (Testing Intelligence Network Automation Assistant — Managed Service Platform)
provides continuous quality management for your web applications.

## Getting Started

### Register Your First Product

1. Navigate to **Settings** in the sidebar.
2. Fill in the product name and repository URL.
3. Click **Register Product**.

Your product will appear in the Dashboard with an initial quality score.

### Setting Up Environments

Environments represent your deployment targets (production, staging, preview).

1. Go to **Settings > Environments**.
2. Select your product.
3. Enter the environment name (e.g. \`production\`) and base URL.
4. Click **Add Environment**.

---

## Quality Score

The quality score (0–100) is a weighted composite of four components:

| Component       | Weight | Description                       |
|-----------------|--------|-----------------------------------|
| Test Health     | 40%    | Pass rate, flakiness, coverage    |
| Performance     | 30%    | Core Web Vitals, response times   |
| Security        | 15%    | HTTPS, headers, vulnerability scan|
| Accessibility   | 15%    | WCAG 2.1 AA compliance            |

### Grade Scale

| Grade | Score Range |
|-------|-------------|
| A     | 90–100      |
| B     | 80–89       |
| C     | 70–79       |
| D     | 60–69       |
| F     | 0–59        |

---

## Playbooks

Playbooks are sequences of automated test steps. Each playbook belongs to a suite type.

### Supported Actions

- \`navigate\` — Load a URL
- \`click\` — Click an element by CSS selector
- \`fill\` — Type text into an input
- \`screenshot\` — Capture a screenshot
- \`wait\` — Pause execution
- \`assert\` — Assert a condition

### Example Playbook (YAML)

\`\`\`yaml
- action: navigate
  url: https://app.example.com
- action: click
  selector: "#login-btn"
- action: fill
  selector: "#email"
  value: "test@example.com"
- action: screenshot
  name: "login-page"
\`\`\`

---

## Metrics

The Metrics page shows performance time-series data. Use the controls to:

- **Select a product** — the data source
- **Choose a time range** — 1h to 30d
- **Switch metric type** — Response Time, Web Vitals, Availability, Error Rate

### Anomaly Detection

TINAA automatically detects anomalies by comparing observed values against the computed baseline.
An anomaly is flagged when the observed value exceeds the P95 baseline by more than 20%.

---

## Alerts

Alerts notify you when metrics cross defined thresholds.

### Severity Levels

- **Critical** — Requires immediate attention
- **Warning** — Investigate soon
- **Info** — Informational only

To acknowledge an alert, click the **Acknowledge** button. To close it, click **Resolve**.
`,

  admin: `# TINAA MSP Admin Guide

## Architecture Overview

TINAA MSP is a FastAPI-based REST API with a vanilla JavaScript SPA frontend.

### Components

- **API** — \`tinaa/api/\` — FastAPI routes for all resources
- **Registry** — \`tinaa/registry/\` — Product/environment/endpoint CRUD
- **Quality** — \`tinaa/quality/\` — Score computation engine
- **APM** — \`tinaa/apm/\` — Baseline and anomaly detection
- **Playbooks** — \`tinaa/playbooks/\` — Test step executor
- **Frontend** — \`tinaa/frontend/\` — SPA served as static files

---

## Configuration

### Environment Variables

| Variable                   | Default              | Description                  |
|----------------------------|----------------------|------------------------------|
| \`DATABASE_URL\`             | SQLite               | Database connection string   |
| \`TINAA_API_KEY_REQUIRED\`   | \`false\`              | Enable API key enforcement   |
| \`TINAA_CORS_ORIGINS\`       | localhost:3000,8080  | Allowed CORS origins         |
| \`REDIS_URL\`                | \`redis://localhost\`  | Redis connection (optional)  |

---

## Database

### Migrations

\`\`\`bash
alembic upgrade head
\`\`\`

### Resetting the Database

\`\`\`bash
rm tinaa.db
alembic upgrade head
\`\`\`

---

## API Documentation

Interactive API documentation is available at:

- **Swagger UI** — \`/api/docs\`
- **ReDoc** — \`/api/redoc\`

---

## Authentication

By default, API key authentication is **disabled**. To enable it:

1. Set \`TINAA_API_KEY_REQUIRED=true\`
2. Set \`TINAA_API_KEY=your-secret-key\`
3. Clients must send the key as \`X-API-Key\` header.

---

## Deployment

### Docker Compose

\`\`\`bash
docker-compose up -d
\`\`\`

### Production

\`\`\`bash
docker-compose -f docker-compose.prod.yml up -d
\`\`\`

### Health Check

\`\`\`
GET /health
\`\`\`

Returns \`{"status": "ok", ...}\` when all services are healthy.
`,

  ops: `# TINAA MSP Operations Guide

## Monitoring

### Health Endpoint

\`\`\`
GET /health
\`\`\`

Response:

\`\`\`json
{
  "status": "ok",
  "version": "2.0.0",
  "services": {
    "database": "ok",
    "redis": "ok"
  }
}
\`\`\`

### Key Metrics to Monitor

- **API response times** — P95 should be < 500ms
- **Database query time** — P95 should be < 100ms
- **Quality score computation** — should complete in < 2s
- **Playbook execution** — depends on test suite size

---

## Log Management

TINAA uses Python's standard \`logging\` module.

### Log Levels

| Level   | When to use               |
|---------|---------------------------|
| DEBUG   | Development only          |
| INFO    | Normal operations         |
| WARNING | Recoverable errors        |
| ERROR   | Action required           |

---

## Backup

### Database Backup (SQLite)

\`\`\`bash
cp tinaa.db tinaa.db.backup.$(date +%Y%m%d)
\`\`\`

### PostgreSQL Backup

\`\`\`bash
pg_dump $DATABASE_URL > tinaa_backup_$(date +%Y%m%d).sql
\`\`\`

---

## Scaling

### Horizontal Scaling

TINAA is stateless (except for database). Run multiple instances behind a load balancer.
Ensure all instances share the same database and Redis.

### Performance Tuning

- Increase \`uvicorn\` workers: \`--workers 4\`
- Enable connection pooling in SQLAlchemy
- Use Redis for caching baseline computations

---

## Incident Response

### Quality Score Drops Unexpectedly

1. Check recent test runs for failures
2. Review anomaly detection in Metrics
3. Verify endpoint health in the product detail page
4. Check for recent deployments in the deployment timeline

### API Is Slow

1. Check database connection pool usage
2. Review recent query patterns
3. Check for missing indexes on \`product_id\` foreign keys
4. Verify Redis connectivity

---

## Maintenance

### Upgrading TINAA

\`\`\`bash
git pull origin main
pip install -e .[dev]
alembic upgrade head
systemctl restart tinaa-api
\`\`\`
`,
};

const TAB_LABELS = [
  { key: "user",  label: "User Guide"       },
  { key: "admin", label: "Admin Guide"      },
  { key: "ops",   label: "Operations Guide" },
];

export async function renderDocs(container) {
  container.innerHTML = `
    <div class="space-y-6">
      <div class="flex items-center justify-between flex-wrap gap-3">
        <h1 class="text-2xl font-bold text-white">Documentation</h1>
        <!-- Doc search -->
        <div class="relative">
          <label for="doc-search" class="sr-only">Search documentation</label>
          <div class="relative">
            <div class="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none"
                 aria-hidden="true">
              <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4 text-slate-400"
                   viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
                   aria-hidden="true" focusable="false">
                <circle cx="11" cy="11" r="8"/>
                <line x1="21" y1="21" x2="16.65" y2="16.65"/>
              </svg>
            </div>
            <input
              id="doc-search"
              type="search"
              placeholder="Search docs…"
              autocomplete="off"
              class="pl-9 pr-4 py-2 text-sm bg-slate-700 border border-slate-600 rounded-md
                     text-slate-200 placeholder-slate-400 w-48
                     focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              aria-label="Search within documentation"
            />
          </div>
        </div>
      </div>

      <!-- Doc tabs -->
      <div role="tablist" aria-label="Documentation sections" id="doc-tabs"
           class="flex gap-1 border-b border-slate-700">
        ${TAB_LABELS.map((t, i) => `
          <button
            role="tab"
            id="dtab-${t.key}"
            aria-selected="${i === 0}"
            aria-controls="doc-panel"
            class="px-4 py-2 text-sm font-medium border-b-2 transition-colors -mb-px
                   focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500
                   ${i === 0
                     ? "border-blue-500 text-white"
                     : "border-transparent text-slate-400 hover:text-white hover:border-slate-500"}"
            data-doc-key="${t.key}"
          >${t.label}</button>
        `).join("")}
      </div>

      <!-- Doc panel -->
      <div
        id="doc-panel"
        role="tabpanel"
        aria-labelledby="dtab-user"
        class="bg-slate-800 rounded-lg border border-slate-700 p-6"
      >
        <tinaa-docs-viewer id="docs-viewer-el"></tinaa-docs-viewer>
      </div>
    </div>
  `;

  const viewer   = container.querySelector("#docs-viewer-el");
  const tabList  = container.querySelector("#doc-tabs");
  const docPanel = container.querySelector("#doc-panel");
  let currentKey = "user";

  const showDoc = (key) => {
    currentKey = key;
    if (viewer) viewer.setContent(DOC_CONTENT[key] || "No content found.");
    docPanel.setAttribute("aria-labelledby", `dtab-${key}`);
  };

  // Render initial
  showDoc("user");

  // Tab click
  tabList.querySelectorAll("[data-doc-key]").forEach((tab, i) => {
    tab.addEventListener("click", () => {
      tabList.querySelectorAll("[role=tab]").forEach((t, j) => {
        const active = t === tab;
        t.setAttribute("aria-selected", String(active));
        t.classList.toggle("border-blue-500", active);
        t.classList.toggle("text-white", active);
        t.classList.toggle("border-transparent", !active);
        t.classList.toggle("text-slate-400", !active);
      });
      showDoc(tab.dataset.docKey);
    });

    tab.addEventListener("keydown", (e) => {
      const tabs = [...tabList.querySelectorAll("[role=tab]")];
      if (e.key === "ArrowRight") tabs[(i + 1) % tabs.length]?.focus();
      if (e.key === "ArrowLeft")  tabs[(i - 1 + tabs.length) % tabs.length]?.focus();
    });
  });

  // Doc search — simple highlight approach
  const searchInput = container.querySelector("#doc-search");
  let searchTimeout;
  searchInput?.addEventListener("input", () => {
    clearTimeout(searchTimeout);
    searchTimeout = setTimeout(() => {
      const q = searchInput.value.trim().toLowerCase();
      const content = container.querySelector(".docs-content");
      if (!content) return;

      if (!q) {
        // Re-render to clear highlights
        showDoc(currentKey);
        return;
      }

      // Scroll to first match
      const walker = document.createTreeWalker(content, NodeFilter.SHOW_TEXT);
      let found = false;
      while (walker.nextNode()) {
        const node = walker.currentNode;
        if (node.textContent.toLowerCase().includes(q)) {
          node.parentElement?.scrollIntoView({ behavior: "smooth", block: "center" });
          found = true;
          break;
        }
      }

      if (!found) {
        _announce(`No matches found for "${q}"`);
      }
    }, 300);
  });
}

function _announce(msg) {
  const el = document.getElementById("aria-announcer");
  if (el) { el.textContent = ""; setTimeout(() => { el.textContent = msg; }, 50); }
}
