# Multi-Tenancy

TINAA MSP supports multiple teams sharing a single installation through an **organisation** model. Each organisation's products, playbooks, metrics, and alerts are isolated from other organisations.

---

## Organisation model

The data hierarchy is:

```
TINAA Instance
  └── Organisation (one per team / business unit)
        ├── Products (one per application)
        │     ├── Environments
        │     └── Endpoints
        ├── Playbooks
        ├── Test Runs
        ├── Metrics
        └── Alerts
```

Each organisation has:
- A unique `id` (UUID).
- A `name` and `slug` for display and API paths.
- A set of members with assigned roles.
- Its own API key (when using per-org key mode) or shared access via OAuth 2.1 roles.

The default installation creates a single organisation with ID `00000000-0000-0000-0000-000000000001`. All products created via the basic API are associated with this organisation.

---

## Creating organisations

### Via admin API

Organisation management requires admin-level access.

```bash
# Create a new organisation
POST /api/v1/admin/organisations
{
  "name": "Platform Team",
  "slug": "platform-team"
}

# Response:
{
  "id": "11111111-1111-1111-1111-111111111111",
  "name": "Platform Team",
  "slug": "platform-team",
  "created_at": "2026-03-21T10:00:00Z"
}
```

### Via dashboard

Admins can create organisations from **Settings → Organisations → New Organisation**. After creation, products can be assigned to the organisation when created.

---

## Isolating products between teams

Every product belongs to exactly one organisation. Products are not visible to members of other organisations (unless cross-org visibility is explicitly enabled).

When calling the product API with multi-tenancy enabled, the organisation context is resolved from the authenticated user's token or API key:

```bash
# List only the products in the authenticated user's organisation
GET /api/v1/products
X-API-Key: team-alpha-api-key
```

Cross-organisation product listing is available only to `admin`-role users via:

```bash
GET /api/v1/admin/products?org_id=all
```

---

## Role-based access

TINAA MSP defines three roles, assigned per organisation membership:

### `admin`

- Create and delete organisations.
- Manage all products, playbooks, and environments within the organisation.
- Issue and revoke API keys.
- Configure GitHub integration and alert channels.
- View and manage all test runs and metrics.
- Manage user memberships and roles.

### `developer`

- Create, edit, and delete products, environments, endpoints, and playbooks.
- Trigger test runs (manual and on demand).
- View all metrics, test results, and quality scores.
- Configure their own notification preferences.
- Cannot manage API keys, user memberships, or GitHub App settings.

### `viewer`

- Read-only access to products, test runs, quality scores, and metrics.
- Can acknowledge alerts.
- Cannot create or modify any resources.
- Useful for stakeholders, QA managers, or external auditors.

### Role assignment table

| Action | admin | developer | viewer |
|--------|-------|-----------|--------|
| Create / delete products | Yes | Yes | No |
| Edit environments and endpoints | Yes | Yes | No |
| Create / edit playbooks | Yes | Yes | No |
| Trigger test runs | Yes | Yes | No |
| View test results and metrics | Yes | Yes | Yes |
| Acknowledge / resolve alerts | Yes | Yes | Yes |
| Configure alert channels | Yes | No | No |
| Manage API keys | Yes | No | No |
| Manage user roles | Yes | No | No |
| Configure GitHub integration | Yes | No | No |
| Create / delete organisations | Yes | No | No |

---

## Managing user memberships

### Adding a member

```bash
POST /api/v1/admin/organisations/{org_id}/members
{
  "user_email": "alice@yourcompany.com",
  "role": "developer"
}
```

If OAuth 2.1 is configured, TINAA looks up the user by email from the IdP. Otherwise, a user record is created with a generated API key.

### Updating a role

```bash
PATCH /api/v1/admin/organisations/{org_id}/members/{user_id}
{
  "role": "admin"
}
```

### Removing a member

```bash
DELETE /api/v1/admin/organisations/{org_id}/members/{user_id}
```

The user immediately loses access to all resources in that organisation.

---

## Data isolation guarantees

TINAA enforces organisation isolation at the database query level. All repository queries filter by `organization_id`:

- Products: `WHERE organization_id = $org_id`
- Playbooks: filtered through the product's `organization_id`
- Test runs, metrics, alerts: filtered through the product's `organization_id`

SQL-level row filtering ensures that even if a developer's code has a bug, cross-organisation data leakage is prevented at the query layer.

Audit logs record the `organization_id`, `user_id`, and action for every write operation.
