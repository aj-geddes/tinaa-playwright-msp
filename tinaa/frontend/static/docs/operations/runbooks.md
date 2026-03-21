# Runbooks

Step-by-step procedures for common operational incidents. Each runbook follows the same structure: symptoms, diagnosis, resolution, and prevention.

---

## Runbook: TINAA is unresponsive

**Severity:** P1

### Symptoms

- `curl http://tinaa.yourcompany.com/health` returns connection refused, timeout, or 5xx.
- Dashboard shows "Failed to connect to TINAA API".
- Users report they cannot access the platform.

### Diagnosis

```bash
# Step 1: Check if the container/process is running
docker compose ps
# Expected: tinaa-api should show "Up" and healthy

# Step 2: Check recent logs for crash cause
docker compose logs --tail=100 tinaa-api

# Step 3: Check system resources (OOM, disk full)
free -h              # available RAM
df -h /              # disk usage
uptime               # load average

# Step 4: Check if the port is bound
ss -tlnp | grep 8765
```

### Resolution

**Container crashed:**
```bash
docker compose up -d tinaa-api
# Wait 15 seconds for startup
curl http://localhost:8765/health
```

**OOM (out of memory):**
```bash
# Check for OOM kills in system logs
dmesg | grep -i "out of memory\|oom"
# Resolution: increase available RAM or reduce PLAYWRIGHT_BROWSER_POOL_SIZE
docker compose stop
# After adding RAM or adjusting config:
docker compose up -d
```

**Disk full:**
```bash
# Free space quickly by clearing Docker logs and old screenshots
docker compose stop
docker system prune -f --volumes  # WARNING: removes stopped containers
# More targeted: remove old screenshot files
find /app/screenshots -mtime +7 -delete
docker compose up -d
```

**Python import error at startup:**
```bash
docker compose logs tinaa-api | grep "ImportError\|ModuleNotFound"
# Resolution: reinstall dependencies
docker compose exec tinaa-api pip install -e .
docker compose restart tinaa-api
```

### Prevention

- Configure memory limits (`mem_limit: 2g`) to prevent OOM from cascading to other services.
- Set up disk usage alerts at 70% and 85%.
- Configure liveness probes to auto-restart crashed containers.
- Monitor `tinaa_api_requests_total` — a sudden drop to zero indicates the API is down.

---

## Runbook: Database connection exhaustion

**Severity:** P2

### Symptoms

- API returns HTTP 503 on product or test run endpoints.
- Logs show `asyncpg.exceptions.TooManyConnectionsError` or `pool timeout`.
- `pg_stat_activity` shows connection count near `max_connections`.

### Diagnosis

```bash
# Step 1: Count active connections
psql -c "
  SELECT count(*), state
  FROM pg_stat_activity
  WHERE datname = 'tinaa'
  GROUP BY state;
"

# Step 2: Identify connection holders
psql -c "
  SELECT pid, usename, application_name, state, query_start, query
  FROM pg_stat_activity
  WHERE datname = 'tinaa' AND state != 'idle'
  ORDER BY query_start;
"

# Step 3: Check for idle-in-transaction connections (common leak)
psql -c "
  SELECT count(*) FROM pg_stat_activity
  WHERE datname = 'tinaa' AND state = 'idle in transaction';
"
```

### Resolution

**Immediate: kill idle-in-transaction connections**
```bash
psql -c "
  SELECT pg_terminate_backend(pid)
  FROM pg_stat_activity
  WHERE datname = 'tinaa'
    AND state = 'idle in transaction'
    AND query_start < NOW() - INTERVAL '5 minutes';
"
```

**Reduce pool size per instance:**
```bash
# .env — reduce pool to make room for multiple instances
DATABASE_POOL_SIZE=5
DATABASE_MAX_OVERFLOW=5
docker compose restart tinaa-api
```

**Add PgBouncer for connection multiplexing:**
See [Scaling — connection pooling](scaling.md#connection-pooling).

**Increase PostgreSQL max_connections (temporary):**
```bash
# postgresql.conf
max_connections = 150    # increase with caution — uses RAM
# Then reload
psql -c "SELECT pg_reload_conf();"
```

### Prevention

- Deploy PgBouncer in transaction mode for production multi-instance deployments.
- Set `DATABASE_POOL_TIMEOUT=15` to fail fast rather than queue indefinitely.
- Alert when `pg_stat_activity` count exceeds 80% of `max_connections`.

---

## Runbook: Playwright browser crashes

**Severity:** P2

### Symptoms

- Test runs stuck in `running` state for > 10 minutes.
- `ps aux | grep chromium` shows many zombie or defunct processes.
- Logs show `Target page, context or browser has been closed`.
- New test runs are not being picked up despite queue depth > 0.

### Diagnosis

```bash
# Step 1: Count Chromium processes
ps aux | grep -c '[c]hromium.*playwright'

# Step 2: Find stuck processes (running > 10 min)
ps aux | awk '/chromium/ && $10 > "10:00"'

# Step 3: Check test runs in "running" state
psql -d tinaa -c "
  SELECT id, product_id, started_at, status
  FROM test_runs
  WHERE status = 'running'
    AND started_at < NOW() - INTERVAL '10 minutes';
"

# Step 4: Check system memory
free -h
```

### Resolution

**Kill stuck browser processes:**
```bash
pkill -f "chromium.*playwright"
# Wait 5 seconds
sleep 5
# Verify they are gone
ps aux | grep -c '[c]hromium.*playwright'
```

**Update stuck test runs:**
```bash
psql -d tinaa -c "
  UPDATE test_runs
  SET status = 'error',
      completed_at = NOW(),
      error_message = 'Browser process crashed; manually recovered by ops'
  WHERE status = 'running'
    AND started_at < NOW() - INTERVAL '10 minutes';
"
```

**Restart the worker:**
```bash
docker compose restart tinaa-api
# or for a dedicated worker container:
docker compose restart tinaa-worker
```

### Prevention

- Set `PLAYWRIGHT_DEFAULT_TIMEOUT_MS=30000` and a maximum run duration (default 30 min).
- Configure a watchdog cron job to kill Chromium processes older than 15 minutes.
- Alert when `tinaa_browser_pool_active` equals the pool size for > 15 consecutive minutes.
- Allocate sufficient memory: each Chromium instance needs 400–800 MB during active tests.

---

## Runbook: High disk usage

**Severity:** P3

### Symptoms

- `df -h` shows disk usage > 85%.
- Logs contain `[Errno 28] No space left on device`.
- Database write failures for metrics and test results.

### Diagnosis

```bash
# Step 1: Find largest directories
du -sh /var/lib/docker/* | sort -rh | head -10

# Step 2: Find largest log files
find /var/log -name "*.log" -size +100M

# Step 3: Find old screenshots
du -sh /app/screenshots/

# Step 4: Check database size
psql -d tinaa -c "SELECT pg_size_pretty(pg_database_size('tinaa'));"

# Step 5: Check Docker image and volume usage
docker system df
```

### Resolution

**Clean Docker artefacts (safe to run any time):**
```bash
docker image prune -f                    # remove dangling images
docker container prune -f                # remove stopped containers
docker volume prune -f                   # remove unused volumes
```

**Remove old screenshots:**
```bash
find /app/screenshots -mtime +30 -delete
echo "Removed screenshots older than 30 days"
```

**Truncate old log files:**
```bash
# Rotate Docker container logs
for container in $(docker ps -q); do
  echo "" > $(docker inspect --format='{{.LogPath}}' $container)
done
```

**Apply TimescaleDB retention policy immediately:**
```bash
psql -d tinaa -c "
  SELECT drop_chunks('endpoint_metrics', older_than => INTERVAL '90 days');
  SELECT drop_chunks('web_vitals', older_than => INTERVAL '90 days');
"
psql -d tinaa -c "VACUUM FULL ANALYZE endpoint_metrics;"
```

### Prevention

- Configure TimescaleDB automatic retention policies (see [Database Management](database.md)).
- Alert at 70% disk usage to have time to react before critical.
- Set up automated screenshot cleanup for files older than 30 days via cron.
- Add Docker log rotation in `/etc/docker/daemon.json`:
  ```json
  {"log-driver": "json-file", "log-opts": {"max-size": "100m", "max-file": "3"}}
  ```

---

## Runbook: Test runs stuck in queued state

**Severity:** P2

### Symptoms

- `GET /api/v1/test-runs` shows many runs with `status: queued`.
- New test runs are not transitioning to `running`.
- Queue depth in Redis is growing (`redis-cli llen tinaa:test_runs:queue > 20`).

### Diagnosis

```bash
# Step 1: Check Redis queue depth
redis-cli llen tinaa:test_runs:queue

# Step 2: Check if worker is running
docker compose ps tinaa-worker   # or tinaa-api for single-container deployment

# Step 3: Check Redis connectivity from worker
docker compose exec tinaa-api redis-cli -u $REDIS_URL ping

# Step 4: Check worker logs
docker compose logs --tail=50 tinaa-worker

# Step 5: Verify browser pool is not exhausted
docker compose exec tinaa-api python -c "
import os; print('Pool size:', os.environ.get('PLAYWRIGHT_BROWSER_POOL_SIZE', '2'))
"
```

### Resolution

**Worker not running:**
```bash
docker compose up -d tinaa-worker
# or for single-container:
docker compose restart tinaa-api
```

**Redis connection failed:**
```bash
# Restart Redis
docker compose restart redis
# Wait for Redis to be ready
redis-cli -u $REDIS_URL ping   # should return PONG
# Then restart worker
docker compose restart tinaa-api
```

**Browser pool exhausted (all browsers executing long-running tests):**
```bash
# Wait for current tests to complete, or:
# Increase pool size temporarily
PLAYWRIGHT_BROWSER_POOL_SIZE=4 docker compose restart tinaa-api
```

**Queue populated but `REDIS_URL` not set (synchronous mode):**

If `REDIS_URL` is empty, test runs execute synchronously and should not queue. Check if there is a configuration mismatch:
```bash
echo $REDIS_URL   # must be non-empty for queue mode
```

### Prevention

- Monitor `redis-cli llen tinaa:test_runs:queue` and alert when > 20.
- Set a dead-letter queue for jobs that fail to start after 3 retries.
- Use Kubernetes readiness probes to route traffic away from unhealthy workers.

---

## Runbook: Quality score calculation incorrect

**Severity:** P3

### Symptoms

- Quality score displayed is unexpectedly high or low.
- Score does not change after a test run completes.
- Component scores (Test Health, Performance, etc.) seem inconsistent with test results.

### Diagnosis

```bash
# Step 1: Verify the most recent quality score record
psql -d tinaa -c "
  SELECT product_id, score, grade, computed_at,
    (components->>'test_health')::text AS test_health,
    (components->>'performance_health')::text AS performance_health
  FROM quality_scores
  WHERE product_id = '$PRODUCT_ID'
  ORDER BY computed_at DESC
  LIMIT 3;
"

# Step 2: Verify the most recent test run completed successfully
psql -d tinaa -c "
  SELECT id, status, started_at, completed_at
  FROM test_runs
  WHERE product_id = '$PRODUCT_ID'
  ORDER BY created_at DESC
  LIMIT 5;
"

# Step 3: Check test run results
psql -d tinaa -c "
  SELECT tr.id, trr.step_action, trr.status, trr.duration_ms
  FROM test_run_results trr
  JOIN test_runs tr ON tr.id = trr.test_run_id
  WHERE tr.product_id = '$PRODUCT_ID'
  ORDER BY tr.created_at DESC, trr.step_index ASC
  LIMIT 20;
"

# Step 4: Manually trigger quality score recomputation
curl -X POST http://localhost:8765/api/v1/products/$PRODUCT_ID/quality/recompute \
  -H "X-API-Key: $TINAA_API_KEY"
```

### Resolution

**Score not updated after test run:**
```bash
# Trigger manual recompute
curl -X POST http://localhost:8765/api/v1/products/$PRODUCT_ID/quality/recompute \
  -H "X-API-Key: $TINAA_API_KEY"
```

**Score seemingly too high (missing test failures):**
- Check if test runs with `status: failed` are included in the score computation. Runs with status `error` (infrastructure failures) are excluded from scoring.
- Verify `TestHealthInput.total_tests` and `passed_tests` fields are populated correctly in the quality_scores record.

**Performance component is 100 but pages are slow:**
- Performance budgets may not be configured for the endpoints.
- Without budgets, endpoint budget compliance defaults to 100%.
- Add `performance_budget_ms` to your endpoint configuration.

### Prevention

- Alert when a quality score changes by > 20 points without a corresponding test run.
- Validate quality score computation in integration tests after model changes.
- Log quality score inputs alongside outputs for auditing.
