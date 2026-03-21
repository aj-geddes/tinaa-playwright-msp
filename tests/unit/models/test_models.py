"""
Unit tests for TINAA MSP data models and Pydantic schemas.

Covers:
- SQLAlchemy ORM model instantiation
- Pydantic v2 schema validation (create / response / update)
- Enum membership
- Relationship definitions
- Timestamp mixin behaviour
- UUID primary key mixin
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest

# ---------------------------------------------------------------------------
# SQLAlchemy ORM models
# ---------------------------------------------------------------------------
from tinaa.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from tinaa.models.organization import Organization
from tinaa.models.product import Product, ProductStatus
from tinaa.models.environment import Environment, EnvironmentType
from tinaa.models.endpoint import Endpoint, EndpointType
from tinaa.models.playbook import Playbook, PlaybookPriority, PlaybookSource
from tinaa.models.test_run import (
    TestRun,
    TestResult,
    TestRunTrigger,
    TestRunStatus,
    TestResultStatus,
)
from tinaa.models.metrics import (
    MetricDatapoint,
    MetricBaseline,
    MetricType,
)
from tinaa.models.quality import QualityScoreSnapshot
from tinaa.models.alert import (
    AlertRule,
    AlertEvent,
    AlertConditionType,
    AlertSeverity,
)

# Deployment is in test_run module
from tinaa.models.test_run import Deployment, DeploymentStatus

# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------
from tinaa.models.organization import OrganizationCreate, OrganizationResponse
from tinaa.models.product import ProductCreate, ProductResponse, ProductUpdate
from tinaa.models.environment import EnvironmentCreate, EnvironmentResponse
from tinaa.models.endpoint import EndpointCreate, EndpointResponse
from tinaa.models.playbook import PlaybookCreate, PlaybookResponse
from tinaa.models.test_run import (
    TestRunCreate,
    TestRunResponse,
    TestResultCreate,
    TestResultResponse,
    DeploymentCreate,
    DeploymentResponse,
)
from tinaa.models.metrics import (
    MetricDatapointCreate,
    MetricDatapointResponse,
    MetricBaselineCreate,
    MetricBaselineResponse,
)
from tinaa.models.quality import (
    QualityScoreSnapshotCreate,
    QualityScoreSnapshotResponse,
)
from tinaa.models.alert import (
    AlertRuleCreate,
    AlertRuleResponse,
    AlertEventCreate,
    AlertEventResponse,
)

# ---------------------------------------------------------------------------
# Database layer
# ---------------------------------------------------------------------------
from tinaa.database.engine import create_async_engine_from_env, create_session_factory
from tinaa.database.session import get_async_session, AsyncSessionContext


# ===========================================================================
# Base / Mixin tests
# ===========================================================================


class TestBaseAndMixins:
    def test_base_is_declarative(self):
        """Base must be a SQLAlchemy DeclarativeBase."""
        # DeclarativeBase subclasses expose a metadata attribute
        assert hasattr(Base, "metadata")

    def test_timestamp_mixin_has_created_at(self):
        """TimestampMixin declares created_at column."""
        assert hasattr(TimestampMixin, "created_at")

    def test_timestamp_mixin_has_updated_at(self):
        """TimestampMixin declares updated_at column."""
        assert hasattr(TimestampMixin, "updated_at")

    def test_uuid_mixin_has_id(self):
        """UUIDPrimaryKeyMixin declares id column."""
        assert hasattr(UUIDPrimaryKeyMixin, "id")


# ===========================================================================
# Organization
# ===========================================================================


class TestOrganizationModel:
    def test_instantiation_with_required_fields(self):
        org = Organization(name="Acme Corp", slug="acme-corp")
        assert org.name == "Acme Corp"
        assert org.slug == "acme-corp"

    def test_github_installation_id_optional(self):
        org = Organization(name="Acme Corp", slug="acme-corp")
        assert org.github_installation_id is None

    def test_table_name(self):
        assert Organization.__tablename__ == "organizations"


class TestOrganizationSchemas:
    def test_create_schema_valid(self):
        data = OrganizationCreate(name="Acme Corp", slug="acme-corp")
        assert data.name == "Acme Corp"

    def test_create_schema_with_github_id(self):
        data = OrganizationCreate(
            name="Acme", slug="acme", github_installation_id=12345
        )
        assert data.github_installation_id == 12345

    def test_response_schema_requires_id(self):
        now = datetime.now(timezone.utc)
        resp = OrganizationResponse(
            id=uuid.uuid4(),
            name="Acme",
            slug="acme",
            github_installation_id=None,
            created_at=now,
            updated_at=now,
        )
        assert isinstance(resp.id, uuid.UUID)

    def test_create_schema_rejects_missing_name(self):
        with pytest.raises(Exception):
            OrganizationCreate(slug="acme")  # name required


# ===========================================================================
# Product
# ===========================================================================


class TestProductModel:
    def test_instantiation(self):
        product = Product(
            name="WebApp",
            slug="webapp",
            organization_id=uuid.uuid4(),
            status=ProductStatus.active,
        )
        assert product.name == "WebApp"
        assert product.status == ProductStatus.active

    def test_default_branch_is_main(self):
        product = Product(
            name="WebApp",
            slug="webapp",
            organization_id=uuid.uuid4(),
        )
        assert product.default_branch == "main"

    def test_table_name(self):
        assert Product.__tablename__ == "products"


class TestProductEnums:
    def test_status_values(self):
        assert ProductStatus.active.value == "active"
        assert ProductStatus.paused.value == "paused"
        assert ProductStatus.archived.value == "archived"


class TestProductSchemas:
    def _org_id(self) -> uuid.UUID:
        return uuid.uuid4()

    def test_create_schema(self):
        data = ProductCreate(
            name="WebApp",
            slug="webapp",
            organization_id=self._org_id(),
            status="active",
        )
        assert data.slug == "webapp"

    def test_update_schema_all_optional(self):
        update = ProductUpdate()
        assert update.name is None

    def test_response_schema(self):
        now = datetime.now(timezone.utc)
        resp = ProductResponse(
            id=uuid.uuid4(),
            organization_id=self._org_id(),
            name="WebApp",
            slug="webapp",
            description=None,
            repository_url=None,
            repository_owner=None,
            repository_name=None,
            default_branch="main",
            quality_score=None,
            quality_score_updated_at=None,
            status="active",
            config={},
            created_at=now,
            updated_at=now,
        )
        assert resp.default_branch == "main"


# ===========================================================================
# Environment
# ===========================================================================


class TestEnvironmentModel:
    def test_instantiation(self):
        env = Environment(
            name="production",
            env_type=EnvironmentType.production,
            base_url="https://example.com",
            product_id=uuid.uuid4(),
        )
        assert env.name == "production"
        assert env.is_active is True

    def test_default_monitoring_interval(self):
        env = Environment(
            name="staging",
            env_type=EnvironmentType.staging,
            base_url="https://staging.example.com",
            product_id=uuid.uuid4(),
        )
        assert env.monitoring_interval_seconds == 300

    def test_table_name(self):
        assert Environment.__tablename__ == "environments"


class TestEnvironmentEnums:
    def test_env_type_values(self):
        assert EnvironmentType.production.value == "production"
        assert EnvironmentType.staging.value == "staging"
        assert EnvironmentType.development.value == "development"
        assert EnvironmentType.preview.value == "preview"


class TestEnvironmentSchemas:
    def test_create_schema(self):
        data = EnvironmentCreate(
            name="production",
            env_type="production",
            base_url="https://example.com",
        )
        assert data.base_url == "https://example.com"

    def test_create_schema_no_product_id(self):
        """product_id must not be a field on EnvironmentCreate — the service sets it."""
        data = EnvironmentCreate(
            name="staging",
            base_url="https://staging.example.com",
        )
        assert not hasattr(data, "product_id")

    def test_create_schema_env_type_defaults_to_staging(self):
        """env_type should default to EnvironmentType.STAGING when not supplied."""
        from tinaa.models.environment import EnvironmentType

        data = EnvironmentCreate(
            name="my-env",
            base_url="https://staging.example.com",
        )
        assert data.env_type == EnvironmentType.staging

    def test_response_schema(self):
        now = datetime.now(timezone.utc)
        resp = EnvironmentResponse(
            id=uuid.uuid4(),
            product_id=uuid.uuid4(),
            name="production",
            env_type="production",
            base_url="https://example.com",
            is_active=True,
            monitoring_interval_seconds=300,
            created_at=now,
            updated_at=now,
        )
        assert resp.is_active is True


# ===========================================================================
# Endpoint
# ===========================================================================


class TestEndpointModel:
    def test_instantiation(self):
        ep = Endpoint(
            path="/login",
            environment_id=uuid.uuid4(),
        )
        assert ep.path == "/login"
        assert ep.method == "GET"
        assert ep.expected_status_code == 200
        assert ep.is_monitored is True

    def test_table_name(self):
        assert Endpoint.__tablename__ == "endpoints"


class TestEndpointEnums:
    def test_endpoint_type_values(self):
        assert EndpointType.page.value == "page"
        assert EndpointType.api.value == "api"
        assert EndpointType.health.value == "health"
        assert EndpointType.websocket.value == "websocket"


class TestEndpointSchemas:
    def test_create_schema(self):
        data = EndpointCreate(
            path="/api/v1/users",
            environment_id=uuid.uuid4(),
            endpoint_type="api",
        )
        assert data.method == "GET"

    def test_response_schema(self):
        now = datetime.now(timezone.utc)
        resp = EndpointResponse(
            id=uuid.uuid4(),
            environment_id=uuid.uuid4(),
            path="/login",
            method="GET",
            endpoint_type="page",
            performance_budget_ms=None,
            lcp_budget_ms=None,
            cls_budget=None,
            expected_status_code=200,
            is_monitored=True,
            last_check_at=None,
            last_status=None,
            created_at=now,
            updated_at=now,
        )
        assert resp.expected_status_code == 200


# ===========================================================================
# Playbook
# ===========================================================================


class TestPlaybookModel:
    def test_instantiation(self):
        pb = Playbook(
            name="Login Flow",
            priority=PlaybookPriority.critical,
            source=PlaybookSource.auto_generated,
            product_id=uuid.uuid4(),
        )
        assert pb.trigger_on_deploy is True
        assert pb.trigger_on_pr is True
        assert pb.is_active is True

    def test_table_name(self):
        assert Playbook.__tablename__ == "playbooks"


class TestPlaybookEnums:
    def test_priority_values(self):
        assert PlaybookPriority.critical.value == "critical"
        assert PlaybookPriority.high.value == "high"
        assert PlaybookPriority.medium.value == "medium"
        assert PlaybookPriority.low.value == "low"

    def test_source_values(self):
        assert PlaybookSource.auto_generated.value == "auto_generated"
        assert PlaybookSource.manual.value == "manual"
        assert PlaybookSource.hybrid.value == "hybrid"


class TestPlaybookSchemas:
    def test_create_schema(self):
        data = PlaybookCreate(
            name="Login Flow",
            priority="critical",
            source="manual",
            product_id=uuid.uuid4(),
        )
        assert data.trigger_on_deploy is True

    def test_response_schema(self):
        now = datetime.now(timezone.utc)
        resp = PlaybookResponse(
            id=uuid.uuid4(),
            product_id=uuid.uuid4(),
            name="Login Flow",
            description=None,
            priority="critical",
            source="manual",
            trigger_on_deploy=True,
            trigger_on_pr=True,
            schedule_cron=None,
            steps=[],
            assertions=[],
            performance_gates={},
            is_active=True,
            last_run_at=None,
            last_result=None,
            affected_paths=[],
            created_at=now,
            updated_at=now,
        )
        assert resp.is_active is True


# ===========================================================================
# TestRun and TestResult
# ===========================================================================


class TestTestRunModel:
    def test_instantiation(self):
        run = TestRun(
            product_id=uuid.uuid4(),
            environment_id=uuid.uuid4(),
            trigger=TestRunTrigger.deployment,
            status=TestRunStatus.queued,
        )
        assert run.status == TestRunStatus.queued

    def test_table_name(self):
        assert TestRun.__tablename__ == "test_runs"


class TestTestResultModel:
    def test_instantiation(self):
        result = TestResult(
            test_run_id=uuid.uuid4(),
            step_index=0,
            step_name="Navigate to login",
            status=TestResultStatus.passed,
            duration_ms=123,
        )
        assert result.step_index == 0
        assert result.duration_ms == 123

    def test_table_name(self):
        assert TestResult.__tablename__ == "test_results"


class TestTestRunEnums:
    def test_trigger_values(self):
        assert TestRunTrigger.deployment.value == "deployment"
        assert TestRunTrigger.schedule.value == "schedule"
        assert TestRunTrigger.manual.value == "manual"
        assert TestRunTrigger.pr.value == "pr"
        assert TestRunTrigger.anomaly.value == "anomaly"

    def test_status_values(self):
        assert TestRunStatus.queued.value == "queued"
        assert TestRunStatus.running.value == "running"
        assert TestRunStatus.passed.value == "passed"
        assert TestRunStatus.failed.value == "failed"
        assert TestRunStatus.error.value == "error"
        assert TestRunStatus.cancelled.value == "cancelled"

    def test_result_status_values(self):
        assert TestResultStatus.passed.value == "passed"
        assert TestResultStatus.failed.value == "failed"
        assert TestResultStatus.skipped.value == "skipped"
        assert TestResultStatus.error.value == "error"


class TestTestRunSchemas:
    def test_create_schema(self):
        data = TestRunCreate(
            product_id=uuid.uuid4(),
            environment_id=uuid.uuid4(),
            trigger="manual",
            status="queued",
        )
        assert data.trigger == "manual"

    def test_result_create_schema(self):
        data = TestResultCreate(
            test_run_id=uuid.uuid4(),
            step_index=1,
            step_name="Click submit",
            status="passed",
            duration_ms=50,
        )
        assert data.step_index == 1


# ===========================================================================
# Deployment
# ===========================================================================


class TestDeploymentModel:
    def test_instantiation(self):
        dep = Deployment(
            product_id=uuid.uuid4(),
            environment_id=uuid.uuid4(),
            commit_sha="abc123",
            ref="main",
            status=DeploymentStatus.pending,
        )
        assert dep.commit_sha == "abc123"
        assert dep.status == DeploymentStatus.pending

    def test_table_name(self):
        assert Deployment.__tablename__ == "deployments"


class TestDeploymentEnums:
    def test_status_values(self):
        assert DeploymentStatus.pending.value == "pending"
        assert DeploymentStatus.in_progress.value == "in_progress"
        assert DeploymentStatus.success.value == "success"
        assert DeploymentStatus.failure.value == "failure"
        assert DeploymentStatus.error.value == "error"


class TestDeploymentSchemas:
    def test_create_schema(self):
        data = DeploymentCreate(
            product_id=uuid.uuid4(),
            environment_id=uuid.uuid4(),
            commit_sha="abc123def456",
            ref="main",
            status="pending",
        )
        assert data.ref == "main"

    def test_response_schema(self):
        now = datetime.now(timezone.utc)
        resp = DeploymentResponse(
            id=uuid.uuid4(),
            product_id=uuid.uuid4(),
            environment_id=uuid.uuid4(),
            commit_sha="abc123",
            ref="main",
            deployment_url=None,
            github_deployment_id=None,
            status="pending",
            deployer=None,
            triggered_test_runs=[],
            quality_score_delta=None,
            created_at=now,
        )
        assert resp.status == "pending"


# ===========================================================================
# Metrics
# ===========================================================================


class TestMetricDatapointModel:
    def test_instantiation(self):
        dp = MetricDatapoint(
            endpoint_id=uuid.uuid4(),
            timestamp=datetime.now(timezone.utc),
            metric_type=MetricType.response_time,
            value=250.0,
        )
        assert dp.value == 250.0

    def test_table_name(self):
        assert MetricDatapoint.__tablename__ == "metric_datapoints"


class TestMetricBaselineModel:
    def test_instantiation(self):
        baseline = MetricBaseline(
            endpoint_id=uuid.uuid4(),
            metric_type=MetricType.lcp,
            p50=1200.0,
            p95=2500.0,
            p99=4000.0,
            sample_count=1000,
            window_start=datetime.now(timezone.utc),
            window_end=datetime.now(timezone.utc),
        )
        assert baseline.is_current is True
        assert baseline.p95 == 2500.0

    def test_table_name(self):
        assert MetricBaseline.__tablename__ == "metric_baselines"


class TestMetricEnums:
    def test_metric_type_values(self):
        expected = {
            "response_time", "ttfb", "fcp", "lcp", "cls", "inp",
            "availability", "error_rate", "status_code",
        }
        actual = {m.value for m in MetricType}
        assert expected == actual


class TestMetricSchemas:
    def test_datapoint_create_schema(self):
        data = MetricDatapointCreate(
            endpoint_id=uuid.uuid4(),
            timestamp=datetime.now(timezone.utc),
            metric_type="response_time",
            value=150.0,
        )
        assert data.value == 150.0

    def test_baseline_create_schema(self):
        now = datetime.now(timezone.utc)
        data = MetricBaselineCreate(
            endpoint_id=uuid.uuid4(),
            metric_type="lcp",
            p50=1100.0,
            p95=2200.0,
            p99=3500.0,
            sample_count=500,
            window_start=now,
            window_end=now,
        )
        assert data.p50 == 1100.0


# ===========================================================================
# QualityScoreSnapshot
# ===========================================================================


class TestQualityScoreSnapshotModel:
    def test_instantiation(self):
        snap = QualityScoreSnapshot(
            product_id=uuid.uuid4(),
            score=82.5,
            test_health_score=90.0,
            performance_health_score=78.0,
            security_posture_score=85.0,
            accessibility_score=80.0,
        )
        assert snap.score == 82.5

    def test_environment_id_optional(self):
        snap = QualityScoreSnapshot(
            product_id=uuid.uuid4(),
            score=80.0,
            test_health_score=80.0,
            performance_health_score=80.0,
            security_posture_score=80.0,
            accessibility_score=80.0,
        )
        assert snap.environment_id is None

    def test_table_name(self):
        assert QualityScoreSnapshot.__tablename__ == "quality_score_snapshots"


class TestQualitySchemas:
    def test_create_schema(self):
        data = QualityScoreSnapshotCreate(
            product_id=uuid.uuid4(),
            score=85.0,
            test_health_score=90.0,
            performance_health_score=80.0,
            security_posture_score=85.0,
            accessibility_score=85.0,
        )
        assert data.score == 85.0

    def test_response_schema(self):
        now = datetime.now(timezone.utc)
        resp = QualityScoreSnapshotResponse(
            id=uuid.uuid4(),
            product_id=uuid.uuid4(),
            environment_id=None,
            score=85.0,
            test_health_score=90.0,
            performance_health_score=80.0,
            security_posture_score=85.0,
            accessibility_score=85.0,
            test_pass_rate=None,
            coverage_breadth=None,
            availability=None,
            avg_response_time_ms=None,
            details={},
            created_at=now,
        )
        assert resp.score == 85.0


# ===========================================================================
# AlertRule and AlertEvent
# ===========================================================================


class TestAlertRuleModel:
    def test_instantiation(self):
        rule = AlertRule(
            name="Quality Drop",
            condition_type=AlertConditionType.quality_score_drop,
            threshold={"min": 70.0},
            channels=[{"type": "slack", "webhook": "https://hooks.slack.com/..."}],
            product_id=uuid.uuid4(),
        )
        assert rule.is_active is True

    def test_table_name(self):
        assert AlertRule.__tablename__ == "alert_rules"


class TestAlertEventModel:
    def test_instantiation(self):
        event = AlertEvent(
            alert_rule_id=uuid.uuid4(),
            severity=AlertSeverity.critical,
            message="Quality score dropped below threshold",
            details={"score": 60.0},
        )
        assert event.acknowledged is False
        assert event.resolved is False

    def test_table_name(self):
        assert AlertEvent.__tablename__ == "alert_events"


class TestAlertEnums:
    def test_condition_type_values(self):
        assert AlertConditionType.quality_score_drop.value == "quality_score_drop"
        assert AlertConditionType.test_failure.value == "test_failure"
        assert AlertConditionType.performance_regression.value == "performance_regression"
        assert AlertConditionType.endpoint_down.value == "endpoint_down"
        assert AlertConditionType.security_issue.value == "security_issue"

    def test_severity_values(self):
        assert AlertSeverity.critical.value == "critical"
        assert AlertSeverity.warning.value == "warning"
        assert AlertSeverity.info.value == "info"


class TestAlertSchemas:
    def test_rule_create_schema(self):
        data = AlertRuleCreate(
            name="Quality Drop",
            condition_type="quality_score_drop",
            threshold={"min": 70.0},
            channels=[],
            product_id=uuid.uuid4(),
        )
        assert data.is_active is True

    def test_event_create_schema(self):
        data = AlertEventCreate(
            alert_rule_id=uuid.uuid4(),
            severity="critical",
            message="Score dropped",
            details={},
        )
        assert data.acknowledged is False

    def test_alert_rule_response_schema(self):
        now = datetime.now(timezone.utc)
        resp = AlertRuleResponse(
            id=uuid.uuid4(),
            product_id=uuid.uuid4(),
            name="Quality Drop",
            condition_type="quality_score_drop",
            threshold={"min": 70.0},
            channels=[],
            is_active=True,
            last_triggered_at=None,
            created_at=now,
            updated_at=now,
        )
        assert resp.name == "Quality Drop"

    def test_alert_event_response_schema(self):
        now = datetime.now(timezone.utc)
        resp = AlertEventResponse(
            id=uuid.uuid4(),
            alert_rule_id=uuid.uuid4(),
            severity="warning",
            message="Performance regression detected",
            details={},
            acknowledged=False,
            acknowledged_by=None,
            resolved=False,
            resolved_at=None,
            created_at=now,
        )
        assert resp.resolved is False


# ===========================================================================
# Database layer
# ===========================================================================


class TestDatabaseEngine:
    def test_create_async_engine_returns_engine(self):
        """create_async_engine_from_env must return an AsyncEngine."""
        from sqlalchemy.ext.asyncio import AsyncEngine

        engine = create_async_engine_from_env()
        assert isinstance(engine, AsyncEngine)

    def test_create_session_factory_returns_factory(self):
        """create_session_factory must return an async_sessionmaker."""
        from sqlalchemy.ext.asyncio import async_sessionmaker

        engine = create_async_engine_from_env()
        factory = create_session_factory(engine)
        assert isinstance(factory, async_sessionmaker)


class TestDatabaseSession:
    def test_async_session_context_is_callable(self):
        """AsyncSessionContext must be a callable (class or function)."""
        assert callable(AsyncSessionContext)

    def test_get_async_session_is_async_generator(self):
        """get_async_session must be an async generator function."""
        import inspect

        assert inspect.isasyncgenfunction(get_async_session)


# ===========================================================================
# Relationship definitions (structural checks)
# ===========================================================================


class TestRelationships:
    def test_product_has_organization_relationship(self):
        assert hasattr(Product, "organization")

    def test_product_has_environments_relationship(self):
        assert hasattr(Product, "environments")

    def test_product_has_playbooks_relationship(self):
        assert hasattr(Product, "playbooks")

    def test_environment_has_endpoints_relationship(self):
        assert hasattr(Environment, "endpoints")

    def test_playbook_has_test_runs_relationship(self):
        assert hasattr(Playbook, "test_runs")

    def test_test_run_has_results_relationship(self):
        assert hasattr(TestRun, "results")

    def test_endpoint_has_metric_datapoints_relationship(self):
        assert hasattr(Endpoint, "metric_datapoints")

    def test_endpoint_has_metric_baselines_relationship(self):
        assert hasattr(Endpoint, "metric_baselines")

    def test_alert_rule_has_events_relationship(self):
        assert hasattr(AlertRule, "events")


# ===========================================================================
# Edge-case / boundary tests
# ===========================================================================


class TestPydanticValidationEdgeCases:
    def test_product_quality_score_accepts_zero(self):
        data = ProductCreate(
            name="X",
            slug="x",
            organization_id=uuid.uuid4(),
            status="active",
            quality_score=0.0,
        )
        assert data.quality_score == 0.0

    def test_product_quality_score_accepts_hundred(self):
        data = ProductCreate(
            name="X",
            slug="x",
            organization_id=uuid.uuid4(),
            status="active",
            quality_score=100.0,
        )
        assert data.quality_score == 100.0

    def test_metric_datapoint_accepts_zero_value(self):
        data = MetricDatapointCreate(
            endpoint_id=uuid.uuid4(),
            timestamp=datetime.now(timezone.utc),
            metric_type="availability",
            value=0.0,
        )
        assert data.value == 0.0

    def test_organization_create_rejects_empty_slug(self):
        with pytest.raises(Exception):
            OrganizationCreate(name="Acme", slug="")

    def test_quality_snapshot_score_range(self):
        """score must be between 0 and 100."""
        data = QualityScoreSnapshotCreate(
            product_id=uuid.uuid4(),
            score=0.0,
            test_health_score=0.0,
            performance_health_score=0.0,
            security_posture_score=0.0,
            accessibility_score=0.0,
        )
        assert data.score == 0.0


# ===========================================================================
# Async database integration tests
# ===========================================================================


class TestDatabaseEngineEnvVars:
    def test_db_echo_false_by_default(self):
        """DB_ECHO env var defaults to false."""
        import os

        os.environ.pop("DB_ECHO", None)
        engine = create_async_engine_from_env()
        assert engine is not None

    def test_db_echo_true_when_set(self):
        """DB_ECHO=true enables SQL echo."""
        import os

        os.environ["DB_ECHO"] = "true"
        engine = create_async_engine_from_env()
        assert engine is not None
        os.environ.pop("DB_ECHO", None)

    def test_sqlite_url_by_default(self):
        """Default DATABASE_URL uses sqlite+aiosqlite."""
        import os

        from tinaa.database.engine import DEFAULT_DATABASE_URL

        os.environ.pop("DATABASE_URL", None)
        assert DEFAULT_DATABASE_URL.startswith("sqlite+aiosqlite")
        engine = create_async_engine_from_env()
        assert engine is not None

    def test_custom_database_url(self):
        """Custom DATABASE_URL is picked up from the environment."""
        import os

        os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///./custom_test.db"
        engine = create_async_engine_from_env()
        assert engine is not None
        os.environ.pop("DATABASE_URL", None)


@pytest.mark.asyncio
class TestAsyncSessionContext:
    async def test_context_manager_yields_session(self):
        """AsyncSessionContext yields a live AsyncSession."""
        from sqlalchemy.ext.asyncio import AsyncSession

        async with AsyncSessionContext() as session:
            assert isinstance(session, AsyncSession)

    async def test_context_manager_rolls_back_on_error(self):
        """AsyncSessionContext rolls back and re-raises on exception."""
        with pytest.raises(ValueError, match="test error"):
            async with AsyncSessionContext() as session:
                assert session is not None
                raise ValueError("test error")

    async def test_context_manager_commits_on_success(self):
        """AsyncSessionContext exits cleanly without raising."""
        async with AsyncSessionContext() as session:
            # No-op query to exercise the commit path
            from sqlalchemy import text

            await session.execute(text("SELECT 1"))


@pytest.mark.asyncio
class TestGetAsyncSession:
    async def test_get_async_session_yields_session(self):
        """get_async_session async generator yields an AsyncSession."""
        from sqlalchemy import text
        from sqlalchemy.ext.asyncio import AsyncSession

        async for session in get_async_session():
            assert isinstance(session, AsyncSession)
            await session.execute(text("SELECT 1"))

    async def test_get_async_session_rolls_back_on_exception(self):
        """get_async_session rolls back and re-raises on unhandled exception."""
        with pytest.raises(RuntimeError, match="simulated failure"):
            async for session in get_async_session():
                assert session is not None
                raise RuntimeError("simulated failure")
