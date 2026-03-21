# Test Playbooks

A **playbook** is a declarative YAML file that describes a browser-based test journey. Each playbook contains an ordered list of steps (navigate, click, fill, assert, etc.) that TINAA's Playwright-backed executor runs against a target environment. Playbooks replace hand-written Playwright scripts with a structured, version-controllable, agent-readable format.

---

## What is a playbook?

A playbook is a declarative test plan — not imperative code. You describe *what* to do (click the checkout button) rather than *how* Playwright does it. This enables:

- **Auto-generation** — the TINAA Explorer agent can discover user journeys and produce playbooks automatically.
- **Reuse across environments** — the same playbook runs against staging and production; only the `base_url` changes.
- **Agent readability** — TINAA's AI agents can analyse, optimise, and regenerate playbooks as your application evolves.
- **Versioning** — YAML files live in your repository alongside your application code.

---

## Playbook YAML format — full annotated example

```yaml
# Playbook identity
name: user-checkout-journey         # unique identifier within the product
description: >
  Verifies the full authenticated checkout flow from product selection
  through order confirmation.
priority: critical                  # critical | high | medium | low
tags:
  - checkout
  - payment
  - smoke

# Trigger conditions — when this playbook runs automatically
trigger:
  on_deploy:                        # run when these environments receive a deployment
    - production
    - staging
  on_pr: true                       # run on every pull request
  schedule_cron: "0 6 * * *"       # nightly at 06:00 UTC
  on_change:                        # run when these file paths change in a PR
    - "src/checkout/**"
    - "src/payment/**"

# Variables — referenced in steps as ${variable_name}
variables:
  base_url: https://staging.acme.example.com
  test_email: qa@acme.example.com
  test_password: "{{env.QA_PASSWORD}}"  # resolved from environment variable

# Performance gate — run fails if any threshold is exceeded
performance_gates:
  total_duration_ms: 15000          # full playbook must complete within 15 s
  lcp_ms: 2500                      # Largest Contentful Paint <= 2500 ms
  fcp_ms: 1800                      # First Contentful Paint <= 1800 ms
  cls: 0.1                          # Cumulative Layout Shift <= 0.1
  inp_ms: 200                       # Interaction to Next Paint <= 200 ms
  max_network_failures: 0           # zero network errors permitted

# Global assertions applied after every step
assertions:
  no_console_errors: true           # fail if any console.error fires
  no_network_failures: true         # fail on 4xx/5xx responses
  max_accessibility_violations: 0   # zero new WCAG violations

# Setup steps — run before the main steps; not included in pass/fail count
setup:
  - action: set_viewport
    params:
      width: 1440
      height: 900

# Main steps
steps:
  - action: navigate
    description: Open the homepage
    params:
      url: ${base_url}/
    timeout_ms: 10000

  - action: assert_visible
    description: Confirm hero section is visible
    params:
      selector: "[data-testid='hero-section']"

  - action: click
    description: Navigate to products page
    params:
      selector: "nav a[href='/products']"

  - action: wait_for_navigation
    description: Wait for products page to load
    params: {}

  - action: assert_text
    description: Confirm products heading
    params:
      selector: "h1"
      text: "Our Products"

  - action: click
    description: Add first product to cart
    params:
      selector: "[data-testid='product-card']:first-child [data-testid='add-to-cart']"

  - action: navigate
    description: Open checkout
    params:
      url: ${base_url}/checkout

  - action: fill
    description: Enter email address
    params:
      selector: "input[name='email']"
      value: ${test_email}

  - action: fill
    description: Enter password
    params:
      selector: "input[name='password']"
      value: ${test_password}

  - action: click
    description: Submit sign-in form
    params:
      selector: "button[type='submit']"

  - action: assert_url
    description: Confirm redirect to checkout confirmation
    params:
      url_pattern: "/checkout/confirm"

  - action: screenshot
    description: Capture checkout confirmation page
    params:
      name: checkout-confirmation

  - action: assert_visible
    description: Confirm order summary is visible
    params:
      selector: "[data-testid='order-summary']"

  - action: assert_no_console_errors
    description: Verify no JavaScript errors occurred
    params: {}

  - action: assert_accessibility
    description: Check WCAG 2.1 AA compliance on checkout page
    params:
      standard: wcag21aa

# Teardown steps — always run, even after failures
teardown:
  - action: navigate
    params:
      url: ${base_url}/logout
    optional: true              # ignore failure if logout page is absent
```

---

## Available actions

### Navigation

| Action | Required params | Description |
|--------|-----------------|-------------|
| `navigate` | `url` | Navigate to a URL. Waits for `domcontentloaded`. |
| `wait_for_navigation` | *(none)* | Wait for a navigation triggered by a click. |
| `wait` | `ms` | Wait for a fixed duration in milliseconds. |

### Interaction

| Action | Required params | Description |
|--------|-----------------|-------------|
| `click` | `selector` | Click an element. Waits for it to be visible first. |
| `fill` | `selector`, `value` | Clear and fill a form input. |
| `type` | `selector`, `text` | Type text character by character (use for autocomplete). |
| `select` | `selector`, `value` | Select an `<option>` by value. |
| `press_key` | `key` | Press a keyboard key, e.g. `Enter`, `Tab`, `Escape`. |
| `hover` | `selector` | Hover over an element (triggers tooltip/dropdown). |
| `scroll` | `selector` or `x`, `y` | Scroll to element or coordinates. |
| `clear` | `selector` | Clear an input field. |
| `upload_file` | `selector`, `file_path` | Upload a file to a file input. |
| `set_viewport` | `width`, `height` | Resize the browser viewport. |
| `evaluate` | `expression` | Run a JavaScript expression in the browser context. |

### Assertions

| Action | Required params | Description |
|--------|-----------------|-------------|
| `assert_visible` | `selector` | Fail if element is not visible. |
| `assert_hidden` | `selector` | Fail if element is visible. |
| `assert_text` | `selector`, `text` | Fail if element's text does not match. |
| `assert_url` | `url_pattern` | Fail if current URL does not match the pattern (substring or regex). |
| `assert_title` | `title` | Fail if page title does not match. |
| `assert_no_console_errors` | *(none)* | Fail if any `console.error` was called since last step. |
| `assert_no_network_failures` | *(none)* | Fail if any 4xx/5xx requests were made since last step. |
| `assert_accessibility` | `standard` | Run axe-core accessibility audit. `standard`: `wcag21aa` (default), `wcag21a`, `wcag22aa`. |

### Utility

| Action | Required params | Description |
|--------|-----------------|-------------|
| `screenshot` | `name` | Capture a named screenshot. Automatically taken on step failure. |
| `group` | `steps` | Group related steps under a named block for reporting. |

---

## Variables and templating

Variables are defined in the `variables` block and referenced with `${variable_name}` in any string param value.

```yaml
variables:
  base_url: https://staging.acme.example.com
  user_email: test@example.com

steps:
  - action: navigate
    params:
      url: ${base_url}/login
  - action: fill
    params:
      selector: "#email"
      value: ${user_email}
```

### Environment variable injection

Reference OS environment variables with `{{env.VARIABLE_NAME}}`:

```yaml
variables:
  admin_password: "{{env.TINAA_TEST_ADMIN_PASSWORD}}"
```

### Built-in variables

| Variable | Value |
|----------|-------|
| `${base_url}` | Environment base URL (always available) |
| `${env_name}` | Environment name, e.g. `staging` |
| `${product_name}` | Product slug |
| `${run_id}` | Current test run UUID |

---

## Performance gates

Performance gates fail the playbook run if metrics exceed thresholds:

```yaml
performance_gates:
  total_duration_ms: 20000   # entire playbook must finish within 20 s
  lcp_ms: 2500               # LCP on any navigated page <= 2.5 s
  fcp_ms: 1800               # FCP on any navigated page <= 1.8 s
  cls: 0.1                   # CLS score <= 0.1
  inp_ms: 200                # INP <= 200 ms (Good threshold per Google)
  max_network_failures: 0    # no network errors
```

Gate failures appear as separate entries in the test results with the measured value alongside the threshold.

---

## Triggers

| Trigger | Description |
|---------|-------------|
| `on_deploy: [environment_names]` | Runs when a GitHub deployment targeting the listed environments is created. Requires GitHub App integration. |
| `on_pr: true` | Runs on every pull request targeting the default branch. |
| `schedule_cron: "0 3 * * *"` | Runs on a cron schedule (UTC). Standard 5-field cron syntax. |
| `on_change: [file_patterns]` | Runs when a PR modifies files matching the glob patterns. Reduces noise for unrelated changes. |

---

## Auto-generated vs manual playbooks

| Source | How created | Best for |
|--------|-------------|---------|
| `auto_generated` | TINAA Explorer agent crawls your app | Initial coverage, smoke tests |
| `manual` | Written by you in YAML | Complex flows, edge cases, authenticated journeys |
| `hybrid` | Auto-generated then hand-edited | Most production playbooks |

Auto-generated playbooks are created in the **Playbooks** tab when you click **Auto-discover**. They cover navigation paths discovered by the Explorer agent but will not include authentication flows or data entry sequences — add those as manual steps.

TINAA marks each playbook with its `source` field. You can promote an auto-generated playbook to `hybrid` by editing it in the dashboard.
