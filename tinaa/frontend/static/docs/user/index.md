# TINAA MSP — User Guide Overview

## What is TINAA MSP?

TINAA (Testing Intelligence Network Automation Assistant) MSP is a managed service platform that fuses continuous browser testing with application performance monitoring into a single, unified quality signal. Rather than operating test suites and APM tools independently, TINAA MSP collects test results, Web Vitals, availability data, and security/accessibility signals from every deployment, then synthesises them into a single **Quality Score** (0–100) per product. Teams use that score to gate deployments, track regressions over time, and receive targeted recommendations before problems reach production users.

## What you can do with TINAA MSP

- **Register products and environments** — model your application as a product with one or more environments (production, staging, preview, development), each with its own set of monitored endpoints.
- **Write or auto-generate test playbooks** — declarative YAML playbooks describe browser journeys (navigate, click, fill, assert) that TINAA runs against each environment using Playwright.
- **Monitor endpoints continuously** — TINAA polls registered endpoints on configurable intervals and records response time, status codes, and Web Vitals.
- **Track your Quality Score** — a composite 0–100 score weighted across Test Health (40%), Performance (30%), Security (15%), and Accessibility (15%).
- **Gate deployments on quality** — integrate with GitHub deployments so that pull requests and deploys only proceed when quality gates pass.
- **Receive intelligent alerts** — configure alert rules that fire on score drops, test failures, endpoint outages, or performance regressions, delivered to Slack, email, PagerDuty, GitHub Issues, or custom webhooks.
- **Explore metrics and trends** — view time-series charts for response times, Web Vitals, error rates, and availability with automatic baseline detection.
- **Use the Claude Code MCP** — interact with TINAA from your terminal using natural language commands via the Model Context Protocol server.

## Navigating the dashboard

The TINAA dashboard is divided into the following main areas accessible from the left navigation sidebar:

| Area | What you will find |
|------|--------------------|
| **Products** | List of all registered products; click a product to drill into its environments and quality history. |
| **Test Runs** | Chronological list of test executions with status, duration, pass/fail counts, and links to screenshots. |
| **Playbooks** | Library of test playbooks; create, edit, run, or delete playbooks here. |
| **Metrics** | Time-series charts for response time, Web Vitals, availability, and error rate per endpoint. |
| **Alerts** | Active and resolved alerts with acknowledgement controls and notification channel configuration. |
| **Docs** | This documentation system. |
| **Settings** | API keys, notification channels, GitHub integration, and user preferences. |

The top navigation bar shows the current product context (selectable via the product dropdown), a global search field, and the real-time quality score badge for the selected product.

## Quick links

| Topic | Link |
|-------|------|
| Register your first product | [Getting Started](getting-started.md) |
| Product and environment setup | [Managing Products](products.md) |
| Writing test playbooks | [Test Playbooks](playbooks.md) |
| Understanding your score | [Quality Scores](quality-scores.md) |
| Running and reading tests | [Test Runs](test-runs.md) |
| Metrics and baselines | [Metrics & Monitoring](metrics.md) |
| Setting up alerts | [Alerts & Notifications](alerts.md) |
| Common questions | [FAQ](faq.md) |
