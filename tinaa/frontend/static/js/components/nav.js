/**
 * nav.js — TINAA MSP Sidebar Navigation Web Component.
 *
 * Renders a collapsible sidebar with SVG icons for each nav item.
 * Uses aria-current="page" on the active route.
 * Supports keyboard navigation and mobile hamburger toggle.
 */

const NAV_ITEMS = [
  {
    id: "dashboard",
    label: "Dashboard",
    hash: "/",
    icon: `<svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" viewBox="0 0 24 24" fill="none"
             stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"
             aria-hidden="true" focusable="false">
             <rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/>
             <rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/>
           </svg>`,
  },
  {
    id: "products",
    label: "Products",
    hash: "/products",
    icon: `<svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" viewBox="0 0 24 24" fill="none"
             stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"
             aria-hidden="true" focusable="false">
             <path d="M21 16V8a2 2 0 0 0-1-1.73l-7-4a2 2 0 0 0-2 0l-7 4A2 2 0 0 0 3 8v8
                      a2 2 0 0 0 1 1.73l7 4a2 2 0 0 0 2 0l7-4A2 2 0 0 0 21 16z"/>
           </svg>`,
  },
  {
    id: "playbooks",
    label: "Playbooks",
    hash: "/playbooks",
    icon: `<svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" viewBox="0 0 24 24" fill="none"
             stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"
             aria-hidden="true" focusable="false">
             <polygon points="5 3 19 12 5 21 5 3"/>
           </svg>`,
  },
  {
    id: "metrics",
    label: "Metrics",
    hash: "/metrics",
    icon: `<svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" viewBox="0 0 24 24" fill="none"
             stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"
             aria-hidden="true" focusable="false">
             <polyline points="22 12 18 12 15 21 9 3 6 12 2 12"/>
           </svg>`,
  },
  {
    id: "test-runs",
    label: "Test Runs",
    hash: "/test-runs",
    icon: `<svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" viewBox="0 0 24 24" fill="none"
             stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"
             aria-hidden="true" focusable="false">
             <path d="M9 11l3 3L22 4"/>
             <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/>
           </svg>`,
  },
  {
    id: "alerts",
    label: "Alerts",
    hash: "/alerts",
    icon: `<svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" viewBox="0 0 24 24" fill="none"
             stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"
             aria-hidden="true" focusable="false">
             <path d="M18 8A6 6 0 0 0 6 8c0 7-3 9-3 9h18s-3-2-3-9"/>
             <path d="M13.73 21a2 2 0 0 1-3.46 0"/>
           </svg>`,
  },
  {
    id: "settings",
    label: "Settings",
    hash: "/settings",
    icon: `<svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" viewBox="0 0 24 24" fill="none"
             stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"
             aria-hidden="true" focusable="false">
             <circle cx="12" cy="12" r="3"/>
             <path d="M19.07 4.93a10 10 0 0 1 0 14.14M4.93 4.93a10 10 0 0 0 0 14.14"/>
           </svg>`,
  },
  {
    id: "integrations",
    label: "Integrations",
    hash: "/integrations",
    icon: `<svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" viewBox="0 0 24 24" fill="none"
             stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"
             aria-hidden="true" focusable="false">
             <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/>
             <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>
           </svg>`,
  },
  {
    id: "docs",
    label: "Documentation",
    hash: "/docs",
    icon: `<svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" viewBox="0 0 24 24" fill="none"
             stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"
             aria-hidden="true" focusable="false">
             <path d="M2 3h6a4 4 0 0 1 4 4v14a3 3 0 0 0-3-3H2z"/>
             <path d="M22 3h-6a4 4 0 0 0-4 4v14a3 3 0 0 1 3-3h7z"/>
           </svg>`,
  },
];

class TINAANav extends HTMLElement {
  constructor() {
    super();
    this._collapsed = false;
    this._activeHash = window.location.hash.slice(1) || "/";
  }

  connectedCallback() {
    this.render();
    this._bindEvents();
    window.addEventListener("hashchange", () => this._updateActive());
  }

  disconnectedCallback() {
    window.removeEventListener("hashchange", () => this._updateActive());
  }

  /** Toggle sidebar collapsed/expanded state. */
  toggleCollapse() {
    this._collapsed = !this._collapsed;
    this.classList.toggle("collapsed", this._collapsed);
    this.render();
  }

  _updateActive() {
    this._activeHash = window.location.hash.slice(1) || "/";
    this.querySelectorAll("a[data-hash]").forEach((link) => {
      const isActive = link.dataset.hash === this._activeHash;
      link.setAttribute("aria-current", isActive ? "page" : "false");
      link.classList.toggle(
        "bg-blue-600",
        isActive
      );
      link.classList.toggle("text-white", isActive);
      link.classList.toggle("text-slate-400", !isActive);
    });
  }

  render() {
    const c = this._collapsed;
    this.innerHTML = `
      <nav
        class="h-full flex flex-col bg-slate-800 border-r border-slate-700
               transition-all duration-250"
        aria-label="Main navigation"
      >
        <!-- Logo / brand -->
        <div class="flex items-center h-14 px-4 border-b border-slate-700 shrink-0">
          <span class="text-blue-400" aria-hidden="true">
            <svg xmlns="http://www.w3.org/2000/svg" class="w-7 h-7" viewBox="0 0 24 24" fill="none"
                 stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <circle cx="12" cy="12" r="10"/>
              <path d="M12 8v4l3 3"/>
            </svg>
          </span>
          ${!c ? `<span class="ml-2 font-bold text-white tracking-wide text-sm">TINAA MSP</span>` : ""}
          <button
            id="nav-collapse-btn"
            class="ml-auto p-1 rounded text-slate-400 hover:text-white hover:bg-slate-700
                   focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
            aria-label="${c ? "Expand sidebar" : "Collapse sidebar"}"
            aria-expanded="${!c}"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" viewBox="0 0 24 24" fill="none"
                 stroke="currentColor" stroke-width="2" aria-hidden="true" focusable="false">
              ${c
                ? '<polyline points="9 18 15 12 9 6"/>'
                : '<polyline points="15 18 9 12 15 6"/>'}
            </svg>
          </button>
        </div>

        <!-- Nav items -->
        <ul class="flex-1 overflow-y-auto py-2 space-y-0.5 px-2" role="list">
          ${NAV_ITEMS.map((item) => this._renderItem(item)).join("")}
        </ul>

        <!-- Version footer -->
        <div class="px-4 py-3 border-t border-slate-700 text-xs text-slate-500 shrink-0">
          ${!c ? '<span>TINAA MSP v2.0</span>' : ""}
        </div>
      </nav>
    `;

    this._bindEvents();
    this._updateActive();
  }

  /**
   * Render a single navigation item.
   * @param {{id:string, label:string, hash:string, icon:string}} item
   */
  _renderItem(item) {
    const c = this._collapsed;
    const isActive = this._activeHash === item.hash;
    const activeClasses = isActive
      ? "bg-blue-600 text-white"
      : "text-slate-400 hover:bg-slate-700 hover:text-white";

    return `
      <li role="listitem">
        <a
          href="#${item.hash}"
          data-hash="${item.hash}"
          aria-current="${isActive ? "page" : "false"}"
          aria-label="${item.label}"
          class="flex items-center gap-3 px-3 py-2 rounded-md text-sm font-medium
                 transition-colors duration-150
                 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500
                 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-800
                 ${activeClasses}"
        >
          ${item.icon}
          ${!c ? `<span class="truncate">${item.label}</span>` : ""}
        </a>
      </li>
    `;
  }

  _bindEvents() {
    const collapseBtn = this.querySelector("#nav-collapse-btn");
    if (collapseBtn) {
      collapseBtn.addEventListener("click", () => this.toggleCollapse());
    }
  }
}

customElements.define("tinaa-nav", TINAANav);
