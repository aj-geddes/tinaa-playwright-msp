/**
 * playbook-list.js — Playbook List Web Component.
 *
 * Renders a list of playbooks with:
 * - Name, suite type badge, status indicator (icon + text)
 * - Run button per playbook
 * - Accessible table layout with proper aria-labels
 * - aria-live updates when run is triggered
 *
 * Usage:
 *   <tinaa-playbook-list></tinaa-playbook-list>
 *
 * Set playbooks via JS:
 *   el.setPlaybooks([{ id, name, suite_type, status, last_run_at }])
 */

const SUITE_BADGE = {
  smoke:       "bg-blue-900 text-blue-300",
  regression:  "bg-purple-900 text-purple-300",
  performance: "bg-green-900 text-green-300",
  security:    "bg-red-900 text-red-300",
  accessibility: "bg-orange-900 text-orange-300",
};

const STATUS_CONFIG = {
  active:  { cls: "text-green-400", icon: "●", label: "Active" },
  draft:   { cls: "text-slate-400", icon: "◌", label: "Draft" },
  paused:  { cls: "text-amber-400", icon: "◙", label: "Paused" },
  error:   { cls: "text-red-400",   icon: "✗", label: "Error" },
};

class TINAAPlaybookList extends HTMLElement {
  constructor() {
    super();
    this._playbooks = [];
    this._loading = false;
  }

  connectedCallback() {
    this.render();
  }

  /**
   * Set playbook data and re-render.
   * @param {Array<{id:string, name:string, suite_type:string, status:string, last_run_at?:string}>} data
   */
  setPlaybooks(data) {
    this._playbooks = data || [];
    this._loading = false;
    this.render();
  }

  /** Show loading skeleton. */
  setLoading() {
    this._loading = true;
    this.render();
  }

  render() {
    if (this._loading) {
      this.innerHTML = `
        <div class="animate-pulse space-y-2" aria-busy="true" aria-label="Loading playbooks">
          ${[...Array(3)].map(() => `
            <div class="h-10 bg-slate-700 rounded-md"></div>
          `).join("")}
        </div>
      `;
      return;
    }

    if (this._playbooks.length === 0) {
      this.innerHTML = `
        <div class="text-center py-10 px-4">
          <svg xmlns="http://www.w3.org/2000/svg" class="w-10 h-10 mx-auto mb-3 text-slate-600"
               viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"
               aria-hidden="true" focusable="false">
            <path d="M9 5H7a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h10a2 2 0 0 0 2-2V7a2 2 0 0 0-2-2h-2"/>
            <rect x="9" y="3" width="6" height="4" rx="1"/>
            <line x1="9" y1="12" x2="15" y2="12"/>
            <line x1="9" y1="16" x2="13" y2="16"/>
          </svg>
          <p class="text-slate-300 font-medium mb-1">No playbooks yet</p>
          <p class="text-slate-500 text-sm mb-3">
            Playbooks define what TINAA tests in each deployment.<br>
            Create one above to start automating quality checks.
          </p>
        </div>
      `;
      return;
    }

    this.innerHTML = `
      <div class="overflow-x-auto rounded-lg border border-slate-700">
        <table
          class="w-full text-sm table-dark"
          aria-label="Playbooks list"
        >
          <thead>
            <tr class="bg-slate-700 text-left">
              <th scope="col" class="px-4 py-3 font-semibold text-slate-300">Name</th>
              <th scope="col" class="px-4 py-3 font-semibold text-slate-300">Type</th>
              <th scope="col" class="px-4 py-3 font-semibold text-slate-300">Status</th>
              <th scope="col" class="px-4 py-3 font-semibold text-slate-300">Last Run</th>
              <th scope="col" class="px-4 py-3 font-semibold text-slate-300">
                <span class="sr-only">Actions</span>
              </th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-700">
            ${this._playbooks.map((pb) => this._renderRow(pb)).join("")}
          </tbody>
        </table>
      </div>
    `;

    this._bindRunButtons();
  }

  _renderRow(pb) {
    const suiteCls = SUITE_BADGE[pb.suite_type] || "bg-slate-700 text-slate-300";
    const statusCfg = STATUS_CONFIG[pb.status] || STATUS_CONFIG.draft;
    const lastRun = pb.last_run_at
      ? new Date(pb.last_run_at).toLocaleString()
      : "Never";

    return `
      <tr class="hover:bg-slate-750 transition-colors" data-playbook-id="${pb.id}">
        <td class="px-4 py-3 font-medium text-white">${pb.name}</td>
        <td class="px-4 py-3">
          <span class="inline-flex px-2 py-0.5 rounded-full text-xs font-medium ${suiteCls}"
                aria-label="Suite type: ${pb.suite_type}">
            ${pb.suite_type}
          </span>
        </td>
        <td class="px-4 py-3">
          <span class="inline-flex items-center gap-1 text-xs ${statusCfg.cls}"
                aria-label="Status: ${statusCfg.label}">
            <span aria-hidden="true">${statusCfg.icon}</span>
            ${statusCfg.label}
          </span>
        </td>
        <td class="px-4 py-3 text-slate-400 text-xs">${lastRun}</td>
        <td class="px-4 py-3 text-right">
          <button
            data-run-id="${pb.id}"
            class="px-3 py-1 text-xs font-medium rounded bg-blue-600 hover:bg-blue-700
                   text-white transition-colors
                   focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-400
                   focus-visible:ring-offset-2 focus-visible:ring-offset-slate-800"
            aria-label="Run playbook: ${pb.name}"
          >
            Run
          </button>
        </td>
      </tr>
    `;
  }

  _bindRunButtons() {
    this.querySelectorAll("button[data-run-id]").forEach((btn) => {
      btn.addEventListener("click", async () => {
        const id = btn.dataset.runId;
        btn.disabled = true;
        btn.textContent = "Running…";
        this.dispatchEvent(
          new CustomEvent("playbook-run", {
            detail: { playbookId: id },
            bubbles: true,
          })
        );
        // Re-enable after 3 s (actual result handled by parent)
        setTimeout(() => {
          if (btn.isConnected) {
            btn.disabled = false;
            btn.textContent = "Run";
          }
        }, 3000);
      });
    });
  }
}

customElements.define("tinaa-playbook-list", TINAAPlaybookList);
