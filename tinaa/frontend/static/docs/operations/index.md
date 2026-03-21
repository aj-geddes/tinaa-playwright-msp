# Operations Guide Overview

This guide is for operations engineers responsible for running TINAA MSP in production. It covers architecture, deployment, monitoring, scaling, database management, security hardening, and incident runbooks.

---

## Operations responsibilities

| Responsibility | Document |
|---------------|---------|
| Understand system components and data flows | [Architecture](architecture.md) |
| Deploy and upgrade TINAA MSP | [Deployment](deployment.md) |
| Monitor TINAA's own health and performance | [Monitoring & Observability](monitoring.md) |
| Scale horizontally or vertically | [Scaling](scaling.md) |
| Manage database schema, retention, and performance | [Database Management](database.md) |
| Harden the installation against threats | [Security Hardening](security.md) |
| Respond to incidents with step-by-step procedures | [Runbooks](runbooks.md) |

---

## SLA targets for TINAA itself

| Metric | Target |
|--------|--------|
| API uptime | 99.9% (< 8.7 hours downtime/year) |
| API p95 response time | < 500 ms |
| Test run queue latency (time from queue to start) | < 30 seconds |
| Monitoring cycle accuracy | Within 10% of configured interval |
| Alert delivery latency | < 60 seconds from trigger to Slack/email |
| Dashboard page load | < 2 seconds |

These are targets for the TINAA platform itself, separate from the quality metrics of the products TINAA monitors.

---

## On-call expectations

The TINAA platform on-call engineer is responsible for:

1. **Acknowledging PagerDuty/Opsgenie alerts** for TINAA infrastructure within 15 minutes.
2. **Diagnosing and resolving** production incidents using the [Runbooks](runbooks.md).
3. **Communicating status** to affected users via the status page or Slack.
4. **Filing post-mortems** for incidents lasting longer than 30 minutes.
5. **Escalating** to the platform team lead if resolution is not achievable within 1 hour.

### Severity levels

| Severity | Impact | Response time |
|----------|--------|--------------|
| P1 — Critical | TINAA is completely down; no tests running | Immediate (< 15 min) |
| P2 — High | Test runs failing for all products; alerts not delivering | < 30 min |
| P3 — Medium | Degraded performance; some features unavailable | < 2 hours |
| P4 — Low | Minor issues; no user-facing impact | Next business day |

---

## Key operational commands

```bash
# Check service status
docker compose ps

# View live logs
docker compose logs -f --tail=100 tinaa-api

# Check database migration state
docker compose exec tinaa-api alembic current

# Run pending migrations
docker compose exec tinaa-api alembic upgrade head

# Restart API server without downtime (rolling restart)
docker compose restart tinaa-api

# Emergency: stop all services
docker compose stop

# Check disk usage
df -h /var/lib/docker

# Check Playwright browser pool
docker compose exec tinaa-api python -c "
import asyncio
from playwright.async_api import async_playwright
async def check():
    async with async_playwright() as p:
        b = await p.chromium.launch()
        print('Browser OK:', await b.version())
        await b.close()
asyncio.run(check())
"
```
