/**
 * header.js — TINAA MSP Top Header Web Component.
 *
 * Renders the top header bar with:
 * - Mobile hamburger menu toggle
 * - Breadcrumb navigation
 * - Global search input
 * - Dark/light mode toggle
 * - User info / avatar menu
 */

class TINAAHeader extends HTMLElement {
  constructor() {
    super();
    this._breadcrumbs = [{ label: "Dashboard", hash: "/" }];
    this._darkMode = document.documentElement.classList.contains("dark");
  }

  connectedCallback() {
    this._updateBreadcrumbs();          // Set correct breadcrumbs on initial load
    window.addEventListener("hashchange", () => this._updateBreadcrumbs());
  }

  disconnectedCallback() {
    window.removeEventListener("hashchange", () => this._updateBreadcrumbs());
  }

  /**
   * Update breadcrumbs based on the current hash route.
   */
  _updateBreadcrumbs() {
    const hash = window.location.hash.slice(1) || "/";
    const ROUTE_LABELS = {
      "/": "Dashboard",
      "/products": "Products",
      "/playbooks": "Playbooks",
      "/metrics": "Metrics",
      "/test-runs": "Test Runs",
      "/alerts": "Alerts",
      "/settings": "Settings",
      "/integrations": "Integrations",
      "/docs": "Documentation",
    };
    const label = ROUTE_LABELS[hash] || hash;
    this._breadcrumbs =
      hash === "/"
        ? [{ label: "Dashboard", hash: "/" }]
        : [
            { label: "Dashboard", hash: "/" },
            { label, hash },
          ];
    this.render();
  }

  /** Toggle the HTML dark class and re-render the button. */
  _toggleTheme() {
    this._darkMode = !this._darkMode;
    document.documentElement.classList.toggle("dark", this._darkMode);
    const btn = this.querySelector("#theme-toggle");
    if (btn) {
      btn.innerHTML = this._themeIcon();
      btn.setAttribute(
        "aria-label",
        this._darkMode ? "Switch to light mode" : "Switch to dark mode"
      );
    }
  }

  _themeIcon() {
    return this._darkMode
      ? `<!-- Sun icon — switch to light -->
         <svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" viewBox="0 0 24 24" fill="none"
              stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"
              aria-hidden="true" focusable="false">
           <circle cx="12" cy="12" r="5"/>
           <line x1="12" y1="1" x2="12" y2="3"/>
           <line x1="12" y1="21" x2="12" y2="23"/>
           <line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/>
           <line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/>
           <line x1="1" y1="12" x2="3" y2="12"/>
           <line x1="21" y1="12" x2="23" y2="12"/>
           <line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/>
           <line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/>
         </svg>`
      : `<!-- Moon icon — switch to dark -->
         <svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" viewBox="0 0 24 24" fill="none"
              stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"
              aria-hidden="true" focusable="false">
           <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
         </svg>`;
  }

  render() {
    this.innerHTML = `
      <header
        class="flex items-center h-14 px-4 bg-slate-800 border-b border-slate-700
               gap-4 shrink-0 z-10"
        role="banner"
      >
        <!-- Mobile: hamburger menu -->
        <button
          id="mobile-menu-btn"
          class="md:hidden p-1 rounded text-slate-400 hover:text-white hover:bg-slate-700
                 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
          aria-label="Open navigation menu"
          aria-haspopup="true"
          aria-expanded="false"
        >
          <svg xmlns="http://www.w3.org/2000/svg" class="w-5 h-5" viewBox="0 0 24 24" fill="none"
               stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"
               aria-hidden="true" focusable="false">
            <line x1="3" y1="12" x2="21" y2="12"/>
            <line x1="3" y1="6" x2="21" y2="6"/>
            <line x1="3" y1="18" x2="21" y2="18"/>
          </svg>
        </button>

        <!-- Breadcrumbs -->
        <nav aria-label="Breadcrumb" class="hidden sm:flex items-center text-sm">
          <ol class="flex items-center gap-1.5" role="list">
            ${this._breadcrumbs
              .map((crumb, i) => {
                const isLast = i === this._breadcrumbs.length - 1;
                return `
                <li class="flex items-center gap-1.5">
                  ${i > 0
                    ? `<svg xmlns="http://www.w3.org/2000/svg" class="w-3 h-3 text-slate-500"
                            viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
                            aria-hidden="true" focusable="false">
                         <polyline points="9 18 15 12 9 6"/>
                       </svg>`
                    : ""}
                  ${isLast
                    ? `<span class="text-white font-medium" aria-current="page">${crumb.label}</span>`
                    : `<a href="#${crumb.hash}"
                           class="text-slate-400 hover:text-white transition-colors
                                  focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500
                                  rounded"
                        >${crumb.label}</a>`}
                </li>`;
              })
              .join("")}
          </ol>
        </nav>

        <!-- Spacer -->
        <div class="flex-1"></div>

        <!-- Global search -->
        <div class="relative hidden sm:block">
          <label for="global-search" class="sr-only">Search products, playbooks, docs</label>
          <div class="relative">
            <div class="absolute inset-y-0 left-0 flex items-center pl-3 pointer-events-none"
                 aria-hidden="true">
              <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4 text-slate-400"
                   viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
                   stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">
                <circle cx="11" cy="11" r="8"/>
                <line x1="21" y1="21" x2="16.65" y2="16.65"/>
              </svg>
            </div>
            <input
              id="global-search"
              type="search"
              placeholder="Search…"
              autocomplete="off"
              class="pl-9 pr-4 py-1.5 text-sm bg-slate-700 border border-slate-600 rounded-md
                     text-slate-200 placeholder-slate-400 w-48 lg:w-64
                     focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              aria-label="Search products, playbooks, and documentation"
            />
          </div>
        </div>

        <!-- Theme toggle -->
        <button
          id="theme-toggle"
          class="p-1.5 rounded text-slate-400 hover:text-white hover:bg-slate-700
                 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
          aria-label="${this._darkMode ? "Switch to light mode" : "Switch to dark mode"}"
        >
          ${this._themeIcon()}
        </button>

        <!-- User menu -->
        <button
          id="user-menu-btn"
          class="flex items-center gap-2 p-1 rounded-md text-slate-400 hover:text-white
                 hover:bg-slate-700 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
          aria-label="User menu"
          aria-haspopup="menu"
          aria-expanded="false"
        >
          <div
            class="w-7 h-7 rounded-full bg-blue-600 flex items-center justify-center
                   text-white text-xs font-bold select-none"
            aria-hidden="true"
          >
            TM
          </div>
          <span class="hidden md:block text-sm text-slate-300">TINAA MSP</span>
          <svg xmlns="http://www.w3.org/2000/svg" class="w-3 h-3 hidden md:block"
               viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
               aria-hidden="true" focusable="false">
            <polyline points="6 9 12 15 18 9"/>
          </svg>
        </button>
      </header>
    `;

    this._bindEvents();
  }

  _bindEvents() {
    const themeBtn = this.querySelector("#theme-toggle");
    if (themeBtn) {
      themeBtn.addEventListener("click", () => this._toggleTheme());
    }

    const mobileBtn = this.querySelector("#mobile-menu-btn");
    if (mobileBtn) {
      mobileBtn.addEventListener("click", () => {
        const nav = document.querySelector("tinaa-nav");
        if (nav) {
          nav.classList.toggle("mobile-open");
          const isOpen = nav.classList.contains("mobile-open");
          mobileBtn.setAttribute("aria-expanded", String(isOpen));

          let overlay = document.querySelector(".nav-overlay");
          if (!overlay) {
            overlay = document.createElement("div");
            overlay.className = "nav-overlay";
            overlay.addEventListener("click", () => {
              nav.classList.remove("mobile-open");
              overlay.classList.remove("open");
              mobileBtn.setAttribute("aria-expanded", "false");
            });
            document.body.appendChild(overlay);
          }
          overlay.classList.toggle("open", isOpen);
        }
      });
    }
  }
}

customElements.define("tinaa-header", TINAAHeader);
