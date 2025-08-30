#!/usr/bin/env python3
"""
Progress tracking system for TINAA operations
"""
import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger("tinaa-progress")


class ProgressLevel(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    SUCCESS = "success"
    DEBUG = "debug"


@dataclass
class ProgressUpdate:
    message: str
    level: ProgressLevel = ProgressLevel.INFO
    timestamp: datetime = field(default_factory=datetime.now)
    progress: Optional[float] = None  # 0-100
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "message": self.message,
            "level": self.level.value,
            "timestamp": self.timestamp.isoformat(),
        }
        if self.progress is not None:
            result["progress"] = self.progress
        if self.metadata:
            result["metadata"] = self.metadata
        return result


class ProgressTracker:
    def __init__(self, callback: Optional[Callable] = None):
        self.callback = callback
        self.updates: List[ProgressUpdate] = []
        self.start_time = time.time()
        self.current_phase = None
        self.phases_completed = 0
        self.total_phases = 0

    async def update(
        self,
        message: str,
        level: ProgressLevel = ProgressLevel.INFO,
        progress: Optional[float] = None,
        **metadata,
    ):
        """Send a progress update"""
        update = ProgressUpdate(
            message=message, level=level, progress=progress, metadata=metadata
        )
        self.updates.append(update)

        if self.callback:
            if asyncio.iscoroutinefunction(self.callback):
                await self.callback(update.to_dict())
            else:
                self.callback(update.to_dict())

        logger.log(
            getattr(logging, level.name, logging.INFO),
            f"[Progress] {message}"
            + (f" ({progress}%)" if progress is not None else ""),
        )

    async def start_phase(self, phase_name: str, total_phases: Optional[int] = None):
        """Start a new phase of operation"""
        self.current_phase = phase_name
        if total_phases:
            self.total_phases = total_phases

        progress = None
        if self.total_phases > 0:
            progress = (self.phases_completed / self.total_phases) * 100

        await self.update(
            f"Starting phase: {phase_name}",
            ProgressLevel.INFO,
            progress,
            phase=phase_name,
            phases_completed=self.phases_completed,
            total_phases=self.total_phases,
        )

    async def complete_phase(self, phase_name: str):
        """Complete a phase of operation"""
        self.phases_completed += 1
        progress = None
        if self.total_phases > 0:
            progress = (self.phases_completed / self.total_phases) * 100

        await self.update(
            f"Completed phase: {phase_name}",
            ProgressLevel.SUCCESS,
            progress,
            phase=phase_name,
            phases_completed=self.phases_completed,
            total_phases=self.total_phases,
        )

    async def error(self, message: str, **metadata):
        """Report an error"""
        await self.update(message, ProgressLevel.ERROR, **metadata)

    async def warning(self, message: str, **metadata):
        """Report a warning"""
        await self.update(message, ProgressLevel.WARNING, **metadata)

    async def success(self, message: str, **metadata):
        """Report a success"""
        await self.update(message, ProgressLevel.SUCCESS, **metadata)

    async def info(self, message: str, progress: Optional[float] = None, **metadata):
        """Report an info message"""
        await self.update(message, ProgressLevel.INFO, progress, **metadata)

    def get_elapsed_time(self) -> float:
        """Get elapsed time since tracker was created"""
        return time.time() - self.start_time

    def get_summary(self) -> Dict[str, Any]:
        """Get a summary of all progress updates"""
        return {
            "total_updates": len(self.updates),
            "elapsed_time": self.get_elapsed_time(),
            "phases_completed": self.phases_completed,
            "total_phases": self.total_phases,
            "current_phase": self.current_phase,
            "updates": [update.to_dict() for update in self.updates],
        }


# Progress context manager for specific operations
class ProgressContext:
    def __init__(
        self,
        tracker: ProgressTracker,
        operation_name: str,
        total_steps: Optional[int] = None,
    ):
        self.tracker = tracker
        self.operation_name = operation_name
        self.total_steps = total_steps
        self.current_step = 0

    async def __aenter__(self):
        await self.tracker.info(f"Starting {self.operation_name}")
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if exc_type:
            await self.tracker.error(
                f"Error in {self.operation_name}: {exc_val}", exception=str(exc_val)
            )
        else:
            await self.tracker.success(f"Completed {self.operation_name}")

    async def step(self, message: str, increment: int = 1):
        """Report progress on a step"""
        self.current_step += increment
        progress = None
        if self.total_steps:
            progress = (self.current_step / self.total_steps) * 100

        await self.tracker.info(
            message,
            progress=progress,
            step=self.current_step,
            total_steps=self.total_steps,
        )


# Specific progress trackers for different test types
class ExploratoryTestProgress(ProgressTracker):
    """Specialized progress tracker for exploratory testing"""

    async def navigation_started(self, url: str):
        await self.info(f"Navigating to {url}", progress=10)

    async def page_loaded(self):
        await self.info("Page loaded successfully", progress=20)

    async def analyzing_structure(self):
        await self.info("Analyzing page structure", progress=30)

    async def testing_interactions(self, total_elements: int):
        await self.info(
            f"Testing interactions with {total_elements} elements",
            progress=40,
            total_elements=total_elements,
        )

    async def element_tested(self, element_type: str, index: int, total: int):
        progress = 40 + (index / total) * 40  # 40-80% range
        await self.info(f"Testing {element_type} ({index}/{total})", progress=progress)

    async def generating_report(self):
        await self.info("Generating test report", progress=90)

    async def test_completed(self, findings_count: int):
        await self.success(
            f"Exploratory test completed with {findings_count} findings",
            progress=100,
            findings_count=findings_count,
        )


class AccessibilityTestProgress(ProgressTracker):
    """Specialized progress tracker for accessibility testing"""

    async def checking_wcag_compliance(self, level: str):
        await self.info(f"Checking WCAG {level} compliance", progress=20)

    async def testing_keyboard_navigation(self):
        await self.info("Testing keyboard navigation", progress=40)

    async def checking_aria_labels(self):
        await self.info("Checking ARIA labels and roles", progress=60)

    async def testing_color_contrast(self):
        await self.info("Testing color contrast ratios", progress=80)

    async def accessibility_issue_found(self, issue_type: str, severity: str):
        await self.warning(
            f"Accessibility issue found: {issue_type}",
            severity=severity,
            issue_type=issue_type,
        )
