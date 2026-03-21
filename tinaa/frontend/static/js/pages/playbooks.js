/**
 * playbooks.js — Playbook Management page.
 *
 * Renders:
 * - List of playbooks across all products
 * - Create playbook form with YAML editor textarea
 * - Validate button (calls API)
 * - Run button per playbook
 */

import { api } from "../api.js";

export async function renderPlaybooks(container) {
  container.innerHTML = `
    <div class="space-y-6">
      <div class="flex items-center justify-between">
        <h1 class="text-2xl font-bold text-white">Playbooks</h1>
        <button
          id="btn-new-playbook"
          class="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700
                 text-white text-sm font-medium rounded-lg transition-colors
                 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-400
                 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900"
          aria-label="Create a new playbook"
          aria-expanded="false"
          aria-controls="create-playbook-form"
        >
          <svg xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" viewBox="0 0 24 24"
               fill="none" stroke="currentColor" stroke-width="2"
               aria-hidden="true" focusable="false">
            <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
          </svg>
          New Playbook
        </button>
      </div>

      <!-- Create playbook form (hidden by default) -->
      <section
        id="create-playbook-form"
        class="hidden bg-slate-800 rounded-lg border border-slate-700 p-6"
        aria-labelledby="create-heading"
      >
        <h2 id="create-heading" class="text-lg font-semibold text-white mb-4">
          Create New Playbook
        </h2>
        <form id="playbook-form" novalidate class="space-y-4">
          <!-- Name -->
          <div>
            <label
              for="pb-name"
              class="block text-sm font-medium text-slate-300 mb-1"
            >
              Playbook Name <span aria-hidden="true" class="text-red-400">*</span>
              <span class="sr-only">(required)</span>
            </label>
            <input
              id="pb-name"
              name="name"
              type="text"
              required
              autocomplete="off"
              placeholder="e.g. Smoke Tests"
              class="w-full bg-slate-700 border border-slate-600 rounded-md px-3 py-2 text-sm
                     text-slate-200 placeholder-slate-400
                     focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              aria-required="true"
              aria-describedby="pb-name-error"
            />
            <p id="pb-name-error" class="hidden mt-1 text-xs text-red-400" role="alert"></p>
          </div>

          <!-- Product ID -->
          <div>
            <label for="pb-product" class="block text-sm font-medium text-slate-300 mb-1">
              Product
            </label>
            <select
              id="pb-product"
              name="product_id"
              class="w-full bg-slate-700 border border-slate-600 rounded-md px-3 py-2 text-sm
                     text-slate-200
                     focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              aria-label="Select product for this playbook"
            >
              <option value="">Loading products…</option>
            </select>
          </div>

          <!-- Suite type -->
          <div>
            <label for="pb-suite-type" class="block text-sm font-medium text-slate-300 mb-1">
              Suite Type
            </label>
            <select
              id="pb-suite-type"
              name="suite_type"
              class="w-full bg-slate-700 border border-slate-600 rounded-md px-3 py-2 text-sm
                     text-slate-200
                     focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="smoke">Smoke</option>
              <option value="regression" selected>Regression</option>
              <option value="performance">Performance</option>
              <option value="security">Security</option>
              <option value="accessibility">Accessibility</option>
            </select>
          </div>

          <!-- YAML steps editor -->
          <div>
            <label for="pb-yaml" class="block text-sm font-medium text-slate-300 mb-1">
              Steps (YAML)
            </label>
            <textarea
              id="pb-yaml"
              name="yaml_steps"
              rows="8"
              placeholder="- action: navigate&#10;  url: https://example.com&#10;- action: click&#10;  selector: '#login-btn'"
              class="code-editor w-full bg-slate-700 border border-slate-600 rounded-md
                     px-3 py-2 text-sm text-slate-200 placeholder-slate-400
                     focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              aria-label="Playbook steps in YAML format"
              aria-describedby="pb-yaml-error pb-yaml-hint"
              spellcheck="false"
            ></textarea>
            <p id="pb-yaml-hint" class="mt-1 text-xs text-slate-500">
              One step per item. Supported actions: navigate, click, fill, screenshot, wait, assert.
            </p>
            <p id="pb-yaml-error" class="hidden mt-1 text-xs text-red-400" role="alert"></p>
          </div>

          <!-- Validation result -->
          <div id="validation-result" class="hidden" aria-live="polite" aria-atomic="true"></div>

          <!-- Actions -->
          <div class="flex flex-wrap items-center gap-3 pt-2">
            <button
              type="button"
              id="btn-validate"
              class="px-4 py-2 bg-slate-600 hover:bg-slate-500 text-slate-200 text-sm
                     font-medium rounded-lg transition-colors
                     focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
            >
              Validate
            </button>
            <button
              type="submit"
              class="px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm
                     font-medium rounded-lg transition-colors
                     focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-400
                     focus-visible:ring-offset-2 focus-visible:ring-offset-slate-800"
            >
              Create Playbook
            </button>
            <button
              type="button"
              id="btn-cancel-create"
              class="px-4 py-2 text-slate-400 hover:text-white text-sm font-medium
                     transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-slate-500"
            >
              Cancel
            </button>
          </div>
        </form>
      </section>

      <!-- Playbooks list -->
      <section aria-labelledby="list-heading">
        <h2 id="list-heading" class="text-lg font-semibold text-white mb-4">All Playbooks</h2>
        <tinaa-playbook-list id="main-playbook-list"></tinaa-playbook-list>
      </section>
    </div>
  `;

  const listEl       = container.querySelector("#main-playbook-list");
  const form         = container.querySelector("#playbook-form");
  const formSection  = container.querySelector("#create-playbook-form");
  const newBtn       = container.querySelector("#btn-new-playbook");
  const cancelBtn    = container.querySelector("#btn-cancel-create");
  const validateBtn  = container.querySelector("#btn-validate");
  const productSel   = container.querySelector("#pb-product");
  const validResult  = container.querySelector("#validation-result");

  listEl?.setLoading?.();

  // Toggle create form
  newBtn?.addEventListener("click", () => {
    const isHidden = formSection.classList.contains("hidden");
    formSection.classList.toggle("hidden", !isHidden);
    newBtn.setAttribute("aria-expanded", String(isHidden));
    if (isHidden) {
      container.querySelector("#pb-name")?.focus();
    }
  });

  cancelBtn?.addEventListener("click", () => {
    formSection.classList.add("hidden");
    newBtn.setAttribute("aria-expanded", "false");
    form.reset();
    validResult.classList.add("hidden");
  });

  // Load products into select
  api.listProducts().then(products => {
    if (productSel) {
      productSel.innerHTML = products.length === 0
        ? '<option value="">No products found</option>'
        : `<option value="">Select a product</option>` +
          products.map(p => `<option value="${p.id}">${_esc(p.name)}</option>`).join("");
    }
  }).catch(() => {
    if (productSel) productSel.innerHTML = '<option value="">Could not load products</option>';
  });

  // Validate button
  validateBtn?.addEventListener("click", async () => {
    const yamlText = container.querySelector("#pb-yaml")?.value || "";
    validateBtn.disabled = true;
    validateBtn.textContent = "Validating…";
    validResult.classList.remove("hidden");
    validResult.innerHTML = `<div class="text-xs text-slate-400 animate-pulse">Validating…</div>`;

    try {
      const steps = _parseYamlSteps(yamlText);
      const result = await api.validatePlaybook({
        name: container.querySelector("#pb-name")?.value || "validation",
        steps,
      });

      if (result.valid) {
        validResult.innerHTML = `
          <tinaa-alert-banner severity="success" message="Playbook is valid."></tinaa-alert-banner>
        `;
      } else {
        const errors = (result.errors || []).join("; ");
        validResult.innerHTML = `
          <tinaa-alert-banner severity="warning"
            message="Validation errors: ${_esc(errors)}"></tinaa-alert-banner>
        `;
      }
    } catch (err) {
      validResult.innerHTML = `
        <tinaa-alert-banner severity="critical"
          message="Validation failed: ${_esc(err.message)}"></tinaa-alert-banner>
      `;
    } finally {
      validateBtn.disabled = false;
      validateBtn.textContent = "Validate";
    }
  });

  // Submit form
  form?.addEventListener("submit", async (e) => {
    e.preventDefault();
    const nameInput  = container.querySelector("#pb-name");
    const nameError  = container.querySelector("#pb-name-error");
    const productId  = container.querySelector("#pb-product")?.value;
    const suiteType  = container.querySelector("#pb-suite-type")?.value;
    const yamlText   = container.querySelector("#pb-yaml")?.value || "";

    // Basic validation
    if (!nameInput?.value.trim()) {
      nameError.textContent = "Playbook name is required.";
      nameError.classList.remove("hidden");
      nameInput.setAttribute("aria-invalid", "true");
      nameInput.focus();
      return;
    }
    nameError.classList.add("hidden");
    nameInput.removeAttribute("aria-invalid");

    if (!productId) {
      _announce("Please select a product.");
      return;
    }

    try {
      const steps = _parseYamlSteps(yamlText);
      await api.createPlaybook(productId, {
        name: nameInput.value.trim(),
        suite_type: suiteType,
        steps,
      });
      _announce("Playbook created successfully.");
      formSection.classList.add("hidden");
      newBtn.setAttribute("aria-expanded", "false");
      form.reset();
      validResult.classList.add("hidden");
      await _loadPlaybooks(container, listEl);
    } catch (err) {
      validResult.classList.remove("hidden");
      validResult.innerHTML = `
        <tinaa-alert-banner severity="critical"
          message="Failed to create playbook: ${_esc(err.message)}"></tinaa-alert-banner>
      `;
    }
  });

  // Listen for run events
  container.addEventListener("playbook-run", async (e) => {
    const { playbookId } = e.detail;
    try {
      const result = await api.executePlaybook(playbookId);
      _announce(`Playbook queued. Run ID: ${result.run_id}`);
    } catch (err) {
      _announce(`Failed to run playbook: ${err.message}`);
    }
  });

  await _loadPlaybooks(container, listEl);
}

async function _loadPlaybooks(container, listEl) {
  if (!listEl) return;
  listEl.setLoading();
  try {
    const products = await api.listProducts();
    const allPlaybooks = [];
    for (const p of products.slice(0, 5)) {
      const pbs = await api.listPlaybooks(p.id).catch(() => []);
      allPlaybooks.push(...pbs);
    }
    listEl.setPlaybooks(allPlaybooks);
  } catch (err) {
    listEl.setPlaybooks([]);
  }
}

/** Minimal YAML list parser: lines starting with "- action:" */
function _parseYamlSteps(yaml) {
  const steps = [];
  const lines  = yaml.split("\n");
  let current  = null;

  for (const line of lines) {
    const trimmed = line.trim();
    if (trimmed.startsWith("- ")) {
      if (current) steps.push(current);
      current = {};
      const rest = trimmed.slice(2);
      const kv   = rest.match(/^(\w+):\s*(.+)/);
      if (kv) current[kv[1]] = kv[2].trim();
    } else if (current && trimmed.includes(":")) {
      const kv = trimmed.match(/^(\w+):\s*(.+)/);
      if (kv) current[kv[1]] = kv[2].trim();
    }
  }
  if (current) steps.push(current);
  return steps;
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
