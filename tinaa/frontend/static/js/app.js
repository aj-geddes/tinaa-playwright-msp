/**
 * app.js — TINAA MSP Single-Page Application entry point.
 *
 * Responsibilities:
 * - Import all Web Components (registers them with customElements.define)
 * - Set up the hash-based router
 * - Map routes to page render functions
 * - Handle 404 / unknown routes
 * - Provide global app state helpers
 */

// ---------------------------------------------------------------- Components
// Each import registers the custom element as a side effect.
import "./components/nav.js";
import "./components/header.js";
import "./components/quality-score.js";
import "./components/metric-card.js";
import "./components/product-card.js";
import "./components/alert-banner.js";
import "./components/playbook-list.js";
import "./components/test-run-table.js";
import "./components/endpoint-status.js";
import "./components/docs-viewer.js";

// ------------------------------------------------------------------- Pages
import { renderDashboard }     from "./pages/dashboard.js";
import { renderProducts }      from "./pages/products.js";
import { renderProductDetail } from "./pages/product-detail.js";
import { renderPlaybooks }     from "./pages/playbooks.js";
import { renderMetrics }       from "./pages/metrics.js";
import { renderTestRuns }      from "./pages/test-runs.js";
import { renderAlerts }        from "./pages/alerts.js";
import { renderSettings }      from "./pages/settings.js";
import { renderDocs }          from "./pages/docs.js";
import { renderIntegrations }  from "./pages/integrations.js";

// -------------------------------------------------------------------- Router

/**
 * Minimal hash-based router.
 *
 * Routes are registered as pattern strings:
 *   "/"               — exact match
 *   "/products/:id"   — match /products/<anything>; id available in params
 *
 * The handler signature is: async (container, params) => void
 */
class Router {
  constructor() {
    /** @type {Array<{pattern: RegExp, keys: string[], handler: Function}>} */
    this._routes = [];
    this._notFoundHandler = null;
  }

  /**
   * Register a route.
   * @param {string} path    - Route pattern (supports :param segments)
   * @param {Function} handler - async (container, params) => void
   */
  register(path, handler) {
    // Convert /:param segments to named capture groups
    const keys = [];
    const regexStr = path
      .replace(/:([^/]+)/g, (_, key) => {
        keys.push(key);
        return "([^/]+)";
      })
      .replace(/\//g, "\\/");
    this._routes.push({
      pattern: new RegExp(`^${regexStr}$`),
      keys,
      handler,
    });
  }

  /**
   * Register a 404 handler.
   * @param {Function} handler
   */
  notFound(handler) {
    this._notFoundHandler = handler;
  }

  /**
   * Navigate to a hash path.
   * @param {string} path - e.g. "/products/abc-123"
   */
  navigate(path) {
    window.location.hash = path;
  }

  /** Start the router — binds to hashchange and renders current route. */
  start() {
    window.addEventListener("hashchange", () => this._render());
    this._render();
  }

  _render() {
    const hash = window.location.hash.slice(1) || "/";
    const container = document.getElementById("main-content");
    if (!container) return;

    // Clear previous content
    container.innerHTML = "";

    // Find matching route
    for (const route of this._routes) {
      const match = hash.match(route.pattern);
      if (match) {
        const params = {};
        route.keys.forEach((key, i) => {
          params[key] = decodeURIComponent(match[i + 1] || "");
        });

        // Announce page change to screen readers
        _announceNavigation(hash);

        // Focus main content after render (for keyboard users)
        container.setAttribute("tabindex", "-1");

        Promise.resolve(route.handler(container, params)).catch((err) => {
          container.innerHTML = `
            <div class="p-6">
              <tinaa-alert-banner
                severity="critical"
                message="Page error: ${_esc(err.message)}"
              ></tinaa-alert-banner>
            </div>
          `;
          console.error("Router render error:", err);
        });
        return;
      }
    }

    // No match — 404
    if (this._notFoundHandler) {
      this._notFoundHandler(container, {});
    } else {
      container.innerHTML = `
        <div class="p-8 text-center">
          <h1 class="text-2xl font-bold text-white mb-3">Page Not Found</h1>
          <p class="text-slate-400 mb-6">The route <code>${_esc(hash)}</code> does not exist.</p>
          <a href="#/" class="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm
                             focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-400">
            Return to Dashboard
          </a>
        </div>
      `;
    }
  }
}

// -------------------------------------------------------------- App Bootstrap

function _esc(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/"/g, "&quot;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

function _announceNavigation(hash) {
  const ROUTE_NAMES = {
    "/":              "Dashboard",
    "/products":      "Products",
    "/playbooks":     "Playbooks",
    "/metrics":       "Metrics",
    "/test-runs":     "Test Runs",
    "/alerts":        "Alerts",
    "/settings":      "Settings",
    "/integrations":  "Integrations",
    "/docs":          "Documentation",
  };
  const name = ROUTE_NAMES[hash] || "Page";
  const announcer = document.getElementById("aria-announcer");
  if (announcer) {
    announcer.textContent = "";
    setTimeout(() => {
      announcer.textContent = `Navigated to ${name}`;
    }, 50);
  }
}

function init() {
  const router = new Router();

  // --------------------------------- Route registrations
  router.register("/",            (el) => renderDashboard(el));
  router.register("/products",    (el) => renderProducts(el));
  router.register("/products/:id",(el, p) => renderProductDetail(el, p.id));
  router.register("/playbooks",   (el) => renderPlaybooks(el));
  router.register("/metrics",     (el) => renderMetrics(el));
  router.register("/test-runs",   (el) => renderTestRuns(el));
  router.register("/alerts",      (el) => renderAlerts(el));
  router.register("/settings",    (el) => renderSettings(el));
  router.register("/integrations",(el) => renderIntegrations(el));
  router.register("/docs",        (el) => renderDocs(el));

  router.notFound((el) => {
    el.innerHTML = `
      <div class="p-8 text-center">
        <h1 class="text-2xl font-bold text-white mb-3">404 — Page Not Found</h1>
        <p class="text-slate-400 mb-6">This page does not exist.</p>
        <a href="#/" class="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm
                           focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-400">
          Return to Dashboard
        </a>
      </div>
    `;
  });

  router.start();

  // Expose router globally for components that need programmatic navigation
  window.__tinaaRouter = router;
}

// Run after DOM is ready
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", init);
} else {
  init();
}
