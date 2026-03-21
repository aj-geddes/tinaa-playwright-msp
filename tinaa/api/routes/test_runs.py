"""Test run routes — trigger, list, retrieve, and cancel test executions."""

import contextlib
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter

from tinaa.services import get_services

router = APIRouter()


@router.get(
    "/products/{product_id}/runs",
    summary="List test runs",
    description="List test runs for a product with optional status filter.",
)
async def list_test_runs(
    product_id: str,
    limit: int = 20,
    status: str | None = None,
) -> list[dict]:
    """Return test runs for a product.

    Real test run data comes from the TestRun table; until that query path
    is connected the route returns representative stub data.
    """
    # TODO: wire to real service when DB is available
    _ = get_services()  # ensure container is accessible
    run_status = status or "passed"
    return [
        {
            "run_id": f"run-{i:03d}",
            "product_id": product_id,
            "status": run_status,
            "suite_type": "regression",
            "started_at": datetime.now(UTC).isoformat(),
            "duration_seconds": 45 + i,
        }
        for i in range(min(limit, 3))
    ]


@router.get(
    "/runs/{run_id}",
    summary="Get test run",
    description="Retrieve details for a specific test run.",
)
async def get_test_run(run_id: str) -> dict:
    """Return a test run by ID.

    Real data comes from the TestRun table; stub data returned until wired.
    """
    # TODO: wire to real service when DB is available
    _ = get_services()
    return {
        "run_id": run_id,
        "status": "passed",
        "suite_type": "regression",
        "total_tests": 42,
        "passed": 40,
        "failed": 2,
        "skipped": 0,
        "started_at": datetime.now(UTC).isoformat(),
        "duration_seconds": 120,
    }


@router.get(
    "/runs/{run_id}/results",
    summary="Get test results",
    description="Return individual test case results for a run.",
)
async def get_test_results(run_id: str) -> list[dict]:
    """Return test case results for a run."""
    return [
        {
            "test_id": f"{run_id}-tc-{i}",
            "name": f"Test case {i}",
            "status": "passed" if i % 5 != 0 else "failed",
            "duration_ms": 200 + i * 10,
            "error": None if i % 5 != 0 else "AssertionError: expected 200, got 500",
        }
        for i in range(5)
    ]


@router.post(
    "/products/{product_id}/runs",
    summary="Trigger test run",
    description="Queue a new test run for a product.",
)
async def trigger_test_run(
    product_id: str,
    suite_type: str = "regression",
    environment: str | None = None,
) -> dict:
    """Queue a new test run via the orchestrator.

    Real execution is dispatched through the Orchestrator to the test_runner
    agent; for now returns a queued status immediately.
    """
    services = get_services()
    with contextlib.suppress(Exception):
        await services.orchestrator.handle_event(
            "deployment_detected",
            {
                "product_id": product_id,
                "deployment_url": "",
            },
        )

    return {
        "run_id": f"run-{uuid.uuid4().hex[:8]}",
        "product_id": product_id,
        "suite_type": suite_type,
        "environment": environment,
        "status": "queued",
        "queued_at": datetime.now(UTC).isoformat(),
    }


@router.post(
    "/runs/{run_id}/cancel",
    summary="Cancel test run",
    description="Request cancellation of an in-progress test run.",
)
async def cancel_test_run(run_id: str) -> dict:
    """Mark a run as cancelled."""
    return {
        "run_id": run_id,
        "status": "cancelled",
        "cancelled_at": datetime.now(UTC).isoformat(),
    }
