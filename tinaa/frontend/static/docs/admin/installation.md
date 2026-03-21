# Installation

TINAA MSP can be installed in two ways: via Docker Compose (recommended for production) or as a Python package for development and custom deployments.

---

## Option 1 — Docker Compose (recommended)

Docker Compose sets up TINAA MSP with PostgreSQL, TimescaleDB, and Redis in a single command.

### Prerequisites

- Docker Engine 24.0+
- Docker Compose v2.20+
- 8 GB RAM available
- Outbound internet access (to pull images and reach GitHub)

### Steps

**1. Clone the repository**

```bash
git clone https://github.com/your-org/tinaa-playwright-msp.git
cd tinaa-playwright-msp
```

**2. Create your environment file**

```bash
cp .env.example .env
```

Edit `.env` and set the required values (see [Configuration](configuration.md) for the full reference):

```bash
TINAA_API_KEY=change-this-to-a-secure-random-value
DATABASE_URL=postgresql+asyncpg://tinaa:tinaa@postgres:5432/tinaa
REDIS_URL=redis://redis:6379/0
```

**3. Start the services**

```bash
docker compose up -d
```

This starts:
- `tinaa-api` — FastAPI server on port 8765
- `tinaa-mcp` — MCP server on port 8080
- `postgres` — PostgreSQL 15 with TimescaleDB extension
- `redis` — Redis 7

**4. Run database migrations**

```bash
docker compose exec tinaa-api alembic upgrade head
```

**5. Install Playwright browsers**

```bash
docker compose exec tinaa-api playwright install chromium
```

**6. Verify the installation**

```bash
curl http://localhost:8765/health
# Expected: {"status": "healthy", "version": "2.0.0", ...}
```

Open the dashboard at `http://localhost:8765`.

### Production compose file

For production deployments, use `docker-compose.prod.yml`:

```bash
docker compose -f docker-compose.prod.yml up -d
```

The production compose file adds:
- TLS termination via Caddy reverse proxy
- Non-root container users
- Read-only filesystem for application containers
- Resource limits (CPU and memory)
- Restart policies (`unless-stopped`)

---

## Option 2 — Manual Python installation

For development or custom deployments without Docker.

### Prerequisites

- Python 3.11 or 3.12
- pip 23+ or pipx
- PostgreSQL 15+ (optional; SQLite works for development)
- Redis 7+ (optional; required for production queue processing)

### Steps

**1. Clone and install**

```bash
git clone https://github.com/your-org/tinaa-playwright-msp.git
cd tinaa-playwright-msp
pip install -e ".[dev]"
```

**2. Install Playwright browsers**

```bash
playwright install chromium
# For cross-browser testing:
playwright install firefox
# Install system dependencies (Linux only):
playwright install-deps
```

**3. Configure environment**

```bash
cp .env.example .env
# Edit .env with your database and Redis URLs
```

For development with SQLite:

```bash
DATABASE_URL=sqlite+aiosqlite:///./tinaa.db
REDIS_URL=  # leave empty to disable async queue (runs synchronously)
TINAA_API_KEY=dev-only-key-change-for-production
```

**4. Run migrations**

```bash
alembic upgrade head
```

**5. Start the API server**

```bash
uvicorn tinaa.api.app:create_app --factory --host 0.0.0.0 --port 8765 --reload
```

**6. Start the MCP server** *(optional, for Claude Code integration)*

```bash
python -m tinaa.mcp_server.server
```

**7. Verify**

```bash
curl http://localhost:8765/health
```

---

## Database setup

### PostgreSQL with TimescaleDB (production)

TimescaleDB is required for efficient time-series storage of metrics data. Without it, the metrics hypertables are not created and metric queries will be slow at scale.

**Install TimescaleDB on Ubuntu:**

```bash
# Add TimescaleDB repository
echo "deb https://packagecloud.io/timescale/timescaledb/ubuntu/ $(lsb_release -c -s) main" \
  | sudo tee /etc/apt/sources.list.d/timescaledb.list
wget --quiet -O - https://packagecloud.io/timescale/timescaledb/gpgkey | sudo apt-key add -
sudo apt-get update
sudo apt-get install -y timescaledb-2-postgresql-15

# Configure
sudo timescaledb-tune --quiet --yes
sudo systemctl restart postgresql
```

**Create the database:**

```bash
sudo -u postgres psql -c "CREATE USER tinaa WITH PASSWORD 'your-secure-password';"
sudo -u postgres psql -c "CREATE DATABASE tinaa OWNER tinaa;"
sudo -u postgres psql -d tinaa -c "CREATE EXTENSION IF NOT EXISTS timescaledb;"
```

### SQLite (development only)

SQLite requires no setup — just set `DATABASE_URL=sqlite+aiosqlite:///./tinaa.db` and run migrations. SQLite does not support TimescaleDB hypertables, so metrics are stored in regular tables with a simple index on the timestamp column.

---

## Initial configuration

After installation, complete these steps:

1. **Set `TINAA_API_KEY`** — this is the shared API key for all API access. Generate a secure value:

   ```bash
   python -c "import secrets; print(secrets.token_urlsafe(32))"
   ```

2. **Configure CORS origins** if your frontend is served from a different origin:

   ```bash
   TINAA_CORS_ORIGINS=https://your-dashboard.example.com,https://api.example.com
   ```

3. **Enable API key enforcement** for production:

   ```bash
   TINAA_API_KEY_REQUIRED=true
   ```

4. **Set up log output**:

   ```bash
   LOG_LEVEL=INFO
   LOG_FORMAT=json   # structured JSON for log aggregation (default: text for dev)
   ```
