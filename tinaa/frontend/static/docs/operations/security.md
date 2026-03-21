# Security Hardening

This document covers hardening the TINAA MSP installation against threats. Apply all items appropriate for your deployment size and threat model.

---

## Network security

### TLS configuration

All production traffic must use TLS. Configure TLS at the reverse proxy (Caddy, Nginx, or cloud load balancer) rather than inside the application container.

**Caddy (automatic TLS via Let's Encrypt):**

```
tinaa.yourcompany.com {
    reverse_proxy tinaa-api:8765
    tls {
        protocols tls1.2 tls1.3
        ciphers TLS_ECDHE_ECDSA_WITH_AES_256_GCM_SHA384 TLS_ECDHE_RSA_WITH_AES_256_GCM_SHA384
    }
    header {
        Strict-Transport-Security "max-age=31536000; includeSubDomains; preload"
        X-Content-Type-Options "nosniff"
        X-Frame-Options "DENY"
        Referrer-Policy "strict-origin-when-cross-origin"
    }
}
```

### Firewall rules

| Port | Service | Allowed from |
|------|---------|-------------|
| 443 | HTTPS (reverse proxy) | Internet (0.0.0.0/0) |
| 80 | HTTP (redirect to 443) | Internet (0.0.0.0/0) |
| 8765 | TINAA API | Internal network only (not internet-facing) |
| 8080 | MCP server | Development machines only |
| 5432 | PostgreSQL | TINAA containers only |
| 6379 | Redis | TINAA containers only |

Never expose PostgreSQL or Redis directly to the internet.

### Internal network

Use a Docker network or Kubernetes namespace to isolate TINAA containers:

```yaml
# docker-compose.prod.yml
networks:
  tinaa-internal:
    driver: bridge
    ipam:
      config:
        - subnet: 172.20.0.0/16

services:
  tinaa-api:
    networks:
      - tinaa-internal
  postgres:
    networks:
      - tinaa-internal    # not exposed externally
  redis:
    networks:
      - tinaa-internal    # not exposed externally
```

---

## Authentication mechanisms

### API key security

- Use a minimum 32-character random key: `python -c "import secrets; print(secrets.token_urlsafe(32))"`.
- Rotate the key at least annually, and immediately upon suspected compromise.
- Never log the API key value — TINAA's middleware logs only the first 8 characters.
- Store the key in a secrets manager (AWS Secrets Manager, HashiCorp Vault, GCP Secret Manager) rather than in `.env` files on disk.

### GitHub webhook signature verification

Every incoming GitHub webhook is verified against the HMAC-SHA256 signature in the `X-Hub-Signature-256` header. This prevents spoofed webhook events.

```python
# tinaa/github/webhooks.py — signature verification
import hashlib
import hmac

def verify_github_signature(payload: bytes, signature: str, secret: str) -> bool:
    expected = "sha256=" + hmac.new(
        secret.encode(), payload, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)
```

Set a strong, unique `GITHUB_WEBHOOK_SECRET` (minimum 32 characters).

---

## Secret management

### Environment variable injection

In production, do not store secrets in `.env` files on disk. Instead, inject them at runtime:

**Docker Compose with Docker Secrets:**
```yaml
secrets:
  tinaa_api_key:
    external: true

services:
  tinaa-api:
    secrets:
      - tinaa_api_key
    environment:
      TINAA_API_KEY_FILE: /run/secrets/tinaa_api_key
```

**Kubernetes Secrets:**
```yaml
apiVersion: v1
kind: Secret
metadata:
  name: tinaa-secrets
type: Opaque
data:
  TINAA_API_KEY: <base64-encoded-value>
  DATABASE_URL: <base64-encoded-value>
  GITHUB_APP_PRIVATE_KEY: <base64-encoded-value>
```

**HashiCorp Vault:**
Use the Vault Agent injector or the Vault CSI provider to inject secrets as environment variables or files.

### GitHub App private key

The GitHub App RSA private key is a sensitive long-lived credential. Store it in a secrets manager and never commit it to source control. If the key is compromised, immediately:
1. Generate a new private key in the GitHub App settings.
2. Update the key in your secrets manager.
3. Restart TINAA to pick up the new key.
4. Delete the compromised key from GitHub App settings.

---

## CORS configuration

Restrict CORS to your actual dashboard origin:

```bash
TINAA_CORS_ORIGINS=https://tinaa.yourcompany.com
```

Do not use `*` (wildcard) origins in production — this allows any website to make authenticated API requests from a user's browser.

---

## Container security

### Non-root user

The production Docker image runs as a non-root user (UID 1000):

```dockerfile
# Dockerfile
RUN useradd --uid 1000 --gid 1000 --no-create-home tinaa
USER tinaa
```

### Read-only filesystem

```yaml
# docker-compose.prod.yml
services:
  tinaa-api:
    read_only: true
    tmpfs:
      - /tmp                    # writable for temp files
      - /app/screenshots        # writable for test screenshots
      - /app/logs               # writable if LOG_FILE is set
```

### Security options

```yaml
services:
  tinaa-api:
    security_opt:
      - no-new-privileges:true   # prevent privilege escalation via setuid
    cap_drop:
      - ALL                      # drop all Linux capabilities
    cap_add:
      - NET_BIND_SERVICE         # only if binding to ports < 1024
```

### Playwright sandbox

Chromium requires a sandbox to isolate browser processes. In Docker, use `--cap-add SYS_ADMIN` or the `--no-sandbox` Chromium flag (less preferred, but necessary in some environments):

```bash
PLAYWRIGHT_CHROMIUM_ARGS=--no-sandbox,--disable-setuid-sandbox
```

The production Docker Compose file includes the necessary seccomp profile for Chromium sandboxing.

---

## Audit logging

TINAA logs all write operations with the authenticated user, timestamp, and action. Audit logs are emitted at `INFO` level with a structured prefix:

```json
{
  "timestamp": "2026-03-21T10:30:00Z",
  "level": "INFO",
  "logger": "tinaa.audit",
  "event": "product.created",
  "actor": "api_key:3Kx8mN...",
  "resource_type": "product",
  "resource_id": "00000000-0000-0000-0000-000000000001",
  "org_id": "00000000-0000-0000-0000-000000000001",
  "ip": "192.168.1.10"
}
```

Audit events include: `product.created`, `product.deleted`, `playbook.executed`, `alert.acknowledged`, `alert.resolved`, `api_key.rotated`.

Ship audit logs to an immutable log store (CloudTrail, Splunk, etc.) and retain for at least 1 year for compliance.

---

## Security checklist

- [ ] TLS enabled on all public endpoints
- [ ] `TINAA_API_KEY` is >= 32 random characters
- [ ] `TINAA_API_KEY_REQUIRED=true` in production
- [ ] CORS origins restricted to known dashboard URL
- [ ] PostgreSQL and Redis not exposed on public network
- [ ] API key stored in secrets manager (not `.env` on disk)
- [ ] GitHub webhook secret set and signature verification enabled
- [ ] Container runs as non-root user
- [ ] Read-only filesystem with tmpfs mounts
- [ ] `no-new-privileges` security option set
- [ ] Audit logs shipped to immutable store
- [ ] TLS grade A or A+ (verify at ssl.hboateng.com or SSLLabs)
- [ ] Security headers set at reverse proxy (HSTS, X-Frame-Options, etc.)
- [ ] Playwright runs in sandboxed mode (or with explicit risk acknowledgement)
- [ ] Database password is >= 24 random characters
- [ ] Redis requires authentication (`requirepass` in redis.conf)
- [ ] Docker images built from pinned base image versions (no `latest`)
- [ ] Regular image vulnerability scanning (Trivy, Snyk, or equivalent)
