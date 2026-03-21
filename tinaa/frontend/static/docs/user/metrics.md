# Metrics & Monitoring

TINAA MSP continuously collects performance and availability metrics from your registered endpoints. These metrics feed the Performance component of the quality score, power anomaly detection, and give you time-series charts for trend analysis.

---

## Metrics collected

TINAA records the following metrics for every monitoring cycle and every test run:

| Metric | Type | Description |
|--------|------|-------------|
| `response_time_ms` | Float | Time from request initiation to full response body received |
| `status_code` | Integer | HTTP status code returned by the endpoint |
| `availability` | Boolean | Whether the endpoint returned a 2xx status code |
| `lcp_ms` | Float | Largest Contentful Paint — time to largest visible element |
| `fcp_ms` | Float | First Contentful Paint — time to first content on screen |
| `cls` | Float | Cumulative Layout Shift — visual stability score |
| `inp_ms` | Float | Interaction to Next Paint — responsiveness to user input |
| `ttfb_ms` | Float | Time to First Byte — server response latency |
| `error_rate_percent` | Float | Percentage of requests returning 4xx or 5xx in the last interval |

Web Vitals (`lcp_ms`, `fcp_ms`, `cls`, `inp_ms`) are only collected for `page`-type endpoints and only during full Playwright browser sessions (not lightweight HTTP polls).

---

## Understanding baselines

### How baselines are established

After TINAA has collected at least **7 days** of monitoring data for an endpoint, it computes a **baseline** — a statistical model of normal behaviour:

- **Baseline response time**: rolling median of the last 7-day window (percentile P50).
- **Baseline P95**: the 95th percentile response time — the threshold below which 95% of requests complete.
- **Baseline availability**: rolling average availability over the last 7 days.

Baselines are stored in the database and updated daily. The **Metrics** tab shows baseline overlaid on current metric charts as a dashed reference line.

### How regressions are detected

TINAA's APM engine runs anomaly detection on every incoming metric point:

1. **Response time regression**: if current value exceeds `baseline_p95 * 1.5`, TINAA flags an anomaly.
2. **Availability drop**: if availability falls below `baseline_availability - 5%`, an anomaly fires.
3. **Error rate spike**: if `error_rate_percent > 5` and it was below 1% in the baseline window, an anomaly fires.

Anomalies are surfaced as alerts (see [Alerts & Notifications](alerts.md)) and can optionally trigger an automatic test run to confirm whether a functional regression has also occurred.

---

## Web Vitals explained

Web Vitals are Google's metrics for user experience. TINAA collects them for every `page`-type endpoint using Playwright's performance APIs.

### Largest Contentful Paint (LCP)

**What it measures**: Time from navigation start until the largest visible content element (image, video poster, or text block) finishes rendering.

**Why it matters**: LCP is the primary measure of perceived load speed. A slow LCP means users wait a long time before seeing meaningful content.

| Rating | Threshold |
|--------|-----------|
| Good | ≤ 2500 ms |
| Needs improvement | 2500–4000 ms |
| Poor | > 4000 ms |

**Common causes of poor LCP**: large hero images without CDN, render-blocking CSS/JS, slow server response (high TTFB).

### First Contentful Paint (FCP)

**What it measures**: Time until the browser renders any content — text, image, canvas, or SVG.

**Why it matters**: FCP gives users the first signal that the page is loading. Poor FCP means users see a blank screen for too long.

| Rating | Threshold |
|--------|-----------|
| Good | ≤ 1800 ms |
| Needs improvement | 1800–3000 ms |
| Poor | > 3000 ms |

**Common causes of poor FCP**: render-blocking scripts in `<head>`, slow DNS resolution, no compression.

### Cumulative Layout Shift (CLS)

**What it measures**: Total amount of unexpected layout shift during the page's lifetime. A score of 0 is perfect; 0.25+ is poor.

**Why it matters**: Layout shifts cause users to click the wrong element when content jumps. Especially problematic on mobile.

| Rating | Threshold |
|--------|-----------|
| Good | ≤ 0.1 |
| Needs improvement | 0.1–0.25 |
| Poor | > 0.25 |

**Common causes of poor CLS**: images without explicit `width`/`height`, late-loading ads, fonts causing text reflow.

### Interaction to Next Paint (INP)

**What it measures**: The latency from user interaction (click, key press, tap) to the browser's next visual update. Replaced First Input Delay (FID) as a Core Web Vital in March 2024.

**Why it matters**: INP measures whether the page feels responsive to user actions throughout the whole visit, not just on first interaction.

| Rating | Threshold |
|--------|-----------|
| Good | ≤ 200 ms |
| Needs improvement | 200–500 ms |
| Poor | > 500 ms |

**Common causes of poor INP**: long JavaScript tasks on the main thread, expensive event handlers, unoptimised React re-renders.

---

## Endpoint monitoring

### Monitoring intervals

Each environment has a configurable monitoring interval:

| Interval | Use case | Resource cost |
|----------|----------|---------------|
| 60 s | Critical production APIs where downtime SLA is 1 minute | High |
| 300 s (5 min) | Standard production monitoring (recommended default) | Moderate |
| 900 s (15 min) | Staging and preview environments | Low |
| 3600 s (1 h) | Development environments | Minimal |

### Health status values

| Status | Meaning |
|--------|---------|
| `healthy` | Last N checks passed with 2xx status and within response-time budget |
| `degraded` | Responding but response time exceeds budget or error rate elevated |
| `down` | Last check returned a non-2xx status or timed out |
| `unknown` | No monitoring data yet (newly added endpoint) |

### Monitoring check procedure

For each monitoring cycle, TINAA:

1. Makes an HTTP GET request (or the configured method) to `base_url + path`.
2. Records status code, response time, and TTFB.
3. For `page`-type endpoints with `collect_vitals: true`, also runs a headless Playwright navigation to capture LCP, FCP, CLS, INP.
4. Compares against baseline; flags anomalies if thresholds are breached.
5. Updates the endpoint health status.
6. Stores the metric point in the TimescaleDB hypertable.

---

## Reading metric trends

### Time-series charts

The Metrics tab shows line charts for each registered endpoint with:
- **Current value** (solid line)
- **Baseline** (dashed line, available after 7 days)
- **Budget / threshold** (dotted horizontal line, if configured)
- **Anomaly markers** (red dots on the timeline)

Select the time range with the date picker: 1h, 6h, 24h, 7d, 30d, 90d.

### Metric aggregations

| Aggregation | Meaning |
|-------------|---------|
| P50 (median) | Typical response — 50% of requests are faster than this |
| P95 | Tail latency — 95% of requests complete within this time |
| P99 | Worst-case latency — useful for SLA compliance tracking |
| Availability % | Percentage of successful (2xx) checks in the period |
| Error rate % | Percentage of failed (4xx/5xx) checks |

Switch between aggregations using the chart toolbar.

### Comparing environments

Select multiple environments using the **Compare environments** toggle to overlay production and staging on the same chart. Performance differences between environments often reveal infrastructure configuration issues.
