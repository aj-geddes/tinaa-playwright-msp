"""TINAA MCP Server — resource definitions.

Resources expose read-only data via the MCP resource protocol.  Each
function is a plain callable registered on the shared FastMCP instance via
``FunctionResource.from_function`` / ``ResourceTemplate.from_function`` at
module import time.  This keeps the functions directly callable in tests.
"""

from fastmcp.resources import FunctionResource, ResourceTemplate

from tinaa.mcp_server._mcp import mcp

MIME_TEXT = "text/plain"


# ---------------------------------------------------------------------------
# Resource functions
# ---------------------------------------------------------------------------


def list_all_products() -> str:
    """List all registered products as formatted text.

    Returns a newline-separated summary of every product registered in
    TINAA MSP, including its slug, name, status, and current quality score.
    """
    lines = [
        "TINAA MSP — Registered Products",
        "=" * 40,
        "",
        "slug: demo-app      | name: Demo App      | status: active | score: 87",
        "slug: api-gateway   | name: API Gateway   | status: active | score: 92",
        "slug: legacy-portal | name: Legacy Portal | status: paused | score: 61",
    ]
    return "\n".join(lines)


def get_product_quality(product_slug: str) -> str:
    """Get quality report for a product.

    Returns a human-readable quality summary for the given product slug,
    including score breakdown, trend, and top recommendations.

    Args:
        product_slug: The product's URL slug (e.g. ``demo-app``).
    """
    lines = [
        f"Quality Report — {product_slug}",
        "=" * 40,
        "",
        "Overall Score   : 87 / 100  (trend: improving +2 this week)",
        "Test Health     : 91  (pass rate: 94%, flakiness: 2%)",
        "Performance     : 84  (P95: 420 ms, LCP: 1.8 s)",
        "Security        : 88  (open findings: 2, critical: 0)",
        "Accessibility   : 82  (violations: 4, warnings: 11)",
        "",
        "Top Recommendations:",
        "  1. Fix 4 accessibility violations on /checkout (+3 pts)",
        "  2. Reduce P95 response time to <400 ms to meet SLO",
    ]
    return "\n".join(lines)


def get_product_metrics(product_slug: str, metric_type: str) -> str:
    """Get latest metrics for a product.

    Returns a formatted table of the most recent metric readings for the
    specified metric type.

    Args:
        product_slug: The product's URL slug (e.g. ``demo-app``).
        metric_type: One of ``response_time``, ``lcp``, ``cls``,
            ``availability``, ``error_rate``.
    """
    lines = [
        f"Metrics — {product_slug} / {metric_type}",
        "=" * 40,
        "",
        "Period  : last 24 hours",
        "Baseline: 300",
        "Avg     : 309  (trend: stable)",
        "",
        "Recent readings:",
        "  2026-03-20T12:00:00Z  312",
        "  2026-03-20T11:00:00Z  298",
        "  2026-03-20T10:00:00Z  340",
        "  2026-03-20T09:00:00Z  285",
    ]
    return "\n".join(lines)


def list_product_playbooks(product_slug: str) -> str:
    """List all playbooks for a product.

    Returns a formatted list of playbooks registered for the given product,
    including their status and last run result.

    Args:
        product_slug: The product's URL slug (e.g. ``demo-app``).
    """
    lines = [
        f"Playbooks — {product_slug}",
        "=" * 40,
        "",
        "ID          Name                    Status   Last Run",
        "-" * 60,
        "pb-a1b2c3  smoke-test              active   passed (2026-03-20)",
        "pb-d4e5f6  checkout-regression     active   failed (2026-03-20)",
        "pb-a7b8c9  accessibility-audit     active   passed (2026-03-19)",
        "pb-d0e1f2  performance-benchmark   active   passed (2026-03-19)",
    ]
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Register resources with the MCP instance
# ---------------------------------------------------------------------------

mcp.add_resource(
    FunctionResource.from_function(
        list_all_products,
        uri="tinaa://products",
        name="list_all_products",
        description=list_all_products.__doc__,
        mime_type=MIME_TEXT,
    )
)

mcp.add_template(
    ResourceTemplate.from_function(
        get_product_quality,
        uri_template="tinaa://products/{product_slug}/quality",
        name="get_product_quality",
        description=get_product_quality.__doc__,
        mime_type=MIME_TEXT,
    )
)

mcp.add_template(
    ResourceTemplate.from_function(
        get_product_metrics,
        uri_template="tinaa://products/{product_slug}/metrics/{metric_type}",
        name="get_product_metrics",
        description=get_product_metrics.__doc__,
        mime_type=MIME_TEXT,
    )
)

mcp.add_template(
    ResourceTemplate.from_function(
        list_product_playbooks,
        uri_template="tinaa://products/{product_slug}/playbooks",
        name="list_product_playbooks",
        description=list_product_playbooks.__doc__,
        mime_type=MIME_TEXT,
    )
)
