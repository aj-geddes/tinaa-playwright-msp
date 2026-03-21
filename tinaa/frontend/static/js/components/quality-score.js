/**
 * quality-score.js — Quality Score donut/gauge SVG Web Component.
 *
 * Renders an animated circular SVG gauge with:
 * - Overall score (0–100) and letter grade in the centre
 * - Four coloured arcs for: test health (blue), performance (green),
 *   security (purple), accessibility (orange)
 * - aria-label describing the score for screen readers
 * - Animates stroke-dashoffset on first render
 *
 * Usage:
 *   <tinaa-quality-score
 *     score="87"
 *     grade="A"
 *     test-health="90"
 *     performance="85"
 *     security="80"
 *     accessibility="95"
 *     size="200"
 *   ></tinaa-quality-score>
 */

const COMPONENT_CONFIG = [
  { key: "test-health",    label: "Test Health",    color: "#3B82F6", weight: 0.40 },
  { key: "performance",    label: "Performance",    color: "#22C55E", weight: 0.30 },
  { key: "security",       label: "Security",       color: "#A855F7", weight: 0.15 },
  { key: "accessibility",  label: "Accessibility",  color: "#F97316", weight: 0.15 },
];

/** Map a numeric score (0–100) to a letter grade. */
function scoreToGrade(score) {
  if (score >= 90) return "A";
  if (score >= 80) return "B";
  if (score >= 70) return "C";
  if (score >= 60) return "D";
  return "F";
}

/** Map a score to a colour from the design palette. */
function scoreToColor(score) {
  if (score >= 80) return "#22C55E";   // green
  if (score >= 60) return "#F59E0B";   // amber
  return "#EF4444";                    // red
}

class TINAAQualityScore extends HTMLElement {
  static get observedAttributes() {
    return ["score", "grade", "test-health", "performance", "security", "accessibility", "size"];
  }

  attributeChangedCallback() {
    if (this.isConnected) this.render();
  }

  connectedCallback() {
    this.render();
  }

  /** Parse numeric attribute with fallback. */
  _num(attr, fallback = 0) {
    const val = parseFloat(this.getAttribute(attr));
    return isNaN(val) ? fallback : val;
  }

  render() {
    const size     = this._num("size", 200);
    const score    = this._num("score", 0);
    const grade    = this.getAttribute("grade") || scoreToGrade(score);
    const center   = size / 2;
    const stroke   = Math.max(size * 0.08, 10);
    const gap      = stroke + 4;
    const outerR   = center - stroke / 2 - 4;

    const scoreColor = scoreToColor(score);
    const ariaLabel  = `Quality Score: ${score} out of 100, Grade ${grade}`;

    // Build the four component arcs
    const components = COMPONENT_CONFIG.map((cfg) => {
      const value = this._num(cfg.key, 0);
      return { ...cfg, value };
    });

    // Outer ring — overall score arc
    const outerCirc = 2 * Math.PI * outerR;
    const outerDash = (score / 100) * outerCirc;
    const outerGap  = outerCirc - outerDash;

    // Inner component rings (stacked, each successively smaller)
    const componentArcs = components.map((comp, idx) => {
      const r    = outerR - stroke - gap * (idx + 1);
      const circ = 2 * Math.PI * r;
      const dash = (comp.value / 100) * circ;
      return { ...comp, r, circ, dash, gap: circ - dash };
    });

    this.innerHTML = `
      <figure
        class="inline-flex flex-col items-center gap-2"
        aria-label="${ariaLabel}"
        role="img"
      >
        <svg
          width="${size}"
          height="${size}"
          viewBox="0 0 ${size} ${size}"
          class="quality-gauge"
          aria-hidden="true"
          focusable="false"
          overflow="visible"
        >
          <!-- Background track — outer ring -->
          <circle
            cx="${center}" cy="${center}" r="${outerR}"
            fill="none"
            stroke="#1E293B"
            stroke-width="${stroke}"
          />
          <!-- Foreground arc — overall score -->
          <circle
            cx="${center}" cy="${center}" r="${outerR}"
            fill="none"
            stroke="${scoreColor}"
            stroke-width="${stroke}"
            stroke-linecap="round"
            stroke-dasharray="${outerDash} ${outerGap}"
            transform="rotate(-90 ${center} ${center})"
            class="quality-gauge-ring"
          />

          ${componentArcs.map((arc) => `
            <!-- Background track for ${arc.label} -->
            <circle
              cx="${center}" cy="${center}" r="${arc.r}"
              fill="none"
              stroke="#1E293B"
              stroke-width="${stroke * 0.65}"
            />
            <!-- Foreground arc for ${arc.label} (${arc.value}%) -->
            <circle
              cx="${center}" cy="${center}" r="${arc.r}"
              fill="none"
              stroke="${arc.color}"
              stroke-width="${stroke * 0.65}"
              stroke-linecap="round"
              stroke-dasharray="${arc.dash} ${arc.gap}"
              transform="rotate(-90 ${center} ${center})"
              class="quality-gauge-ring"
            />
          `).join("")}

          <!-- Centre: score number -->
          <text
            x="${center}" y="${center - 8}"
            text-anchor="middle"
            dominant-baseline="middle"
            font-size="${size * 0.18}px"
            font-weight="700"
            fill="${scoreColor}"
            class="quality-grade-label"
          >${score}</text>

          <!-- Centre: grade letter -->
          <text
            x="${center}" y="${center + size * 0.12}"
            text-anchor="middle"
            dominant-baseline="middle"
            font-size="${size * 0.09}px"
            font-weight="600"
            fill="#94A3B8"
          >Grade ${grade}</text>
        </svg>

        <!-- Legend -->
        <dl class="grid grid-cols-2 gap-x-4 gap-y-1 text-xs w-full max-w-xs">
          ${components.map((c) => `
            <div class="flex items-center gap-1.5">
              <span
                class="w-2.5 h-2.5 rounded-full shrink-0"
                style="background:${c.color}"
                aria-hidden="true"
              ></span>
              <dt class="text-slate-400 truncate">${c.label}</dt>
              <dd class="ml-auto font-medium text-slate-200">${c.value}</dd>
            </div>
          `).join("")}
        </dl>
      </figure>
    `;
  }
}

customElements.define("tinaa-quality-score", TINAAQualityScore);
