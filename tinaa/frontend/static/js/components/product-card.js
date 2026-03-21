/**
 * product-card.js — Product Summary Card Web Component.
 *
 * Displays a product overview card with:
 * - Product name
 * - Mini quality score gauge
 * - Environment count badges
 * - Last test run status
 * - Active alerts count
 * - Click/Enter/Space to navigate to product detail
 *
 * Usage:
 *   <tinaa-product-card
 *     product-id="abc-123"
 *     name="My App"
 *     score="87"
 *     grade="A"
 *     status="active"
 *     env-count="3"
 *     alert-count="0"
 *     last-run="2024-01-15T10:30:00Z"
 *     last-run-status="passed"
 *   ></tinaa-product-card>
 */

/** Format an ISO date string to a human-readable relative time. */
function relativeTime(isoString) {
  if (!isoString) return "Never";
  try {
    const diff = Date.now() - new Date(isoString).getTime();
    const mins  = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days  = Math.floor(diff / 86400000);
    if (mins < 1)   return "Just now";
    if (mins < 60)  return `${mins}m ago`;
    if (hours < 24) return `${hours}h ago`;
    return `${days}d ago`;
  } catch {
    return "Unknown";
  }
}

/** Map run status to badge styling. */
function runStatusBadge(status) {
  const map = {
    passed:  { cls: "bg-green-900 text-green-300",  icon: "✓", label: "Passed" },
    failed:  { cls: "bg-red-900 text-red-300",      icon: "✗", label: "Failed" },
    running: { cls: "bg-blue-900 text-blue-300",    icon: "●", label: "Running" },
    queued:  { cls: "bg-slate-700 text-slate-300",  icon: "◷", label: "Queued"  },
  };
  return map[status] || map.queued;
}

/** Map score to fill colour. */
function scoreColor(score) {
  if (score >= 80) return "#22C55E";
  if (score >= 60) return "#F59E0B";
  return "#EF4444";
}

class TINAAProductCard extends HTMLElement {
  static get observedAttributes() {
    return [
      "product-id", "name", "score", "grade", "status",
      "env-count", "alert-count", "last-run", "last-run-status",
    ];
  }

  attributeChangedCallback() {
    if (this.isConnected) this.render();
  }

  connectedCallback() {
    this.render();
    this._bindEvents();
  }

  render() {
    const pid        = this.getAttribute("product-id") || "";
    const name       = this.getAttribute("name") || "Unknown Product";
    const score      = parseFloat(this.getAttribute("score") ?? "0");
    const grade      = this.getAttribute("grade") || "F";
    const envCount   = parseInt(this.getAttribute("env-count") ?? "0");
    const alertCount = parseInt(this.getAttribute("alert-count") ?? "0");
    const lastRun    = this.getAttribute("last-run") || "";
    const lastRunSt  = this.getAttribute("last-run-status") || "queued";
    const badge      = runStatusBadge(lastRunSt);
    const color      = scoreColor(score);

    // Mini SVG gauge (simplified single-ring)
    const r      = 24;
    const circ   = 2 * Math.PI * r;
    const dash   = (score / 100) * circ;
    const size   = 64;
    const center = size / 2;

    this.innerHTML = `
      <article
        class="bg-slate-800 rounded-lg p-4 border border-slate-700 cursor-pointer
               hover:border-blue-500 hover:bg-slate-750 transition-colors duration-150
               focus-within:ring-2 focus-within:ring-blue-500"
        data-product-id="${pid}"
        aria-label="${name} — Quality Score ${score}, Grade ${grade}"
      >
        <a
          href="#/products/${pid}"
          class="block focus:outline-none"
          aria-label="View ${name} details"
          tabindex="0"
        >
          <div class="flex items-start gap-3">
            <!-- Mini quality score gauge -->
            <div class="shrink-0" aria-hidden="true">
              <svg
                width="${size}" height="${size}"
                viewBox="0 0 ${size} ${size}"
                aria-hidden="true" focusable="false"
              >
                <!-- Track -->
                <circle cx="${center}" cy="${center}" r="${r}"
                        fill="none" stroke="#1E293B" stroke-width="6"/>
                <!-- Arc -->
                <circle cx="${center}" cy="${center}" r="${r}"
                        fill="none" stroke="${color}" stroke-width="6"
                        stroke-linecap="round"
                        stroke-dasharray="${dash} ${circ - dash}"
                        transform="rotate(-90 ${center} ${center})"/>
                <!-- Score -->
                <text x="${center}" y="${center + 1}"
                      text-anchor="middle" dominant-baseline="middle"
                      font-size="11px" font-weight="700" fill="${color}">
                  ${score}
                </text>
              </svg>
            </div>

            <!-- Product info -->
            <div class="flex-1 min-w-0">
              <h2 class="font-semibold text-white truncate text-base leading-tight">
                ${name}
              </h2>
              <p class="text-xs text-slate-400 mt-0.5">
                Grade <strong class="text-slate-200">${grade}</strong>
                &bull;
                <span>${envCount} environment${envCount !== 1 ? "s" : ""}</span>
              </p>
            </div>
          </div>

          <!-- Footer row -->
          <div class="mt-3 flex items-center justify-between text-xs">
            <!-- Last run status (icon + text, not just colour) -->
            <span
              class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full font-medium ${badge.cls}"
              aria-label="Last test run: ${badge.label}"
            >
              <span aria-hidden="true">${badge.icon}</span>
              ${badge.label}
            </span>

            <!-- Alert count -->
            <span
              class="${alertCount > 0 ? "text-red-400" : "text-slate-500"}"
              aria-label="${alertCount} active alert${alertCount !== 1 ? "s" : ""}"
            >
              <span aria-hidden="true">&#x26A0;</span>
              ${alertCount} alert${alertCount !== 1 ? "s" : ""}
            </span>

            <!-- Relative time -->
            <time
              datetime="${lastRun}"
              class="text-slate-500"
            >${relativeTime(lastRun)}</time>
          </div>
        </a>
      </article>
    `;

    this._bindEvents();
  }

  _bindEvents() {
    // Keyboard: Enter/Space activates the card (in addition to the <a> tag)
    this.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        const pid = this.getAttribute("product-id");
        if (pid) {
          e.preventDefault();
          window.location.hash = `/products/${pid}`;
        }
      }
    });
  }
}

customElements.define("tinaa-product-card", TINAAProductCard);
