# Deployment

This document covers deploying TINAA MSP to production using Docker Compose, Kubernetes (Helm), and environment-specific configuration patterns.

---

## Docker Compose deployment (production)

### File structure

The repository includes multiple compose files:

| File | Purpose |
|------|---------|
| `docker-compose.yml` | Base development configuration |
| `docker-compose.dev.yml` | Development overrides (hot reload, exposed ports) |
| `docker-compose.prod.yml` | Production configuration with security hardening |
| `docker-compose.http.yml` | Add HTTP/TLS via Caddy reverse proxy |

### Production deployment steps

```bash
# 1. Clone on the production host
git clone https://github.com/your-org/tinaa-playwright-msp.git
cd tinaa-playwright-msp

# 2. Create and configure .env
cp .env.example .env
# Edit .env: set DATABASE_URL, REDIS_URL, TINAA_API_KEY, GITHUB_APP_* vars

# 3. Start services
docker compose -f docker-compose.prod.yml up -d

# 4. Run migrations
docker compose -f docker-compose.prod.yml exec tinaa-api alembic upgrade head

# 5. Install Playwright browsers inside the container
docker compose -f docker-compose.prod.yml exec tinaa-api playwright install chromium

# 6. Verify
curl -f http://localhost:8765/health && echo "TINAA is healthy"
```

### docker-compose.prod.yml highlights

Key differences from the development configuration:

```yaml
services:
  tinaa-api:
    restart: unless-stopped
    user: "1000:1000"           # non-root user
    read_only: true              # read-only filesystem
    tmpfs:
      - /tmp                     # writable tmp
      - /app/screenshots         # screenshot storage
    security_opt:
      - no-new-privileges:true   # prevent privilege escalation
    mem_limit: 2g
    cpus: "2.0"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8765/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 15s
    environment:
      TINAA_ENV: production
      TINAA_API_KEY_REQUIRED: "true"
      LOG_FORMAT: json
```

---

## Kubernetes deployment (Helm)

### Prerequisites

- Kubernetes 1.28+
- Helm 3.14+
- PostgreSQL accessible from the cluster (managed service or in-cluster)
- Redis accessible from the cluster

### Install via Helm

```bash
# Add the TINAA Helm repository (if published)
helm repo add tinaa https://helm.tinaa.example.com
helm repo update

# Install to the tinaa namespace
helm install tinaa tinaa/tinaa-msp \
  --namespace tinaa \
  --create-namespace \
  --set config.databaseUrl="postgresql+asyncpg://tinaa:pass@postgres:5432/tinaa" \
  --set config.redisUrl="redis://redis:6379/0" \
  --set secrets.apiKey="your-api-key" \
  --set secrets.githubAppId="123456" \
  --set replicaCount=2
```

### Helm values overview

```yaml
# values.yaml
replicaCount: 2

image:
  repository: your-registry/tinaa-msp
  tag: "2.0.0"
  pullPolicy: IfNotPresent

service:
  type: ClusterIP
  port: 8765

ingress:
  enabled: true
  className: nginx
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
  hosts:
    - host: tinaa.yourcompany.com
      paths:
        - path: /
          pathType: Prefix
  tls:
    - secretName: tinaa-tls
      hosts:
        - tinaa.yourcompany.com

resources:
  requests:
    cpu: 500m
    memory: 1Gi
  limits:
    cpu: 2000m
    memory: 4Gi

autoscaling:
  enabled: false   # see Scaling guide for HPA configuration

# Playwright browser pool
playwright:
  browserPoolSize: 2

# Database connection pooling
database:
  poolSize: 10
  maxOverflow: 20
```

---

## Environment-specific configurations

### Development

```bash
docker compose -f docker-compose.yml -f docker-compose.dev.yml up
```

Development configuration adds:
- `--reload` flag on Uvicorn for code hot-reload
- Exposed Redis port (6379) for local inspection
- `LOG_LEVEL=DEBUG` and `LOG_FORMAT=text`
- `TINAA_API_KEY_REQUIRED=false` for convenience

### Staging

Staging should mirror production as closely as possible. Differences:
- Lower resource limits (1 CPU, 1 GB RAM)
- Monitoring interval set to 15 minutes to reduce cost
- Alerts deliver to `#tinaa-staging` Slack channel, not on-call PagerDuty
- GitHub integration pointing to a staging environment

### Production

Production requirements:
- `TINAA_API_KEY_REQUIRED=true`
- `LOG_FORMAT=json` with log shipping to your aggregation platform
- TLS termination at the load balancer or reverse proxy
- Database backed by PostgreSQL with TimescaleDB and daily backups
- Redis with persistence enabled (`appendonly yes`)
- Resource limits enforced

---

## Rolling updates and zero-downtime deploys

### Docker Compose rolling update

```bash
# Pull new image
docker compose -f docker-compose.prod.yml pull tinaa-api

# Rolling restart: Compose stops and restarts one container at a time
# (single-container deployment — no true rolling, but Uvicorn restarts gracefully)
docker compose -f docker-compose.prod.yml up -d --no-deps tinaa-api

# Run migrations after the new container starts
docker compose -f docker-compose.prod.yml exec tinaa-api alembic upgrade head
```

For true zero-downtime, deploy behind a load balancer with at least 2 instances. Kubernetes deployments handle rolling updates natively via `RollingUpdate` strategy.

### Kubernetes rolling update

```bash
# Update the image tag in the deployment
kubectl set image deployment/tinaa-api \
  tinaa-api=your-registry/tinaa-msp:2.1.0 \
  -n tinaa

# Monitor rollout
kubectl rollout status deployment/tinaa-api -n tinaa

# Rollback if needed
kubectl rollout undo deployment/tinaa-api -n tinaa
```

Kubernetes rolls out new pods with the `RollingUpdate` strategy — new pods start and pass health checks before old pods are terminated, ensuring continuous availability.

---

## Health check and readiness probes

### Liveness probe

Checks whether the process is alive. If it fails, Kubernetes/Docker restarts the container.

```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8765
  initialDelaySeconds: 15
  periodSeconds: 30
  failureThreshold: 3
```

### Readiness probe

Checks whether the container is ready to receive traffic. If it fails, the container is removed from the load balancer pool.

```yaml
readinessProbe:
  httpGet:
    path: /health
    port: 8765
  initialDelaySeconds: 5
  periodSeconds: 10
  failureThreshold: 3
```

### Custom health check endpoint

`GET /health` returns:

```json
{
  "status": "healthy",
  "version": "2.0.0",
  "timestamp": "2026-03-21T10:00:00Z"
}
```

Status `"healthy"` indicates the API server is running. For deeper health checks that include database and Redis connectivity, use `GET /api/v1/health/full` if configured in your deployment.
