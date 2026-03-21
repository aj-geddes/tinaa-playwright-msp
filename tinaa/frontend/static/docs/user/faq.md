# Frequently Asked Questions

---

**Q: How is TINAA MSP different from running Playwright tests directly?**

A: TINAA MSP wraps Playwright in a managed service layer that adds scheduling, continuous APM monitoring, quality scoring, GitHub integration, anomaly detection, alert routing, and a unified dashboard. You write YAML playbooks rather than imperative JavaScript, and TINAA handles execution, result storage, baseline tracking, and notification delivery. Think of it as "Playwright as a service with APM built in."

---

**Q: Do I need to write all my playbooks manually?**

A: No. TINAA's Explorer agent can auto-discover user journeys by crawling your application. Run **Auto-discover playbooks** from the product overview and TINAA will generate YAML playbooks covering the navigation paths it finds. These auto-generated playbooks are a starting point — review and extend them with authentication flows, form interactions, and business-critical assertions.

---

**Q: How long does it take to see a quality score after registering a product?**

A: You need at least one completed test run to get a Test Health score and one monitoring cycle to get a Performance score. After clicking **Run Tests** (or waiting for a deployment trigger), your quality score appears within 2–5 minutes depending on the number of playbooks and the speed of your application. The Security and Accessibility components are populated from data collected during test runs.

---

**Q: What browsers does TINAA use for testing?**

A: Chromium by default. You can add Firefox to your `.tinaa.yml` testing configuration. Playwright also supports WebKit (Safari-compatible), but WebKit is not enabled by default due to higher resource consumption. For most teams, Chromium coverage is sufficient since it also powers Google's Web Vitals scoring.

---

**Q: Can TINAA test authenticated pages?**

A: Yes. Use the `fill` action to enter credentials in your sign-in playbook step, or use `evaluate` to inject a session token into `localStorage` or `sessionStorage`. Store credentials as environment variables referenced with `{{env.MY_PASSWORD}}` in your playbook — never hard-code them in YAML.

---

**Q: Why is my quality score lower than I expected?**

A: Open the **Quality Score** panel on your product overview and expand each component. The panel shows the score for each of the four components and a list of recommendations for any component below 80. Common causes of a lower-than-expected score:
- Missing security headers (reduces Security Posture significantly)
- No performance budgets configured (TINAA cannot penalise budget violations without them)
- Auto-generated playbooks with low test coverage breadth
- Accessibility violations found by axe-core during `assert_accessibility` steps

---

**Q: How do I prevent deployments when the quality score is too low?**

A: Install the TINAA GitHub App and enable **deployment protection rules** on your repository. TINAA posts a deployment status (`success` or `failure`) to every GitHub deployment event. GitHub's branch protection rules can require this status to be `success` before merging a PR or deploying. See [Admin — GitHub Integration](../admin/github-integration.md) for setup steps.

---

**Q: Can I run TINAA against a localhost environment?**

A: TINAA's Playwright workers run inside Docker containers and cannot reach your development machine's `localhost` by default. Options:
1. Use your machine's LAN IP (e.g. `http://192.168.1.10:3000`) if TINAA and your machine are on the same network.
2. Use `host.docker.internal` (Docker Desktop on macOS/Windows) as the base URL.
3. Register a development environment and use a tunnel tool like `ngrok` or `cloudflared tunnel` to expose your local server.

---

**Q: How are baselines established and how long does it take?**

A: TINAA collects 7 days of monitoring data before computing a baseline. During the first 7 days, the Performance component uses the performance budgets you configured as proxy thresholds. After 7 days, the system transitions to statistical baselines (P50 median, P95 tail latency). Baselines are recomputed daily using a rolling 7-day window, so they naturally adapt to seasonal traffic patterns.

---

**Q: What happens to my data if I delete a product?**

A: Deleting a product permanently removes all associated data: environments, endpoints, playbooks, test runs, metrics, and quality history. This action cannot be undone. If you only want to stop monitoring temporarily, set the product's status to `inactive` instead — all data is preserved and monitoring pauses until you re-activate it.

---

**Q: Can multiple teams share the same TINAA MSP instance?**

A: Yes, via multi-tenancy. Each team operates within an **organisation** that isolates their products, playbooks, and metrics. Users are assigned roles (`admin`, `developer`, `viewer`) per organisation. An admin can create organisations and invite users from the Settings panel. See [Admin — Multi-Tenancy](../admin/multi-tenancy.md) for the full setup guide.

---

**Q: How do I integrate TINAA with a CI/CD pipeline that is not GitHub?**

A: TINAA exposes a REST API for triggering test runs manually. Call `POST /api/v1/test-runs` with your API key from any CI/CD platform (GitLab CI, CircleCI, Jenkins, etc.). Poll `GET /api/v1/test-runs/{run_id}` until status is `passed` or `failed`, then fail your pipeline step if needed. Example GitLab CI step:

```yaml
test-quality:
  script:
    - |
      RUN_ID=$(curl -s -X POST $TINAA_URL/api/v1/test-runs \
        -H "X-API-Key: $TINAA_API_KEY" \
        -H "Content-Type: application/json" \
        -d '{"product_id":"'$PRODUCT_ID'","environment":"staging","trigger":"ci"}' \
        | jq -r '.id')
      while true; do
        STATUS=$(curl -s $TINAA_URL/api/v1/test-runs/$RUN_ID | jq -r '.status')
        [ "$STATUS" = "passed" ] && exit 0
        [ "$STATUS" = "failed" ] && exit 1
        sleep 10
      done
```

---

**Q: How do I update a playbook after the UI changes?**

A: Open the playbook in the **Playbooks** tab, click **Edit**, and update the `selector` values or assertion text that changed. Save the playbook and run it against staging to confirm it passes before pushing changes. If you store playbooks in your repository (under `.tinaa/playbooks/`), update the YAML files in your code review workflow — TINAA syncs from the repository on the next deployment event.

---

**Q: What does TINAA do when a test run takes too long?**

A: Each playbook has a `timeout_ms` per step (default 30 seconds). If a step times out, TINAA marks it `failed`, captures a screenshot of the current browser state, and moves to the next playbook. There is also a maximum test run duration (default 30 minutes) after which the entire run is cancelled with status `cancelled`. Set `testing.timeout_ms` in `.tinaa.yml` to adjust per-step timeouts.
