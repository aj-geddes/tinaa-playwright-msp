---
layout: page
title: "Quality Scores"
description: "How TINAA MSP computes the composite 0-100 quality score, deployment gates, and how to improve your grade."
---

# Quality Scores

The TINAA MSP quality score is a single composite number from **0 to 100** that represents the overall health of an application across four dimensions: test coverage and reliability, runtime performance, security posture, and accessibility compliance. It is designed to give teams one authoritative signal they can act on — and defend to stakeholders.

---

## What Is the Quality Score?

The quality score fuses test and APM data into a single number that:

- Tracks over time so you can see if quality is improving or degrading
- Breaks down into four labelled components so you know exactly what to fix
- Maps to a letter grade so it is easy to communicate to non-technical stakeholders
- Can block deployments when it falls below a configured threshold

---

## Component Breakdown

The score is a weighted sum of four component scores, each computed from 0 to 100.

```
Quality Score = (Test Health × 0.40)
              + (Performance × 0.30)
              + (Security    × 0.15)
              + (Accessibility × 0.15)
```

### Test Health (40%)

Measures how well your automated test suite protects the application.

| Sub-component | Weight within Test Health | What it measures |
|---|---|---|
| Pass rate | 40% | Fraction of test runs that pass: `passed / total × 100` |
| Coverage breadth | 30% | Fraction of discovered user journeys that have at least one test |
| Test freshness | 20% | How recently tests were updated relative to a 30-day threshold |
| Regression detection | 10% | Fraction of detected regressions that have been resolved |

**Formula:**

```
TestHealth = (PassRate × 0.40)
           + (CoverageBreadth × 0.30)
           + (Freshness × 0.20)
           + (RegressionManagement × 0.10)
```

Where:

- `PassRate = passed_tests / total_tests × 100`
- `CoverageBreadth = journeys_with_tests / total_journeys_discovered × 100`
- `Freshness = clamp(100 − avg_test_age_days / 30 × 100, 0, 100)`
- `RegressionManagement = regressions_resolved / regressions_detected × 100`

### Performance Health (30%)

Measures how fast and available your application is.

| Sub-component | Weight within Performance | What it measures |
|---|---|---|
| Endpoint budget compliance | 30% | Fraction of endpoints responding within their configured time budget |
| Web Vitals | 30% | Average score across LCP, CLS, FCP, and average response time vs budgets |
| Availability | 25% | Uptime percentage vs the 99.9% target |
| Error rate | 15% | HTTP error rate vs the 1.0% target |

Web Vitals scoring uses a linear degradation formula:

- Score = 100 when actual <= budget
- Score degrades linearly to 0 at 2x the budget
- LCP budget: 2500 ms / CLS budget: 0.10 / FCP budget: 1800 ms

### Security Posture (15%)

Measures how well the application protects users and data.

| Sub-component | Weight within Security | What it checks |
|---|---|---|
| HTTPS | 20% | All endpoints served over TLS |
| Security headers | 30% | Presence of 6 recommended headers (CSP, X-Frame-Options, X-Content-Type-Options, HSTS, Referrer-Policy, Permissions-Policy) |
| TLS grade | 20% | SSL Labs-style grade (A+ = 100, A = 90, B = 70, C = 50, D = 30, F = 0) |
| Mixed content | 15% | HTTP resources on HTTPS pages (−10 points per occurrence) |
| Cookie and form security | 15% | Cookie security flags, forms not submitting over HTTP (−15 per insecure form) |

### Accessibility (15%)

Measures WCAG 2.1 compliance and usability for users with disabilities.

| Sub-component | Weight within Accessibility | What it checks |
|---|---|---|
| Critical violations | 30% | WCAG failures that completely block access (−25 per violation) |
| Serious violations | 25% | WCAG failures that significantly impair access (−15 per violation) |
| Moderate violations | 20% | WCAG failures that cause friction (−8 per violation) |
| Alt text coverage | 15% | Fraction of images with meaningful alt attributes |
| Keyboard navigability | 10% | All interactive elements reachable and operable by keyboard |

---

## Grade Scale

| Grade | Score range | What it means |
|---|---|---|
| **A+** | 95 – 100 | Exceptional. All components excellent. |
| **A** | 85 – 94 | Strong. Minor improvements available. |
| **B** | 70 – 84 | Good. Some components need attention. |
| **C** | 55 – 69 | Acceptable. Significant improvements needed. |
| **D** | 40 – 54 | Poor. Multiple components require immediate work. |
| **F** | 0 – 39 | Critical. Application quality is unacceptable for production. |

---

## Deployment Gates

A deployment gate prevents a deployment from proceeding if the product quality score drops below a configured threshold. Gates are evaluated against the quality score measured on the PR's preview environment or the post-deploy environment.

### Configuring Gates in `.tinaa.yml`

Add a `.tinaa.yml` file to the root of your repository to configure per-product gates:

```yaml
# .tinaa.yml
product: checkout-service

quality_gates:
  # Minimum composite score required to pass the gate
  min_score: 75

  # Block if any single component drops below its threshold
  components:
    test_health: 70
    performance: 65
    security: 80
    accessibility: 60

  # Block if score drops by more than this delta compared to the main branch
  max_score_drop: 5

  # Which environments trigger gate evaluation
  environments:
    - staging
    - production

  # Set to "warn" to report failures without blocking the deployment
  # Set to "block" to hard-fail the CI/CD pipeline
  mode: block
```

### How Gates Work in CI/CD

1. TINAA detects the GitHub deployment event
2. TINAA runs the smoke test suite against the deployment URL
3. TINAA evaluates the resulting quality score against the configured gate
4. If the gate fails, TINAA posts a failing GitHub Check Run on the PR
5. With `mode: block`, the PR cannot be merged until the check passes

```yaml
# GitHub Actions integration example
- name: TINAA Quality Gate
  run: |
    curl -f -X POST $TINAA_URL/api/v1/products/$PRODUCT_SLUG/quality-gate \
      -H "X-API-Key: $TINAA_API_KEY" \
      -H "Content-Type: application/json" \
      -d '{"environment": "staging", "commit_sha": "${{ github.sha }}"}'
```

---

## Trend Analysis and Historical Tracking

TINAA records a quality score snapshot every time a test suite runs. The dashboard shows:

- **Current score** — the most recent computed score
- **7-day trend** — delta from 7 days ago (+/−)
- **30-day trend** — delta from 30 days ago (+/−)
- **Score history chart** — time-series plot with component breakdown

Trend direction is reported as:

| Direction | Condition |
|---|---|
| `improving` | Score increased by more than 1 point in the last 7 days |
| `stable` | Score changed by 1 point or less |
| `degrading` | Score dropped by more than 1 point in the last 7 days |

Access historical scores via the API:

```bash
GET /api/v1/products/{product_id}/quality-history?days=30
```

---

## Improving Your Score

### Improving Test Health (40% of score)

- Fix failing tests first — a single failing test can cut pass rate significantly
- Add playbooks for uncovered journeys — the dashboard lists journeys without tests
- Update playbooks older than 30 days — stale tests score lower on freshness
- Resolve open regressions — unresolved regressions reduce the regression management sub-score

### Improving Performance (30% of score)

- Address endpoints exceeding their response time budget (check **Metrics** for P95 data)
- Optimise your Largest Contentful Paint element (usually a hero image or large text block)
- Set explicit `width` and `height` on images to eliminate Cumulative Layout Shift
- Investigate any endpoints with availability below 99.9%
- Reduce your HTTP error rate below 1%

### Improving Security (15% of score)

Add the six recommended response headers to your server configuration. In Express/Node:

```javascript
import helmet from 'helmet';
app.use(helmet());  // sets CSP, X-Frame-Options, HSTS, X-Content-Type-Options, Referrer-Policy
```

In nginx:

```nginx
add_header Content-Security-Policy "default-src 'self'" always;
add_header X-Frame-Options "SAMEORIGIN" always;
add_header X-Content-Type-Options "nosniff" always;
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header Permissions-Policy "geolocation=(), microphone=(), camera=()" always;
```

Fix mixed content by ensuring all sub-resources (images, scripts, fonts, API calls) use `https://` URLs.

### Improving Accessibility (15% of score)

- Fix critical violations first — each one costs 25 points in the accessibility sub-score
- Add `alt` attributes to all meaningful images (`alt=""` for decorative images)
- Ensure all form inputs have associated `<label>` elements
- Test keyboard navigation: every interactive element must be reachable with Tab and activatable with Enter/Space
- Use the TINAA `assert_accessibility` step in your playbooks to catch new violations before they ship

---

## Fetching Scores via the API

```bash
# Current score for a product (all environments)
GET /api/v1/products/{product_id}/quality-score

# Score scoped to a specific environment
GET /api/v1/products/{product_id}/quality-score?environment=production

# Full quality report with recommendations
GET /api/v1/products/{product_id}/quality-report
```

**Example response:**

```json
{
  "score": 87.4,
  "grade": "A",
  "environment": "production",
  "components": {
    "test_health":       { "score": 91.0, "weight": 0.40, "weighted_score": 36.4 },
    "performance_health":{ "score": 84.0, "weight": 0.30, "weighted_score": 25.2 },
    "security_posture":  { "score": 88.0, "weight": 0.15, "weighted_score": 13.2 },
    "accessibility":     { "score": 82.0, "weight": 0.15, "weighted_score": 12.3 }
  },
  "trend": "improving",
  "trend_7d": 2,
  "trend_30d": 5,
  "recommendations": [
    "Add alt text to 3 images on /checkout to fix accessibility violations.",
    "Optimise /api/search to bring P95 response time below 400ms."
  ]
}
```

---

## Next Steps

- [APM and Metrics](metrics.md) — the raw data behind the performance component
- [Alerts](alerts.md) — get notified when the quality score drops below a threshold
- [Configuration Reference](configuration.md) — configure quality gate thresholds in `.tinaa.yml`
- [MCP Integration](mcp-integration.md) — query quality scores from Claude
