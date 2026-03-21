# Configuration

TINAA MSP is configured through environment variables. All settings have sensible defaults for development, but production deployments must set several required values explicitly.

---

## Environment variables reference

### Core settings

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `TINAA_API_KEY` | Yes (production) | `dev-key` | Shared API key for authenticating all API requests. Set to a cryptographically random 32+ character string. |
| `TINAA_API_KEY_REQUIRED` | No | `false` | Set to `true` to enforce API key authentication on all routes. In development this defaults to `false` for convenience. |
| `TINAA_ENV` | No | `development` | Runtime environment: `development`, `staging`, or `production`. Controls log verbosity and safety checks. |

### Database

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | Yes | `sqlite+aiosqlite:///./tinaa.db` | SQLAlchemy async database URL. Use `postgresql+asyncpg://user:pass@host:5432/db` for production. |
| `DATABASE_POOL_SIZE` | No | `10` | SQLAlchemy connection pool size. Increase for high-concurrency deployments. |
| `DATABASE_MAX_OVERFLOW` | No | `20` | Maximum overflow connections above `DATABASE_POOL_SIZE`. |
| `DATABASE_POOL_TIMEOUT` | No | `30` | Seconds to wait for a connection from the pool before raising an error. |
| `DATABASE_ECHO` | No | `false` | Set to `true` to log all SQL statements. Use only for debugging; very verbose. |

### Redis

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `REDIS_URL` | No | *(empty)* | Redis connection URL, e.g. `redis://localhost:6379/0`. Required for async test run queuing in production. If empty, test runs execute synchronously. |
| `REDIS_MAX_CONNECTIONS` | No | `10` | Maximum Redis connection pool size. |

### GitHub App

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `GITHUB_APP_ID` | No | *(empty)* | GitHub App ID (numeric). Required for GitHub integration. |
| `GITHUB_APP_PRIVATE_KEY` | No | *(empty)* | GitHub App RSA private key in PEM format. Provide as a multi-line env var or mount from a file. |
| `GITHUB_WEBHOOK_SECRET` | No | *(empty)* | Secret used to verify GitHub webhook signatures. Must match the secret configured in the GitHub App. |
| `GITHUB_APP_INSTALLATION_ID` | No | *(empty)* | Installation ID when the app is installed on a specific org/repo. |

### Network and CORS

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `TINAA_CORS_ORIGINS` | No | `http://localhost:3000,http://localhost:8080` | Comma-separated list of allowed CORS origins. Set to your dashboard URL in production. |
| `TINAA_HOST` | No | `0.0.0.0` | Host address the API server binds to. |
| `TINAA_PORT` | No | `8765` | Port the API server listens on. |
| `MCP_HOST` | No | `0.0.0.0` | Host address the MCP server binds to. |
| `MCP_PORT` | No | `8080` | Port the MCP server listens on. |

### Logging

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `LOG_LEVEL` | No | `INFO` | Log level: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`. |
| `LOG_FORMAT` | No | `text` | Log format: `text` (human-readable) or `json` (structured JSON for log aggregators). |
| `LOG_FILE` | No | *(empty)* | Path to a log file. Logs to stderr if empty. |

### Playwright and testing

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `PLAYWRIGHT_HEADLESS` | No | `true` | Set to `false` to show browser windows (development only). |
| `PLAYWRIGHT_BROWSER_POOL_SIZE` | No | `2` | Number of concurrent Playwright browser instances. Increase for higher test throughput. |
| `PLAYWRIGHT_DEFAULT_TIMEOUT_MS` | No | `30000` | Default per-step timeout in milliseconds. Overridden by playbook-level `timeout_ms`. |
| `PLAYWRIGHT_SLOWMO_MS` | No | `0` | Add artificial delay between Playwright actions (ms). Use for debugging. |

### APM and monitoring

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `APM_MONITORING_ENABLED` | No | `true` | Enable continuous endpoint monitoring. Set to `false` to disable (e.g. in test environments). |
| `APM_DEFAULT_INTERVAL_SECONDS` | No | `300` | Default monitoring interval when not specified per environment. |
| `APM_BASELINE_WINDOW_DAYS` | No | `7` | Number of days of data used to compute performance baselines. |

---

## .env file setup

Create `.env` in the project root. This file is never committed to version control (it is in `.gitignore`).

### Development `.env`

```bash
# Core
TINAA_ENV=development
TINAA_API_KEY=dev-only-key
TINAA_API_KEY_REQUIRED=false

# Database (SQLite for development)
DATABASE_URL=sqlite+aiosqlite:///./tinaa.db

# Logging
LOG_LEVEL=DEBUG
LOG_FORMAT=text

# Playwright
PLAYWRIGHT_HEADLESS=true
PLAYWRIGHT_BROWSER_POOL_SIZE=1
```

### Production `.env`

```bash
# Core
TINAA_ENV=production
TINAA_API_KEY=<32-char-random-token>
TINAA_API_KEY_REQUIRED=true

# Database
DATABASE_URL=postgresql+asyncpg://tinaa:<password>@postgres:5432/tinaa
DATABASE_POOL_SIZE=20
DATABASE_MAX_OVERFLOW=40

# Redis
REDIS_URL=redis://redis:6379/0

# GitHub
GITHUB_APP_ID=123456
GITHUB_APP_PRIVATE_KEY=-----BEGIN RSA PRIVATE KEY-----\n...\n-----END RSA PRIVATE KEY-----
GITHUB_WEBHOOK_SECRET=<random-webhook-secret>

# Network
TINAA_CORS_ORIGINS=https://tinaa.yourcompany.com
TINAA_PORT=8765

# Logging
LOG_LEVEL=INFO
LOG_FORMAT=json

# Playwright
PLAYWRIGHT_HEADLESS=true
PLAYWRIGHT_BROWSER_POOL_SIZE=4
```

---

## pyproject.toml settings

Project metadata and tool configuration live in `pyproject.toml`. Admins do not typically need to modify this file, but the following sections are relevant:

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"      # use async test functions without decorators
testpaths = ["tests"]
addopts = "-v --tb=short"

[tool.ruff]
target-version = "py311"
line-length = 100

[tool.mypy]
python_version = "3.11"
warn_return_any = true
```

---

## Logging configuration

TINAA uses Python's standard `logging` module with structured output. Log levels and their typical contents:

| Level | Contents |
|-------|---------|
| `DEBUG` | SQL queries, HTTP request details, Playwright step details |
| `INFO` | API requests, test run lifecycle events, monitoring check results |
| `WARNING` | Anomaly detections, alert triggers, slow queries |
| `ERROR` | Failed deliveries, Playwright crashes, database connection errors |
| `CRITICAL` | Service startup failures, unrecoverable errors |

In production, use `LOG_FORMAT=json` and ship logs to your aggregation platform (Datadog, Loki, CloudWatch):

```json
{
  "timestamp": "2026-03-21T10:30:00.123Z",
  "level": "INFO",
  "logger": "tinaa.api.middleware",
  "message": "POST /api/v1/test-runs 201 42ms",
  "request_id": "abc123",
  "method": "POST",
  "path": "/api/v1/test-runs",
  "status_code": 201,
  "duration_ms": 42
}
```

---

## CORS configuration

CORS is configured via `TINAA_CORS_ORIGINS`. In production, restrict this to your dashboard's actual origin:

```bash
TINAA_CORS_ORIGINS=https://tinaa.yourcompany.com
```

If you serve the dashboard and API on the same domain, CORS is not needed; leave `TINAA_CORS_ORIGINS` empty.

If you need multiple origins (e.g. the dashboard and a CI tool):

```bash
TINAA_CORS_ORIGINS=https://tinaa.yourcompany.com,https://ci.yourcompany.com
```

TINAA allows `GET`, `POST`, `PUT`, `DELETE`, `PATCH`, and `OPTIONS` methods, and the `Authorization`, `Content-Type`, and `X-API-Key` headers.
