# Troubleshooting

Common issues, diagnostic steps, and resolutions for TINAA MSP.

---

## Connection errors

### Cannot connect to the API

**Symptoms:** `curl http://localhost:8765/health` returns connection refused or times out.

**Diagnosis:**

```bash
# Check if the container/process is running
docker compose ps          # Docker deployment
ps aux | grep uvicorn      # manual deployment

# Check port binding
ss -tlnp | grep 8765

# Check recent logs
docker compose logs --tail=50 tinaa-api
```

**Common causes and resolutions:**

| Cause | Resolution |
|-------|-----------|
| Container not started | `docker compose up -d tinaa-api` |
| Port conflict | Change `TINAA_PORT` to an available port |
| Binding to wrong interface | Set `TINAA_HOST=0.0.0.0` (not `127.0.0.1`) |
| Startup crash | Check logs for Python import errors; run `pip install -e .` to ensure all dependencies are installed |

### Database connection errors

**Symptoms:** API starts but returns 503 on product endpoints, or logs show `asyncpg.exceptions.ConnectionDoesNotExistError`.

**Diagnosis:**

```bash
# Test database connectivity
psql $DATABASE_URL -c "SELECT 1;"

# Check connection pool stats
curl http://localhost:8765/api/v1/health/db   # if available

# Check for too many connections
psql -c "SELECT count(*) FROM pg_stat_activity WHERE datname='tinaa';"
```

**Resolutions:**

- Verify `DATABASE_URL` is correct (including password and database name).
- Increase `DATABASE_POOL_SIZE` if you see pool exhaustion under load.
- Check PostgreSQL's `max_connections` setting (`SHOW max_connections;`).
- Ensure TimescaleDB extension is installed: `SELECT extname FROM pg_extension;`

---

## Playwright failures

### Playwright browser not found

**Symptoms:** Test runs fail immediately with `BrowserType.launch: Executable doesn't exist at...`

**Resolution:**

```bash
# Install the required browsers
playwright install chromium

# For Docker, run inside the container
docker compose exec tinaa-api playwright install chromium

# Install system dependencies (Linux only)
playwright install-deps chromium
```

### Playwright hangs or crashes

**Symptoms:** Test runs get stuck in `running` state; browser processes accumulate.

**Diagnosis:**

```bash
# List Playwright processes
ps aux | grep chromium | grep -v grep

# Kill stuck browsers
pkill -f "chromium.*playwright"

# Check system resources
free -h
df -h
```

**Common causes:**

| Cause | Resolution |
|-------|-----------|
| Out of memory | Reduce `PLAYWRIGHT_BROWSER_POOL_SIZE`; add more RAM |
| Too many concurrent runs | Limit parallel test runs in the admin settings |
| Sandbox disabled in container | Set `--no-sandbox` flag (already configured in Docker deployment) |
| Missing fonts/dependencies | Run `playwright install-deps` |

### Screenshots not saving

**Symptoms:** Test run completes but screenshot links show 404.

**Resolution:**

- Check that the screenshot storage directory is writable by the TINAA process.
- In Docker, ensure the screenshot volume is mounted: `docker compose ps` to verify volume mounts.
- Check disk space: `df -h`.

---

## Migration issues

### Alembic revision mismatch

**Symptoms:** API fails to start with `Target database is not up to date` or tests fail with `column does not exist`.

**Resolution:**

```bash
# Check current state
alembic current

# Apply all pending migrations
alembic upgrade head

# If the database is ahead (e.g. from a downgrade):
alembic stamp head   # marks the current state as head WITHOUT running migrations
```

### Migration fails with constraint violation

**Symptoms:** `alembic upgrade head` fails with a unique constraint or not-null error.

**Resolution:**

1. Identify which migration failed in the output.
2. Open the migration file in `alembic/versions/`.
3. Run the failing SQL manually in `psql` to see the exact error.
4. If data migration is required (e.g. backfilling a new not-null column), add a `UPDATE` step before the `ALTER COLUMN` in the migration file.

---

## GitHub integration issues

See [GitHub Integration — Troubleshooting](github-integration.md#troubleshooting-github-integration) for GitHub-specific issues.

---

## Quality score calculation issues

### Score not updating after a test run

**Symptoms:** Test run shows `passed` but the quality score badge doesn't change.

**Diagnosis:**

```bash
# Check if quality score computation ran
docker compose logs tinaa-api | grep "quality_score"

# Manually trigger a quality score recompute
curl -X POST http://localhost:8765/api/v1/products/$PRODUCT_ID/quality/recompute \
  -H "X-API-Key: $TINAA_API_KEY"
```

### Score unexpectedly low

**Symptoms:** Score dropped significantly without any apparent test failures.

**Diagnosis:**

1. Open the quality score panel in the dashboard.
2. Expand each component to see which one dropped.
3. Check recent test runs for new failures or regressions.
4. Check if any endpoints were added without performance budgets (they default to no budget, which may affect scoring).

---

## Log locations

| Deployment type | Log location |
|-----------------|-------------|
| Docker Compose | `docker compose logs tinaa-api` or `/var/log/tinaa/` (if log file configured) |
| Manual / systemd | `journalctl -u tinaa-api -f` or the path set in `LOG_FILE` |
| Kubernetes | `kubectl logs -l app=tinaa-api -n tinaa` |

### Useful log grep patterns

```bash
# API errors (5xx)
docker compose logs tinaa-api | grep '"status_code": 5'

# Failed test runs
docker compose logs tinaa-api | grep '"trigger": "manual".*"status": "failed"'

# Database pool warnings
docker compose logs tinaa-api | grep 'pool'

# GitHub webhook delivery
docker compose logs tinaa-api | grep 'webhook'

# Playwright errors
docker compose logs tinaa-api | grep 'playwright\|browser\|chromium'
```

---

## Health check endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /health` | Basic liveness check — returns `{"status": "healthy"}` |
| `GET /api/v1/health` | *(if configured)* Detailed health including DB connectivity and Redis |

Use the basic health endpoint for load balancer and Kubernetes liveness probes:

```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8765
  initialDelaySeconds: 10
  periodSeconds: 30
```

---

## Support channels

If you cannot resolve an issue with this guide:

1. **Check the GitHub Issues** on the TINAA MSP repository — your issue may already be filed and resolved.
2. **File a new issue** with:
   - TINAA version (`GET /health` → `version` field)
   - OS and deployment method (Docker / manual)
   - Relevant log output (redact secrets)
   - Steps to reproduce
3. **Community Slack** — `#tinaa-support` channel (if your organisation has access).
4. **Enterprise support** — contact your TINAA account representative.
