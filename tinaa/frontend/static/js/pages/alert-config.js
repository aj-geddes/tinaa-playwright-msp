/**
 * alert-config.js — Alert Channels Configuration page.
 *
 * Renders:
 * 1. Configured channels list — cards showing each channel with type icon,
 *    name, enabled/disabled badge, Test / Edit / Remove buttons.
 * 2. Add new channel section — channel type selector, guided numbered steps,
 *    dynamically-rendered form fields, Test Connection and Save Channel actions.
 * 3. Alert Rules section — table of existing rules and an Add Rule form.
 *
 * All forms follow accessibility best practices:
 * - Explicit <label for="..."> associations
 * - aria-describedby for help text and error messages
 * - aria-live="polite" regions for status announcements
 * - Focus management after async operations
 */

import { api } from "../api.js";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const CHANNEL_ICONS = {
  slack:     "💬",
  teams:     "🟦",
  pagerduty: "🔔",
  email:     "✉️",
  webhook:   "🔗",
};

const SEVERITY_BADGE = {
  critical: "bg-red-900 text-red-300",
  warning:  "bg-amber-900 text-amber-300",
  info:     "bg-blue-900 text-blue-300",
};

const CONDITION_LABELS = {
  quality_score_drop:       "Quality Score Drop",
  quality_score_below:      "Quality Score Below Threshold",
  test_failure:             "Test Failure",
  test_suite_failure:       "Test Suite Failure",
  performance_regression:   "Performance Regression",
  endpoint_down:            "Endpoint Down",
  endpoint_degraded:        "Endpoint Degraded",
  security_issue:           "Security Issue",
  accessibility_regression: "Accessibility Regression",
  availability_drop:        "Availability Drop",
  error_rate_spike:         "Error Rate Spike",
};

// ---------------------------------------------------------------------------
// Utilities
// ---------------------------------------------------------------------------

/** Escape HTML special characters to prevent XSS. */
function _esc(str) {
  return String(str ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

/** Announce a message to screen reader via aria-live region. */
function _announce(container, message) {
  const region = container.querySelector("#alert-config-announce");
  if (region) {
    region.textContent = "";
    // Force re-announcement by briefly clearing then setting
    requestAnimationFrame(() => { region.textContent = message; });
  }
}

/** Show an inline error message bound to a field via aria-describedby. */
function _showFieldError(formEl, fieldName, message) {
  const errId = `err-${fieldName}`;
  const errEl = formEl.querySelector(`#${errId}`);
  if (errEl) {
    errEl.textContent = message;
    errEl.hidden = false;
  }
  const input = formEl.querySelector(`[name="${fieldName}"]`);
  if (input) {
    input.setAttribute("aria-invalid", "true");
    input.setAttribute("aria-describedby", errId);
    input.focus();
  }
}

/** Clear all inline field errors in a form. */
function _clearFieldErrors(formEl) {
  formEl.querySelectorAll("[data-error]").forEach(el => {
    el.textContent = "";
    el.hidden = true;
  });
  formEl.querySelectorAll("[aria-invalid]").forEach(el => {
    el.removeAttribute("aria-invalid");
    el.removeAttribute("aria-describedby");
  });
}

/** Gather form field values into a plain object. */
function _collectFormValues(formEl) {
  const data = {};
  formEl.querySelectorAll("input, select, textarea").forEach(input => {
    if (input.name) {
      data[input.name] = input.type === "number" ? Number(input.value) : input.value;
    }
  });
  return data;
}

// ---------------------------------------------------------------------------
// Main entry point
// ---------------------------------------------------------------------------

/**
 * Render the full Alert Configuration page into the given container.
 *
 * @param {HTMLElement} container
 */
export async function renderAlertConfig(container) {
  container.innerHTML = `
    <div class="space-y-8" id="alert-config-root">

      <!-- Screen reader live region -->
      <div id="alert-config-announce" role="status" aria-live="polite"
           class="sr-only"></div>

      <div class="flex items-center justify-between">
        <h1 class="text-2xl font-bold text-white">Alert Channels</h1>
      </div>

      <!-- Configured channels -->
      <section aria-labelledby="channels-heading">
        <h2 id="channels-heading" class="text-lg font-semibold text-white mb-4">
          Configured Channels
        </h2>
        <div id="channels-list" aria-live="polite" aria-atomic="false"
             class="space-y-3">
          <div class="animate-pulse h-16 bg-slate-700 rounded-lg"></div>
        </div>
      </section>

      <!-- Add new channel -->
      <section aria-labelledby="add-channel-heading">
        <h2 id="add-channel-heading" class="text-lg font-semibold text-white mb-4">
          Add New Channel
        </h2>
        <div class="bg-slate-800 rounded-lg border border-slate-700 p-5">
          <div class="mb-5">
            <label for="channel-type-select"
                   class="block text-sm font-medium text-slate-300 mb-1">
              Channel Type
            </label>
            <select id="channel-type-select"
                    class="bg-slate-700 border border-slate-600 rounded-md px-3 py-2
                           text-sm text-slate-200 focus:outline-none
                           focus:ring-2 focus:ring-blue-500 w-full sm:w-auto">
              <option value="">-- Select a channel type --</option>
              <option value="slack">Slack</option>
              <option value="teams">Microsoft Teams</option>
              <option value="pagerduty">PagerDuty</option>
              <option value="email">Email (SMTP)</option>
              <option value="webhook">Custom Webhook</option>
            </select>
          </div>

          <!-- Guide + form injected here -->
          <div id="channel-setup-area"></div>
        </div>
      </section>

      <!-- Alert Rules -->
      <section aria-labelledby="rules-heading">
        <h2 id="rules-heading" class="text-lg font-semibold text-white mb-4">
          Alert Rules
        </h2>
        <div id="rules-area">
          <div class="animate-pulse h-16 bg-slate-700 rounded-lg"></div>
        </div>
      </section>

    </div>
  `;

  // Load channels and rules in parallel
  await Promise.all([
    _loadChannels(container),
    _loadRules(container),
  ]);

  // Wire up channel type selector
  const typeSelect = container.querySelector("#channel-type-select");
  typeSelect?.addEventListener("change", async () => {
    const channelType = typeSelect.value;
    const setupArea = container.querySelector("#channel-setup-area");
    if (!channelType || !setupArea) return;
    await _renderChannelSetupForm(container, setupArea, channelType);
  });
}

// ---------------------------------------------------------------------------
// Channels section
// ---------------------------------------------------------------------------

async function _loadChannels(container) {
  const listEl = container.querySelector("#channels-list");
  if (!listEl) return;

  try {
    const channels = await api.request("GET", "/alerts/channels");
    _renderChannelCards(container, listEl, channels);
  } catch (err) {
    listEl.innerHTML = `
      <p class="text-amber-400 text-sm" role="alert">
        Could not load channels: ${_esc(err.message)}
      </p>
    `;
  }
}

function _renderChannelCards(container, listEl, channels) {
  if (channels.length === 0) {
    listEl.innerHTML = `
      <p class="text-slate-400 text-sm py-4 text-center">
        No channels configured. Add one below.
      </p>
    `;
    return;
  }

  listEl.innerHTML = channels.map(ch => `
    <article class="flex items-center gap-4 bg-slate-800 rounded-lg border border-slate-700
                    px-4 py-3"
             data-channel-id="${_esc(ch.id)}"
             aria-label="Channel: ${_esc(ch.name)}">
      <span class="text-2xl" aria-hidden="true">
        ${CHANNEL_ICONS[ch.type] ?? "📡"}
      </span>
      <div class="flex-1 min-w-0">
        <p class="text-sm font-medium text-white">${_esc(ch.name)}</p>
        <p class="text-xs text-slate-400 capitalize">${_esc(ch.type)}</p>
      </div>
      <span class="${ch.enabled ? "bg-green-900 text-green-300" : "bg-slate-700 text-slate-400"}
                  px-2 py-0.5 rounded-full text-xs font-medium"
            aria-label="Status: ${ch.enabled ? "enabled" : "disabled"}">
        ${ch.enabled ? "Enabled" : "Disabled"}
      </span>
      <div class="flex items-center gap-2 shrink-0">
        <button type="button"
                data-test-id="${_esc(ch.id)}"
                data-test-type="${_esc(ch.type)}"
                class="px-3 py-1.5 text-xs font-medium bg-slate-700 hover:bg-slate-600
                       text-slate-200 rounded-md transition-colors
                       focus:outline-none focus:ring-2 focus:ring-blue-500"
                aria-label="Send test notification to ${_esc(ch.name)}">
          Test
        </button>
        <button type="button"
                data-toggle-id="${_esc(ch.id)}"
                data-toggle-enabled="${ch.enabled}"
                class="px-3 py-1.5 text-xs font-medium bg-slate-700 hover:bg-slate-600
                       text-slate-200 rounded-md transition-colors
                       focus:outline-none focus:ring-2 focus:ring-blue-500"
                aria-label="${ch.enabled ? "Disable" : "Enable"} channel ${_esc(ch.name)}">
          ${ch.enabled ? "Disable" : "Enable"}
        </button>
        <button type="button"
                data-remove-id="${_esc(ch.id)}"
                class="px-3 py-1.5 text-xs font-medium bg-red-900 hover:bg-red-800
                       text-red-300 rounded-md transition-colors
                       focus:outline-none focus:ring-2 focus:ring-red-500"
                aria-label="Remove channel ${_esc(ch.name)}">
          Remove
        </button>
      </div>
    </article>
  `).join("");

  // Bind Test buttons
  listEl.querySelectorAll("[data-test-id]").forEach(btn => {
    btn.addEventListener("click", () => _testExistingChannel(container, btn));
  });

  // Bind Enable/Disable toggle buttons
  listEl.querySelectorAll("[data-toggle-id]").forEach(btn => {
    btn.addEventListener("click", () => _toggleChannel(container, btn));
  });

  // Bind Remove buttons
  listEl.querySelectorAll("[data-remove-id]").forEach(btn => {
    btn.addEventListener("click", () => _removeChannel(container, btn));
  });
}

async function _testExistingChannel(container, btn) {
  const channelId = btn.dataset.testId;
  const channelType = btn.dataset.testType;
  btn.disabled = true;
  btn.textContent = "Testing…";

  try {
    const result = await api.request("POST", "/alerts/channels/test", {
      channel_type: channelType,
      config: {},
    });
    const msg = result.success
      ? "Test notification sent successfully."
      : `Test failed: ${result.message}`;
    _announce(container, msg);
    btn.textContent = result.success ? "Sent!" : "Failed";
  } catch (err) {
    _announce(container, `Test error: ${err.message}`);
    btn.textContent = "Error";
  } finally {
    setTimeout(() => {
      btn.disabled = false;
      btn.textContent = "Test";
    }, 3000);
  }
}

async function _toggleChannel(container, btn) {
  const channelId = btn.dataset.toggleId;
  const currentlyEnabled = btn.dataset.toggleEnabled === "true";
  btn.disabled = true;

  try {
    await api.request("PATCH", `/alerts/channels/${channelId}`, {
      enabled: !currentlyEnabled,
    });
    _announce(container, `Channel ${currentlyEnabled ? "disabled" : "enabled"}.`);
    await _loadChannels(container);
  } catch (err) {
    _announce(container, `Could not update channel: ${err.message}`);
    btn.disabled = false;
  }
}

async function _removeChannel(container, btn) {
  const channelId = btn.dataset.removeId;
  const article = btn.closest("[data-channel-id]");
  const name = article?.querySelector("p.font-medium")?.textContent ?? "this channel";

  if (!confirm(`Remove ${name}?`)) return;

  btn.disabled = true;
  try {
    await api.request("DELETE", `/alerts/channels/${channelId}`);
    _announce(container, `Channel removed.`);
    await _loadChannels(container);
  } catch (err) {
    _announce(container, `Could not remove channel: ${err.message}`);
    btn.disabled = false;
  }
}

// ---------------------------------------------------------------------------
// Add channel: setup guide + form
// ---------------------------------------------------------------------------

async function _renderChannelSetupForm(container, setupArea, channelType) {
  setupArea.innerHTML = `
    <div class="animate-pulse space-y-3">
      <div class="h-4 bg-slate-700 rounded w-1/3"></div>
      <div class="h-10 bg-slate-700 rounded w-full"></div>
    </div>
  `;

  let guide;
  try {
    const guides = await api.request("GET", "/alerts/setup-guides");
    guide = guides[channelType];
  } catch (err) {
    setupArea.innerHTML = `
      <p class="text-amber-400 text-sm" role="alert">
        Could not load setup guide: ${_esc(err.message)}
      </p>
    `;
    return;
  }

  if (!guide) {
    setupArea.innerHTML = `
      <p class="text-slate-400 text-sm">No setup guide available for this channel type.</p>
    `;
    return;
  }

  const icon = CHANNEL_ICONS[channelType] ?? "📡";
  const stepsHtml = guide.steps.map(s => `
    <li class="flex gap-3">
      <span class="shrink-0 w-6 h-6 rounded-full bg-blue-900 text-blue-300
                   flex items-center justify-center text-xs font-bold"
            aria-hidden="true">${s.step}</span>
      <div>
        <p class="text-sm font-medium text-slate-200">${_esc(s.title)}</p>
        <p class="text-xs text-slate-400 mt-0.5">${_esc(s.description)}</p>
      </div>
    </li>
  `).join("");

  const fieldsHtml = _renderFormFields(guide.fields, `add-${channelType}`);

  setupArea.innerHTML = `
    <div class="space-y-5">
      <!-- Setup steps -->
      <div>
        <h3 class="text-sm font-semibold text-slate-200 mb-3 flex items-center gap-2">
          <span aria-hidden="true">${icon}</span>
          ${_esc(guide.title)} Setup
        </h3>
        <ol class="space-y-3" aria-label="Setup steps for ${_esc(guide.title)}">
          ${stepsHtml}
        </ol>
      </div>

      <hr class="border-slate-700" />

      <!-- Channel name -->
      <div>
        <label for="channel-name-input"
               class="block text-sm font-medium text-slate-300 mb-1">
          Channel Name
          <span class="text-slate-500 font-normal ml-1">(display label)</span>
        </label>
        <input type="text"
               id="channel-name-input"
               name="channel_name_label"
               placeholder="e.g. Engineering Alerts"
               class="bg-slate-700 border border-slate-600 rounded-md px-3 py-2
                      text-sm text-slate-200 focus:outline-none
                      focus:ring-2 focus:ring-blue-500 w-full"
               aria-describedby="channel-name-help" />
        <p id="channel-name-help" class="text-xs text-slate-500 mt-1">
          A friendly name to identify this channel in the dashboard.
        </p>
        <p id="err-channel_name_label" data-error class="text-xs text-red-400 mt-1"
           hidden></p>
      </div>

      <!-- Dynamic fields from guide -->
      <div class="space-y-4" id="dynamic-fields">
        ${fieldsHtml}
      </div>

      <!-- Enabled toggle -->
      <div class="flex items-center gap-3">
        <input type="checkbox"
               id="channel-enabled-check"
               name="channel_enabled"
               checked
               class="w-4 h-4 rounded bg-slate-700 border-slate-600
                      text-blue-500 focus:ring-blue-500" />
        <label for="channel-enabled-check" class="text-sm text-slate-300">
          Enable this channel immediately
        </label>
      </div>

      <!-- Status message -->
      <div id="add-channel-status" role="status" aria-live="polite"
           class="text-sm hidden"></div>

      <!-- Actions -->
      <div class="flex flex-wrap gap-3">
        <button type="button"
                id="test-connection-btn"
                class="px-4 py-2 text-sm font-medium bg-slate-700 hover:bg-slate-600
                       text-slate-200 rounded-md transition-colors
                       focus:outline-none focus:ring-2 focus:ring-blue-500"
                aria-describedby="add-channel-status">
          Test Connection
        </button>
        <button type="button"
                id="save-channel-btn"
                class="px-4 py-2 text-sm font-medium bg-blue-600 hover:bg-blue-500
                       text-white rounded-md transition-colors
                       focus:outline-none focus:ring-2 focus:ring-blue-400">
          Save Channel
        </button>
      </div>
    </div>
  `;

  // Bind Test Connection
  setupArea.querySelector("#test-connection-btn")?.addEventListener("click", async () => {
    await _testNewChannelConnection(container, setupArea, channelType, guide.fields);
  });

  // Bind Save Channel
  setupArea.querySelector("#save-channel-btn")?.addEventListener("click", async () => {
    await _saveNewChannel(container, setupArea, channelType, guide.fields);
  });
}

/**
 * Render form input fields from a guide's fields array.
 * Each field gets a <label>, <input> (or <select>), optional help text,
 * and an aria-described error placeholder.
 */
function _renderFormFields(fields, prefix) {
  return fields.map(field => {
    const inputId = `${prefix}-${field.name}`;
    const errId   = `err-${field.name}`;
    const helpId  = `help-${field.name}`;
    const requiredAttr = field.required ? "required" : "";
    const requiredMark = field.required
      ? `<span class="text-red-400 ml-0.5" aria-label="required">*</span>`
      : "";

    let inputHtml;
    if (field.type === "select" && field.options) {
      inputHtml = `
        <select id="${inputId}"
                name="${field.name}"
                ${requiredAttr}
                aria-describedby="${helpId} ${errId}"
                class="bg-slate-700 border border-slate-600 rounded-md px-3 py-2
                       text-sm text-slate-200 focus:outline-none
                       focus:ring-2 focus:ring-blue-500 w-full">
          ${field.options.map(o => `<option value="${_esc(o)}">${_esc(o)}</option>`).join("")}
        </select>
      `;
    } else {
      const inputType = field.type === "password" ? "password"
        : field.type === "number" ? "number"
        : field.type === "email"  ? "email"
        : field.type === "url"    ? "url"
        : "text";
      inputHtml = `
        <input type="${inputType}"
               id="${inputId}"
               name="${field.name}"
               placeholder="${_esc(field.placeholder ?? "")}"
               ${requiredAttr}
               aria-describedby="${helpId} ${errId}"
               class="bg-slate-700 border border-slate-600 rounded-md px-3 py-2
                      text-sm text-slate-200 focus:outline-none
                      focus:ring-2 focus:ring-blue-500 w-full" />
      `;
    }

    return `
      <div>
        <label for="${inputId}"
               class="block text-sm font-medium text-slate-300 mb-1">
          ${_esc(field.label)}${requiredMark}
        </label>
        ${inputHtml}
        <p id="${helpId}" class="text-xs text-slate-500 mt-1 hidden"></p>
        <p id="${errId}" data-error class="text-xs text-red-400 mt-1" hidden></p>
      </div>
    `;
  }).join("");
}

async function _testNewChannelConnection(container, setupArea, channelType, fields) {
  const testBtn   = setupArea.querySelector("#test-connection-btn");
  const statusEl  = setupArea.querySelector("#add-channel-status");
  if (!testBtn || !statusEl) return;

  _clearFieldErrors(setupArea);
  const formValues = _collectFormValues(setupArea);

  // Build config from dynamic fields
  const config = {};
  fields.forEach(f => {
    if (formValues[f.name] !== undefined) config[f.name] = formValues[f.name];
  });

  testBtn.disabled = true;
  testBtn.textContent = "Testing…";
  statusEl.className = "text-sm text-slate-400";
  statusEl.hidden = false;
  statusEl.textContent = "Sending test notification…";

  try {
    const result = await api.request("POST", "/alerts/channels/test", {
      channel_type: channelType,
      config,
    });

    if (result.success) {
      statusEl.className = "text-sm text-green-400";
      statusEl.textContent = "Test notification sent successfully.";
      _announce(container, "Test notification sent successfully.");
    } else {
      statusEl.className = "text-sm text-red-400";
      statusEl.textContent = `Test failed: ${result.message}`;
      _announce(container, `Test failed: ${result.message}`);
    }
  } catch (err) {
    statusEl.className = "text-sm text-red-400";
    statusEl.textContent = `Error: ${err.message}`;
    _announce(container, `Test error: ${err.message}`);
  } finally {
    testBtn.disabled = false;
    testBtn.textContent = "Test Connection";
  }
}

async function _saveNewChannel(container, setupArea, channelType, fields) {
  const saveBtn  = setupArea.querySelector("#save-channel-btn");
  const statusEl = setupArea.querySelector("#add-channel-status");
  if (!saveBtn || !statusEl) return;

  _clearFieldErrors(setupArea);
  const formValues = _collectFormValues(setupArea);

  // Validate required fields
  let hasError = false;
  fields.forEach(f => {
    if (f.required && !formValues[f.name]) {
      _showFieldError(setupArea, f.name, `${f.label} is required.`);
      hasError = true;
    }
  });
  if (hasError) return;

  const channelName = setupArea.querySelector("#channel-name-input")?.value.trim();
  if (!channelName) {
    _showFieldError(setupArea, "channel_name_label", "Channel name is required.");
    return;
  }

  const enabled = setupArea.querySelector("#channel-enabled-check")?.checked ?? true;

  // Build config from dynamic fields
  const config = {};
  fields.forEach(f => {
    if (formValues[f.name] !== undefined) config[f.name] = formValues[f.name];
  });

  saveBtn.disabled = true;
  saveBtn.textContent = "Saving…";
  statusEl.className = "text-sm text-slate-400";
  statusEl.hidden = false;
  statusEl.textContent = "Saving channel…";

  try {
    await api.request("POST", "/alerts/channels", {
      channel_type: channelType,
      name: channelName,
      enabled,
      config,
    });

    statusEl.className = "text-sm text-green-400";
    statusEl.textContent = "Channel saved successfully.";
    _announce(container, "Channel saved successfully.");

    // Reset type selector and hide setup form
    const typeSelect = container.querySelector("#channel-type-select");
    if (typeSelect) typeSelect.value = "";
    setupArea.innerHTML = "";

    // Reload channels list
    await _loadChannels(container);

    // Move focus to channels heading for orientation
    container.querySelector("#channels-heading")?.focus();
  } catch (err) {
    statusEl.className = "text-sm text-red-400";
    statusEl.textContent = `Save failed: ${err.message}`;
    _announce(container, `Save failed: ${err.message}`);
  } finally {
    saveBtn.disabled = false;
    saveBtn.textContent = "Save Channel";
  }
}

// ---------------------------------------------------------------------------
// Alert Rules section
// ---------------------------------------------------------------------------

async function _loadRules(container) {
  const rulesArea = container.querySelector("#rules-area");
  if (!rulesArea) return;

  let channels = [];
  let rules = [];

  try {
    [channels, rules] = await Promise.all([
      api.request("GET", "/alerts/channels"),
      api.request("GET", "/alerts/rules"),
    ]);
  } catch (err) {
    rulesArea.innerHTML = `
      <p class="text-amber-400 text-sm" role="alert">
        Could not load rules: ${_esc(err.message)}
      </p>
    `;
    return;
  }

  _renderRulesSection(container, rulesArea, rules, channels);
}

function _renderRulesSection(container, rulesArea, rules, channels) {
  const rulesTableHtml = rules.length === 0
    ? `<p class="text-slate-400 text-sm py-4 text-center">No rules configured.</p>`
    : `
      <div class="overflow-x-auto rounded-lg border border-slate-700 mb-6">
        <table class="w-full text-sm" aria-label="Alert rules">
          <thead>
            <tr class="bg-slate-700">
              <th scope="col" class="px-4 py-3 text-left font-semibold text-slate-300">Name</th>
              <th scope="col" class="px-4 py-3 text-left font-semibold text-slate-300">Condition</th>
              <th scope="col" class="px-4 py-3 text-left font-semibold text-slate-300">Severity</th>
              <th scope="col" class="px-4 py-3 text-left font-semibold text-slate-300">Channels</th>
              <th scope="col" class="px-4 py-3 text-left font-semibold text-slate-300">Actions</th>
            </tr>
          </thead>
          <tbody class="divide-y divide-slate-700">
            ${rules.map(r => _renderRuleRow(r)).join("")}
          </tbody>
        </table>
      </div>
    `;

  const channelOptions = channels.map(ch =>
    `<option value="${_esc(ch.id)}">${_esc(ch.name)} (${_esc(ch.type)})</option>`
  ).join("");

  const conditionOptions = Object.entries(CONDITION_LABELS).map(([val, label]) =>
    `<option value="${_esc(val)}">${_esc(label)}</option>`
  ).join("");

  rulesArea.innerHTML = `
    ${rulesTableHtml}

    <!-- Add Rule form -->
    <details class="bg-slate-800 rounded-lg border border-slate-700">
      <summary class="px-5 py-4 cursor-pointer text-sm font-semibold text-slate-200
                      hover:text-white list-none flex items-center gap-2
                      focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
               aria-expanded="false">
        <span aria-hidden="true">+</span>
        Add Alert Rule
      </summary>
      <div class="px-5 pb-5 pt-2 space-y-4">
        <form id="add-rule-form" novalidate>

          <div class="grid grid-cols-1 sm:grid-cols-2 gap-4 mb-4">
            <!-- Rule name -->
            <div>
              <label for="rule-name-input"
                     class="block text-sm font-medium text-slate-300 mb-1">
                Rule Name
                <span class="text-red-400 ml-0.5" aria-label="required">*</span>
              </label>
              <input type="text"
                     id="rule-name-input"
                     name="rule_name"
                     placeholder="e.g. critical-quality-drop"
                     required
                     aria-describedby="err-rule_name"
                     class="bg-slate-700 border border-slate-600 rounded-md px-3 py-2
                            text-sm text-slate-200 focus:outline-none
                            focus:ring-2 focus:ring-blue-500 w-full" />
              <p id="err-rule_name" data-error class="text-xs text-red-400 mt-1"
                 hidden></p>
            </div>

            <!-- Condition type -->
            <div>
              <label for="rule-condition-select"
                     class="block text-sm font-medium text-slate-300 mb-1">
                Condition Type
                <span class="text-red-400 ml-0.5" aria-label="required">*</span>
              </label>
              <select id="rule-condition-select"
                      name="condition_type"
                      required
                      aria-describedby="err-condition_type"
                      class="bg-slate-700 border border-slate-600 rounded-md px-3 py-2
                             text-sm text-slate-200 focus:outline-none
                             focus:ring-2 focus:ring-blue-500 w-full">
                <option value="">-- Select condition --</option>
                ${conditionOptions}
              </select>
              <p id="err-condition_type" data-error class="text-xs text-red-400 mt-1"
                 hidden></p>
            </div>

            <!-- Threshold value -->
            <div>
              <label for="rule-threshold-input"
                     class="block text-sm font-medium text-slate-300 mb-1">
                Threshold Value
              </label>
              <input type="number"
                     id="rule-threshold-input"
                     name="threshold_value"
                     placeholder="e.g. 10"
                     aria-describedby="rule-threshold-help"
                     class="bg-slate-700 border border-slate-600 rounded-md px-3 py-2
                            text-sm text-slate-200 focus:outline-none
                            focus:ring-2 focus:ring-blue-500 w-full" />
              <p id="rule-threshold-help" class="text-xs text-slate-500 mt-1">
                Numeric threshold relevant to the selected condition type.
              </p>
            </div>

            <!-- Severity -->
            <div>
              <label for="rule-severity-select"
                     class="block text-sm font-medium text-slate-300 mb-1">
                Severity
                <span class="text-red-400 ml-0.5" aria-label="required">*</span>
              </label>
              <select id="rule-severity-select"
                      name="severity"
                      required
                      aria-describedby="err-severity"
                      class="bg-slate-700 border border-slate-600 rounded-md px-3 py-2
                             text-sm text-slate-200 focus:outline-none
                             focus:ring-2 focus:ring-blue-500 w-full">
                <option value="warning">Warning</option>
                <option value="critical">Critical</option>
                <option value="info">Info</option>
              </select>
              <p id="err-severity" data-error class="text-xs text-red-400 mt-1"
                 hidden></p>
            </div>
          </div>

          <!-- Channel assignment -->
          <div class="mb-4">
            <fieldset>
              <legend class="block text-sm font-medium text-slate-300 mb-2">
                Notify Channels
              </legend>
              ${channels.length === 0
                ? `<p class="text-xs text-slate-500">
                     No channels configured yet. Add a channel above first.
                   </p>`
                : `<div class="flex flex-wrap gap-3">
                    ${channels.map(ch => `
                      <label class="flex items-center gap-2 text-sm text-slate-300
                                    cursor-pointer">
                        <input type="checkbox"
                               name="notify_channels"
                               value="${_esc(ch.id)}"
                               class="w-4 h-4 rounded bg-slate-700 border-slate-600
                                      text-blue-500 focus:ring-blue-500" />
                        <span>${_esc(CHANNEL_ICONS[ch.type] ?? "📡")} ${_esc(ch.name)}</span>
                      </label>
                    `).join("")}
                   </div>`
              }
            </fieldset>
          </div>

          <!-- Status -->
          <div id="add-rule-status" role="status" aria-live="polite"
               class="text-sm hidden"></div>

          <!-- Submit -->
          <button type="submit"
                  class="px-4 py-2 text-sm font-medium bg-blue-600 hover:bg-blue-500
                         text-white rounded-md transition-colors
                         focus:outline-none focus:ring-2 focus:ring-blue-400">
            Add Rule
          </button>
        </form>
      </div>
    </details>
  `;

  // Bind rule row remove buttons
  rulesArea.querySelectorAll("[data-remove-rule-id]").forEach(btn => {
    btn.addEventListener("click", () => _removeRule(container, btn));
  });

  // Bind Add Rule form
  rulesArea.querySelector("#add-rule-form")?.addEventListener("submit", async (e) => {
    e.preventDefault();
    await _saveNewRule(container, rulesArea, e.currentTarget);
  });
}

function _renderRuleRow(rule) {
  const condLabel = CONDITION_LABELS[rule.condition_type] ?? rule.condition_type ?? "—";
  const sevBadge  = SEVERITY_BADGE[rule.severity] ?? SEVERITY_BADGE.info;

  return `
    <tr data-rule-id="${_esc(rule.id)}">
      <td class="px-4 py-3 text-slate-200 font-medium">${_esc(rule.name ?? rule.id)}</td>
      <td class="px-4 py-3 text-slate-400">${_esc(condLabel)}</td>
      <td class="px-4 py-3">
        <span class="${sevBadge} px-2 py-0.5 rounded-full text-xs font-medium capitalize">
          ${_esc(rule.severity ?? "warning")}
        </span>
      </td>
      <td class="px-4 py-3 text-slate-400 text-xs">
        ${Array.isArray(rule.channels) && rule.channels.length > 0
          ? rule.channels.map(c => _esc(c)).join(", ")
          : "—"}
      </td>
      <td class="px-4 py-3">
        <button type="button"
                data-remove-rule-id="${_esc(rule.id)}"
                class="px-2 py-1 text-xs font-medium bg-red-900 hover:bg-red-800
                       text-red-300 rounded transition-colors
                       focus:outline-none focus:ring-2 focus:ring-red-500"
                aria-label="Remove rule ${_esc(rule.name ?? rule.id)}">
          Remove
        </button>
      </td>
    </tr>
  `;
}

async function _removeRule(container, btn) {
  const ruleId = btn.dataset.removeRuleId;
  btn.disabled = true;
  try {
    await api.request("DELETE", `/alerts/rules/${ruleId}`);
    _announce(container, "Rule removed.");
    await _loadRules(container);
  } catch (err) {
    _announce(container, `Could not remove rule: ${err.message}`);
    btn.disabled = false;
  }
}

async function _saveNewRule(container, rulesArea, formEl) {
  const statusEl = rulesArea.querySelector("#add-rule-status");
  _clearFieldErrors(formEl);

  const ruleName     = formEl.querySelector("[name=rule_name]")?.value.trim();
  const conditionType = formEl.querySelector("[name=condition_type]")?.value;
  const thresholdVal = formEl.querySelector("[name=threshold_value]")?.value;
  const severity     = formEl.querySelector("[name=severity]")?.value ?? "warning";

  let hasError = false;
  if (!ruleName) {
    _showFieldError(formEl, "rule_name", "Rule name is required.");
    hasError = true;
  }
  if (!conditionType) {
    _showFieldError(formEl, "condition_type", "Condition type is required.");
    hasError = true;
  }
  if (hasError) return;

  // Collect checked channel IDs
  const notifyChannels = [...formEl.querySelectorAll("[name=notify_channels]:checked")]
    .map(cb => cb.value);

  // Build threshold dict from threshold value
  const threshold = thresholdVal !== "" && thresholdVal !== undefined
    ? { value: Number(thresholdVal) }
    : {};

  const submitBtn = formEl.querySelector("[type=submit]");
  if (submitBtn) { submitBtn.disabled = true; submitBtn.textContent = "Saving…"; }
  if (statusEl) { statusEl.hidden = false; statusEl.textContent = "Saving rule…"; }

  try {
    await api.request("POST", "/alerts/rules", {
      name: ruleName,
      condition_type: conditionType,
      severity,
      channels: notifyChannels,
      threshold,
    });

    if (statusEl) {
      statusEl.className = "text-sm text-green-400";
      statusEl.textContent = "Rule added.";
    }
    _announce(container, "Alert rule added.");
    formEl.reset();
    await _loadRules(container);
  } catch (err) {
    if (statusEl) {
      statusEl.className = "text-sm text-red-400";
      statusEl.textContent = `Save failed: ${err.message}`;
    }
    _announce(container, `Save failed: ${err.message}`);
  } finally {
    if (submitBtn) { submitBtn.disabled = false; submitBtn.textContent = "Add Rule"; }
  }
}
