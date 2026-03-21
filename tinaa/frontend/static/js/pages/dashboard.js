/**
 * dashboard.js — Main Dashboard page.
 *
 * Renders:
 * - Summary stats bar (total products, avg quality score, endpoints, alerts)
 * - Grid of product cards
 * - Recent activity feed (last 5 test runs)
 * - Quick actions: Register Product, Run Tests, View Reports
 */

import { api } from "../api.js";

/**
 * Render the dashboard page into the given container element.
 * @param {HTMLElement} container
 */
export async function renderDashboard(container) {
  container.innerHTML = `
    <div class="space-y-6">
      <!-- Page heading -->
      <div class="flex items-center justify-between">
        <h1 class="text-2xl font-bold text-white">Dashboard</h1>
        <div class="flex items-center gap-2">
          <button
            id="btn-register-product"
            class="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700
                   text-white text-sm font-medium rounded-lg transition-colors
                   focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-400
                   focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900"
            aria-label="Register a new product"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" viewBox="0 0 24 24"
                 fill="none" stroke="currentColor" stroke-width="2"
                 aria-hidden="true" focusable="false">
              <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
            </svg>
            Register Product
          </button>
        </div>
      </div>

      <!-- Summary stats -->
      <section aria-labelledby="stats-heading">
        <h2 id="stats-heading" class="sr-only">Summary Statistics</h2>
        <div
          id="stats-grid"
          class="grid grid-cols-2 md:grid-cols-4 gap-4"
          aria-live="polite"
          aria-busy="true"
        >
          ${[
            { label: "Total Products", id: "stat-products" },
            { label: "Avg Quality Score", id: "stat-quality" },
            { label: "Endpoints Monitored", id: "stat-endpoints" },
            { label: "Active Alerts", id: "stat-alerts" },
          ].map(s => `
            <div class="bg-slate-800 rounded-lg p-4 border border-slate-700 animate-pulse">
              <div class="h-3 bg-slate-700 rounded w-2/3 mb-3"></div>
              <div class="h-7 bg-slate-700 rounded w-1/2"></div>
            </div>
          `).join("")}
        </div>
      </section>

      <!-- Quick actions -->
      <section aria-labelledby="actions-heading">
        <h2 id="actions-heading" class="text-sm font-semibold text-slate-400 uppercase tracking-wider mb-3">
          Quick Actions
        </h2>
        <div class="flex flex-wrap gap-3">
          <button
            id="btn-run-tests"
            class="inline-flex items-center gap-2 px-4 py-2 bg-slate-700 hover:bg-slate-600
                   text-slate-200 text-sm font-medium rounded-lg transition-colors
                   focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" viewBox="0 0 24 24"
                 fill="none" stroke="currentColor" stroke-width="2"
                 aria-hidden="true" focusable="false">
              <polygon points="5 3 19 12 5 21 5 3"/>
            </svg>
            Run Tests
          </button>
          <button
            id="btn-view-reports"
            class="inline-flex items-center gap-2 px-4 py-2 bg-slate-700 hover:bg-slate-600
                   text-slate-200 text-sm font-medium rounded-lg transition-colors
                   focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" viewBox="0 0 24 24"
                 fill="none" stroke="currentColor" stroke-width="2"
                 aria-hidden="true" focusable="false">
              <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
              <polyline points="14 2 14 8 20 8"/>
            </svg>
            View Reports
          </button>
        </div>
      </section>

      <!-- Products grid -->
      <section aria-labelledby="products-heading">
        <div class="flex items-center justify-between mb-4">
          <h2 id="products-heading" class="text-lg font-semibold text-white">Products</h2>
          <a href="#/products"
             class="text-sm text-blue-400 hover:text-blue-300 transition-colors
                    focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 rounded">
            View all →
          </a>
        </div>
        <div
          id="products-grid"
          class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4"
          aria-live="polite"
          aria-busy="true"
        >
          <!-- Loading skeleton cards -->
          ${[...Array(4)].map(() => `
            <div class="bg-slate-800 rounded-lg p-4 border border-slate-700 animate-pulse">
              <div class="flex gap-3 mb-3">
                <div class="w-16 h-16 bg-slate-700 rounded-full"></div>
                <div class="flex-1 space-y-2 pt-1">
                  <div class="h-4 bg-slate-700 rounded"></div>
                  <div class="h-3 bg-slate-700 rounded w-2/3"></div>
                </div>
              </div>
              <div class="h-6 bg-slate-700 rounded"></div>
            </div>
          `).join("")}
        </div>
      </section>

      <!-- Recent activity -->
      <section aria-labelledby="activity-heading">
        <h2 id="activity-heading" class="text-lg font-semibold text-white mb-4">
          Recent Activity
        </h2>
        <div
          id="activity-feed"
          class="bg-slate-800 rounded-lg border border-slate-700 overflow-hidden"
          aria-live="polite"
          aria-busy="true"
        >
          <div class="animate-pulse p-4 space-y-3">
            ${[...Array(5)].map(() => `
              <div class="flex gap-3">
                <div class="w-2 h-2 bg-slate-700 rounded-full mt-1.5"></div>
                <div class="flex-1 h-4 bg-slate-700 rounded"></div>
              </div>
            `).join("")}
          </div>
        </div>
      </section>
    </div>
  `;

  // Wire quick-action buttons
  container.querySelector("#btn-register-product")?.addEventListener("click", () => {
    window.location.hash = "/settings";
  });
  container.querySelector("#btn-run-tests")?.addEventListener("click", () => {
    window.location.hash = "/test-runs";
  });
  container.querySelector("#btn-view-reports")?.addEventListener("click", () => {
    window.location.hash = "/test-runs";
  });

  // Load data
  await _loadDashboardData(container);
}

async function _loadDashboardData(container) {
  try {
    const products = await api.listProducts();
    _renderStats(container, products);
    _renderProductCards(container, products);
    await _renderActivity(container, products);
  } catch (err) {
    _renderError(container, err);
  }
}

function _renderStats(container, products) {
  const grid = container.querySelector("#stats-grid");
  if (!grid) return;

  const totalProducts = products.length;
  const avgQuality    = products.length
    ? Math.round(products.reduce((s, p) => s + (p.quality_score || 0), 0) / products.length)
    : 0;

  const stats = [
    { label: "Total Products",      value: totalProducts, unit: "",  id: "stat-products" },
    { label: "Avg Quality Score",   value: avgQuality,    unit: "/100", id: "stat-quality" },
    { label: "Endpoints Monitored", value: "—",           unit: "",  id: "stat-endpoints" },
    { label: "Active Alerts",       value: 0,             unit: "",  id: "stat-alerts" },
  ];

  grid.setAttribute("aria-busy", "false");
  grid.innerHTML = stats.map(s => `
    <div class="bg-slate-800 rounded-lg p-4 border border-slate-700">
      <p class="text-xs font-medium text-slate-400 uppercase tracking-wider mb-1">${s.label}</p>
      <p class="text-2xl font-bold text-white tabular-nums" aria-live="polite">
        ${s.value}<span class="text-sm font-normal text-slate-400 ml-1">${s.unit}</span>
      </p>
    </div>
  `).join("");
}

function _renderProductCards(container, products) {
  const grid = container.querySelector("#products-grid");
  if (!grid) return;
  grid.setAttribute("aria-busy", "false");

  if (products.length === 0) {
    grid.innerHTML = `
      <div class="col-span-full text-center py-12 text-slate-400">
        <p class="text-lg font-medium mb-2">No products registered yet</p>
        <p class="text-sm">Use the Register Product button to add your first product.</p>
      </div>
    `;
    return;
  }

  grid.innerHTML = products
    .slice(0, 8)
    .map(p => `
      <tinaa-product-card
        product-id="${p.id}"
        name="${_esc(p.name)}"
        score="${p.quality_score || 0}"
        grade="${_grade(p.quality_score || 0)}"
        status="${p.status || "active"}"
        env-count="${p.environments?.length ?? 0}"
        alert-count="0"
        last-run="${p.created_at || ""}"
        last-run-status="queued"
      ></tinaa-product-card>
    `)
    .join("");
}

async function _renderActivity(container, products) {
  const feed = container.querySelector("#activity-feed");
  if (!feed) return;
  feed.setAttribute("aria-busy", "false");

  // Collect recent runs from first 3 products
  const allRuns = [];
  for (const p of products.slice(0, 3)) {
    try {
      const runs = await api.listTestRuns(p.id);
      allRuns.push(...runs.map(r => ({ ...r, productName: p.name })));
    } catch {
      // Ignore per-product errors
    }
  }

  if (allRuns.length === 0) {
    feed.innerHTML = `
      <p class="text-center text-slate-400 py-6 text-sm">No recent test runs.</p>
    `;
    return;
  }

  const recent = allRuns.slice(0, 5);
  feed.innerHTML = `
    <ul class="divide-y divide-slate-700" aria-label="Recent test run activity">
      ${recent.map(r => `
        <li class="flex items-center gap-3 px-4 py-3">
          <span class="w-2 h-2 rounded-full shrink-0 ${
            r.status === "passed"  ? "bg-green-400" :
            r.status === "failed"  ? "bg-red-400"   :
            r.status === "running" ? "bg-blue-400"  : "bg-slate-400"
          }" aria-hidden="true"></span>
          <span class="flex-1 text-sm text-slate-300">
            <span class="font-medium text-white">${_esc(r.productName || "")}</span>
            &nbsp;—&nbsp;${r.status || "unknown"}
          </span>
          <time class="text-xs text-slate-500 shrink-0">
            ${r.triggered_at ? new Date(r.triggered_at).toLocaleTimeString() : "—"}
          </time>
        </li>
      `).join("")}
    </ul>
  `;
}

function _renderError(container, err) {
  const statsGrid = container.querySelector("#stats-grid");
  if (statsGrid) {
    statsGrid.setAttribute("aria-busy", "false");
    statsGrid.innerHTML = `
      <div class="col-span-full">
        <tinaa-alert-banner
          severity="warning"
          message="Could not load dashboard data: ${_esc(err.message)}"
        ></tinaa-alert-banner>
      </div>
    `;
  }
}

function _grade(score) {
  if (score >= 90) return "A";
  if (score >= 80) return "B";
  if (score >= 70) return "C";
  if (score >= 60) return "D";
  return "F";
}

function _esc(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/"/g, "&quot;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}
