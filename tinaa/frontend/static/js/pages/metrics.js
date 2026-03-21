/**
 * metrics.js — APM Metrics page.
 *
 * Renders:
 * - Endpoint selector dropdown
 * - Metric type tabs (Response Time, Web Vitals, Availability, Error Rate)
 * - Time range selector (1h, 6h, 24h, 7d, 30d)
 * - Line chart drawn on <canvas> using the Canvas API (no library)
 * - Current value vs baseline comparison cards
 * - Anomaly indicators
 */

import { api } from "../api.js";

const METRIC_TABS = [
  {
    id: "response_time_ms",
    label: "Response Time",
    description: "Server response latency in milliseconds. Lower is better. P95 means 95% of requests are faster.",
  },
  {
    id: "web_vitals",
    label: "Web Vitals",
    description: "Core Web Vitals measure real user experience. LCP (loading), CLS (visual stability), INP (interactivity).",
  },
  {
    id: "availability",
    label: "Availability",
    description: "Percentage of successful health checks over time. Target: 99.9%+.",
  },
  {
    id: "error_rate",
    label: "Error Rate",
    description: "Percentage of requests returning 4xx/5xx errors. Target: <1%.",
  },
];

const TIME_RANGES = [
  { value: "1",   label: "1h"  },
  { value: "6",   label: "6h"  },
  { value: "24",  label: "24h" },
  { value: "168", label: "7d"  },
  { value: "720", label: "30d" },
];

export async function renderMetrics(container) {
  container.innerHTML = `
    <div class="space-y-6">
      <h1 class="text-2xl font-bold text-white">Metrics</h1>

      <!-- Controls row -->
      <div class="flex flex-wrap items-center gap-4" role="group" aria-label="Metric controls">
        <!-- Product / endpoint selector -->
        <div>
          <label for="product-selector" class="block text-xs text-slate-400 mb-1">
            Product
          </label>
          <select
            id="product-selector"
            class="bg-slate-700 border border-slate-600 rounded-md px-3 py-2 text-sm text-slate-200
                   focus:outline-none focus:ring-2 focus:ring-blue-500"
            aria-label="Select product to view metrics"
          >
            <option value="">Loading…</option>
          </select>
        </div>

        <!-- Time range selector -->
        <div role="group" aria-labelledby="time-range-label">
          <p id="time-range-label" class="text-xs text-slate-400 mb-1">Time Range</p>
          <div class="flex rounded-md overflow-hidden border border-slate-600">
            ${TIME_RANGES.map((r, i) => `
              <button
                data-hours="${r.value}"
                class="px-3 py-2 text-xs font-medium transition-colors
                       focus:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-blue-500
                       ${i === 2
                         ? "bg-blue-600 text-white"
                         : "bg-slate-700 text-slate-400 hover:bg-slate-600 hover:text-white"}"
                aria-pressed="${i === 2}"
                aria-label="${r.label} time range"
              >${r.label}</button>
            `).join("")}
          </div>
        </div>
      </div>

      <!-- Metric type tabs -->
      <div role="tablist" aria-label="Metric types" id="metric-tabs"
           class="flex gap-1 border-b border-slate-700">
        ${METRIC_TABS.map((tab, i) => `
          <button
            role="tab"
            id="tab-${tab.id}"
            aria-selected="${i === 0}"
            aria-controls="metric-panel"
            class="px-4 py-2 text-sm font-medium border-b-2 transition-colors -mb-px
                   focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500
                   ${i === 0
                     ? "border-blue-500 text-white"
                     : "border-transparent text-slate-400 hover:text-white hover:border-slate-500"}"
            data-metric="${tab.id}"
            data-description="${tab.description.replace(/"/g, '&quot;')}"
          >${tab.label}</button>
        `).join("")}
      </div>

      <!-- Active metric description -->
      <p
        id="metric-description"
        class="text-xs text-slate-400 -mt-2 mb-0"
        aria-live="polite"
      >${METRIC_TABS[0].description}</p>

      <!-- Chart area -->
      <section
        id="metric-panel"
        role="tabpanel"
        aria-live="polite"
        aria-labelledby="tab-response_time_ms"
        class="bg-slate-800 rounded-lg border border-slate-700 p-4"
      >
        <div id="chart-header" class="flex items-center justify-between mb-4">
          <h2 class="text-base font-semibold text-white">Response Time</h2>
          <span id="chart-unit" class="text-xs text-slate-400">ms</span>
        </div>
        <canvas
          id="metrics-canvas"
          class="tinaa-chart"
          aria-label="Response time line chart"
          role="img"
          height="200"
        ></canvas>
        <p id="chart-no-data" class="hidden text-center text-slate-400 py-8 text-sm">
          No data available for this time range.
        </p>
      </section>

      <!-- Baseline comparison cards -->
      <section aria-labelledby="baseline-heading">
        <h2 id="baseline-heading" class="text-lg font-semibold text-white mb-4">
          Current vs Baseline
        </h2>
        <div id="baseline-cards" class="grid grid-cols-2 md:grid-cols-4 gap-4">
          ${["p50", "p90", "p99", "mean"].map(p => `
            <div class="bg-slate-800 rounded-lg p-4 border border-slate-700 animate-pulse">
              <div class="h-3 bg-slate-700 rounded w-1/2 mb-3"></div>
              <div class="h-6 bg-slate-700 rounded w-3/4"></div>
            </div>
          `).join("")}
        </div>
      </section>

      <!-- Anomalies -->
      <section aria-labelledby="anomalies-heading">
        <h2 id="anomalies-heading" class="text-lg font-semibold text-white mb-4">
          Detected Anomalies
        </h2>
        <div id="anomalies-list" class="space-y-2" aria-live="polite">
          <div class="animate-pulse h-12 bg-slate-800 rounded-lg border border-slate-700"></div>
        </div>
      </section>
    </div>
  `;

  // State
  let selectedProductId = null;
  let selectedHours     = 24;
  let selectedMetric    = "response_time_ms";

  // Load product list
  const productSel = container.querySelector("#product-selector");
  try {
    const products = await api.listProducts();
    if (products.length === 0) {
      productSel.innerHTML = '<option value="">No products — register one in Settings</option>';
      const chartPanel = container.querySelector("#metric-panel");
      if (chartPanel) {
        chartPanel.innerHTML = `
          <div class="text-center py-12">
            <svg xmlns="http://www.w3.org/2000/svg" class="w-10 h-10 mx-auto mb-3 text-slate-600"
                 viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"
                 aria-hidden="true" focusable="false">
              <path d="M3 3v18h18"/><path d="m19 9-5 5-4-4-3 3"/>
            </svg>
            <p class="text-slate-300 font-medium mb-1">No metrics yet</p>
            <p class="text-slate-500 text-sm mb-3">
              Metrics appear after you register a product and run tests.
            </p>
            <a href="#/settings"
               class="text-blue-400 hover:text-blue-300 text-sm transition-colors
                      focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 rounded">
              Register your first product &rarr;
            </a>
          </div>
        `;
      }
    } else {
      productSel.innerHTML =
        '<option value="">Select product</option>' +
        products.map(p => `<option value="${p.id}">${_esc(p.name)}</option>`).join("");
      selectedProductId = products[0]?.id;
      productSel.value  = selectedProductId;
      await _loadMetrics(container, selectedProductId, selectedHours, selectedMetric);
    }
  } catch {
    productSel.innerHTML = '<option value="">Error loading products</option>';
  }

  // Product change
  productSel.addEventListener("change", async () => {
    selectedProductId = productSel.value;
    if (selectedProductId) {
      await _loadMetrics(container, selectedProductId, selectedHours, selectedMetric);
    }
  });

  // Time range buttons
  container.querySelectorAll("[data-hours]").forEach(btn => {
    btn.addEventListener("click", async () => {
      selectedHours = parseInt(btn.dataset.hours, 10);
      container.querySelectorAll("[data-hours]").forEach(b => {
        const active = b === btn;
        b.classList.toggle("bg-blue-600", active);
        b.classList.toggle("text-white", active);
        b.classList.toggle("bg-slate-700", !active);
        b.classList.toggle("text-slate-400", !active);
        b.setAttribute("aria-pressed", String(active));
      });
      if (selectedProductId) {
        await _loadMetrics(container, selectedProductId, selectedHours, selectedMetric);
      }
    });
  });

  // Metric tabs
  container.querySelectorAll("[role=tab][data-metric]").forEach((tab, i) => {
    tab.addEventListener("click", async () => {
      selectedMetric = tab.dataset.metric;
      container.querySelectorAll("[role=tab][data-metric]").forEach((t, j) => {
        const active = t === tab;
        t.setAttribute("aria-selected", String(active));
        t.classList.toggle("border-blue-500", active);
        t.classList.toggle("text-white", active);
        t.classList.toggle("border-transparent", !active);
        t.classList.toggle("text-slate-400", !active);
      });
      const panel = container.querySelector("#metric-panel");
      panel?.setAttribute("aria-labelledby", `tab-${selectedMetric}`);
      container.querySelector("#chart-header h2").textContent = tab.textContent;
      // Update description text
      const descEl = container.querySelector("#metric-description");
      if (descEl) descEl.textContent = tab.dataset.description || "";
      if (selectedProductId) {
        await _loadMetrics(container, selectedProductId, selectedHours, selectedMetric);
      }
    });

    tab.addEventListener("keydown", (e) => {
      const tabs = [...container.querySelectorAll("[role=tab][data-metric]")];
      if (e.key === "ArrowRight") tabs[(i + 1) % tabs.length]?.focus();
      if (e.key === "ArrowLeft")  tabs[(i - 1 + tabs.length) % tabs.length]?.focus();
    });
  });
}

async function _loadMetrics(container, productId, hours, metricType) {
  try {
    const data = await api.getMetrics(productId, { hours, metric_type: metricType });
    _drawChart(container, data.metrics || [], metricType);
    _renderBaselineCards(container, data.baseline || {}, data.metrics);
    await _loadAnomalies(container, productId, hours);
  } catch (err) {
    const canvas = container.querySelector("#metrics-canvas");
    const noData = container.querySelector("#chart-no-data");
    if (canvas) canvas.style.display = "none";
    if (noData) {
      noData.classList.remove("hidden");
      noData.textContent = `Could not load metrics: ${err.message}`;
    }
  }
}

/**
 * Draw a line chart on the canvas element using the Canvas 2D API.
 * @param {HTMLElement} container
 * @param {Array<{timestamp:string, value:number}>} points
 * @param {string} metricType
 */
function _drawChart(container, points, metricType) {
  const canvas = container.querySelector("#metrics-canvas");
  const noData = container.querySelector("#chart-no-data");
  if (!canvas) return;

  canvas.style.display = "";
  noData?.classList.add("hidden");

  if (!points.length) {
    noData?.classList.remove("hidden");
    canvas.style.display = "none";
    return;
  }

  // Responsive: set canvas width to container width
  const rect = canvas.parentElement?.getBoundingClientRect();
  const W    = rect ? Math.max(rect.width - 32, 300) : 600;
  const H    = 200;
  canvas.width  = W;
  canvas.height = H;

  const ctx = canvas.getContext("2d");
  if (!ctx) return;

  const PAD    = { top: 16, right: 16, bottom: 28, left: 52 };
  const chartW = W - PAD.left - PAD.right;
  const chartH = H - PAD.top  - PAD.bottom;

  const values = points.map(p => p.value);
  const minV   = Math.min(...values);
  const maxV   = Math.max(...values) || 1;
  const rangeV = maxV - minV || 1;

  // Clear
  ctx.clearRect(0, 0, W, H);

  // Grid lines
  ctx.strokeStyle = "#1E293B";
  ctx.lineWidth   = 1;
  const gridLines = 4;
  for (let i = 0; i <= gridLines; i++) {
    const y = PAD.top + (i / gridLines) * chartH;
    ctx.beginPath();
    ctx.moveTo(PAD.left, y);
    ctx.lineTo(W - PAD.right, y);
    ctx.stroke();

    // Y-axis labels
    const val = maxV - (i / gridLines) * rangeV;
    ctx.fillStyle = "#64748B";
    ctx.font      = "10px system-ui, sans-serif";
    ctx.textAlign = "right";
    ctx.fillText(Math.round(val), PAD.left - 6, y + 3);
  }

  // Map to canvas coordinates
  const toX = (i) => PAD.left + (i / (points.length - 1 || 1)) * chartW;
  const toY = (v) => PAD.top  + (1 - (v - minV) / rangeV) * chartH;

  // Gradient fill under line
  const grad = ctx.createLinearGradient(0, PAD.top, 0, PAD.top + chartH);
  grad.addColorStop(0,   "rgba(59,130,246,0.3)");
  grad.addColorStop(1,   "rgba(59,130,246,0.0)");

  ctx.beginPath();
  ctx.moveTo(toX(0), toY(values[0]));
  for (let i = 1; i < points.length; i++) {
    ctx.lineTo(toX(i), toY(values[i]));
  }
  ctx.lineTo(toX(points.length - 1), H - PAD.bottom);
  ctx.lineTo(toX(0), H - PAD.bottom);
  ctx.closePath();
  ctx.fillStyle = grad;
  ctx.fill();

  // Main line
  ctx.beginPath();
  ctx.strokeStyle = "#3B82F6";
  ctx.lineWidth   = 2;
  ctx.lineJoin    = "round";
  ctx.moveTo(toX(0), toY(values[0]));
  for (let i = 1; i < points.length; i++) {
    ctx.lineTo(toX(i), toY(values[i]));
  }
  ctx.stroke();

  // Data points (every n-th point to avoid clutter)
  const step = Math.max(1, Math.floor(points.length / 8));
  for (let i = 0; i < points.length; i += step) {
    ctx.beginPath();
    ctx.arc(toX(i), toY(values[i]), 3, 0, 2 * Math.PI);
    ctx.fillStyle   = "#3B82F6";
    ctx.strokeStyle = "#0F172A";
    ctx.lineWidth   = 1.5;
    ctx.fill();
    ctx.stroke();
  }

  // X-axis time labels
  const labelStep = Math.max(1, Math.floor(points.length / 5));
  ctx.fillStyle = "#64748B";
  ctx.font      = "10px system-ui, sans-serif";
  ctx.textAlign = "center";
  for (let i = 0; i < points.length; i += labelStep) {
    const t = new Date(points[i].timestamp);
    const label = `${t.getHours().toString().padStart(2, "0")}:${t.getMinutes().toString().padStart(2, "0")}`;
    ctx.fillText(label, toX(i), H - 6);
  }

  // Update aria-label with summary
  canvas.setAttribute(
    "aria-label",
    `${metricType} over time. Latest: ${values.at(-1)?.toFixed(0)}. Min: ${Math.min(...values).toFixed(0)}, Max: ${Math.max(...values).toFixed(0)}.`
  );
}

function _renderBaselineCards(container, baseline, metrics) {
  const cardsEl = container.querySelector("#baseline-cards");
  if (!cardsEl) return;

  const current = metrics?.at(-1)?.value ?? null;
  const percentiles = [
    { key: "p50",  label: "P50 (Median)" },
    { key: "p90",  label: "P90" },
    { key: "p99",  label: "P99" },
    { key: "mean", label: "Mean" },
  ];

  cardsEl.innerHTML = percentiles.map(p => {
    const baseVal = baseline[p.key];
    return `
      <tinaa-metric-card
        label="${_esc(p.label)}"
        value="${baseVal != null ? Math.round(baseVal) : 0}"
        unit="ms"
        baseline="${current != null ? Math.round(current) : 0}"
        trend="stable"
      ></tinaa-metric-card>
    `;
  }).join("");
}

async function _loadAnomalies(container, productId, hours) {
  const listEl = container.querySelector("#anomalies-list");
  if (!listEl) return;
  try {
    const anomalies = await api.getAnomalies(productId, hours);
    if (!anomalies.length) {
      listEl.innerHTML = `
        <div class="text-center py-6">
          <p class="text-green-400 font-medium text-sm mb-1">All clear</p>
          <p class="text-slate-500 text-xs">No anomalies detected in the selected time range.</p>
        </div>
      `;
      return;
    }
    listEl.innerHTML = anomalies.map(a => `
      <tinaa-alert-banner
        severity="${a.severity === "critical" ? "critical" : "warning"}"
        message="${_esc(a.metric)}: ${a.observed_value}ms (${a.deviation_pct > 0 ? "+" : ""}${a.deviation_pct}% vs baseline) at ${new Date(a.detected_at).toLocaleString()}"
      ></tinaa-alert-banner>
    `).join("");
  } catch {
    listEl.innerHTML = `<p class="text-slate-400 text-sm py-4 text-center">Could not load anomalies.</p>`;
  }
}

function _esc(str) {
  return String(str)
    .replace(/&/g, "&amp;").replace(/"/g, "&quot;")
    .replace(/</g, "&lt;").replace(/>/g, "&gt;");
}
