---
layout: page
title: "Deployment Guide"
description: "Deploy TINAA MSP with Docker Compose, Kubernetes, or manual installation"
---

# Deployment Guide

TINAA MSP v2.0 is a Python 3.11+ application packaged as a Docker image. This guide covers every supported deployment path from a single-node Docker Compose setup through a production Kubernetes cluster.

**Runtime requirements**

| Component | Minimum version |
|-----------|----------------|
| Python | 3.11 |
| PostgreSQL + TimescaleDB | 16 |
| Redis | 7 |
| Docker | 24.0 |
| Kubernetes | 1.28 |

---

## Docker Compose (recommended for getting started)

The fastest path to a running TINAA MSP instance. All services start with a single command.

### docker-compose.yml

```yaml
services:
  tinaa:
    build:
      context: .
      target: production
    image: tinaa-msp:latest
    ports:
      - "8765:8765"
    environment:
      - DATABASE_URL=postgresql+asyncpg://tinaa:tinaa@postgres:5432/tinaa
      - REDIS_URL=redis://redis:6379/0
      - GITHUB_APP_ID=${GITHUB_APP_ID}
      - GITHUB_PRIVATE_KEY=${GITHUB_PRIVATE_KEY}
      - GITHUB_WEBHOOK_SECRET=${GITHUB_WEBHOOK_SECRET}
      - TINAA_API_KEY=${TINAA_API_KEY}
      - TINAA_MODE=${TINAA_MODE:-api}
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8765/health"]
      interval: 30s
      timeout: 10s
      start_period: 20s
      retries: 3
    restart: unless-stopped

  postgres:
    image: timescale/timescaledb:latest-pg16
    environment:
      POSTGRES_USER: tinaa
      POSTGRES_PASSWORD: tinaa
      POSTGRES_DB: tinaa
    ports:
      - "5432:5432"
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U tinaa"]
      interval: 5s
      timeout: 5s
      retries: 5
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
```

### Environment variables

Create a `.env` file in the project root before starting:

```bash
# Required
TINAA_API_KEY=your-secret-api-key-here

# Optional — only needed for GitHub integration
GITHUB_APP_ID=123456
GITHUB_PRIVATE_KEY="-----BEGIN RSA PRIVATE KEY-----\n..."
GITHUB_WEBHOOK_SECRET=your-webhook-secret

# Mode: api (default) | mcp
TINAA_MODE=api
```

| Variable | Default | Description |
|----------|---------|-------------|
| `TINAA_API_KEY` | — | API key for authenticating REST requests. Leave empty to disable auth |
| `DATABASE_URL` | — | PostgreSQL connection string (`postgresql+asyncpg://...`) |
| `REDIS_URL` | — | Redis connection string (`redis://host:port/db`) |
| `GITHUB_APP_ID` | — | GitHub App ID for webhook integration |
| `GITHUB_PRIVATE_KEY` | — | PEM-encoded GitHub App private key |
| `GITHUB_WEBHOOK_SECRET` | — | HMAC secret for validating GitHub webhooks |
| `TINAA_MODE` | `api` | Server mode: `api` starts the REST server; `mcp` starts the MCP server |
| `TINAA_DEBUG` | `false` | Enable debug logging |
| `TINAA_CORS_ORIGINS` | `*` | Comma-separated list of allowed CORS origins |

### Starting the stack

```bash
# Clone and enter the repository
git clone https://github.com/aj-geddes/tinaa-playwright-msp.git
cd tinaa-playwright-msp

# Create your .env file
cp .env.example .env
# Edit .env with your values

# Build and start all services
docker compose up -d

# Check that all services are healthy
docker compose ps

# View TINAA logs
docker compose logs -f tinaa

# Verify the API is reachable
curl http://localhost:8765/health
```

### Persistent volumes

Both `postgres_data` and `redis_data` are named volumes. They persist across `docker compose down` / `up` cycles.

To completely reset all data:

```bash
docker compose down -v   # removes containers and volumes
```

### Health checks

Docker Compose waits for the health checks before starting dependent services:

- **postgres**: `pg_isready -U tinaa` (5 s interval, 5 retries)
- **redis**: `redis-cli ping` (5 s interval, 5 retries)
- **tinaa**: `curl -f http://localhost:8765/health` (30 s interval, 3 retries)

The `tinaa` service starts only after both `postgres` and `redis` are healthy.

---

## Docker Compose — Production

For internet-facing production deployments use the pre-built image with a reverse proxy for SSL termination.

### docker-compose.prod.yml

```yaml
services:
  tinaa:
    image: ghcr.io/aj-geddes/tinaa-playwright-msp:latest
    container_name: tinaa-msp
    ports:
      - "127.0.0.1:8765:8765"   # bind to loopback — reverse proxy handles public traffic
    environment:
      - DATABASE_URL=postgresql+asyncpg://tinaa:${POSTGRES_PASSWORD}@postgres:5432/tinaa
      - REDIS_URL=redis://:${REDIS_PASSWORD}@redis:6379/0
      - TINAA_API_KEY=${TINAA_API_KEY}
      - TINAA_MODE=api
      - TINAA_DEBUG=false
      - TINAA_CORS_ORIGINS=https://tinaa.yourdomain.com
    depends_on:
      postgres:
        condition: service_healthy
      redis:
        condition: service_healthy
    deploy:
      resources:
        limits:
          cpus: "2.0"
          memory: 2G
        reservations:
          cpus: "0.5"
          memory: 512M
    restart: unless-stopped
    logging:
      driver: json-file
      options:
        max-size: "50m"
        max-file: "5"

  postgres:
    image: timescale/timescaledb:latest-pg16
    environment:
      POSTGRES_USER: tinaa
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: tinaa
    volumes:
      - postgres_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U tinaa"]
      interval: 5s
      timeout: 5s
      retries: 5
    deploy:
      resources:
        limits:
          memory: 1G
    restart: unless-stopped

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "-a", "${REDIS_PASSWORD}", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5
    deploy:
      resources:
        limits:
          memory: 256M
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
```

### Nginx reverse proxy with SSL/TLS

```nginx
server {
    listen 443 ssl http2;
    server_name tinaa.yourdomain.com;

    ssl_certificate     /etc/letsencrypt/live/tinaa.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/tinaa.yourdomain.com/privkey.pem;
    ssl_protocols       TLSv1.2 TLSv1.3;
    ssl_ciphers         HIGH:!aNULL:!MD5;

    # Proxy WebSocket upgrades
    location /ws/ {
        proxy_pass http://127.0.0.1:8765;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_read_timeout 3600s;
    }

    location / {
        proxy_pass         http://127.0.0.1:8765;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
        client_max_body_size 50m;
    }
}

server {
    listen 80;
    server_name tinaa.yourdomain.com;
    return 301 https://$host$request_uri;
}
```

### Key differences from development

| Concern | Development | Production |
|---------|-------------|------------|
| Image | Built locally | `ghcr.io/aj-geddes/tinaa-playwright-msp:latest` |
| Port binding | `0.0.0.0:8765` | `127.0.0.1:8765` (loopback only) |
| Redis auth | None | Password via `REDIS_PASSWORD` |
| Resource limits | Unlimited | CPU 2 core / 2 GB RAM |
| Log rotation | Docker default | 50 MB, 5 files |
| CORS | `*` | Explicit domain list |

---

## Kubernetes Deployment

TINAA MSP ships with seven ready-to-apply Kubernetes manifests in the `k8s/` directory.

### Manifest overview

| File | Resource(s) | Description |
|------|-------------|-------------|
| `namespace.yaml` | `Namespace` | Dedicated `tinaa` namespace with labels |
| `configmap.yaml` | `ConfigMap` | Non-secret configuration values |
| `secret.yaml` | `Secret` | API keys and credentials |
| `postgres.yaml` | `PVC`, `Deployment`, `Service` | TimescaleDB 16 with persistent volume |
| `redis.yaml` | `PVC`, `Deployment`, `Service` | Redis 7 with AOF persistence |
| `deployment.yaml` | `Deployment`, `Service` | TINAA MSP application + init containers |
| `ingress.yaml` | `Ingress` | NGINX Ingress with TLS via cert-manager |

### namespace.yaml

```yaml
apiVersion: v1
kind: Namespace
metadata:
  name: tinaa
  labels:
    app.kubernetes.io/name: tinaa-msp
    app.kubernetes.io/part-of: tinaa
```

### configmap.yaml

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: tinaa-config
  namespace: tinaa
data:
  DATABASE_URL: "postgresql+asyncpg://tinaa:tinaa@tinaa-postgres:5432/tinaa"
  REDIS_URL: "redis://tinaa-redis:6379/0"
  TINAA_MODE: "api"
  TINAA_CORS_ORIGINS: "https://tinaa.yourdomain.com,http://localhost:3000"
  TINAA_DEBUG: "false"
```

All values are readable by any pod in the namespace. Move sensitive values (passwords, keys) to the Secret.

### secret.yaml

```yaml
apiVersion: v1
kind: Secret
metadata:
  name: tinaa-secret
  namespace: tinaa
type: Opaque
stringData:
  TINAA_API_KEY: "tinaa-prod-key-changeme"
  GITHUB_WEBHOOK_SECRET: ""
  GITHUB_APP_ID: ""
  GITHUB_PRIVATE_KEY: ""
```

Replace `stringData` values with your real secrets before applying. In production, use an external secrets manager (Vault, AWS Secrets Manager, Sealed Secrets) rather than committing this file.

### postgres.yaml

Deploys TimescaleDB 16 as a single-replica pod with a 5 Gi persistent volume.

```yaml
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: tinaa-postgres-pvc
  namespace: tinaa
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: local-path
  resources:
    requests:
      storage: 5Gi
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: tinaa-postgres
  namespace: tinaa
  labels:
    app: tinaa-postgres
spec:
  replicas: 1
  selector:
    matchLabels:
      app: tinaa-postgres
  template:
    metadata:
      labels:
        app: tinaa-postgres
    spec:
      containers:
        - name: postgres
          image: timescale/timescaledb:latest-pg16
          ports:
            - containerPort: 5432
          env:
            - name: POSTGRES_USER
              value: "tinaa"
            - name: POSTGRES_PASSWORD
              value: "tinaa"
            - name: POSTGRES_DB
              value: "tinaa"
          volumeMounts:
            - name: postgres-data
              mountPath: /var/lib/postgresql/data
          readinessProbe:
            exec:
              command: ["pg_isready", "-U", "tinaa"]
            initialDelaySeconds: 5
            periodSeconds: 5
          livenessProbe:
            exec:
              command: ["pg_isready", "-U", "tinaa"]
            initialDelaySeconds: 15
            periodSeconds: 10
          resources:
            requests:
              memory: "256Mi"
              cpu: "100m"
            limits:
              memory: "512Mi"
              cpu: "500m"
      volumes:
        - name: postgres-data
          persistentVolumeClaim:
            claimName: tinaa-postgres-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: tinaa-postgres
  namespace: tinaa
spec:
  selector:
    app: tinaa-postgres
  ports:
    - port: 5432
      targetPort: 5432
```

Change `storageClassName: local-path` to your cluster's storage class (e.g. `standard`, `gp2`, `premium-rwo`).

### redis.yaml

Deploys Redis 7 with AOF persistence enabled and a 2 Gi volume.

```yaml
---
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: tinaa-redis-pvc
  namespace: tinaa
spec:
  accessModes:
    - ReadWriteOnce
  storageClassName: local-path
  resources:
    requests:
      storage: 2Gi
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: tinaa-redis
  namespace: tinaa
  labels:
    app: tinaa-redis
spec:
  replicas: 1
  selector:
    matchLabels:
      app: tinaa-redis
  template:
    metadata:
      labels:
        app: tinaa-redis
    spec:
      containers:
        - name: redis
          image: redis:7-alpine
          ports:
            - containerPort: 6379
          command: ["redis-server", "--appendonly", "yes"]
          volumeMounts:
            - name: redis-data
              mountPath: /data
          readinessProbe:
            exec:
              command: ["redis-cli", "ping"]
            initialDelaySeconds: 5
            periodSeconds: 5
          livenessProbe:
            exec:
              command: ["redis-cli", "ping"]
            initialDelaySeconds: 15
            periodSeconds: 10
          resources:
            requests:
              memory: "64Mi"
              cpu: "50m"
            limits:
              memory: "128Mi"
              cpu: "200m"
      volumes:
        - name: redis-data
          persistentVolumeClaim:
            claimName: tinaa-redis-pvc
---
apiVersion: v1
kind: Service
metadata:
  name: tinaa-redis
  namespace: tinaa
spec:
  selector:
    app: tinaa-redis
  ports:
    - port: 6379
      targetPort: 6379
```

### deployment.yaml

The main TINAA MSP application. Includes two init containers that run before the application starts:

1. **wait-for-postgres** — polls until PostgreSQL accepts connections
2. **run-migrations** — runs `alembic upgrade head` to apply database migrations

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: tinaa-msp
  namespace: tinaa
  labels:
    app: tinaa-msp
spec:
  replicas: 1
  selector:
    matchLabels:
      app: tinaa-msp
  template:
    metadata:
      labels:
        app: tinaa-msp
    spec:
      containers:
        - name: tinaa
          image: ghcr.io/aj-geddes/tinaa-playwright-msp:latest
          imagePullPolicy: Always
          ports:
            - containerPort: 8765
              name: http
          envFrom:
            - configMapRef:
                name: tinaa-config
            - secretRef:
                name: tinaa-secret
          readinessProbe:
            httpGet:
              path: /health
              port: 8765
            initialDelaySeconds: 10
            periodSeconds: 10
          livenessProbe:
            httpGet:
              path: /health
              port: 8765
            initialDelaySeconds: 30
            periodSeconds: 30
          resources:
            requests:
              memory: "512Mi"
              cpu: "200m"
            limits:
              memory: "1Gi"
              cpu: "1000m"
      initContainers:
        - name: wait-for-postgres
          image: busybox:1.36
          command:
            - sh
            - -c
            - |
              echo "Waiting for PostgreSQL..."
              until nc -z tinaa-postgres 5432; do
                echo "PostgreSQL not ready, sleeping..."
                sleep 2
              done
              echo "PostgreSQL is ready!"
        - name: run-migrations
          image: ghcr.io/aj-geddes/tinaa-playwright-msp:latest
          imagePullPolicy: Always
          command: ["python", "-m", "alembic", "upgrade", "head"]
          envFrom:
            - configMapRef:
                name: tinaa-config
            - secretRef:
                name: tinaa-secret
---
apiVersion: v1
kind: Service
metadata:
  name: tinaa-msp
  namespace: tinaa
spec:
  selector:
    app: tinaa-msp
  ports:
    - port: 8765
      targetPort: 8765
      name: http
```

**Resource requests/limits**

| Container | CPU request | CPU limit | Memory request | Memory limit |
|-----------|------------|-----------|----------------|--------------|
| tinaa | 200 m | 1000 m | 512 Mi | 1 Gi |
| postgres | 100 m | 500 m | 256 Mi | 512 Mi |
| redis | 50 m | 200 m | 64 Mi | 128 Mi |

### ingress.yaml

NGINX Ingress with TLS terminated by cert-manager.

```yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: tinaa-msp
  namespace: tinaa
  annotations:
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/proxy-read-timeout: "3600"
    nginx.ingress.kubernetes.io/proxy-send-timeout: "3600"
    nginx.ingress.kubernetes.io/proxy-body-size: "50m"
spec:
  ingressClassName: nginx
  tls:
    - hosts:
        - tinaa.yourdomain.com
      secretName: tinaa-tls
  rules:
    - host: tinaa.yourdomain.com
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: tinaa-msp
                port:
                  number: 8765
```

Replace `tinaa.yourdomain.com` with your actual domain and set the correct `cert-manager.io/cluster-issuer` for your environment.

### Applying all manifests

```bash
# 1. Create namespace first
kubectl apply -f k8s/namespace.yaml

# 2. Apply configuration and secrets
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secret.yaml

# 3. Deploy databases
kubectl apply -f k8s/postgres.yaml
kubectl apply -f k8s/redis.yaml

# 4. Wait for databases to become ready
kubectl wait --for=condition=ready pod -l app=tinaa-postgres -n tinaa --timeout=60s
kubectl wait --for=condition=ready pod -l app=tinaa-redis -n tinaa --timeout=60s

# 5. Deploy the application
kubectl apply -f k8s/deployment.yaml

# 6. Apply ingress
kubectl apply -f k8s/ingress.yaml

# 7. Verify everything is running
kubectl get all -n tinaa

# 8. Check TINAA pod logs
kubectl logs -f deployment/tinaa-msp -n tinaa

# 9. Test the health endpoint (from within the cluster)
kubectl exec -n tinaa deployment/tinaa-msp -- curl -s http://localhost:8765/health
```

Apply the entire directory in one command if you prefer:

```bash
kubectl apply -f k8s/
```

### Horizontal Pod Autoscaler

Scale TINAA MSP automatically based on CPU utilisation:

```yaml
apiVersion: autoscaling/v2
kind: HorizontalPodAutoscaler
metadata:
  name: tinaa-msp-hpa
  namespace: tinaa
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: tinaa-msp
  minReplicas: 1
  maxReplicas: 5
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

Apply with:

```bash
kubectl apply -f - <<'EOF'
# paste the HPA manifest above
EOF
```

---

## Pre-built Docker image

TINAA MSP publishes a ready-to-run image to GitHub Container Registry on every release.

```
ghcr.io/aj-geddes/tinaa-playwright-msp:latest
```

### Running with docker run

```bash
# Minimal: SQLite (for evaluation only — not for production)
docker run -d \
  --name tinaa \
  -p 8765:8765 \
  -e TINAA_API_KEY=my-api-key \
  ghcr.io/aj-geddes/tinaa-playwright-msp:latest

# Full: with external PostgreSQL and Redis
docker run -d \
  --name tinaa \
  -p 8765:8765 \
  -e DATABASE_URL="postgresql+asyncpg://tinaa:password@host.docker.internal:5432/tinaa" \
  -e REDIS_URL="redis://host.docker.internal:6379/0" \
  -e TINAA_API_KEY=my-api-key \
  -v "$(pwd)/logs:/app/logs" \
  ghcr.io/aj-geddes/tinaa-playwright-msp:latest

# Verify
curl http://localhost:8765/health
```

### Available tags

| Tag | Description |
|-----|-------------|
| `latest` | Most recent release |
| `2.0.0` | Specific version |
| `main` | Built from the main branch (development) |

---

## Manual Installation

For bare-metal or VM deployments without Docker.

### Prerequisites

- Python 3.11+
- PostgreSQL 16 with TimescaleDB extension
- Redis 7
- Chromium (installed by Playwright)

### Steps

```bash
# 1. Clone the repository
git clone https://github.com/aj-geddes/tinaa-playwright-msp.git
cd tinaa-playwright-msp

# 2. Create and activate a virtual environment
python3.11 -m venv .venv
source .venv/bin/activate

# 3. Install dependencies
pip install -e ".[all]"
# or: pip install -r requirements.txt

# 4. Install Playwright browsers
playwright install chromium
playwright install-deps chromium

# 5. Set environment variables
export DATABASE_URL="postgresql+asyncpg://tinaa:password@localhost:5432/tinaa"
export REDIS_URL="redis://localhost:6379/0"
export TINAA_API_KEY="your-api-key"

# 6. Run database migrations
python -m alembic upgrade head

# 7. Start the server
uvicorn tinaa.api.app:app --host 0.0.0.0 --port 8765 --workers 2
```

For production, use a process supervisor such as systemd or supervisord.

**systemd unit example**

```ini
[Unit]
Description=TINAA MSP API Server
After=network.target postgresql.service redis.service

[Service]
Type=simple
User=tinaa
WorkingDirectory=/opt/tinaa-msp
EnvironmentFile=/opt/tinaa-msp/.env
ExecStart=/opt/tinaa-msp/.venv/bin/uvicorn tinaa.api.app:app \
          --host 0.0.0.0 --port 8765 --workers 2
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

---

## Database Setup

### PostgreSQL with TimescaleDB

TINAA MSP requires TimescaleDB for efficient time-series storage of metrics data.

**Install TimescaleDB on Ubuntu 24.04**

```bash
# Add TimescaleDB repository
curl -s https://packagecloud.io/install/repositories/timescale/timescaledb/script.deb.sh | sudo bash

# Install
sudo apt-get install -y timescaledb-2-postgresql-16

# Run the tuning wizard
sudo timescaledb-tune

# Restart PostgreSQL
sudo systemctl restart postgresql

# Connect and create the database
psql -U postgres -c "CREATE USER tinaa WITH PASSWORD 'your-password';"
psql -U postgres -c "CREATE DATABASE tinaa OWNER tinaa;"
psql -U postgres -d tinaa -c "CREATE EXTENSION IF NOT EXISTS timescaledb;"
```

### Alembic migrations

TINAA MSP manages its schema through Alembic migrations. The `run-migrations` init container handles this automatically in Docker/Kubernetes. For manual deployments:

```bash
# Apply all pending migrations
python -m alembic upgrade head

# Check current revision
python -m alembic current

# View migration history
python -m alembic history

# Roll back one step
python -m alembic downgrade -1
```

Migration files are in `alembic/versions/`. Never delete or modify them manually.

---

## Production Checklist

Before taking TINAA MSP to production, verify the following:

### Security

- [ ] `TINAA_API_KEY` is set to a strong random value (min 32 characters)
- [ ] Database password is not the default `tinaa`
- [ ] `secret.yaml` or `.env` is not committed to version control
- [ ] TLS/SSL is terminated at the load balancer or reverse proxy
- [ ] `TINAA_CORS_ORIGINS` is set to your specific domain(s), not `*`
- [ ] GitHub webhook secret is configured if using the integration

### Database

- [ ] Daily automated backups are enabled
  ```bash
  # pg_dump backup script example
  pg_dump -U tinaa -h localhost tinaa | gzip > /backups/tinaa-$(date +%Y%m%d).sql.gz
  ```
- [ ] Backup restore has been tested
- [ ] TimescaleDB `pg_isready` health check is wired up
- [ ] Data retention policy is set on hypertables (TimescaleDB)

### Redis

- [ ] AOF persistence is enabled (`--appendonly yes`)
- [ ] `maxmemory` and `maxmemory-policy` are configured
- [ ] Redis password is set in production
- [ ] Persistence volume is on reliable storage

### Application

- [ ] `TINAA_DEBUG=false` in production
- [ ] Liveness and readiness probes are configured
- [ ] Log rotation is configured
- [ ] Structured JSON logging is enabled for log aggregation
- [ ] Sentry or equivalent error tracking is configured

### Infrastructure

- [ ] Horizontal scaling tested under load
- [ ] Resource limits prevent OOM kills
- [ ] Alerting on pod restarts and health check failures
- [ ] Metrics exported to Prometheus (optional — scrape `/metrics`)

### Operational

- [ ] Runbook documented for common failure modes
- [ ] On-call rotation is aware of deployment
- [ ] Rollback procedure tested: `kubectl rollout undo deployment/tinaa-msp -n tinaa`
