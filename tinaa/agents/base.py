"""
Base agent class and core data structures for the TINAA agent system.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any
from uuid import UUID, uuid4


class AgentStatus(str, Enum):
    """Lifecycle states for an agent or task."""

    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class AgentTask:
    """A unit of work dispatched to an agent.

    Tracks the full lifecycle from creation through completion, including
    timing data used for performance monitoring.
    """

    id: UUID = field(default_factory=uuid4)
    agent_type: str = ""
    action: str = ""
    params: dict = field(default_factory=dict)
    status: AgentStatus = AgentStatus.IDLE
    result: Any = None
    error: str | None = None
    created_at: datetime = field(default_factory=datetime.utcnow)
    started_at: datetime | None = None
    completed_at: datetime | None = None

    @property
    def duration_ms(self) -> int | None:
        """Wall-clock duration in milliseconds, or None if not yet complete."""
        if self.started_at and self.completed_at:
            return int((self.completed_at - self.started_at).total_seconds() * 1000)
        return None


class BaseAgent(ABC):
    """Abstract base for all TINAA agents.

    Provides the execution harness that handles status transitions,
    timing, and error capture.  Subclasses implement ``_run``.
    """

    def __init__(self, name: str) -> None:
        self.name = name
        self.logger = logging.getLogger(f"tinaa.agents.{name}")
        self._status: AgentStatus = AgentStatus.IDLE
        self._current_task: AgentTask | None = None

    @property
    def status(self) -> AgentStatus:
        """Current agent status."""
        return self._status

    async def execute(self, task: AgentTask) -> AgentTask:
        """Execute a task, managing status transitions and error handling.

        Sets ``task.started_at`` before calling ``_run`` and
        ``task.completed_at`` in the finally block regardless of outcome.
        """
        self._current_task = task
        task.status = AgentStatus.RUNNING
        task.started_at = datetime.utcnow()
        self._status = AgentStatus.RUNNING

        try:
            result = await self._run(task)
            task.result = result
            task.status = AgentStatus.COMPLETED
            self._status = AgentStatus.COMPLETED
        except Exception as exc:
            task.error = str(exc)
            task.status = AgentStatus.FAILED
            self._status = AgentStatus.FAILED
            self.logger.error("Task %s failed: %s", task.id, exc)
        finally:
            task.completed_at = datetime.utcnow()
            self._current_task = None

        return task

    @abstractmethod
    async def _run(self, task: AgentTask) -> Any:
        """Implement the agent's core domain logic.

        Must return a JSON-serialisable value that will be stored in
        ``task.result``.  Raise any exception to mark the task as FAILED.
        """
