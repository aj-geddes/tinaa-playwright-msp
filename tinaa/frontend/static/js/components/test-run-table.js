/**
 * test-run-table.js — Test Run Results Table Web Component.
 *
 * Displays test run history with:
 * - Status badge (icon + text, not colour alone)
 * - Pass/fail counts
 * - Duration
 * - Trigger type (manual/scheduled/webhook)
 * - Link to full run details
 * - Accessible sortable columns
 *
 * Usage:
 *   <tinaa-test-run-table></tinaa-test-run-table>
 *   el.setRuns([{ id, status, passed, failed, duration_ms, triggered_at, trigger }])
 */

const RUN_STATUS = {
  passed:  { cls: "bg-green-900 text-green-300",  icon: "✓", label: "Passed" },
  failed:  { cls: "bg-red-900 text-red-300",      icon: "✗", label: "Failed" },
  running: { cls: "bg-blue-900 text-blue-300",    icon: "●", label: "Running" },
  queued:  { cls: "bg-slate-700 text-slate-300",  icon: "◷", label: "Queued" },
  error:   { cls: "bg-orange-900 text-orange-300",icon: "!", label: "Error" },
};

/** Format milliseconds to a human-readable duration. */
function formatDuration(ms) {
  if (!ms && ms !== 0) return "—";
  const s = Math.round(ms / 1000);
  if (s < 60) return `${s}s`;
  const m = Math.floor(s / 60);
  const rem = s % 60;
  return `${m}m ${rem}s`;
}

class TINAATestRunTable extends HTMLElement {
  constructor() {
    super();
    this._runs = [];
    this._loading = false;
  }

  connectedCallback() {
    this.render();
  }

  /**
   * @param {Array} runs
   */
  setRuns(runs) {
    this._runs = runs || [];
    this._loading = false;
    this.render();
  }

  setLoading() {
    this._loading = true;
    this.render();
  }

  render() {
    if (this._loading) {
      this.innerHTML = `
        <div class="animate-pulse space-y-2" aria-busy="true" aria-label="Loading test runs">
          ${[...Array(4)].map(() => `<div class="h-10 bg-slate-700 rounded"></div>`).join("")}
        </div>
      `;
      return;
    }

    if (this._runs.length === 0) {
      this.innerHTML = `
        <p class="text-center text-slate-400 py-8 text-sm">
          No test runs found. Trigger a run to get started.
        </p>
      `;
      return;
    }

    this.innerHTML = `
      <div class="overflow-x-auto rounded-lg border border-slate-700">
        <table
          class="w-full text-sm table-dark"
          aria-label="Test run history"
        >
          <thead>
            <tr class="bg-slate-700 text-left">
              <th scope="col" class="px-4 py-3 font-semibold text-slate-300">Status</th>
              <th scope="col" class="px-4 py-3 font-semibold text-slate-300">Run ID</th>
              <th scope="col" class="px-4 py-3 font-semibold text-slate-300">
                Pass / Fail
              </th>
              <th scope="col" class="px-4 py-3 font-semibold text-slate-300">Duration</th>
              <th scope="col" class="px-4 py-3 font-semibold text-slate-300">Trigger</th>
              <th scope="col" class="px-4 py-3 font-semibold text-slate-300">Started</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-700">
            ${this._runs.map((run) => this._renderRow(run)).join("")}
          </tbody>
        </table>
      </div>
    `;
  }

  _renderRow(run) {
    const cfg  = RUN_STATUS[run.status] || RUN_STATUS.queued;
    const dur  = formatDuration(run.duration_ms);
    const pass = run.passed ?? 0;
    const fail = run.failed ?? 0;
    const started = run.triggered_at
      ? new Date(run.triggered_at).toLocaleString()
      : "—";
    const trigger = run.trigger || "manual";
    const shortId = String(run.id || "").slice(0, 8) || "—";

    return `
      <tr class="hover:bg-slate-750 transition-colors">
        <td class="px-4 py-3">
          <span
            class="inline-flex items-center gap-1.5 px-2 py-0.5 rounded-full text-xs
                   font-medium ${cfg.cls}"
            aria-label="Status: ${cfg.label}"
          >
            <span aria-hidden="true">${cfg.icon}</span>
            ${cfg.label}
          </span>
        </td>
        <td class="px-4 py-3 font-mono text-slate-400 text-xs">${shortId}</td>
        <td class="px-4 py-3">
          <span class="text-green-400 font-medium" aria-label="${pass} passed">
            ${pass}↑
          </span>
          <span class="text-slate-500 mx-1">/</span>
          <span class="text-red-400 font-medium" aria-label="${fail} failed">
            ${fail}↓
          </span>
        </td>
        <td class="px-4 py-3 text-slate-400 tabular-nums">${dur}</td>
        <td class="px-4 py-3">
          <span class="px-2 py-0.5 bg-slate-700 text-slate-300 rounded text-xs">
            ${trigger}
          </span>
        </td>
        <td class="px-4 py-3 text-slate-400 text-xs">${started}</td>
      </tr>
    `;
  }
}

customElements.define("tinaa-test-run-table", TINAATestRunTable);
