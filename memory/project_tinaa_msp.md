---
name: TINAA MSP Product Vision
description: TINAA is a Managed Service Platform fusing Testing + APM — agent-based continuous quality for registered products with GitHub integration, Quality Score, and multi-surface access
type: project
---

TINAA MSP = Testing Intelligence Network Automation Assistant — Managed Service Platform.

Core concept: Register your products and endpoints, TINAA autonomously tests, monitors, and improves application quality continuously. Combines functional testing (Playwright) with APM (synthetic monitoring, Web Vitals, endpoint profiling) into a unified Quality Score.

**Why:** Traditional testing and APM are separate tools requiring manual setup and maintenance. TINAA unifies them into an agent-based managed service that explores codebases, auto-generates tests, monitors performance, and evolves with the product.

**How to apply:**
- All architecture decisions should serve the "managed service" model — autonomous, continuous, product-centric
- Product Registry is the first-class entity; everything anchors to Products
- Quality Score (0-100, weighted: 40% tests, 30% perf, 15% security, 15% accessibility) is the signature metric
- GitHub App integration is core (webhooks, Checks API, Deployment Protection Rules)
- Multi-surface access: Claude Code MCP, GitHub App, HTTP API/Dashboard, Claude API (headless/CI)
- Agent architecture: Orchestrator → Explorer, Test Designer, Test Runner, APM, Analyst, Reporter agents
- Implementation phases: Registry → APM → Codebase Intelligence → Quality Engine → Enterprise
- Full product definition lives at docs/PRODUCT_DEFINITION.md
