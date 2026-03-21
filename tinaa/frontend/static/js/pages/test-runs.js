/**
 * test-runs.js — Test Run History and Results page.
 *
 * Renders:
 * - Product selector
 * - Trigger test run button
 * - Test run history table (uses tinaa-test-run-table component)
 * - Run detail modal/panel
 */

import { api } from "../api.js";

export async function renderTestRuns(container) {
  container.innerHTML = `
    <div class="space-y-6">
      <div class="flex items-center justify-between">
        <h1 class="text-2xl font-bold text-white">Test Runs</h1>
      </div>

      <!-- Controls -->
      <div class="flex flex-wrap items-end gap-4">
        <div>
          <label for="tr-product" class="block text-xs text-slate-400 mb-1">Product</label>
          <select
            id="tr-product"
            class="bg-slate-700 border border-slate-600 rounded-md px-3 py-2 text-sm text-slate-200
                   focus:outline-none focus:ring-2 focus:ring-blue-500"
            aria-label="Select product"
          >
            <option value="">Loading…</option>
          </select>
        </div>
        <button
          id="btn-trigger-run"
          disabled
          class="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700
                 text-white text-sm font-medium rounded-lg transition-colors
                 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-400
                 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900
                 disabled:opacity-50 disabled:cursor-not-allowed"
          aria-label="Trigger a new test run"
        >
          <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" viewBox="0 0 24 24"
               fill="none" stroke="currentColor" stroke-width="2"
               aria-hidden="true" focusable="false">
            <polygon points="5 3 19 12 5 21 5 3"/>
          </svg>
          Run Tests
        </button>
      </div>

      <!-- Summary stats -->
      <div id="run-stats"
           class="grid grid-cols-2 md:grid-cols-4 gap-4" aria-live="polite">
      </div>

      <!-- Test run table -->
      <section aria-labelledby="runs-heading">
        <h2 id="runs-heading" class="text-lg font-semibold text-white mb-4">
          Run History
        </h2>
        <tinaa-test-run-table id="run-table"></tinaa-test-run-table>
      </section>
    </div>
  `;

  const productSel = container.querySelector("#tr-product");
  const runBtn     = container.querySelector("#btn-trigger-run");
  const runTable   = container.querySelector("#run-table");
  let selectedId   = null;

  runTable?.setLoading?.();

  // Load products
  try {
    const products = await api.listProducts();
    productSel.innerHTML = products.length === 0
      ? '<option value="">No products</option>'
      : `<option value="">Select product</option>` +
        products.map(p => `<option value="${p.id}">${_esc(p.name)}</option>`).join("");

    if (products.length > 0) {
      selectedId = products[0].id;
      productSel.value = selectedId;
      runBtn.disabled = false;
      await _loadRuns(container, runTable, selectedId);
    }
  } catch {
    productSel.innerHTML = '<option value="">Error loading products</option>';
  }

  // Product change
  productSel.addEventListener("change", async () => {
    selectedId = productSel.value;
    runBtn.disabled = !selectedId;
    if (selectedId) {
      runTable.setLoading();
      await _loadRuns(container, runTable, selectedId);
    }
  });

  // Trigger run
  runBtn.addEventListener("click", async () => {
    if (!selectedId) return;
    runBtn.disabled = true;
    runBtn.innerHTML = `
      <svg class="animate-spin w-4 h-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24"
           aria-hidden="true" focusable="false">
        <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
        <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.37 0 0 5.37 0 12h4z"/>
      </svg>
      Queuing…
    `;
    try {
      const run = await api.triggerTestRun(selectedId, { trigger: "manual" });
      _announce(`Test run queued. Run ID: ${run.run_id || run.id || "unknown"}`);
      setTimeout(async () => {
        runTable.setLoading();
        await _loadRuns(container, runTable, selectedId);
      }, 1000);
    } catch (err) {
      _announce(`Failed to trigger run: ${err.message}`);
    } finally {
      runBtn.disabled = false;
      runBtn.innerHTML = `
        <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" viewBox="0 0 24 24"
             fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true" focusable="false">
          <polygon points="5 3 19 12 5 21 5 3"/>
        </svg>
        Run Tests
      `;
    }
  });
}

async function _loadRuns(container, tableEl, productId) {
  try {
    const runs = await api.listTestRuns(productId);
    if (tableEl) tableEl.setRuns(runs);
    _renderRunStats(container, runs);
  } catch {
    if (tableEl) tableEl.setRuns([]);
    _renderRunStats(container, []);
  }
}

function _renderRunStats(container, runs) {
  const statsEl = container.querySelector("#run-stats");
  if (!statsEl) return;

  const total   = runs.length;
  const passed  = runs.filter(r => r.status === "passed").length;
  const failed  = runs.filter(r => r.status === "failed").length;
  const passRate = total ? Math.round((passed / total) * 100) : 0;

  statsEl.innerHTML = [
    { label: "Total Runs",   value: total,   color: "text-white" },
    { label: "Passed",       value: passed,  color: "text-green-400" },
    { label: "Failed",       value: failed,  color: "text-red-400" },
    { label: "Pass Rate",    value: `${passRate}%`, color: passRate >= 80 ? "text-green-400" : "text-amber-400" },
  ].map(s => `
    <div class="bg-slate-800 rounded-lg p-4 border border-slate-700">
      <p class="text-xs font-medium text-slate-400 uppercase tracking-wider mb-1">${s.label}</p>
      <p class="text-2xl font-bold ${s.color} tabular-nums">${s.value}</p>
    </div>
  `).join("");
}

function _announce(msg) {
  const el = document.getElementById("aria-announcer");
  if (el) { el.textContent = ""; setTimeout(() => { el.textContent = msg; }, 50); }
}

function _esc(str) {
  return String(str)
    .replace(/&/g, "&amp;").replace(/"/g, "&quot;")
    .replace(/</g, "&lt;").replace(/>/g, "&gt;");
}
