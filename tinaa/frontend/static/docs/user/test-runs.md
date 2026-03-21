# Test Runs

A **test run** is a single execution of one or more playbooks against a product environment. TINAA records the outcome of every step, captures screenshots on failure, collects performance metrics, and stores console logs and network activity for debugging.

---

## Triggering test runs

### Manual trigger (dashboard)

1. Navigate to your product's **Test Runs** tab.
2. Click **Run Tests**.
3. Select the **environment** (e.g. `staging` or `production`).
4. Optionally select specific **playbooks** to run; if none are selected, all playbooks for the product run.
5. Click **Start Run**.

The run appears immediately in the list with status `queued`, transitions to `running` within seconds, and completes with `passed` or `failed`.

### Manual trigger (API)

```bash
POST /api/v1/test-runs
{
  "product_id": "00000000-0000-0000-0000-000000000001",
  "environment": "staging",
  "trigger": "manual",
  "playbook_ids": []   # empty = run all playbooks
}
```

### Deployment trigger

When TINAA's GitHub App is installed and a deployment event fires on a monitored repository, TINAA automatically queues a test run against the deployment's environment. The result is posted back to GitHub as a deployment status (`success` or `failure`) with a link to the run details.

### Schedule trigger

Playbooks with a `schedule_cron` field in their trigger block run on that schedule. Scheduled runs use the `schedule` trigger type in run records. Configured via `.tinaa.yml`:

```yaml
testing:
  schedule: "0 3 * * *"   # all playbooks run nightly at 03:00 UTC
```

### PR trigger

When a pull request is opened or updated against the default branch, TINAA queues a run against the `staging` environment (or the environment specified in `on_pr`). The result appears as a GitHub check on the PR.

### Anomaly trigger

TINAA's APM component monitors endpoint metrics continuously. When an anomaly is detected (e.g. response time suddenly increases 3× baseline), TINAA can auto-queue a targeted test run to verify whether a functional regression is also present. Enable this in the monitoring settings under **Auto-test on anomaly**.

---

## Understanding test results

### Run status values

| Status | Meaning |
|--------|---------|
| `queued` | Run is waiting for a Playwright worker to become available |
| `running` | A Playwright browser is actively executing steps |
| `passed` | All steps passed and all performance gates were met |
| `failed` | One or more steps failed or a performance gate was breached |
| `cancelled` | Run was manually cancelled or timed out |
| `error` | TINAA infrastructure error (browser crash, network issue) |

### Run summary panel

The summary panel shows:
- **Total playbooks**: how many playbooks ran
- **Passed / Failed**: count of playbooks by outcome
- **Total steps**: sum of all steps executed
- **Duration**: wall-clock time from start to finish
- **Quality score delta**: change in quality score relative to the previous run

### Step-level results

Each step shows:
- **Status**: `passed`, `failed`, or `skipped`
- **Duration**: time taken for this step
- **Screenshot**: thumbnail (click to expand); always captured on failure, optionally on success
- **Error message**: assertion message, selector not found, timeout, etc.
- **Console output**: browser `console.log` and `console.error` from this step
- **Network activity**: list of HTTP requests made during this step with status codes

### Performance metrics panel

For `page`-type endpoints, TINAA displays Web Vitals collected during the run:

| Metric | Good | Needs Improvement | Poor |
|--------|------|------------------|------|
| LCP | ≤ 2.5 s | 2.5–4.0 s | > 4.0 s |
| FCP | ≤ 1.8 s | 1.8–3.0 s | > 3.0 s |
| CLS | ≤ 0.1 | 0.1–0.25 | > 0.25 |
| INP | ≤ 200 ms | 200–500 ms | > 500 ms |

Values are colour-coded green/amber/red to match the Google Web Vitals classification.

---

## Test run history and comparison

### History view

The **Test Runs** tab shows a chronological list of all runs for the selected product. Filter by:
- **Environment** — production, staging, etc.
- **Status** — passed, failed, all
- **Trigger** — manual, deployment, schedule, pr, anomaly
- **Date range** — last 7 days, 30 days, 90 days, custom

### Comparing runs

Click **Compare** on any two runs to see a side-by-side diff:
- Steps that changed status (new failures or new passes)
- Performance metric changes with percentage delta
- Screenshots from each run placed side-by-side for visual diff

### Trend charts

Each playbook has a **Trend** view showing pass rate over time as a sparkline. Playbooks with declining trends are highlighted in amber to indicate increasing flakiness.

---

## Debugging failed tests

### Step 1: Identify the failing step

Open the failed run and expand the playbook. Look for the first step with a red `failed` badge — subsequent failures are often caused by the first one.

### Step 2: Read the error message

Common error messages and their causes:

| Error | Likely cause |
|-------|-------------|
| `Timeout waiting for selector` | Element not rendered in time — check if selector is correct, page may be slow |
| `Element not found: [data-testid='...']` | Selector changed after a UI update — update the playbook |
| `Expected text "Foo" but got "Bar"` | Copy change or locale issue — update assertion value |
| `Navigation timeout exceeded` | Page taking > `timeout_ms` to respond — check endpoint health |
| `net::ERR_CONNECTION_REFUSED` | Environment is down — check monitoring alerts |
| `assert_no_console_errors: found 2 error(s)` | JavaScript errors in the page — check browser console |

### Step 3: Examine the screenshot

The screenshot captured at the moment of failure often shows exactly what the browser saw: a loading spinner (timeout), an error page (500), or incorrect content (assertion failure).

### Step 4: Check network activity

Look for failed network requests (4xx/5xx responses) in the step's network panel. A failed API call often cascades into a broken UI.

### Step 5: Reproduce locally

Run the failing playbook locally with the TINAA CLI:

```bash
tinaa run-playbook --file playbooks/checkout.yml --env staging --debug
```

The `--debug` flag opens a visible (non-headless) Playwright browser so you can watch the steps execute in real time.

### Step 6: Update or fix

- **Selector changed**: update the `selector` in the playbook YAML.
- **Application bug**: file a bug; the failing test is doing its job.
- **Environment issue**: check the environment's health in the Metrics tab.
- **Flaky timing**: add a `wait` step before the failing assertion, or increase `timeout_ms` on that step.
