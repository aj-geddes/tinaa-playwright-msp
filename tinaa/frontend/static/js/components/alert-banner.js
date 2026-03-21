/**
 * alert-banner.js — Alert Notification Banner Web Component.
 *
 * Renders an alert banner with:
 * - Severity icon (critical/warning/info/success) — icon + text, not colour alone
 * - Alert message
 * - Dismiss button
 * - aria-live region for dynamic announcements
 *
 * Usage:
 *   <tinaa-alert-banner
 *     severity="warning"
 *     message="Response time exceeded baseline by 45%"
 *     dismissible
 *   ></tinaa-alert-banner>
 *
 * Severity: "critical" | "warning" | "info" | "success"
 */

const SEVERITY_CONFIG = {
  critical: {
    containerCls: "bg-red-950 border-red-700 text-red-200",
    iconCls:      "text-red-400",
    label:        "Critical",
    icon: `<svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5 shrink-0" viewBox="0 0 24 24"
                fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"
                stroke-linejoin="round" aria-hidden="true" focusable="false">
             <circle cx="12" cy="12" r="10"/>
             <line x1="12" y1="8" x2="12" y2="12"/>
             <line x1="12" y1="16" x2="12.01" y2="16"/>
           </svg>`,
  },
  warning: {
    containerCls: "bg-amber-950 border-amber-700 text-amber-200",
    iconCls:      "text-amber-400",
    label:        "Warning",
    icon: `<svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5 shrink-0" viewBox="0 0 24 24"
                fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"
                stroke-linejoin="round" aria-hidden="true" focusable="false">
             <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86
                      a2 2 0 0 0-3.42 0z"/>
             <line x1="12" y1="9" x2="12" y2="13"/>
             <line x1="12" y1="17" x2="12.01" y2="17"/>
           </svg>`,
  },
  info: {
    containerCls: "bg-blue-950 border-blue-700 text-blue-200",
    iconCls:      "text-blue-400",
    label:        "Info",
    icon: `<svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5 shrink-0" viewBox="0 0 24 24"
                fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"
                stroke-linejoin="round" aria-hidden="true" focusable="false">
             <circle cx="12" cy="12" r="10"/>
             <line x1="12" y1="16" x2="12" y2="12"/>
             <line x1="12" y1="8" x2="12.01" y2="8"/>
           </svg>`,
  },
  success: {
    containerCls: "bg-green-950 border-green-700 text-green-200",
    iconCls:      "text-green-400",
    label:        "Success",
    icon: `<svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5 shrink-0" viewBox="0 0 24 24"
                fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"
                stroke-linejoin="round" aria-hidden="true" focusable="false">
             <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
             <polyline points="22 4 12 14.01 9 11.01"/>
           </svg>`,
  },
};

class TINAAAlertBanner extends HTMLElement {
  static get observedAttributes() {
    return ["severity", "message", "dismissible"];
  }

  attributeChangedCallback() {
    if (this.isConnected) this.render();
  }

  connectedCallback() {
    this.render();
  }

  render() {
    const severity    = this.getAttribute("severity") || "info";
    const message     = this.getAttribute("message") || "";
    const dismissible = this.hasAttribute("dismissible");
    const cfg         = SEVERITY_CONFIG[severity] || SEVERITY_CONFIG.info;

    this.innerHTML = `
      <div
        class="flex items-start gap-3 p-3 rounded-lg border ${cfg.containerCls}"
        role="alert"
        aria-live="polite"
        aria-atomic="true"
      >
        <!-- Icon — not colour-only indicator -->
        <span class="${cfg.iconCls}">${cfg.icon}</span>

        <!-- Content -->
        <div class="flex-1 min-w-0">
          <p class="text-sm font-medium">
            <span class="font-semibold mr-1">${cfg.label}:</span>${message}
          </p>
        </div>

        <!-- Dismiss button -->
        ${dismissible
          ? `<button
               type="button"
               class="shrink-0 ml-1 p-0.5 rounded hover:bg-white/10
                      focus:outline-none focus-visible:ring-2 focus-visible:ring-white"
               aria-label="Dismiss this ${cfg.label.toLowerCase()} alert"
             >
               <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" viewBox="0 0 24 24"
                    fill="none" stroke="currentColor" stroke-width="2"
                    aria-hidden="true" focusable="false">
                 <line x1="18" y1="6" x2="6" y2="18"/>
                 <line x1="6" y1="6" x2="18" y2="18"/>
               </svg>
             </button>`
          : ""}
      </div>
    `;

    if (dismissible) {
      const btn = this.querySelector("button");
      btn?.addEventListener("click", () => {
        this.dispatchEvent(new CustomEvent("dismissed", { bubbles: true }));
        this.remove();
      });
    }
  }
}

customElements.define("tinaa-alert-banner", TINAAAlertBanner);
