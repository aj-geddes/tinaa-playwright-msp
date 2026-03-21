"""
PlaybookParser — parses YAML, JSON, or plain dicts into PlaybookDefinition.

Supports three step formats:
  - Shorthand dict:  {"navigate": "https://..."}  or {"click": "#btn"}
  - Rich dict:       {"fill": {"selector": "#e", "value": "x"}}
  - Longhand dict:   {"action": "navigate", "url": "...", "timeout": 5000}

Duration strings like "< 4s", "2.5s", "500ms" are parsed to milliseconds.
Template variables (${...}) are resolved via resolve_variables().
"""

from __future__ import annotations

import json
import random
import re
import string
from datetime import UTC, datetime
from typing import Any

import yaml

from tinaa.playbooks.schema import (
    PerformanceGate,
    PlaybookAssertion,
    PlaybookDefinition,
    PlaybookSource,
    PlaybookStep,
    PlaybookTrigger,
    Priority,
    StepAction,
)

# Actions where a plain string value is the URL
_URL_ACTIONS: frozenset[str] = frozenset({"navigate"})

# Actions where a plain string value is a CSS selector
_SELECTOR_ACTIONS: frozenset[str] = frozenset(
    {
        "click",
        "assert_visible",
        "assert_hidden",
        "hover",
        "clear",
        # NOTE: "wait" is NOT included here because it has its own branch
        # that supports both string and dict values.
    }
)

# Built-in variable names that are always available
_BUILTIN_VARIABLES: frozenset[str] = frozenset(
    {
        "base_url",
        "credentials.email",
        "credentials.password",
        "timestamp",
        "random_string",
    }
)

# Regex for template variable placeholders
_VAR_PATTERN = re.compile(r"\$\{([^}]+)\}")


class PlaybookParser:
    """Parses playbook definitions from YAML, JSON, or Python dicts."""

    # ------------------------------------------------------------------
    # Public parse methods
    # ------------------------------------------------------------------

    def parse_yaml(self, yaml_content: str) -> PlaybookDefinition:
        """Parse a YAML string into a PlaybookDefinition.

        Raises ValueError on malformed YAML or missing required fields.
        """
        try:
            data = yaml.safe_load(yaml_content)
        except yaml.YAMLError as exc:
            raise ValueError(f"Invalid YAML: {exc}") from exc

        if not isinstance(data, dict):
            raise ValueError("Invalid YAML: top-level value must be a mapping")

        return self.parse_dict(data)

    def parse_json(self, json_content: str) -> PlaybookDefinition:
        """Parse a JSON string into a PlaybookDefinition.

        Raises ValueError on malformed JSON or missing required fields.
        """
        try:
            data = json.loads(json_content)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSON: {exc}") from exc

        return self.parse_dict(data)

    def parse_dict(self, data: dict[str, Any]) -> PlaybookDefinition:
        """Parse a Python dict into a PlaybookDefinition.

        Raises ValueError on missing required fields.
        """
        if "playbook" not in data:
            raise ValueError("Missing required top-level key 'playbook' in playbook definition")

        pb_data: dict[str, Any] = data["playbook"]

        if not pb_data.get("name"):
            raise ValueError("Playbook definition is missing required field 'name'")

        name: str = pb_data["name"]
        description: str = pb_data.get("description", "")

        # Priority
        raw_priority = pb_data.get("priority", "medium")
        priority = Priority(raw_priority.lower())

        # Source
        raw_source = pb_data.get("source", "manual")
        source = PlaybookSource(raw_source.lower())

        # Tags
        tags: list[str] = pb_data.get("tags", []) or []

        # Variables
        variables: dict[str, str] = pb_data.get("variables", {}) or {}

        # Affected paths
        affected_paths: list[str] = pb_data.get("affected_paths", []) or []

        # Steps
        raw_steps = pb_data.get("steps", []) or []
        steps = [self._parse_step(s) for s in raw_steps]

        # Setup / teardown
        raw_setup = pb_data.get("setup_steps") or pb_data.get("setup")
        setup_steps = [self._parse_step(s) for s in raw_setup] if raw_setup else None

        raw_teardown = pb_data.get("teardown_steps") or pb_data.get("teardown")
        teardown_steps = [self._parse_step(s) for s in raw_teardown] if raw_teardown else None

        # Trigger
        trigger = self._parse_trigger(pb_data.get("trigger"))

        # Performance gates
        performance_gates = self._parse_performance_gates(pb_data.get("performance_gates"))

        # Assertions
        assertions = self._parse_assertions(pb_data.get("assertions"))

        return PlaybookDefinition(
            name=name,
            description=description,
            priority=priority,
            source=source,
            tags=tags,
            variables=variables,
            affected_paths=affected_paths,
            steps=steps,
            setup_steps=setup_steps,
            teardown_steps=teardown_steps,
            trigger=trigger,
            performance_gates=performance_gates,
            assertions=assertions,
        )

    # ------------------------------------------------------------------
    # Step parsing
    # ------------------------------------------------------------------

    def _parse_step(self, step_data: Any) -> PlaybookStep:
        """Parse a single step from shorthand or longhand dict format.

        Shorthand:  {"navigate": "https://..."}, {"click": "#btn"}
        Rich dict:  {"fill": {"selector": "#e", "value": "x"}}
        Longhand:   {"action": "navigate", "url": "...", "timeout": 5000}

        Raises ValueError for unknown actions.
        """
        if not isinstance(step_data, dict):
            raise ValueError(
                f"Step must be a mapping, got {type(step_data).__name__}: {step_data!r}"
            )

        # Longhand form — has explicit "action" key
        if "action" in step_data:
            return self._parse_longhand_step(step_data)

        # Shorthand / rich dict form — key is the action name
        return self._parse_shorthand_step(step_data)

    def _parse_longhand_step(self, data: dict[str, Any]) -> PlaybookStep:
        """Parse a step in {"action": "...", ...} format."""
        action_str = data["action"]
        try:
            action = StepAction(action_str)
        except ValueError as err:
            raise ValueError(
                f"Unknown action '{action_str}'. Valid actions: {[a.value for a in StepAction]}"
            ) from err

        # Collect params — everything except control keys
        control_keys = {"action", "description", "timeout", "optional", "retry_count"}
        params: dict[str, Any] = {k: v for k, v in data.items() if k not in control_keys}

        timeout_ms = int(data.get("timeout", 30000))
        description = data.get("description")
        optional = bool(data.get("optional", False))
        retry_count = int(data.get("retry_count", 0))

        return PlaybookStep(
            action=action,
            params=params,
            description=description,
            timeout_ms=timeout_ms,
            optional=optional,
            retry_count=retry_count,
        )

    def _parse_shorthand_step(self, data: dict[str, Any]) -> PlaybookStep:
        """Parse a step where the key is the action name."""
        # Find the action key (only one non-meta key expected)
        possible_actions = [k for k in data if k not in {"description", "optional", "retry_count"}]

        if not possible_actions:
            raise ValueError(f"Cannot determine action from step: {data!r}")

        action_key = possible_actions[0]

        try:
            action = StepAction(action_key)
        except ValueError as err:
            raise ValueError(
                f"Unknown action '{action_key}'. Valid actions: {[a.value for a in StepAction]}"
            ) from err

        value = data[action_key]
        timeout_ms = 30000
        description: str | None = data.get("description")
        optional = bool(data.get("optional", False))
        retry_count = int(data.get("retry_count", 0))
        params: dict[str, Any] = {}

        if action in (StepAction.WAIT_FOR_NAVIGATION,) and isinstance(value, dict):
            # {"wait_for_navigation": {"timeout": 5000}}
            timeout_ms = int(value.get("timeout", 30000))

        elif action == StepAction.FILL and isinstance(value, dict):
            # {"fill": {"selector": "#e", "value": "x"}}
            params = dict(value)

        elif (
            action == StepAction.TYPE
            and isinstance(value, dict)
            or action == StepAction.SELECT
            and isinstance(value, dict)
            or action == StepAction.SET_VIEWPORT
            and isinstance(value, dict)
            or action == StepAction.ASSERT_TEXT
            and isinstance(value, dict)
        ):
            params = dict(value)

        elif action == StepAction.ASSERT_URL:
            # Plain string — treat as "contains"
            params = dict(value) if isinstance(value, dict) else {"contains": str(value)}

        elif action == StepAction.ASSERT_TITLE:
            params = dict(value) if isinstance(value, dict) else {"contains": str(value)}

        elif action == StepAction.SCREENSHOT:
            if isinstance(value, str) and value:
                params = {"name": value}
            elif isinstance(value, dict):
                params = dict(value)

        elif action == StepAction.NAVIGATE:
            params = {"url": str(value)}

        elif action_key in _SELECTOR_ACTIONS:
            params = {"selector": str(value)}

        elif action == StepAction.EVALUATE:
            if isinstance(value, str):
                params = {"expression": value}
            elif isinstance(value, dict):
                params = dict(value)

        elif action == StepAction.SCROLL:
            if isinstance(value, dict):
                params = dict(value)
            elif isinstance(value, str):
                params = {"selector": value}

        elif action == StepAction.UPLOAD_FILE:
            if isinstance(value, dict):
                params = dict(value)

        elif action == StepAction.PRESS_KEY:
            if isinstance(value, str):
                params = {"key": value}
            elif isinstance(value, dict):
                params = dict(value)

        elif action == StepAction.GROUP:
            if isinstance(value, list):
                sub_steps = [self._parse_step(s) for s in value]
                return PlaybookStep(
                    action=action,
                    params=params,
                    description=description,
                    timeout_ms=timeout_ms,
                    optional=optional,
                    retry_count=retry_count,
                    steps=sub_steps,
                )
            elif isinstance(value, dict):
                params = dict(value)

        elif action in (
            StepAction.ASSERT_VISIBLE,
            StepAction.ASSERT_HIDDEN,
            StepAction.CLICK,
            StepAction.HOVER,
            StepAction.CLEAR,
        ):
            params = {"selector": str(value)}

        elif action == StepAction.WAIT:
            params = dict(value) if isinstance(value, dict) else {"selector": str(value)}

        elif action in (
            StepAction.ASSERT_NO_CONSOLE_ERRORS,
            StepAction.ASSERT_NO_NETWORK_FAILURES,
            StepAction.ASSERT_ACCESSIBILITY,
            StepAction.WAIT_FOR_NAVIGATION,
        ) and isinstance(value, dict):
            params = dict(value)

        return PlaybookStep(
            action=action,
            params=params,
            description=description,
            timeout_ms=timeout_ms,
            optional=optional,
            retry_count=retry_count,
        )

    # ------------------------------------------------------------------
    # Sub-structure parsing
    # ------------------------------------------------------------------

    def _parse_trigger(self, data: dict[str, Any] | None) -> PlaybookTrigger | None:
        if not data:
            return None

        on_deploy = data.get("on_deploy")
        on_pr = bool(data.get("on_pr", False))
        schedule_cron: str | None = data.get("schedule") or data.get("schedule_cron")
        on_change = data.get("on_change")

        return PlaybookTrigger(
            on_deploy=list(on_deploy) if on_deploy else None,
            on_pr=on_pr,
            schedule_cron=schedule_cron,
            on_change=list(on_change) if on_change else None,
        )

    def _parse_performance_gates(self, data: dict[str, Any] | None) -> PerformanceGate | None:
        if not data:
            return None

        raw_total = data.get("total_duration")
        raw_lcp = data.get("lcp")
        raw_fcp = data.get("fcp")
        raw_cls = data.get("cls")
        raw_inp = data.get("inp")
        max_net = int(data.get("max_network_failures", 0))

        def _to_ms(raw: str | int | float | None) -> float | None:
            if raw is None:
                return None
            return float(self._parse_duration(str(raw)))

        total_ms_raw = _to_ms(raw_total)
        total_ms = int(total_ms_raw) if total_ms_raw is not None else None

        return PerformanceGate(
            total_duration_ms=total_ms,
            lcp_ms=_to_ms(raw_lcp),
            fcp_ms=_to_ms(raw_fcp),
            cls=float(raw_cls) if raw_cls is not None else None,
            inp_ms=_to_ms(raw_inp),
            max_network_failures=max_net,
        )

    def _parse_assertions(self, data: dict[str, Any] | None) -> PlaybookAssertion | None:
        if not data:
            return None

        return PlaybookAssertion(
            no_console_errors=bool(data.get("no_console_errors", False)),
            no_network_failures=bool(data.get("no_network_failures", False)),
            max_accessibility_violations=(
                int(data["max_accessibility_violations"])
                if "max_accessibility_violations" in data
                else None
            ),
        )

    # ------------------------------------------------------------------
    # Duration parsing
    # ------------------------------------------------------------------

    def _parse_duration(self, value: str) -> int:
        """Convert human-readable duration strings to milliseconds.

        Examples:
            "4s"     -> 4000
            "2.5s"   -> 2500
            "500ms"  -> 500
            "< 4s"   -> 4000
            "<2.5s"  -> 2500
            "1m"     -> 60000
        """
        # Strip comparison operators and whitespace
        cleaned = re.sub(r"^[<>=\s]+", "", value.strip())

        ms_match = re.fullmatch(r"(\d+(?:\.\d+)?)\s*ms", cleaned)
        if ms_match:
            return int(float(ms_match.group(1)))

        s_match = re.fullmatch(r"(\d+(?:\.\d+)?)\s*s", cleaned)
        if s_match:
            return int(float(s_match.group(1)) * 1000)

        m_match = re.fullmatch(r"(\d+(?:\.\d+)?)\s*m", cleaned)
        if m_match:
            return int(float(m_match.group(1)) * 60 * 1000)

        raise ValueError(
            f"Cannot parse duration '{value}'. "
            "Expected formats: '4s', '2.5s', '500ms', '1m', '< 4s'."
        )

    # ------------------------------------------------------------------
    # Variable resolution
    # ------------------------------------------------------------------

    def resolve_variables(
        self,
        playbook: PlaybookDefinition,
        variables: dict[str, str],
    ) -> PlaybookDefinition:
        """Return a copy of the playbook with ${...} placeholders resolved.

        Precedence (highest first):
          1. Passed-in variables dict
          2. Playbook-level variables
          3. Built-in variables (base_url, credentials.*, timestamp, random_string)
        """
        # Build resolution context
        ctx: dict[str, str] = {}

        # Built-ins (lowest precedence)
        now_iso = datetime.now(UTC).isoformat()
        rand = "".join(random.choices(string.ascii_lowercase + string.digits, k=8))
        ctx["timestamp"] = now_iso
        ctx["random_string"] = rand

        # Playbook-level variables
        ctx.update(playbook.variables)

        # Passed-in variables (highest precedence)
        ctx.update(variables)

        def _resolve_str(s: str) -> str:
            def _replace(match: re.Match) -> str:
                key = match.group(1)
                return ctx.get(key, match.group(0))

            return _VAR_PATTERN.sub(_replace, s)

        def _resolve_params(params: dict[str, Any]) -> dict[str, Any]:
            resolved: dict[str, Any] = {}
            for k, v in params.items():
                if isinstance(v, str):
                    resolved[k] = _resolve_str(v)
                else:
                    resolved[k] = v
            return resolved

        def _resolve_step(step: PlaybookStep) -> PlaybookStep:
            new_params = _resolve_params(step.params)
            new_desc = _resolve_str(step.description) if step.description else None
            new_sub = [_resolve_step(s) for s in step.steps] if step.steps else None
            return PlaybookStep(
                action=step.action,
                params=new_params,
                description=new_desc,
                timeout_ms=step.timeout_ms,
                optional=step.optional,
                retry_count=step.retry_count,
                steps=new_sub,
            )

        def _resolve_steps(
            steps: list[PlaybookStep] | None,
        ) -> list[PlaybookStep] | None:
            if steps is None:
                return None
            return [_resolve_step(s) for s in steps]

        return PlaybookDefinition(
            name=playbook.name,
            description=playbook.description,
            priority=playbook.priority,
            source=playbook.source,
            tags=list(playbook.tags),
            variables=dict(playbook.variables),
            affected_paths=list(playbook.affected_paths),
            steps=_resolve_steps(playbook.steps) or [],
            setup_steps=_resolve_steps(playbook.setup_steps),
            teardown_steps=_resolve_steps(playbook.teardown_steps),
            trigger=playbook.trigger,
            performance_gates=playbook.performance_gates,
            assertions=playbook.assertions,
        )
