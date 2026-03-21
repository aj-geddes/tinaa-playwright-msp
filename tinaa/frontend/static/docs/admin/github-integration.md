# GitHub Integration

TINAA MSP integrates with GitHub via a GitHub App to receive deployment events, post check results, and gate deployments based on quality scores. This integration is optional but strongly recommended for teams using GitHub for CI/CD.

---

## What the integration enables

- **Automatic test runs** on every GitHub deployment event targeting monitored environments.
- **Deployment status updates** — TINAA posts a `deployment_status` back to GitHub (`success` or `failure`) with a link to the test results.
- **PR check results** — TINAA creates a GitHub Check on pull requests with a summary of test outcomes, quality score, and a link to the full report.
- **Deployment protection rules** — block merges and deploys when the quality gate fails.
- **Webhook-triggered monitoring** — optionally start a monitoring burst after a deployment completes.

---

## Step 1 — Create a GitHub App

1. Go to **GitHub → Settings → Developer settings → GitHub Apps → New GitHub App** (or your organisation's equivalent at `github.com/organizations/<org>/settings/apps/new`).

2. Fill in the app details:

   | Field | Value |
   |-------|-------|
   | GitHub App name | `TINAA MSP - <YourOrg>` (must be unique across GitHub) |
   | Homepage URL | `https://tinaa.yourcompany.com` (your TINAA instance URL) |
   | Webhook URL | `https://tinaa.yourcompany.com/api/v1/webhooks/github` |
   | Webhook secret | Generate a random secret; you will copy it into `GITHUB_WEBHOOK_SECRET` |

3. Under **Permissions**, set the following:

   **Repository permissions:**

   | Permission | Level |
   |------------|-------|
   | Checks | Read & write |
   | Deployments | Read & write |
   | Pull requests | Read-only |
   | Contents | Read-only |
   | Metadata | Read-only (mandatory) |

   **Organisation permissions:** none required.

   **Account permissions:** none required.

4. Under **Subscribe to events**, enable:
   - `Deployment`
   - `Deployment status`
   - `Pull request`
   - `Push`

5. Under **Where can this GitHub App be installed?**, select **Only on this account** (for a single-org install) or **Any account** (for a multi-org SaaS deployment).

6. Click **Create GitHub App**.

---

## Step 2 — Generate a private key

After creating the app:

1. On the app's settings page, scroll to **Private keys**.
2. Click **Generate a private key** — GitHub downloads a `.pem` file.
3. Store this file securely (e.g. in a secrets manager or as an environment variable).
4. Copy the key content into `GITHUB_APP_PRIVATE_KEY` in your `.env` file. Replace literal newlines with `\n`:

   ```bash
   GITHUB_APP_PRIVATE_KEY=$(cat my-app.2026-03-21.private-key.pem | tr '\n' '\\n')
   ```

   Or mount it as a file and reference the path in the app configuration.

---

## Step 3 — Note the App ID and Installation ID

1. On the app's settings page, note the **App ID** (a number like `123456`) — set this as `GITHUB_APP_ID`.
2. Install the app on your organisation or specific repositories.
3. After installation, the URL changes to include an installation ID (e.g. `/installations/987654`) — set this as `GITHUB_APP_INSTALLATION_ID`.

---

## Step 4 — Configure TINAA

Add these values to your `.env` or Docker Compose environment:

```bash
GITHUB_APP_ID=123456
GITHUB_APP_INSTALLATION_ID=987654
GITHUB_APP_PRIVATE_KEY=-----BEGIN RSA PRIVATE KEY-----\nMIIE...\n-----END RSA PRIVATE KEY-----
GITHUB_WEBHOOK_SECRET=your-random-webhook-secret
```

Restart the API server after updating these values. Verify by checking:

```bash
curl http://localhost:8765/health
# Expect: {"status": "healthy", "github_app": "configured"}
```

---

## Step 5 — Configure webhook

The GitHub App webhook must point to your TINAA instance's public URL:

```
https://tinaa.yourcompany.com/api/v1/webhooks/github
```

TINAA verifies every incoming webhook using HMAC-SHA256 with the `GITHUB_WEBHOOK_SECRET`. Requests with invalid signatures are rejected with HTTP 401.

If your TINAA instance is behind a firewall, ensure GitHub's webhook IP ranges can reach your webhook endpoint. GitHub publishes their IP ranges at `https://api.github.com/meta`.

---

## Step 6 — Install on organisations and repos

1. Go to your GitHub App's settings page.
2. Click **Install App** in the left sidebar.
3. Select the organisation or account to install on.
4. Choose **All repositories** or select specific repositories.
5. Click **Install**.

TINAA now receives webhook events from the installed repositories.

---

## Step 7 — Enable deployment protection rules

To block merges and deploys when quality gates fail:

1. In your GitHub repository, go to **Settings → Environments**.
2. Create or select an environment (e.g. `production`).
3. Under **Deployment protection rules**, click **Add rule**.
4. Select **Required reviewers** or use a custom deployment protection rule (GitHub Enterprise / Teams required for custom rules).
5. For Teams/Enterprise: add TINAA as a deployment protection reviewer.

When TINAA posts a `failure` deployment status, the deployment is blocked until the quality gate passes.

---

## Troubleshooting GitHub integration

### Webhooks not arriving

- Check the webhook delivery log in GitHub App settings → **Advanced** → **Recent deliveries**.
- Confirm the webhook URL is publicly accessible from GitHub's servers.
- Verify `GITHUB_WEBHOOK_SECRET` matches the secret set in the GitHub App.
- Check TINAA logs for `"webhook received"` entries.

### Authentication errors (401 from GitHub API)

- Verify `GITHUB_APP_ID` matches the numeric App ID on the GitHub App settings page.
- Regenerate the private key if you suspect it was corrupted or truncated during copy-paste.
- Confirm the app is installed on the target organisation/repository.
- Check that the installation ID matches the repository's installation (not the app-level ID).

### Deployment statuses not posting

- Verify the app has `Deployments: Read & write` permission.
- Confirm the GitHub deployment was created with the correct environment name matching a TINAA environment.
- Check the TINAA API logs for `POST /api/v1/webhooks/github` entries and the resulting test run.

### Check runs not appearing on PRs

- Verify the app has `Checks: Read & write` permission.
- Confirm `Pull request` events are subscribed in the GitHub App.
- TINAA creates checks on the PR head commit SHA — verify this matches what GitHub expects.
