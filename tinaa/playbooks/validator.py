"""
PlaybookValidator — validates PlaybookDefinition for correctness.

Collects ALL errors before returning (never stops at first error).
Returns a list of ValidationError dataclasses.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from tinaa.playbooks.schema import (
    PerformanceGate,
    PlaybookDefinition,
    PlaybookStep,
    PlaybookTrigger,
    StepAction,
)

# Required params per action: maps action -> set of required param names
_REQUIRED_PARAMS: dict[StepAction, tuple[str, ...]] = {
    StepAction.NAVIGATE: ("url",),
    StepAction.CLICK: ("selector",),
    StepAction.FILL: ("selector", "value"),
    StepAction.TYPE: ("selector", "value"),
    StepAction.SELECT: ("selector", "value"),
    StepAction.HOVER: ("selector",),
    StepAction.CLEAR: ("selector",),
    StepAction.ASSERT_VISIBLE: ("selector",),
    StepAction.ASSERT_HIDDEN: ("selector",),
    StepAction.ASSERT_TEXT: ("selector", "text"),
    StepAction.SET_VIEWPORT: ("width", "height"),
    StepAction.WAIT: ("selector",),
}

# Built-in variable names that require no definition
_BUILTIN_VARIABLES: frozenset[str] = frozenset(
    {
        "base_url",
        "credentials.email",
        "credentials.password",
        "timestamp",
        "random_string",
    }
)

_VAR_PATTERN = re.compile(r"\$\{([^}]+)\}")

# Minimal cron expression check: 5 or 6 whitespace-separated fields
_CRON_PATTERN = re.compile(r"^(\S+\s+){4}\S+(\s+\S+)?$")


@dataclass
class ValidationError:
    """A single validation problem found in a playbook definition."""

    path: str
    message: str
    severity: str = "error"


class PlaybookValidator:
    """Validates PlaybookDefinition objects, collecting all errors."""

    def validate(self, playbook: PlaybookDefinition) -> list[ValidationError]:
        """Run all validations and return the full list of errors/warnings."""
        errors: list[ValidationError] = []

        # Name
        if not playbook.name or not playbook.name.strip():
            errors.append(
                ValidationError(
                    path="name",
                    message="Playbook name must be a non-empty string.",
                )
            )

        # Steps presence
        if not playbook.steps:
            errors.append(
                ValidationError(
                    path="steps",
                    message="Playbook must contain at least one step.",
                )
            )

        # Validate each step
        for i, step in enumerate(playbook.steps):
            errors.extend(self.validate_step(step, i))

        # Setup / teardown steps
        for i, step in enumerate(playbook.setup_steps or []):
            errors.extend(self.validate_step(step, i, prefix="setup_steps"))

        for i, step in enumerate(playbook.teardown_steps or []):
            errors.extend(self.validate_step(step, i, prefix="teardown_steps"))

        # Performance gates
        if playbook.performance_gates:
            errors.extend(self._validate_performance_gates(playbook.performance_gates))

        # Trigger cron
        if playbook.trigger:
            errors.extend(self._validate_trigger(playbook.trigger))

        return errors

    def validate_step(
        self,
        step: PlaybookStep,
        index: int,
        prefix: str = "steps",
    ) -> list[ValidationError]:
        """Validate a single step and return its errors."""
        errors: list[ValidationError] = []
        path_prefix = f"{prefix}[{index}]"

        # GROUP step must have sub-steps
        if step.action == StepAction.GROUP:
            if not step.steps:
                errors.append(
                    ValidationError(
                        path=f"{path_prefix}.steps",
                        message=(
                            f"Step {index} has action 'group' but no sub-steps defined. "
                            "GROUP steps must contain at least one sub-step."
                        ),
                    )
                )
            else:
                for j, sub in enumerate(step.steps):
                    errors.extend(self.validate_step(sub, j, prefix=f"{path_prefix}.steps"))
            return errors

        # ASSERT_URL: needs 'contains' or 'equals'
        if step.action == StepAction.ASSERT_URL:
            if "contains" not in step.params and "equals" not in step.params:
                errors.append(
                    ValidationError(
                        path=f"{path_prefix}.params",
                        message=(
                            "assert_url requires either 'contains' or 'equals' param. "
                            'Example: {"contains": "/dashboard"}'
                        ),
                    )
                )
            return errors

        # ASSERT_TITLE: needs 'contains' or 'equals'
        if step.action == StepAction.ASSERT_TITLE:
            if "contains" not in step.params and "equals" not in step.params:
                errors.append(
                    ValidationError(
                        path=f"{path_prefix}.params",
                        message=("assert_title requires either 'contains' or 'equals' param."),
                    )
                )
            return errors

        # EVALUATE action: script param is required and length-capped
        if step.action == StepAction.EVALUATE:
            script = step.params.get("script", "")
            if not script:
                errors.append(
                    ValidationError(
                        path=f"{path_prefix}.params.script",
                        message="evaluate action requires a 'script' parameter",
                        severity="error",
                    )
                )
            elif len(script) > 4096:
                errors.append(
                    ValidationError(
                        path=f"{path_prefix}.params.script",
                        message="evaluate script exceeds maximum length of 4096 characters",
                        severity="error",
                    )
                )
            return errors

        # Actions with required params
        required = _REQUIRED_PARAMS.get(step.action, ())
        for param_name in required:
            if param_name not in step.params:
                errors.append(
                    ValidationError(
                        path=f"{path_prefix}.params.{param_name}",
                        message=(
                            f"Step {index} ({step.action.value}) is missing required "
                            f"param '{param_name}'."
                        ),
                    )
                )

        return errors

    def check_unreferenced_variables(self, playbook: PlaybookDefinition) -> list[ValidationError]:
        """Return warnings for ${...} variables used in steps but not defined."""
        defined = set(playbook.variables.keys()) | _BUILTIN_VARIABLES
        errors: list[ValidationError] = []

        def _check_params(params: dict, path: str) -> None:
            for key, value in params.items():
                if isinstance(value, str):
                    for match in _VAR_PATTERN.finditer(value):
                        var_name = match.group(1)
                        if var_name not in defined:
                            errors.append(
                                ValidationError(
                                    path=f"{path}.{key}",
                                    message=(
                                        f"Variable '${{{{  {var_name}  }}}}' is used but "
                                        f"not defined in playbook.variables. "
                                        f"Undefined variable: {var_name}"
                                    ),
                                    severity="warning",
                                )
                            )

        def _check_steps(steps: list[PlaybookStep], prefix: str) -> None:
            for i, step in enumerate(steps):
                _check_params(step.params, f"{prefix}[{i}].params")
                if step.steps:
                    _check_steps(step.steps, f"{prefix}[{i}].steps")

        _check_steps(playbook.steps, "steps")
        if playbook.setup_steps:
            _check_steps(playbook.setup_steps, "setup_steps")
        if playbook.teardown_steps:
            _check_steps(playbook.teardown_steps, "teardown_steps")

        return errors

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _validate_performance_gates(self, gates: PerformanceGate) -> list[ValidationError]:
        errors: list[ValidationError] = []

        def _check_positive(value: float | int | None, field: str) -> None:
            if value is not None and value < 0:
                errors.append(
                    ValidationError(
                        path=f"performance_gates.{field}",
                        message=(
                            f"Performance gate '{field}' must be a positive value, got {value}."
                        ),
                    )
                )

        _check_positive(gates.total_duration_ms, "total_duration_ms")
        _check_positive(gates.lcp_ms, "lcp_ms")
        _check_positive(gates.fcp_ms, "fcp_ms")
        _check_positive(gates.cls, "cls")
        _check_positive(gates.inp_ms, "inp_ms")
        _check_positive(gates.max_network_failures, "max_network_failures")

        return errors

    def _validate_trigger(self, trigger: PlaybookTrigger) -> list[ValidationError]:
        errors: list[ValidationError] = []

        if trigger.schedule_cron and not _CRON_PATTERN.match(trigger.schedule_cron.strip()):
            errors.append(
                ValidationError(
                    path="trigger.schedule_cron",
                    message=(
                        f"Cron expression '{trigger.schedule_cron}' does not appear "
                        "valid. Expected 5 or 6 space-separated fields "
                        "(e.g., '*/30 * * * *')."
                    ),
                    severity="warning",
                )
            )

        return errors
