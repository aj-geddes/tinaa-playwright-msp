# TINAA MSP Integration Report

**Date**: 2026-03-20
**Scope**: Full codebase discovery after 12 parallel agent builds
**Author**: Architect Agent

---

## A. Structural Issues

### A1. Missing Entry Points (CRITICAL)

`pyproject.toml` declares two console scripts that do not exist:

```
tinaa = "tinaa.mcp_server.server:main"
tinaa-api = "tinaa.api.app:main"
```

Neither `tinaa/mcp_server/server.py` nor `tinaa/api/app.py` defines a `main()` function. The `server.py` has a `if __name__ == "__main__"` block but no callable `main`. The `app.py` only has `create_app()`.

**Impact**: `pip install .` succeeds, but running `tinaa` or `tinaa-api` from the command line immediately crashes with `AttributeError: module has no attribute 'main'`.

**Fix**: Add `main()` functions to both modules.

### A2. Ruff Configuration Conflict (IMPORTANT)

Two conflicting ruff configurations exist:

| Setting | `ruff.toml` (standalone) | `pyproject.toml` `[tool.ruff]` |
|---------|-------------------------|-------------------------------|
| `line-length` | 88 | 100 |
| `target-version` | py310 | py311 |
| `lint.select` | 22 rule groups | 9 rule groups |

The standalone `ruff.toml` takes precedence over `pyproject.toml`. The `target-version = "py310"` in `ruff.toml` contradicts `requires-python = ">=3.11"` in `pyproject.toml`.

Additionally, `ruff.toml` ignores `F821` (undefined name), `F841` (unused variable), and `E722` (bare except) -- these are real bugs that should be caught, not suppressed. This looks like a team that added ignores to make their code pass lint rather than fixing the issues.

### A3. Eager Database Initialization in session.py (IMPORTANT)

`tinaa/database/session.py` lines 26-27 execute at import time:

```python
_engine = create_async_engine_from_env()
_session_factory = create_session_factory(_engine)
```

This means importing anything that touches the database module (even in tests) immediately creates a database engine from environment variables. Any import of `tinaa.registry`, `tinaa.models`, or the session module itself triggers this side effect.

**Impact**: Tests fail or connect to unexpected databases. Cannot cleanly inject test database URLs.

### A4. SQLAlchemy result.first() vs scalars().first() (BUG)

`tinaa/registry/service.py` uses `result.first()` and `result.all()` on raw `execute()` results. With SQLAlchemy 2.0, `execute()` returns `Result` objects where `.first()` returns a `Row` (a tuple-like), not the ORM model instance. The code then calls `ProductResponse.model_validate(product)` expecting an ORM object but receives a `Row`.

This will either fail with a Pydantic validation error or silently produce incorrect data.

**Fix**: Use `result.scalars().first()` and `result.scalars().all()`.

### A5. Deprecated datetime.utcnow() (IMPORTANT)

`tinaa/agents/base.py` uses `datetime.utcnow()` in three places (lines 40, 78, 92). This is deprecated since Python 3.12 and produces timezone-naive datetimes, which are inconsistent with the timezone-aware datetimes used everywhere else in the codebase (`datetime.now(timezone.utc)`).

### A6. No Alembic Configuration (IMPORTANT)

The Makefile references `alembic upgrade head` and `alembic revision --autogenerate`, but there is no `alembic.ini` or `alembic/` directory. The 11 SQLAlchemy models define tables but there is no way to create them in the database.

**Impact**: `make migrate` fails. No database schema can be created.

---

## B. Integration Gaps

This is the most critical section. The 12 modules were built in parallel with stub/mock data. Here is where they should connect but do not.

### B1. API Routes -- All Returning Stub Data (CRITICAL)

Every API route handler returns hardcoded stub data instead of calling the actual service layer:

| Route File | Should Call | Currently Does |
|------------|-----------|----------------|
| `api/routes/products.py` | `tinaa.registry.ProductRegistryService` | Returns hardcoded `_stub_product()` dicts |
| `api/routes/playbooks.py` | `tinaa.playbooks.PlaybookParser`, `PlaybookExecutor` | Returns hardcoded stub dicts |
| `api/routes/test_runs.py` | `tinaa.agents.Orchestrator`, `TestRunnerAgent` | Returns hardcoded stub dicts |
| `api/routes/metrics.py` | `tinaa.apm.MetricCollector`, `BaselineManager` | Returns `_make_metric_series()` hardcoded data |
| `api/routes/quality.py` | `tinaa.quality.QualityScorer`, `QualityGate` | Returns hardcoded score 87.5 |
| `api/routes/webhooks.py` | `tinaa.github.TINAAGitHubApp` | Has its own inline handlers, does not use `TINAAGitHubApp` |

The API routes also define their own Pydantic models (`ProductCreateRequest`, `ProductResponse`) that duplicate and conflict with the canonical models in `tinaa/models/product.py`. The API route `ProductResponse.id` is a `str`, but the model's is a `uuid.UUID`.

### B2. MCP Tools -- All Returning Mock Data (CRITICAL)

All 14 MCP tools in `tinaa/mcp_server/tools.py` return hardcoded mock data. None of them call any actual service:

- `register_product()` -- generates a fake product_id, does not call `ProductRegistryService`
- `list_products()` -- returns 3 hardcoded products
- `get_quality_score()` -- returns hardcoded score of 87
- `run_playbook()` -- returns fake results, does not call `PlaybookExecutor`
- `run_suite()` -- returns fake results
- `get_metrics()` -- returns 4 hardcoded data points
- `configure_alerts()` -- returns "ok" without saving anything
- `explore_codebase()` -- returns hardcoded routes/APIs/forms

The MCP resources in `tinaa/mcp_server/resources.py` are the same -- all hardcoded text strings.

### B3. Agents Not Wired to Services (CRITICAL)

The `Orchestrator` can dispatch tasks to agents, but:

1. The agents are never instantiated or registered anywhere in the application startup
2. `Orchestrator._run()` only handles `get_status` and `init_monitoring` -- the `init_monitoring` handler just logs and returns, does not call `EndpointMonitor`
3. No code connects GitHub webhook events to `Orchestrator.handle_event()`
4. No code connects APM anomaly detection to the orchestrator

### B4. GitHub Webhooks Disconnected from Orchestrator (CRITICAL)

Two completely independent webhook handler implementations exist:

1. `tinaa/github/webhooks.py` + `tinaa/github/app.py` -- the GitHub module's handler with signature verification and event routing
2. `tinaa/api/routes/webhooks.py` -- the API route's handler with its own signature verification and its own stub event handlers

Neither calls the other. Neither calls the `Orchestrator`. The API webhook route's handlers just log and return stub dicts. The GitHub module's handlers (`_on_deployment_status`, `_on_pull_request`, `_on_push`) also just log and return minimal dicts without triggering any TINAA actions.

### B5. APM Monitor Not Connected to Registry or Alerts (IMPORTANT)

`EndpointMonitor` has a fully working probe loop, but:

1. No code fetches endpoints from `ProductRegistryService.get_endpoints_for_monitoring()` to feed into `start_monitoring()`
2. No code feeds probe results into `AlertEngine.evaluate_endpoint_health()`
3. `MetricCollector` has no storage callback set -- samples are buffered but flushed to nowhere (`_storage_callback` is None)
4. No code persists metrics to the database using the `MetricDatapoint` model

### B6. Quality Scorer Not Connected to Data Sources (IMPORTANT)

`QualityScorer.compute_quality_score()` accepts four input dataclasses, but nothing in the application collects the data to populate them:

- `TestHealthInput` -- needs data from test run records
- `PerformanceHealthInput` -- needs data from APM metrics
- `SecurityPostureInput` -- needs data from security scans (no scanner exists)
- `AccessibilityInput` -- needs data from accessibility audits (no auditor exists)

### B7. Alert Engine Not Wired Into Application Lifecycle (IMPORTANT)

`AlertEngine` is fully implemented with 7 condition types and 5 channels, but:

1. No code instantiates `AlertEngine` during app startup
2. No code calls `evaluate_quality_score()` after quality scores are computed
3. No code calls `evaluate_endpoint_health()` after endpoint probes
4. No code calls `evaluate_test_results()` after test runs
5. No alert channels are registered

### B8. Config Parser Not Used at Startup (IMPORTANT)

`ConfigParser` can parse `.tinaa.yml` files, but:

1. No code reads a config file during app startup
2. No code transforms `TINAAConfig` into `ProductRegistryService` calls
3. `TINAAGitHubApp.onboard_repository()` reads `.tinaa.yml` from GitHub but does nothing with it beyond returning the raw content

### B9. Playbook Validator Called From Executor But Not From API (MINOR)

`PlaybookExecutor` validates playbooks internally, but the API route `validate_playbook` does its own inline validation (checking only that each step has an "action" key) instead of calling `PlaybookValidator`.

---

## C. Configuration Issues

### C1. Missing Alembic Setup (CRITICAL)

No `alembic.ini`, no `alembic/` directory. The Makefile `migrate` target will fail.

### C2. Missing `main()` Entry Points (CRITICAL)

Covered in A1. Both console scripts point to nonexistent functions.

### C3. pyproject.toml Dependencies (OK with notes)

Dependencies are correctly declared for the current feature set. Notes:

- `redis[hiredis]>=5.0.0` is declared but Redis is not used anywhere in the Python code. The docker-compose starts Redis but no module imports or uses it.
- `pyyaml` is correctly included (used by playbook parser and config parser).
- `fastmcp>=2.0.0` -- verify that `FunctionTool.from_function` and `FunctionResource.from_function` APIs are stable in the installed version.

### C4. Dockerfile is Functional (OK with notes)

The multi-stage Dockerfile is well-structured. Issues:

- Production stage copies `tinaa/` but does not copy `pyproject.toml` for `pip install .` -- the venv from the builder stage already has the package installed, but the source in `/app/tinaa/` is just raw files. The `COPY --chown=tinaa:tinaa tinaa/ ./tinaa/` copies source, but the installed package in the venv points to `/build/tinaa/` from the builder stage. This means changes in `/app/tinaa/` are NOT what gets imported -- the installed egg in site-packages is. This needs verification: either install in editable mode or copy the full project and reinstall.
- `scripts/docker-entrypoint.sh` references `exec tinaa` (the console script), which depends on the broken `main()` entry point (see A1).

### C5. Test Configuration (OK)

`pyproject.toml` correctly configures pytest with `asyncio_mode = "auto"` and `testpaths = ["tests"]`. Coverage target of 80% is set in the Makefile.

---

## D. Code Quality

### D1. Duplicate Code Between Modules

| Duplication | Locations | Impact |
|-------------|-----------|--------|
| Webhook signature verification | `tinaa/github/webhooks.py` AND `tinaa/api/routes/webhooks.py` | Two implementations of HMAC-SHA256 verification |
| Product slugification | `tinaa/registry/service.py` AND `tinaa/api/routes/products.py` AND `tinaa/mcp_server/tools.py` | Three different slug implementations |
| Pydantic product models | `tinaa/models/product.py` AND `tinaa/api/routes/products.py` | Conflicting `ProductResponse` schemas (UUID vs str) |

### D2. Type Safety Gaps

- `tinaa/registry/service.py` uses `Any` for session_factory, session, and stmt parameters in private helpers. The service works but provides no type checking.
- `tinaa/agents/base.py` `AgentTask.params` is typed as `dict` (bare, unparameterized).
- `tinaa/mcp_server/tools.py` tool functions use `dict` and `list[dict]` without type parameters.

### D3. Inconsistent Error Handling Patterns

- Registry service raises domain exceptions (`ProductNotFoundError`) -- correct pattern
- API routes raise `HTTPException` directly -- correct but should map from domain exceptions
- MCP tools have no error handling at all
- GitHub client raises `httpx` exceptions directly

### D4. Good Patterns Worth Noting

- SQLAlchemy model design (base mixins, MappedAsDataclass) is clean
- APM module (collector, monitor, web_vitals) has production-quality code with proper async patterns
- Alert engine has thorough condition checking with cooldown support
- Quality scorer has well-documented weighted scoring with recommendation generation
- Playbook parser supports three input formats with variable resolution

---

## E. Missing Pieces for a Runnable Application

### E1. Application Wiring / Service Container (CRITICAL)

There is no application-level code that:
1. Creates a `ProductRegistryService` instance with a real session factory
2. Creates an `Orchestrator` and registers sub-agents
3. Creates an `AlertEngine` and registers default rules + channels
4. Creates a `MetricCollector` with a storage callback
5. Creates an `EndpointMonitor` and starts monitoring
6. Wires webhook events to the orchestrator
7. Makes these instances available to API routes (via FastAPI dependency injection)

This is the single largest gap. All the components exist but nothing plugs them together.

### E2. Database Initialization (CRITICAL)

- No Alembic configuration
- No `Base.metadata.create_all()` call anywhere
- No migration files for the 11 ORM models

### E3. Application Lifecycle Hooks (IMPORTANT)

`create_app()` does not use FastAPI `lifespan` or `on_event` to:
- Initialize the database session factory
- Start the APM monitoring loop
- Register default alert rules
- Gracefully shut down monitoring tasks

### E4. Background Task Infrastructure (IMPORTANT)

- No task queue (Celery, arq, etc.) for async playbook execution
- `PlaybookExecutor.execute()` is synchronous from the caller's perspective (blocking)
- No scheduling system for cron-triggered playbooks

### E5. Redis Integration (NICE-TO-HAVE)

Redis is declared as a dependency and in docker-compose but has no Python integration. Could be used for:
- MetricCollector storage callback (buffer before DB write)
- WebSocket pub/sub for multi-worker broadcasts
- Rate limiting in API middleware

---

## F. Affected Files -- Grouped by Priority

### CRITICAL (Required to make the app functional)

| File | Change Needed |
|------|--------------|
| `tinaa/mcp_server/server.py` | Add `def main()` entry point |
| `tinaa/api/app.py` | Add `def main()` entry point; add lifespan hooks for service initialization |
| `tinaa/registry/service.py` | Fix `result.first()` -> `result.scalars().first()` and `result.all()` -> `result.scalars().all()` |
| `tinaa/api/routes/products.py` | Replace stub data with `ProductRegistryService` calls; remove duplicate Pydantic models |
| `tinaa/api/routes/playbooks.py` | Replace stub data with `PlaybookParser`/`PlaybookExecutor` calls |
| `tinaa/api/routes/test_runs.py` | Replace stub data with agent/orchestrator calls |
| `tinaa/api/routes/metrics.py` | Replace stub data with `MetricCollector`/`BaselineManager` calls |
| `tinaa/api/routes/quality.py` | Replace stub data with `QualityScorer`/`QualityGate` calls |
| `tinaa/api/routes/webhooks.py` | Replace inline handlers; delegate to `TINAAGitHubApp` + `Orchestrator` |
| `tinaa/mcp_server/tools.py` | Replace all mock returns with real service calls |
| `tinaa/mcp_server/resources.py` | Replace hardcoded text with real service calls |
| NEW: `tinaa/app_wiring.py` or `tinaa/dependencies.py` | Service container / FastAPI dependency injection for all services |
| NEW: `alembic.ini` | Alembic configuration |
| NEW: `alembic/env.py` | Migration environment |
| NEW: `alembic/versions/001_initial.py` | Initial migration for all 11 models |

### IMPORTANT (Required for production readiness)

| File | Change Needed |
|------|--------------|
| `tinaa/database/session.py` | Remove eager module-level engine creation; use lazy init or dependency injection |
| `tinaa/agents/base.py` | Replace `datetime.utcnow()` with `datetime.now(timezone.utc)` |
| `ruff.toml` | Align target-version to py311; remove dangerous ignores (F821, F841, E722); reconcile with pyproject.toml or delete one |
| `tinaa/agents/orchestrator.py` | Wire `init_monitoring` to real `EndpointMonitor`; connect to alert engine |
| `tinaa/github/app.py` | Wire event handlers to `Orchestrator.handle_event()` |
| `tinaa/apm/collector.py` | Add database storage callback implementation |
| `tinaa/api/app.py` | Add FastAPI lifespan handler for startup/shutdown |
| `tinaa/api/middleware.py` | Fix `TINAA_API_KEYS` env var vs `TINAA_API_KEY` inconsistency with .env.example |
| `Dockerfile` | Verify that production stage actually uses the installed package, not raw source copy |

### NICE-TO-HAVE (Improvements, not blockers)

| File | Change Needed |
|------|--------------|
| `tinaa/api/routes/products.py` | Add proper Pydantic request/response models using canonical models |
| `tinaa/quality/scorer.py` | Replace `assert` with proper ValueError in __init__ |
| `tinaa/config/parser.py` | Add integration with app startup to auto-configure from .tinaa.yml |
| NEW: Redis integration module | Connect Redis for caching/pub-sub |
| `tinaa/api/websocket.py` | Connect WebSocket broadcasts to actual events (test progress, alerts) |
| `tinaa/playbooks/executor.py` | Add web vitals collection using `tinaa.apm.web_vitals.WebVitalsCollector` injection script (currently checks `window.__tinaa_web_vitals__` but never injects the script that populates it) |
| All agent files | Wire sub-agents to real services (explorer to GitHub client, test_runner to PlaybookExecutor, etc.) |

---

## Summary

The 12 teams each built well-designed, well-tested modules in isolation. The code quality within each module is generally high. The fundamental problem is that **no integration layer exists**. The application is a collection of independent libraries that share a package namespace but do not communicate at runtime.

The highest-priority work is:

1. **Fix the two broken entry points** (`main()` functions) -- 30 minutes
2. **Fix the `result.first()` / `result.all()` bug** in registry service -- 10 minutes
3. **Create Alembic configuration** and initial migration -- 1 hour
4. **Build the service wiring layer** (dependency injection, lifespan hooks) -- 4-6 hours
5. **Replace stub data in API routes** with real service calls -- 4-6 hours
6. **Replace mock data in MCP tools** with real service calls -- 3-4 hours
7. **Connect GitHub webhooks to orchestrator** -- 2-3 hours
8. **Connect APM monitor to registry + alerts** -- 2-3 hours

Total estimated integration effort: **3-4 developer-days** of focused work.
