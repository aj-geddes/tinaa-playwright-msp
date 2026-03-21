/**
 * metric-card.js — Metric display card Web Component.
 *
 * Displays a single metric with:
 * - Metric name
 * - Current value with unit
 * - Trend arrow (up/down/stable)
 * - Percentage vs baseline (colour-coded)
 * - aria-live="polite" for dynamic value updates
 *
 * Usage:
 *   <tinaa-metric-card
 *     label="Response Time"
 *     value="245"
 *     unit="ms"
 *     baseline="220"
 *     trend="up"
 *   ></tinaa-metric-card>
 *
 * Trend: "up" | "down" | "stable"
 * For response-time metrics "up" is bad; for other metrics "up" may be good.
 * Use `invert` attribute to reverse colour logic (e.g., for throughput).
 */

class TINAAMetricCard extends HTMLElement {
  static get observedAttributes() {
    return ["label", "value", "unit", "baseline", "trend", "invert"];
  }

  attributeChangedCallback() {
    if (this.isConnected) this.render();
  }

  connectedCallback() {
    this.render();
  }

  render() {
    const label    = this.getAttribute("label") || "Metric";
    const value    = parseFloat(this.getAttribute("value") ?? "0");
    const unit     = this.getAttribute("unit") || "";
    const baseline = parseFloat(this.getAttribute("baseline") ?? "0");
    const trend    = this.getAttribute("trend") || "stable";
    const invert   = this.hasAttribute("invert");

    // Percentage difference from baseline
    const pctDiff =
      baseline !== 0
        ? Math.round(((value - baseline) / baseline) * 100)
        : 0;
    const absPct = Math.abs(pctDiff);

    // Colour logic: red if over budget, amber if close, green if ok
    // For "invert" metrics (e.g., throughput), flip good/bad
    let colorClass = "text-green-400";
    let statusText = "within budget";
    if (baseline !== 0) {
      const isBad = invert ? pctDiff < 0 : pctDiff > 0;
      const isClose = absPct >= 10 && absPct < 25;
      const isOver  = absPct >= 25;
      if (isOver && isBad) {
        colorClass = "text-red-400";
        statusText = "over budget";
      } else if (isClose && isBad) {
        colorClass = "text-amber-400";
        statusText = "approaching limit";
      } else {
        colorClass = "text-green-400";
        statusText = "within budget";
      }
    }

    // Trend icon
    const trendIcons = {
      up: `<svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" viewBox="0 0 24 24"
                fill="none" stroke="currentColor" stroke-width="2"
                aria-hidden="true" focusable="false">
             <polyline points="18 15 12 9 6 15"/>
           </svg>`,
      down: `<svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" viewBox="0 0 24 24"
                  fill="none" stroke="currentColor" stroke-width="2"
                  aria-hidden="true" focusable="false">
               <polyline points="6 9 12 15 18 9"/>
             </svg>`,
      stable: `<svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" viewBox="0 0 24 24"
                    fill="none" stroke="currentColor" stroke-width="2"
                    aria-hidden="true" focusable="false">
                 <line x1="5" y1="12" x2="19" y2="12"/>
               </svg>`,
    };
    const trendIcon = trendIcons[trend] || trendIcons.stable;

    const pctLabel =
      pctDiff === 0
        ? "Baseline"
        : `${pctDiff > 0 ? "+" : ""}${pctDiff}% vs baseline`;

    this.innerHTML = `
      <article
        class="bg-slate-800 rounded-lg p-4 border border-slate-700 flex flex-col gap-2"
        aria-label="${label}: ${value}${unit}, ${statusText}"
      >
        <!-- Label row -->
        <header class="flex items-center justify-between">
          <h3 class="text-xs font-medium text-slate-400 uppercase tracking-wider truncate">
            ${label}
          </h3>
          <span
            class="${colorClass} shrink-0"
            aria-label="Trend: ${trend}"
          >${trendIcon}</span>
        </header>

        <!-- Value -->
        <p
          class="text-2xl font-bold text-white tabular-nums"
          aria-live="polite"
          aria-atomic="true"
        >
          ${value.toLocaleString()}
          <span class="text-sm font-normal text-slate-400">${unit}</span>
        </p>

        <!-- Baseline comparison -->
        <footer class="flex items-center gap-1 text-xs ${colorClass}">
          <span aria-hidden="true">
            ${pctDiff > 0 ? "▲" : pctDiff < 0 ? "▼" : "—"}
          </span>
          <span>${pctLabel}</span>
          <span class="sr-only">${statusText}</span>
        </footer>
      </article>
    `;
  }
}

customElements.define("tinaa-metric-card", TINAAMetricCard);
