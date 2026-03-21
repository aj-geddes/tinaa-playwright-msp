"""
Orchestrator — coordinates all TINAA sub-agents and routes work.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from tinaa.agents.base import AgentStatus, AgentTask, BaseAgent

# Event types handled by the orchestrator
PRODUCT_REGISTERED = "product_registered"
DEPLOYMENT_DETECTED = "deployment_detected"
PR_OPENED = "pr_opened"
SCHEDULE_TRIGGERED = "schedule_triggered"
ANOMALY_DETECTED = "anomaly_detected"
MANUAL_REQUEST = "manual_request"

_KNOWN_EVENTS = {
    PRODUCT_REGISTERED,
    DEPLOYMENT_DETECTED,
    PR_OPENED,
    SCHEDULE_TRIGGERED,
    ANOMALY_DETECTED,
    MANUAL_REQUEST,
}


class Orchestrator(BaseAgent):
    """Lead agent that coordinates all sub-agents and routes work.

    Agents register themselves with ``register_agent``.  Incoming events
    are translated into ``AgentTask`` objects and dispatched to the
    appropriate registered agent.
    """

    def __init__(self) -> None:
        super().__init__("orchestrator")
        self._agents: dict[str, BaseAgent] = {}
        self._event_handlers: dict[str, list[Callable]] = {}
        self._task_queue: list[AgentTask] = []

    # ------------------------------------------------------------------
    # Registration
    # ------------------------------------------------------------------

    def register_agent(self, agent: BaseAgent) -> None:
        """Register a sub-agent under its ``name`` key."""
        self._agents[agent.name] = agent
        self.logger.info("Registered agent: %s", agent.name)

    def on_event(self, event_type: str, handler: Callable) -> None:
        """Register a callable invoked after the orchestrator handles an event."""
        self._event_handlers.setdefault(event_type, []).append(handler)

    # ------------------------------------------------------------------
    # Event handling
    # ------------------------------------------------------------------

    async def handle_event(self, event_type: str, payload: dict) -> list[AgentTask]:
        """Translate an incoming event into tasks and dispatch them.

        Returns the list of created ``AgentTask`` objects (completed or failed).
        Unknown event types return an empty list rather than raising.
        """
        if event_type not in _KNOWN_EVENTS:
            self.logger.warning("Unknown event type: %s", event_type)
            return []

        tasks = self._build_tasks_for_event(event_type, payload)
        results: list[AgentTask] = []
        for task in tasks:
            result = await self.dispatch_task(task)
            results.append(result)

        return results

    def _build_tasks_for_event(self, event_type: str, payload: dict) -> list[AgentTask]:
        """Map event type to one or more AgentTask objects."""
        product_id = payload.get("product_id", "")

        if event_type == PRODUCT_REGISTERED:
            return [
                AgentTask(
                    agent_type="explorer",
                    action="explore_codebase",
                    params={
                        "repo_path": payload.get("repo_path", ""),
                        "product_id": product_id,
                    },
                ),
                AgentTask(
                    agent_type="orchestrator",
                    action="init_monitoring",
                    params={"product_id": product_id},
                ),
            ]

        if event_type == DEPLOYMENT_DETECTED:
            return [
                AgentTask(
                    agent_type="test_runner",
                    action="run_suite",
                    params={
                        "product_id": product_id,
                        "target_url": payload.get("deployment_url", ""),
                    },
                )
            ]

        if event_type == PR_OPENED:
            return [
                AgentTask(
                    agent_type="explorer",
                    action="analyze_diff",
                    params={
                        "product_id": product_id,
                        "changed_files": payload.get("changed_files", []),
                        "pr_number": payload.get("pr_number"),
                    },
                )
            ]

        if event_type == SCHEDULE_TRIGGERED:
            return [
                AgentTask(
                    agent_type="test_runner",
                    action="run_suite",
                    params={
                        "product_id": product_id,
                        "trigger": "schedule",
                    },
                )
            ]

        if event_type == ANOMALY_DETECTED:
            return [
                AgentTask(
                    agent_type="test_runner",
                    action="run_playbook",
                    params={
                        "product_id": product_id,
                        "endpoint": payload.get("endpoint", ""),
                        "metric": payload.get("metric", ""),
                    },
                )
            ]

        if event_type == MANUAL_REQUEST:
            return [
                AgentTask(
                    agent_type=payload.get("agent_type", "orchestrator"),
                    action=payload.get("action", "get_status"),
                    params=payload.get("params", {}),
                )
            ]

        return []

    # ------------------------------------------------------------------
    # Dispatch
    # ------------------------------------------------------------------

    async def dispatch_task(self, task: AgentTask) -> AgentTask:
        """Route a task to the agent registered under ``task.agent_type``.

        If the target agent is not registered the task is marked FAILED
        rather than raising an exception.
        """
        agent = self._agents.get(task.agent_type)
        if agent is None:
            task.status = AgentStatus.FAILED
            task.error = f"No agent registered for type '{task.agent_type}'"
            self.logger.error("Dispatch failed — no agent for type '%s'", task.agent_type)
            return task

        self.logger.info("Dispatching task %s → %s.%s", task.id, task.agent_type, task.action)
        return await agent.execute(task)

    # ------------------------------------------------------------------
    # Orchestrator's own _run
    # ------------------------------------------------------------------

    async def _run(self, task: AgentTask) -> Any:
        """Handle coordination tasks addressed directly to the orchestrator."""
        action = task.action

        if action == "get_status":
            return await self.get_status()

        if action == "init_monitoring":
            product_id = task.params.get("product_id", "")
            self.logger.info("Initialising monitoring for product %s", product_id)
            return {"monitoring_initialised": True, "product_id": product_id}

        raise ValueError(f"Orchestrator has no handler for action '{action}'")

    # ------------------------------------------------------------------
    # Status reporting
    # ------------------------------------------------------------------

    async def get_status(self) -> dict:
        """Return a snapshot of all registered agents and pending tasks."""
        agents_status = {name: agent.status.value for name, agent in self._agents.items()}
        return {
            "orchestrator": self._status.value,
            "agents": agents_status,
            "pending_tasks": len(self._task_queue),
            "registered_agent_count": len(self._agents),
        }
