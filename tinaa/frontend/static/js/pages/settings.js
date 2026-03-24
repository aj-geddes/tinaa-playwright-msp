/**
 * settings.js — Product and Environment Settings page.
 *
 * Renders:
 * - Product configuration form
 * - Environment management (add/remove/edit environments)
 * - Endpoint management
 * - Alert rule configuration
 * - .tinaa.yml viewer/editor
 */

import { api } from "../api.js";

export async function renderSettings(container) {
  container.innerHTML = `
    <div class="space-y-6">
      <h1 class="text-2xl font-bold text-white">Settings</h1>

      <!-- Settings tabs -->
      <div role="tablist" aria-label="Settings sections" id="settings-tabs"
           class="flex gap-1 border-b border-slate-700 flex-wrap">
        ${["Product", "Environments", "Endpoints", "Alert Rules", "Config"].map((t, i) => `
          <button
            role="tab"
            aria-selected="${i === 0}"
            aria-controls="settings-panel"
            id="stab-${i}"
            class="px-4 py-2 text-sm font-medium border-b-2 transition-colors -mb-px
                   focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500
                   ${i === 0
                     ? "border-blue-500 text-white"
                     : "border-transparent text-slate-400 hover:text-white hover:border-slate-500"}"
            data-tab-idx="${i}"
          >${t}</button>
        `).join("")}
      </div>

      <div id="settings-panel" role="tabpanel" aria-live="polite">
        <!-- Filled by tab logic -->
      </div>
    </div>
  `;

  const panel = container.querySelector("#settings-panel");
  let selectedTab = 0;

  const PANELS = [
    () => _renderProductPanel(panel),
    () => _renderEnvironmentsPanel(panel),
    () => _renderEndpointsPanel(panel),
    () => _renderAlertRulesPanel(panel),
    () => _renderConfigPanel(panel),
  ];

  container.querySelectorAll("[role=tab][data-tab-idx]").forEach((tab, i) => {
    tab.addEventListener("click", () => {
      selectedTab = i;
      container.querySelectorAll("[role=tab][data-tab-idx]").forEach((t, j) => {
        const active = j === i;
        t.setAttribute("aria-selected", String(active));
        t.classList.toggle("border-blue-500", active);
        t.classList.toggle("text-white", active);
        t.classList.toggle("border-transparent", !active);
        t.classList.toggle("text-slate-400", !active);
      });
      PANELS[i]?.();
    });

    tab.addEventListener("keydown", (e) => {
      const tabs = [...container.querySelectorAll("[role=tab][data-tab-idx]")];
      if (e.key === "ArrowRight") tabs[(i + 1) % tabs.length]?.focus();
      if (e.key === "ArrowLeft")  tabs[(i - 1 + tabs.length) % tabs.length]?.focus();
    });
  });

  // Render default panel
  PANELS[0]();
}

/** Panel 0: Product configuration */
async function _renderProductPanel(panel) {
  panel.innerHTML = `
    <section aria-labelledby="prod-settings-heading">
      <h2 id="prod-settings-heading" class="text-lg font-semibold text-white mb-4">
        Product Configuration
      </h2>
      <div id="product-settings-content" class="animate-pulse space-y-3">
        <div class="h-10 bg-slate-700 rounded w-full"></div>
        <div class="h-10 bg-slate-700 rounded w-full"></div>
      </div>
    </section>
  `;

  try {
    const products = await api.listProducts();
    const content  = panel.querySelector("#product-settings-content");
    if (!content) return;
    content.removeAttribute("class");

    if (products.length === 0) {
      content.innerHTML = `
        <p class="text-slate-400 text-sm">No products registered yet.</p>
        ${_registerProductForm()}
      `;
      _bindRegisterForm(panel, () => _renderProductPanel(panel));
    } else {
      content.innerHTML = `
        <div class="mb-6">
          <label for="settings-product-sel" class="block text-xs text-slate-400 mb-1">
            Select Product to Configure
          </label>
          <select id="settings-product-sel"
                  class="bg-slate-700 border border-slate-600 rounded-md px-3 py-2 text-sm
                         text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500">
            ${products.map(p => `<option value="${p.id}">${_esc(p.name)}</option>`).join("")}
          </select>
        </div>
        <div id="product-form-area">
          ${_productEditForm(products[0])}
        </div>
        <hr class="border-slate-700 my-6"/>
        <h3 class="text-base font-semibold text-white mb-4">Register New Product</h3>
        ${_registerProductForm()}
      `;

      _bindRegisterForm(panel, () => _renderProductPanel(panel));

      panel.querySelector("#settings-product-sel")?.addEventListener("change", (e) => {
        const p = products.find(x => x.id === e.target.value);
        if (p) {
          panel.querySelector("#product-form-area").innerHTML = _productEditForm(p);
        }
      });
    }
  } catch (err) {
    panel.querySelector("#product-settings-content").innerHTML = `
      <tinaa-alert-banner severity="warning"
        message="Could not load products: ${_esc(err.message)}"></tinaa-alert-banner>
    `;
  }
}

function _productEditForm(product) {
  return `
    <form id="edit-product-form" class="space-y-4 max-w-lg" novalidate>
      <div>
        <label for="edit-name" class="block text-sm font-medium text-slate-300 mb-1">
          Product Name
        </label>
        <input id="edit-name" type="text" value="${_esc(product.name)}"
               aria-describedby="edit-name-help"
               class="w-full bg-slate-700 border border-slate-600 rounded-md px-3 py-2 text-sm
                      text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500"/>
        <p id="edit-name-help" class="mt-1 text-xs text-slate-500">
          A human-readable name for your application (e.g., &ldquo;Acme Web App&rdquo;)
        </p>
      </div>
      <div>
        <label for="edit-desc" class="block text-sm font-medium text-slate-300 mb-1">
          Description
        </label>
        <textarea id="edit-desc" rows="3"
                  class="w-full bg-slate-700 border border-slate-600 rounded-md px-3 py-2 text-sm
                         text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
        >${_esc(product.description || "")}</textarea>
      </div>
      <div>
        <label for="edit-repo" class="block text-sm font-medium text-slate-300 mb-1">
          Repository URL
        </label>
        <input id="edit-repo" type="url" value="${_esc(product.repository_url || "")}"
               placeholder="https://github.com/org/repo"
               aria-describedby="edit-repo-help"
               class="w-full bg-slate-700 border border-slate-600 rounded-md px-3 py-2 text-sm
                      text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500"/>
        <p id="edit-repo-help" class="mt-1 text-xs text-slate-500">
          GitHub repository URL (e.g., github.com/acme/webapp). Used for codebase analysis and CI integration.
        </p>
      </div>
      <button type="submit"
              class="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium
                     rounded-lg transition-colors focus:outline-none focus-visible:ring-2
                     focus-visible:ring-blue-400">
        Save Changes
      </button>
    </form>
  `;
}

function _registerProductForm() {
  return `
    <form id="register-product-form" class="space-y-4 max-w-lg" novalidate>
      <div>
        <label for="new-prod-name" class="block text-sm font-medium text-slate-300 mb-1">
          Product Name <span aria-hidden="true" class="text-red-400">*</span>
        </label>
        <input id="new-prod-name" type="text" required
               placeholder="My Application"
               class="w-full bg-slate-700 border border-slate-600 rounded-md px-3 py-2 text-sm
                      text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
               aria-required="true"
               aria-describedby="new-prod-name-help new-prod-name-error"/>
        <p id="new-prod-name-help" class="mt-1 text-xs text-slate-500">
          A human-readable name for your application (e.g., &ldquo;Acme Web App&rdquo;)
        </p>
        <p id="new-prod-name-error" class="hidden mt-1 text-xs text-red-400" role="alert"></p>
      </div>
      <div>
        <label for="new-prod-desc" class="block text-sm font-medium text-slate-300 mb-1">
          Description
        </label>
        <textarea id="new-prod-desc" rows="2"
                  class="w-full bg-slate-700 border border-slate-600 rounded-md px-3 py-2 text-sm
                         text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500"
        ></textarea>
      </div>
      <div>
        <label for="new-prod-repo" class="block text-sm font-medium text-slate-300 mb-1">
          Repository URL
        </label>
        <input id="new-prod-repo" type="url" placeholder="https://github.com/org/repo"
               aria-describedby="new-prod-repo-help"
               class="w-full bg-slate-700 border border-slate-600 rounded-md px-3 py-2 text-sm
                      text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500"/>
        <p id="new-prod-repo-help" class="mt-1 text-xs text-slate-500">
          GitHub repository URL (e.g., github.com/acme/webapp). Used for codebase analysis and CI integration.
        </p>
      </div>
      <div id="register-result" class="hidden" aria-live="polite"></div>
      <button type="submit"
              class="px-4 py-2 bg-green-600 hover:bg-green-700 text-white text-sm font-medium
                     rounded-lg transition-colors focus:outline-none focus-visible:ring-2
                     focus-visible:ring-green-400">
        Register Product
      </button>
    </form>
  `;
}

/** Panel 1: Environment management */
async function _renderEnvironmentsPanel(panel) {
  panel.innerHTML = `
    <section aria-labelledby="env-settings-heading">
      <h2 id="env-settings-heading" class="text-lg font-semibold text-white mb-4">
        Environment Management
      </h2>
      <p class="text-slate-400 text-sm mb-4">
        Add and manage deployment environments for your products.
      </p>
      <form id="add-env-form" class="space-y-4 max-w-lg mb-6 bg-slate-800 p-4 rounded-lg
                                    border border-slate-700" novalidate>
        <h3 class="font-medium text-white text-sm">Add Environment</h3>
        <div>
          <label for="env-product" class="block text-xs text-slate-400 mb-1">Product</label>
          <select id="env-product"
                  class="w-full bg-slate-700 border border-slate-600 rounded-md px-3 py-2 text-sm
                         text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500">
            <option value="">Loading…</option>
          </select>
        </div>
        <div>
          <label for="env-name" class="block text-xs text-slate-400 mb-1">Name</label>
          <input id="env-name" type="text" placeholder="production" required
                 class="w-full bg-slate-700 border border-slate-600 rounded-md px-3 py-2 text-sm
                        text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500"/>
        </div>
        <div>
          <label for="env-url" class="block text-xs text-slate-400 mb-1">Base URL</label>
          <input id="env-url" type="url" placeholder="https://app.example.com" required
                 aria-describedby="env-url-help"
                 class="w-full bg-slate-700 border border-slate-600 rounded-md px-3 py-2 text-sm
                        text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500"/>
          <p id="env-url-help" class="mt-1 text-xs text-slate-500">
            The base URL where this environment is deployed (e.g., https://app.acme.com)
          </p>
        </div>
        <div>
          <label for="env-type" class="block text-xs text-slate-400 mb-1">Type</label>
          <select id="env-type"
                  class="w-full bg-slate-700 border border-slate-600 rounded-md px-3 py-2 text-sm
                         text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500">
            <option value="production">Production</option>
            <option value="staging" selected>Staging</option>
            <option value="preview">Preview</option>
            <option value="development">Development</option>
          </select>
        </div>
        <div id="env-form-result" class="hidden" aria-live="polite"></div>
        <button type="submit"
                class="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium
                       rounded-lg transition-colors focus:outline-none focus-visible:ring-2
                       focus-visible:ring-blue-400">
          Add Environment
        </button>
      </form>
    </section>
  `;

  // Load products
  api.listProducts().then(products => {
    const sel = panel.querySelector("#env-product");
    if (sel) {
      sel.innerHTML = products.length === 0
        ? '<option value="">No products</option>'
        : `<option value="">Select product</option>` +
          products.map(p => `<option value="${p.id}">${_esc(p.name)}</option>`).join("");
    }
  }).catch(() => {
    const sel = panel.querySelector("#env-product");
    if (sel) sel.innerHTML = '<option value="">Error loading</option>';
  });

  // Form submit
  panel.querySelector("#add-env-form")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const productId = panel.querySelector("#env-product")?.value;
    const name      = panel.querySelector("#env-name")?.value.trim();
    const baseUrl   = panel.querySelector("#env-url")?.value.trim();
    const envType   = panel.querySelector("#env-type")?.value;
    const result    = panel.querySelector("#env-form-result");

    if (!productId || !name || !baseUrl) {
      if (result) {
        result.classList.remove("hidden");
        result.innerHTML = `<tinaa-alert-banner severity="warning"
          message="Product, name, and base URL are required."></tinaa-alert-banner>`;
      }
      return;
    }

    try {
      await api.createEnvironment(productId, { name, base_url: baseUrl, env_type: envType });
      if (result) {
        result.classList.remove("hidden");
        result.innerHTML = `<tinaa-alert-banner severity="success"
          message="Environment '${_esc(name)}' added successfully."></tinaa-alert-banner>`;
      }
      _announce(`Environment ${name} added.`);
    } catch (err) {
      if (result) {
        result.classList.remove("hidden");
        result.innerHTML = `<tinaa-alert-banner severity="critical"
          message="Failed: ${_esc(err.message)}"></tinaa-alert-banner>`;
      }
    }
  });
}

/** Panel 2: Endpoint management */
async function _renderEndpointsPanel(panel) {
  panel.innerHTML = `
    <section aria-labelledby="ep-settings-heading">
      <h2 id="ep-settings-heading" class="text-lg font-semibold text-white mb-4">
        Endpoint Management
      </h2>
      <p class="text-slate-400 text-sm">
        Register endpoints to monitor within each environment.
        Select a product and environment to manage endpoints.
      </p>
      <p class="mt-4 text-slate-500 text-sm italic">
        Endpoint management UI — select an environment from the Environments tab first.
      </p>
    </section>
  `;
}

/** Panel 3: Alert rules */
async function _renderAlertRulesPanel(panel) {
  panel.innerHTML = `
    <section aria-labelledby="alert-rules-heading">
      <h2 id="alert-rules-heading" class="text-lg font-semibold text-white mb-4">
        Alert Rule Configuration
      </h2>
      <p class="text-slate-400 text-sm mb-4">
        Configure when alerts are triggered based on metric thresholds.
      </p>
      <div class="bg-slate-800 rounded-lg border border-slate-700 p-4 max-w-lg">
        <form class="space-y-4" novalidate>
          <div>
            <label for="alert-metric" class="block text-xs text-slate-400 mb-1">
              Metric
            </label>
            <select id="alert-metric"
                    class="w-full bg-slate-700 border border-slate-600 rounded-md px-3 py-2 text-sm
                           text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500">
              <option value="response_time_ms">Response Time (ms)</option>
              <option value="quality_score">Quality Score</option>
              <option value="error_rate">Error Rate (%)</option>
              <option value="availability">Availability (%)</option>
            </select>
          </div>
          <div class="grid grid-cols-2 gap-3">
            <div>
              <label for="alert-operator" class="block text-xs text-slate-400 mb-1">
                Operator
              </label>
              <select id="alert-operator"
                      class="w-full bg-slate-700 border border-slate-600 rounded-md px-3 py-2 text-sm
                             text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500">
                <option value="gt">Greater than (&gt;)</option>
                <option value="lt">Less than (&lt;)</option>
                <option value="gte">Greater than or equal (&ge;)</option>
                <option value="lte">Less than or equal (&le;)</option>
              </select>
            </div>
            <div>
              <label for="alert-threshold" class="block text-xs text-slate-400 mb-1">
                Threshold
              </label>
              <input id="alert-threshold" type="number" placeholder="e.g. 2000"
                     class="w-full bg-slate-700 border border-slate-600 rounded-md px-3 py-2 text-sm
                            text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500"/>
            </div>
          </div>
          <div>
            <label for="alert-severity" class="block text-xs text-slate-400 mb-1">
              Severity
            </label>
            <select id="alert-severity"
                    class="w-full bg-slate-700 border border-slate-600 rounded-md px-3 py-2 text-sm
                           text-slate-200 focus:outline-none focus:ring-2 focus:ring-blue-500">
              <option value="critical">Critical</option>
              <option value="warning" selected>Warning</option>
              <option value="info">Info</option>
            </select>
          </div>
          <button type="submit"
                  class="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium
                         rounded-lg transition-colors focus:outline-none focus-visible:ring-2
                         focus-visible:ring-blue-400">
            Save Rule
          </button>
        </form>
      </div>
    </section>
  `;
}

/** Panel 4: .tinaa.yml viewer/editor */
async function _renderConfigPanel(panel) {
  const defaultConfig = `# .tinaa.yml — TINAA MSP Configuration
version: "2.0"

product:
  name: "My Application"
  repository: "https://github.com/org/repo"

environments:
  production:
    base_url: "https://app.example.com"
    monitoring_interval_seconds: 300
  staging:
    base_url: "https://staging.example.com"
    monitoring_interval_seconds: 60

playbooks:
  smoke:
    suite_type: smoke
    steps:
      - action: navigate
        url: "/"
      - action: screenshot
        name: "homepage"

quality_gates:
  production:
    minimum_score: 80
    block_on_fail: true
  staging:
    minimum_score: 70
    block_on_fail: false

alerts:
  response_time_ms:
    warning: 1500
    critical: 3000
  quality_score:
    warning: 70
    critical: 60
`;

  panel.innerHTML = `
    <section aria-labelledby="config-heading">
      <h2 id="config-heading" class="text-lg font-semibold text-white mb-4">
        Configuration (.tinaa.yml)
      </h2>
      <p class="text-slate-400 text-sm mb-4">
        View and edit the TINAA configuration for your project.
      </p>
      <div class="relative">
        <label for="config-editor" class="sr-only">TINAA YAML configuration editor</label>
        <textarea
          id="config-editor"
          rows="30"
          class="code-editor w-full bg-slate-800 border border-slate-700 rounded-lg
                 px-4 py-3 text-slate-200
                 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
          aria-label="TINAA YAML configuration"
          spellcheck="false"
        >${_esc(defaultConfig)}</textarea>
      </div>
      <div class="flex gap-3 mt-3">
        <button
          id="btn-save-config"
          class="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium
                 rounded-lg transition-colors focus:outline-none focus-visible:ring-2
                 focus-visible:ring-blue-400"
        >
          Save Configuration
        </button>
        <button
          id="btn-reset-config"
          class="px-4 py-2 bg-slate-600 hover:bg-slate-500 text-slate-200 text-sm font-medium
                 rounded-lg transition-colors focus:outline-none focus-visible:ring-2
                 focus-visible:ring-slate-500"
        >
          Reset to Default
        </button>
      </div>
      <div id="config-save-result" class="mt-3 hidden" aria-live="polite"></div>
    </section>
  `;

  panel.querySelector("#btn-save-config")?.addEventListener("click", () => {
    const result = panel.querySelector("#config-save-result");
    result.classList.remove("hidden");
    result.innerHTML = `<tinaa-alert-banner severity="success"
      message="Configuration saved (client-side only — API persistence coming soon)."
      dismissible></tinaa-alert-banner>`;
    _announce("Configuration saved.");
  });

  panel.querySelector("#btn-reset-config")?.addEventListener("click", () => {
    panel.querySelector("#config-editor").value = defaultConfig;
    _announce("Configuration reset to default.");
  });
}

/** Bind the register-product-form to API submission. */
function _bindRegisterForm(panel, onSuccess) {
  panel.querySelector("#register-product-form")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const name    = panel.querySelector("#new-prod-name")?.value.trim();
    const desc    = panel.querySelector("#new-prod-desc")?.value.trim();
    const repoUrl = panel.querySelector("#new-prod-repo")?.value.trim();
    const result  = panel.querySelector("#register-result");
    const errEl   = panel.querySelector("#new-prod-name-error");

    // Client-side validation
    if (!name) {
      if (errEl) {
        errEl.textContent = "Product name is required.";
        errEl.classList.remove("hidden");
      }
      panel.querySelector("#new-prod-name")?.focus();
      return;
    }
    if (errEl) errEl.classList.add("hidden");

    const btn = e.target.querySelector('button[type="submit"]');
    if (btn) { btn.disabled = true; btn.textContent = "Registering…"; }

    try {
      await api.createProduct({ name, description: desc, repository_url: repoUrl || null });
      if (result) {
        result.classList.remove("hidden");
        result.innerHTML = `<tinaa-alert-banner severity="success"
          message="Product '${_esc(name)}' registered successfully."></tinaa-alert-banner>`;
      }
      _announce(`Product ${name} registered successfully.`);
      // Refresh the panel after a short delay to show the new product
      setTimeout(() => { if (onSuccess) onSuccess(); }, 1000);
    } catch (err) {
      if (result) {
        result.classList.remove("hidden");
        result.innerHTML = `<tinaa-alert-banner severity="critical"
          message="Failed: ${_esc(err.message)}"></tinaa-alert-banner>`;
      }
    } finally {
      if (btn) { btn.disabled = false; btn.textContent = "Register Product"; }
    }
  });
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
