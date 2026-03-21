/**
 * product-detail.js — Single Product Detail page.
 *
 * Renders:
 * - Large quality score gauge with component breakdown
 * - Environment tabs (production/staging/preview) with endpoint status
 * - Recent test runs table
 * - Active playbooks list
 * - Active alerts for this product
 */

import { api } from "../api.js";

/**
 * @param {HTMLElement} container
 * @param {string} productId
 */
export async function renderProductDetail(container, productId) {
  if (!productId) {
    container.innerHTML = `
      <tinaa-alert-banner severity="critical" message="No product ID provided."></tinaa-alert-banner>
    `;
    return;
  }

  container.innerHTML = `
    <div class="space-y-6" id="product-detail-root">
      <!-- Back link -->
      <nav aria-label="Back navigation">
        <a href="#/"
           class="inline-flex items-center gap-1 text-sm text-blue-400 hover:text-blue-300
                  transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 rounded">
          <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" viewBox="0 0 24 24"
               fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true" focusable="false">
            <polyline points="15 18 9 12 15 6"/>
          </svg>
          Back to Dashboard
        </a>
      </nav>

      <!-- Loading skeleton -->
      <div id="product-header" class="animate-pulse space-y-3" aria-busy="true">
        <div class="h-8 bg-slate-700 rounded w-1/4"></div>
        <div class="h-4 bg-slate-700 rounded w-1/2"></div>
      </div>

      <div class="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <!-- Quality Score column -->
        <div class="lg:col-span-1">
          <section
            aria-labelledby="quality-heading"
            class="bg-slate-800 rounded-lg border border-slate-700 p-6 flex flex-col items-center gap-4"
          >
            <h2 id="quality-heading" class="text-lg font-semibold text-white self-start">
              Quality Score
            </h2>
            <div id="quality-gauge-container" class="animate-pulse w-48 h-48 bg-slate-700 rounded-full">
            </div>
            <div id="quality-recommendations" class="text-xs text-slate-400 space-y-1 self-start w-full">
            </div>
          </section>
        </div>

        <!-- Environments + Endpoints column -->
        <div class="lg:col-span-2">
          <section aria-labelledby="env-heading" class="bg-slate-800 rounded-lg border border-slate-700 p-4">
            <h2 id="env-heading" class="text-lg font-semibold text-white mb-4">Environments</h2>
            <!-- Environment tabs -->
            <div
              role="tablist"
              aria-label="Environments"
              id="env-tabs"
              class="flex gap-1 mb-4 border-b border-slate-700 pb-0"
            ></div>
            <div id="env-panel" class="min-h-32">
              <div class="animate-pulse h-24 bg-slate-700 rounded" aria-busy="true"></div>
            </div>
          </section>
        </div>
      </div>

      <!-- Test runs -->
      <section aria-labelledby="runs-heading">
        <h2 id="runs-heading" class="text-lg font-semibold text-white mb-4">Recent Test Runs</h2>
        <tinaa-test-run-table id="test-run-table"></tinaa-test-run-table>
      </section>

      <!-- Playbooks -->
      <section aria-labelledby="playbooks-heading">
        <h2 id="playbooks-heading" class="text-lg font-semibold text-white mb-4">Playbooks</h2>
        <tinaa-playbook-list id="playbook-list-widget"></tinaa-playbook-list>
      </section>
    </div>
  `;

  // Get component references
  const testRunTable    = container.querySelector("#test-run-table");
  const playbookList    = container.querySelector("#playbook-list-widget");

  testRunTable?.setLoading?.();
  playbookList?.setLoading?.();

  try {
    const [product, quality, runs, playbooks, environments] = await Promise.allSettled([
      api.getProduct(productId),
      api.getQualityScore(productId),
      api.listTestRuns(productId),
      api.listPlaybooks(productId),
      api.listEnvironments(productId),
    ]);

    // Product header
    if (product.status === "fulfilled") {
      _renderProductHeader(container, product.value);
    } else {
      container.querySelector("#product-header").innerHTML = `
        <tinaa-alert-banner severity="warning"
          message="Could not load product: ${_esc(product.reason?.message || "Unknown error")}">
        </tinaa-alert-banner>
      `;
    }

    // Quality gauge
    if (quality.status === "fulfilled") {
      _renderQualityGauge(container, quality.value);
    }

    // Environments + endpoints
    const envList = environments.status === "fulfilled" ? environments.value : [];
    _renderEnvironmentTabs(container, envList, productId);

    // Test runs
    if (testRunTable) {
      const runsData = runs.status === "fulfilled" ? runs.value : [];
      testRunTable.setRuns(runsData);
    }

    // Playbooks
    if (playbookList) {
      const pbData = playbooks.status === "fulfilled" ? playbooks.value : [];
      playbookList.setPlaybooks(pbData);
    }

  } catch (err) {
    container.querySelector("#product-detail-root").prepend(
      Object.assign(document.createElement("tinaa-alert-banner"), {})
    );
  }

  // Handle playbook run events
  container.addEventListener("playbook-run", async (e) => {
    const { playbookId } = e.detail;
    try {
      const result = await api.executePlaybook(playbookId);
      _announce(`Playbook queued: run ID ${result.run_id}`);
    } catch (err) {
      _announce(`Failed to run playbook: ${err.message}`);
    }
  });
}

function _renderProductHeader(container, product) {
  const header = container.querySelector("#product-header");
  if (!header) return;
  header.setAttribute("aria-busy", "false");
  header.innerHTML = `
    <div>
      <h1 class="text-2xl font-bold text-white">${_esc(product.name)}</h1>
      ${product.description
        ? `<p class="text-slate-400 mt-1">${_esc(product.description)}</p>`
        : ""}
      <div class="flex items-center gap-3 mt-2">
        <span class="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs
                     bg-green-900 text-green-300"
              aria-label="Status: ${product.status}">
          <span aria-hidden="true">●</span> ${product.status}
        </span>
        ${product.repository_url
          ? `<a href="${_esc(product.repository_url)}" target="_blank" rel="noopener noreferrer"
                class="text-xs text-blue-400 hover:text-blue-300 transition-colors
                       focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 rounded">
               Repository ↗
             </a>`
          : ""}
      </div>
    </div>
  `;
}

function _renderQualityGauge(container, quality) {
  const gaugeContainer = container.querySelector("#quality-gauge-container");
  const recContainer   = container.querySelector("#quality-recommendations");
  if (!gaugeContainer) return;

  const comp = quality.components || {};
  gaugeContainer.innerHTML = `
    <tinaa-quality-score
      score="${Math.round(quality.score || 0)}"
      grade="${quality.grade || "F"}"
      test-health="${Math.round(comp.test_health?.score ?? 0)}"
      performance="${Math.round(comp.performance?.score ?? 0)}"
      security="${Math.round(comp.security?.score ?? 0)}"
      accessibility="${Math.round(comp.accessibility?.score ?? 0)}"
      size="180"
    ></tinaa-quality-score>
  `;

  if (recContainer && quality.recommendations?.length) {
    recContainer.innerHTML = `
      <p class="font-medium text-slate-300 mb-1 text-sm">Recommendations</p>
      <ul class="space-y-1">
        ${quality.recommendations.slice(0, 3).map(r => `
          <li class="flex items-start gap-1.5 text-xs text-slate-400">
            <span aria-hidden="true" class="text-blue-400 mt-0.5">›</span>
            ${_esc(r)}
          </li>
        `).join("")}
      </ul>
    `;
  }
}

function _renderEnvironmentTabs(container, environments, productId) {
  const tabList = container.querySelector("#env-tabs");
  const panel   = container.querySelector("#env-panel");
  if (!tabList || !panel) return;

  if (environments.length === 0) {
    tabList.innerHTML = "";
    panel.innerHTML = `
      <div class="py-6 text-center">
        <svg xmlns="http://www.w3.org/2000/svg" class="w-8 h-8 mx-auto mb-2 text-slate-600"
             viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"
             aria-hidden="true" focusable="false">
          <rect x="2" y="3" width="20" height="14" rx="2"/>
          <path d="M8 21h8M12 17v4"/>
        </svg>
        <p class="text-slate-300 font-medium text-sm mb-1">No environments configured</p>
        <p class="text-slate-500 text-xs mb-3">
          Environments represent where your app is deployed (production, staging, etc.).
        </p>
        <a href="#/settings"
           class="text-blue-400 hover:text-blue-300 text-sm transition-colors
                  focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 rounded">
          Add an environment in Settings &rarr;
        </a>
      </div>
    `;
    return;
  }

  let activeIdx = 0;

  const renderPanel = (env) => {
    const statusEl = document.createElement("tinaa-endpoint-status");
    panel.innerHTML = "";
    panel.appendChild(statusEl);
    statusEl.setLoading();

    api.listEndpoints(productId, env.id)
      .then(endpoints => {
        statusEl.setEndpoints(
          endpoints.map(ep => ({
            ...ep,
            status: "healthy",
            response_time_ms: null,
            last_checked: null,
          }))
        );
      })
      .catch(() => {
        statusEl.setEndpoints([]);
      });
  };

  tabList.innerHTML = environments.map((env, i) => `
    <button
      role="tab"
      aria-selected="${i === activeIdx}"
      aria-controls="env-panel"
      id="tab-${env.id}"
      class="px-4 py-2 text-sm font-medium border-b-2 transition-colors
             focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500
             ${i === activeIdx
               ? "border-blue-500 text-white"
               : "border-transparent text-slate-400 hover:text-white hover:border-slate-500"}"
      data-env-idx="${i}"
    >
      ${_esc(env.name)} <span class="ml-1 text-xs text-slate-500">${env.env_type}</span>
    </button>
  `).join("");

  tabList.querySelectorAll("[role=tab]").forEach((tab, i) => {
    tab.addEventListener("click", () => {
      activeIdx = i;
      tabList.querySelectorAll("[role=tab]").forEach((t, j) => {
        t.setAttribute("aria-selected", j === i ? "true" : "false");
        t.classList.toggle("border-blue-500", j === i);
        t.classList.toggle("text-white", j === i);
        t.classList.toggle("border-transparent", j !== i);
        t.classList.toggle("text-slate-400", j !== i);
      });
      renderPanel(environments[i]);
    });

    tab.addEventListener("keydown", (e) => {
      if (e.key === "ArrowRight") {
        tabList.querySelectorAll("[role=tab]")[(i + 1) % environments.length]?.focus();
      } else if (e.key === "ArrowLeft") {
        tabList.querySelectorAll("[role=tab]")[
          (i - 1 + environments.length) % environments.length
        ]?.focus();
      }
    });
  });

  renderPanel(environments[activeIdx]);
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
