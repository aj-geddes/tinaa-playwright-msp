"""Service container for TINAA MSP — wires all real services together.

Provides a lazy-initialized singleton container that instantiates each
service on first access. Import get_services() and use as a FastAPI
dependency or call directly from MCP tools.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tinaa.agents.orchestrator import Orchestrator
    from tinaa.alerts.engine import AlertEngine
    from tinaa.apm.baselines import BaselineManager
    from tinaa.apm.collector import MetricCollector
    from tinaa.config.parser import ConfigParser
    from tinaa.playbooks.executor import PlaybookExecutor
    from tinaa.playbooks.parser import PlaybookParser
    from tinaa.playbooks.validator import PlaybookValidator
    from tinaa.quality.gates import QualityGate
    from tinaa.quality.scorer import QualityScorer
    from tinaa.quality.trends import QualityTrendAnalyzer
    from tinaa.registry.service import ProductRegistryService

logger = logging.getLogger(__name__)


class ServiceContainer:
    """Lazy-initialized singleton service container.

    Each service property imports and instantiates the service on first
    access. This avoids import-time side effects and circular imports, and
    ensures the database engine is only created once per process.

    Use ServiceContainer.reset() in tests to discard the singleton.
    """

    _instance: ServiceContainer | None = None

    def __init__(self) -> None:
        self._registry: ProductRegistryService | None = None
        self._quality_scorer: QualityScorer | None = None
        self._quality_gate: QualityGate | None = None
        self._trend_analyzer: QualityTrendAnalyzer | None = None
        self._playbook_parser: PlaybookParser | None = None
        self._playbook_validator: PlaybookValidator | None = None
        self._playbook_executor: PlaybookExecutor | None = None
        self._alert_engine: AlertEngine | None = None
        self._config_parser: ConfigParser | None = None
        self._metric_collector: MetricCollector | None = None
        self._baseline_manager: BaselineManager | None = None
        self._orchestrator: Orchestrator | None = None

    @classmethod
    def get(cls) -> ServiceContainer:
        """Return (or create) the process-wide singleton container."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Discard the singleton. Used in tests to get a fresh container."""
        cls._instance = None

    # ------------------------------------------------------------------
    # Data / registry services
    # ------------------------------------------------------------------

    @property
    def registry(self) -> ProductRegistryService:
        """Return the ProductRegistryService, creating it on first access.

        The session factory is the AsyncSessionContext class itself — it is
        callable (returns an instance that is an async context manager), which
        is exactly what ProductRegistryService.session_factory expects.
        """
        if self._registry is None:
            from tinaa.database.session import AsyncSessionContext
            from tinaa.registry.service import ProductRegistryService

            self._registry = ProductRegistryService(AsyncSessionContext)
            logger.debug("Initialized ProductRegistryService")
        return self._registry

    # ------------------------------------------------------------------
    # Quality services
    # ------------------------------------------------------------------

    @property
    def quality_scorer(self) -> QualityScorer:
        """Return the QualityScorer, creating it on first access."""
        if self._quality_scorer is None:
            from tinaa.quality.scorer import QualityScorer

            self._quality_scorer = QualityScorer()
            logger.debug("Initialized QualityScorer")
        return self._quality_scorer

    @property
    def quality_gate(self) -> QualityGate:
        """Return the QualityGate, creating it on first access."""
        if self._quality_gate is None:
            from tinaa.quality.gates import QualityGate

            self._quality_gate = QualityGate()
            logger.debug("Initialized QualityGate")
        return self._quality_gate

    @property
    def trend_analyzer(self) -> QualityTrendAnalyzer:
        """Return the QualityTrendAnalyzer, creating it on first access."""
        if self._trend_analyzer is None:
            from tinaa.quality.trends import QualityTrendAnalyzer

            self._trend_analyzer = QualityTrendAnalyzer()
            logger.debug("Initialized QualityTrendAnalyzer")
        return self._trend_analyzer

    # ------------------------------------------------------------------
    # Playbook services
    # ------------------------------------------------------------------

    @property
    def playbook_parser(self) -> PlaybookParser:
        """Return the PlaybookParser, creating it on first access."""
        if self._playbook_parser is None:
            from tinaa.playbooks.parser import PlaybookParser

            self._playbook_parser = PlaybookParser()
            logger.debug("Initialized PlaybookParser")
        return self._playbook_parser

    @property
    def playbook_validator(self) -> PlaybookValidator:
        """Return the PlaybookValidator, creating it on first access."""
        if self._playbook_validator is None:
            from tinaa.playbooks.validator import PlaybookValidator

            self._playbook_validator = PlaybookValidator()
            logger.debug("Initialized PlaybookValidator")
        return self._playbook_validator

    @property
    def playbook_executor(self) -> PlaybookExecutor:
        """Return the PlaybookExecutor, creating it on first access."""
        if self._playbook_executor is None:
            from tinaa.playbooks.executor import PlaybookExecutor

            self._playbook_executor = PlaybookExecutor()
            logger.debug("Initialized PlaybookExecutor")
        return self._playbook_executor

    # ------------------------------------------------------------------
    # Alert services
    # ------------------------------------------------------------------

    @property
    def alert_engine(self) -> AlertEngine:
        """Return the AlertEngine, creating it on first access."""
        if self._alert_engine is None:
            from tinaa.alerts.engine import AlertEngine

            self._alert_engine = AlertEngine()
            logger.debug("Initialized AlertEngine")
        return self._alert_engine

    # ------------------------------------------------------------------
    # Config service
    # ------------------------------------------------------------------

    @property
    def config_parser(self) -> ConfigParser:
        """Return the ConfigParser, creating it on first access."""
        if self._config_parser is None:
            from tinaa.config.parser import ConfigParser

            self._config_parser = ConfigParser()
            logger.debug("Initialized ConfigParser")
        return self._config_parser

    # ------------------------------------------------------------------
    # APM services
    # ------------------------------------------------------------------

    @property
    def metric_collector(self) -> MetricCollector:
        """Return the MetricCollector, creating it on first access."""
        if self._metric_collector is None:
            from tinaa.apm.collector import MetricCollector

            self._metric_collector = MetricCollector(flush_interval=30, batch_size=100)
            logger.debug("Initialized MetricCollector")
        return self._metric_collector

    @property
    def baseline_manager(self) -> BaselineManager:
        """Return the BaselineManager, creating it on first access."""
        if self._baseline_manager is None:
            from tinaa.apm.baselines import BaselineManager

            self._baseline_manager = BaselineManager(min_samples=30, window_hours=168)
            logger.debug("Initialized BaselineManager")
        return self._baseline_manager

    # ------------------------------------------------------------------
    # Agent services
    # ------------------------------------------------------------------

    @property
    def orchestrator(self) -> Orchestrator:
        """Return the Orchestrator, creating it on first access."""
        if self._orchestrator is None:
            from tinaa.agents.orchestrator import Orchestrator

            self._orchestrator = Orchestrator()
            logger.debug("Initialized Orchestrator")
        return self._orchestrator


def get_services() -> ServiceContainer:
    """Return the global service container.

    Safe to use as a FastAPI dependency::

        @router.get("/products")
        async def list_products(services: ServiceContainer = Depends(get_services)):
            return await services.registry.list_products(org_id)
    """
    return ServiceContainer.get()
