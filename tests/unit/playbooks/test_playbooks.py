"""
Unit tests for the TINAA Playbook Engine.

Covers: schema, parsing, validation, executor results.
TDD order: RED -> GREEN -> REFACTOR
"""

from __future__ import annotations

import json
import pytest
import pytest_asyncio
from dataclasses import asdict
from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch

from tinaa.playbooks.schema import (
    PlaybookDefinition,
    PlaybookStep,
    PlaybookTrigger,
    PlaybookAssertion,
    PerformanceGate,
    StepAction,
    Priority,
    PlaybookSource,
)
from tinaa.playbooks.parser import PlaybookParser
from tinaa.playbooks.validator import PlaybookValidator, ValidationError
from tinaa.playbooks.executor import PlaybookExecutor, PlaybookResult, StepResult


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def parser() -> PlaybookParser:
    return PlaybookParser()


@pytest.fixture
def validator() -> PlaybookValidator:
    return PlaybookValidator()


@pytest.fixture
def executor() -> PlaybookExecutor:
    return PlaybookExecutor()


@pytest.fixture
def minimal_playbook() -> PlaybookDefinition:
    """Smallest valid playbook."""
    return PlaybookDefinition(
        name="Minimal",
        steps=[
            PlaybookStep(
                action=StepAction.NAVIGATE,
                params={"url": "https://example.com"},
            )
        ],
    )


@pytest.fixture
def login_yaml() -> str:
    return """
playbook:
  name: "Login Flow"
  description: "Test the standard login flow"
  priority: critical
  tags:
    - auth
    - smoke
  trigger:
    on_deploy:
      - staging
      - production
    on_pr: true
    schedule: "*/30 * * * *"
    on_change:
      - "src/auth/**"
  steps:
    - navigate: "${base_url}/login"
    - assert_visible: "[data-testid='login-form']"
    - fill:
        selector: "[name='email']"
        value: "${credentials.email}"
    - fill:
        selector: "[name='password']"
        value: "${credentials.password}"
    - click: "[type='submit']"
    - wait_for_navigation:
        timeout: 5000
    - assert_url:
        contains: "/dashboard"
    - screenshot: "post-login"
  performance_gates:
    total_duration: "< 4s"
    lcp: "< 2.5s"
    fcp: "< 1.8s"
  assertions:
    no_console_errors: true
    no_network_failures: false
"""


@pytest.fixture
def login_json() -> str:
    data = {
        "playbook": {
            "name": "Login Flow JSON",
            "description": "JSON variant",
            "priority": "high",
            "steps": [
                {"navigate": "https://example.com/login"},
                {"click": "#submit"},
                {"assert_url": {"equals": "https://example.com/dashboard"}},
            ],
        }
    }
    return json.dumps(data)


# ---------------------------------------------------------------------------
# Schema Tests
# ---------------------------------------------------------------------------

class TestStepActionEnum:
    """All expected step actions must exist in the enum."""

    def test_navigate_action(self) -> None:
        assert StepAction.NAVIGATE == "navigate"

    def test_click_action(self) -> None:
        assert StepAction.CLICK == "click"

    def test_fill_action(self) -> None:
        assert StepAction.FILL == "fill"

    def test_type_action(self) -> None:
        assert StepAction.TYPE == "type"

    def test_select_action(self) -> None:
        assert StepAction.SELECT == "select"

    def test_press_key_action(self) -> None:
        assert StepAction.PRESS_KEY == "press_key"

    def test_wait_action(self) -> None:
        assert StepAction.WAIT == "wait"

    def test_wait_for_navigation_action(self) -> None:
        assert StepAction.WAIT_FOR_NAVIGATION == "wait_for_navigation"

    def test_screenshot_action(self) -> None:
        assert StepAction.SCREENSHOT == "screenshot"

    def test_assert_visible_action(self) -> None:
        assert StepAction.ASSERT_VISIBLE == "assert_visible"

    def test_assert_hidden_action(self) -> None:
        assert StepAction.ASSERT_HIDDEN == "assert_hidden"

    def test_assert_text_action(self) -> None:
        assert StepAction.ASSERT_TEXT == "assert_text"

    def test_assert_url_action(self) -> None:
        assert StepAction.ASSERT_URL == "assert_url"

    def test_assert_title_action(self) -> None:
        assert StepAction.ASSERT_TITLE == "assert_title"

    def test_assert_no_console_errors_action(self) -> None:
        assert StepAction.ASSERT_NO_CONSOLE_ERRORS == "assert_no_console_errors"

    def test_assert_no_network_failures_action(self) -> None:
        assert StepAction.ASSERT_NO_NETWORK_FAILURES == "assert_no_network_failures"

    def test_assert_accessibility_action(self) -> None:
        assert StepAction.ASSERT_ACCESSIBILITY == "assert_accessibility"

    def test_evaluate_action(self) -> None:
        assert StepAction.EVALUATE == "evaluate"

    def test_hover_action(self) -> None:
        assert StepAction.HOVER == "hover"

    def test_scroll_action(self) -> None:
        assert StepAction.SCROLL == "scroll"

    def test_upload_file_action(self) -> None:
        assert StepAction.UPLOAD_FILE == "upload_file"

    def test_set_viewport_action(self) -> None:
        assert StepAction.SET_VIEWPORT == "set_viewport"

    def test_clear_action(self) -> None:
        assert StepAction.CLEAR == "clear"

    def test_group_action(self) -> None:
        assert StepAction.GROUP == "group"

    def test_all_actions_are_strings(self) -> None:
        for action in StepAction:
            assert isinstance(action.value, str)


class TestPlaybookStep:
    """PlaybookStep dataclass defaults and behavior."""

    def test_step_defaults(self) -> None:
        step = PlaybookStep(action=StepAction.CLICK)
        assert step.params == {}
        assert step.timeout_ms == 30000
        assert step.optional is False
        assert step.retry_count == 0
        assert step.description is None
        assert step.steps is None

    def test_step_with_params(self) -> None:
        step = PlaybookStep(
            action=StepAction.FILL,
            params={"selector": "#email", "value": "test@example.com"},
        )
        assert step.params["selector"] == "#email"
        assert step.params["value"] == "test@example.com"

    def test_group_step_with_substeps(self) -> None:
        sub = PlaybookStep(action=StepAction.CLICK, params={"selector": "#btn"})
        group = PlaybookStep(action=StepAction.GROUP, steps=[sub])
        assert group.steps is not None
        assert len(group.steps) == 1


class TestPlaybookDefinition:
    """PlaybookDefinition dataclass properties."""

    def test_total_steps_main_only(self, minimal_playbook: PlaybookDefinition) -> None:
        assert minimal_playbook.total_steps == 1

    def test_total_steps_with_setup_and_teardown(self) -> None:
        pb = PlaybookDefinition(
            name="Full",
            steps=[PlaybookStep(action=StepAction.CLICK)],
            setup_steps=[PlaybookStep(action=StepAction.NAVIGATE, params={"url": "/"})],
            teardown_steps=[
                PlaybookStep(action=StepAction.SCREENSHOT),
                PlaybookStep(action=StepAction.SCREENSHOT),
            ],
        )
        assert pb.total_steps == 4  # 1 main + 1 setup + 2 teardown

    def test_default_priority_is_medium(self) -> None:
        pb = PlaybookDefinition(name="X", steps=[])
        assert pb.priority == Priority.MEDIUM

    def test_default_source_is_manual(self) -> None:
        pb = PlaybookDefinition(name="X", steps=[])
        assert pb.source == PlaybookSource.MANUAL

    def test_tags_default_empty(self) -> None:
        pb = PlaybookDefinition(name="X", steps=[])
        assert pb.tags == []

    def test_variables_default_empty(self) -> None:
        pb = PlaybookDefinition(name="X", steps=[])
        assert pb.variables == {}


# ---------------------------------------------------------------------------
# Parser Tests
# ---------------------------------------------------------------------------

class TestPlaybookParserYAML:
    """YAML parsing tests."""

    def test_parse_yaml_returns_playbook_definition(
        self, parser: PlaybookParser, login_yaml: str
    ) -> None:
        pb = parser.parse_yaml(login_yaml)
        assert isinstance(pb, PlaybookDefinition)

    def test_parse_yaml_name(self, parser: PlaybookParser, login_yaml: str) -> None:
        pb = parser.parse_yaml(login_yaml)
        assert pb.name == "Login Flow"

    def test_parse_yaml_description(self, parser: PlaybookParser, login_yaml: str) -> None:
        pb = parser.parse_yaml(login_yaml)
        assert pb.description == "Test the standard login flow"

    def test_parse_yaml_priority_critical(
        self, parser: PlaybookParser, login_yaml: str
    ) -> None:
        pb = parser.parse_yaml(login_yaml)
        assert pb.priority == Priority.CRITICAL

    def test_parse_yaml_tags(self, parser: PlaybookParser, login_yaml: str) -> None:
        pb = parser.parse_yaml(login_yaml)
        assert "auth" in pb.tags
        assert "smoke" in pb.tags

    def test_parse_yaml_step_count(self, parser: PlaybookParser, login_yaml: str) -> None:
        pb = parser.parse_yaml(login_yaml)
        assert len(pb.steps) == 8

    def test_parse_yaml_navigate_step(self, parser: PlaybookParser, login_yaml: str) -> None:
        pb = parser.parse_yaml(login_yaml)
        assert pb.steps[0].action == StepAction.NAVIGATE
        assert pb.steps[0].params["url"] == "${base_url}/login"

    def test_parse_yaml_assert_visible_shorthand(
        self, parser: PlaybookParser, login_yaml: str
    ) -> None:
        pb = parser.parse_yaml(login_yaml)
        assert pb.steps[1].action == StepAction.ASSERT_VISIBLE
        assert pb.steps[1].params["selector"] == "[data-testid='login-form']"

    def test_parse_yaml_fill_step_with_subkeys(
        self, parser: PlaybookParser, login_yaml: str
    ) -> None:
        pb = parser.parse_yaml(login_yaml)
        fill_step = pb.steps[2]
        assert fill_step.action == StepAction.FILL
        assert fill_step.params["selector"] == "[name='email']"
        assert fill_step.params["value"] == "${credentials.email}"

    def test_parse_yaml_click_shorthand(
        self, parser: PlaybookParser, login_yaml: str
    ) -> None:
        pb = parser.parse_yaml(login_yaml)
        assert pb.steps[4].action == StepAction.CLICK
        assert pb.steps[4].params["selector"] == "[type='submit']"

    def test_parse_yaml_wait_for_navigation_with_timeout(
        self, parser: PlaybookParser, login_yaml: str
    ) -> None:
        pb = parser.parse_yaml(login_yaml)
        nav_step = pb.steps[5]
        assert nav_step.action == StepAction.WAIT_FOR_NAVIGATION
        assert nav_step.timeout_ms == 5000

    def test_parse_yaml_assert_url_contains(
        self, parser: PlaybookParser, login_yaml: str
    ) -> None:
        pb = parser.parse_yaml(login_yaml)
        url_step = pb.steps[6]
        assert url_step.action == StepAction.ASSERT_URL
        assert url_step.params["contains"] == "/dashboard"

    def test_parse_yaml_screenshot_shorthand(
        self, parser: PlaybookParser, login_yaml: str
    ) -> None:
        pb = parser.parse_yaml(login_yaml)
        ss_step = pb.steps[7]
        assert ss_step.action == StepAction.SCREENSHOT

    def test_parse_yaml_trigger_on_deploy(
        self, parser: PlaybookParser, login_yaml: str
    ) -> None:
        pb = parser.parse_yaml(login_yaml)
        assert pb.trigger is not None
        assert "staging" in pb.trigger.on_deploy
        assert "production" in pb.trigger.on_deploy

    def test_parse_yaml_trigger_on_pr(
        self, parser: PlaybookParser, login_yaml: str
    ) -> None:
        pb = parser.parse_yaml(login_yaml)
        assert pb.trigger.on_pr is True

    def test_parse_yaml_trigger_schedule(
        self, parser: PlaybookParser, login_yaml: str
    ) -> None:
        pb = parser.parse_yaml(login_yaml)
        assert pb.trigger.schedule_cron == "*/30 * * * *"

    def test_parse_yaml_trigger_on_change(
        self, parser: PlaybookParser, login_yaml: str
    ) -> None:
        pb = parser.parse_yaml(login_yaml)
        assert pb.trigger.on_change == ["src/auth/**"]

    def test_parse_yaml_performance_gates_total_duration(
        self, parser: PlaybookParser, login_yaml: str
    ) -> None:
        pb = parser.parse_yaml(login_yaml)
        assert pb.performance_gates is not None
        assert pb.performance_gates.total_duration_ms == 4000

    def test_parse_yaml_performance_gates_lcp(
        self, parser: PlaybookParser, login_yaml: str
    ) -> None:
        pb = parser.parse_yaml(login_yaml)
        assert pb.performance_gates.lcp_ms == 2500.0

    def test_parse_yaml_performance_gates_fcp(
        self, parser: PlaybookParser, login_yaml: str
    ) -> None:
        pb = parser.parse_yaml(login_yaml)
        assert pb.performance_gates.fcp_ms == 1800.0

    def test_parse_yaml_assertions_no_console_errors(
        self, parser: PlaybookParser, login_yaml: str
    ) -> None:
        pb = parser.parse_yaml(login_yaml)
        assert pb.assertions is not None
        assert pb.assertions.no_console_errors is True

    def test_parse_yaml_assertions_no_network_failures(
        self, parser: PlaybookParser, login_yaml: str
    ) -> None:
        pb = parser.parse_yaml(login_yaml)
        assert pb.assertions.no_network_failures is False

    def test_parse_invalid_yaml_raises_value_error(
        self, parser: PlaybookParser
    ) -> None:
        with pytest.raises(ValueError, match="Invalid YAML"):
            parser.parse_yaml("not: valid: yaml: [[[")

    def test_parse_yaml_missing_playbook_key_raises(
        self, parser: PlaybookParser
    ) -> None:
        with pytest.raises(ValueError, match="playbook"):
            parser.parse_yaml("name: foo\nsteps: []")

    def test_parse_yaml_missing_name_raises(self, parser: PlaybookParser) -> None:
        with pytest.raises(ValueError, match="name"):
            parser.parse_yaml("playbook:\n  steps: []")


class TestPlaybookParserJSON:
    """JSON parsing tests."""

    def test_parse_json_returns_playbook_definition(
        self, parser: PlaybookParser, login_json: str
    ) -> None:
        pb = parser.parse_json(login_json)
        assert isinstance(pb, PlaybookDefinition)

    def test_parse_json_name(self, parser: PlaybookParser, login_json: str) -> None:
        pb = parser.parse_json(login_json)
        assert pb.name == "Login Flow JSON"

    def test_parse_json_step_count(
        self, parser: PlaybookParser, login_json: str
    ) -> None:
        pb = parser.parse_json(login_json)
        assert len(pb.steps) == 3

    def test_parse_json_navigate_step(
        self, parser: PlaybookParser, login_json: str
    ) -> None:
        pb = parser.parse_json(login_json)
        assert pb.steps[0].action == StepAction.NAVIGATE
        assert pb.steps[0].params["url"] == "https://example.com/login"

    def test_parse_json_assert_url_equals(
        self, parser: PlaybookParser, login_json: str
    ) -> None:
        pb = parser.parse_json(login_json)
        url_step = pb.steps[2]
        assert url_step.action == StepAction.ASSERT_URL
        assert url_step.params["equals"] == "https://example.com/dashboard"

    def test_parse_invalid_json_raises_value_error(
        self, parser: PlaybookParser
    ) -> None:
        with pytest.raises(ValueError, match="Invalid JSON"):
            parser.parse_json("{not valid json}")


class TestPlaybookParserDict:
    """dict parsing tests."""

    def test_parse_dict_basic(self, parser: PlaybookParser) -> None:
        data = {
            "playbook": {
                "name": "Dict Playbook",
                "steps": [{"navigate": "https://example.com"}],
            }
        }
        pb = parser.parse_dict(data)
        assert pb.name == "Dict Playbook"
        assert pb.steps[0].action == StepAction.NAVIGATE

    def test_parse_dict_with_setup_and_teardown(self, parser: PlaybookParser) -> None:
        data = {
            "playbook": {
                "name": "Setup/Teardown",
                "steps": [{"click": "#btn"}],
                "setup_steps": [{"navigate": "https://example.com"}],
                "teardown_steps": [{"screenshot": "after"}],
            }
        }
        pb = parser.parse_dict(data)
        assert pb.setup_steps is not None
        assert len(pb.setup_steps) == 1
        assert pb.teardown_steps is not None
        assert len(pb.teardown_steps) == 1

    def test_parse_dict_with_variables(self, parser: PlaybookParser) -> None:
        data = {
            "playbook": {
                "name": "Vars",
                "variables": {"env": "staging", "timeout": "5000"},
                "steps": [{"navigate": "${env}"}],
            }
        }
        pb = parser.parse_dict(data)
        assert pb.variables == {"env": "staging", "timeout": "5000"}


class TestPlaybookParserStepFormats:
    """Step shorthand/longhand parsing."""

    def test_shorthand_navigate(self, parser: PlaybookParser) -> None:
        step = parser._parse_step({"navigate": "https://example.com"})
        assert step.action == StepAction.NAVIGATE
        assert step.params["url"] == "https://example.com"

    def test_shorthand_click_selector(self, parser: PlaybookParser) -> None:
        step = parser._parse_step({"click": "#button"})
        assert step.action == StepAction.CLICK
        assert step.params["selector"] == "#button"

    def test_shorthand_assert_visible(self, parser: PlaybookParser) -> None:
        step = parser._parse_step({"assert_visible": ".modal"})
        assert step.action == StepAction.ASSERT_VISIBLE
        assert step.params["selector"] == ".modal"

    def test_shorthand_assert_hidden(self, parser: PlaybookParser) -> None:
        step = parser._parse_step({"assert_hidden": ".spinner"})
        assert step.action == StepAction.ASSERT_HIDDEN
        assert step.params["selector"] == ".spinner"

    def test_shorthand_hover(self, parser: PlaybookParser) -> None:
        step = parser._parse_step({"hover": "#menu"})
        assert step.action == StepAction.HOVER
        assert step.params["selector"] == "#menu"

    def test_shorthand_clear(self, parser: PlaybookParser) -> None:
        step = parser._parse_step({"clear": "#input"})
        assert step.action == StepAction.CLEAR
        assert step.params["selector"] == "#input"

    def test_shorthand_screenshot_with_name(self, parser: PlaybookParser) -> None:
        step = parser._parse_step({"screenshot": "my-shot"})
        assert step.action == StepAction.SCREENSHOT
        assert step.params.get("name") == "my-shot"

    def test_shorthand_assert_url_string(self, parser: PlaybookParser) -> None:
        step = parser._parse_step({"assert_url": "/dashboard"})
        assert step.action == StepAction.ASSERT_URL
        assert step.params["contains"] == "/dashboard"

    def test_shorthand_assert_title_string(self, parser: PlaybookParser) -> None:
        step = parser._parse_step({"assert_title": "My App"})
        assert step.action == StepAction.ASSERT_TITLE
        assert step.params["contains"] == "My App"

    def test_longhand_action_form(self, parser: PlaybookParser) -> None:
        step = parser._parse_step({
            "action": "navigate",
            "url": "https://example.com",
            "description": "Go home",
        })
        assert step.action == StepAction.NAVIGATE
        assert step.params["url"] == "https://example.com"
        assert step.description == "Go home"

    def test_longhand_with_timeout(self, parser: PlaybookParser) -> None:
        step = parser._parse_step({
            "action": "click",
            "selector": "#btn",
            "timeout": 10000,
        })
        assert step.timeout_ms == 10000

    def test_longhand_with_optional_flag(self, parser: PlaybookParser) -> None:
        step = parser._parse_step({
            "action": "screenshot",
            "optional": True,
        })
        assert step.optional is True

    def test_fill_longhand_with_selector_and_value(self, parser: PlaybookParser) -> None:
        step = parser._parse_step({
            "fill": {"selector": "#email", "value": "test@test.com"}
        })
        assert step.action == StepAction.FILL
        assert step.params["selector"] == "#email"
        assert step.params["value"] == "test@test.com"

    def test_wait_for_navigation_with_timeout_key(self, parser: PlaybookParser) -> None:
        step = parser._parse_step({"wait_for_navigation": {"timeout": 5000}})
        assert step.action == StepAction.WAIT_FOR_NAVIGATION
        assert step.timeout_ms == 5000

    def test_unknown_action_raises(self, parser: PlaybookParser) -> None:
        with pytest.raises(ValueError, match="Unknown action"):
            parser._parse_step({"do_something_unknown": "#foo"})


class TestDurationParsing:
    """_parse_duration converts strings to milliseconds."""

    def test_seconds_integer(self, parser: PlaybookParser) -> None:
        assert parser._parse_duration("4s") == 4000

    def test_seconds_float(self, parser: PlaybookParser) -> None:
        assert parser._parse_duration("2.5s") == 2500

    def test_milliseconds(self, parser: PlaybookParser) -> None:
        assert parser._parse_duration("500ms") == 500

    def test_milliseconds_int(self, parser: PlaybookParser) -> None:
        assert parser._parse_duration("1000ms") == 1000

    def test_less_than_prefix_seconds(self, parser: PlaybookParser) -> None:
        assert parser._parse_duration("< 4s") == 4000

    def test_less_than_prefix_ms(self, parser: PlaybookParser) -> None:
        assert parser._parse_duration("< 500ms") == 500

    def test_less_than_no_space(self, parser: PlaybookParser) -> None:
        assert parser._parse_duration("<2.5s") == 2500

    def test_minutes(self, parser: PlaybookParser) -> None:
        assert parser._parse_duration("1m") == 60000

    def test_invalid_duration_raises(self, parser: PlaybookParser) -> None:
        with pytest.raises(ValueError, match="Cannot parse duration"):
            parser._parse_duration("very long time")


class TestVariableResolution:
    """resolve_variables replaces ${...} in step params."""

    def test_resolve_base_url(self, parser: PlaybookParser) -> None:
        pb = PlaybookDefinition(
            name="X",
            steps=[
                PlaybookStep(
                    action=StepAction.NAVIGATE,
                    params={"url": "${base_url}/login"},
                )
            ],
        )
        resolved = parser.resolve_variables(pb, {"base_url": "https://app.example.com"})
        assert resolved.steps[0].params["url"] == "https://app.example.com/login"

    def test_resolve_nested_variable_credentials_email(
        self, parser: PlaybookParser
    ) -> None:
        pb = PlaybookDefinition(
            name="X",
            steps=[
                PlaybookStep(
                    action=StepAction.FILL,
                    params={"selector": "#email", "value": "${credentials.email}"},
                )
            ],
        )
        resolved = parser.resolve_variables(
            pb, {"credentials.email": "user@test.com"}
        )
        assert resolved.steps[0].params["value"] == "user@test.com"

    def test_resolve_custom_variable_from_playbook(
        self, parser: PlaybookParser
    ) -> None:
        pb = PlaybookDefinition(
            name="X",
            variables={"env": "staging"},
            steps=[
                PlaybookStep(
                    action=StepAction.NAVIGATE,
                    params={"url": "https://${env}.example.com"},
                )
            ],
        )
        resolved = parser.resolve_variables(pb, {})
        assert resolved.steps[0].params["url"] == "https://staging.example.com"

    def test_passed_variables_override_playbook_variables(
        self, parser: PlaybookParser
    ) -> None:
        pb = PlaybookDefinition(
            name="X",
            variables={"env": "staging"},
            steps=[
                PlaybookStep(
                    action=StepAction.NAVIGATE,
                    params={"url": "https://${env}.example.com"},
                )
            ],
        )
        resolved = parser.resolve_variables(pb, {"env": "production"})
        assert resolved.steps[0].params["url"] == "https://production.example.com"

    def test_resolve_timestamp_is_substituted(self, parser: PlaybookParser) -> None:
        pb = PlaybookDefinition(
            name="X",
            steps=[
                PlaybookStep(
                    action=StepAction.SCREENSHOT,
                    params={"name": "shot-${timestamp}"},
                )
            ],
        )
        resolved = parser.resolve_variables(pb, {})
        name = resolved.steps[0].params["name"]
        assert "${timestamp}" not in name
        assert "shot-" in name

    def test_resolve_random_string_is_substituted(
        self, parser: PlaybookParser
    ) -> None:
        pb = PlaybookDefinition(
            name="X",
            steps=[
                PlaybookStep(
                    action=StepAction.FILL,
                    params={"value": "user-${random_string}"},
                )
            ],
        )
        resolved = parser.resolve_variables(pb, {})
        value = resolved.steps[0].params["value"]
        assert "${random_string}" not in value
        assert "user-" in value

    def test_unresolved_variables_remain_intact(self, parser: PlaybookParser) -> None:
        """Variables not in scope are left as-is for downstream resolution."""
        pb = PlaybookDefinition(
            name="X",
            steps=[
                PlaybookStep(
                    action=StepAction.NAVIGATE,
                    params={"url": "${unknown_var}/path"},
                )
            ],
        )
        resolved = parser.resolve_variables(pb, {})
        assert resolved.steps[0].params["url"] == "${unknown_var}/path"

    def test_resolve_setup_steps(self, parser: PlaybookParser) -> None:
        pb = PlaybookDefinition(
            name="X",
            steps=[PlaybookStep(action=StepAction.CLICK, params={"selector": "#x"})],
            setup_steps=[
                PlaybookStep(
                    action=StepAction.NAVIGATE,
                    params={"url": "${base_url}"},
                )
            ],
        )
        resolved = parser.resolve_variables(pb, {"base_url": "https://app.io"})
        assert resolved.setup_steps[0].params["url"] == "https://app.io"

    def test_resolve_teardown_steps(self, parser: PlaybookParser) -> None:
        pb = PlaybookDefinition(
            name="X",
            steps=[PlaybookStep(action=StepAction.CLICK, params={"selector": "#x"})],
            teardown_steps=[
                PlaybookStep(
                    action=StepAction.SCREENSHOT,
                    params={"name": "teardown-${base_url}"},
                )
            ],
        )
        resolved = parser.resolve_variables(pb, {"base_url": "myapp"})
        assert resolved.teardown_steps[0].params["name"] == "teardown-myapp"


# ---------------------------------------------------------------------------
# Validator Tests
# ---------------------------------------------------------------------------

class TestPlaybookValidatorValid:
    """Valid playbooks produce no errors."""

    def test_valid_minimal_playbook_no_errors(
        self, validator: PlaybookValidator, minimal_playbook: PlaybookDefinition
    ) -> None:
        errors = validator.validate(minimal_playbook)
        assert errors == []

    def test_valid_full_playbook_no_errors(self, validator: PlaybookValidator) -> None:
        pb = PlaybookDefinition(
            name="Full Playbook",
            description="A complete test playbook",
            priority=Priority.HIGH,
            steps=[
                PlaybookStep(action=StepAction.NAVIGATE, params={"url": "https://x.com"}),
                PlaybookStep(action=StepAction.ASSERT_VISIBLE, params={"selector": "#main"}),
                PlaybookStep(
                    action=StepAction.FILL,
                    params={"selector": "#email", "value": "x@x.com"},
                ),
                PlaybookStep(action=StepAction.CLICK, params={"selector": "#btn"}),
                PlaybookStep(action=StepAction.ASSERT_URL, params={"contains": "/home"}),
            ],
        )
        errors = validator.validate(pb)
        assert errors == []


class TestPlaybookValidatorErrors:
    """Invalid playbooks produce appropriate ValidationError list."""

    def test_empty_name_produces_error(self, validator: PlaybookValidator) -> None:
        pb = PlaybookDefinition(
            name="",
            steps=[PlaybookStep(action=StepAction.NAVIGATE, params={"url": "https://x.com"})],
        )
        errors = validator.validate(pb)
        assert any(e.path == "name" for e in errors)

    def test_no_steps_produces_error(self, validator: PlaybookValidator) -> None:
        pb = PlaybookDefinition(name="Empty", steps=[])
        errors = validator.validate(pb)
        assert any("steps" in e.path for e in errors)

    def test_navigate_missing_url_produces_error(
        self, validator: PlaybookValidator
    ) -> None:
        pb = PlaybookDefinition(
            name="Bad Navigate",
            steps=[PlaybookStep(action=StepAction.NAVIGATE, params={})],
        )
        errors = validator.validate(pb)
        assert any("url" in e.message.lower() for e in errors)

    def test_click_missing_selector_produces_error(
        self, validator: PlaybookValidator
    ) -> None:
        pb = PlaybookDefinition(
            name="Bad Click",
            steps=[PlaybookStep(action=StepAction.CLICK, params={})],
        )
        errors = validator.validate(pb)
        assert any("selector" in e.message.lower() for e in errors)

    def test_fill_missing_selector_produces_error(
        self, validator: PlaybookValidator
    ) -> None:
        pb = PlaybookDefinition(
            name="Bad Fill",
            steps=[PlaybookStep(action=StepAction.FILL, params={"value": "x"})],
        )
        errors = validator.validate(pb)
        assert any("selector" in e.message.lower() for e in errors)

    def test_fill_missing_value_produces_error(
        self, validator: PlaybookValidator
    ) -> None:
        pb = PlaybookDefinition(
            name="Bad Fill",
            steps=[
                PlaybookStep(action=StepAction.FILL, params={"selector": "#email"})
            ],
        )
        errors = validator.validate(pb)
        assert any("value" in e.message.lower() for e in errors)

    def test_assert_text_missing_selector_produces_error(
        self, validator: PlaybookValidator
    ) -> None:
        pb = PlaybookDefinition(
            name="Bad AssertText",
            steps=[
                PlaybookStep(
                    action=StepAction.ASSERT_TEXT, params={"text": "Hello"}
                )
            ],
        )
        errors = validator.validate(pb)
        assert any("selector" in e.message.lower() for e in errors)

    def test_assert_text_missing_text_produces_error(
        self, validator: PlaybookValidator
    ) -> None:
        pb = PlaybookDefinition(
            name="Bad AssertText",
            steps=[
                PlaybookStep(
                    action=StepAction.ASSERT_TEXT, params={"selector": "#h1"}
                )
            ],
        )
        errors = validator.validate(pb)
        assert any("text" in e.message.lower() for e in errors)

    def test_assert_url_missing_both_contains_and_equals_produces_error(
        self, validator: PlaybookValidator
    ) -> None:
        pb = PlaybookDefinition(
            name="Bad URL",
            steps=[PlaybookStep(action=StepAction.ASSERT_URL, params={})],
        )
        errors = validator.validate(pb)
        assert any(e for e in errors)

    def test_set_viewport_missing_width_produces_error(
        self, validator: PlaybookValidator
    ) -> None:
        pb = PlaybookDefinition(
            name="Bad Viewport",
            steps=[
                PlaybookStep(
                    action=StepAction.SET_VIEWPORT, params={"height": 768}
                )
            ],
        )
        errors = validator.validate(pb)
        assert any("width" in e.message.lower() for e in errors)

    def test_set_viewport_missing_height_produces_error(
        self, validator: PlaybookValidator
    ) -> None:
        pb = PlaybookDefinition(
            name="Bad Viewport",
            steps=[
                PlaybookStep(
                    action=StepAction.SET_VIEWPORT, params={"width": 1024}
                )
            ],
        )
        errors = validator.validate(pb)
        assert any("height" in e.message.lower() for e in errors)

    def test_select_missing_selector_produces_error(
        self, validator: PlaybookValidator
    ) -> None:
        pb = PlaybookDefinition(
            name="Bad Select",
            steps=[
                PlaybookStep(action=StepAction.SELECT, params={"value": "option1"})
            ],
        )
        errors = validator.validate(pb)
        assert any("selector" in e.message.lower() for e in errors)

    def test_select_missing_value_produces_error(
        self, validator: PlaybookValidator
    ) -> None:
        pb = PlaybookDefinition(
            name="Bad Select",
            steps=[
                PlaybookStep(action=StepAction.SELECT, params={"selector": "#s"})
            ],
        )
        errors = validator.validate(pb)
        assert any("value" in e.message.lower() for e in errors)

    def test_wait_missing_selector_produces_error(
        self, validator: PlaybookValidator
    ) -> None:
        pb = PlaybookDefinition(
            name="Bad Wait",
            steps=[PlaybookStep(action=StepAction.WAIT, params={})],
        )
        errors = validator.validate(pb)
        assert any("selector" in e.message.lower() for e in errors)

    def test_group_step_without_substeps_produces_error(
        self, validator: PlaybookValidator
    ) -> None:
        pb = PlaybookDefinition(
            name="Bad Group",
            steps=[PlaybookStep(action=StepAction.GROUP, steps=None)],
        )
        errors = validator.validate(pb)
        assert any(e for e in errors)

    def test_multiple_errors_returned_at_once(
        self, validator: PlaybookValidator
    ) -> None:
        """Validator does not stop at first error."""
        pb = PlaybookDefinition(
            name="",
            steps=[
                PlaybookStep(action=StepAction.NAVIGATE, params={}),
                PlaybookStep(action=StepAction.CLICK, params={}),
            ],
        )
        errors = validator.validate(pb)
        assert len(errors) >= 3  # name + navigate.url + click.selector

    def test_negative_performance_gate_produces_error(
        self, validator: PlaybookValidator
    ) -> None:
        pb = PlaybookDefinition(
            name="Bad Gates",
            steps=[
                PlaybookStep(action=StepAction.NAVIGATE, params={"url": "https://x.com"})
            ],
            performance_gates=PerformanceGate(total_duration_ms=-100),
        )
        errors = validator.validate(pb)
        assert any(e for e in errors)

    def test_invalid_cron_produces_warning(
        self, validator: PlaybookValidator
    ) -> None:
        pb = PlaybookDefinition(
            name="Bad Cron",
            steps=[
                PlaybookStep(action=StepAction.NAVIGATE, params={"url": "https://x.com"})
            ],
            trigger=PlaybookTrigger(schedule_cron="not-a-cron"),
        )
        errors = validator.validate(pb)
        assert any(e.severity in ("warning", "error") for e in errors)

    def test_valid_cron_no_error(self, validator: PlaybookValidator) -> None:
        pb = PlaybookDefinition(
            name="Good Cron",
            steps=[
                PlaybookStep(action=StepAction.NAVIGATE, params={"url": "https://x.com"})
            ],
            trigger=PlaybookTrigger(schedule_cron="*/30 * * * *"),
        )
        errors = validator.validate(pb)
        cron_errors = [e for e in errors if "cron" in e.message.lower()]
        assert cron_errors == []

    def test_validation_error_has_path_and_message(
        self, validator: PlaybookValidator
    ) -> None:
        pb = PlaybookDefinition(
            name="",
            steps=[PlaybookStep(action=StepAction.NAVIGATE, params={"url": "https://x.com"})],
        )
        errors = validator.validate(pb)
        for err in errors:
            assert hasattr(err, "path")
            assert hasattr(err, "message")
            assert isinstance(err.path, str)
            assert isinstance(err.message, str)


class TestPlaybookValidatorVariables:
    """Variable reference validation."""

    def test_undefined_variable_in_step_returns_warning(
        self, validator: PlaybookValidator
    ) -> None:
        pb = PlaybookDefinition(
            name="Var Test",
            variables={},  # empty — no variables defined
            steps=[
                PlaybookStep(
                    action=StepAction.NAVIGATE,
                    params={"url": "${undefined_var}/path"},
                )
            ],
        )
        errors = validator.check_unreferenced_variables(pb)
        assert any("undefined_var" in e.message for e in errors)

    def test_defined_variable_no_warning(self, validator: PlaybookValidator) -> None:
        pb = PlaybookDefinition(
            name="Var Test",
            variables={"base_url": "https://example.com"},
            steps=[
                PlaybookStep(
                    action=StepAction.NAVIGATE,
                    params={"url": "${base_url}/path"},
                )
            ],
        )
        errors = validator.check_unreferenced_variables(pb)
        undefined = [e for e in errors if "base_url" in e.message]
        assert undefined == []

    def test_builtin_variables_not_flagged(self, validator: PlaybookValidator) -> None:
        pb = PlaybookDefinition(
            name="Builtin Vars",
            variables={},
            steps=[
                PlaybookStep(
                    action=StepAction.NAVIGATE,
                    params={"url": "${base_url}/path"},
                ),
                PlaybookStep(
                    action=StepAction.FILL,
                    params={"selector": "#e", "value": "${credentials.email}"},
                ),
                PlaybookStep(
                    action=StepAction.FILL,
                    params={"selector": "#p", "value": "${credentials.password}"},
                ),
                PlaybookStep(
                    action=StepAction.SCREENSHOT,
                    params={"name": "${timestamp}"},
                ),
                PlaybookStep(
                    action=StepAction.FILL,
                    params={"selector": "#r", "value": "${random_string}"},
                ),
            ],
        )
        errors = validator.check_unreferenced_variables(pb)
        assert errors == []


# ---------------------------------------------------------------------------
# Executor Result Tests
# ---------------------------------------------------------------------------

class TestStepResult:
    """StepResult dataclass."""

    def test_step_result_defaults(self) -> None:
        r = StepResult(step_index=0, action="navigate", status="passed")
        assert r.duration_ms == 0
        assert r.error is None
        assert r.screenshot is None
        assert r.metadata == {}

    def test_step_result_with_error(self) -> None:
        r = StepResult(
            step_index=1,
            action="click",
            status="failed",
            error="Element not found",
        )
        assert r.status == "failed"
        assert r.error == "Element not found"


class TestPlaybookResult:
    """PlaybookResult dataclass and properties."""

    def test_passed_property_true_when_status_passed(self) -> None:
        r = PlaybookResult(playbook_name="Test", status="passed")
        assert r.passed is True

    def test_passed_property_false_when_status_failed(self) -> None:
        r = PlaybookResult(playbook_name="Test", status="failed")
        assert r.passed is False

    def test_passed_property_false_when_status_error(self) -> None:
        r = PlaybookResult(playbook_name="Test", status="error")
        assert r.passed is False

    def test_playbook_result_defaults(self) -> None:
        r = PlaybookResult(playbook_name="X", status="passed")
        assert r.steps == []
        assert r.total_duration_ms == 0
        assert r.started_at is None
        assert r.completed_at is None
        assert r.performance_data == {}
        assert r.console_logs == []
        assert r.network_requests == []
        assert r.assertions_passed == 0
        assert r.assertions_failed == 0
        assert r.screenshots == []
        assert r.error is None


class TestPlaybookExecutorValidation:
    """Executor validates playbooks before executing."""

    @pytest.mark.asyncio
    async def test_execute_invalid_playbook_returns_error_result(
        self, executor: PlaybookExecutor
    ) -> None:
        pb = PlaybookDefinition(name="", steps=[])
        result = await executor.execute(pb, target_url="https://example.com")
        assert result.status == "error"
        assert result.error is not None

    @pytest.mark.asyncio
    async def test_execute_empty_steps_returns_error(
        self, executor: PlaybookExecutor
    ) -> None:
        pb = PlaybookDefinition(name="No steps", steps=[])
        result = await executor.execute(pb, target_url="https://example.com")
        assert result.status == "error"


class TestPlaybookExecutorMocked:
    """Executor integration with mocked Playwright."""

    @pytest.mark.asyncio
    async def test_execute_single_navigate_passes(
        self, executor: PlaybookExecutor, minimal_playbook: PlaybookDefinition
    ) -> None:
        mock_page = AsyncMock()
        mock_page.goto = AsyncMock()
        mock_page.evaluate = AsyncMock(return_value={})
        mock_context = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_browser = AsyncMock()
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_playwright = AsyncMock()
        mock_playwright.chromium.launch = AsyncMock(return_value=mock_browser)

        with patch("tinaa.playbooks.executor.async_playwright") as mock_pw_ctx:
            mock_pw_instance = AsyncMock()
            mock_pw_instance.__aenter__ = AsyncMock(return_value=mock_playwright)
            mock_pw_instance.__aexit__ = AsyncMock(return_value=None)
            mock_pw_ctx.return_value = mock_pw_instance

            result = await executor.execute(
                minimal_playbook,
                target_url="https://example.com",
                collect_metrics=False,
            )

        assert result.playbook_name == "Minimal"
        assert result.status == "passed"
        assert len(result.steps) == 1
        assert result.steps[0].action == "navigate"
        assert result.steps[0].status == "passed"

    @pytest.mark.asyncio
    async def test_execute_sets_started_and_completed_at(
        self, executor: PlaybookExecutor, minimal_playbook: PlaybookDefinition
    ) -> None:
        mock_page = AsyncMock()
        mock_page.goto = AsyncMock()
        mock_page.evaluate = AsyncMock(return_value={})
        mock_context = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_browser = AsyncMock()
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_playwright = AsyncMock()
        mock_playwright.chromium.launch = AsyncMock(return_value=mock_browser)

        with patch("tinaa.playbooks.executor.async_playwright") as mock_pw_ctx:
            mock_pw_instance = AsyncMock()
            mock_pw_instance.__aenter__ = AsyncMock(return_value=mock_playwright)
            mock_pw_instance.__aexit__ = AsyncMock(return_value=None)
            mock_pw_ctx.return_value = mock_pw_instance

            result = await executor.execute(
                minimal_playbook,
                target_url="https://example.com",
                collect_metrics=False,
            )

        assert result.started_at is not None
        assert result.completed_at is not None
        assert isinstance(result.started_at, datetime)
        assert isinstance(result.completed_at, datetime)

    @pytest.mark.asyncio
    async def test_execute_failed_step_marks_playbook_failed(
        self, executor: PlaybookExecutor
    ) -> None:
        pb = PlaybookDefinition(
            name="Fail Test",
            steps=[
                PlaybookStep(
                    action=StepAction.CLICK,
                    params={"selector": "#nonexistent"},
                )
            ],
        )
        mock_page = AsyncMock()
        mock_page.click = AsyncMock(side_effect=Exception("Element not found: #nonexistent"))
        mock_page.evaluate = AsyncMock(return_value={})
        mock_context = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_browser = AsyncMock()
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_playwright = AsyncMock()
        mock_playwright.chromium.launch = AsyncMock(return_value=mock_browser)

        with patch("tinaa.playbooks.executor.async_playwright") as mock_pw_ctx:
            mock_pw_instance = AsyncMock()
            mock_pw_instance.__aenter__ = AsyncMock(return_value=mock_playwright)
            mock_pw_instance.__aexit__ = AsyncMock(return_value=None)
            mock_pw_ctx.return_value = mock_pw_instance

            result = await executor.execute(
                pb, target_url="https://example.com", collect_metrics=False
            )

        assert result.status == "failed"
        assert result.steps[0].status == "failed"
        assert result.steps[0].error is not None

    @pytest.mark.asyncio
    async def test_optional_step_failure_does_not_fail_playbook(
        self, executor: PlaybookExecutor
    ) -> None:
        pb = PlaybookDefinition(
            name="Optional Step",
            steps=[
                PlaybookStep(
                    action=StepAction.NAVIGATE,
                    params={"url": "https://example.com"},
                ),
                PlaybookStep(
                    action=StepAction.CLICK,
                    params={"selector": "#optional-btn"},
                    optional=True,
                ),
            ],
        )
        mock_page = AsyncMock()
        mock_page.goto = AsyncMock()
        mock_page.click = AsyncMock(side_effect=Exception("not found"))
        mock_page.evaluate = AsyncMock(return_value={})
        mock_context = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_browser = AsyncMock()
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_playwright = AsyncMock()
        mock_playwright.chromium.launch = AsyncMock(return_value=mock_browser)

        with patch("tinaa.playbooks.executor.async_playwright") as mock_pw_ctx:
            mock_pw_instance = AsyncMock()
            mock_pw_instance.__aenter__ = AsyncMock(return_value=mock_playwright)
            mock_pw_instance.__aexit__ = AsyncMock(return_value=None)
            mock_pw_ctx.return_value = mock_pw_instance

            result = await executor.execute(
                pb, target_url="https://example.com", collect_metrics=False
            )

        assert result.status == "passed"
        assert result.steps[1].status in ("failed", "skipped")


class TestPlaybookExecutorSuite:
    """execute_suite runs multiple playbooks."""

    @pytest.mark.asyncio
    async def test_execute_suite_returns_list_of_results(
        self, executor: PlaybookExecutor
    ) -> None:
        pb1 = PlaybookDefinition(name="PB1", steps=[])
        pb2 = PlaybookDefinition(name="PB2", steps=[])

        with patch.object(executor, "execute", new_callable=AsyncMock) as mock_exec:
            mock_exec.side_effect = [
                PlaybookResult(playbook_name="PB1", status="error"),
                PlaybookResult(playbook_name="PB2", status="error"),
            ]
            results = await executor.execute_suite(
                [pb1, pb2], target_url="https://example.com"
            )

        assert len(results) == 2
        assert results[0].playbook_name == "PB1"
        assert results[1].playbook_name == "PB2"

    @pytest.mark.asyncio
    async def test_execute_suite_stop_on_failure_stops_early(
        self, executor: PlaybookExecutor
    ) -> None:
        pb1 = PlaybookDefinition(name="PB1", steps=[])
        pb2 = PlaybookDefinition(name="PB2", steps=[])
        pb3 = PlaybookDefinition(name="PB3", steps=[])

        with patch.object(executor, "execute", new_callable=AsyncMock) as mock_exec:
            mock_exec.side_effect = [
                PlaybookResult(playbook_name="PB1", status="failed"),
                PlaybookResult(playbook_name="PB2", status="passed"),
            ]
            results = await executor.execute_suite(
                [pb1, pb2, pb3],
                target_url="https://example.com",
                stop_on_failure=True,
            )

        assert len(results) == 1  # stops after PB1 fails
        mock_exec.assert_called_once()

    @pytest.mark.asyncio
    async def test_execute_suite_no_stop_on_failure_runs_all(
        self, executor: PlaybookExecutor
    ) -> None:
        pb1 = PlaybookDefinition(name="PB1", steps=[])
        pb2 = PlaybookDefinition(name="PB2", steps=[])

        with patch.object(executor, "execute", new_callable=AsyncMock) as mock_exec:
            mock_exec.side_effect = [
                PlaybookResult(playbook_name="PB1", status="failed"),
                PlaybookResult(playbook_name="PB2", status="passed"),
            ]
            results = await executor.execute_suite(
                [pb1, pb2],
                target_url="https://example.com",
                stop_on_failure=False,
            )

        assert len(results) == 2
        assert mock_exec.call_count == 2


# ---------------------------------------------------------------------------
# ValidationError dataclass
# ---------------------------------------------------------------------------

class TestValidationError:
    def test_validation_error_default_severity(self) -> None:
        err = ValidationError(path="steps[0]", message="Missing url")
        assert err.severity == "error"

    def test_validation_error_warning_severity(self) -> None:
        err = ValidationError(path="trigger", message="Bad cron", severity="warning")
        assert err.severity == "warning"


# ---------------------------------------------------------------------------
# Executor _dispatch_action unit tests (page is a mock, no browser needed)
# ---------------------------------------------------------------------------

class TestDispatchAction:
    """Direct unit tests for _dispatch_action covering all action branches."""

    @pytest.fixture
    def mock_page(self) -> AsyncMock:
        page = AsyncMock()
        page.url = "https://example.com/dashboard"
        page.title = AsyncMock(return_value="My App Title")
        return page

    @pytest.mark.asyncio
    async def test_dispatch_navigate(
        self, executor: PlaybookExecutor, mock_page: AsyncMock
    ) -> None:
        step = PlaybookStep(
            action=StepAction.NAVIGATE, params={"url": "https://example.com"}
        )
        await executor._dispatch_action(mock_page, step)
        mock_page.goto.assert_awaited_once_with("https://example.com", timeout=30000)

    @pytest.mark.asyncio
    async def test_dispatch_click(
        self, executor: PlaybookExecutor, mock_page: AsyncMock
    ) -> None:
        step = PlaybookStep(action=StepAction.CLICK, params={"selector": "#btn"})
        await executor._dispatch_action(mock_page, step)
        mock_page.click.assert_awaited_once_with("#btn", timeout=30000)

    @pytest.mark.asyncio
    async def test_dispatch_fill(
        self, executor: PlaybookExecutor, mock_page: AsyncMock
    ) -> None:
        step = PlaybookStep(
            action=StepAction.FILL,
            params={"selector": "#email", "value": "test@example.com"},
        )
        await executor._dispatch_action(mock_page, step)
        mock_page.fill.assert_awaited_once_with(
            "#email", "test@example.com", timeout=30000
        )

    @pytest.mark.asyncio
    async def test_dispatch_type(
        self, executor: PlaybookExecutor, mock_page: AsyncMock
    ) -> None:
        step = PlaybookStep(
            action=StepAction.TYPE,
            params={"selector": "#search", "value": "query"},
        )
        await executor._dispatch_action(mock_page, step)
        mock_page.type.assert_awaited_once_with("#search", "query", timeout=30000)

    @pytest.mark.asyncio
    async def test_dispatch_select(
        self, executor: PlaybookExecutor, mock_page: AsyncMock
    ) -> None:
        step = PlaybookStep(
            action=StepAction.SELECT,
            params={"selector": "#country", "value": "US"},
        )
        await executor._dispatch_action(mock_page, step)
        mock_page.select_option.assert_awaited_once_with(
            "#country", "US", timeout=30000
        )

    @pytest.mark.asyncio
    async def test_dispatch_press_key_without_selector(
        self, executor: PlaybookExecutor, mock_page: AsyncMock
    ) -> None:
        step = PlaybookStep(
            action=StepAction.PRESS_KEY, params={"key": "Enter"}
        )
        await executor._dispatch_action(mock_page, step)
        mock_page.keyboard.press.assert_awaited_once_with("Enter")

    @pytest.mark.asyncio
    async def test_dispatch_press_key_with_selector(
        self, executor: PlaybookExecutor, mock_page: AsyncMock
    ) -> None:
        step = PlaybookStep(
            action=StepAction.PRESS_KEY,
            params={"selector": "#input", "key": "Tab"},
        )
        await executor._dispatch_action(mock_page, step)
        mock_page.press.assert_awaited_once_with("#input", "Tab", timeout=30000)

    @pytest.mark.asyncio
    async def test_dispatch_wait(
        self, executor: PlaybookExecutor, mock_page: AsyncMock
    ) -> None:
        step = PlaybookStep(action=StepAction.WAIT, params={"selector": ".loaded"})
        await executor._dispatch_action(mock_page, step)
        mock_page.wait_for_selector.assert_awaited_once_with(".loaded", timeout=30000)

    @pytest.mark.asyncio
    async def test_dispatch_wait_for_navigation(
        self, executor: PlaybookExecutor, mock_page: AsyncMock
    ) -> None:
        step = PlaybookStep(action=StepAction.WAIT_FOR_NAVIGATION, params={})
        await executor._dispatch_action(mock_page, step)
        mock_page.wait_for_load_state.assert_awaited_once_with(
            "networkidle", timeout=30000
        )

    @pytest.mark.asyncio
    async def test_dispatch_screenshot(
        self, executor: PlaybookExecutor, mock_page: AsyncMock
    ) -> None:
        mock_page.screenshot = AsyncMock(return_value=b"fake-png-bytes")
        step = PlaybookStep(
            action=StepAction.SCREENSHOT, params={"name": "my-shot"}
        )
        await executor._dispatch_action(mock_page, step)
        mock_page.screenshot.assert_awaited_once_with(full_page=True)

    @pytest.mark.asyncio
    async def test_dispatch_assert_visible(
        self, executor: PlaybookExecutor, mock_page: AsyncMock
    ) -> None:
        step = PlaybookStep(
            action=StepAction.ASSERT_VISIBLE, params={"selector": "#modal"}
        )
        await executor._dispatch_action(mock_page, step)
        mock_page.wait_for_selector.assert_awaited_once_with(
            "#modal", state="visible", timeout=30000
        )

    @pytest.mark.asyncio
    async def test_dispatch_assert_hidden(
        self, executor: PlaybookExecutor, mock_page: AsyncMock
    ) -> None:
        step = PlaybookStep(
            action=StepAction.ASSERT_HIDDEN, params={"selector": "#spinner"}
        )
        await executor._dispatch_action(mock_page, step)
        mock_page.wait_for_selector.assert_awaited_once_with(
            "#spinner", state="hidden", timeout=30000
        )

    @pytest.mark.asyncio
    async def test_dispatch_assert_text_passes_when_text_matches(
        self, executor: PlaybookExecutor, mock_page: AsyncMock
    ) -> None:
        element_mock = AsyncMock()
        element_mock.inner_text = AsyncMock(return_value="Welcome, User!")
        mock_page.wait_for_selector = AsyncMock(return_value=element_mock)
        step = PlaybookStep(
            action=StepAction.ASSERT_TEXT,
            params={"selector": "#greeting", "text": "Welcome"},
        )
        await executor._dispatch_action(mock_page, step)

    @pytest.mark.asyncio
    async def test_dispatch_assert_text_fails_when_text_absent(
        self, executor: PlaybookExecutor, mock_page: AsyncMock
    ) -> None:
        element_mock = AsyncMock()
        element_mock.inner_text = AsyncMock(return_value="Hello World")
        mock_page.wait_for_selector = AsyncMock(return_value=element_mock)
        step = PlaybookStep(
            action=StepAction.ASSERT_TEXT,
            params={"selector": "#msg", "text": "NOTPRESENT"},
        )
        with pytest.raises(AssertionError, match="NOTPRESENT"):
            await executor._dispatch_action(mock_page, step)

    @pytest.mark.asyncio
    async def test_dispatch_assert_url_equals_passes(
        self, executor: PlaybookExecutor, mock_page: AsyncMock
    ) -> None:
        mock_page.url = "https://example.com/dashboard"
        step = PlaybookStep(
            action=StepAction.ASSERT_URL,
            params={"equals": "https://example.com/dashboard"},
        )
        await executor._dispatch_action(mock_page, step)  # no exception

    @pytest.mark.asyncio
    async def test_dispatch_assert_url_equals_fails(
        self, executor: PlaybookExecutor, mock_page: AsyncMock
    ) -> None:
        mock_page.url = "https://example.com/login"
        step = PlaybookStep(
            action=StepAction.ASSERT_URL,
            params={"equals": "https://example.com/dashboard"},
        )
        with pytest.raises(AssertionError, match="Expected URL"):
            await executor._dispatch_action(mock_page, step)

    @pytest.mark.asyncio
    async def test_dispatch_assert_url_contains_fails(
        self, executor: PlaybookExecutor, mock_page: AsyncMock
    ) -> None:
        mock_page.url = "https://example.com/login"
        step = PlaybookStep(
            action=StepAction.ASSERT_URL,
            params={"contains": "/dashboard"},
        )
        with pytest.raises(AssertionError, match="Expected URL to contain"):
            await executor._dispatch_action(mock_page, step)

    @pytest.mark.asyncio
    async def test_dispatch_assert_title_equals_passes(
        self, executor: PlaybookExecutor, mock_page: AsyncMock
    ) -> None:
        mock_page.title = AsyncMock(return_value="My App Title")
        step = PlaybookStep(
            action=StepAction.ASSERT_TITLE,
            params={"equals": "My App Title"},
        )
        await executor._dispatch_action(mock_page, step)

    @pytest.mark.asyncio
    async def test_dispatch_assert_title_equals_fails(
        self, executor: PlaybookExecutor, mock_page: AsyncMock
    ) -> None:
        mock_page.title = AsyncMock(return_value="Wrong Title")
        step = PlaybookStep(
            action=StepAction.ASSERT_TITLE,
            params={"equals": "My App Title"},
        )
        with pytest.raises(AssertionError, match="Expected title"):
            await executor._dispatch_action(mock_page, step)

    @pytest.mark.asyncio
    async def test_dispatch_assert_title_contains_fails(
        self, executor: PlaybookExecutor, mock_page: AsyncMock
    ) -> None:
        mock_page.title = AsyncMock(return_value="Welcome Page")
        step = PlaybookStep(
            action=StepAction.ASSERT_TITLE,
            params={"contains": "My App"},
        )
        with pytest.raises(AssertionError, match="Expected title to contain"):
            await executor._dispatch_action(mock_page, step)

    @pytest.mark.asyncio
    async def test_dispatch_assert_no_console_errors(
        self, executor: PlaybookExecutor, mock_page: AsyncMock
    ) -> None:
        step = PlaybookStep(action=StepAction.ASSERT_NO_CONSOLE_ERRORS, params={})
        await executor._dispatch_action(mock_page, step)  # no-op, no exception

    @pytest.mark.asyncio
    async def test_dispatch_assert_no_network_failures(
        self, executor: PlaybookExecutor, mock_page: AsyncMock
    ) -> None:
        step = PlaybookStep(action=StepAction.ASSERT_NO_NETWORK_FAILURES, params={})
        await executor._dispatch_action(mock_page, step)

    @pytest.mark.asyncio
    async def test_dispatch_assert_accessibility(
        self, executor: PlaybookExecutor, mock_page: AsyncMock
    ) -> None:
        step = PlaybookStep(action=StepAction.ASSERT_ACCESSIBILITY, params={})
        await executor._dispatch_action(mock_page, step)

    @pytest.mark.asyncio
    async def test_dispatch_evaluate(
        self, executor: PlaybookExecutor, mock_page: AsyncMock
    ) -> None:
        step = PlaybookStep(
            action=StepAction.EVALUATE, params={"expression": "document.title"}
        )
        await executor._dispatch_action(mock_page, step)
        mock_page.evaluate.assert_awaited_once_with("document.title")

    @pytest.mark.asyncio
    async def test_dispatch_hover(
        self, executor: PlaybookExecutor, mock_page: AsyncMock
    ) -> None:
        step = PlaybookStep(action=StepAction.HOVER, params={"selector": "#menu"})
        await executor._dispatch_action(mock_page, step)
        mock_page.hover.assert_awaited_once_with("#menu", timeout=30000)

    @pytest.mark.asyncio
    async def test_dispatch_scroll_with_selector(
        self, executor: PlaybookExecutor, mock_page: AsyncMock
    ) -> None:
        element_mock = AsyncMock()
        mock_page.wait_for_selector = AsyncMock(return_value=element_mock)
        step = PlaybookStep(
            action=StepAction.SCROLL, params={"selector": "#footer"}
        )
        await executor._dispatch_action(mock_page, step)
        element_mock.scroll_into_view_if_needed.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_dispatch_scroll_without_selector(
        self, executor: PlaybookExecutor, mock_page: AsyncMock
    ) -> None:
        step = PlaybookStep(
            action=StepAction.SCROLL, params={"x": 0, "y": 500}
        )
        await executor._dispatch_action(mock_page, step)
        mock_page.evaluate.assert_awaited_once_with("window.scrollTo(0, 500)")

    @pytest.mark.asyncio
    async def test_dispatch_upload_file(
        self, executor: PlaybookExecutor, mock_page: AsyncMock
    ) -> None:
        step = PlaybookStep(
            action=StepAction.UPLOAD_FILE,
            params={"selector": "#upload", "file_path": "/tmp/test.pdf"},
        )
        await executor._dispatch_action(mock_page, step)
        mock_page.set_input_files.assert_awaited_once_with(
            "#upload", "/tmp/test.pdf"
        )

    @pytest.mark.asyncio
    async def test_dispatch_set_viewport(
        self, executor: PlaybookExecutor, mock_page: AsyncMock
    ) -> None:
        step = PlaybookStep(
            action=StepAction.SET_VIEWPORT, params={"width": 1920, "height": 1080}
        )
        await executor._dispatch_action(mock_page, step)
        mock_page.set_viewport_size.assert_awaited_once_with(
            {"width": 1920, "height": 1080}
        )

    @pytest.mark.asyncio
    async def test_dispatch_clear(
        self, executor: PlaybookExecutor, mock_page: AsyncMock
    ) -> None:
        step = PlaybookStep(action=StepAction.CLEAR, params={"selector": "#input"})
        await executor._dispatch_action(mock_page, step)
        mock_page.fill.assert_awaited_once_with("#input", "", timeout=30000)

    @pytest.mark.asyncio
    async def test_dispatch_group_runs_substeps(
        self, executor: PlaybookExecutor, mock_page: AsyncMock
    ) -> None:
        sub1 = PlaybookStep(
            action=StepAction.NAVIGATE, params={"url": "https://example.com"}
        )
        sub2 = PlaybookStep(action=StepAction.CLICK, params={"selector": "#btn"})
        group = PlaybookStep(action=StepAction.GROUP, steps=[sub1, sub2])
        await executor._dispatch_action(mock_page, group)
        mock_page.goto.assert_awaited_once()
        mock_page.click.assert_awaited_once()


# ---------------------------------------------------------------------------
# Executor _check_performance_gates unit tests
# ---------------------------------------------------------------------------

class TestCheckPerformanceGates:

    @pytest.mark.asyncio
    async def test_no_gates_returns_empty(self, executor: PlaybookExecutor) -> None:
        pb = PlaybookDefinition(name="X", steps=[], performance_gates=None)
        result = PlaybookResult(playbook_name="X", status="passed", total_duration_ms=5000)
        failures = await executor._check_performance_gates(pb, result, {})
        assert failures == []

    @pytest.mark.asyncio
    async def test_total_duration_gate_passes(self, executor: PlaybookExecutor) -> None:
        pb = PlaybookDefinition(
            name="X",
            steps=[],
            performance_gates=PerformanceGate(total_duration_ms=10000),
        )
        result = PlaybookResult(playbook_name="X", status="passed", total_duration_ms=5000)
        failures = await executor._check_performance_gates(pb, result, {})
        assert failures == []

    @pytest.mark.asyncio
    async def test_total_duration_gate_fails(self, executor: PlaybookExecutor) -> None:
        pb = PlaybookDefinition(
            name="X",
            steps=[],
            performance_gates=PerformanceGate(total_duration_ms=3000),
        )
        result = PlaybookResult(
            playbook_name="X", status="passed", total_duration_ms=5000
        )
        failures = await executor._check_performance_gates(pb, result, {})
        assert len(failures) == 1
        assert "total_duration" in failures[0]

    @pytest.mark.asyncio
    async def test_lcp_gate_fails(self, executor: PlaybookExecutor) -> None:
        pb = PlaybookDefinition(
            name="X",
            steps=[],
            performance_gates=PerformanceGate(lcp_ms=2500.0),
        )
        result = PlaybookResult(playbook_name="X", status="passed")
        failures = await executor._check_performance_gates(
            pb, result, {"lcp": 3000.0}
        )
        assert any("lcp" in f for f in failures)

    @pytest.mark.asyncio
    async def test_cls_gate_fails(self, executor: PlaybookExecutor) -> None:
        pb = PlaybookDefinition(
            name="X",
            steps=[],
            performance_gates=PerformanceGate(cls=0.1),
        )
        result = PlaybookResult(playbook_name="X", status="passed")
        failures = await executor._check_performance_gates(
            pb, result, {"cls": 0.25}
        )
        assert any("cls" in f for f in failures)


# ---------------------------------------------------------------------------
# Executor _check_assertions unit tests
# ---------------------------------------------------------------------------

class TestCheckAssertions:

    @pytest.mark.asyncio
    async def test_no_assertions_returns_empty(
        self, executor: PlaybookExecutor
    ) -> None:
        pb = PlaybookDefinition(name="X", steps=[], assertions=None)
        mock_page = AsyncMock()
        result = PlaybookResult(playbook_name="X", status="passed")
        failures = await executor._check_assertions(pb, mock_page, result)
        assert failures == []

    @pytest.mark.asyncio
    async def test_no_console_errors_passes_when_clean(
        self, executor: PlaybookExecutor
    ) -> None:
        pb = PlaybookDefinition(
            name="X",
            steps=[],
            assertions=PlaybookAssertion(no_console_errors=True),
        )
        mock_page = AsyncMock()
        result = PlaybookResult(playbook_name="X", status="passed", console_logs=[])
        failures = await executor._check_assertions(pb, mock_page, result)
        assert failures == []

    @pytest.mark.asyncio
    async def test_no_console_errors_fails_when_errors_present(
        self, executor: PlaybookExecutor
    ) -> None:
        pb = PlaybookDefinition(
            name="X",
            steps=[],
            assertions=PlaybookAssertion(no_console_errors=True),
        )
        mock_page = AsyncMock()
        result = PlaybookResult(
            playbook_name="X",
            status="passed",
            console_logs=["[error] TypeError: undefined is not a function"],
        )
        failures = await executor._check_assertions(pb, mock_page, result)
        assert len(failures) == 1
        assert "Console errors" in failures[0]

    @pytest.mark.asyncio
    async def test_no_network_failures_assertion_is_noop(
        self, executor: PlaybookExecutor
    ) -> None:
        pb = PlaybookDefinition(
            name="X",
            steps=[],
            assertions=PlaybookAssertion(no_network_failures=True),
        )
        mock_page = AsyncMock()
        result = PlaybookResult(playbook_name="X", status="passed")
        failures = await executor._check_assertions(pb, mock_page, result)
        assert failures == []


# ---------------------------------------------------------------------------
# Additional parser step format coverage
# ---------------------------------------------------------------------------

class TestParserAdditionalStepFormats:
    """Cover parser branches for less common step formats."""

    def test_type_shorthand_dict(self, parser: PlaybookParser) -> None:
        step = parser._parse_step({"type": {"selector": "#search", "value": "hello"}})
        assert step.action == StepAction.TYPE
        assert step.params["selector"] == "#search"
        assert step.params["value"] == "hello"

    def test_select_shorthand_dict(self, parser: PlaybookParser) -> None:
        step = parser._parse_step(
            {"select": {"selector": "#country", "value": "US"}}
        )
        assert step.action == StepAction.SELECT
        assert step.params["value"] == "US"

    def test_set_viewport_shorthand_dict(self, parser: PlaybookParser) -> None:
        step = parser._parse_step(
            {"set_viewport": {"width": 1280, "height": 720}}
        )
        assert step.action == StepAction.SET_VIEWPORT
        assert step.params["width"] == 1280

    def test_assert_text_shorthand_dict(self, parser: PlaybookParser) -> None:
        step = parser._parse_step(
            {"assert_text": {"selector": "#h1", "text": "Hello"}}
        )
        assert step.action == StepAction.ASSERT_TEXT
        assert step.params["text"] == "Hello"

    def test_assert_url_with_dict_contains(self, parser: PlaybookParser) -> None:
        step = parser._parse_step({"assert_url": {"contains": "/dashboard"}})
        assert step.action == StepAction.ASSERT_URL
        assert step.params["contains"] == "/dashboard"

    def test_assert_title_with_dict(self, parser: PlaybookParser) -> None:
        step = parser._parse_step({"assert_title": {"equals": "My App"}})
        assert step.action == StepAction.ASSERT_TITLE
        assert step.params["equals"] == "My App"

    def test_evaluate_shorthand_str(self, parser: PlaybookParser) -> None:
        step = parser._parse_step({"evaluate": "document.title"})
        assert step.action == StepAction.EVALUATE
        assert step.params["expression"] == "document.title"

    def test_evaluate_shorthand_dict(self, parser: PlaybookParser) -> None:
        step = parser._parse_step(
            {"evaluate": {"expression": "window.location.href"}}
        )
        assert step.action == StepAction.EVALUATE
        assert step.params["expression"] == "window.location.href"

    def test_scroll_shorthand_dict(self, parser: PlaybookParser) -> None:
        step = parser._parse_step({"scroll": {"x": 0, "y": 500}})
        assert step.action == StepAction.SCROLL
        assert step.params["y"] == 500

    def test_scroll_shorthand_str(self, parser: PlaybookParser) -> None:
        step = parser._parse_step({"scroll": "#footer"})
        assert step.action == StepAction.SCROLL
        assert step.params["selector"] == "#footer"

    def test_upload_file_shorthand_dict(self, parser: PlaybookParser) -> None:
        step = parser._parse_step(
            {"upload_file": {"selector": "#upload", "file_path": "/tmp/a.pdf"}}
        )
        assert step.action == StepAction.UPLOAD_FILE
        assert step.params["file_path"] == "/tmp/a.pdf"

    def test_press_key_shorthand_str(self, parser: PlaybookParser) -> None:
        step = parser._parse_step({"press_key": "Enter"})
        assert step.action == StepAction.PRESS_KEY
        assert step.params["key"] == "Enter"

    def test_press_key_shorthand_dict(self, parser: PlaybookParser) -> None:
        step = parser._parse_step(
            {"press_key": {"selector": "#field", "key": "Tab"}}
        )
        assert step.action == StepAction.PRESS_KEY
        assert step.params["key"] == "Tab"

    def test_group_with_list_of_substeps(self, parser: PlaybookParser) -> None:
        step = parser._parse_step(
            {
                "group": [
                    {"navigate": "https://example.com"},
                    {"click": "#btn"},
                ]
            }
        )
        assert step.action == StepAction.GROUP
        assert step.steps is not None
        assert len(step.steps) == 2

    def test_assert_no_console_errors_with_empty_dict(
        self, parser: PlaybookParser
    ) -> None:
        step = parser._parse_step({"assert_no_console_errors": {}})
        assert step.action == StepAction.ASSERT_NO_CONSOLE_ERRORS

    def test_assert_no_network_failures_with_empty_dict(
        self, parser: PlaybookParser
    ) -> None:
        step = parser._parse_step({"assert_no_network_failures": {}})
        assert step.action == StepAction.ASSERT_NO_NETWORK_FAILURES

    def test_assert_accessibility_with_empty_dict(
        self, parser: PlaybookParser
    ) -> None:
        step = parser._parse_step({"assert_accessibility": {}})
        assert step.action == StepAction.ASSERT_ACCESSIBILITY

    def test_wait_with_dict_params(self, parser: PlaybookParser) -> None:
        step = parser._parse_step({"wait": {"selector": ".loaded", "state": "visible"}})
        assert step.action == StepAction.WAIT
        assert step.params["selector"] == ".loaded"

    def test_parse_step_raises_for_non_dict_input(
        self, parser: PlaybookParser
    ) -> None:
        with pytest.raises(ValueError, match="mapping"):
            parser._parse_step("navigate: https://example.com")

    def test_parse_step_raises_for_empty_dict(
        self, parser: PlaybookParser
    ) -> None:
        with pytest.raises(ValueError):
            parser._parse_step({})

    def test_parse_yaml_non_mapping_raises(self, parser: PlaybookParser) -> None:
        with pytest.raises(ValueError, match="Invalid YAML"):
            parser.parse_yaml("- item1\n- item2")

    def test_longhand_invalid_action_raises(self, parser: PlaybookParser) -> None:
        with pytest.raises(ValueError, match="Unknown action"):
            parser._parse_step({"action": "do_magic", "selector": "#x"})


# ---------------------------------------------------------------------------
# Executor additional coverage: pass extra variables + unexpected exception
# ---------------------------------------------------------------------------

class TestExecutorAdditionalCoverage:

    @pytest.mark.asyncio
    async def test_execute_with_extra_variables(
        self, executor: PlaybookExecutor
    ) -> None:
        """Covers line 119: variables dict update branch."""
        pb = PlaybookDefinition(
            name="Var Execute",
            steps=[
                PlaybookStep(
                    action=StepAction.NAVIGATE,
                    params={"url": "${base_url}/path"},
                )
            ],
        )
        mock_page = AsyncMock()
        mock_page.goto = AsyncMock()
        mock_page.evaluate = AsyncMock(return_value={})
        mock_context = AsyncMock()
        mock_context.new_page = AsyncMock(return_value=mock_page)
        mock_browser = AsyncMock()
        mock_browser.new_context = AsyncMock(return_value=mock_context)
        mock_playwright = AsyncMock()
        mock_playwright.chromium.launch = AsyncMock(return_value=mock_browser)

        with patch("tinaa.playbooks.executor.async_playwright") as mock_pw_ctx:
            mock_pw_instance = AsyncMock()
            mock_pw_instance.__aenter__ = AsyncMock(return_value=mock_playwright)
            mock_pw_instance.__aexit__ = AsyncMock(return_value=None)
            mock_pw_ctx.return_value = mock_pw_instance

            result = await executor.execute(
                pb,
                target_url="https://app.io",
                variables={"extra": "value"},
                collect_metrics=False,
            )

        assert result.status == "passed"

    @pytest.mark.asyncio
    async def test_execute_unexpected_exception_returns_error(
        self, executor: PlaybookExecutor
    ) -> None:
        """Covers lines 137-140: unexpected exception handler."""
        pb = PlaybookDefinition(
            name="Exception Test",
            steps=[
                PlaybookStep(
                    action=StepAction.NAVIGATE,
                    params={"url": "https://example.com"},
                )
            ],
        )

        with patch.object(
            executor,
            "_run_with_browser",
            new_callable=AsyncMock,
            side_effect=RuntimeError("Unexpected crash"),
        ):
            result = await executor.execute(
                pb, target_url="https://example.com", collect_metrics=False
            )

        assert result.status == "error"
        assert "Unexpected crash" in result.error


# ---------------------------------------------------------------------------
# Additional validator coverage tests
# ---------------------------------------------------------------------------

class TestValidatorAdditionalCoverage:
    """Cover setup/teardown validation, assert_title invalid, group valid."""

    def test_validate_setup_steps_with_invalid_step(
        self, validator: PlaybookValidator
    ) -> None:
        """Covers validator line 94: setup_steps iteration."""
        pb = PlaybookDefinition(
            name="Bad Setup",
            steps=[
                PlaybookStep(action=StepAction.NAVIGATE, params={"url": "https://x.com"})
            ],
            setup_steps=[
                PlaybookStep(action=StepAction.CLICK, params={})  # missing selector
            ],
        )
        errors = validator.validate(pb)
        setup_errors = [e for e in errors if "setup_steps" in e.path]
        assert len(setup_errors) >= 1

    def test_validate_teardown_steps_with_invalid_step(
        self, validator: PlaybookValidator
    ) -> None:
        """Covers validator line 97: teardown_steps iteration."""
        pb = PlaybookDefinition(
            name="Bad Teardown",
            steps=[
                PlaybookStep(action=StepAction.NAVIGATE, params={"url": "https://x.com"})
            ],
            teardown_steps=[
                PlaybookStep(action=StepAction.FILL, params={"selector": "#x"})  # missing value
            ],
        )
        errors = validator.validate(pb)
        teardown_errors = [e for e in errors if "teardown_steps" in e.path]
        assert len(teardown_errors) >= 1

    def test_validate_assert_title_missing_params_produces_error(
        self, validator: PlaybookValidator
    ) -> None:
        """Covers validator line 155-165: assert_title validation."""
        pb = PlaybookDefinition(
            name="Bad Title",
            steps=[PlaybookStep(action=StepAction.ASSERT_TITLE, params={})],
        )
        errors = validator.validate(pb)
        assert any(e for e in errors)

    def test_validate_group_with_valid_substeps_no_errors(
        self, validator: PlaybookValidator
    ) -> None:
        """Covers validator line 134-135: group with valid sub-steps."""
        sub = PlaybookStep(action=StepAction.CLICK, params={"selector": "#btn"})
        pb = PlaybookDefinition(
            name="Valid Group",
            steps=[PlaybookStep(action=StepAction.GROUP, steps=[sub])],
        )
        errors = validator.validate(pb)
        assert errors == []

    def test_validate_group_with_invalid_substeps_produces_errors(
        self, validator: PlaybookValidator
    ) -> None:
        """Covers validator line 134-135: group with invalid sub-step."""
        bad_sub = PlaybookStep(action=StepAction.CLICK, params={})  # missing selector
        pb = PlaybookDefinition(
            name="Bad Group Substep",
            steps=[PlaybookStep(action=StepAction.GROUP, steps=[bad_sub])],
        )
        errors = validator.validate(pb)
        assert any(e for e in errors)

    def test_check_unreferenced_variables_in_setup_steps(
        self, validator: PlaybookValidator
    ) -> None:
        """Covers validator line 215-216: setup_steps variable check."""
        pb = PlaybookDefinition(
            name="X",
            variables={},
            steps=[PlaybookStep(action=StepAction.CLICK, params={"selector": "#x"})],
            setup_steps=[
                PlaybookStep(
                    action=StepAction.NAVIGATE,
                    params={"url": "${undefined_setup_var}"},
                )
            ],
        )
        errors = validator.check_unreferenced_variables(pb)
        assert any("undefined_setup_var" in e.message for e in errors)

    def test_check_unreferenced_variables_in_teardown_steps(
        self, validator: PlaybookValidator
    ) -> None:
        """Covers validator line 217-218: teardown_steps variable check."""
        pb = PlaybookDefinition(
            name="X",
            variables={},
            steps=[PlaybookStep(action=StepAction.CLICK, params={"selector": "#x"})],
            teardown_steps=[
                PlaybookStep(
                    action=StepAction.SCREENSHOT,
                    params={"name": "${undefined_teardown_var}"},
                )
            ],
        )
        errors = validator.check_unreferenced_variables(pb)
        assert any("undefined_teardown_var" in e.message for e in errors)

    def test_validate_performance_gate_all_positive_no_errors(
        self, validator: PlaybookValidator
    ) -> None:
        """Covers positive performance gate values path."""
        pb = PlaybookDefinition(
            name="Good Gates",
            steps=[
                PlaybookStep(action=StepAction.NAVIGATE, params={"url": "https://x.com"})
            ],
            performance_gates=PerformanceGate(
                total_duration_ms=10000,
                lcp_ms=2500.0,
                fcp_ms=1800.0,
                cls=0.1,
                inp_ms=200.0,
            ),
        )
        errors = validator.validate(pb)
        gate_errors = [
            e for e in errors if "performance_gates" in e.path
        ]
        assert gate_errors == []


# ---------------------------------------------------------------------------
# Additional parser coverage: screenshot/group dict branches
# ---------------------------------------------------------------------------

class TestParserEdgeCases:
    """Cover remaining parser edge cases."""

    def test_screenshot_with_dict_params(self, parser: PlaybookParser) -> None:
        step = parser._parse_step(
            {"screenshot": {"name": "my-shot", "full_page": True}}
        )
        assert step.action == StepAction.SCREENSHOT
        assert step.params["name"] == "my-shot"

    def test_group_with_dict_value(self, parser: PlaybookParser) -> None:
        """Group with a dict value (unusual but handled)."""
        step = parser._parse_step({"group": {"config": "value"}})
        assert step.action == StepAction.GROUP
        assert step.steps is None

    def test_assert_url_dict_with_equals(self, parser: PlaybookParser) -> None:
        step = parser._parse_step({"assert_url": {"equals": "https://example.com/home"}})
        assert step.action == StepAction.ASSERT_URL
        assert step.params["equals"] == "https://example.com/home"


# ---------------------------------------------------------------------------
# Evaluate action security validation
# ---------------------------------------------------------------------------


class TestValidatorEvaluateAction:
    """EVALUATE action must require a non-empty script with length <= 4096."""

    def test_evaluate_without_script_param_produces_error(
        self, validator: PlaybookValidator
    ) -> None:
        pb = PlaybookDefinition(
            name="No Script",
            steps=[PlaybookStep(action=StepAction.EVALUATE, params={})],
        )
        errors = validator.validate(pb)
        script_errors = [e for e in errors if "script" in e.path]
        assert len(script_errors) >= 1
        assert script_errors[0].severity == "error"

    def test_evaluate_with_empty_script_produces_error(
        self, validator: PlaybookValidator
    ) -> None:
        pb = PlaybookDefinition(
            name="Empty Script",
            steps=[PlaybookStep(action=StepAction.EVALUATE, params={"script": ""})],
        )
        errors = validator.validate(pb)
        script_errors = [e for e in errors if "script" in e.path]
        assert len(script_errors) >= 1

    def test_evaluate_with_valid_script_produces_no_error(
        self, validator: PlaybookValidator
    ) -> None:
        pb = PlaybookDefinition(
            name="Good Script",
            steps=[
                PlaybookStep(
                    action=StepAction.EVALUATE,
                    params={"script": "return document.title"},
                )
            ],
        )
        errors = validator.validate(pb)
        script_errors = [e for e in errors if "script" in e.path]
        assert script_errors == []

    def test_evaluate_script_over_4096_chars_produces_error(
        self, validator: PlaybookValidator
    ) -> None:
        pb = PlaybookDefinition(
            name="Too Long",
            steps=[
                PlaybookStep(
                    action=StepAction.EVALUATE,
                    params={"script": "x" * 4097},
                )
            ],
        )
        errors = validator.validate(pb)
        script_errors = [e for e in errors if "script" in e.path]
        assert len(script_errors) >= 1
        assert "4096" in script_errors[0].message

    def test_evaluate_script_exactly_4096_chars_is_valid(
        self, validator: PlaybookValidator
    ) -> None:
        pb = PlaybookDefinition(
            name="Max Script",
            steps=[
                PlaybookStep(
                    action=StepAction.EVALUATE,
                    params={"script": "x" * 4096},
                )
            ],
        )
        errors = validator.validate(pb)
        script_errors = [e for e in errors if "script" in e.path]
        assert script_errors == []

    def test_evaluate_error_path_includes_step_index(
        self, validator: PlaybookValidator
    ) -> None:
        pb = PlaybookDefinition(
            name="Index Check",
            steps=[
                PlaybookStep(
                    action=StepAction.NAVIGATE,
                    params={"url": "https://example.com"},
                ),
                PlaybookStep(action=StepAction.EVALUATE, params={}),
            ],
        )
        errors = validator.validate(pb)
        script_errors = [e for e in errors if "script" in e.path]
        assert len(script_errors) >= 1
        assert "steps[1]" in script_errors[0].path
