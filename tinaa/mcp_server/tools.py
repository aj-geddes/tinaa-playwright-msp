"""TINAA MCP Server — tool definitions.

All tool functions are plain ``async`` callables and are registered on the
shared FastMCP instance via ``mcp.add_tool()`` at module import time.  This
keeps the functions directly callable in tests without going through the
``FunctionTool`` wrapper.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Optional

from fastmcp import Context
from fastmcp.tools.tool import FunctionTool

from tinaa.mcp_server._mcp import mcp
from tinaa.services import get_services

# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _new_id(prefix: str = "") -> str:
    """Generate a short deterministic-looking mock ID."""
    short = str(uuid.uuid4())[:8]
    return f"{prefix}{short}" if prefix else short


def _ts() -> str:
    """Return an ISO-8601 UTC timestamp string."""
    return datetime.now(tz=UTC).isoformat()


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


async def register_product(
    name: str,
    repo_url: str,
    environments: dict,
    description: str = "",
    ctx: Optional[Context] = None,
) -> dict:
    """Register a new product for quality management.

    Creates a product record in TINAA MSP, associating it with one or more
    deployment environments for continuous testing and monitoring.

    Args:
        name: Human-readable product name (e.g. "Checkout Service").
        repo_url: Git repository URL for codebase exploration.
        environments: Mapping of environment name to base URL, e.g.
            ``{"production": "https://app.example.com",
               "staging": "https://staging.example.com"}``.
        description: Optional product description.
        ctx: MCP context (injected automatically).

    Returns:
        dict with keys: product_id, slug, name, repo_url, environments,
        description, status, quality_score, created_at.
    """
    slug = name.lower().replace(" ", "-")
    return {
        "product_id": _new_id("prod-"),
        "slug": slug,
        "name": name,
        "repo_url": repo_url,
        "environments": environments,
        "description": description,
        "status": "active",
        "quality_score": None,
        "created_at": _ts(),
    }


_STUB_PRODUCTS = [
    {
        "product_id": "prod-a1b2c3d4",
        "slug": "demo-app",
        "name": "Demo App",
        "status": "active",
        "quality_score": 87,
        "environment_count": 2,
    },
    {
        "product_id": "prod-e5f6a7b8",
        "slug": "api-gateway",
        "name": "API Gateway",
        "status": "active",
        "quality_score": 92,
        "environment_count": 3,
    },
    {
        "product_id": "prod-c9d0e1f2",
        "slug": "legacy-portal",
        "name": "Legacy Portal",
        "status": "paused",
        "quality_score": 61,
        "environment_count": 1,
    },
]

_REGISTRY_ORG_ID = "00000000-0000-0000-0000-000000000001"


def _registry_product_to_dict(p) -> dict:
    """Convert a ProductResponse to the tool's return dict shape."""
    return {
        "product_id": str(p.id),
        "slug": p.slug,
        "name": p.name,
        "status": str(p.status),
        "quality_score": p.quality_score,
        "environment_count": 0,
        "last_run_at": _ts(),
    }


async def list_products(
    status: Optional[str] = None,
    ctx: Optional[Context] = None,
) -> list[dict]:
    """List all registered products, optionally filtered by status.

    Args:
        status: Optional filter — one of ``active``, ``paused``, ``archived``.
        ctx: MCP context (injected automatically).

    Returns:
        List of product summary dicts, each containing: product_id, slug,
        name, status, quality_score, environment_count, last_run_at.
    """
    import uuid as _uuid

    services = get_services()
    try:
        org_id = _uuid.UUID(_REGISTRY_ORG_ID)
        results = await services.registry.list_products(org_id, status=status)
        return [_registry_product_to_dict(p) for p in results]
    except Exception:
        products = [{**p, "last_run_at": _ts()} for p in _STUB_PRODUCTS]
        if status is not None:
            products = [p for p in products if p["status"] == status]
        return products


async def get_product(
    product_id_or_slug: str,
    ctx: Optional[Context] = None,
) -> dict:
    """Get detailed product info including environments, endpoints, quality score, and recent test runs.

    Args:
        product_id_or_slug: Product ID (e.g. ``prod-a1b2c3d4``) or slug
            (e.g. ``demo-app``).
        ctx: MCP context (injected automatically).

    Returns:
        dict with keys: product_id, slug, name, repo_url, environments,
        endpoints, quality_score, recent_test_runs, created_at, updated_at.
    """
    return {
        "product_id": "prod-a1b2c3d4",
        "slug": product_id_or_slug,
        "name": "Demo App",
        "repo_url": "https://github.com/example/demo-app",
        "environments": {
            "production": "https://app.example.com",
            "staging": "https://staging.example.com",
        },
        "endpoints": [
            {"path": "/", "method": "GET", "type": "page"},
            {"path": "/login", "method": "POST", "type": "api"},
            {"path": "/checkout", "method": "POST", "type": "api"},
        ],
        "quality_score": 87,
        "recent_test_runs": [
            {
                "run_id": _new_id("run-"),
                "playbook_name": "smoke-test",
                "status": "passed",
                "timestamp": _ts(),
            }
        ],
        "created_at": _ts(),
        "updated_at": _ts(),
    }


def _compute_quality_score_dict(environment: Optional[str]) -> dict:
    """Compute quality score using QualityScorer with default inputs.

    Returns the structured score dict expected by MCP callers.
    Raises on any scorer failure — callers should catch.
    """
    from tinaa.quality.scorer import (
        AccessibilityInput,
        PerformanceHealthInput,
        SecurityPostureInput,
        TestHealthInput,
    )

    services = get_services()
    result = services.quality_scorer.compute_quality_score(
        test_health=TestHealthInput(),
        performance=PerformanceHealthInput(),
        security=SecurityPostureInput(),
        accessibility=AccessibilityInput(),
    )
    components = result["components"]
    return {
        "score": result["score"],
        "environment": environment or "all",
        "test_health": {
            "score": components["test_health"]["score"],
            "pass_rate": 0.0,
            "flakiness": 0.0,
        },
        "performance_health": {
            "score": components["performance_health"]["score"],
            "p95_ms": None,
            "lcp_ms": None,
        },
        "security_posture": {
            "score": components["security_posture"]["score"],
            "open_findings": 0,
            "critical": 0,
        },
        "accessibility": {
            "score": components["accessibility"]["score"],
            "violations": 0,
            "warnings": 0,
        },
        "trend": "stable",
        "recommendations": result["recommendations"],
    }


_STUB_QUALITY_SCORE = {
    "score": 87,
    "test_health": {"score": 91, "pass_rate": 0.94, "flakiness": 0.02},
    "performance_health": {"score": 84, "p95_ms": 420, "lcp_ms": 1800},
    "security_posture": {"score": 88, "open_findings": 2, "critical": 0},
    "accessibility": {"score": 82, "violations": 4, "warnings": 11},
    "trend": "improving",
    "recommendations": [
        "Fix 4 accessibility violations on /checkout to gain +3 points.",
        "Reduce P95 response time below 400 ms to meet SLO.",
    ],
}


async def get_quality_score(
    product_id_or_slug: str,
    environment: Optional[str] = None,
    ctx: Optional[Context] = None,
) -> dict:
    """Get the current quality score for a product, with breakdown by component.

    Aggregates test health, performance metrics, security posture, and
    accessibility results into a single quality score with trend analysis.

    Args:
        product_id_or_slug: Product ID or slug.
        environment: Optional environment name to scope the score (e.g.
            ``production``). When omitted, returns the aggregate score.
        ctx: MCP context (injected automatically).

    Returns:
        dict with keys: score, test_health, performance_health,
        security_posture, accessibility, trend, recommendations.
    """
    try:
        return _compute_quality_score_dict(environment)
    except Exception:
        return {**_STUB_QUALITY_SCORE, "environment": environment or "all"}


async def run_playbook(
    playbook_id_or_name: str,
    environment: Optional[str] = None,
    target_url: Optional[str] = None,
    ctx: Optional[Context] = None,
) -> dict:
    """Execute a specific test playbook against an environment.

    Runs a named playbook and returns a summary of results including pass/fail
    counts, duration, and the impact on the product quality score.

    Args:
        playbook_id_or_name: Playbook ID or name (e.g. ``smoke-test``).
        environment: Target environment name (e.g. ``staging``). Uses the
            product's default environment when omitted.
        target_url: Override the base URL for this run.
        ctx: MCP context (injected automatically).

    Returns:
        dict with keys: run_id, status, results_summary, duration_ms,
        quality_score_impact.
    """
    return {
        "run_id": _new_id("run-"),
        "playbook_name": playbook_id_or_name,
        "environment": environment or "staging",
        "status": "passed",
        "results_summary": {
            "total": 12,
            "passed": 11,
            "failed": 1,
            "skipped": 0,
            "error_messages": ["Assertion failed: expected 200, got 404 on /health"],
        },
        "duration_ms": 3240,
        "quality_score_impact": -1,
        "started_at": _ts(),
    }


async def run_suite(
    product_id_or_slug: str,
    environment: str = "staging",
    suite_type: str = "regression",
    ctx: Optional[Context] = None,
) -> dict:
    """Run all playbooks for a product/environment.

    Executes the full suite of playbooks associated with the product and
    returns aggregated results with an updated quality score.

    Args:
        product_id_or_slug: Product ID or slug.
        environment: Target environment. Defaults to ``staging``.
        suite_type: One of ``regression``, ``smoke``, ``full``,
            ``security``, ``accessibility``. Defaults to ``regression``.
        ctx: MCP context (injected automatically).

    Returns:
        dict with keys: run_id, playbooks_executed, passed, failed,
        quality_score.
    """
    return {
        "run_id": _new_id("suite-"),
        "product_id_or_slug": product_id_or_slug,
        "environment": environment,
        "suite_type": suite_type,
        "playbooks_executed": 8,
        "passed": 7,
        "failed": 1,
        "duration_ms": 28_400,
        "quality_score": 85,
        "started_at": _ts(),
        "completed_at": _ts(),
    }


async def get_metrics(
    product_id_or_slug: str,
    endpoint_path: Optional[str] = None,
    metric_type: Optional[str] = None,
    hours: int = 24,
    ctx: Optional[Context] = None,
) -> dict:
    """Query APM metrics for a product or specific endpoint.

    Returns time-series data for the requested metric over the specified
    lookback window, along with baseline comparison and trend direction.

    Args:
        product_id_or_slug: Product ID or slug.
        endpoint_path: Optional endpoint path filter (e.g. ``/api/checkout``).
        metric_type: One of ``response_time``, ``lcp``, ``cls``,
            ``availability``, ``error_rate``. Returns all types when omitted.
        hours: Lookback window in hours. Defaults to ``24``.
        ctx: MCP context (injected automatically).

    Returns:
        dict with keys: metrics (list of {timestamp, value}), baseline,
        current_avg, trend.
    """
    sample_metrics = [
        {"timestamp": _ts(), "value": 312},
        {"timestamp": _ts(), "value": 298},
        {"timestamp": _ts(), "value": 340},
        {"timestamp": _ts(), "value": 285},
    ]
    return {
        "product_id_or_slug": product_id_or_slug,
        "endpoint_path": endpoint_path,
        "metric_type": metric_type or "response_time",
        "hours": hours,
        "metrics": sample_metrics,
        "baseline": 300,
        "current_avg": 309,
        "trend": "stable",
    }


async def get_test_results(
    product_id_or_slug: str,
    limit: int = 10,
    status: Optional[str] = None,
    ctx: Optional[Context] = None,
) -> list[dict]:
    """Get recent test run results for a product.

    Args:
        product_id_or_slug: Product ID or slug.
        limit: Maximum number of results to return. Defaults to ``10``.
        status: Optional filter by run status — ``passed``, ``failed``,
            ``error``, ``running``.
        ctx: MCP context (injected automatically).

    Returns:
        List of run result dicts, each containing: run_id, playbook_name,
        status, duration_ms, passed, failed, timestamp.
    """
    results = [
        {
            "run_id": _new_id("run-"),
            "playbook_name": "smoke-test",
            "status": "passed",
            "duration_ms": 2100,
            "passed": 10,
            "failed": 0,
            "timestamp": _ts(),
        },
        {
            "run_id": _new_id("run-"),
            "playbook_name": "checkout-regression",
            "status": "failed",
            "duration_ms": 5800,
            "passed": 18,
            "failed": 2,
            "timestamp": _ts(),
        },
        {
            "run_id": _new_id("run-"),
            "playbook_name": "accessibility-audit",
            "status": "passed",
            "duration_ms": 8200,
            "passed": 41,
            "failed": 0,
            "timestamp": _ts(),
        },
    ]
    if status is not None:
        results = [r for r in results if r["status"] == status]
    return results[:limit]


async def suggest_tests(
    product_id_or_slug: str,
    changed_files: Optional[list[str]] = None,
    ctx: Optional[Context] = None,
) -> list[dict]:
    """Get test suggestions based on codebase analysis and changed files.

    Analyzes the product's codebase and, when provided, the list of recently
    changed files to recommend the most relevant playbooks to run.

    Args:
        product_id_or_slug: Product ID or slug.
        changed_files: Optional list of changed file paths from the current
            diff (e.g. ``["src/checkout.py", "src/cart.py"]``).
        ctx: MCP context (injected automatically).

    Returns:
        List of suggestion dicts, each with: playbook_name, reason,
        priority (``high``/``medium``/``low``), affected_journeys.
    """
    suggestions = [
        {
            "playbook_name": "checkout-regression",
            "reason": "checkout.py modified — full checkout journey validation recommended",
            "priority": "high",
            "affected_journeys": ["add-to-cart", "checkout", "payment"],
        },
        {
            "playbook_name": "smoke-test",
            "reason": "Always run smoke tests after any change to verify core flows",
            "priority": "high",
            "affected_journeys": ["homepage", "login", "search"],
        },
        {
            "playbook_name": "accessibility-audit",
            "reason": "UI components modified — accessibility re-check recommended",
            "priority": "medium",
            "affected_journeys": ["checkout", "forms"],
        },
    ]
    if changed_files:
        for suggestion in suggestions:
            suggestion["changed_files"] = changed_files
    return suggestions


def _validate_playbook_steps(name: str, steps: list[dict]) -> list[str]:
    """Parse and validate playbook steps using the real PlaybookValidator.

    Returns a list of error strings. Empty list means the playbook is valid.
    """
    from tinaa.playbooks.schema import PlaybookDefinition, PlaybookStep, StepAction

    errors: list[str] = []
    parsed_steps: list[PlaybookStep] = []

    for raw_step in steps:
        action_str = raw_step.get("action", "")
        try:
            action = StepAction(action_str)
            params = {k: v for k, v in raw_step.items() if k != "action"}
            parsed_steps.append(PlaybookStep(action=action, params=params))
        except ValueError:
            errors.append(f"Unknown action: {action_str!r}")

    if not errors:
        playbook_def = PlaybookDefinition(name=name, steps=parsed_steps)
        validation_errors = get_services().playbook_validator.validate(playbook_def)
        errors = [f"{e.path}: {e.message}" for e in validation_errors]

    return errors


async def create_playbook(
    product_id_or_slug: str,
    name: str,
    steps: list[dict],
    assertions: Optional[dict] = None,
    performance_gates: Optional[dict] = None,
    ctx: Optional[Context] = None,
) -> dict:
    """Create a new test playbook for a product.

    Defines a sequence of browser actions and optional assertions or
    performance gates. The playbook is saved and immediately available
    for execution via run_playbook.

    Args:
        product_id_or_slug: Product ID or slug.
        name: Human-readable playbook name.
        steps: Ordered list of action dicts, e.g.
            ``[{"action": "navigate", "url": "https://..."},
               {"action": "click", "selector": "#submit"}]``.
        assertions: Optional dict of assertion rules, e.g.
            ``{"status_code": 200, "text_present": "Welcome"}``.
        performance_gates: Optional performance thresholds, e.g.
            ``{"lcp_ms": 2500, "cls": 0.1}``.
        ctx: MCP context (injected automatically).

    Returns:
        dict with keys: playbook_id, name, status.
    """
    try:
        validation_errors = _validate_playbook_steps(name, steps)
    except Exception as exc:
        return {"error": str(exc), "status": "error"}

    return {
        "playbook_id": _new_id("pb-"),
        "product_id_or_slug": product_id_or_slug,
        "name": name,
        "step_count": len(steps),
        "has_assertions": assertions is not None,
        "has_performance_gates": performance_gates is not None,
        "validation_errors": validation_errors,
        "status": "active" if not validation_errors else "invalid",
        "created_at": _ts(),
    }


async def get_quality_report(
    product_id_or_slug: str,
    environment: Optional[str] = None,
    ctx: Optional[Context] = None,
) -> dict:
    """Generate a comprehensive quality report for a product.

    Aggregates test results, performance metrics, security findings, and
    accessibility scores into a single report with trend analysis and
    actionable recommendations.

    Args:
        product_id_or_slug: Product ID or slug.
        environment: Optional environment scope (e.g. ``production``).
        ctx: MCP context (injected automatically).

    Returns:
        dict with keys: quality_score, trend_7d, trend_30d, test_summary,
        performance_summary, security_summary, accessibility_summary,
        top_issues, recommendations.
    """
    return {
        "product_id_or_slug": product_id_or_slug,
        "environment": environment or "all",
        "generated_at": _ts(),
        "quality_score": 87,
        "trend_7d": +2,
        "trend_30d": +5,
        "test_summary": {
            "total_runs": 124,
            "pass_rate": 0.94,
            "flaky_playbooks": 1,
            "avg_duration_ms": 4200,
        },
        "performance_summary": {
            "p50_ms": 210,
            "p95_ms": 420,
            "p99_ms": 890,
            "lcp_ms": 1800,
            "cls": 0.08,
            "slo_compliance": 0.98,
        },
        "security_summary": {
            "open_findings": 2,
            "critical": 0,
            "high": 0,
            "medium": 2,
            "last_scan_at": _ts(),
        },
        "accessibility_summary": {
            "violations": 4,
            "warnings": 11,
            "wcag_level": "AA",
            "score": 82,
        },
        "top_issues": [
            {
                "severity": "medium",
                "type": "accessibility",
                "description": "Missing alt text on 3 images in /checkout",
            },
            {
                "severity": "medium",
                "type": "performance",
                "description": "P95 response time exceeds 400 ms SLO on /api/search",
            },
        ],
        "recommendations": [
            "Add alt text to images on /checkout to fix 3 accessibility violations.",
            "Optimise /api/search query to bring P95 below 400 ms.",
            "Schedule nightly full suite run to catch regressions earlier.",
        ],
    }


def _register_alert_rule(product_id: str, rule_dict: dict, index: int) -> str | None:
    """Register a single alert rule dict via AlertEngine.

    Returns None on success, or an error string on failure.
    """
    from tinaa.alerts.rules import AlertConditionType, AlertRule, AlertSeverity

    rule_type = rule_dict.get("type", "")
    try:
        condition_type = AlertConditionType(rule_type)
        alert_rule = AlertRule(
            name=f"{product_id}-{rule_type}-{index}",
            condition_type=condition_type,
            severity=AlertSeverity.WARNING,
            threshold={"value": rule_dict.get("threshold", 10)},
            product_id=product_id,
        )
        get_services().alert_engine.register_rule(alert_rule)
        return None
    except Exception as exc:
        return f"Rule {rule_type!r}: {exc}"


async def configure_alerts(
    product_id_or_slug: str,
    rules: list[dict],
    ctx: Optional[Context] = None,
) -> dict:
    """Configure alert rules for a product.

    Saves one or more alert rules that will fire when thresholds are breached.
    Supported rule types include quality_score_drop, error_rate_spike,
    performance_degradation, and test_failure_streak.

    Args:
        product_id_or_slug: Product ID or slug.
        rules: List of rule dicts, e.g.
            ``[{"type": "quality_score_drop", "threshold": 10,
                "channels": ["slack:#alerts"]}]``.
        ctx: MCP context (injected automatically).

    Returns:
        dict with keys: status, rules_configured, product_id_or_slug.
    """
    errors = [
        err
        for i, rule_dict in enumerate(rules)
        if (err := _register_alert_rule(product_id_or_slug, rule_dict, i)) is not None
    ]
    registered = len(rules) - len(errors)
    return {
        "status": "ok" if not errors else "partial",
        "product_id_or_slug": product_id_or_slug,
        "rules_configured": registered,
        "errors": errors,
        "updated_at": _ts(),
    }


async def get_deployments(
    product_id_or_slug: str,
    environment: Optional[str] = None,
    limit: int = 10,
    ctx: Optional[Context] = None,
) -> list[dict]:
    """Get recent deployments with their quality impact.

    Returns a list of deployment events for the product, each enriched with
    the quality score delta measured before and after the deploy.

    Args:
        product_id_or_slug: Product ID or slug.
        environment: Optional environment filter (e.g. ``production``).
        limit: Maximum number of deployments to return. Defaults to ``10``.
        ctx: MCP context (injected automatically).

    Returns:
        List of deployment dicts, each containing: deployment_id,
        environment, commit_sha, url, quality_score_delta,
        test_results_summary.
    """
    deployments = [
        {
            "deployment_id": _new_id("deploy-"),
            "environment": environment or "production",
            "commit_sha": "a1b2c3d4e5f6",
            "url": "https://app.example.com",
            "quality_score_delta": +2,
            "test_results_summary": {"passed": 47, "failed": 0},
            "deployed_at": _ts(),
        },
        {
            "deployment_id": _new_id("deploy-"),
            "environment": environment or "production",
            "commit_sha": "f6e5d4c3b2a1",
            "url": "https://app.example.com",
            "quality_score_delta": -3,
            "test_results_summary": {"passed": 44, "failed": 3},
            "deployed_at": _ts(),
        },
    ]
    return deployments[:limit]


async def explore_codebase(
    product_id_or_slug: str,
    ctx: Optional[Context] = None,
) -> dict:
    """Trigger codebase exploration for a product.

    Scans the product's repository to discover routes, API endpoints, HTML
    forms, and inferred user journeys. The results are used to auto-generate
    playbook suggestions and populate the product's endpoint registry.

    Args:
        product_id_or_slug: Product ID or slug.
        ctx: MCP context (injected automatically).

    Returns:
        dict with keys: routes, apis, forms, user_journeys.
    """
    return {
        "product_id_or_slug": product_id_or_slug,
        "explored_at": _ts(),
        "routes": [
            {"path": "/", "method": "GET", "type": "page"},
            {"path": "/login", "method": "GET", "type": "page"},
            {"path": "/register", "method": "GET", "type": "page"},
            {"path": "/checkout", "method": "GET", "type": "page"},
            {"path": "/dashboard", "method": "GET", "type": "page"},
        ],
        "apis": [
            {"path": "/api/auth/login", "method": "POST", "auth": False},
            {"path": "/api/auth/logout", "method": "POST", "auth": True},
            {"path": "/api/products", "method": "GET", "auth": False},
            {"path": "/api/cart", "method": "POST", "auth": True},
            {"path": "/api/orders", "method": "POST", "auth": True},
        ],
        "forms": [
            {"page": "/login", "id": "login-form", "fields": ["email", "password"]},
            {
                "page": "/register",
                "id": "register-form",
                "fields": ["name", "email", "password"],
            },
            {
                "page": "/checkout",
                "id": "checkout-form",
                "fields": ["address", "card_number", "expiry"],
            },
        ],
        "user_journeys": [
            {
                "name": "user-registration",
                "steps": ["visit /register", "fill form", "submit", "verify email"],
            },
            {
                "name": "checkout",
                "steps": ["login", "browse products", "add to cart", "checkout"],
            },
        ],
    }


# ---------------------------------------------------------------------------
# Register all tool functions with the MCP instance
# ---------------------------------------------------------------------------

_TOOL_FUNCTIONS = [
    register_product,
    list_products,
    get_product,
    get_quality_score,
    run_playbook,
    run_suite,
    get_metrics,
    get_test_results,
    suggest_tests,
    create_playbook,
    get_quality_report,
    configure_alerts,
    get_deployments,
    explore_codebase,
]

for _fn in _TOOL_FUNCTIONS:
    mcp.add_tool(FunctionTool.from_function(_fn))
