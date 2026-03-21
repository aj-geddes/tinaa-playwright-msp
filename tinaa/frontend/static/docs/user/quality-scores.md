# Quality Scores

The **Quality Score** is TINAA MSP's primary output — a single 0–100 number that summarises the health of your product across testing, performance, security, and accessibility. It drives deployment gate decisions and gives teams a shared language for quality conversations.

---

## What the score represents

A quality score of 100 means: all tests pass, pages load within budget, security headers are present, and there are no accessibility violations. The score degrades proportionally as any component worsens. The score is recomputed after every test run and after every monitoring cycle.

---

## Weight breakdown

| Component | Weight | What it reflects |
|-----------|--------|-----------------|
| **Test Health** | 40% | Whether your automated test suite is passing, broad, fresh, and stable |
| **Performance** | 30% | Whether your pages load fast and your endpoints respond within budget |
| **Security Posture** | 15% | Whether standard security protections are in place |
| **Accessibility** | 15% | Whether your product is usable by people with disabilities |

The weights are fixed in the default configuration. Enterprise installations can customise them via `QualityWeights` in the API.

---

## Grade mapping

| Score range | Grade | Interpretation |
|-------------|-------|----------------|
| 95–100 | A+ | Excellent — production ready, deploy with confidence |
| 85–94 | A | Good — minor improvements available but not blocking |
| 70–84 | B | Acceptable — several issues to address this sprint |
| 55–69 | C | Needs attention — quality gate likely failing |
| 40–54 | D | Significant problems — investigate before shipping |
| 0–39 | F | Critical issues — deployment blocked |

By default, the quality gate minimum is **80** (grade B or better). Configure this threshold in `.tinaa.yml` under `quality_gates.default.min_score`.

---

## How each component is calculated

### Test Health (40%)

Test Health combines four sub-metrics:

| Sub-metric | Weight within Test Health | Formula |
|------------|--------------------------|---------|
| Pass rate | 40% | `passed_tests / total_tests * 100` |
| Coverage breadth | 30% | `journeys_with_tests / journeys_discovered * 100` |
| Test freshness | 20% | `100 - (avg_test_age_days / 30 * 100)`, clamped 0–100 |
| Regression management | 10% | `regressions_resolved / regressions_detected * 100` |

**Example**: A product with 48/50 tests passing (96%), 8/10 journeys covered (80%), average test age 10 days (freshness 67%), and 1 unresolved regression out of 2 detected (50%):

```
Test Health = 96*0.40 + 80*0.30 + 67*0.20 + 50*0.10
            = 38.4 + 24.0 + 13.4 + 5.0
            = 80.8
```

### Performance (30%)

Performance combines four sub-metrics:

| Sub-metric | Weight within Performance | Formula |
|------------|--------------------------|---------|
| Endpoint budget compliance | 30% | `endpoints_within_budget / endpoints_total * 100` |
| Web Vitals | 30% | Average of available vitals scores (LCP, FCP, CLS, response time) |
| Availability | 25% | `(availability_percent / availability_target) * 100` |
| Error rate | 15% | `100` if below target, else `target_rate / actual_rate * 100` |

Web Vitals scoring uses a linear degradation model: 100 at or below budget, degrading to 0 at 2× the budget.

**Web Vitals thresholds used by default:**

| Vital | Good (100) | Poor (0) |
|-------|-----------|---------|
| LCP | ≤ 2500 ms | ≥ 5000 ms |
| FCP | ≤ 1800 ms | ≥ 3600 ms |
| CLS | ≤ 0.1 | ≥ 0.2 |
| Response time | ≤ 500 ms | ≥ 1000 ms |

### Security Posture (15%)

| Sub-metric | Weight within Security |
|------------|------------------------|
| HTTPS | 20% |
| Security headers | 30% |
| TLS grade | 20% |
| Mixed content | 15% |
| Cookie / form security | 15% |

The six security headers checked: `Content-Security-Policy`, `X-Frame-Options`, `X-Content-Type-Options`, `Strict-Transport-Security`, `Referrer-Policy`, `Permissions-Policy`. Each missing header reduces the headers sub-score by ~17 points.

TLS grade mapping: A+ → 100, A → 90, B → 70, C → 50, D → 30, F → 0.

### Accessibility (15%)

| Sub-metric | Weight within Accessibility | Penalty per violation |
|------------|-----------------------------|-----------------------|
| Critical violations | 30% | −25 points each |
| Serious violations | 25% | −15 points each |
| Moderate violations | 20% | −8 points each |
| Alt text coverage | 15% | Ratio of images with alt text |
| Keyboard navigability | 10% | 0 or 100 (binary) |

Violations are detected by running [axe-core](https://github.com/dequelabs/axe-core) inside the Playwright browser context during `assert_accessibility` steps.

---

## Quality gates and deployment decisions

When TINAA is integrated with GitHub via the GitHub App, it posts a **deployment status** to your GitHub deployment event. The status is:

- **success** — quality score >= `min_score` AND no critical test failures AND performance regression within limits.
- **failure** — any gate condition not met.

This integrates with GitHub's **deployment protection rules** to block merges or deployments when quality is insufficient.

Gate configuration in `.tinaa.yml`:

```yaml
quality_gates:
  default:
    min_score: 80
    no_critical_failures: true
    max_performance_regression_percent: 20
    max_new_accessibility_violations: 0
  pre-production:
    min_score: 90               # stricter gate for production-bound changes
    no_critical_failures: true
    max_performance_regression_percent: 10
    max_new_accessibility_violations: 0
```

---

## Tips to improve each component

### Improve Test Health

- Fix failing tests before writing new ones. One failing test at 100 total is 99% pass rate; at 10 total it is 90%.
- Run **Auto-discover** to find uncovered user journeys and generate baseline playbooks.
- Update playbooks when the UI changes rather than deleting and recreating — preserves history.
- Keep test age below 30 days: TINAA considers playbooks "stale" after 30 days without a run.

### Improve Performance

- Add performance budgets to your endpoints. Without budgets, TINAA cannot calculate budget compliance.
- Optimise LCP by ensuring the largest visible element (hero image, heading) loads from cache or CDN.
- Set explicit `width` and `height` on images to eliminate CLS from layout shifts.
- Use HTTP/2, enable compression, and reduce render-blocking scripts to improve FCP.
- Enable uptime monitoring on all production endpoints to catch availability degradations quickly.

### Improve Security Posture

- Enable all six security headers. Most web frameworks have middleware for this (e.g. `helmet` in Express, `SecurityMiddleware` in Django).
- Upgrade to TLS 1.3 and obtain an A+ TLS grade via [SSL Labs](https://www.ssllabs.com/ssltest/).
- Audit your HTML for mixed-content resources (`http://` URLs inside `https://` pages).
- Ensure all forms POST to `https://` URLs.

### Improve Accessibility

- Treat every critical violation as a P0 bug — they block users with disabilities entirely.
- Run `assert_accessibility` in your checkout and sign-in playbooks where violations have the most impact.
- Add `alt` text to every meaningful image. Use `alt=""` for decorative images to suppress screen reader announcement.
- Test keyboard navigation by tabbing through all interactive elements in the browser.
- Install the axe DevTools browser extension for immediate feedback during development.
