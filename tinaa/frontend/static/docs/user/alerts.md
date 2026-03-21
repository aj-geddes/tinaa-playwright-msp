# Alerts & Notifications

TINAA MSP monitors your products continuously and fires alerts when quality degrades, tests fail, endpoints go down, or performance regresses. Alerts are delivered to your configured notification channels and remain active until acknowledged or resolved.

---

## Alert types

### Quality score drop

Fires when the product's composite quality score drops by a configured number of points between consecutive runs.

- **Default threshold**: score drops by 10 or more points.
- **Severity**: `warning` by default; configurable.
- **Use case**: catch broad regressions that cut across multiple quality dimensions.

### Test failure

Fires when one or more playbook steps fail in a test run.

- **Variants**: `any_failure` (any test fails), `critical_failure` (only playbooks tagged `priority: critical`).
- **Severity**: `critical` for critical playbooks, `warning` for others.
- **Use case**: know immediately when a user journey is broken.

### Endpoint down

Fires when a monitored endpoint stops returning a 2xx HTTP status or times out.

- **Trigger**: endpoint health transitions to `down`.
- **Severity**: `critical` for `production` environments, `warning` for others.
- **Use case**: catch outages faster than your users do.

### Performance regression

Fires when an endpoint's response time or Web Vital exceeds a configured threshold relative to its baseline.

- **Default threshold**: response time exceeds baseline P95 by 50%.
- **Severity**: `warning`.
- **Use case**: detect infrastructure or deployment-induced slowdowns.

### Accessibility violation (new)

Fires when a test run introduces new WCAG violations that were not present in the previous run.

- **Severity**: `critical` for new `critical` violations, `warning` for `serious` violations.
- **Use case**: prevent accessibility regressions from reaching production.

---

## Configuring alert rules

### Dashboard

1. Go to **Settings → Alerts → Rules**.
2. Click **Add Rule**.
3. Select the **condition type** from the list above.
4. Set the **threshold** (e.g. score drop of 10 points, response time ratio 1.5×).
5. Select the **severity**: `critical`, `warning`, or `info`.
6. Set the **cooldown period** (minutes) — how long to wait before re-firing the same alert.
7. Optionally scope to a specific environment (e.g. only fire on `production`).
8. Click **Save Rule**.

### .tinaa.yml configuration

```yaml
alerts:
  rules:
    - name: score-drop-warning
      condition: quality_score_drop
      threshold: 10              # alert when score drops by >= 10 points
      severity: warning
      cooldown_minutes: 30
      environments: [production, staging]

    - name: critical-test-failure
      condition: critical_test_failure
      severity: critical
      cooldown_minutes: 5
      environments: [production]

    - name: endpoint-down-production
      condition: endpoint_unavailable
      severity: critical
      cooldown_minutes: 5
      environments: [production]

    - name: performance-regression
      condition: performance_regression
      threshold: 1.5             # fires when response time is 1.5x baseline P95
      severity: warning
      cooldown_minutes: 60
```

---

## Notification channels

### Slack

Alerts are posted to a Slack channel as formatted messages with colour-coded attachments (red=critical, orange=warning, blue=info).

**Setup:**
1. Create an Incoming Webhook in your Slack workspace: *App Directory → Incoming Webhooks → Add to Slack*.
2. Copy the webhook URL.
3. In TINAA Settings → Channels → Add Channel, select **Slack** and paste the URL.

```yaml
alerts:
  channels:
    - type: slack
      config:
        webhook_url: https://hooks.slack.com/services/T00000000/B00000000/xxxxxxxxxxxx
```

### Email

Alerts are sent as plain-text emails. Requires SMTP configuration in admin settings.

```yaml
alerts:
  channels:
    - type: email
      config:
        to:
          - oncall@yourcompany.com
          - platform-team@yourcompany.com
        subject_prefix: "[TINAA]"
```

### PagerDuty

Alerts are sent via the PagerDuty Events API v2. TINAA maps its severity levels to PagerDuty's (`critical` → `critical`, `warning` → `warning`, `info` → `info`). Deduplication keys prevent duplicate incidents for the same ongoing issue.

```yaml
alerts:
  channels:
    - type: pagerduty
      config:
        routing_key: abc123def456    # from PagerDuty integration settings
        severity_threshold: critical  # only page on-call for critical alerts
```

### GitHub Issues

Alerts create GitHub Issues in a specified repository. Useful for tracking quality regressions as first-class issues alongside feature work.

```yaml
alerts:
  channels:
    - type: github_issues
      config:
        owner: acme
        repo: webapp
        labels:
          - tinaa-alert
          - quality
```

### Webhooks

TINAA POSTs alert data as JSON to any HTTP endpoint. Useful for integrating with custom ticketing systems, Datadog events, or internal notification infrastructure.

```yaml
alerts:
  channels:
    - type: webhook
      config:
        url: https://internal-alerts.acme.example.com/tinaa
        headers:
          Authorization: Bearer my-internal-token
          X-Source: tinaa
```

Webhook payload schema:

```json
{
  "rule_name": "endpoint-down-production",
  "severity": "critical",
  "condition_type": "endpoint_unavailable",
  "message": "Endpoint / is unavailable in production",
  "details": {
    "endpoint_path": "/",
    "environment": "production",
    "last_status_code": 503
  },
  "product_id": "00000000-0000-0000-0000-000000000001",
  "product_name": "acme-web-app",
  "environment": "production",
  "triggered_at": "2026-03-21T10:30:00Z",
  "acknowledged": false,
  "resolved": false
}
```

---

## Alert lifecycle

```
TRIGGERED → ACKNOWLEDGED → RESOLVED
              ↑                ↓
              └── (auto-resolve when condition clears)
```

### TRIGGERED

An alert enters `triggered` state when a rule condition is met. Notifications are sent to all configured channels. The alert appears in the **Alerts** panel with a red badge.

### ACKNOWLEDGED

A team member clicks **Acknowledge** on the alert. This:
- Silences repeat notifications for the cooldown period.
- Records who acknowledged it and when.
- Signals to the team that someone is investigating.

### RESOLVED

An alert resolves when:
- **Auto-resolve**: the condition that triggered it clears (e.g. endpoint returns to 2xx, score recovers).
- **Manual resolve**: a team member clicks **Resolve** after confirming the issue is fixed.

When an alert resolves, a resolution notification is sent to the same channels that received the trigger notification.

---

## Cooldown periods

The **cooldown** prevents alert storms — repeated notifications for the same persistent condition. After an alert fires, TINAA waits the cooldown period before re-evaluating the condition. If the condition is still active after the cooldown, a new alert fires.

Recommended cooldown values:

| Alert type | Recommended cooldown |
|------------|---------------------|
| Endpoint down (production) | 5 minutes |
| Critical test failure | 5–15 minutes |
| Quality score drop | 30 minutes |
| Performance regression | 60 minutes |
| Score drop (staging) | 60 minutes |

Set very short cooldowns (1–5 minutes) only for critical production alerts where immediate re-notification is important. Long cooldowns (60+ minutes) reduce noise for non-urgent conditions.
