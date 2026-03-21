"""
Unit tests for TINAA agent system.

Tests cover:
- AgentTask lifecycle and status transitions
- Orchestrator event routing and dispatch
- ExplorerAgent framework detection and codebase analysis
- TestDesignerAgent playbook generation structure
- TestRunnerAgent step mapping and execution
- AnalystAgent analysis output structure
- ReporterAgent markdown formatting
"""

from __future__ import annotations

import pytest
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID

from tinaa.agents.base import AgentStatus, AgentTask, BaseAgent
from tinaa.agents.orchestrator import Orchestrator
from tinaa.agents.explorer import ExplorerAgent
from tinaa.agents.test_designer import TestDesignerAgent
from tinaa.agents.test_runner import TestRunnerAgent
from tinaa.agents.analyst import AnalystAgent
from tinaa.agents.reporter import ReporterAgent


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


class ConcreteAgent(BaseAgent):
    """Minimal concrete agent for testing BaseAgent behavior."""

    def __init__(self, name: str = "concrete"):
        super().__init__(name)
        self.run_called_with: AgentTask | None = None
        self.should_raise: Exception | None = None

    async def _run(self, task: AgentTask) -> dict:
        self.run_called_with = task
        if self.should_raise:
            raise self.should_raise
        return {"output": "done", "task_action": task.action}


@pytest.fixture
def simple_task() -> AgentTask:
    return AgentTask(agent_type="concrete", action="do_something", params={"key": "val"})


@pytest.fixture
def orchestrator() -> Orchestrator:
    return Orchestrator()


@pytest.fixture
def explorer() -> ExplorerAgent:
    return ExplorerAgent()


@pytest.fixture
def test_designer() -> TestDesignerAgent:
    return TestDesignerAgent()


@pytest.fixture
def test_runner() -> TestRunnerAgent:
    return TestRunnerAgent()


@pytest.fixture
def analyst() -> AnalystAgent:
    return AnalystAgent()


@pytest.fixture
def reporter() -> ReporterAgent:
    return ReporterAgent()


# ---------------------------------------------------------------------------
# AgentTask Tests
# ---------------------------------------------------------------------------


class TestAgentTask:
    """Tests for AgentTask dataclass lifecycle."""

    def test_task_has_uuid_id(self, simple_task: AgentTask) -> None:
        assert isinstance(simple_task.id, UUID)

    def test_task_default_status_is_idle(self, simple_task: AgentTask) -> None:
        assert simple_task.status == AgentStatus.IDLE

    def test_task_stores_action_and_params(self, simple_task: AgentTask) -> None:
        assert simple_task.action == "do_something"
        assert simple_task.params == {"key": "val"}

    def test_task_agent_type_stored(self, simple_task: AgentTask) -> None:
        assert simple_task.agent_type == "concrete"

    def test_duration_ms_none_when_not_started(self, simple_task: AgentTask) -> None:
        assert simple_task.duration_ms is None

    def test_duration_ms_none_when_only_started(self, simple_task: AgentTask) -> None:
        simple_task.started_at = datetime.utcnow()
        assert simple_task.duration_ms is None

    def test_duration_ms_calculated_when_both_set(self, simple_task: AgentTask) -> None:
        from datetime import timedelta

        start = datetime(2024, 1, 1, 12, 0, 0)
        end = start + timedelta(seconds=2, milliseconds=500)
        simple_task.started_at = start
        simple_task.completed_at = end
        assert simple_task.duration_ms == 2500

    def test_task_result_initially_none(self, simple_task: AgentTask) -> None:
        assert simple_task.result is None

    def test_task_error_initially_none(self, simple_task: AgentTask) -> None:
        assert simple_task.error is None

    def test_task_created_at_set(self, simple_task: AgentTask) -> None:
        assert isinstance(simple_task.created_at, datetime)

    def test_two_tasks_have_different_ids(self) -> None:
        t1 = AgentTask()
        t2 = AgentTask()
        assert t1.id != t2.id


# ---------------------------------------------------------------------------
# BaseAgent Tests
# ---------------------------------------------------------------------------


class TestBaseAgent:
    """Tests for BaseAgent execution lifecycle."""

    @pytest.mark.asyncio
    async def test_execute_transitions_to_completed(self, simple_task: AgentTask) -> None:
        agent = ConcreteAgent()
        result_task = await agent.execute(simple_task)
        assert result_task.status == AgentStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_execute_sets_result(self, simple_task: AgentTask) -> None:
        agent = ConcreteAgent()
        result_task = await agent.execute(simple_task)
        assert result_task.result == {"output": "done", "task_action": "do_something"}

    @pytest.mark.asyncio
    async def test_execute_sets_started_at(self, simple_task: AgentTask) -> None:
        agent = ConcreteAgent()
        result_task = await agent.execute(simple_task)
        assert result_task.started_at is not None

    @pytest.mark.asyncio
    async def test_execute_sets_completed_at(self, simple_task: AgentTask) -> None:
        agent = ConcreteAgent()
        result_task = await agent.execute(simple_task)
        assert result_task.completed_at is not None

    @pytest.mark.asyncio
    async def test_execute_duration_positive(self, simple_task: AgentTask) -> None:
        agent = ConcreteAgent()
        result_task = await agent.execute(simple_task)
        assert result_task.duration_ms is not None
        assert result_task.duration_ms >= 0

    @pytest.mark.asyncio
    async def test_execute_failure_sets_failed_status(self, simple_task: AgentTask) -> None:
        agent = ConcreteAgent()
        agent.should_raise = ValueError("boom")
        result_task = await agent.execute(simple_task)
        assert result_task.status == AgentStatus.FAILED

    @pytest.mark.asyncio
    async def test_execute_failure_sets_error_message(self, simple_task: AgentTask) -> None:
        agent = ConcreteAgent()
        agent.should_raise = ValueError("boom")
        result_task = await agent.execute(simple_task)
        assert result_task.error == "boom"

    @pytest.mark.asyncio
    async def test_execute_failure_still_sets_completed_at(
        self, simple_task: AgentTask
    ) -> None:
        agent = ConcreteAgent()
        agent.should_raise = RuntimeError("fail")
        result_task = await agent.execute(simple_task)
        assert result_task.completed_at is not None

    @pytest.mark.asyncio
    async def test_agent_status_matches_task_status_after_success(
        self, simple_task: AgentTask
    ) -> None:
        agent = ConcreteAgent()
        await agent.execute(simple_task)
        assert agent.status == AgentStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_agent_status_failed_after_exception(self, simple_task: AgentTask) -> None:
        agent = ConcreteAgent()
        agent.should_raise = RuntimeError("fail")
        await agent.execute(simple_task)
        assert agent.status == AgentStatus.FAILED

    def test_agent_initial_status_idle(self) -> None:
        agent = ConcreteAgent()
        assert agent.status == AgentStatus.IDLE

    def test_agent_has_logger(self) -> None:
        import logging

        agent = ConcreteAgent("myagent")
        assert agent.logger.name == "tinaa.agents.myagent"


# ---------------------------------------------------------------------------
# Orchestrator Tests
# ---------------------------------------------------------------------------


class TestOrchestrator:
    """Tests for Orchestrator event routing and dispatch."""

    def test_orchestrator_name(self, orchestrator: Orchestrator) -> None:
        assert orchestrator.name == "orchestrator"

    def test_register_agent_stores_agent(self, orchestrator: Orchestrator) -> None:
        agent = ConcreteAgent("worker")
        orchestrator.register_agent(agent)
        assert "worker" in orchestrator._agents

    def test_register_multiple_agents(self, orchestrator: Orchestrator) -> None:
        orchestrator.register_agent(ConcreteAgent("a"))
        orchestrator.register_agent(ConcreteAgent("b"))
        assert len(orchestrator._agents) == 2

    def test_on_event_registers_handler(self, orchestrator: Orchestrator) -> None:
        handler = MagicMock()
        orchestrator.on_event("deployment_detected", handler)
        assert "deployment_detected" in orchestrator._event_handlers
        assert handler in orchestrator._event_handlers["deployment_detected"]

    def test_on_event_multiple_handlers_same_type(self, orchestrator: Orchestrator) -> None:
        h1 = MagicMock()
        h2 = MagicMock()
        orchestrator.on_event("pr_opened", h1)
        orchestrator.on_event("pr_opened", h2)
        assert len(orchestrator._event_handlers["pr_opened"]) == 2

    @pytest.mark.asyncio
    async def test_handle_event_product_registered_returns_tasks(
        self, orchestrator: Orchestrator
    ) -> None:
        tasks = await orchestrator.handle_event(
            "product_registered", {"product_id": "123", "repo_path": "/repo"}
        )
        assert isinstance(tasks, list)
        assert len(tasks) > 0

    @pytest.mark.asyncio
    async def test_handle_event_deployment_detected_returns_tasks(
        self, orchestrator: Orchestrator
    ) -> None:
        tasks = await orchestrator.handle_event(
            "deployment_detected",
            {"product_id": "123", "deployment_url": "https://example.com"},
        )
        assert isinstance(tasks, list)
        assert len(tasks) > 0

    @pytest.mark.asyncio
    async def test_handle_event_pr_opened_returns_tasks(
        self, orchestrator: Orchestrator
    ) -> None:
        tasks = await orchestrator.handle_event(
            "pr_opened",
            {"product_id": "123", "pr_number": 42, "changed_files": []},
        )
        assert isinstance(tasks, list)

    @pytest.mark.asyncio
    async def test_handle_event_anomaly_detected_returns_tasks(
        self, orchestrator: Orchestrator
    ) -> None:
        tasks = await orchestrator.handle_event(
            "anomaly_detected",
            {"product_id": "123", "endpoint": "/api/users", "metric": "p99"},
        )
        assert isinstance(tasks, list)

    @pytest.mark.asyncio
    async def test_handle_unknown_event_returns_empty_list(
        self, orchestrator: Orchestrator
    ) -> None:
        tasks = await orchestrator.handle_event("unknown_event_type", {})
        assert tasks == []

    @pytest.mark.asyncio
    async def test_dispatch_task_routes_to_registered_agent(
        self, orchestrator: Orchestrator
    ) -> None:
        agent = ConcreteAgent("concrete")
        orchestrator.register_agent(agent)
        task = AgentTask(agent_type="concrete", action="do_something")
        result = await orchestrator.dispatch_task(task)
        assert result.status == AgentStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_dispatch_task_unregistered_agent_fails(
        self, orchestrator: Orchestrator
    ) -> None:
        task = AgentTask(agent_type="nonexistent", action="something")
        result = await orchestrator.dispatch_task(task)
        assert result.status == AgentStatus.FAILED

    @pytest.mark.asyncio
    async def test_get_status_returns_dict(self, orchestrator: Orchestrator) -> None:
        status = await orchestrator.get_status()
        assert isinstance(status, dict)
        assert "agents" in status
        assert "pending_tasks" in status

    @pytest.mark.asyncio
    async def test_get_status_includes_registered_agents(
        self, orchestrator: Orchestrator
    ) -> None:
        orchestrator.register_agent(ConcreteAgent("myagent"))
        status = await orchestrator.get_status()
        assert "myagent" in status["agents"]

    @pytest.mark.asyncio
    async def test_orchestrator_own_task_execution(
        self, orchestrator: Orchestrator
    ) -> None:
        task = AgentTask(agent_type="orchestrator", action="get_status")
        result = await orchestrator.execute(task)
        assert result.status == AgentStatus.COMPLETED


# ---------------------------------------------------------------------------
# ExplorerAgent Tests
# ---------------------------------------------------------------------------


class TestExplorerAgent:
    """Tests for ExplorerAgent framework detection and analysis."""

    # --- detect_framework ---

    @pytest.mark.asyncio
    async def test_detect_nextjs_from_next_config(self, explorer: ExplorerAgent) -> None:
        files = ["next.config.js", "package.json", "pages/index.tsx"]
        result = await explorer.detect_framework(files)
        assert result["frontend"] == "nextjs"

    @pytest.mark.asyncio
    async def test_detect_react_from_package_without_next(
        self, explorer: ExplorerAgent
    ) -> None:
        files = ["package.json", "src/App.tsx", "src/index.jsx"]
        result = await explorer.detect_framework(files)
        assert result["frontend"] == "react"

    @pytest.mark.asyncio
    async def test_detect_vue_from_vue_config(self, explorer: ExplorerAgent) -> None:
        files = ["vue.config.js", "src/App.vue", "package.json"]
        result = await explorer.detect_framework(files)
        assert result["frontend"] == "vue"

    @pytest.mark.asyncio
    async def test_detect_angular_from_angular_json(self, explorer: ExplorerAgent) -> None:
        files = ["angular.json", "src/app/app.module.ts", "package.json"]
        result = await explorer.detect_framework(files)
        assert result["frontend"] == "angular"

    @pytest.mark.asyncio
    async def test_detect_django_from_manage_py(self, explorer: ExplorerAgent) -> None:
        files = ["manage.py", "myapp/models.py", "myapp/views.py", "requirements.txt"]
        result = await explorer.detect_framework(files)
        assert result["backend"] == "django"

    @pytest.mark.asyncio
    async def test_detect_fastapi_from_main_py_pattern(
        self, explorer: ExplorerAgent
    ) -> None:
        files = ["main.py", "requirements.txt", "app/routers/users.py"]
        result = await explorer.detect_framework(files)
        # fastapi is detected via requirements.txt presence + main.py pattern
        assert "backend" in result

    @pytest.mark.asyncio
    async def test_detect_flask_from_app_py(self, explorer: ExplorerAgent) -> None:
        files = ["app.py", "requirements.txt", "templates/index.html"]
        result = await explorer.detect_framework(files)
        assert result["backend"] in ("flask", "unknown")

    @pytest.mark.asyncio
    async def test_detect_rails_from_gemfile(self, explorer: ExplorerAgent) -> None:
        files = ["Gemfile", "config/routes.rb", "app/controllers/application_controller.rb"]
        result = await explorer.detect_framework(files)
        assert result["backend"] == "rails"

    @pytest.mark.asyncio
    async def test_detect_express_from_package_json(self, explorer: ExplorerAgent) -> None:
        files = ["package.json", "server.js", "routes/users.js"]
        result = await explorer.detect_framework(files)
        assert "backend" in result

    @pytest.mark.asyncio
    async def test_detect_framework_returns_detected_flag(
        self, explorer: ExplorerAgent
    ) -> None:
        files = ["next.config.js", "package.json"]
        result = await explorer.detect_framework(files)
        assert "detected" in result
        assert isinstance(result["detected"], bool)

    @pytest.mark.asyncio
    async def test_detect_framework_empty_files_returns_unknown(
        self, explorer: ExplorerAgent
    ) -> None:
        result = await explorer.detect_framework([])
        assert result["frontend"] == "unknown"
        assert result["backend"] == "unknown"

    # --- explore_codebase ---

    @pytest.mark.asyncio
    async def test_explore_codebase_returns_required_keys(
        self, explorer: ExplorerAgent, tmp_path
    ) -> None:
        result = await explorer.explore_codebase(str(tmp_path))
        required_keys = {
            "framework",
            "routes",
            "api_endpoints",
            "forms",
            "auth_flows",
            "user_journeys",
            "static_assets",
            "test_coverage",
        }
        assert required_keys.issubset(result.keys())

    @pytest.mark.asyncio
    async def test_explore_codebase_routes_is_list(
        self, explorer: ExplorerAgent, tmp_path
    ) -> None:
        result = await explorer.explore_codebase(str(tmp_path))
        assert isinstance(result["routes"], list)

    @pytest.mark.asyncio
    async def test_explore_codebase_api_endpoints_is_list(
        self, explorer: ExplorerAgent, tmp_path
    ) -> None:
        result = await explorer.explore_codebase(str(tmp_path))
        assert isinstance(result["api_endpoints"], list)

    @pytest.mark.asyncio
    async def test_explore_codebase_user_journeys_is_list(
        self, explorer: ExplorerAgent, tmp_path
    ) -> None:
        result = await explorer.explore_codebase(str(tmp_path))
        assert isinstance(result["user_journeys"], list)

    @pytest.mark.asyncio
    async def test_explore_codebase_accepts_framework_hint(
        self, explorer: ExplorerAgent, tmp_path
    ) -> None:
        result = await explorer.explore_codebase(str(tmp_path), framework="nextjs")
        assert result["framework"]["frontend"] == "nextjs"

    # --- analyze_diff ---

    @pytest.mark.asyncio
    async def test_analyze_diff_returns_required_keys(
        self, explorer: ExplorerAgent
    ) -> None:
        changed_files = [
            {
                "path": "src/pages/login.tsx",
                "additions": 10,
                "deletions": 2,
                "patch": "@@ -1,5 +1,15 @@",
            }
        ]
        app_model = {
            "routes": [{"path": "/login", "component": "Login", "file": "src/pages/login.tsx"}],
            "user_journeys": [{"name": "User Login", "steps": [], "priority": "critical"}],
        }
        result = await explorer.analyze_diff(changed_files, app_model)
        assert "affected_routes" in result
        assert "affected_journeys" in result
        assert "risk_level" in result
        assert "suggested_tests" in result

    @pytest.mark.asyncio
    async def test_analyze_diff_risk_level_valid_values(
        self, explorer: ExplorerAgent
    ) -> None:
        changed_files = [{"path": "src/auth.ts", "additions": 50, "deletions": 30, "patch": ""}]
        result = await explorer.analyze_diff(changed_files, {})
        assert result["risk_level"] in ("low", "medium", "high")

    @pytest.mark.asyncio
    async def test_analyze_diff_empty_changes_low_risk(
        self, explorer: ExplorerAgent
    ) -> None:
        result = await explorer.analyze_diff([], {})
        assert result["risk_level"] == "low"

    # --- _run dispatch ---

    @pytest.mark.asyncio
    async def test_explorer_run_explore_codebase_action(
        self, explorer: ExplorerAgent, tmp_path
    ) -> None:
        task = AgentTask(
            agent_type="explorer",
            action="explore_codebase",
            params={"repo_path": str(tmp_path)},
        )
        result_task = await explorer.execute(task)
        assert result_task.status == AgentStatus.COMPLETED
        assert "framework" in result_task.result

    @pytest.mark.asyncio
    async def test_explorer_run_unknown_action_fails(
        self, explorer: ExplorerAgent
    ) -> None:
        task = AgentTask(agent_type="explorer", action="invalid_action", params={})
        result_task = await explorer.execute(task)
        assert result_task.status == AgentStatus.FAILED


# ---------------------------------------------------------------------------
# TestDesignerAgent Tests
# ---------------------------------------------------------------------------


class TestTestDesignerAgent:
    """Tests for TestDesignerAgent playbook generation."""

    @pytest.mark.asyncio
    async def test_generate_playbooks_returns_list(
        self, test_designer: TestDesignerAgent
    ) -> None:
        app_model = {
            "routes": [{"path": "/home", "component": "Home", "file": "pages/index.tsx", "methods": ["GET"]}],
            "user_journeys": [
                {"name": "Homepage Visit", "steps": ["navigate to /home"], "priority": "high"}
            ],
            "auth_flows": [],
            "api_endpoints": [],
        }
        result = await test_designer.generate_playbooks(app_model)
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_generate_playbooks_each_has_name(
        self, test_designer: TestDesignerAgent
    ) -> None:
        app_model = {
            "user_journeys": [
                {"name": "Login Flow", "steps": ["navigate", "fill", "submit"], "priority": "critical"}
            ],
            "routes": [],
            "auth_flows": [],
            "api_endpoints": [],
        }
        playbooks = await test_designer.generate_playbooks(app_model)
        assert len(playbooks) > 0
        for pb in playbooks:
            assert "name" in pb

    @pytest.mark.asyncio
    async def test_generate_playbooks_each_has_steps(
        self, test_designer: TestDesignerAgent
    ) -> None:
        app_model = {
            "user_journeys": [
                {"name": "Navigate Home", "steps": ["open homepage"], "priority": "medium"}
            ],
            "routes": [],
            "auth_flows": [],
            "api_endpoints": [],
        }
        playbooks = await test_designer.generate_playbooks(app_model)
        for pb in playbooks:
            assert "steps" in pb
            assert isinstance(pb["steps"], list)

    @pytest.mark.asyncio
    async def test_generate_auth_playbook_has_login_step(
        self, test_designer: TestDesignerAgent
    ) -> None:
        auth_flow = {
            "type": "form",
            "login_page": "/login",
            "fields": ["username", "password"],
        }
        playbook = await test_designer.generate_auth_playbook(auth_flow)
        assert "steps" in playbook
        step_actions = [s.get("action") for s in playbook["steps"]]
        assert "navigate" in step_actions

    @pytest.mark.asyncio
    async def test_generate_auth_playbook_includes_fill_steps(
        self, test_designer: TestDesignerAgent
    ) -> None:
        auth_flow = {
            "type": "form",
            "login_page": "/login",
            "fields": ["email", "password"],
        }
        playbook = await test_designer.generate_auth_playbook(auth_flow)
        step_actions = [s.get("action") for s in playbook["steps"]]
        assert "fill" in step_actions

    @pytest.mark.asyncio
    async def test_generate_crud_playbook_has_required_fields(
        self, test_designer: TestDesignerAgent
    ) -> None:
        endpoint = {"path": "/api/users", "method": "POST", "file": "routes/users.py", "handler": "create_user"}
        playbook = await test_designer.generate_crud_playbook(endpoint)
        assert "name" in playbook
        assert "steps" in playbook

    @pytest.mark.asyncio
    async def test_suggest_tests_for_diff_returns_list(
        self, test_designer: TestDesignerAgent
    ) -> None:
        diff_analysis = {
            "affected_routes": ["/login"],
            "affected_journeys": ["User Login"],
            "risk_level": "high",
            "suggested_tests": ["test login"],
        }
        existing_playbooks = [{"name": "Login Test", "steps": []}]
        result = await test_designer.suggest_tests_for_diff(diff_analysis, existing_playbooks)
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_suggest_tests_each_has_required_fields(
        self, test_designer: TestDesignerAgent
    ) -> None:
        diff_analysis = {
            "affected_routes": ["/checkout"],
            "affected_journeys": ["Checkout Flow"],
            "risk_level": "high",
            "suggested_tests": ["test checkout"],
        }
        suggestions = await test_designer.suggest_tests_for_diff(diff_analysis, [])
        for s in suggestions:
            assert "type" in s
            assert s["type"] in ("new", "modify")
            assert "playbook_name" in s
            assert "priority" in s

    @pytest.mark.asyncio
    async def test_designer_run_generate_playbooks_action(
        self, test_designer: TestDesignerAgent
    ) -> None:
        task = AgentTask(
            agent_type="test_designer",
            action="generate_playbooks",
            params={
                "app_model": {
                    "user_journeys": [],
                    "routes": [],
                    "auth_flows": [],
                    "api_endpoints": [],
                }
            },
        )
        result_task = await test_designer.execute(task)
        assert result_task.status == AgentStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_designer_run_unknown_action_fails(
        self, test_designer: TestDesignerAgent
    ) -> None:
        task = AgentTask(
            agent_type="test_designer", action="nonsense_action", params={}
        )
        result_task = await test_designer.execute(task)
        assert result_task.status == AgentStatus.FAILED


# ---------------------------------------------------------------------------
# TestRunnerAgent Tests
# ---------------------------------------------------------------------------


class TestTestRunnerAgent:
    """Tests for TestRunnerAgent step mapping and execution."""

    ALL_STEP_TYPES = [
        "navigate",
        "click",
        "fill",
        "type",
        "wait",
        "screenshot",
        "assert_visible",
        "assert_text",
        "assert_url",
        "evaluate",
        "select",
        "press_key",
        "wait_for_navigation",
    ]

    @pytest.mark.asyncio
    async def test_run_playbook_returns_required_keys(
        self, test_runner: TestRunnerAgent
    ) -> None:
        playbook = {
            "name": "Simple Test",
            "steps": [{"action": "navigate", "url": "https://example.com"}],
        }
        with patch.object(test_runner, "_ensure_browser", new_callable=AsyncMock), patch(
            "playwright.async_api.async_playwright"
        ):
            result = await test_runner.run_playbook(playbook, "https://example.com")
        required_keys = {"status", "steps", "duration_ms", "assertions"}
        assert required_keys.issubset(result.keys())

    @pytest.mark.asyncio
    async def test_run_playbook_status_valid_values(
        self, test_runner: TestRunnerAgent
    ) -> None:
        playbook = {"name": "Test", "steps": []}
        with patch.object(test_runner, "_ensure_browser", new_callable=AsyncMock):
            result = await test_runner.run_playbook(playbook, "https://example.com")
        assert result["status"] in ("passed", "failed", "error")

    @pytest.mark.asyncio
    async def test_execute_step_navigate_recognized(
        self, test_runner: TestRunnerAgent
    ) -> None:
        mock_page = AsyncMock()
        mock_page.goto = AsyncMock()
        step = {"action": "navigate", "url": "https://example.com"}
        result = await test_runner.execute_step(mock_page, step)
        assert result["status"] in ("passed", "failed", "error")
        mock_page.goto.assert_called_once_with("https://example.com")

    @pytest.mark.asyncio
    async def test_execute_step_click_recognized(
        self, test_runner: TestRunnerAgent
    ) -> None:
        mock_page = AsyncMock()
        mock_page.click = AsyncMock()
        step = {"action": "click", "selector": "#submit"}
        result = await test_runner.execute_step(mock_page, step)
        assert result["status"] in ("passed", "failed", "error")
        mock_page.click.assert_called_once_with("#submit")

    @pytest.mark.asyncio
    async def test_execute_step_fill_recognized(
        self, test_runner: TestRunnerAgent
    ) -> None:
        mock_page = AsyncMock()
        mock_page.fill = AsyncMock()
        step = {"action": "fill", "selector": "#email", "value": "user@example.com"}
        result = await test_runner.execute_step(mock_page, step)
        assert result["status"] in ("passed", "failed", "error")
        mock_page.fill.assert_called_once_with("#email", "user@example.com")

    @pytest.mark.asyncio
    async def test_execute_step_type_recognized(
        self, test_runner: TestRunnerAgent
    ) -> None:
        mock_page = AsyncMock()
        mock_page.type = AsyncMock()
        step = {"action": "type", "selector": "#search", "text": "hello"}
        result = await test_runner.execute_step(mock_page, step)
        assert result["status"] in ("passed", "failed", "error")

    @pytest.mark.asyncio
    async def test_execute_step_wait_recognized(
        self, test_runner: TestRunnerAgent
    ) -> None:
        mock_page = AsyncMock()
        mock_page.wait_for_selector = AsyncMock()
        step = {"action": "wait", "selector": ".loader", "state": "hidden"}
        result = await test_runner.execute_step(mock_page, step)
        assert result["status"] in ("passed", "failed", "error")

    @pytest.mark.asyncio
    async def test_execute_step_screenshot_recognized(
        self, test_runner: TestRunnerAgent
    ) -> None:
        mock_page = AsyncMock()
        mock_page.screenshot = AsyncMock(return_value=b"fake_png_data")
        step = {"action": "screenshot", "name": "homepage"}
        result = await test_runner.execute_step(mock_page, step)
        assert result["status"] in ("passed", "failed", "error")

    @pytest.mark.asyncio
    async def test_execute_step_assert_visible_recognized(
        self, test_runner: TestRunnerAgent
    ) -> None:
        mock_page = AsyncMock()
        mock_page.is_visible = AsyncMock(return_value=True)
        step = {"action": "assert_visible", "selector": ".hero"}
        result = await test_runner.execute_step(mock_page, step)
        assert result["status"] == "passed"

    @pytest.mark.asyncio
    async def test_execute_step_assert_visible_fails_when_not_visible(
        self, test_runner: TestRunnerAgent
    ) -> None:
        mock_page = AsyncMock()
        mock_page.is_visible = AsyncMock(return_value=False)
        step = {"action": "assert_visible", "selector": ".hero"}
        result = await test_runner.execute_step(mock_page, step)
        assert result["status"] == "failed"

    @pytest.mark.asyncio
    async def test_execute_step_assert_text_recognized(
        self, test_runner: TestRunnerAgent
    ) -> None:
        mock_page = AsyncMock()
        mock_page.inner_text = AsyncMock(return_value="Welcome!")
        step = {"action": "assert_text", "selector": "h1", "text": "Welcome!"}
        result = await test_runner.execute_step(mock_page, step)
        assert result["status"] == "passed"

    @pytest.mark.asyncio
    async def test_execute_step_assert_text_fails_on_mismatch(
        self, test_runner: TestRunnerAgent
    ) -> None:
        mock_page = AsyncMock()
        mock_page.inner_text = AsyncMock(return_value="Different text")
        step = {"action": "assert_text", "selector": "h1", "text": "Welcome!"}
        result = await test_runner.execute_step(mock_page, step)
        assert result["status"] == "failed"

    @pytest.mark.asyncio
    async def test_execute_step_assert_url_recognized(
        self, test_runner: TestRunnerAgent
    ) -> None:
        mock_page = AsyncMock()
        mock_page.url = "https://example.com/dashboard"
        step = {"action": "assert_url", "contains": "dashboard"}
        result = await test_runner.execute_step(mock_page, step)
        assert result["status"] == "passed"

    @pytest.mark.asyncio
    async def test_execute_step_assert_url_fails_when_not_matched(
        self, test_runner: TestRunnerAgent
    ) -> None:
        mock_page = AsyncMock()
        mock_page.url = "https://example.com/home"
        step = {"action": "assert_url", "contains": "dashboard"}
        result = await test_runner.execute_step(mock_page, step)
        assert result["status"] == "failed"

    @pytest.mark.asyncio
    async def test_execute_step_evaluate_recognized(
        self, test_runner: TestRunnerAgent
    ) -> None:
        mock_page = AsyncMock()
        mock_page.evaluate = AsyncMock(return_value=42)
        step = {"action": "evaluate", "script": "return document.title.length"}
        result = await test_runner.execute_step(mock_page, step)
        assert result["status"] in ("passed", "failed", "error")

    @pytest.mark.asyncio
    async def test_execute_step_select_recognized(
        self, test_runner: TestRunnerAgent
    ) -> None:
        mock_page = AsyncMock()
        mock_page.select_option = AsyncMock()
        step = {"action": "select", "selector": "#country", "value": "US"}
        result = await test_runner.execute_step(mock_page, step)
        assert result["status"] in ("passed", "failed", "error")

    @pytest.mark.asyncio
    async def test_execute_step_press_key_recognized(
        self, test_runner: TestRunnerAgent
    ) -> None:
        mock_page = AsyncMock()
        mock_page.keyboard = AsyncMock()
        mock_page.keyboard.press = AsyncMock()
        step = {"action": "press_key", "key": "Enter"}
        result = await test_runner.execute_step(mock_page, step)
        assert result["status"] in ("passed", "failed", "error")

    @pytest.mark.asyncio
    async def test_execute_step_wait_for_navigation_recognized(
        self, test_runner: TestRunnerAgent
    ) -> None:
        mock_page = AsyncMock()
        mock_page.wait_for_load_state = AsyncMock()
        step = {"action": "wait_for_navigation", "timeout": 5000}
        result = await test_runner.execute_step(mock_page, step)
        assert result["status"] in ("passed", "failed", "error")

    @pytest.mark.asyncio
    async def test_execute_step_unknown_action_returns_error(
        self, test_runner: TestRunnerAgent
    ) -> None:
        mock_page = AsyncMock()
        step = {"action": "beam_me_up", "target": "enterprise"}
        result = await test_runner.execute_step(mock_page, step)
        assert result["status"] == "error"

    @pytest.mark.asyncio
    async def test_execute_step_returns_duration_ms(
        self, test_runner: TestRunnerAgent
    ) -> None:
        mock_page = AsyncMock()
        mock_page.goto = AsyncMock()
        step = {"action": "navigate", "url": "https://example.com"}
        result = await test_runner.execute_step(mock_page, step)
        assert "duration_ms" in result
        assert isinstance(result["duration_ms"], int)
        assert result["duration_ms"] >= 0

    @pytest.mark.asyncio
    async def test_runner_run_playbook_action_via_execute(
        self, test_runner: TestRunnerAgent
    ) -> None:
        task = AgentTask(
            agent_type="test_runner",
            action="run_playbook",
            params={
                "playbook": {"name": "Smoke Test", "steps": []},
                "target_url": "https://example.com",
            },
        )
        with patch.object(test_runner, "_ensure_browser", new_callable=AsyncMock):
            result_task = await test_runner.execute(task)
        assert result_task.status == AgentStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_runner_unknown_action_fails(self, test_runner: TestRunnerAgent) -> None:
        task = AgentTask(
            agent_type="test_runner", action="fly_to_moon", params={}
        )
        result_task = await test_runner.execute(task)
        assert result_task.status == AgentStatus.FAILED


# ---------------------------------------------------------------------------
# AnalystAgent Tests
# ---------------------------------------------------------------------------


class TestAnalystAgent:
    """Tests for AnalystAgent analysis output structure."""

    @pytest.fixture
    def sample_test_run(self) -> dict:
        return {
            "id": "run-001",
            "status": "failed",
            "steps": [
                {"name": "Navigate to login", "status": "passed", "duration_ms": 120},
                {"name": "Fill credentials", "status": "passed", "duration_ms": 80},
                {"name": "Assert dashboard loaded", "status": "failed", "duration_ms": 5000, "error": "Timeout"},
            ],
            "duration_ms": 5200,
            "assertions": [
                {"name": "Page title", "passed": True},
                {"name": "Dashboard visible", "passed": False},
            ],
        }

    @pytest.mark.asyncio
    async def test_analyze_test_run_returns_required_keys(
        self, analyst: AnalystAgent, sample_test_run: dict
    ) -> None:
        result = await analyst.analyze_test_run(sample_test_run)
        required_keys = {
            "summary",
            "pass_rate",
            "failures",
            "performance_regressions",
            "quality_impact",
            "recommendations",
        }
        assert required_keys.issubset(result.keys())

    @pytest.mark.asyncio
    async def test_analyze_test_run_pass_rate_between_0_and_1(
        self, analyst: AnalystAgent, sample_test_run: dict
    ) -> None:
        result = await analyst.analyze_test_run(sample_test_run)
        assert 0.0 <= result["pass_rate"] <= 1.0

    @pytest.mark.asyncio
    async def test_analyze_test_run_failures_is_list(
        self, analyst: AnalystAgent, sample_test_run: dict
    ) -> None:
        result = await analyst.analyze_test_run(sample_test_run)
        assert isinstance(result["failures"], list)

    @pytest.mark.asyncio
    async def test_analyze_test_run_summary_is_string(
        self, analyst: AnalystAgent, sample_test_run: dict
    ) -> None:
        result = await analyst.analyze_test_run(sample_test_run)
        assert isinstance(result["summary"], str)
        assert len(result["summary"]) > 0

    @pytest.mark.asyncio
    async def test_analyze_test_run_recommendations_is_list(
        self, analyst: AnalystAgent, sample_test_run: dict
    ) -> None:
        result = await analyst.analyze_test_run(sample_test_run)
        assert isinstance(result["recommendations"], list)

    @pytest.mark.asyncio
    async def test_analyze_test_run_with_all_passing(
        self, analyst: AnalystAgent
    ) -> None:
        all_pass_run = {
            "status": "passed",
            "steps": [
                {"name": "Step 1", "status": "passed", "duration_ms": 100},
                {"name": "Step 2", "status": "passed", "duration_ms": 200},
            ],
            "assertions": [{"name": "Assert 1", "passed": True}],
        }
        result = await analyst.analyze_test_run(all_pass_run)
        assert result["pass_rate"] == 1.0
        assert result["failures"] == []

    @pytest.mark.asyncio
    async def test_correlate_deployment_returns_required_keys(
        self, analyst: AnalystAgent
    ) -> None:
        deployment = {"id": "deploy-001", "commit_sha": "abc123", "ref": "main"}
        test_results = [{"status": "failed", "steps": [], "assertions": []}]
        metrics_before = {"p50": 100, "p99": 400}
        metrics_after = {"p50": 120, "p99": 600}
        result = await analyst.correlate_deployment(
            deployment, test_results, metrics_before, metrics_after
        )
        required_keys = {
            "deployment_id",
            "quality_score_delta",
            "root_causes",
            "affected_endpoints",
            "recommendations",
        }
        assert required_keys.issubset(result.keys())

    @pytest.mark.asyncio
    async def test_identify_regressions_returns_list(
        self, analyst: AnalystAgent
    ) -> None:
        current = {"status": "failed", "steps": [], "assertions": [{"name": "X", "passed": False}]}
        historical = [
            {"status": "passed", "steps": [], "assertions": [{"name": "X", "passed": True}]}
        ]
        result = await analyst.identify_regressions(current, historical)
        assert isinstance(result, list)

    @pytest.mark.asyncio
    async def test_identify_regressions_each_has_type(
        self, analyst: AnalystAgent
    ) -> None:
        current = {"status": "failed", "steps": [], "assertions": [{"name": "X", "passed": False}]}
        historical = [
            {"status": "passed", "steps": [], "assertions": [{"name": "X", "passed": True}]}
        ]
        regressions = await analyst.identify_regressions(current, historical)
        valid_types = {"functional", "performance", "accessibility", "security"}
        for r in regressions:
            assert r["type"] in valid_types

    @pytest.mark.asyncio
    async def test_analyst_run_analyze_test_run_action(
        self, analyst: AnalystAgent
    ) -> None:
        task = AgentTask(
            agent_type="analyst",
            action="analyze_test_run",
            params={"test_run": {"status": "passed", "steps": [], "assertions": []}},
        )
        result_task = await analyst.execute(task)
        assert result_task.status == AgentStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_analyst_unknown_action_fails(self, analyst: AnalystAgent) -> None:
        task = AgentTask(agent_type="analyst", action="read_tea_leaves", params={})
        result_task = await analyst.execute(task)
        assert result_task.status == AgentStatus.FAILED


# ---------------------------------------------------------------------------
# ReporterAgent Tests
# ---------------------------------------------------------------------------


class TestReporterAgent:
    """Tests for ReporterAgent markdown formatting."""

    @pytest.fixture
    def sample_analysis(self) -> dict:
        return {
            "summary": "2 of 5 tests failed",
            "pass_rate": 0.6,
            "failures": [
                {"step": "Assert dashboard", "reason": "Element not found", "severity": "critical"}
            ],
            "performance_regressions": [],
            "quality_impact": {"score_delta": -5.0, "affected_components": ["login"]},
            "recommendations": ["Check auth service", "Review timeout settings"],
        }

    @pytest.fixture
    def sample_quality_score(self) -> dict:
        return {"score": 72.5, "trend": "declining", "grade": "C"}

    @pytest.mark.asyncio
    async def test_format_check_run_output_returns_required_keys(
        self, reporter: ReporterAgent, sample_analysis: dict
    ) -> None:
        result = await reporter.format_check_run_output(sample_analysis)
        required_keys = {"title", "summary", "text", "annotations", "conclusion"}
        assert required_keys.issubset(result.keys())

    @pytest.mark.asyncio
    async def test_format_check_run_conclusion_valid_values(
        self, reporter: ReporterAgent, sample_analysis: dict
    ) -> None:
        result = await reporter.format_check_run_output(sample_analysis)
        assert result["conclusion"] in ("success", "failure", "neutral")

    @pytest.mark.asyncio
    async def test_format_check_run_summary_is_markdown(
        self, reporter: ReporterAgent, sample_analysis: dict
    ) -> None:
        result = await reporter.format_check_run_output(sample_analysis)
        assert isinstance(result["summary"], str)
        assert len(result["summary"]) > 0

    @pytest.mark.asyncio
    async def test_format_check_run_high_pass_rate_is_success(
        self, reporter: ReporterAgent
    ) -> None:
        good_analysis = {
            "summary": "All tests passed",
            "pass_rate": 1.0,
            "failures": [],
            "performance_regressions": [],
            "quality_impact": {"score_delta": 2.0, "affected_components": []},
            "recommendations": [],
        }
        result = await reporter.format_check_run_output(good_analysis)
        assert result["conclusion"] == "success"

    @pytest.mark.asyncio
    async def test_format_check_run_failures_is_failure(
        self, reporter: ReporterAgent, sample_analysis: dict
    ) -> None:
        result = await reporter.format_check_run_output(sample_analysis)
        assert result["conclusion"] == "failure"

    @pytest.mark.asyncio
    async def test_format_pr_comment_returns_string(
        self, reporter: ReporterAgent, sample_analysis: dict, sample_quality_score: dict
    ) -> None:
        result = await reporter.format_pr_comment(sample_analysis, sample_quality_score)
        assert isinstance(result, str)
        assert len(result) > 0

    @pytest.mark.asyncio
    async def test_format_pr_comment_is_markdown(
        self, reporter: ReporterAgent, sample_analysis: dict, sample_quality_score: dict
    ) -> None:
        result = await reporter.format_pr_comment(sample_analysis, sample_quality_score)
        # Should contain markdown headers or formatting
        assert "#" in result or "**" in result or "|" in result

    @pytest.mark.asyncio
    async def test_format_quality_report_returns_required_keys(
        self, reporter: ReporterAgent
    ) -> None:
        quality_data = {"score": 85.0, "trend": "stable"}
        test_summary = {"total": 20, "passed": 18, "failed": 2, "pass_rate": 0.9}
        metrics_summary = {"avg_response_ms": 250, "error_rate": 0.01}
        result = await reporter.format_quality_report(
            "My Product", quality_data, test_summary, metrics_summary
        )
        required_keys = {"text", "summary", "score", "trend", "top_issues"}
        assert required_keys.issubset(result.keys())

    @pytest.mark.asyncio
    async def test_format_quality_report_score_is_float(
        self, reporter: ReporterAgent
    ) -> None:
        result = await reporter.format_quality_report(
            "Test Product",
            {"score": 75.0, "trend": "improving"},
            {"total": 10, "passed": 9, "failed": 1, "pass_rate": 0.9},
            {},
        )
        assert isinstance(result["score"], float)

    @pytest.mark.asyncio
    async def test_format_quality_report_text_contains_product_name(
        self, reporter: ReporterAgent
    ) -> None:
        result = await reporter.format_quality_report(
            "AcmeCorp Dashboard",
            {"score": 90.0, "trend": "stable"},
            {"total": 5, "passed": 5, "failed": 0, "pass_rate": 1.0},
            {},
        )
        assert "AcmeCorp Dashboard" in result["text"]

    @pytest.mark.asyncio
    async def test_format_alert_message_returns_required_keys(
        self, reporter: ReporterAgent
    ) -> None:
        alert = {
            "type": "anomaly",
            "severity": "critical",
            "endpoint": "/api/payments",
            "metric": "error_rate",
            "value": 0.15,
            "threshold": 0.05,
        }
        result = await reporter.format_alert_message(alert)
        assert "subject" in result
        assert "body" in result
        assert "severity" in result
        assert "actions" in result

    @pytest.mark.asyncio
    async def test_format_alert_message_severity_matches_input(
        self, reporter: ReporterAgent
    ) -> None:
        alert = {"type": "anomaly", "severity": "critical", "endpoint": "/api/pay"}
        result = await reporter.format_alert_message(alert)
        assert result["severity"] == "critical"

    @pytest.mark.asyncio
    async def test_reporter_run_format_quality_report_action(
        self, reporter: ReporterAgent
    ) -> None:
        task = AgentTask(
            agent_type="reporter",
            action="format_quality_report",
            params={
                "product_name": "Test App",
                "quality_data": {"score": 80.0, "trend": "stable"},
                "test_summary": {"total": 5, "passed": 4, "failed": 1, "pass_rate": 0.8},
                "metrics_summary": {},
            },
        )
        result_task = await reporter.execute(task)
        assert result_task.status == AgentStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_reporter_unknown_action_fails(self, reporter: ReporterAgent) -> None:
        task = AgentTask(agent_type="reporter", action="send_smoke_signals", params={})
        result_task = await reporter.execute(task)
        assert result_task.status == AgentStatus.FAILED


# ---------------------------------------------------------------------------
# Additional coverage tests
# ---------------------------------------------------------------------------


class TestExplorerCoverageExtra:
    """Additional ExplorerAgent tests for private helper coverage."""

    @pytest.mark.asyncio
    async def test_explore_codebase_with_real_files(
        self, explorer: ExplorerAgent, tmp_path
    ) -> None:
        """Test explore_codebase with actual files in a temp directory."""
        # Create a minimal Next.js-like structure
        (tmp_path / "next.config.js").write_text("module.exports = {}")
        (tmp_path / "package.json").write_text('{"name": "myapp"}')
        pages = tmp_path / "pages"
        pages.mkdir()
        (pages / "index.tsx").write_text("export default function Home() {}")
        (pages / "login.tsx").write_text("export default function Login() {}")
        api = tmp_path / "api"
        api.mkdir()
        (api / "users.py").write_text("def get_users(): pass")

        result = await explorer.explore_codebase(str(tmp_path))
        assert result["framework"]["frontend"] == "nextjs"
        assert len(result["routes"]) > 0
        assert len(result["api_endpoints"]) > 0

    @pytest.mark.asyncio
    async def test_explore_codebase_detects_auth_flow(
        self, explorer: ExplorerAgent, tmp_path
    ) -> None:
        """Auth flow detected when login-named file present."""
        pages = tmp_path / "pages"
        pages.mkdir()
        (pages / "login.tsx").write_text("export default function Login() {}")

        result = await explorer.explore_codebase(str(tmp_path))
        assert len(result["auth_flows"]) > 0

    @pytest.mark.asyncio
    async def test_explore_codebase_counts_static_assets(
        self, explorer: ExplorerAgent, tmp_path
    ) -> None:
        """Static asset counts are computed correctly."""
        (tmp_path / "app.css").write_text("body {}")
        (tmp_path / "logo.png").write_bytes(b"")
        (tmp_path / "main.js").write_text("console.log('hi')")

        result = await explorer.explore_codebase(str(tmp_path))
        assert result["static_assets"]["css_files"] >= 1
        assert result["static_assets"]["images"] >= 1
        assert result["static_assets"]["js_files"] >= 1

    @pytest.mark.asyncio
    async def test_explore_codebase_detects_pytest_framework(
        self, explorer: ExplorerAgent, tmp_path
    ) -> None:
        """Test coverage framework detected from pytest.ini."""
        (tmp_path / "pytest.ini").write_text("[pytest]")
        (tmp_path / "test_foo.py").write_text("def test_foo(): pass")

        result = await explorer.explore_codebase(str(tmp_path))
        assert result["test_coverage"]["test_framework"] == "pytest"
        assert result["test_coverage"]["existing_tests"] >= 1

    @pytest.mark.asyncio
    async def test_analyze_diff_matches_route_from_app_model(
        self, explorer: ExplorerAgent
    ) -> None:
        """Changed file that matches a known route's source file is marked affected."""
        changed_files = [
            {"path": "pages/dashboard.tsx", "additions": 5, "deletions": 1, "patch": ""}
        ]
        app_model = {
            "routes": [
                {"path": "/dashboard", "component": "Dashboard", "file": "pages/dashboard.tsx"}
            ],
            "user_journeys": [
                {"name": "Visit Dashboard", "steps": ["navigate to /dashboard"], "priority": "high"}
            ],
        }
        result = await explorer.analyze_diff(changed_files, app_model)
        assert "/dashboard" in result["affected_routes"]

    @pytest.mark.asyncio
    async def test_analyze_diff_high_risk_with_auth_file(
        self, explorer: ExplorerAgent
    ) -> None:
        """Auth file changes always trigger high risk."""
        changed_files = [
            {"path": "src/auth/login.ts", "additions": 10, "deletions": 5, "patch": ""}
        ]
        result = await explorer.analyze_diff(changed_files, {})
        assert result["risk_level"] == "high"

    @pytest.mark.asyncio
    async def test_analyze_diff_medium_risk_with_many_lines(
        self, explorer: ExplorerAgent
    ) -> None:
        """More than 50 changed lines raises risk to at least medium."""
        changed_files = [
            {"path": "src/component.tsx", "additions": 40, "deletions": 20, "patch": ""}
        ]
        result = await explorer.analyze_diff(changed_files, {})
        assert result["risk_level"] in ("medium", "high")

    @pytest.mark.asyncio
    async def test_detect_framework_with_vue_files_only(
        self, explorer: ExplorerAgent
    ) -> None:
        """Vue detected from .vue file extension without config file."""
        files = ["src/components/Header.vue", "src/App.vue", "package.json"]
        result = await explorer.detect_framework(files)
        assert result["frontend"] == "vue"

    @pytest.mark.asyncio
    async def test_detect_framework_express_backend(
        self, explorer: ExplorerAgent
    ) -> None:
        """Express detected from server.js in a Node project."""
        files = ["package.json", "server.js", "routes/api.js"]
        result = await explorer.detect_framework(files)
        assert result["backend"] == "express"

    @pytest.mark.asyncio
    async def test_explorer_discover_routes_action(
        self, explorer: ExplorerAgent, tmp_path
    ) -> None:
        """discover_routes action dispatches correctly."""
        pages = tmp_path / "pages"
        pages.mkdir()
        (pages / "home.tsx").write_text("")
        task = AgentTask(
            agent_type="explorer",
            action="discover_routes",
            params={"repo_path": str(tmp_path)},
        )
        result_task = await explorer.execute(task)
        assert result_task.status == AgentStatus.COMPLETED
        assert isinstance(result_task.result, list)

    @pytest.mark.asyncio
    async def test_explorer_discover_apis_action(
        self, explorer: ExplorerAgent, tmp_path
    ) -> None:
        """discover_apis action dispatches correctly."""
        api_dir = tmp_path / "api"
        api_dir.mkdir()
        (api_dir / "users.py").write_text("")
        task = AgentTask(
            agent_type="explorer",
            action="discover_apis",
            params={"repo_path": str(tmp_path)},
        )
        result_task = await explorer.execute(task)
        assert result_task.status == AgentStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_explorer_discover_forms_action(
        self, explorer: ExplorerAgent, tmp_path
    ) -> None:
        """discover_forms action dispatches correctly."""
        (tmp_path / "login_form.tsx").write_text("")
        task = AgentTask(
            agent_type="explorer",
            action="discover_forms",
            params={"repo_path": str(tmp_path)},
        )
        result_task = await explorer.execute(task)
        assert result_task.status == AgentStatus.COMPLETED


class TestTestRunnerCoverageExtra:
    """Additional TestRunnerAgent tests for coverage."""

    @pytest.mark.asyncio
    async def test_run_playbook_with_real_browser_mock(
        self, test_runner: TestRunnerAgent
    ) -> None:
        """run_playbook with mocked browser executes steps successfully."""
        mock_browser = AsyncMock()
        mock_context = AsyncMock()
        mock_page = AsyncMock()
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page
        mock_page.goto = AsyncMock()
        mock_page.is_visible = AsyncMock(return_value=True)
        mock_page.url = "https://example.com/dashboard"
        mock_page.evaluate = AsyncMock(return_value={"TTFB": 10, "domContentLoaded": 50, "pageLoad": 100})
        mock_page.close = AsyncMock()
        mock_context.close = AsyncMock()
        test_runner._browser = mock_browser

        playbook = {
            "name": "Full Test",
            "steps": [
                {"action": "navigate", "url": "https://example.com", "name": "Go home"},
                {"action": "assert_visible", "selector": ".hero", "name": "Hero visible"},
                {"action": "assert_url", "contains": "example.com", "name": "URL check"},
            ],
            "assertions": [{"name": "Page works", "type": "no_errors"}],
        }
        result = await test_runner.run_playbook(playbook, "https://example.com")
        assert result["status"] == "passed"
        assert len(result["steps"]) == 3
        assert result["duration_ms"] >= 0
        assert isinstance(result["assertions"], list)

    @pytest.mark.asyncio
    async def test_run_playbook_marks_failed_when_step_fails(
        self, test_runner: TestRunnerAgent
    ) -> None:
        """Overall status becomes 'failed' if any step fails."""
        mock_browser = AsyncMock()
        mock_context = AsyncMock()
        mock_page = AsyncMock()
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page
        mock_page.is_visible = AsyncMock(return_value=False)
        mock_page.evaluate = AsyncMock(return_value={})
        mock_page.close = AsyncMock()
        mock_context.close = AsyncMock()
        test_runner._browser = mock_browser

        playbook = {
            "name": "Failing Test",
            "steps": [{"action": "assert_visible", "selector": ".missing", "name": "Missing element"}],
            "assertions": [],
        }
        result = await test_runner.run_playbook(playbook, "https://example.com")
        assert result["status"] == "failed"

    @pytest.mark.asyncio
    async def test_run_playbook_collects_screenshot(
        self, test_runner: TestRunnerAgent
    ) -> None:
        """Screenshots are collected from screenshot steps."""
        mock_browser = AsyncMock()
        mock_context = AsyncMock()
        mock_page = AsyncMock()
        mock_browser.new_context.return_value = mock_context
        mock_context.new_page.return_value = mock_page
        mock_page.screenshot = AsyncMock(return_value=b"png_data")
        mock_page.evaluate = AsyncMock(return_value={})
        mock_page.close = AsyncMock()
        mock_context.close = AsyncMock()
        test_runner._browser = mock_browser

        playbook = {
            "name": "Screenshot Test",
            "steps": [{"action": "screenshot", "name": "capture_home"}],
            "assertions": [],
        }
        result = await test_runner.run_playbook(playbook, "https://example.com")
        assert len(result["screenshots"]) == 1

    @pytest.mark.asyncio
    async def test_run_suite_via_execute(self, test_runner: TestRunnerAgent) -> None:
        """run_suite dispatches correctly via execute."""
        task = AgentTask(
            agent_type="test_runner",
            action="run_suite",
            params={"playbooks": [], "target_url": "https://example.com"},
        )
        with patch.object(test_runner, "_ensure_browser", new_callable=AsyncMock):
            result_task = await test_runner.execute(task)
        assert result_task.status == AgentStatus.COMPLETED
        assert result_task.result["suite_status"] == "passed"

    @pytest.mark.asyncio
    async def test_cleanup_when_browser_set(self, test_runner: TestRunnerAgent) -> None:
        """cleanup closes browser and playwright instances."""
        mock_browser = AsyncMock()
        mock_playwright = AsyncMock()
        test_runner._browser = mock_browser
        test_runner._playwright = mock_playwright

        await test_runner.cleanup()

        mock_browser.close.assert_called_once()
        mock_playwright.stop.assert_called_once()
        assert test_runner._browser is None
        assert test_runner._playwright is None

    @pytest.mark.asyncio
    async def test_cleanup_when_browser_not_set(self, test_runner: TestRunnerAgent) -> None:
        """cleanup is a no-op when browser not initialised."""
        test_runner._browser = None
        test_runner._playwright = None
        await test_runner.cleanup()  # Should not raise

    @pytest.mark.asyncio
    async def test_ensure_browser_skips_if_already_set(
        self, test_runner: TestRunnerAgent
    ) -> None:
        """_ensure_browser is idempotent when already initialised."""
        mock_browser = MagicMock()
        test_runner._browser = mock_browser
        # Call should return without re-launching
        await test_runner._ensure_browser()
        assert test_runner._browser is mock_browser

    @pytest.mark.asyncio
    async def test_execute_step_fill_exception_status_error(
        self, test_runner: TestRunnerAgent
    ) -> None:
        """Non-assert step exception => status 'error'."""
        mock_page = AsyncMock()
        mock_page.fill = AsyncMock(side_effect=RuntimeError("element detached"))
        step = {"action": "fill", "selector": "#gone", "value": "x"}
        result = await test_runner.execute_step(mock_page, step)
        assert result["status"] == "error"
        assert "element detached" in result["error"]

    @pytest.mark.asyncio
    async def test_execute_step_assert_exception_status_failed(
        self, test_runner: TestRunnerAgent
    ) -> None:
        """Assert step exception => status 'failed'."""
        mock_page = AsyncMock()
        mock_page.is_visible = AsyncMock(side_effect=RuntimeError("timeout"))
        step = {"action": "assert_visible", "selector": ".missing"}
        result = await test_runner.execute_step(mock_page, step)
        assert result["status"] == "failed"


class TestAnalystCoverageExtra:
    """Additional AnalystAgent tests for coverage."""

    @pytest.mark.asyncio
    async def test_analyze_test_run_with_baselines_detects_regression(
        self, analyst: AnalystAgent
    ) -> None:
        """Performance regression is detected when duration exceeds baseline."""
        test_run = {
            "status": "passed",
            "steps": [{"name": "Login step", "status": "passed", "duration_ms": 2000}],
            "assertions": [],
        }
        baselines = {"Login step": {"duration_ms": 500}}
        result = await analyst.analyze_test_run(test_run, baselines)
        assert len(result["performance_regressions"]) > 0
        assert result["performance_regressions"][0]["endpoint"] == "Login step"

    @pytest.mark.asyncio
    async def test_identify_regressions_no_regression_when_rates_equal(
        self, analyst: AnalystAgent
    ) -> None:
        """No regression reported when pass rates are equal."""
        current = {"status": "passed", "steps": [{"name": "s", "status": "passed", "duration_ms": 100}], "assertions": []}
        historical = [{"status": "passed", "steps": [{"name": "s", "status": "passed", "duration_ms": 100}], "assertions": []}]
        result = await analyst.identify_regressions(current, historical)
        functional_regressions = [r for r in result if r["type"] == "functional"]
        assert functional_regressions == []

    @pytest.mark.asyncio
    async def test_identify_regressions_empty_history(
        self, analyst: AnalystAgent
    ) -> None:
        """Empty historical results returns empty regressions list."""
        current = {"status": "passed", "steps": [], "assertions": []}
        result = await analyst.identify_regressions(current, [])
        assert result == []

    @pytest.mark.asyncio
    async def test_correlate_deployment_with_metrics_delta(
        self, analyst: AnalystAgent
    ) -> None:
        """Metric deltas are surfaced as root causes."""
        deployment = {"id": "deploy-abc", "commit_sha": "abc123"}
        test_results = [{"status": "passed", "steps": [], "assertions": []}]
        metrics_before = {"p99": 200}
        metrics_after = {"p99": 400}
        result = await analyst.correlate_deployment(
            deployment, test_results, metrics_before, metrics_after
        )
        assert result["deployment_id"] == "deploy-abc"
        # p99 doubled — should appear in root causes
        assert len(result["root_causes"]) > 0

    @pytest.mark.asyncio
    async def test_analyst_generate_quality_report_action(
        self, analyst: AnalystAgent
    ) -> None:
        """generate_quality_report action dispatches correctly."""
        task = AgentTask(
            agent_type="analyst",
            action="generate_quality_report",
            params={"test_run": {"status": "passed", "steps": [], "assertions": []}},
        )
        result_task = await analyst.execute(task)
        assert result_task.status == AgentStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_analyst_correlate_deployment_action(
        self, analyst: AnalystAgent
    ) -> None:
        """correlate_deployment action dispatches correctly."""
        task = AgentTask(
            agent_type="analyst",
            action="correlate_deployment",
            params={
                "deployment": {"id": "dep-1"},
                "test_results": [],
                "metrics_before": {},
                "metrics_after": {},
            },
        )
        result_task = await analyst.execute(task)
        assert result_task.status == AgentStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_analyst_identify_regressions_action(
        self, analyst: AnalystAgent
    ) -> None:
        """identify_regressions action dispatches correctly."""
        task = AgentTask(
            agent_type="analyst",
            action="identify_regressions",
            params={
                "current_results": {"status": "passed", "steps": [], "assertions": []},
                "historical_results": [],
            },
        )
        result_task = await analyst.execute(task)
        assert result_task.status == AgentStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_regression_severity_critical(self, analyst: AnalystAgent) -> None:
        """A 30%+ drop in pass rate is classified as critical."""
        severity = analyst._regression_severity(0.5, 0.9)
        assert severity == "critical"

    @pytest.mark.asyncio
    async def test_regression_severity_major(self, analyst: AnalystAgent) -> None:
        """A 10-29% drop is classified as major."""
        severity = analyst._regression_severity(0.8, 0.95)
        assert severity == "major"

    @pytest.mark.asyncio
    async def test_regression_severity_minor(self, analyst: AnalystAgent) -> None:
        """A small drop is classified as minor."""
        severity = analyst._regression_severity(0.92, 0.95)
        assert severity == "minor"


class TestReporterCoverageExtra:
    """Additional ReporterAgent tests for coverage."""

    @pytest.mark.asyncio
    async def test_format_check_run_neutral_conclusion(
        self, reporter: ReporterAgent
    ) -> None:
        """Neutral conclusion when pass rate is below threshold but no explicit failures."""
        analysis = {
            "summary": "Partial pass",
            "pass_rate": 0.90,
            "failures": [],  # no explicit failures
            "performance_regressions": [],
            "quality_impact": {"score_delta": -1.0, "affected_components": []},
            "recommendations": [],
        }
        result = await reporter.format_check_run_output(analysis)
        assert result["conclusion"] == "neutral"

    @pytest.mark.asyncio
    async def test_format_alert_high_severity_actions(
        self, reporter: ReporterAgent
    ) -> None:
        """High severity alert includes review action."""
        alert = {"type": "spike", "severity": "high", "endpoint": "/api/orders"}
        result = await reporter.format_alert_message(alert)
        assert any("review" in a.lower() for a in result["actions"])

    @pytest.mark.asyncio
    async def test_format_quality_report_grade_a(
        self, reporter: ReporterAgent
    ) -> None:
        """Score >= 90 yields grade A."""
        result = await reporter.format_quality_report(
            "TopProduct",
            {"score": 95.0, "trend": "stable"},
            {"total": 10, "passed": 10, "failed": 0, "pass_rate": 1.0},
            {},
        )
        assert "A" in result["text"]

    @pytest.mark.asyncio
    async def test_format_quality_report_with_issues(
        self, reporter: ReporterAgent
    ) -> None:
        """Top issues reported when tests fail."""
        result = await reporter.format_quality_report(
            "BrokenApp",
            {"score": 40.0, "trend": "declining"},
            {"total": 10, "passed": 3, "failed": 7, "pass_rate": 0.3},
            {"avg_response_ms": 800, "error_rate": 0.1},
        )
        assert len(result["top_issues"]) > 0
        assert result["top_issues"][0]["severity"] == "critical"

    @pytest.mark.asyncio
    async def test_reporter_report_to_github_action(
        self, reporter: ReporterAgent
    ) -> None:
        """report_to_github action dispatches correctly."""
        task = AgentTask(
            agent_type="reporter",
            action="report_to_github",
            params={
                "analysis": {
                    "summary": "Passed",
                    "pass_rate": 1.0,
                    "failures": [],
                    "performance_regressions": [],
                    "quality_impact": {"score_delta": 0, "affected_components": []},
                    "recommendations": [],
                }
            },
        )
        result_task = await reporter.execute(task)
        assert result_task.status == AgentStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_reporter_create_pr_comment_action(
        self, reporter: ReporterAgent
    ) -> None:
        """create_pr_comment action dispatches correctly."""
        task = AgentTask(
            agent_type="reporter",
            action="create_pr_comment",
            params={
                "analysis": {
                    "summary": "All good",
                    "pass_rate": 1.0,
                    "failures": [],
                    "performance_regressions": [],
                    "quality_impact": {"score_delta": 0, "affected_components": []},
                    "recommendations": [],
                },
                "quality_score": {"score": 90.0, "trend": "stable", "grade": "A"},
            },
        )
        result_task = await reporter.execute(task)
        assert result_task.status == AgentStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_reporter_report_to_slack_action(
        self, reporter: ReporterAgent
    ) -> None:
        """report_to_slack action dispatches correctly."""
        task = AgentTask(
            agent_type="reporter",
            action="report_to_slack",
            params={"analysis": {"pass_rate": 0.8}},
        )
        result_task = await reporter.execute(task)
        assert result_task.status == AgentStatus.COMPLETED

    @pytest.mark.asyncio
    async def test_format_pr_comment_shows_failures(
        self, reporter: ReporterAgent
    ) -> None:
        """PR comment lists failures when they exist."""
        analysis = {
            "summary": "Tests failed",
            "pass_rate": 0.5,
            "failures": [{"step": "Login step", "reason": "Timeout", "severity": "critical"}],
            "performance_regressions": [],
            "quality_impact": {"score_delta": -10.0, "affected_components": ["auth"]},
            "recommendations": ["Check auth service"],
        }
        quality_score = {"score": 60.0, "trend": "declining", "grade": "D"}
        result = await reporter.format_pr_comment(analysis, quality_score)
        assert "Login step" in result
        assert "Timeout" in result

    @pytest.mark.asyncio
    async def test_format_check_run_has_annotations_for_failures(
        self, reporter: ReporterAgent
    ) -> None:
        """Failures produce annotations in the check run output."""
        analysis = {
            "summary": "Failed",
            "pass_rate": 0.0,
            "failures": [
                {"step": "Navigate to login", "reason": "Connection refused", "severity": "critical"}
            ],
            "performance_regressions": [],
            "quality_impact": {"score_delta": -20, "affected_components": []},
            "recommendations": [],
        }
        result = await reporter.format_check_run_output(analysis)
        assert len(result["annotations"]) > 0
        assert result["annotations"][0]["annotation_level"] == "failure"


class TestOrchestratorCoverageExtra:
    """Additional Orchestrator tests for coverage."""

    @pytest.mark.asyncio
    async def test_handle_schedule_triggered_event(
        self, orchestrator: Orchestrator
    ) -> None:
        """schedule_triggered creates a run_suite task."""
        tasks = await orchestrator.handle_event(
            "schedule_triggered", {"product_id": "prod-1"}
        )
        assert len(tasks) > 0

    @pytest.mark.asyncio
    async def test_handle_manual_request_event(
        self, orchestrator: Orchestrator
    ) -> None:
        """manual_request creates a task with specified action."""
        orchestrator.register_agent(ConcreteAgent("orchestrator"))
        tasks = await orchestrator.handle_event(
            "manual_request",
            {
                "agent_type": "orchestrator",
                "action": "get_status",
                "params": {},
            },
        )
        assert len(tasks) > 0

    @pytest.mark.asyncio
    async def test_orchestrator_init_monitoring_action(
        self, orchestrator: Orchestrator
    ) -> None:
        """Orchestrator handles init_monitoring action."""
        task = AgentTask(
            agent_type="orchestrator",
            action="init_monitoring",
            params={"product_id": "prod-123"},
        )
        result_task = await orchestrator.execute(task)
        assert result_task.status == AgentStatus.COMPLETED
        assert result_task.result["product_id"] == "prod-123"

    @pytest.mark.asyncio
    async def test_orchestrator_unknown_action_fails(
        self, orchestrator: Orchestrator
    ) -> None:
        """Orchestrator raises for unknown action in _run."""
        task = AgentTask(
            agent_type="orchestrator", action="fly_to_mars", params={}
        )
        result_task = await orchestrator.execute(task)
        assert result_task.status == AgentStatus.FAILED
