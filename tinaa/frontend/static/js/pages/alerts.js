/**
 * alerts.js — Alert Management page.
 *
 * Renders:
 * - Active alerts list with severity badges (icon + text, not colour alone)
 * - Alert rules configuration table (placeholder)
 * - Acknowledge and resolve buttons
 * - Alert history
 */

import { api } from "../api.js";

/** Simulated alert data (until a dedicated alerts API endpoint exists). */
function _getMockAlerts() {
  return [
    {
      id:        "alt-001",
      severity:  "critical",
      title:     "Response time exceeded threshold",
      message:   "Endpoint /api/checkout took 3200ms — 60% above P99 baseline of 2000ms",
      product:   "E-Commerce Platform",
      triggered: new Date(Date.now() - 600000).toISOString(),
      status:    "active",
    },
    {
      id:        "alt-002",
      severity:  "warning",
      title:     "Quality score dropped below 75",
      message:   "Current quality score is 71. Consider reviewing failed test suites.",
      product:   "Admin Portal",
      triggered: new Date(Date.now() - 1800000).toISOString(),
      status:    "active",
    },
    {
      id:        "alt-003",
      severity:  "info",
      title:     "Scheduled test run completed",
      message:   "Nightly regression suite finished: 124 passed, 2 failed.",
      product:   "Mobile API",
      triggered: new Date(Date.now() - 7200000).toISOString(),
      status:    "acknowledged",
    },
  ];
}

const SEV_CONFIG = {
  critical: { badge: "bg-red-900 text-red-300",    icon: "✗", label: "Critical", rowCls: "border-l-4 border-red-600" },
  warning:  { badge: "bg-amber-900 text-amber-300", icon: "△", label: "Warning",  rowCls: "border-l-4 border-amber-600" },
  info:     { badge: "bg-blue-900 text-blue-300",   icon: "ℹ", label: "Info",     rowCls: "border-l-4 border-blue-600" },
  success:  { badge: "bg-green-900 text-green-300", icon: "✓", label: "Success",  rowCls: "border-l-4 border-green-600" },
};

export async function renderAlerts(container) {
  const alerts = _getMockAlerts();
  const active = alerts.filter(a => a.status === "active");

  container.innerHTML = `
    <div class="space-y-6">
      <div class="flex items-center justify-between">
        <h1 class="text-2xl font-bold text-white">Alerts</h1>
        <div class="flex items-center gap-2">
          <span class="inline-flex items-center gap-1 px-2 py-1 bg-red-900 text-red-300
                       rounded-full text-xs font-medium"
                aria-label="${active.length} active critical alerts">
            <span aria-hidden="true">✗</span>
            ${active.length} active
          </span>
        </div>
      </div>

      <!-- Severity legend -->
      <section
        aria-label="Alert severity guide"
        class="bg-slate-800/60 rounded-lg border border-slate-700 p-4"
      >
        <h2 class="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-3">
          Severity Guide
        </h2>
        <dl class="space-y-2">
          <div class="flex items-start gap-3">
            <span class="shrink-0 inline-flex items-center gap-1 px-2 py-0.5 rounded-full
                         text-xs font-medium bg-red-900 text-red-300"
                  aria-hidden="true">
              <span>✗</span> Critical
            </span>
            <dd class="text-xs text-slate-400">
              Requires immediate attention. Quality or availability severely impacted.
            </dd>
          </div>
          <div class="flex items-start gap-3">
            <span class="shrink-0 inline-flex items-center gap-1 px-2 py-0.5 rounded-full
                         text-xs font-medium bg-amber-900 text-amber-300"
                  aria-hidden="true">
              <span>△</span> Warning
            </span>
            <dd class="text-xs text-slate-400">
              Should be investigated soon. Quality trending downward.
            </dd>
          </div>
          <div class="flex items-start gap-3">
            <span class="shrink-0 inline-flex items-center gap-1 px-2 py-0.5 rounded-full
                         text-xs font-medium bg-blue-900 text-blue-300"
                  aria-hidden="true">
              <span>ℹ</span> Info
            </span>
            <dd class="text-xs text-slate-400">
              Informational. No action required but worth noting.
            </dd>
          </div>
        </dl>
      </section>

      <!-- Active alerts -->
      <section aria-labelledby="active-heading">
        <h2 id="active-heading" class="text-lg font-semibold text-white mb-4">
          Active Alerts
        </h2>
        <div
          id="active-alerts"
          class="space-y-3"
          aria-live="polite"
          aria-atomic="false"
        >
          ${active.length === 0
            ? `<div class="text-center py-8">
                 <p class="text-green-400 font-medium mb-1">No active alerts</p>
                 <p class="text-slate-500 text-sm">
                   All systems are operating normally. Alerts will appear here when thresholds are exceeded.
                 </p>
               </div>`
            : active.map(a => _renderAlertCard(a)).join("")}
        </div>
      </section>

      <!-- Alert rules -->
      <section aria-labelledby="rules-heading">
        <h2 id="rules-heading" class="text-lg font-semibold text-white mb-4">
          Alert Rules
        </h2>
        <div class="overflow-x-auto rounded-lg border border-slate-700">
          <table class="w-full text-sm table-dark" aria-label="Alert rules configuration">
            <thead>
              <tr class="bg-slate-700">
                <th scope="col" class="px-4 py-3 text-left font-semibold text-slate-300">Rule</th>
                <th scope="col" class="px-4 py-3 text-left font-semibold text-slate-300">Metric</th>
                <th scope="col" class="px-4 py-3 text-left font-semibold text-slate-300">Threshold</th>
                <th scope="col" class="px-4 py-3 text-left font-semibold text-slate-300">Severity</th>
                <th scope="col" class="px-4 py-3 text-left font-semibold text-slate-300">Enabled</th>
              </tr>
            </thead>
            <tbody class="divide-y divide-slate-700">
              ${_renderAlertRules()}
            </tbody>
          </table>
        </div>
      </section>

      <!-- Alert history -->
      <section aria-labelledby="history-heading">
        <h2 id="history-heading" class="text-lg font-semibold text-white mb-4">
          Alert History
        </h2>
        <div class="bg-slate-800 rounded-lg border border-slate-700 overflow-hidden">
          <ul aria-label="Alert history" class="divide-y divide-slate-700">
            ${alerts.map(a => `
              <li class="flex items-start gap-3 px-4 py-3">
                <span class="shrink-0 mt-0.5 ${SEV_CONFIG[a.severity]?.badge || SEV_CONFIG.info.badge}
                             px-2 py-0.5 rounded-full text-xs font-medium inline-flex items-center gap-1"
                      aria-label="Severity: ${SEV_CONFIG[a.severity]?.label}">
                  <span aria-hidden="true">${SEV_CONFIG[a.severity]?.icon}</span>
                  ${SEV_CONFIG[a.severity]?.label}
                </span>
                <div class="flex-1 min-w-0">
                  <p class="text-sm font-medium text-white">${_esc(a.title)}</p>
                  <p class="text-xs text-slate-400 mt-0.5">${_esc(a.product)}</p>
                </div>
                <time class="text-xs text-slate-500 shrink-0">
                  ${new Date(a.triggered).toLocaleString()}
                </time>
              </li>
            `).join("")}
          </ul>
        </div>
      </section>
    </div>
  `;

  // Bind action buttons
  container.querySelectorAll("[data-ack-id]").forEach(btn => {
    btn.addEventListener("click", () => {
      const card = btn.closest("[data-alert-id]");
      if (card) {
        card.style.opacity = "0.5";
        btn.disabled = true;
        btn.textContent = "Acknowledged";
        _announce(`Alert acknowledged.`);
      }
    });
  });

  container.querySelectorAll("[data-resolve-id]").forEach(btn => {
    btn.addEventListener("click", () => {
      const card = btn.closest("[data-alert-id]");
      if (card) {
        card.remove();
        _announce(`Alert resolved and removed.`);
        const remaining = container.querySelectorAll("[data-alert-id]").length;
        if (remaining === 0) {
          container.querySelector("#active-alerts").innerHTML = `
            <div class="text-center py-8">
              <p class="text-green-400 font-medium mb-1">No active alerts</p>
              <p class="text-slate-500 text-sm">
                All systems are operating normally. Alerts will appear here when thresholds are exceeded.
              </p>
            </div>
          `;
        }
      }
    });
  });
}

function _renderAlertCard(alert) {
  const cfg = SEV_CONFIG[alert.severity] || SEV_CONFIG.info;
  return `
    <article
      data-alert-id="${alert.id}"
      class="bg-slate-800 rounded-lg p-4 border border-slate-700 ${cfg.rowCls}"
      aria-label="Alert: ${_esc(alert.title)}, severity: ${cfg.label}"
    >
      <div class="flex items-start gap-3">
        <!-- Severity badge (icon + text, not just colour) -->
        <span
          class="shrink-0 inline-flex items-center gap-1 px-2 py-0.5 rounded-full
                 text-xs font-medium ${cfg.badge}"
          aria-label="Severity: ${cfg.label}"
        >
          <span aria-hidden="true">${cfg.icon}</span>
          ${cfg.label}
        </span>

        <div class="flex-1 min-w-0">
          <h3 class="font-semibold text-white text-sm">${_esc(alert.title)}</h3>
          <p class="text-xs text-slate-400 mt-0.5">${_esc(alert.message)}</p>
          <p class="text-xs text-slate-500 mt-1">
            ${_esc(alert.product)} &bull;
            <time datetime="${alert.triggered}">${new Date(alert.triggered).toLocaleString()}</time>
          </p>
        </div>

        <!-- Actions -->
        <div class="flex items-center gap-2 shrink-0">
          <button
            data-ack-id="${alert.id}"
            class="px-3 py-1 text-xs font-medium rounded bg-slate-600 hover:bg-slate-500
                   text-slate-200 transition-colors
                   focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
            aria-label="Acknowledge alert: ${_esc(alert.title)}"
          >
            Acknowledge
          </button>
          <button
            data-resolve-id="${alert.id}"
            class="px-3 py-1 text-xs font-medium rounded bg-green-700 hover:bg-green-600
                   text-white transition-colors
                   focus:outline-none focus-visible:ring-2 focus-visible:ring-green-400"
            aria-label="Resolve alert: ${_esc(alert.title)}"
          >
            Resolve
          </button>
        </div>
      </div>
    </article>
  `;
}

function _renderAlertRules() {
  const rules = [
    { name: "High Response Time",    metric: "response_time_ms",  threshold: "> P99 + 50%", severity: "critical", enabled: true },
    { name: "Quality Score Drop",    metric: "quality_score",     threshold: "< 75",         severity: "warning",  enabled: true },
    { name: "Test Failure Rate",     metric: "test_failure_rate", threshold: "> 20%",        severity: "warning",  enabled: true },
    { name: "Endpoint Down",         metric: "availability",      threshold: "< 99.9%",      severity: "critical", enabled: true },
    { name: "Security Score Low",    metric: "security_score",    threshold: "< 60",         severity: "critical", enabled: false },
  ];

  const sev = {
    critical: "bg-red-900 text-red-300",
    warning:  "bg-amber-900 text-amber-300",
    info:     "bg-blue-900 text-blue-300",
  };

  return rules.map(r => `
    <tr class="hover:bg-slate-750 transition-colors">
      <td class="px-4 py-3 font-medium text-white">${_esc(r.name)}</td>
      <td class="px-4 py-3 font-mono text-xs text-slate-400">${_esc(r.metric)}</td>
      <td class="px-4 py-3 text-slate-300">${_esc(r.threshold)}</td>
      <td class="px-4 py-3">
        <span class="px-2 py-0.5 rounded-full text-xs font-medium ${sev[r.severity] || sev.info}">
          ${r.severity}
        </span>
      </td>
      <td class="px-4 py-3">
        <span class="inline-flex items-center gap-1 text-xs ${r.enabled ? "text-green-400" : "text-slate-500"}"
              aria-label="${r.enabled ? "Enabled" : "Disabled"}">
          <span aria-hidden="true">${r.enabled ? "●" : "○"}</span>
          ${r.enabled ? "Enabled" : "Disabled"}
        </span>
      </td>
    </tr>
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
