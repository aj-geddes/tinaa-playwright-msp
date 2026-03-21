# GitHub APIs for Deployment-Aware Testing Platforms: Deep Research

This document captures comprehensive research on the GitHub APIs, webhooks, and architecture patterns that enable a testing platform to discover deployed endpoints and product URLs, run tests against them, and report results back into the GitHub developer workflow.

---

## Table of Contents

1. [GitHub Deployments API](#1-github-deployments-api)
2. [GitHub Environments API](#2-github-environments-api)
3. [GitHub Webhooks for Deployment Events](#3-github-webhooks-for-deployment-events)
4. [GitHub Apps Architecture](#4-github-apps-architecture)
5. [GitHub Checks API](#5-github-checks-api)
6. [GitHub Actions Integration Patterns](#6-github-actions-integration-patterns)
7. [End-to-End Integration Architecture](#7-end-to-end-integration-architecture)

---

## 1. GitHub Deployments API

The Deployments API is the core mechanism for tracking where code is deployed and at what URL. GitHub describes it as enabling "developers and organizations to build loosely coupled tooling around deployments."

### 1.1 Core Concepts

A **Deployment** represents a request to deploy a specific ref (branch, tag, or SHA). A **Deployment Status** represents the state of that deployment (queued, pending, in_progress, success, failure, error, inactive). The crucial field is `environment_url` on the Deployment Status -- this carries the actual URL where the deployed code can be accessed.

The flow is:
1. A tool creates a Deployment via the API
2. GitHub dispatches a `deployment` webhook event
3. Services (e.g., Vercel, Netlify, a custom deployer) listen and perform the actual deployment
4. Services update the Deployment Status with the result and the `environment_url`
5. GitHub dispatches a `deployment_status` webhook event
6. Testing platforms listen for `deployment_status` with `state: "success"` and extract the `environment_url`

### 1.2 Endpoints

#### List Deployments

```
GET /repos/{owner}/{repo}/deployments
```

**Query Parameters:**
| Parameter | Type | Description |
|-----------|------|-------------|
| `sha` | string | Filter by commit SHA |
| `ref` | string | Filter by branch, tag, or SHA |
| `task` | string | Filter by task name (default: "deploy") |
| `environment` | string | Filter by environment name (e.g., "production", "staging", "preview") |
| `per_page` | integer | Results per page (max 100, default 30) |
| `page` | integer | Page number |

**Example Request:**
```bash
curl -H "Authorization: Bearer $TOKEN" \
     -H "Accept: application/vnd.github+json" \
     "https://api.github.com/repos/octocat/hello-world/deployments?environment=preview&ref=feature-branch"
```

#### Create a Deployment

```
POST /repos/{owner}/{repo}/deployments
```

**Request Body:**
```json
{
  "ref": "feature-branch",
  "task": "deploy",
  "auto_merge": false,
  "required_contexts": [],
  "payload": {
    "deploy_type": "preview",
    "pr_number": 42
  },
  "environment": "preview",
  "description": "Preview deployment for PR #42",
  "transient_environment": true,
  "production_environment": false
}
```

| Field | Required | Description |
|-------|----------|-------------|
| `ref` | Yes | Branch, tag, or SHA to deploy |
| `task` | No | Task to execute (default: "deploy") |
| `auto_merge` | No | Auto-merge default branch into ref (default: true) |
| `required_contexts` | No | Status contexts that must pass before deployment |
| `payload` | No | Arbitrary JSON data about the deployment |
| `environment` | No | Target environment name (default: "production") |
| `description` | No | Short description |
| `transient_environment` | No | True if environment is temporary (e.g., PR preview) |
| `production_environment` | No | True if environment is user-facing production |

**Response:** 201 Created, 202 (auto-merge), 409 (conflict), 422 (validation failed)

#### Get a Deployment

```
GET /repos/{owner}/{repo}/deployments/{deployment_id}
```

#### Delete a Deployment

```
DELETE /repos/{owner}/{repo}/deployments/{deployment_id}
```

Only works if the deployment is `inactive`. If a repo has a single deployment, that deployment can be deleted regardless of state.

### 1.3 Deployment Object Schema

```json
{
  "url": "https://api.github.com/repos/octocat/example/deployments/1",
  "id": 1,
  "node_id": "MDEwOkRlcGxveW1lbnQx",
  "sha": "a]84d88e7554fc1fa21bcbc4efae3c782a70d2b9d",
  "ref": "topic-branch",
  "task": "deploy",
  "payload": {},
  "original_environment": "staging",
  "environment": "production",
  "description": "Deploy request from GitHub Actions",
  "creator": {
    "login": "octocat",
    "id": 1,
    "type": "User"
  },
  "created_at": "2012-07-20T01:19:13Z",
  "updated_at": "2012-07-20T01:19:13Z",
  "statuses_url": "https://api.github.com/repos/octocat/example/deployments/1/statuses",
  "repository_url": "https://api.github.com/repos/octocat/example",
  "transient_environment": false,
  "production_environment": true,
  "performed_via_github_app": null
}
```

### 1.4 Deployment Statuses API

This is where the actual deployed URL lives.

#### Create a Deployment Status

```
POST /repos/{owner}/{repo}/deployments/{deployment_id}/statuses
```

**Request Body:**
```json
{
  "state": "success",
  "environment": "preview",
  "environment_url": "https://pr-42--my-app.vercel.app",
  "log_url": "https://github.com/octocat/example/actions/runs/123456",
  "description": "Deployment finished successfully",
  "auto_inactive": true
}
```

| Field | Required | Description |
|-------|----------|-------------|
| `state` | Yes | `error`, `failure`, `inactive`, `in_progress`, `queued`, `pending`, `success` |
| `environment` | No | Environment name (production, staging, qa) |
| `environment_url` | No | **The URL for accessing the deployed environment** |
| `log_url` | No | Full URL of the deployment's output/logs |
| `target_url` | No | Deprecated -- use `log_url` instead |
| `description` | No | Short description (max 140 chars) |
| `auto_inactive` | No | If true, prior non-transient, non-production deployments with the same environment become `inactive` |

#### List Deployment Statuses

```
GET /repos/{owner}/{repo}/deployments/{deployment_id}/statuses
```

#### Get a Deployment Status

```
GET /repos/{owner}/{repo}/deployments/{deployment_id}/statuses/{status_id}
```

#### Deployment Status Response Schema

```json
{
  "id": 1,
  "state": "success",
  "description": "Deployment finished successfully.",
  "environment": "production",
  "environment_url": "https://my-app.example.com",
  "log_url": "https://example.com/deployments/1/output",
  "target_url": "https://example.com/deployments/1/output",
  "deployment_url": "https://api.github.com/repos/octocat/example/deployments/1",
  "repository_url": "https://api.github.com/repos/octocat/example",
  "created_at": "2012-07-20T01:19:13Z",
  "updated_at": "2012-07-20T01:19:13Z",
  "creator": { "login": "octocat", "id": 1 },
  "performed_via_github_app": null
}
```

### 1.5 How Platforms Like Vercel/Netlify Create Deployments

**Vercel's Pattern:**
- Vercel registers as a GitHub App with `deployments:write` permission
- When a push or PR event occurs, Vercel creates a Deployment via the API with `environment: "Preview"` and `transient_environment: true`
- Vercel builds and deploys the application
- Vercel posts a Deployment Status with `state: "success"` and `environment_url` set to the unique preview URL (e.g., `https://my-app-git-feature-branch.vercel.app`)
- Each preview gets both a branch-specific URL and a commit-specific URL

**Netlify's Pattern:**
- Netlify similarly creates deployments via the GitHub Deployments API
- Preview URLs follow a predictable pattern: `https://deploy-preview-{PR_NUMBER}--{SITE_NAME}.netlify.app`
- Netlify posts status updates to the PR and adds comments with the Deploy Preview link
- Netlify also posts a Deployment Status with the `environment_url` set to the preview URL

### 1.6 Authentication Requirements

- **OAuth/PAT:** Requires `repo` or `repo_deployment` scope. The `repo_deployment` scope provides access to deployments without granting access to repository code.
- **GitHub App:** Requires `deployments:read` (for GET) or `deployments:write` (for POST/DELETE) repository permission.

---

## 2. GitHub Environments API

Environments provide a higher-level abstraction over deployments. They define named targets (production, staging, preview) with protection rules, secrets, and variables.

### 2.1 Endpoints

#### List Environments

```
GET /repos/{owner}/{repo}/environments
```

#### Get an Environment

```
GET /repos/{owner}/{repo}/environments/{environment_name}
```

#### Create or Update an Environment

```
PUT /repos/{owner}/{repo}/environments/{environment_name}
```

**Request Body:**
```json
{
  "wait_timer": 5,
  "prevent_self_review": false,
  "reviewers": [
    { "type": "User", "id": 1 },
    { "type": "Team", "id": 1 }
  ],
  "deployment_branch_policy": {
    "protected_branches": false,
    "custom_branch_policies": true
  }
}
```

#### Delete an Environment

```
DELETE /repos/{owner}/{repo}/environments/{environment_name}
```

### 2.2 Environment Object Schema

```json
{
  "id": 56780428,
  "node_id": "MDExOkVudmlyb25tZW50NTY3ODA0Mjg=",
  "name": "staging",
  "url": "https://api.github.com/repos/octocat/example/environments/staging",
  "html_url": "https://github.com/octocat/example/deployments/activity_log?environment=staging",
  "created_at": "2020-11-23T22:00:40Z",
  "updated_at": "2020-11-23T22:00:40Z",
  "protection_rules": [
    {
      "id": 3736,
      "type": "wait_timer",
      "wait_timer": 30
    },
    {
      "id": 3755,
      "type": "required_reviewers",
      "reviewers": [
        {
          "type": "User",
          "reviewer": { "login": "octocat", "id": 1 }
        },
        {
          "type": "Team",
          "reviewer": { "name": "deploy-team", "id": 1 }
        }
      ]
    }
  ],
  "deployment_branch_policy": {
    "protected_branches": false,
    "custom_branch_policies": true
  }
}
```

### 2.3 Protection Rules

| Rule Type | Description |
|-----------|-------------|
| **Wait Timer** | Delays deployment job execution by 0-43,200 minutes (up to 30 days) |
| **Required Reviewers** | Up to 6 users or teams must approve; only one approval needed to proceed |
| **Self-Review Prevention** | Prevents the person who triggered the workflow from approving it |
| **Administrator Bypass** | By default admins can bypass; can be disabled |
| **Custom Deployment Protection Rules** | GitHub Apps can provide custom protection logic |
| **Deployment Branch Policies** | Restrict which branches/tags can deploy (protected branches only, or custom patterns) |

### 2.4 Environment Secrets and Variables

**Secrets Endpoints:**
```
GET  /repos/{owner}/{repo}/environments/{environment_name}/secrets
GET  /repos/{owner}/{repo}/environments/{environment_name}/secrets/{secret_name}
PUT  /repos/{owner}/{repo}/environments/{environment_name}/secrets/{secret_name}
DELETE /repos/{owner}/{repo}/environments/{environment_name}/secrets/{secret_name}
```

**Variables Endpoints:**
```
GET    /repos/{owner}/{repo}/environments/{environment_name}/variables
GET    /repos/{owner}/{repo}/environments/{environment_name}/variables/{name}
POST   /repos/{owner}/{repo}/environments/{environment_name}/variables
PATCH  /repos/{owner}/{repo}/environments/{environment_name}/variables/{name}
DELETE /repos/{owner}/{repo}/environments/{environment_name}/variables/{name}
```

Requires `environments:read` (GET) or `environments:write` (PUT/POST/PATCH/DELETE) permission on the GitHub App.

### 2.5 Discovering Environment URLs

Environment URLs are **not stored on the Environment object itself**. Instead, environment URLs are carried by Deployment Statuses. To discover the current URL for an environment:

1. List deployments filtered by environment name: `GET /repos/{owner}/{repo}/deployments?environment=staging`
2. Get the latest deployment status for the most recent deployment: `GET /repos/{owner}/{repo}/deployments/{id}/statuses`
3. Extract the `environment_url` field from the latest status with `state: "success"`

This is the programmatic way a testing platform discovers "where is staging right now?"

### 2.6 Using Environments in GitHub Actions

```yaml
jobs:
  deploy:
    runs-on: ubuntu-latest
    environment:
      name: staging
      url: ${{ steps.deploy.outputs.url }}
    steps:
      - id: deploy
        run: |
          DEPLOY_URL=$(deploy-my-app.sh)
          echo "url=$DEPLOY_URL" >> "$GITHUB_OUTPUT"
```

When this job runs, GitHub Actions automatically creates a Deployment object for the "staging" environment and posts a Deployment Status with the `environment_url` set to the value of the `url` field.

Setting `deployment: false` on the environment reference allows accessing environment secrets/variables without creating a deployment object -- useful for CI/testing jobs that need credentials but are not deploying.

---

## 3. GitHub Webhooks for Deployment Events

### 3.1 `deployment` Event

**Fires when:** A new deployment is created (via API or GitHub Actions).

**Availability:** Repository, Organization, GitHub App

**Required Permission:** `deployments:read` (minimum)

**Payload Structure:**
```json
{
  "action": "created",
  "deployment": {
    "url": "https://api.github.com/repos/octocat/example/deployments/1",
    "id": 1,
    "node_id": "MDEwOkRlcGxveW1lbnQx",
    "sha": "a]84d88e7554fc1fa21bcbc4efae3c782a70d2b9d",
    "ref": "main",
    "task": "deploy",
    "payload": {},
    "environment": "production",
    "description": "Deploy from main",
    "creator": {
      "login": "octocat",
      "id": 1
    },
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:30:00Z",
    "statuses_url": "https://api.github.com/repos/octocat/example/deployments/1/statuses",
    "repository_url": "https://api.github.com/repos/octocat/example",
    "transient_environment": false,
    "production_environment": true
  },
  "workflow": null,
  "workflow_run": null,
  "repository": { "id": 1, "full_name": "octocat/example" },
  "sender": { "login": "octocat", "id": 1 },
  "installation": { "id": 12345 }
}
```

**Key Use:** A deployer service listens for this event to know "someone requested a deployment -- go do it."

### 3.2 `deployment_status` Event

**Fires when:** A new deployment status is created. **Does NOT fire for `inactive` state.**

**Availability:** Repository, Organization, GitHub App

**Required Permission:** `deployments:read` (minimum)

**Payload Structure:**
```json
{
  "action": "created",
  "deployment_status": {
    "url": "https://api.github.com/repos/octocat/example/deployments/1/statuses/1",
    "id": 1,
    "state": "success",
    "description": "Deployment finished successfully",
    "environment": "preview",
    "environment_url": "https://pr-42--my-app.vercel.app",
    "log_url": "https://github.com/octocat/example/actions/runs/123456",
    "target_url": "https://github.com/octocat/example/actions/runs/123456",
    "created_at": "2024-01-15T10:35:00Z",
    "updated_at": "2024-01-15T10:35:00Z",
    "deployment_url": "https://api.github.com/repos/octocat/example/deployments/1",
    "repository_url": "https://api.github.com/repos/octocat/example",
    "creator": { "login": "vercel[bot]", "id": 1 },
    "performed_via_github_app": {
      "id": 1234,
      "slug": "vercel",
      "name": "Vercel"
    }
  },
  "deployment": {
    "url": "https://api.github.com/repos/octocat/example/deployments/1",
    "id": 1,
    "sha": "a]84d88e7554fc1fa21bcbc4efae3c782a70d2b9d",
    "ref": "feature-branch",
    "task": "deploy",
    "environment": "preview",
    "description": "Preview deployment for PR #42",
    "creator": { "login": "octocat" },
    "created_at": "2024-01-15T10:30:00Z",
    "statuses_url": "https://api.github.com/repos/octocat/example/deployments/1/statuses",
    "transient_environment": true,
    "production_environment": false
  },
  "check_run": null,
  "workflow": null,
  "workflow_run": null,
  "repository": { "id": 1, "full_name": "octocat/example" },
  "sender": { "login": "vercel[bot]" },
  "installation": { "id": 12345 }
}
```

**Critical fields for a testing platform:**
- `deployment_status.state` -- check for `"success"` to know deployment is ready
- `deployment_status.environment_url` -- **the URL to test against**
- `deployment_status.environment` -- which environment (preview, staging, production)
- `deployment.sha` -- the commit being tested
- `deployment.ref` -- the branch/tag
- `deployment.transient_environment` -- whether this is a PR preview
- `installation.id` -- needed for authenticating API calls back

### 3.3 Webhook Event Lifecycle for a PR Preview

The sequence when a developer pushes to a PR branch with Vercel configured:

1. Developer pushes code to `feature-branch`
2. GitHub fires a `push` event
3. Vercel (GitHub App) receives the push event
4. Vercel creates a Deployment: `POST /repos/{owner}/{repo}/deployments` with `environment: "Preview"`, `transient_environment: true`
5. GitHub fires a `deployment` event
6. Vercel posts Deployment Status: `state: "in_progress"`
7. GitHub fires a `deployment_status` event (state=in_progress)
8. Vercel builds and deploys the application
9. Vercel posts Deployment Status: `state: "success"`, `environment_url: "https://pr-42--app.vercel.app"`
10. GitHub fires a `deployment_status` event (state=success) -- **this is the event a testing platform should listen for**
11. Testing platform receives the webhook, extracts `environment_url`, runs tests
12. Testing platform reports results via Checks API

### 3.4 Using `deployment_status` as a GitHub Actions Trigger

```yaml
on:
  deployment_status:

jobs:
  test-deployment:
    if: github.event.deployment_status.state == 'success'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run tests against deployment
        run: |
          npx playwright test --config=e2e.config.ts
        env:
          TARGET_URL: ${{ github.event.deployment_status.environment_url }}
```

**Context values available:**
- `github.event.deployment_status.state` -- e.g., "success"
- `github.event.deployment_status.environment_url` -- the deployed URL
- `github.event.deployment_status.environment` -- environment name
- `github.event.deployment.sha` -- commit SHA
- `github.event.deployment.ref` -- branch/tag ref

**Important caveat:** Workflows triggered by `deployment_status` do NOT fire for `inactive` states.

---

## 4. GitHub Apps Architecture

A GitHub App is the recommended architecture for a testing platform that needs to receive deployment events, run tests, and report results.

### 4.1 Why GitHub App (Not OAuth App)

| Feature | GitHub App | OAuth App |
|---------|-----------|-----------|
| Granular permissions | Yes, per-resource | No, broad scopes |
| Webhook events | Subscribed per-app | Per-repo hooks only |
| Acts as bot identity | Yes (`app-name[bot]`) | No, acts as user |
| Installation-based auth | Yes, per-org/repo | No |
| Rate limits | Higher (5000/hour per install) | User-based |
| Checks API write access | Yes | No |
| Built-in webhook verification | Yes | Manual |

### 4.2 Required Permissions for a Testing Platform

| Permission | Level | Purpose |
|------------|-------|---------|
| **Deployments** | Read | Receive `deployment` and `deployment_status` events; read deployment data |
| **Checks** | Write | Create and update check runs with test results and annotations |
| **Pull Requests** | Read | Read PR data to associate tests with PRs; optionally Write to post comments |
| **Statuses** | Write | Post commit status checks (simpler alternative to Checks API) |
| **Contents** | Read | Read repository files (e.g., test configuration) |
| **Actions** | Read | Read workflow run data (optional, for correlating with Actions runs) |
| **Metadata** | Read | Automatically granted; basic repo metadata |

**Webhook Event Subscriptions:**
- `deployment_status` -- primary trigger for running tests
- `deployment` -- optional, to track deployment creation
- `check_suite` -- to handle re-run requests
- `check_run` -- to handle re-run and requested_action events
- `pull_request` -- optional, for PR-aware testing logic
- `installation` -- to handle app installation/uninstallation

### 4.3 Permitted API Endpoints by Permission

**With `deployments:read`:**
- `GET /repos/{owner}/{repo}/deployments`
- `GET /repos/{owner}/{repo}/deployments/{deployment_id}`
- `GET /repos/{owner}/{repo}/deployments/{deployment_id}/statuses`
- `GET /repos/{owner}/{repo}/deployments/{deployment_id}/statuses/{status_id}`

**With `checks:write`:**
- `POST /repos/{owner}/{repo}/check-runs`
- `PATCH /repos/{owner}/{repo}/check-runs/{check_run_id}`
- `POST /repos/{owner}/{repo}/check-runs/{check_run_id}/rerequest`
- `GET /repos/{owner}/{repo}/check-runs/{check_run_id}`
- `GET /repos/{owner}/{repo}/check-runs/{check_run_id}/annotations`
- `GET /repos/{owner}/{repo}/check-suites/{check_suite_id}/check-runs`
- `GET /repos/{owner}/{repo}/commits/{ref}/check-runs`

**With `statuses:write`:**
- `POST /repos/{owner}/{repo}/statuses/{sha}`
- `GET /repos/{owner}/{repo}/commits/{ref}/status`
- `GET /repos/{owner}/{repo}/commits/{ref}/statuses`

### 4.4 Creating a GitHub App

1. Navigate to GitHub Settings > Developer Settings > GitHub Apps > New GitHub App
2. Fill in:
   - **App Name:** Max 34 characters, must be unique across GitHub
   - **Homepage URL:** Your testing platform's website
   - **Webhook URL:** Your server endpoint that will receive events (e.g., `https://your-platform.com/webhooks/github`)
   - **Webhook Secret:** A strong random string for verifying webhook payloads
3. Select permissions (as listed in 4.2 above)
4. Subscribe to webhook events (deployment_status, check_suite, check_run, etc.)
5. Choose installation scope: "Any account" for public apps, or "Only this account" for private
6. Generate a private key (downloaded as `.pem` file)
7. Note the App ID and Client ID

### 4.5 Authentication Flow

#### Step 1: Generate JWT (authenticate as the App)

The JWT authenticates the app itself. Used to list installations and create installation tokens.

**JWT Payload:**
```json
{
  "iat": 1700000000,
  "exp": 1700000600,
  "iss": "YOUR_APP_CLIENT_ID"
}
```

- `iat`: Issued at -- set 60 seconds in the past (clock drift protection)
- `exp`: Expires at -- max 10 minutes in the future
- `iss`: Your app's Client ID (or App ID for older apps)
- Algorithm: RS256, signed with the app's private key

**Python Example:**
```python
import jwt
import time

def generate_jwt(app_id, private_key_path):
    with open(private_key_path, 'r') as f:
        private_key = f.read()

    payload = {
        'iat': int(time.time()) - 60,
        'exp': int(time.time()) + (10 * 60),
        'iss': app_id
    }

    return jwt.encode(payload, private_key, algorithm='RS256')
```

**Usage:**
```bash
curl -H "Authorization: Bearer YOUR_JWT" \
     -H "Accept: application/vnd.github+json" \
     "https://api.github.com/app/installations"
```

#### Step 2: Get Installation Access Token

Exchange the JWT for an installation-specific token that can access repos.

```
POST /app/installations/{installation_id}/access_tokens
```

**Request (with JWT as Bearer):**
```json
{
  "repositories": ["my-repo"],
  "permissions": {
    "checks": "write",
    "deployments": "read",
    "pull_requests": "read"
  }
}
```

**Response:**
```json
{
  "token": "ghs_xxxxxxxxxxxxxxxxxxxx",
  "expires_at": "2024-01-15T11:30:00Z",
  "permissions": {
    "checks": "write",
    "deployments": "read",
    "pull_requests": "read"
  },
  "repositories": [
    { "id": 1, "name": "my-repo", "full_name": "octocat/my-repo" }
  ]
}
```

- Token expires after **1 hour**
- Can scope down to specific repositories and permissions (cannot exceed app's granted permissions)
- `installation_id` comes from the webhook payload's `installation.id` field or from listing installations

#### Step 3: Use Installation Token for API Calls

```bash
curl -H "Authorization: Bearer ghs_xxxxxxxxxxxxxxxxxxxx" \
     -H "Accept: application/vnd.github+json" \
     "https://api.github.com/repos/octocat/my-repo/deployments"
```

### 4.6 Installation Flow for Organizations

1. Organization admin visits your app's GitHub page (e.g., `https://github.com/apps/your-app`)
2. Clicks "Install" or "Configure"
3. Chooses the organization to install on
4. Selects repository access: "All repositories" or "Only select repositories"
5. Reviews and approves the requested permissions
6. Your app receives an `installation` webhook event with the `installation_id`
7. Your app stores the `installation_id` for future API calls

**Installation Object:**
```json
{
  "id": 12345,
  "account": {
    "login": "my-org",
    "id": 67890,
    "type": "Organization"
  },
  "app_id": 1234,
  "repository_selection": "selected",
  "permissions": {
    "checks": "write",
    "deployments": "read",
    "pull_requests": "read",
    "metadata": "read"
  },
  "created_at": "2024-01-15T10:00:00Z",
  "updated_at": "2024-01-15T10:00:00Z"
}
```

### 4.7 Webhook Verification

All incoming webhooks must be verified using HMAC-SHA256:

```python
import hmac
import hashlib

def verify_webhook(payload_body, signature_header, secret):
    expected = 'sha256=' + hmac.new(
        secret.encode('utf-8'),
        payload_body,
        hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature_header)
```

The signature is in the `X-Hub-Signature-256` header.

### 4.8 Using Octokit SDK (Recommended Approach)

```javascript
import { App } from 'octokit';

const app = new App({
  appId: process.env.APP_ID,
  privateKey: process.env.PRIVATE_KEY,
  webhooks: { secret: process.env.WEBHOOK_SECRET }
});

// Handle deployment_status events
app.webhooks.on('deployment_status', async ({ octokit, payload }) => {
  if (payload.deployment_status.state !== 'success') return;

  const deploymentUrl = payload.deployment_status.environment_url;
  const sha = payload.deployment.sha;
  const repo = payload.repository.full_name;

  // Create a check run
  await octokit.request('POST /repos/{owner}/{repo}/check-runs', {
    owner: payload.repository.owner.login,
    repo: payload.repository.name,
    name: 'E2E Tests',
    head_sha: sha,
    status: 'in_progress',
    started_at: new Date().toISOString()
  });

  // Run tests against deploymentUrl...
  // Update check run with results...
});
```

---

## 5. GitHub Checks API

The Checks API is how testing platforms report results back into GitHub pull requests. It supports rich output with markdown, annotations (inline code comments), and images.

### 5.1 Check Runs vs. Commit Statuses

| Feature | Check Runs (Checks API) | Commit Statuses |
|---------|------------------------|-----------------|
| Rich output | Markdown, annotations, images | Simple description string |
| Inline annotations | Yes, per-file per-line | No |
| Re-run support | Yes, built-in | No |
| Action buttons | Yes (up to 3) | No |
| Who can create | GitHub Apps only | Any authenticated user |
| Multiple results | Yes, different check names | Yes, different context strings |
| PR integration | Deep -- appears in Checks tab | Appears in status checks |

### 5.2 Creating a Check Run

```
POST /repos/{owner}/{repo}/check-runs
```

**Request Body:**
```json
{
  "name": "TINAA E2E Tests",
  "head_sha": "ce587453ced02b1526dfb4cb910479d431683101",
  "status": "in_progress",
  "started_at": "2024-01-15T10:35:00Z",
  "external_id": "tinaa-run-12345",
  "details_url": "https://tinaa.example.com/runs/12345"
}
```

**Required fields:**
- `name` -- display name for the check
- `head_sha` -- the commit SHA to associate the check with

**Optional fields:**
| Field | Description |
|-------|-------------|
| `status` | `queued`, `in_progress`, `completed`, `waiting`, `requested`, `pending` |
| `conclusion` | Required when `status: "completed"` -- see below |
| `started_at` | ISO 8601 timestamp |
| `completed_at` | ISO 8601 timestamp |
| `external_id` | Your platform's internal identifier |
| `details_url` | Link to full results on your platform |
| `output` | Rich output object (see 5.4) |
| `actions` | Up to 3 action buttons (see 5.6) |

### 5.3 Updating a Check Run

```
PATCH /repos/{owner}/{repo}/check-runs/{check_run_id}
```

Use this to update status, add output/annotations, and set conclusions as tests complete.

### 5.4 Rich Output Object

The `output` object supports markdown, annotations, and images:

```json
{
  "output": {
    "title": "E2E Test Results",
    "summary": "**23 passed**, 2 failed, 1 skipped out of 26 tests\n\nRun time: 4m 32s\nTarget: https://pr-42--app.vercel.app",
    "text": "## Failed Tests\n\n### `test/checkout.spec.ts`\n- **Payment form validation** -- Timeout waiting for payment confirmation\n- **Cart total calculation** -- Expected $29.99 but got $31.49\n\n## Performance Metrics\n| Page | LCP | FID | CLS |\n|------|-----|-----|-----|\n| Home | 1.2s | 45ms | 0.05 |\n| Checkout | 2.8s | 120ms | 0.12 |\n\n## Screenshots\nSee annotations for failure screenshots.",
    "annotations": [
      {
        "path": "test/checkout.spec.ts",
        "start_line": 42,
        "end_line": 42,
        "annotation_level": "failure",
        "title": "Payment form validation",
        "message": "Timeout waiting for payment confirmation dialog.\nExpected element [data-testid='confirmation'] to be visible within 30000ms.",
        "raw_details": "Error: locator.waitFor: Timeout 30000ms exceeded.\nCall log:\n  - waiting for locator('[data-testid=confirmation]')"
      },
      {
        "path": "test/checkout.spec.ts",
        "start_line": 78,
        "end_line": 85,
        "annotation_level": "failure",
        "title": "Cart total calculation",
        "message": "Expected $29.99 but got $31.49. Possible tax calculation issue.",
        "raw_details": "AssertionError: expected '$31.49' to equal '$29.99'"
      },
      {
        "path": "test/homepage.spec.ts",
        "start_line": 15,
        "end_line": 15,
        "annotation_level": "warning",
        "title": "Slow page load",
        "message": "Homepage LCP is 2.8s, exceeding 2.5s threshold."
      }
    ],
    "images": [
      {
        "alt": "Checkout page failure screenshot",
        "image_url": "https://tinaa.example.com/screenshots/run-12345/checkout-failure.png",
        "caption": "Payment confirmation dialog did not appear"
      },
      {
        "alt": "Test results summary",
        "image_url": "https://tinaa.example.com/badges/run-12345/summary.svg",
        "caption": "23/26 tests passed (88.5%)"
      }
    ]
  }
}
```

**Field details:**
| Field | Limits | Description |
|-------|--------|-------------|
| `title` | Required | Displayed as the check run's heading |
| `summary` | Required, supports Markdown | Displayed prominently; max 65535 chars |
| `text` | Supports Markdown | Detailed output; max 65535 chars |
| `annotations` | Max 50 per request | Inline code comments on specific files/lines |
| `images` | Array | Images displayed in the check output |

**Annotation fields:**
| Field | Required | Description |
|-------|----------|-------------|
| `path` | Yes | File path relative to repo root |
| `start_line` | Yes | Starting line number |
| `end_line` | Yes | Ending line number |
| `start_column` | No | Starting column (same line only) |
| `end_column` | No | Ending column (same line only) |
| `annotation_level` | Yes | `notice`, `warning`, or `failure` |
| `title` | No | Short title (max 255 chars) |
| `message` | Yes | Description (max 64 KB) |
| `raw_details` | No | Additional details like stack traces (max 64 KB) |

### 5.5 Conclusion Values

When setting `status: "completed"`, you must set a `conclusion`:

| Value | Meaning |
|-------|---------|
| `success` | All tests passed |
| `failure` | Tests failed |
| `neutral` | Tests completed but results are informational only |
| `cancelled` | Test run was cancelled |
| `timed_out` | Test run timed out |
| `action_required` | Manual intervention needed |
| `skipped` | Tests were skipped |
| `stale` | Results are outdated |

### 5.6 Action Buttons

Check runs can include up to 3 action buttons that trigger webhook events when clicked:

```json
{
  "actions": [
    {
      "label": "Re-run Tests",
      "description": "Run the full test suite again",
      "identifier": "rerun_all"
    },
    {
      "label": "Re-run Failed",
      "description": "Only re-run failed tests",
      "identifier": "rerun_failed"
    },
    {
      "label": "View Report",
      "description": "Open detailed test report",
      "identifier": "view_report"
    }
  ]
}
```

When a user clicks an action button, your app receives a `check_run` webhook event with `action: "requested_action"` and the `identifier` in the payload.

### 5.7 Constraints

- Maximum 1000 check runs per name in a check suite
- Maximum 50 annotations per API request (make multiple requests for more)
- GitHub Actions workflows: limited to 10 warning and 10 error annotations per step
- Maximum 3 actions per check run
- Checks API only detects pushes in the repository where created; forked branch pushes return empty `pull_requests`
- **Only GitHub Apps can create/update check runs** (not OAuth apps or PATs)

### 5.8 How Real Platforms Use the Checks API

**Codecov:**
- Creates a check run named "CodecovChecks" with a "patch" status
- Annotations show line-by-line coverage on files changed in the PR
- Lines added without test coverage get `warning` annotations
- Rich markdown summary shows coverage percentages and diffs
- Enabled by default for all GitHub users

**Snyk:**
- Creates check runs for security vulnerability scanning
- Annotations point to specific dependency declarations or code patterns
- Markdown output includes severity levels, CVE IDs, and remediation advice
- Uses `failure` conclusion when critical vulnerabilities are found

**Pattern for a Testing Platform (like TINAA):**
1. Receive `deployment_status` webhook with `state: "success"`
2. Create a check run with `status: "in_progress"` against the deployment's `sha`
3. Run tests against the `environment_url`
4. Update the check run with `status: "completed"`, appropriate `conclusion`, and rich `output` with annotations for failures
5. Optionally include action buttons for re-running tests

---

## 6. GitHub Actions Integration Patterns

### 6.1 Pattern 1: Deployment-Triggered Testing Workflow

This workflow runs tests automatically whenever a deployment succeeds:

```yaml
name: Post-Deployment Tests
on:
  deployment_status:

jobs:
  e2e-tests:
    if: github.event.deployment_status.state == 'success'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          ref: ${{ github.event.deployment.sha }}

      - name: Install dependencies
        run: npm ci

      - name: Install Playwright browsers
        run: npx playwright install --with-deps

      - name: Run E2E tests
        run: npx playwright test
        env:
          BASE_URL: ${{ github.event.deployment_status.environment_url }}
          DEPLOYMENT_ENV: ${{ github.event.deployment_status.environment }}

      - name: Upload test results
        if: always()
        uses: actions/upload-artifact@v4
        with:
          name: playwright-report
          path: playwright-report/
```

### 6.2 Pattern 2: Deploy-Then-Test with Job Outputs

Pass deployment URLs between a deploy job and a test job:

```yaml
name: Deploy and Test
on:
  push:
    branches: [main]
  pull_request:

jobs:
  deploy:
    runs-on: ubuntu-latest
    outputs:
      deployment-url: ${{ steps.deploy.outputs.url }}
      environment: ${{ steps.deploy.outputs.environment }}
    environment:
      name: ${{ github.event_name == 'push' && 'production' || 'preview' }}
      url: ${{ steps.deploy.outputs.url }}
    steps:
      - uses: actions/checkout@v4
      - id: deploy
        run: |
          # Deploy and capture the URL
          DEPLOY_URL=$(./deploy.sh)
          echo "url=$DEPLOY_URL" >> "$GITHUB_OUTPUT"
          echo "environment=${{ github.event_name == 'push' && 'production' || 'preview' }}" >> "$GITHUB_OUTPUT"

  test:
    needs: deploy
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run tests against deployment
        run: npx playwright test
        env:
          BASE_URL: ${{ needs.deploy.outputs.deployment-url }}
          TEST_ENV: ${{ needs.deploy.outputs.environment }}
```

**Key mechanism:** The `deploy` job writes the URL to `$GITHUB_OUTPUT`, maps it to a job-level output via `outputs:`, and the `test` job accesses it via `needs.deploy.outputs.deployment-url`.

### 6.3 Pattern 3: Custom Action That Invokes an External Testing Service

```yaml
# .github/actions/run-tinaa-tests/action.yml
name: 'Run TINAA Tests'
description: 'Invoke TINAA testing platform against a deployment'
inputs:
  deployment-url:
    description: 'URL of the deployment to test'
    required: true
  api-key:
    description: 'TINAA API key'
    required: true
  test-suite:
    description: 'Test suite to run'
    required: false
    default: 'full'
  wait-for-results:
    description: 'Wait for test results'
    required: false
    default: 'true'
outputs:
  run-id:
    description: 'TINAA test run ID'
    value: ${{ steps.trigger.outputs.run-id }}
  result:
    description: 'Test result (pass/fail)'
    value: ${{ steps.wait.outputs.result }}
  report-url:
    description: 'URL to the test report'
    value: ${{ steps.wait.outputs.report-url }}
runs:
  using: 'composite'
  steps:
    - id: trigger
      shell: bash
      run: |
        RESPONSE=$(curl -s -X POST "https://api.tinaa.example.com/runs" \
          -H "Authorization: Bearer ${{ inputs.api-key }}" \
          -H "Content-Type: application/json" \
          -d '{
            "target_url": "${{ inputs.deployment-url }}",
            "test_suite": "${{ inputs.test-suite }}",
            "commit_sha": "${{ github.sha }}",
            "repository": "${{ github.repository }}"
          }')
        RUN_ID=$(echo $RESPONSE | jq -r '.run_id')
        echo "run-id=$RUN_ID" >> "$GITHUB_OUTPUT"

    - id: wait
      if: inputs.wait-for-results == 'true'
      shell: bash
      run: |
        # Poll for results
        while true; do
          STATUS=$(curl -s "https://api.tinaa.example.com/runs/${{ steps.trigger.outputs.run-id }}" \
            -H "Authorization: Bearer ${{ inputs.api-key }}" | jq -r '.status')
          if [ "$STATUS" = "completed" ] || [ "$STATUS" = "failed" ]; then
            RESULT=$(curl -s "https://api.tinaa.example.com/runs/${{ steps.trigger.outputs.run-id }}" \
              -H "Authorization: Bearer ${{ inputs.api-key }}")
            echo "result=$(echo $RESULT | jq -r '.result')" >> "$GITHUB_OUTPUT"
            echo "report-url=$(echo $RESULT | jq -r '.report_url')" >> "$GITHUB_OUTPUT"
            break
          fi
          sleep 10
        done
```

**Usage in a workflow:**
```yaml
- uses: ./.github/actions/run-tinaa-tests
  with:
    deployment-url: ${{ needs.deploy.outputs.url }}
    api-key: ${{ secrets.TINAA_API_KEY }}
    test-suite: smoke
```

### 6.4 Pattern 4: `workflow_dispatch` for On-Demand Testing

Allow external services or users to trigger test runs with custom parameters:

```yaml
name: On-Demand Test Run
on:
  workflow_dispatch:
    inputs:
      deployment-url:
        description: 'URL to test against'
        required: true
        type: string
      test-suite:
        description: 'Test suite to run'
        required: true
        type: choice
        options:
          - smoke
          - regression
          - full
      environment:
        description: 'Target environment'
        type: environment
        required: true
      browser:
        description: 'Browser to test'
        type: choice
        options:
          - chromium
          - firefox
          - webkit
          - all
        default: 'chromium'

jobs:
  test:
    runs-on: ubuntu-latest
    environment: ${{ inputs.environment }}
    steps:
      - uses: actions/checkout@v4
      - run: npx playwright test --project=${{ inputs.browser }}
        env:
          BASE_URL: ${{ inputs.deployment-url }}
          TEST_SUITE: ${{ inputs.test-suite }}
```

**Triggering via API:**
```bash
curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Accept: application/vnd.github+json" \
  "https://api.github.com/repos/octocat/my-repo/actions/workflows/test.yml/dispatches" \
  -d '{
    "ref": "main",
    "inputs": {
      "deployment-url": "https://pr-42--app.vercel.app",
      "test-suite": "smoke",
      "environment": "preview",
      "browser": "chromium"
    }
  }'
```

**Triggering via GitHub CLI:**
```bash
gh workflow run test.yml \
  -f deployment-url="https://pr-42--app.vercel.app" \
  -f test-suite=smoke \
  -f environment=preview \
  -f browser=chromium
```

Input limits: max 25 inputs, max 65,535 characters total payload.

### 6.5 Pattern 5: `repository_dispatch` for External Service Integration

When an external testing platform needs to trigger GitHub Actions workflows:

```yaml
name: External Test Trigger
on:
  repository_dispatch:
    types: [run-tests, test-completed]

jobs:
  run-tests:
    if: github.event.action == 'run-tests'
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npx playwright test
        env:
          BASE_URL: ${{ github.event.client_payload.deployment_url }}
          COMMIT_SHA: ${{ github.event.client_payload.sha }}

  handle-results:
    if: github.event.action == 'test-completed'
    runs-on: ubuntu-latest
    steps:
      - run: |
          echo "Tests ${{ github.event.client_payload.result }} on ${{ github.event.client_payload.deployment_url }}"
          echo "Report: ${{ github.event.client_payload.report_url }}"
```

**Triggering via API:**
```bash
curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Accept: application/vnd.github+json" \
  "https://api.github.com/repos/octocat/my-repo/dispatches" \
  -d '{
    "event_type": "run-tests",
    "client_payload": {
      "deployment_url": "https://staging.example.com",
      "sha": "abc123",
      "environment": "staging",
      "pr_number": 42
    }
  }'
```

Constraints: max 10 top-level properties in `client_payload`, max 65,535 characters, `event_type` max 100 characters.

### 6.6 Pattern 6: Reusable Workflows for Testing

Define a reusable testing workflow that multiple repositories can call:

```yaml
# .github/workflows/reusable-e2e-tests.yml
name: Reusable E2E Tests
on:
  workflow_call:
    inputs:
      deployment-url:
        required: true
        type: string
      test-suite:
        required: false
        type: string
        default: 'full'
      node-version:
        required: false
        type: string
        default: '20'
    secrets:
      test-api-key:
        required: false
    outputs:
      test-result:
        description: 'Test outcome'
        value: ${{ jobs.test.outputs.result }}
      report-url:
        description: 'Test report URL'
        value: ${{ jobs.test.outputs.report-url }}

jobs:
  test:
    runs-on: ubuntu-latest
    outputs:
      result: ${{ steps.run-tests.outputs.result }}
      report-url: ${{ steps.run-tests.outputs.report-url }}
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with:
          node-version: ${{ inputs.node-version }}
      - run: npm ci
      - run: npx playwright install --with-deps
      - id: run-tests
        run: |
          if npx playwright test; then
            echo "result=success" >> "$GITHUB_OUTPUT"
          else
            echo "result=failure" >> "$GITHUB_OUTPUT"
          fi
          echo "report-url=https://tinaa.example.com/reports/${{ github.run_id }}" >> "$GITHUB_OUTPUT"
        env:
          BASE_URL: ${{ inputs.deployment-url }}
          TEST_SUITE: ${{ inputs.test-suite }}
```

**Calling the reusable workflow:**
```yaml
jobs:
  deploy:
    # ... deploy job ...
    outputs:
      url: ${{ steps.deploy.outputs.url }}

  test:
    needs: deploy
    uses: my-org/.github/.github/workflows/reusable-e2e-tests.yml@main
    with:
      deployment-url: ${{ needs.deploy.outputs.url }}
      test-suite: smoke
    secrets:
      test-api-key: ${{ secrets.TINAA_API_KEY }}

  notify:
    needs: test
    runs-on: ubuntu-latest
    steps:
      - run: echo "Tests ${{ needs.test.outputs.test-result }}"
```

Limitations: max 10 levels of nesting, no loops, environment secrets cannot be passed via `workflow_call` (use `secrets: inherit` instead).

### 6.7 GITHUB_TOKEN Permissions for Testing Workflows

```yaml
permissions:
  deployments: read
  checks: write
  pull-requests: write
  statuses: write
  contents: read
```

These permissions allow the workflow's `GITHUB_TOKEN` to read deployment data, create check runs, post PR comments, update commit statuses, and read repo contents.

---

## 7. End-to-End Integration Architecture

### 7.1 Architecture Overview: Testing Platform as a GitHub App

```
Developer pushes code
         |
         v
  GitHub fires events
         |
    +----+----+
    |         |
    v         v
 Vercel    TINAA (GitHub App)
 deploys   listens for deployment_status
    |         |
    v         |
 Posts        |
 deployment   |
 status       v
 (success) <- Receives webhook:
    |         - environment_url
    |         - commit SHA
    |         - installation_id
    v
 TINAA runs tests against environment_url
         |
         v
 TINAA posts results via Checks API
 (check run with annotations, markdown, images)
         |
         v
 Results appear in PR Checks tab
```

### 7.2 Complete Webhook Handler (Node.js / Octokit)

```javascript
import { App, createNodeMiddleware } from 'octokit';

const app = new App({
  appId: process.env.APP_ID,
  privateKey: process.env.PRIVATE_KEY,
  webhooks: { secret: process.env.WEBHOOK_SECRET }
});

// Listen for successful deployments
app.webhooks.on('deployment_status', async ({ octokit, payload }) => {
  const { deployment_status, deployment, repository } = payload;

  // Only act on successful deployments
  if (deployment_status.state !== 'success') return;

  // Skip if no environment URL
  if (!deployment_status.environment_url) return;

  const owner = repository.owner.login;
  const repo = repository.name;
  const sha = deployment.sha;
  const targetUrl = deployment_status.environment_url;
  const environment = deployment_status.environment;

  // Step 1: Create a check run (in_progress)
  const { data: checkRun } = await octokit.request(
    'POST /repos/{owner}/{repo}/check-runs',
    {
      owner, repo,
      name: 'TINAA E2E Tests',
      head_sha: sha,
      status: 'in_progress',
      started_at: new Date().toISOString(),
      details_url: `https://tinaa.example.com/runs/${sha}`,
      output: {
        title: 'Running E2E tests...',
        summary: `Testing deployment at ${targetUrl}\nEnvironment: ${environment}`
      }
    }
  );

  try {
    // Step 2: Run tests against the deployment URL
    const results = await runTests(targetUrl, environment);

    // Step 3: Update check run with results
    await octokit.request(
      'PATCH /repos/{owner}/{repo}/check-runs/{check_run_id}',
      {
        owner, repo,
        check_run_id: checkRun.id,
        status: 'completed',
        conclusion: results.allPassed ? 'success' : 'failure',
        completed_at: new Date().toISOString(),
        output: {
          title: results.allPassed
            ? `All ${results.total} tests passed`
            : `${results.failed} of ${results.total} tests failed`,
          summary: results.summary,   // Markdown
          text: results.details,       // Markdown with full details
          annotations: results.annotations.slice(0, 50),  // Max 50 per request
          images: results.images
        },
        actions: [
          {
            label: 'Re-run All',
            description: 'Re-run the full test suite',
            identifier: 'rerun_all'
          },
          {
            label: 'Re-run Failed',
            description: 'Only re-run failed tests',
            identifier: 'rerun_failed'
          }
        ]
      }
    );

    // Handle more than 50 annotations
    for (let i = 50; i < results.annotations.length; i += 50) {
      await octokit.request(
        'PATCH /repos/{owner}/{repo}/check-runs/{check_run_id}',
        {
          owner, repo,
          check_run_id: checkRun.id,
          output: {
            title: results.title,
            summary: results.summary,
            annotations: results.annotations.slice(i, i + 50)
          }
        }
      );
    }
  } catch (error) {
    // Update check run with error
    await octokit.request(
      'PATCH /repos/{owner}/{repo}/check-runs/{check_run_id}',
      {
        owner, repo,
        check_run_id: checkRun.id,
        status: 'completed',
        conclusion: 'failure',
        completed_at: new Date().toISOString(),
        output: {
          title: 'Test execution failed',
          summary: `Error: ${error.message}`
        }
      }
    );
  }
});

// Handle check run re-run requests
app.webhooks.on('check_run.requested_action', async ({ octokit, payload }) => {
  const action = payload.requested_action.identifier;
  // Trigger re-run based on action identifier
});

// Handle check suite re-run requests
app.webhooks.on('check_run.rerequested', async ({ octokit, payload }) => {
  // Re-run the tests for this check run
});
```

### 7.3 Discovering Deployment URLs Programmatically

For a testing platform that needs to find existing deployment URLs (not just react to webhooks):

```javascript
async function getDeploymentUrl(octokit, owner, repo, environment) {
  // Get the latest deployment for the environment
  const { data: deployments } = await octokit.request(
    'GET /repos/{owner}/{repo}/deployments',
    {
      owner, repo,
      environment: environment,
      per_page: 1
    }
  );

  if (deployments.length === 0) return null;

  // Get the latest status for that deployment
  const { data: statuses } = await octokit.request(
    'GET /repos/{owner}/{repo}/deployments/{deployment_id}/statuses',
    {
      owner, repo,
      deployment_id: deployments[0].id,
      per_page: 1
    }
  );

  if (statuses.length === 0 || statuses[0].state !== 'success') return null;

  return {
    url: statuses[0].environment_url,
    sha: deployments[0].sha,
    ref: deployments[0].ref,
    environment: deployments[0].environment,
    deployed_at: statuses[0].created_at
  };
}

// Usage
const staging = await getDeploymentUrl(octokit, 'my-org', 'my-app', 'staging');
// => { url: 'https://staging.my-app.com', sha: 'abc123', ... }

const preview = await getDeploymentUrl(octokit, 'my-org', 'my-app', 'Preview');
// => { url: 'https://pr-42--my-app.vercel.app', sha: 'def456', ... }
```

### 7.4 Summary of API Headers

All GitHub API requests require:
```
Authorization: Bearer <token>
Accept: application/vnd.github+json
X-GitHub-Api-Version: 2022-11-28
```

The token is either:
- A GitHub App installation access token (for GitHub App auth)
- A personal access token with appropriate scopes
- The `GITHUB_TOKEN` in GitHub Actions workflows
