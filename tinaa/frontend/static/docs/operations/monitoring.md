# Monitoring & Observability

This document covers monitoring TINAA MSP itself — distinct from the application performance monitoring TINAA provides for your products. Use these metrics and dashboards to ensure the TINAA platform is healthy and performant.

---

## TINAA's own health metrics

Monitor these metrics to assess the health of the TINAA platform:

| Metric | Description | Alert threshold |
|--------|-------------|----------------|
| `tinaa_api_requests_total` | Total API requests by method, path, status | N/A (counter) |
| `tinaa_api_request_duration_seconds` | API request duration (histogram) | p95 > 2 s |
| `tinaa_test_runs_total` | Test runs completed by status (passed, failed, error) | Error rate > 5% |
| `tinaa_test_run_queue_depth` | Number of test runs waiting to start | > 20 queued |
| `tinaa_test_run_duration_seconds` | Test run wall-clock duration (histogram) | p95 > 600 s |
| `tinaa_browser_pool_active` | Number of Playwright browsers currently executing tests | > pool size (stuck) |
| `tinaa_monitoring_cycles_total` | Number of endpoint monitoring cycles completed | N/A |
| `tinaa_alerts_sent_total` | Alerts sent by channel type and severity | N/A |

---

## Database monitoring

### Connection pool

Monitor the SQLAlchemy connection pool to detect exhaustion:

```bash
# Current connections to TINAA database
psql -c "
  SELECT count(*) AS total,
    sum(CASE WHEN state = 'active' THEN 1 ELSE 0 END) AS active,
    sum(CASE WHEN state = 'idle' THEN 1 ELSE 0 END) AS idle,
    sum(CASE WHEN state = 'idle in transaction' THEN 1 ELSE 0 END) AS idle_in_tx
  FROM pg_stat_activity
  WHERE datname = 'tinaa';
"
```

Alert when `idle in transaction` count is consistently > 0 (may indicate uncommitted transactions).

### Query latency

```sql
-- Top 10 slowest queries (requires pg_stat_statements extension)
SELECT query,
       calls,
       round(total_exec_time::numeric, 2) AS total_ms,
       round(mean_exec_time::numeric, 2) AS mean_ms,
       round(stddev_exec_time::numeric, 2) AS stddev_ms
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;
```

### Disk usage

```bash
# Database size
psql -c "SELECT pg_size_pretty(pg_database_size('tinaa'));"

# Table sizes (top 10)
psql -d tinaa -c "
  SELECT table_name,
    pg_size_pretty(pg_total_relation_size(quote_ident(table_name))) AS total_size
  FROM information_schema.tables
  WHERE table_schema = 'public'
  ORDER BY pg_total_relation_size(quote_ident(table_name)) DESC
  LIMIT 10;
"

# TimescaleDB chunk sizes
psql -d tinaa -c "
  SELECT hypertable_name,
    pg_size_pretty(hypertable_size(hypertable_name::regclass))
  FROM timescaledb_information.hypertables;
"
```

Alert when database disk usage exceeds 70% of available space.

---

## Redis monitoring

### Basic health check

```bash
redis-cli ping         # should return PONG
redis-cli info server  # server version and config
redis-cli info memory  # memory usage
redis-cli info clients # connected clients
```

### Queue depth

```bash
# Number of test run jobs waiting in queue
redis-cli llen tinaa:test_runs:queue

# Number of monitoring jobs scheduled
redis-cli zcard tinaa:monitoring:schedule
```

Alert when queue depth (`tinaa:test_runs:queue`) exceeds 20 items — this indicates workers are not keeping up with demand.

### Memory usage

```bash
redis-cli info memory | grep used_memory_human
```

Alert when Redis memory usage exceeds 80% of `maxmemory` setting.

---

## Playwright browser pool monitoring

### Browser pool health

```bash
# Count running Chromium processes
ps aux | grep -c '[c]hromium.*playwright'

# Expected: should equal PLAYWRIGHT_BROWSER_POOL_SIZE when tests are running
# and 0 when idle
```

### Detecting stuck browsers

If a Playwright process runs for longer than 10 minutes (maximum test run duration), it is likely stuck:

```bash
# Find long-running Chromium processes
ps aux | awk '/chromium.*playwright/ && $10 > "10:00" {print $0}'
```

If stuck processes are found, kill them and check the corresponding test run status in the database — set it to `error` manually if it's stuck in `running`.

---

## Application logs

### Structured JSON logging (production)

In production, TINAA emits JSON-structured logs. Each log line contains:

```json
{
  "timestamp": "2026-03-21T10:30:00.123Z",
  "level": "INFO",
  "logger": "tinaa.api.middleware",
  "message": "GET /api/v1/products 200 12ms",
  "request_id": "abc-123",
  "method": "GET",
  "path": "/api/v1/products",
  "status_code": 200,
  "duration_ms": 12,
  "user_agent": "TINAA-Dashboard/2.0"
}
```

### Log aggregation

Ship logs to your aggregation platform using your preferred agent:

**Datadog Agent:**
```yaml
# /etc/datadog-agent/conf.d/tinaa.d/conf.yaml
logs:
  - type: docker
    service: tinaa-api
    source: python
    tags:
      - env:production
      - version:2.0.0
```

**Grafana Loki / promtail:**
```yaml
# promtail config
scrape_configs:
  - job_name: tinaa
    docker_sd_configs:
      - host: unix:///var/run/docker.sock
    relabel_configs:
      - source_labels: [__meta_docker_container_name]
        regex: tinaa.*
        action: keep
```

### Log level guide

| Situation | Expected level |
|-----------|---------------|
| Normal API request | INFO |
| Successful test run | INFO |
| Alert triggered | WARNING |
| Anomaly detected | WARNING |
| Test run failed (expected) | INFO |
| Database connection timeout | ERROR |
| Playwright browser crash | ERROR |
| Failed alert delivery | ERROR |
| Migration error | CRITICAL |

---

## OpenTelemetry integration

TINAA MSP emits OpenTelemetry (OTEL) traces and metrics when the OTEL SDK is configured. Enable by setting:

```bash
OTEL_SERVICE_NAME=tinaa-msp
OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4317
OTEL_TRACES_SAMPLER=parentbased_traceidratio
OTEL_TRACES_SAMPLER_ARG=0.1   # sample 10% of traces in production
```

Exported spans include:
- `tinaa.api.request` — per-request spans with HTTP attributes
- `tinaa.test_run.execute` — spans for each test run with playbook and step counts
- `tinaa.quality.compute` — spans for quality score computation
- `tinaa.alert.evaluate` — spans for alert rule evaluation

View traces in Jaeger, Zipkin, Tempo, or any OTLP-compatible backend.

---

## Recommended dashboards

If using Grafana, create dashboards for:

1. **TINAA API Health** — request rate, error rate, p50/p95/p99 latency by endpoint.
2. **Test Run Throughput** — runs/hour by status (passed, failed, error), queue depth over time.
3. **Database Performance** — connection pool utilisation, slow queries, disk growth.
4. **Alert Activity** — alerts triggered/resolved per hour, delivery latency by channel.
5. **Browser Pool** — active browsers over time, stuck browser detection.
