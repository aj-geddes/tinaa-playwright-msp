# Authentication & API Keys

TINAA MSP uses API key authentication for all REST API and MCP server access. Enterprise deployments can additionally configure OAuth 2.1 for user-facing dashboard authentication.

---

## API key setup

### Generating a secure API key

TINAA uses a single shared API key (`TINAA_API_KEY`) for all API access in the default configuration. Generate a cryptographically secure value:

```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
# Example output: 3Kx8mN2vP7qL4rT6wB9cE1fH5jA0iD_y
```

Set this in your `.env` file:

```bash
TINAA_API_KEY=3Kx8mN2vP7qL4rT6wB9cE1fH5jA0iD_y
TINAA_API_KEY_REQUIRED=true
```

When `TINAA_API_KEY_REQUIRED=true`, all API requests without a valid key receive HTTP 401.

In development (`TINAA_ENV=development`), you can set `TINAA_API_KEY_REQUIRED=false` to skip authentication entirely.

---

## API key usage

### X-API-Key header (recommended)

```bash
curl -H "X-API-Key: your-api-key" http://localhost:8765/api/v1/products
```

### Authorization: Bearer header

```bash
curl -H "Authorization: Bearer your-api-key" http://localhost:8765/api/v1/products
```

Both formats are accepted. The `X-API-Key` header is recommended for simplicity and clarity.

### In .tinaa.yml and CI scripts

Store the API key as a secret in your CI/CD platform (GitHub Actions secrets, GitLab CI variables, etc.) and inject it as an environment variable:

```bash
# GitHub Actions
curl -H "X-API-Key: ${{ secrets.TINAA_API_KEY }}" \
  https://tinaa.yourcompany.com/api/v1/products
```

Never hard-code API keys in playbook YAML, configuration files, or source code.

---

## Key rotation

To rotate the API key without service interruption:

1. Generate a new key: `python -c "import secrets; print(secrets.token_urlsafe(32))"`.
2. Update the `TINAA_API_KEY` value in your `.env` or secrets manager.
3. Update the key in all CI/CD systems and integrations.
4. Restart the TINAA API server to pick up the new key.
5. Verify all integrations are using the new key before discarding the old value.

TINAA does not support simultaneous multiple API keys in the base configuration. If you need per-user or per-integration keys, use the multi-tenancy OAuth 2.1 configuration (see below).

---

## OAuth 2.1 setup (enterprise)

Enterprise and multi-tenant deployments can configure OAuth 2.1 for user-level authentication via an external identity provider (IdP). This enables:

- Per-user access with individual tokens.
- Role-based access control (admin, developer, viewer) per organisation.
- Audit logs tied to individual users.
- Token expiry and refresh without shared-key rotation.

### Supported OAuth 2.1 grant types

| Grant type | Use case |
|------------|---------|
| Authorization Code + PKCE | Dashboard users (browser-based) |
| Client Credentials | CI/CD systems and service accounts |

### Configuration

Set the following environment variables:

```bash
# OAuth provider settings
OAUTH_ISSUER=https://auth.yourcompany.com
OAUTH_AUDIENCE=tinaa-msp
OAUTH_JWKS_URI=https://auth.yourcompany.com/.well-known/jwks.json

# Client settings for the dashboard
OAUTH_CLIENT_ID=tinaa-dashboard
OAUTH_CLIENT_SECRET=your-dashboard-client-secret
OAUTH_REDIRECT_URI=https://tinaa.yourcompany.com/auth/callback
```

Supported IdPs:
- **Auth0** — configure an Auth0 application with callback URL set to your TINAA instance.
- **Okta** — configure an Okta OIDC application.
- **Keycloak** — configure a Keycloak realm and client.
- **GitHub OAuth** — for GitHub.com users via GitHub's OAuth app.

### Token validation

TINAA validates incoming JWTs against the JWKS endpoint of the configured issuer. Required JWT claims:

| Claim | Description |
|-------|-------------|
| `sub` | User identifier (string) |
| `aud` | Must include `tinaa-msp` (or the value of `OAUTH_AUDIENCE`) |
| `exp` | Token expiry (Unix timestamp) |
| `email` | User email address (for display and notifications) |
| `tinaa_role` | Optional: `admin`, `developer`, or `viewer`. Defaults to `viewer` if absent. |

---

## Managing user access

### Roles

| Role | Permissions |
|------|------------|
| `admin` | Full access: create/delete products, manage API keys, configure integrations, view all data |
| `developer` | Create/edit products and playbooks, trigger test runs, view metrics and alerts |
| `viewer` | Read-only access to products, test runs, metrics, and quality scores |

### Assigning roles

With shared API key authentication, all users have admin-level access. Role-based access requires OAuth 2.1.

In the OAuth 2.1 setup, assign the `tinaa_role` claim in your IdP's token claim mapping. For example, in Auth0 you would add a custom claim action:

```javascript
// Auth0 Action: Add TINAA role claim
exports.onExecutePostLogin = async (event, api) => {
  const namespace = 'https://tinaa.yourcompany.com';
  const roles = event.authorization?.roles || [];
  const tinaaRole = roles.includes('tinaa-admin') ? 'admin'
                  : roles.includes('tinaa-developer') ? 'developer'
                  : 'viewer';
  api.idToken.setCustomClaim(`${namespace}/tinaa_role`, tinaaRole);
  api.accessToken.setCustomClaim(`${namespace}/tinaa_role`, tinaaRole);
};
```

### Revoking access

- **Shared API key**: rotate the key (see Key rotation above).
- **OAuth 2.1**: revoke the user's session in your IdP or remove the user from the application.
