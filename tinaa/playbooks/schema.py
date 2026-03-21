"""
Playbook data structures for the TINAA Playbook Engine.

These are pure Python dataclasses — no ORM or Pydantic dependency.
The ORM model lives in tinaa.models.playbook; these are the
in-memory domain objects used by parser, validator, and executor.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class StepAction(str, Enum):
    """All supported step actions in a playbook."""

    NAVIGATE = "navigate"
    CLICK = "click"
    FILL = "fill"
    TYPE = "type"
    SELECT = "select"
    PRESS_KEY = "press_key"
    WAIT = "wait"
    WAIT_FOR_NAVIGATION = "wait_for_navigation"
    SCREENSHOT = "screenshot"
    ASSERT_VISIBLE = "assert_visible"
    ASSERT_HIDDEN = "assert_hidden"
    ASSERT_TEXT = "assert_text"
    ASSERT_URL = "assert_url"
    ASSERT_TITLE = "assert_title"
    ASSERT_NO_CONSOLE_ERRORS = "assert_no_console_errors"
    ASSERT_NO_NETWORK_FAILURES = "assert_no_network_failures"
    ASSERT_ACCESSIBILITY = "assert_accessibility"
    EVALUATE = "evaluate"
    HOVER = "hover"
    SCROLL = "scroll"
    UPLOAD_FILE = "upload_file"
    SET_VIEWPORT = "set_viewport"
    CLEAR = "clear"
    GROUP = "group"


class Priority(str, Enum):
    """Playbook execution priority."""

    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class PlaybookSource(str, Enum):
    """How the playbook was authored."""

    AUTO_GENERATED = "auto_generated"
    MANUAL = "manual"
    HYBRID = "hybrid"


@dataclass
class PlaybookStep:
    """A single step in a playbook."""

    action: StepAction
    params: dict[str, Any] = field(default_factory=dict)
    description: str | None = None
    timeout_ms: int = 30000
    optional: bool = False
    retry_count: int = 0

    # Used only for GROUP action
    steps: list[PlaybookStep] | None = None


@dataclass
class PerformanceGate:
    """Performance thresholds that the playbook run must satisfy."""

    total_duration_ms: int | None = None
    lcp_ms: float | None = None
    fcp_ms: float | None = None
    cls: float | None = None
    inp_ms: float | None = None
    max_network_failures: int = 0


@dataclass
class PlaybookTrigger:
    """Conditions that cause a playbook to be scheduled or run."""

    on_deploy: list[str] | None = None
    on_pr: bool = False
    schedule_cron: str | None = None
    on_change: list[str] | None = None


@dataclass
class PlaybookAssertion:
    """Global assertions applied across the entire playbook run."""

    no_console_errors: bool = False
    no_network_failures: bool = False
    max_accessibility_violations: int | None = None


@dataclass
class PlaybookDefinition:
    """Complete, parsed playbook definition ready for validation and execution."""

    name: str
    steps: list[PlaybookStep]
    description: str = ""
    priority: Priority = Priority.MEDIUM
    source: PlaybookSource = PlaybookSource.MANUAL
    tags: list[str] = field(default_factory=list)
    trigger: PlaybookTrigger | None = None
    performance_gates: PerformanceGate | None = None
    assertions: PlaybookAssertion | None = None
    setup_steps: list[PlaybookStep] | None = None
    teardown_steps: list[PlaybookStep] | None = None
    variables: dict[str, str] = field(default_factory=dict)
    affected_paths: list[str] = field(default_factory=list)

    @property
    def total_steps(self) -> int:
        """Total number of steps including setup and teardown."""
        count = len(self.steps)
        if self.setup_steps:
            count += len(self.setup_steps)
        if self.teardown_steps:
            count += len(self.teardown_steps)
        return count
