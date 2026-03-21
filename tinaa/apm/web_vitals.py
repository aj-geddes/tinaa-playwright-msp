"""
Web Vitals collection for TINAA APM.

Provides JavaScript injection scripts for collecting Core Web Vitals via
PerformanceObserver, extraction utilities, and threshold-based evaluation
against Google's thresholds.
"""

from __future__ import annotations

import asyncio
import json
import logging

logger = logging.getLogger(__name__)

# Google Web Vitals thresholds (milliseconds / score)
_LCP_GOOD = 2500.0
_LCP_POOR = 4000.0

_FCP_GOOD = 1800.0
_FCP_POOR = 3000.0

_CLS_GOOD = 0.1
_CLS_POOR = 0.25

_INP_GOOD = 200.0
_INP_POOR = 500.0

# Extra wait after page load to allow LCP to stabilise
_LCP_STABILISE_SECONDS = 3.0

_RATING_GOOD = "good"
_RATING_NEEDS_IMPROVEMENT = "needs-improvement"
_RATING_POOR = "poor"


class WebVitalsCollector:
    """Collects Core Web Vitals from a Playwright page."""

    @staticmethod
    def get_injection_script() -> str:
        """Return the JavaScript snippet that installs PerformanceObservers.

        Metrics stored on ``window.__TINAA_WEB_VITALS__``:
        - lcp_ms: Largest Contentful Paint (ms)
        - fcp_ms: First Contentful Paint (ms)
        - cls: Cumulative Layout Shift score (unitless)
        - inp_ms: Interaction to Next Paint approximation (ms) or null
        - ttfb_ms: Time to First Byte from navigation timing (ms)
        """
        return r"""
(function() {
  if (window.__TINAA_WEB_VITALS__) return;

  var vitals = {
    lcp_ms: null,
    fcp_ms: null,
    cls: 0,
    inp_ms: null,
    ttfb_ms: null
  };
  window.__TINAA_WEB_VITALS__ = vitals;

  // ---- TTFB via Navigation Timing ----------------------------------------
  try {
    var navEntries = performance.getEntriesByType('navigation');
    if (navEntries.length > 0) {
      vitals.ttfb_ms = navEntries[0].responseStart - navEntries[0].requestStart;
    }
  } catch (e) {}

  // ---- LCP ----------------------------------------------------------------
  try {
    var lcpObserver = new PerformanceObserver(function(list) {
      var entries = list.getEntries();
      if (entries.length > 0) {
        vitals.lcp_ms = entries[entries.length - 1].startTime;
      }
    });
    lcpObserver.observe({ type: 'largest-contentful-paint', buffered: true });
  } catch (e) {}

  // ---- FCP ----------------------------------------------------------------
  try {
    var fcpObserver = new PerformanceObserver(function(list) {
      var entries = list.getEntries();
      for (var i = 0; i < entries.length; i++) {
        if (entries[i].name === 'first-contentful-paint') {
          vitals.fcp_ms = entries[i].startTime;
          break;
        }
      }
    });
    fcpObserver.observe({ type: 'paint', buffered: true });
  } catch (e) {}

  // ---- CLS ----------------------------------------------------------------
  // Accumulate layout-shift entries that were NOT triggered by user input
  try {
    var clsObserver = new PerformanceObserver(function(list) {
      var entries = list.getEntries();
      for (var i = 0; i < entries.length; i++) {
        var entry = entries[i];
        if (!entry.hadRecentInput) {
          vitals.cls += entry.value;
        }
      }
    });
    clsObserver.observe({ type: 'layout-shift', buffered: true });
  } catch (e) {}

  // ---- INP (approximated via event timing) --------------------------------
  try {
    var inpObserver = new PerformanceObserver(function(list) {
      var entries = list.getEntries();
      for (var i = 0; i < entries.length; i++) {
        var duration = entries[i].duration;
        if (vitals.inp_ms === null || duration > vitals.inp_ms) {
          vitals.inp_ms = duration;
        }
      }
    });
    inpObserver.observe({ type: 'event', buffered: true, durationThreshold: 16 });
  } catch (e) {}
})();
"""

    @staticmethod
    def get_extraction_script() -> str:
        """Return JavaScript that serialises ``window.__TINAA_WEB_VITALS__`` to JSON."""
        return "return JSON.stringify(window.__TINAA_WEB_VITALS__ || null);"

    @staticmethod
    async def collect_from_page(page) -> dict:
        """Collect Web Vitals from an open Playwright page.

        Steps:
        1. Inject the collection script.
        2. Wait for ``load`` state plus a stabilisation window for LCP.
        3. Extract and return the collected metrics.

        Returns:
            dict with keys: lcp_ms, fcp_ms, cls, inp_ms, ttfb_ms
        """
        await page.add_init_script(WebVitalsCollector.get_injection_script())
        await page.wait_for_load_state("load")
        await asyncio.sleep(_LCP_STABILISE_SECONDS)

        raw = await page.evaluate(WebVitalsCollector.get_extraction_script())
        if raw is None:
            return {"lcp_ms": None, "fcp_ms": None, "cls": 0.0, "inp_ms": None, "ttfb_ms": None}

        data = json.loads(raw) if isinstance(raw, str) else raw
        return {
            "lcp_ms": data.get("lcp_ms"),
            "fcp_ms": data.get("fcp_ms"),
            "cls": data.get("cls", 0.0),
            "inp_ms": data.get("inp_ms"),
            "ttfb_ms": data.get("ttfb_ms"),
        }

    @staticmethod
    def evaluate_web_vitals(vitals: dict) -> dict:
        """Rate Web Vitals values against Google's published thresholds.

        Args:
            vitals: dict with keys lcp_ms, fcp_ms, cls, inp_ms (may be None),
                    ttfb_ms (ignored in overall rating).

        Returns:
            dict with per-metric rating dicts and an ``overall_rating`` key.
            Each per-metric dict: {"value": float, "rating": str}
        """
        ratings: dict[str, dict] = {}

        lcp = vitals.get("lcp_ms")
        if lcp is not None:
            ratings["lcp"] = {"value": lcp, "rating": _rate(lcp, _LCP_GOOD, _LCP_POOR)}

        fcp = vitals.get("fcp_ms")
        if fcp is not None:
            ratings["fcp"] = {"value": fcp, "rating": _rate(fcp, _FCP_GOOD, _FCP_POOR)}

        cls = vitals.get("cls")
        if cls is not None:
            ratings["cls"] = {"value": cls, "rating": _rate(cls, _CLS_GOOD, _CLS_POOR)}

        inp = vitals.get("inp_ms")
        if inp is not None:
            ratings["inp"] = {"value": inp, "rating": _rate(inp, _INP_GOOD, _INP_POOR)}

        overall = _worst_rating([r["rating"] for r in ratings.values()])
        return {**ratings, "overall_rating": overall}


# ---------------------------------------------------------------------------
# Private helpers
# ---------------------------------------------------------------------------

_RATING_ORDER = {_RATING_GOOD: 0, _RATING_NEEDS_IMPROVEMENT: 1, _RATING_POOR: 2}


def _rate(value: float, good_threshold: float, poor_threshold: float) -> str:
    """Map a metric value to a Google Web Vitals rating string."""
    if value < good_threshold:
        return _RATING_GOOD
    if value < poor_threshold:
        return _RATING_NEEDS_IMPROVEMENT
    return _RATING_POOR


def _worst_rating(ratings: list[str]) -> str:
    """Return the worst (most severe) rating from a collection."""
    if not ratings:
        return _RATING_GOOD
    return max(ratings, key=lambda r: _RATING_ORDER.get(r, 0))
