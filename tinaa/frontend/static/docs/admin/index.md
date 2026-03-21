# Admin Guide Overview

This guide is for administrators who install, configure, and maintain TINAA MSP for their organisation. As an admin you are responsible for setting up the platform, managing GitHub integration, issuing API keys, configuring authentication, and supporting end-users.

---

## Admin responsibilities

| Responsibility | Where |
|---------------|-------|
| Install and upgrade TINAA MSP | [Installation](installation.md) |
| Configure environment variables and service settings | [Configuration](configuration.md) |
| Set up GitHub App and deployment hooks | [GitHub Integration](github-integration.md) |
| Issue and revoke API keys | [Authentication & API Keys](authentication.md) |
| Create organisations and manage user roles | [Multi-Tenancy](multi-tenancy.md) |
| Run database backups and migrations | [Backup & Restore](backup-restore.md) |
| Diagnose and fix operational problems | [Troubleshooting](troubleshooting.md) |

---

## System requirements

### Minimum requirements (development / small teams)

| Component | Minimum |
|-----------|---------|
| CPU | 2 cores |
| RAM | 2 GB |
| Disk | 10 GB |
| Python | 3.11+ |
| Database | SQLite (bundled) |
| OS | Linux, macOS, or Windows (WSL2) |

### Recommended requirements (production)

| Component | Recommended |
|-----------|------------|
| CPU | 4+ cores |
| RAM | 8 GB |
| Disk | 50 GB SSD |
| Python | 3.11+ |
| Database | PostgreSQL 15+ with TimescaleDB extension |
| Cache / Queue | Redis 7+ |
| Container runtime | Docker 24+ with Compose v2 |
| OS | Ubuntu 22.04 LTS or Debian 12 |

### Network requirements

- Outbound HTTPS (443) to GitHub (api.github.com, hooks.github.com) for GitHub App functionality.
- Outbound HTTPS to target product URLs for monitoring and testing.
- Inbound port 8765 (API server) exposed to users and CI/CD systems.
- Inbound port 8080 (MCP server) exposed to Claude Code users.
- Redis accessible from the API server (default port 6379).

---

## Quick setup checklist

Use this checklist when setting up a new TINAA MSP instance:

- [ ] Review system requirements and provision a suitable host.
- [ ] Install Docker and Docker Compose (or Python 3.11+ for manual install).
- [ ] Clone the repository and configure `.env` file.
- [ ] Set `TINAA_API_KEY` to a secure random value.
- [ ] Configure `DATABASE_URL` (PostgreSQL recommended for production).
- [ ] Configure `REDIS_URL`.
- [ ] Run `docker compose up -d` (or `uvicorn` for manual install).
- [ ] Verify health at `GET /health` — should return `{"status": "healthy"}`.
- [ ] Run database migrations: `alembic upgrade head`.
- [ ] Install Playwright browsers: `playwright install chromium`.
- [ ] (Optional) Create a GitHub App and configure `GITHUB_APP_ID`, `GITHUB_APP_PRIVATE_KEY`, `GITHUB_WEBHOOK_SECRET`.
- [ ] Create the first product via the dashboard or API.
- [ ] Configure at least one alert notification channel.
- [ ] Test a manual test run and confirm results appear in the dashboard.
