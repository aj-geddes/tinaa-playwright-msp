# Scaling

TINAA MSP can be scaled horizontally (more instances) and vertically (larger instances). This document describes scaling strategies for each component and provides sizing guidance based on product count.

---

## Horizontal scaling (multiple API server instances)

The TINAA API server is stateless — all state lives in the database and Redis. You can run multiple API server instances behind a load balancer.

### Requirements for horizontal scaling

1. **Shared PostgreSQL** — all instances must connect to the same database.
2. **Shared Redis** — the test run queue is in Redis; all instances must use the same Redis.
3. **Sticky WebSocket sessions** (optional) — if the dashboard uses WebSocket for live updates, route WebSocket connections to the same instance, or replace with a Redis pub/sub broadcast.

### Docker Compose scaling

```bash
# Scale to 3 API instances
docker compose -f docker-compose.prod.yml up -d --scale tinaa-api=3
```

With a Caddy or Nginx load balancer, upstream traffic is round-robined across all instances.

### Kubernetes Horizontal Pod Autoscaler

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: tinaa-api
  namespace: tinaa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: tinaa-api
  minReplicas: 2
  maxReplicas: 10
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80
```

---

## Database scaling

### Connection pooling

The API server uses SQLAlchemy's async connection pool. Default pool size is 10 per instance. For 3 instances, this means up to 30 connections from TINAA plus overhead from other clients. PostgreSQL's default `max_connections` is 100.

Recommended configuration for multi-instance deployments:

```bash
# .env — adjust per instance count
DATABASE_POOL_SIZE=5           # reduced per instance when scaling out
DATABASE_MAX_OVERFLOW=10
```

For larger deployments, add [PgBouncer](https://www.pgbouncer.org/) as a connection pooler between TINAA instances and PostgreSQL:

```
TINAA instances → PgBouncer (transaction mode, pool=50) → PostgreSQL (max_connections=100)
```

### Read replicas

Metric queries (time-series lookups, trend analysis) are read-heavy. Route them to a PostgreSQL read replica:

```bash
# Primary — for writes
DATABASE_URL=postgresql+asyncpg://tinaa:pass@primary:5432/tinaa

# Replica — for metric reads (configure in application settings)
DATABASE_REPLICA_URL=postgresql+asyncpg://tinaa:pass@replica:5432/tinaa
```

TimescaleDB supports streaming replication to read replicas natively.

---

## Browser pool scaling (multiple Playwright workers)

Each Playwright browser can execute one playbook at a time. To run more tests concurrently, increase the browser pool size or run multiple worker containers.

### Increasing pool size (vertical)

```bash
# .env
PLAYWRIGHT_BROWSER_POOL_SIZE=4   # run up to 4 concurrent browser sessions
```

Each Chromium instance uses approximately:
- 200–400 MB RAM when idle
- 400–800 MB RAM during active test execution

With `PLAYWRIGHT_BROWSER_POOL_SIZE=4` and 2 GB RAM available for browsers, you have adequate headroom.

### Separate worker containers (horizontal)

Dedicated worker containers pull test jobs from the Redis queue:

```yaml
# docker-compose.prod.yml addition
services:
  tinaa-worker:
    image: tinaa-msp:2.0.0
    command: ["python", "-m", "tinaa.worker"]
    environment:
      DATABASE_URL: ${DATABASE_URL}
      REDIS_URL: ${REDIS_URL}
      PLAYWRIGHT_BROWSER_POOL_SIZE: "2"
      PLAYWRIGHT_HEADLESS: "true"
    deploy:
      replicas: 3     # 3 workers × 2 browsers each = 6 concurrent tests
```

Worker containers do not need an HTTP server — they only pull from the Redis queue.

---

## Queue-based test execution

When `REDIS_URL` is configured, test runs are queued in Redis and executed by worker processes asynchronously:

```
API server: creates TestRun record (status: queued)
          → pushes job to Redis list: LPUSH tinaa:test_runs:queue <run_id>

Worker process: BLPOP tinaa:test_runs:queue
              → fetches TestRun from database
              → executes playbooks via Playwright
              → updates TestRun record (status: passed/failed)
              → pushes results via WebSocket
```

Without Redis (`REDIS_URL` empty), test runs execute synchronously in the API request handler — suitable for development but not for production.

### Queue monitoring

```bash
redis-cli llen tinaa:test_runs:queue    # queued job count
redis-cli lrange tinaa:test_runs:queue 0 -1  # list queued run IDs
```

---

## Resource sizing guide

### Small (1–10 products)

| Component | Spec |
|-----------|------|
| API server | 1 instance, 1 CPU, 1 GB RAM |
| Worker | Co-located with API, `PLAYWRIGHT_BROWSER_POOL_SIZE=2` |
| PostgreSQL | 1 CPU, 2 GB RAM, 20 GB disk |
| Redis | 256 MB RAM |
| Total | 2 CPUs, 3.25 GB RAM, 20 GB disk |

### Medium (10–50 products)

| Component | Spec |
|-----------|------|
| API server | 2 instances, 1 CPU each, 2 GB RAM each |
| Worker | 2 instances, 1 CPU each, 2 GB RAM each, `PLAYWRIGHT_BROWSER_POOL_SIZE=2` |
| PostgreSQL | 2 CPUs, 4 GB RAM, 100 GB SSD |
| Redis | 512 MB RAM |
| PgBouncer | 0.5 CPU, 256 MB RAM |
| Total | ~8 CPUs, ~12.75 GB RAM, 100 GB SSD |

### Large (50+ products)

| Component | Spec |
|-----------|------|
| API server | 3–5 instances, 2 CPUs each, 4 GB RAM each |
| Worker | 4–8 instances, 2 CPUs each, 4 GB RAM each, `PLAYWRIGHT_BROWSER_POOL_SIZE=4` |
| PostgreSQL primary | 4 CPUs, 16 GB RAM, 500 GB SSD |
| PostgreSQL read replica | 2 CPUs, 8 GB RAM |
| Redis | 2 GB RAM, persistence enabled |
| PgBouncer | 1 CPU, 512 MB RAM |
| Load balancer | Managed (ALB, Nginx, Caddy) |
| Total | 30–50 CPUs, 60–120 GB RAM, 500+ GB SSD |

### Throughput reference

| Configuration | Concurrent tests | Tests/hour |
|---------------|-----------------|------------|
| 1 worker, 2 browsers | 2 | ~120 (assuming 60s/test avg) |
| 2 workers, 2 browsers each | 4 | ~240 |
| 4 workers, 4 browsers each | 16 | ~960 |

For burst capacity (e.g. many PRs at once), use the Kubernetes HPA to scale workers up automatically when the Redis queue depth exceeds a threshold.
