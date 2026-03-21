"""Tests for TINAA MCP Server — tools, resources, and data shapes."""
import asyncio
import pytest
from typing import Any


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def run(coro):
    """Run a coroutine synchronously."""
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# Server bootstrap
# ---------------------------------------------------------------------------

class TestServerBootstrap:
    """Server module exports the FastMCP instance."""

    def test_mcp_instance_is_accessible(self):
        from tinaa.mcp_server.server import mcp
        assert mcp is not None

    def test_mcp_has_expected_name(self):
        from tinaa.mcp_server.server import mcp
        assert "TINAA" in mcp.name

    def test_mcp_has_instructions(self):
        from tinaa.mcp_server.server import mcp
        assert mcp.instructions is not None
        assert len(mcp.instructions) > 10


# ---------------------------------------------------------------------------
# Tool registration
# ---------------------------------------------------------------------------

EXPECTED_TOOLS = [
    "register_product",
    "list_products",
    "get_product",
    "get_quality_score",
    "run_playbook",
    "run_suite",
    "get_metrics",
    "get_test_results",
    "suggest_tests",
    "create_playbook",
    "get_quality_report",
    "configure_alerts",
    "get_deployments",
    "explore_codebase",
]


class TestToolRegistration:
    """All 14 tools are registered on the MCP instance."""

    def _get_tools(self) -> dict:
        from tinaa.mcp_server.server import mcp
        return run(mcp.get_tools())

    def test_all_expected_tools_registered(self):
        tools = self._get_tools()
        for name in EXPECTED_TOOLS:
            assert name in tools, f"Tool '{name}' not registered"

    def test_tool_count_is_exactly_14(self):
        tools = self._get_tools()
        assert len(tools) == 14

    def test_each_tool_has_description(self):
        tools = self._get_tools()
        for name, tool in tools.items():
            assert tool.description, f"Tool '{name}' is missing a description"

    def test_register_product_tool_exists(self):
        tools = self._get_tools()
        assert "register_product" in tools

    def test_explore_codebase_tool_exists(self):
        tools = self._get_tools()
        assert "explore_codebase" in tools


# ---------------------------------------------------------------------------
# Resource registration
# ---------------------------------------------------------------------------

EXPECTED_RESOURCES = ["tinaa://products"]
EXPECTED_TEMPLATES = [
    "tinaa://products/{product_slug}/quality",
    "tinaa://products/{product_slug}/metrics/{metric_type}",
    "tinaa://products/{product_slug}/playbooks",
]


class TestResourceRegistration:
    """MCP resources and templates are registered correctly."""

    def _get_resources(self) -> dict:
        from tinaa.mcp_server.server import mcp
        return run(mcp.get_resources())

    def _get_templates(self) -> dict:
        from tinaa.mcp_server.server import mcp
        return run(mcp.get_resource_templates())

    def test_static_products_resource_registered(self):
        resources = self._get_resources()
        assert "tinaa://products" in resources

    def test_quality_template_registered(self):
        templates = self._get_templates()
        assert "tinaa://products/{product_slug}/quality" in templates

    def test_metrics_template_registered(self):
        templates = self._get_templates()
        assert "tinaa://products/{product_slug}/metrics/{metric_type}" in templates

    def test_playbooks_template_registered(self):
        templates = self._get_templates()
        assert "tinaa://products/{product_slug}/playbooks" in templates

    def test_total_template_count(self):
        templates = self._get_templates()
        assert len(templates) >= 3


# ---------------------------------------------------------------------------
# Tool stub shapes — register_product
# ---------------------------------------------------------------------------

class TestRegisterProductShape:
    """register_product returns a dict with required keys."""

    @pytest.mark.asyncio
    async def test_returns_dict(self):
        from tinaa.mcp_server.tools import register_product
        result = await register_product(
            name="My App",
            repo_url="https://github.com/org/repo",
            environments={"production": "https://app.example.com"},
        )
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_returns_product_id(self):
        from tinaa.mcp_server.tools import register_product
        result = await register_product(
            name="My App",
            repo_url="https://github.com/org/repo",
            environments={"production": "https://app.example.com"},
        )
        assert "product_id" in result

    @pytest.mark.asyncio
    async def test_returns_name(self):
        from tinaa.mcp_server.tools import register_product
        result = await register_product(
            name="My App",
            repo_url="https://github.com/org/repo",
            environments={"staging": "https://staging.example.com"},
        )
        assert result["name"] == "My App"

    @pytest.mark.asyncio
    async def test_returns_status(self):
        from tinaa.mcp_server.tools import register_product
        result = await register_product(
            name="My App",
            repo_url="https://github.com/org/repo",
            environments={},
        )
        assert "status" in result

    @pytest.mark.asyncio
    async def test_returns_slug(self):
        from tinaa.mcp_server.tools import register_product
        result = await register_product(
            name="My App",
            repo_url="https://github.com/org/repo",
            environments={},
        )
        assert "slug" in result


# ---------------------------------------------------------------------------
# Tool stub shapes — list_products
# ---------------------------------------------------------------------------

class TestListProductsShape:
    """list_products returns a list of product dicts."""

    @pytest.mark.asyncio
    async def test_returns_list(self):
        from tinaa.mcp_server.tools import list_products
        result = await list_products()
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_each_item_has_product_id(self):
        from tinaa.mcp_server.tools import list_products
        result = await list_products()
        for item in result:
            assert "product_id" in item

    @pytest.mark.asyncio
    async def test_each_item_has_status(self):
        from tinaa.mcp_server.tools import list_products
        result = await list_products()
        for item in result:
            assert "status" in item

    @pytest.mark.asyncio
    async def test_accepts_status_filter(self):
        from tinaa.mcp_server.tools import list_products
        result = await list_products(status="active")
        assert isinstance(result, list)


# ---------------------------------------------------------------------------
# Tool stub shapes — get_product
# ---------------------------------------------------------------------------

class TestGetProductShape:
    """get_product returns detailed product info."""

    @pytest.mark.asyncio
    async def test_returns_dict(self):
        from tinaa.mcp_server.tools import get_product
        result = await get_product(product_id_or_slug="demo-app")
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_returns_environments(self):
        from tinaa.mcp_server.tools import get_product
        result = await get_product(product_id_or_slug="demo-app")
        assert "environments" in result

    @pytest.mark.asyncio
    async def test_returns_quality_score(self):
        from tinaa.mcp_server.tools import get_product
        result = await get_product(product_id_or_slug="demo-app")
        assert "quality_score" in result

    @pytest.mark.asyncio
    async def test_returns_recent_test_runs(self):
        from tinaa.mcp_server.tools import get_product
        result = await get_product(product_id_or_slug="demo-app")
        assert "recent_test_runs" in result


# ---------------------------------------------------------------------------
# Tool stub shapes — get_quality_score
# ---------------------------------------------------------------------------

class TestGetQualityScoreShape:
    """get_quality_score returns a structured quality breakdown."""

    @pytest.mark.asyncio
    async def test_returns_score(self):
        from tinaa.mcp_server.tools import get_quality_score
        result = await get_quality_score(product_id_or_slug="demo-app")
        assert "score" in result
        assert isinstance(result["score"], (int, float))

    @pytest.mark.asyncio
    async def test_returns_component_breakdown(self):
        from tinaa.mcp_server.tools import get_quality_score
        result = await get_quality_score(product_id_or_slug="demo-app")
        for key in ("test_health", "performance_health", "security_posture",
                    "accessibility"):
            assert key in result, f"Missing key: {key}"

    @pytest.mark.asyncio
    async def test_returns_trend(self):
        from tinaa.mcp_server.tools import get_quality_score
        result = await get_quality_score(product_id_or_slug="demo-app")
        assert "trend" in result

    @pytest.mark.asyncio
    async def test_returns_recommendations(self):
        from tinaa.mcp_server.tools import get_quality_score
        result = await get_quality_score(product_id_or_slug="demo-app")
        assert "recommendations" in result
        assert isinstance(result["recommendations"], list)

    @pytest.mark.asyncio
    async def test_accepts_environment_param(self):
        from tinaa.mcp_server.tools import get_quality_score
        result = await get_quality_score(
            product_id_or_slug="demo-app", environment="production"
        )
        assert "score" in result


# ---------------------------------------------------------------------------
# Tool stub shapes — run_playbook
# ---------------------------------------------------------------------------

class TestRunPlaybookShape:
    """run_playbook returns execution result with required keys."""

    @pytest.mark.asyncio
    async def test_returns_run_id(self):
        from tinaa.mcp_server.tools import run_playbook
        result = await run_playbook(playbook_id_or_name="smoke-test")
        assert "run_id" in result

    @pytest.mark.asyncio
    async def test_returns_status(self):
        from tinaa.mcp_server.tools import run_playbook
        result = await run_playbook(playbook_id_or_name="smoke-test")
        assert "status" in result

    @pytest.mark.asyncio
    async def test_returns_results_summary(self):
        from tinaa.mcp_server.tools import run_playbook
        result = await run_playbook(playbook_id_or_name="smoke-test")
        assert "results_summary" in result

    @pytest.mark.asyncio
    async def test_returns_duration_ms(self):
        from tinaa.mcp_server.tools import run_playbook
        result = await run_playbook(playbook_id_or_name="smoke-test")
        assert "duration_ms" in result

    @pytest.mark.asyncio
    async def test_returns_quality_score_impact(self):
        from tinaa.mcp_server.tools import run_playbook
        result = await run_playbook(playbook_id_or_name="smoke-test")
        assert "quality_score_impact" in result


# ---------------------------------------------------------------------------
# Tool stub shapes — run_suite
# ---------------------------------------------------------------------------

class TestRunSuiteShape:
    """run_suite returns aggregated suite results."""

    @pytest.mark.asyncio
    async def test_returns_run_id(self):
        from tinaa.mcp_server.tools import run_suite
        result = await run_suite(product_id_or_slug="demo-app")
        assert "run_id" in result

    @pytest.mark.asyncio
    async def test_returns_playbooks_executed(self):
        from tinaa.mcp_server.tools import run_suite
        result = await run_suite(product_id_or_slug="demo-app")
        assert "playbooks_executed" in result

    @pytest.mark.asyncio
    async def test_returns_pass_fail_counts(self):
        from tinaa.mcp_server.tools import run_suite
        result = await run_suite(product_id_or_slug="demo-app")
        assert "passed" in result
        assert "failed" in result

    @pytest.mark.asyncio
    async def test_returns_quality_score(self):
        from tinaa.mcp_server.tools import run_suite
        result = await run_suite(product_id_or_slug="demo-app")
        assert "quality_score" in result

    @pytest.mark.asyncio
    async def test_default_environment_is_staging(self):
        from tinaa.mcp_server.tools import run_suite
        import inspect
        sig = inspect.signature(run_suite)
        assert sig.parameters["environment"].default == "staging"

    @pytest.mark.asyncio
    async def test_default_suite_type_is_regression(self):
        from tinaa.mcp_server.tools import run_suite
        import inspect
        sig = inspect.signature(run_suite)
        assert sig.parameters["suite_type"].default == "regression"


# ---------------------------------------------------------------------------
# Tool stub shapes — get_metrics
# ---------------------------------------------------------------------------

class TestGetMetricsShape:
    """get_metrics returns time-series data with baseline and trend."""

    @pytest.mark.asyncio
    async def test_returns_metrics_list(self):
        from tinaa.mcp_server.tools import get_metrics
        result = await get_metrics(product_id_or_slug="demo-app")
        assert "metrics" in result
        assert isinstance(result["metrics"], list)

    @pytest.mark.asyncio
    async def test_metrics_items_have_timestamp_and_value(self):
        from tinaa.mcp_server.tools import get_metrics
        result = await get_metrics(product_id_or_slug="demo-app")
        for item in result["metrics"]:
            assert "timestamp" in item
            assert "value" in item

    @pytest.mark.asyncio
    async def test_returns_baseline(self):
        from tinaa.mcp_server.tools import get_metrics
        result = await get_metrics(product_id_or_slug="demo-app")
        assert "baseline" in result

    @pytest.mark.asyncio
    async def test_returns_current_avg(self):
        from tinaa.mcp_server.tools import get_metrics
        result = await get_metrics(product_id_or_slug="demo-app")
        assert "current_avg" in result

    @pytest.mark.asyncio
    async def test_returns_trend(self):
        from tinaa.mcp_server.tools import get_metrics
        result = await get_metrics(product_id_or_slug="demo-app")
        assert "trend" in result

    @pytest.mark.asyncio
    async def test_default_hours_is_24(self):
        from tinaa.mcp_server.tools import get_metrics
        import inspect
        sig = inspect.signature(get_metrics)
        assert sig.parameters["hours"].default == 24


# ---------------------------------------------------------------------------
# Tool stub shapes — get_test_results
# ---------------------------------------------------------------------------

class TestGetTestResultsShape:
    """get_test_results returns a list of run result dicts."""

    @pytest.mark.asyncio
    async def test_returns_list(self):
        from tinaa.mcp_server.tools import get_test_results
        result = await get_test_results(product_id_or_slug="demo-app")
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_each_item_has_required_keys(self):
        from tinaa.mcp_server.tools import get_test_results
        result = await get_test_results(product_id_or_slug="demo-app")
        required = {"run_id", "playbook_name", "status", "duration_ms",
                    "passed", "failed", "timestamp"}
        for item in result:
            for key in required:
                assert key in item, f"Item missing key '{key}'"

    @pytest.mark.asyncio
    async def test_default_limit_is_10(self):
        from tinaa.mcp_server.tools import get_test_results
        import inspect
        sig = inspect.signature(get_test_results)
        assert sig.parameters["limit"].default == 10

    @pytest.mark.asyncio
    async def test_accepts_status_filter(self):
        from tinaa.mcp_server.tools import get_test_results
        result = await get_test_results(product_id_or_slug="demo-app", status="passed")
        assert isinstance(result, list)


# ---------------------------------------------------------------------------
# Tool stub shapes — suggest_tests
# ---------------------------------------------------------------------------

class TestSuggestTestsShape:
    """suggest_tests returns prioritized test suggestions."""

    @pytest.mark.asyncio
    async def test_returns_list(self):
        from tinaa.mcp_server.tools import suggest_tests
        result = await suggest_tests(product_id_or_slug="demo-app")
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_each_item_has_required_keys(self):
        from tinaa.mcp_server.tools import suggest_tests
        result = await suggest_tests(product_id_or_slug="demo-app")
        required = {"playbook_name", "reason", "priority", "affected_journeys"}
        for item in result:
            for key in required:
                assert key in item, f"Suggestion missing key '{key}'"

    @pytest.mark.asyncio
    async def test_accepts_changed_files_param(self):
        from tinaa.mcp_server.tools import suggest_tests
        result = await suggest_tests(
            product_id_or_slug="demo-app",
            changed_files=["src/checkout.py", "src/cart.py"],
        )
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_default_changed_files_is_none(self):
        from tinaa.mcp_server.tools import suggest_tests
        import inspect
        sig = inspect.signature(suggest_tests)
        assert sig.parameters["changed_files"].default is None


# ---------------------------------------------------------------------------
# Tool stub shapes — create_playbook
# ---------------------------------------------------------------------------

class TestCreatePlaybookShape:
    """create_playbook returns newly created playbook metadata."""

    @pytest.mark.asyncio
    async def test_returns_playbook_id(self):
        from tinaa.mcp_server.tools import create_playbook
        result = await create_playbook(
            product_id_or_slug="demo-app",
            name="Login Flow",
            steps=[{"action": "navigate", "url": "https://app.example.com/login"}],
        )
        assert "playbook_id" in result

    @pytest.mark.asyncio
    async def test_returns_name(self):
        from tinaa.mcp_server.tools import create_playbook
        result = await create_playbook(
            product_id_or_slug="demo-app",
            name="Login Flow",
            steps=[],
        )
        assert result["name"] == "Login Flow"

    @pytest.mark.asyncio
    async def test_returns_status(self):
        from tinaa.mcp_server.tools import create_playbook
        result = await create_playbook(
            product_id_or_slug="demo-app",
            name="Login Flow",
            steps=[],
        )
        assert "status" in result

    @pytest.mark.asyncio
    async def test_default_assertions_is_none(self):
        from tinaa.mcp_server.tools import create_playbook
        import inspect
        sig = inspect.signature(create_playbook)
        assert sig.parameters["assertions"].default is None

    @pytest.mark.asyncio
    async def test_default_performance_gates_is_none(self):
        from tinaa.mcp_server.tools import create_playbook
        import inspect
        sig = inspect.signature(create_playbook)
        assert sig.parameters["performance_gates"].default is None


# ---------------------------------------------------------------------------
# Tool stub shapes — get_quality_report
# ---------------------------------------------------------------------------

class TestGetQualityReportShape:
    """get_quality_report returns a comprehensive report dict."""

    @pytest.mark.asyncio
    async def test_returns_quality_score(self):
        from tinaa.mcp_server.tools import get_quality_report
        result = await get_quality_report(product_id_or_slug="demo-app")
        assert "quality_score" in result

    @pytest.mark.asyncio
    async def test_returns_trend_fields(self):
        from tinaa.mcp_server.tools import get_quality_report
        result = await get_quality_report(product_id_or_slug="demo-app")
        assert "trend_7d" in result
        assert "trend_30d" in result

    @pytest.mark.asyncio
    async def test_returns_summary_fields(self):
        from tinaa.mcp_server.tools import get_quality_report
        result = await get_quality_report(product_id_or_slug="demo-app")
        for key in ("test_summary", "performance_summary", "security_summary",
                    "accessibility_summary"):
            assert key in result, f"Missing key: {key}"

    @pytest.mark.asyncio
    async def test_returns_top_issues_and_recommendations(self):
        from tinaa.mcp_server.tools import get_quality_report
        result = await get_quality_report(product_id_or_slug="demo-app")
        assert "top_issues" in result
        assert "recommendations" in result
        assert isinstance(result["top_issues"], list)
        assert isinstance(result["recommendations"], list)


# ---------------------------------------------------------------------------
# Tool stub shapes — configure_alerts
# ---------------------------------------------------------------------------

class TestConfigureAlertsShape:
    """configure_alerts returns confirmation with rule count."""

    @pytest.mark.asyncio
    async def test_returns_dict(self):
        from tinaa.mcp_server.tools import configure_alerts
        result = await configure_alerts(
            product_id_or_slug="demo-app",
            rules=[{"type": "quality_score_drop", "threshold": 10,
                    "channels": ["slack:#alerts"]}],
        )
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_returns_status(self):
        from tinaa.mcp_server.tools import configure_alerts
        result = await configure_alerts(product_id_or_slug="demo-app", rules=[])
        assert "status" in result

    @pytest.mark.asyncio
    async def test_returns_rules_configured_count(self):
        from tinaa.mcp_server.tools import configure_alerts
        rules = [
            {"type": "quality_score_drop", "threshold": 10, "channels": []},
            {"type": "error_rate_spike", "threshold": 5, "channels": []},
        ]
        result = await configure_alerts(product_id_or_slug="demo-app", rules=rules)
        assert "rules_configured" in result
        assert result["rules_configured"] == 2


# ---------------------------------------------------------------------------
# Tool stub shapes — get_deployments
# ---------------------------------------------------------------------------

class TestGetDeploymentsShape:
    """get_deployments returns a list of deployment dicts."""

    @pytest.mark.asyncio
    async def test_returns_list(self):
        from tinaa.mcp_server.tools import get_deployments
        result = await get_deployments(product_id_or_slug="demo-app")
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_each_item_has_required_keys(self):
        from tinaa.mcp_server.tools import get_deployments
        result = await get_deployments(product_id_or_slug="demo-app")
        required = {"deployment_id", "environment", "commit_sha", "url",
                    "quality_score_delta", "test_results_summary"}
        for item in result:
            for key in required:
                assert key in item, f"Deployment missing key '{key}'"

    @pytest.mark.asyncio
    async def test_default_limit_is_10(self):
        from tinaa.mcp_server.tools import get_deployments
        import inspect
        sig = inspect.signature(get_deployments)
        assert sig.parameters["limit"].default == 10


# ---------------------------------------------------------------------------
# Tool stub shapes — explore_codebase
# ---------------------------------------------------------------------------

class TestExploreCodebaseShape:
    """explore_codebase returns discovery results."""

    @pytest.mark.asyncio
    async def test_returns_dict(self):
        from tinaa.mcp_server.tools import explore_codebase
        result = await explore_codebase(product_id_or_slug="demo-app")
        assert isinstance(result, dict)

    @pytest.mark.asyncio
    async def test_returns_routes(self):
        from tinaa.mcp_server.tools import explore_codebase
        result = await explore_codebase(product_id_or_slug="demo-app")
        assert "routes" in result

    @pytest.mark.asyncio
    async def test_returns_apis(self):
        from tinaa.mcp_server.tools import explore_codebase
        result = await explore_codebase(product_id_or_slug="demo-app")
        assert "apis" in result

    @pytest.mark.asyncio
    async def test_returns_forms(self):
        from tinaa.mcp_server.tools import explore_codebase
        result = await explore_codebase(product_id_or_slug="demo-app")
        assert "forms" in result

    @pytest.mark.asyncio
    async def test_returns_user_journeys(self):
        from tinaa.mcp_server.tools import explore_codebase
        result = await explore_codebase(product_id_or_slug="demo-app")
        assert "user_journeys" in result


# ---------------------------------------------------------------------------
# Resource callable correctness
# ---------------------------------------------------------------------------

class TestResourceCallables:
    """Resource functions return non-empty strings."""

    def test_list_all_products_returns_string(self):
        from tinaa.mcp_server.resources import list_all_products
        result = list_all_products()
        assert isinstance(result, str)
        assert len(result) > 0

    def test_get_product_quality_returns_string(self):
        from tinaa.mcp_server.resources import get_product_quality
        result = get_product_quality("demo-app")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_get_product_metrics_returns_string(self):
        from tinaa.mcp_server.resources import get_product_metrics
        result = get_product_metrics("demo-app", "response_time")
        assert isinstance(result, str)
        assert len(result) > 0

    def test_list_product_playbooks_returns_string(self):
        from tinaa.mcp_server.resources import list_product_playbooks
        result = list_product_playbooks("demo-app")
        assert isinstance(result, str)
        assert len(result) > 0
