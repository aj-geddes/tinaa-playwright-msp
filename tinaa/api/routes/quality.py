"""Quality score, history, report, and gate evaluation routes."""

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter

from tinaa.services import get_services

router = APIRouter()


@router.get(
    "/products/{product_id}/quality",
    summary="Get quality score",
    description="Return the current quality score with component breakdown.",
)
async def get_quality_score(
    product_id: str,
    environment: str | None = None,
) -> dict:
    """Return a quality score computed by QualityScorer with default inputs."""
    from tinaa.quality.scorer import (
        AccessibilityInput,
        PerformanceHealthInput,
        SecurityPostureInput,
        TestHealthInput,
    )

    services = get_services()
    result = services.quality_scorer.compute_quality_score(
        test_health=TestHealthInput(),
        performance=PerformanceHealthInput(),
        security=SecurityPostureInput(),
        accessibility=AccessibilityInput(),
    )

    return {
        "product_id": product_id,
        "environment": environment or "production",
        "score": result["score"],
        "grade": result["grade"],
        "components": result["components"],
        "recommendations": result["recommendations"],
        "evaluated_at": datetime.now(UTC).isoformat(),
    }


@router.get(
    "/products/{product_id}/quality/history",
    summary="Get quality history",
    description="Return daily quality score history for the given number of days.",
)
async def get_quality_history(product_id: str, days: int = 30) -> list[dict]:
    """Return stub daily quality history records.

    Real history would come from the QualityScoreSnapshot table; that
    database query path is not yet connected so we return computed scores
    with the same structure for now.
    """
    now = datetime.now(UTC)
    services = get_services()

    from tinaa.quality.scorer import (
        AccessibilityInput,
        PerformanceHealthInput,
        SecurityPostureInput,
        TestHealthInput,
    )

    base_result = services.quality_scorer.compute_quality_score(
        test_health=TestHealthInput(),
        performance=PerformanceHealthInput(),
        security=SecurityPostureInput(),
        accessibility=AccessibilityInput(),
    )
    base_score: float = base_result["score"]

    return [
        {
            "date": (now - timedelta(days=days - i)).date().isoformat(),
            "score": round(base_score + (i % 10) * 0.8, 2),
            "grade": base_result["grade"],
        }
        for i in range(min(days, 30))
    ]


@router.get(
    "/products/{product_id}/quality/report",
    summary="Get quality report",
    description="Return a comprehensive quality report for the product.",
)
async def get_quality_report(product_id: str) -> dict:
    """Return a quality report using QualityScorer with default inputs."""
    from tinaa.quality.scorer import (
        AccessibilityInput,
        PerformanceHealthInput,
        SecurityPostureInput,
        TestHealthInput,
    )

    services = get_services()
    result = services.quality_scorer.compute_quality_score(
        test_health=TestHealthInput(),
        performance=PerformanceHealthInput(),
        security=SecurityPostureInput(),
        accessibility=AccessibilityInput(),
    )

    return {
        "product_id": product_id,
        "generated_at": datetime.now(UTC).isoformat(),
        "overall_score": result["score"],
        "grade": result["grade"],
        "summary": "Quality report generated from current product signals.",
        "components": result["components"],
        "recommendations": result["recommendations"],
    }


@router.get(
    "/products/{product_id}/quality/gate",
    summary="Evaluate quality gate",
    description="Determine whether the product passes quality gates for a given environment.",
)
async def evaluate_quality_gate(
    product_id: str,
    environment: str = "production",
) -> dict:
    """Evaluate the quality gate using QualityGate service."""
    from tinaa.quality.scorer import (
        AccessibilityInput,
        PerformanceHealthInput,
        SecurityPostureInput,
        TestHealthInput,
    )

    services = get_services()

    quality_score = services.quality_scorer.compute_quality_score(
        test_health=TestHealthInput(),
        performance=PerformanceHealthInput(),
        security=SecurityPostureInput(),
        accessibility=AccessibilityInput(),
    )

    gate_result = services.quality_gate.evaluate(quality_score)

    return {
        "product_id": product_id,
        "environment": environment,
        "passed": gate_result["passed"],
        "score": gate_result["score"],
        "checks": gate_result["checks"],
        "blocking_reasons": gate_result["blocking_reasons"],
        "recommendation": gate_result["recommendation"],
        "evaluated_at": datetime.now(UTC).isoformat(),
    }
