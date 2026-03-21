"""Quality Score Engine for TINAA MSP.

Computes a composite 0-100 quality score per product, fusing testing
and APM data across four weighted components:

    Test Health       40%
    Performance       30%
    Security Posture  15%
    Accessibility     15%
"""

from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# Grade thresholds (inclusive lower bound)
GRADE_THRESHOLDS: list[tuple[float, str]] = [
    (95.0, "A+"),
    (85.0, "A"),
    (70.0, "B"),
    (55.0, "C"),
    (40.0, "D"),
    (0.0, "F"),
]

# Recommendation trigger: components below this score get recommendations
RECOMMENDATION_THRESHOLD = 80.0

# TLS grade point values
TLS_GRADE_SCORES: dict[str, float] = {
    "A+": 100.0,
    "A": 90.0,
    "B": 70.0,
    "C": 50.0,
    "D": 30.0,
    "F": 0.0,
}

# Mixed-content penalty per occurrence (for security scoring)
MIXED_CONTENT_PENALTY_PER_ITEM = 10.0

# Insecure form penalty per occurrence (for security scoring)
INSECURE_FORM_PENALTY_PER_ITEM = 15.0

# Accessibility violation penalties
CRITICAL_VIOLATION_PENALTY = 25.0
SERIOUS_VIOLATION_PENALTY = 15.0
MODERATE_VIOLATION_PENALTY = 8.0


# ---------------------------------------------------------------------------
# Data classes — inputs
# ---------------------------------------------------------------------------


@dataclass
class QualityWeights:
    """Configurable weights for quality score components."""

    test_health: float = 0.40
    performance_health: float = 0.30
    security_posture: float = 0.15
    accessibility: float = 0.15

    def validate(self) -> bool:
        """Ensure weights sum to 1.0 within floating-point tolerance."""
        total = (
            self.test_health + self.performance_health + self.security_posture + self.accessibility
        )
        return abs(total - 1.0) < 0.001


@dataclass
class TestHealthInput:
    """Input data for test health scoring."""

    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    skipped_tests: int = 0
    total_journeys_discovered: int = 0
    journeys_with_tests: int = 0
    avg_test_age_days: float = 0
    max_acceptable_age_days: float = 30
    regressions_detected: int = 0
    regressions_resolved: int = 0


@dataclass
class PerformanceHealthInput:
    """Input data for performance health scoring."""

    endpoints_total: int = 0
    endpoints_within_budget: int = 0
    avg_lcp_ms: float | None = None
    lcp_budget_ms: float = 2500
    avg_cls: float | None = None
    cls_budget: float = 0.1
    avg_fcp_ms: float | None = None
    fcp_budget_ms: float = 1800
    availability_percent: float = 100.0
    availability_target: float = 99.9
    error_rate_percent: float = 0.0
    error_rate_target: float = 1.0
    avg_response_time_ms: float | None = None
    response_time_budget_ms: float = 500


@dataclass
class SecurityPostureInput:
    """Input data for security posture scoring."""

    has_https: bool = True
    has_csp: bool = False
    has_x_frame_options: bool = False
    has_x_content_type_options: bool = False
    has_strict_transport_security: bool = False
    has_referrer_policy: bool = False
    has_permissions_policy: bool = False
    tls_grade: str = "A"
    mixed_content_count: int = 0
    insecure_form_count: int = 0
    cookie_security_score: float = 100.0


@dataclass
class AccessibilityInput:
    """Input data for accessibility scoring."""

    critical_violations: int = 0
    serious_violations: int = 0
    moderate_violations: int = 0
    minor_violations: int = 0
    total_elements_checked: int = 0
    images_without_alt: int = 0
    total_images: int = 0
    inputs_without_labels: int = 0
    total_inputs: int = 0
    color_contrast_issues: int = 0
    keyboard_navigable: bool = True


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _clamp(value: float, lo: float = 0.0, hi: float = 100.0) -> float:
    """Clamp *value* to [lo, hi]."""
    return max(lo, min(hi, value))


def _linear_score(actual: float, budget: float) -> float:
    """Return 0-100 score: 100 when actual is at or below budget, linearly
    degrading to 0 at 2x the budget (lower actual is better).

    Examples:
        actual=0,   budget=2500 -> 100
        actual=2500, budget=2500 -> 100
        actual=3750, budget=2500 -> 50
        actual=5000, budget=2500 -> 0
    """
    if actual <= budget:
        return 100.0
    if budget == 0:
        return 0.0
    return _clamp(100.0 * (1.0 - (actual - budget) / budget))


def _score_to_grade(score: float) -> str:
    """Map a 0-100 score to a letter grade."""
    for threshold, grade in GRADE_THRESHOLDS:
        if score >= threshold:
            return grade
    return "F"


# ---------------------------------------------------------------------------
# Performance sub-scorers (module-level for reuse and testability)
# ---------------------------------------------------------------------------


def _endpoint_budget_score(data: PerformanceHealthInput) -> float:
    """Return 0-100 score for endpoint response-time budget compliance."""
    if data.endpoints_total > 0:
        return data.endpoints_within_budget / data.endpoints_total * 100.0
    return 100.0


def _web_vitals_score(data: PerformanceHealthInput) -> float:
    """Return 0-100 average score for available Web Vitals metrics."""
    vital_scores: list[float] = []
    if data.avg_lcp_ms is not None:
        vital_scores.append(_linear_score(data.avg_lcp_ms, data.lcp_budget_ms))
    if data.avg_cls is not None:
        vital_scores.append(_linear_score(data.avg_cls, data.cls_budget))
    if data.avg_fcp_ms is not None:
        vital_scores.append(_linear_score(data.avg_fcp_ms, data.fcp_budget_ms))
    if data.avg_response_time_ms is not None:
        vital_scores.append(_linear_score(data.avg_response_time_ms, data.response_time_budget_ms))
    return sum(vital_scores) / len(vital_scores) if vital_scores else 100.0


def _availability_score(data: PerformanceHealthInput) -> float:
    """Return 0-100 score for service availability vs. target."""
    if data.availability_percent >= data.availability_target:
        return 100.0
    if data.availability_target > 0:
        return _clamp((data.availability_percent / data.availability_target) * 100.0)
    return 100.0


def _error_rate_score(data: PerformanceHealthInput) -> float:
    """Return 0-100 score for error rate vs. target (lower rate is better)."""
    if data.error_rate_percent <= data.error_rate_target:
        return 100.0
    if data.error_rate_target > 0:
        return _clamp((data.error_rate_target / data.error_rate_percent) * 100.0)
    return 0.0


# ---------------------------------------------------------------------------
# Scorer
# ---------------------------------------------------------------------------


class QualityScorer:
    """Computes the composite quality score for a product."""

    def __init__(self, weights: QualityWeights | None = None) -> None:
        self.weights = weights or QualityWeights()
        assert self.weights.validate(), "Weights must sum to 1.0"

    # ------------------------------------------------------------------
    # Component scorers
    # ------------------------------------------------------------------

    def score_test_health(self, data: TestHealthInput) -> float:
        """Score test health from 0-100.

        Sub-components and their weights within test health:
            Pass rate          40%
            Coverage breadth   30%
            Test freshness     20%
            Regression mgmt    10%
        """
        # Pass rate (40%)
        pass_rate = data.passed_tests / data.total_tests * 100.0 if data.total_tests > 0 else 0.0

        # Coverage breadth (30%)
        if data.total_journeys_discovered > 0:
            coverage = data.journeys_with_tests / data.total_journeys_discovered * 100.0
        else:
            coverage = 100.0  # no journeys discovered yet — no penalty

        # Test freshness (20%)
        if data.max_acceptable_age_days > 0:
            freshness = _clamp(
                100.0 - (data.avg_test_age_days / data.max_acceptable_age_days * 100.0)
            )
        else:
            freshness = 100.0

        # Regression management (10%)
        if data.regressions_detected > 0:
            regression_score = data.regressions_resolved / data.regressions_detected * 100.0
        else:
            regression_score = 100.0

        score = pass_rate * 0.40 + coverage * 0.30 + freshness * 0.20 + regression_score * 0.10
        return _clamp(score)

    def score_performance_health(self, data: PerformanceHealthInput) -> float:
        """Score performance health from 0-100.

        Sub-components:
            Endpoint budget compliance  30%
            Web Vitals (LCP+CLS+FCP)   30%
            Availability               25%
            Error rate                 15%
        """
        budget_compliance = _endpoint_budget_score(data)
        web_vitals = _web_vitals_score(data)
        availability_score = _availability_score(data)
        error_score = _error_rate_score(data)

        score = (
            budget_compliance * 0.30
            + web_vitals * 0.30
            + availability_score * 0.25
            + error_score * 0.15
        )
        return _clamp(score)

    def score_security_posture(self, data: SecurityPostureInput) -> float:
        """Score security posture from 0-100.

        Sub-components:
            HTTPS              20%
            Security headers   30%
            TLS grade          20%
            Mixed content      15%
            Cookie/form sec    15%
        """
        # HTTPS (20%)
        https_score = 100.0 if data.has_https else 0.0

        # Security headers (30%) — 6 headers
        headers_present = sum(
            [
                data.has_csp,
                data.has_x_frame_options,
                data.has_x_content_type_options,
                data.has_strict_transport_security,
                data.has_referrer_policy,
                data.has_permissions_policy,
            ]
        )
        headers_score = headers_present / 6.0 * 100.0

        # TLS grade (20%)
        tls_score = TLS_GRADE_SCORES.get(data.tls_grade, 0.0)

        # Mixed content (15%)
        mixed_score = _clamp(100.0 - data.mixed_content_count * MIXED_CONTENT_PENALTY_PER_ITEM)

        # Cookie/form security (15%)
        insecure_form_penalty = _clamp(data.insecure_form_count * INSECURE_FORM_PENALTY_PER_ITEM)
        cookie_form_score = _clamp(
            (data.cookie_security_score + (100.0 - insecure_form_penalty)) / 2.0
        )

        score = (
            https_score * 0.20
            + headers_score * 0.30
            + tls_score * 0.20
            + mixed_score * 0.15
            + cookie_form_score * 0.15
        )
        return _clamp(score)

    def score_accessibility(self, data: AccessibilityInput) -> float:
        """Score accessibility from 0-100.

        Sub-components:
            Critical violations  30%
            Serious violations   25%
            Moderate violations  20%
            Alt text coverage    15%
            Keyboard navigable   10%
        """
        # Critical violations (30%)
        critical_score = _clamp(100.0 - data.critical_violations * CRITICAL_VIOLATION_PENALTY)

        # Serious violations (25%)
        serious_score = _clamp(100.0 - data.serious_violations * SERIOUS_VIOLATION_PENALTY)

        # Moderate violations (20%)
        moderate_score = _clamp(100.0 - data.moderate_violations * MODERATE_VIOLATION_PENALTY)

        # Alt text coverage (15%)
        if data.total_images > 0:
            alt_score = (data.total_images - data.images_without_alt) / data.total_images * 100.0
        else:
            alt_score = 100.0

        # Keyboard navigable (10%)
        keyboard_score = 100.0 if data.keyboard_navigable else 0.0

        score = (
            critical_score * 0.30
            + serious_score * 0.25
            + moderate_score * 0.20
            + alt_score * 0.15
            + keyboard_score * 0.10
        )
        return _clamp(score)

    # ------------------------------------------------------------------
    # Composite scorer
    # ------------------------------------------------------------------

    def compute_quality_score(
        self,
        test_health: TestHealthInput,
        performance: PerformanceHealthInput,
        security: SecurityPostureInput,
        accessibility: AccessibilityInput,
    ) -> dict:
        """Compute the overall quality score.

        Returns a dict with keys: score, grade, components, recommendations.
        """
        component_scores = (
            self.score_test_health(test_health),
            self.score_performance_health(performance),
            self.score_security_posture(security),
            self.score_accessibility(accessibility),
        )
        components = self._build_components_dict(*component_scores)
        overall = _clamp(sum(c["weighted_score"] for c in components.values()))
        return {
            "score": overall,
            "grade": _score_to_grade(overall),
            "components": components,
            "recommendations": self._generate_recommendations(
                components, test_health, performance, security, accessibility
            ),
        }

    def _build_components_dict(
        self,
        th_score: float,
        ph_score: float,
        sp_score: float,
        a11y_score: float,
    ) -> dict:
        """Build the components breakdown dict from individual component scores."""
        w = self.weights
        return {
            "test_health": {
                "score": th_score,
                "weight": w.test_health,
                "weighted_score": th_score * w.test_health,
            },
            "performance_health": {
                "score": ph_score,
                "weight": w.performance_health,
                "weighted_score": ph_score * w.performance_health,
            },
            "security_posture": {
                "score": sp_score,
                "weight": w.security_posture,
                "weighted_score": sp_score * w.security_posture,
            },
            "accessibility": {
                "score": a11y_score,
                "weight": w.accessibility,
                "weighted_score": a11y_score * w.accessibility,
            },
        }

    # ------------------------------------------------------------------
    # Recommendation generation
    # ------------------------------------------------------------------

    def _generate_recommendations(
        self,
        components: dict,
        test_health: TestHealthInput,
        performance: PerformanceHealthInput,
        security: SecurityPostureInput,
        accessibility: AccessibilityInput,
    ) -> list[str]:
        """Generate actionable recommendations for low-scoring components."""
        recs: list[str] = []

        if components["test_health"]["score"] < RECOMMENDATION_THRESHOLD:
            recs.extend(self._test_health_recommendations(test_health))
        if components["performance_health"]["score"] < RECOMMENDATION_THRESHOLD:
            recs.extend(self._performance_recommendations(performance))
        if components["security_posture"]["score"] < RECOMMENDATION_THRESHOLD:
            recs.extend(self._security_recommendations(security))
        if components["accessibility"]["score"] < RECOMMENDATION_THRESHOLD:
            recs.extend(self._accessibility_recommendations(accessibility))

        return recs

    @staticmethod
    def _test_health_recommendations(data: TestHealthInput) -> list[str]:
        """Return recommendations for a low test-health score."""
        recs: list[str] = []
        if data.total_tests == 0:
            recs.append(
                "Add automated tests: no tests detected. Start with critical user journeys."
            )
        elif data.passed_tests < data.total_tests:
            fail_count = data.total_tests - data.passed_tests
            recs.append(f"Fix {fail_count} failing test(s) to restore test suite stability.")
        if (
            data.total_journeys_discovered > 0
            and data.journeys_with_tests < data.total_journeys_discovered
        ):
            uncovered = data.total_journeys_discovered - data.journeys_with_tests
            recs.append(
                f"Add tests for {uncovered} uncovered user journey(s) to improve coverage breadth."
            )
        if data.avg_test_age_days > data.max_acceptable_age_days:
            recs.append(
                f"Update stale tests: average age {data.avg_test_age_days:.0f}d exceeds "
                f"the {data.max_acceptable_age_days:.0f}d freshness threshold."
            )
        if data.regressions_detected > data.regressions_resolved:
            unresolved = data.regressions_detected - data.regressions_resolved
            recs.append(
                f"Resolve {unresolved} unresolved regression(s) to stabilise the test suite."
            )
        return recs

    @staticmethod
    def _performance_recommendations(data: PerformanceHealthInput) -> list[str]:
        """Return recommendations for a low performance-health score."""
        recs: list[str] = []
        if data.endpoints_total > 0:
            over_budget = data.endpoints_total - data.endpoints_within_budget
            if over_budget > 0:
                recs.append(f"Optimise {over_budget} endpoint(s) exceeding response-time budget.")
        if data.avg_lcp_ms is not None and data.avg_lcp_ms > data.lcp_budget_ms:
            recs.append(
                f"Improve LCP: current {data.avg_lcp_ms:.0f}ms exceeds "
                f"{data.lcp_budget_ms:.0f}ms budget. Optimise largest content element."
            )
        if data.avg_cls is not None and data.avg_cls > data.cls_budget:
            recs.append(
                f"Reduce layout shift (CLS {data.avg_cls:.3f} > budget {data.cls_budget}). "
                "Set explicit dimensions on images and embeds."
            )
        if data.availability_percent < data.availability_target:
            recs.append(
                f"Availability {data.availability_percent:.2f}% is below "
                f"{data.availability_target}% target. Investigate reliability issues."
            )
        if data.error_rate_percent > data.error_rate_target:
            recs.append(
                f"Error rate {data.error_rate_percent:.1f}% exceeds "
                f"{data.error_rate_target}% target. Review error logs and add monitoring."
            )
        return recs

    @staticmethod
    def _security_recommendations(data: SecurityPostureInput) -> list[str]:
        """Return recommendations for a low security-posture score."""
        recs: list[str] = []
        if not data.has_https:
            recs.append("Enable HTTPS immediately: all traffic must use TLS to protect user data.")
        missing_headers = [
            header
            for flag, header in [
                (data.has_csp, "Content-Security-Policy"),
                (data.has_x_frame_options, "X-Frame-Options"),
                (data.has_x_content_type_options, "X-Content-Type-Options"),
                (data.has_strict_transport_security, "Strict-Transport-Security"),
                (data.has_referrer_policy, "Referrer-Policy"),
                (data.has_permissions_policy, "Permissions-Policy"),
            ]
            if not flag
        ]
        if missing_headers:
            recs.append(f"Add missing security headers: {', '.join(missing_headers)}.")
        if data.tls_grade not in ("A+", "A"):
            recs.append(f"Upgrade TLS configuration from grade {data.tls_grade} to A or A+.")
        if data.mixed_content_count > 0:
            recs.append(
                f"Fix {data.mixed_content_count} mixed-content resource(s) to prevent "
                "browser security warnings."
            )
        if data.insecure_form_count > 0:
            recs.append(f"Secure {data.insecure_form_count} form(s) submitting over HTTP.")
        return recs

    @staticmethod
    def _accessibility_recommendations(data: AccessibilityInput) -> list[str]:
        """Return recommendations for a low accessibility score."""
        recs: list[str] = []
        if data.critical_violations > 0:
            recs.append(
                f"Fix {data.critical_violations} critical accessibility violation(s) "
                "immediately — these block users with disabilities."
            )
        if data.serious_violations > 0:
            recs.append(f"Address {data.serious_violations} serious accessibility violation(s).")
        if data.images_without_alt > 0:
            recs.append(
                f"Add alt text to {data.images_without_alt} image(s) for screen reader support."
            )
        if not data.keyboard_navigable:
            recs.append(
                "Ensure all interactive elements are keyboard-navigable (Tab/Enter/Escape)."
            )
        return recs
