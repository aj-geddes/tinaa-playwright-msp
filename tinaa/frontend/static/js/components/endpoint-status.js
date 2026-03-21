/**
 * endpoint-status.js — Endpoint Health Status Grid Web Component.
 *
 * Renders a grid of endpoint status cards showing:
 * - Method badge (GET/POST/etc.)
 * - Path
 * - Status (healthy/degraded/down) — icon + text + colour
 * - Response time
 * - Last checked timestamp
 *
 * Usage:
 *   <tinaa-endpoint-status></tinaa-endpoint-status>
 *   el.setEndpoints([{ id, path, method, status, response_time_ms, last_checked }])
 */

const ENDPOINT_STATUS = {
  healthy:  {
    cls:    "border-green-700 bg-green-950",
    badge:  "bg-green-900 text-green-300",
    dot:    "bg-green-400",
    icon:   "✓",
    label:  "Healthy",
    pulse:  false,
  },
  degraded: {
    cls:    "border-amber-700 bg-amber-950",
    badge:  "bg-amber-900 text-amber-300",
    dot:    "bg-amber-400",
    icon:   "△",
    label:  "Degraded",
    pulse:  true,
  },
  down: {
    cls:    "border-red-700 bg-red-950",
    badge:  "bg-red-900 text-red-300",
    dot:    "bg-red-400",
    icon:   "✗",
    label:  "Down",
    pulse:  true,
  },
  unknown: {
    cls:    "border-slate-600 bg-slate-800",
    badge:  "bg-slate-700 text-slate-300",
    dot:    "bg-slate-400",
    icon:   "?",
    label:  "Unknown",
    pulse:  false,
  },
};

const METHOD_COLOURS = {
  GET:    "bg-blue-900 text-blue-300",
  POST:   "bg-green-900 text-green-300",
  PUT:    "bg-amber-900 text-amber-300",
  PATCH:  "bg-purple-900 text-purple-300",
  DELETE: "bg-red-900 text-red-300",
};

class TINAAEndpointStatus extends HTMLElement {
  constructor() {
    super();
    this._endpoints = [];
    this._loading = false;
  }

  connectedCallback() {
    this.render();
  }

  /**
   * @param {Array<{id, path, method, status, response_time_ms, last_checked}>} data
   */
  setEndpoints(data) {
    this._endpoints = data || [];
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
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3 animate-pulse"
             aria-busy="true" aria-label="Loading endpoint statuses">
          ${[...Array(6)].map(() => `
            <div class="h-20 bg-slate-700 rounded-lg"></div>
          `).join("")}
        </div>
      `;
      return;
    }

    if (this._endpoints.length === 0) {
      this.innerHTML = `
        <p class="text-center text-slate-400 py-8 text-sm">
          No endpoints registered. Add endpoints in Settings.
        </p>
      `;
      return;
    }

    this.innerHTML = `
      <section aria-label="Endpoint health status grid">
        <ul
          class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3"
          role="list"
        >
          ${this._endpoints.map((ep) => this._renderCard(ep)).join("")}
        </ul>
      </section>
    `;
  }

  _renderCard(ep) {
    const cfg    = ENDPOINT_STATUS[ep.status] || ENDPOINT_STATUS.unknown;
    const mCls   = METHOD_COLOURS[ep.method?.toUpperCase()] || "bg-slate-700 text-slate-300";
    const rt     = ep.response_time_ms != null ? `${ep.response_time_ms}ms` : "—";
    const when   = ep.last_checked
      ? new Date(ep.last_checked).toLocaleTimeString()
      : "Never";

    return `
      <li role="listitem">
        <article
          class="rounded-lg border p-3 ${cfg.cls} text-sm"
          aria-label="Endpoint ${ep.method} ${ep.path}: ${cfg.label}, ${rt}"
        >
          <!-- Header: method + path + status dot -->
          <header class="flex items-center gap-2 mb-2">
            <span
              class="px-1.5 py-0.5 rounded text-xs font-mono font-semibold ${mCls}"
              aria-label="Method: ${ep.method}"
            >${ep.method}</span>
            <span class="font-mono text-xs text-slate-200 truncate flex-1"
                  title="${ep.path}">${ep.path}</span>
            <span
              class="w-2 h-2 rounded-full ${cfg.dot} ${cfg.pulse ? "status-dot-pulse" : ""} shrink-0"
              aria-hidden="true"
            ></span>
          </header>

          <!-- Status + response time -->
          <div class="flex items-center justify-between text-xs">
            <span
              class="inline-flex items-center gap-1 ${cfg.badge} px-2 py-0.5 rounded-full"
              aria-label="Status: ${cfg.label}"
            >
              <span aria-hidden="true">${cfg.icon}</span>
              ${cfg.label}
            </span>
            <span class="text-slate-400 tabular-nums"
                  aria-label="Response time: ${rt}">${rt}</span>
          </div>

          <!-- Last checked -->
          <footer class="mt-1.5 text-xs text-slate-500">
            Checked: <time>${when}</time>
          </footer>
        </article>
      </li>
    `;
  }
}

customElements.define("tinaa-endpoint-status", TINAAEndpointStatus);
