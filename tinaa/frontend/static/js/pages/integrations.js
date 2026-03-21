/**
 * integrations.js — GitHub and Alert Channels integration setup page.
 *
 * Renders:
 * - GitHub tab: PAT setup wizard, GitHub App setup, connected repo list
 * - Alert Channels tab: placeholder for future alert channel configuration
 */

import { api } from "../api.js";

// ---------------------------------------------------------------------------
// Escape helper (shared across all render functions)
// ---------------------------------------------------------------------------

function _esc(str) {
  return String(str ?? "")
    .replace(/&/g, "&amp;")
    .replace(/"/g, "&quot;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;");
}

// ---------------------------------------------------------------------------
// Page entry point
// ---------------------------------------------------------------------------

export async function renderIntegrations(container) {
  container.innerHTML = `
    <div class="space-y-6" id="integrations-root">
      <h1 class="text-2xl font-bold text-white">Integrations</h1>

      <!-- Tabs -->
      <div role="tablist" aria-label="Integration categories" id="int-tabs"
           class="flex gap-1 border-b border-slate-700 flex-wrap">
        ${["GitHub", "Alert Channels"].map((label, i) => `
          <button
            role="tab"
            id="int-tab-${i}"
            aria-selected="${i === 0}"
            aria-controls="int-panel"
            data-tab-idx="${i}"
            class="px-4 py-2 text-sm font-medium border-b-2 -mb-px transition-colors
                   focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500
                   ${i === 0
                     ? "border-blue-500 text-white"
                     : "border-transparent text-slate-400 hover:text-white hover:border-slate-500"}"
          >${_esc(label)}</button>
        `).join("")}
      </div>

      <div id="int-panel" role="tabpanel" aria-live="polite"></div>
    </div>
  `;

  const panel = container.querySelector("#int-panel");
  const PANELS = [
    () => _renderGitHubTab(panel),
    () => _renderAlertChannelsTab(panel),
  ];

  container.querySelectorAll("[role=tab][data-tab-idx]").forEach((tab, i) => {
    tab.addEventListener("click", () => {
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

  PANELS[0]();
}

// ---------------------------------------------------------------------------
// GitHub tab
// ---------------------------------------------------------------------------

async function _renderGitHubTab(panel) {
  panel.innerHTML = `<div class="flex items-center justify-center py-8">
    <div class="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-400"></div>
  </div>`;

  let status = { configured: false, type: null, user: null };
  let setupGuide = { pat: { steps: [], required_permissions: [] }, app: { steps: [], required_permissions: [] } };

  try {
    [status, setupGuide] = await Promise.all([
      api.request("GET", "/integrations/github/status"),
      api.request("GET", "/integrations/github/setup-guide"),
    ]);
  } catch {
    // If either call fails, render with defaults (not configured)
  }

  panel.innerHTML = `
    <div class="space-y-6" id="github-tab">

      <!-- Status banner -->
      ${_renderStatusBanner(status)}

      <!-- Setup wizard (hidden when connected) -->
      <div id="github-setup-wizard" class="${status.configured ? "hidden" : ""}">
        <h2 class="text-lg font-semibold text-white mb-4">Connect GitHub</h2>

        <!-- PAT card -->
        <div class="rounded-lg border border-slate-700 bg-slate-800 overflow-hidden mb-4">
          <button
            id="pat-card-toggle"
            aria-expanded="true"
            aria-controls="pat-card-body"
            class="w-full flex items-center justify-between px-5 py-4
                   text-left focus:outline-none focus-visible:ring-2
                   focus-visible:ring-inset focus-visible:ring-blue-500"
          >
            <div>
              <span class="font-semibold text-white text-sm">Personal Access Token</span>
              <p class="text-xs text-slate-400 mt-0.5">Recommended for individuals getting started</p>
            </div>
            <svg id="pat-chevron" xmlns="http://www.w3.org/2000/svg" class="w-4 h-4 text-slate-400 transition-transform"
                 viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
                 aria-hidden="true" focusable="false">
              <polyline points="18 15 12 9 6 15"/>
            </svg>
          </button>

          <div id="pat-card-body" class="px-5 pb-5 border-t border-slate-700">
            ${_renderPATGuideSteps(setupGuide.pat.steps)}
            ${_renderPATForm()}
          </div>
        </div>

        <!-- GitHub App card -->
        <div class="rounded-lg border border-slate-700 bg-slate-800 overflow-hidden">
          <button
            id="app-card-toggle"
            aria-expanded="false"
            aria-controls="app-card-body"
            class="w-full flex items-center justify-between px-5 py-4
                   text-left focus:outline-none focus-visible:ring-2
                   focus-visible:ring-inset focus-visible:ring-blue-500"
          >
            <div>
              <span class="font-semibold text-white text-sm">GitHub App</span>
              <p class="text-xs text-slate-400 mt-0.5">Recommended for organizations</p>
            </div>
            <svg id="app-chevron" xmlns="http://www.w3.org/2000/svg" class="w-4 h-4 text-slate-400 transition-transform rotate-180"
                 viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
                 aria-hidden="true" focusable="false">
              <polyline points="18 15 12 9 6 15"/>
            </svg>
          </button>

          <div id="app-card-body" class="px-5 pb-5 border-t border-slate-700 hidden">
            ${_renderAppGuideSteps(setupGuide.app.steps)}
            ${_renderAppForm()}
          </div>
        </div>
      </div>

      <!-- Repo list (shown after connection) -->
      <div id="github-repos-section" class="${status.configured ? "" : "hidden"}">
        <div class="flex items-center justify-between mb-4">
          <h2 class="text-lg font-semibold text-white">Your Repositories</h2>
          <button
            id="disconnect-github-btn"
            class="text-xs text-red-400 hover:text-red-300 focus:outline-none
                   focus-visible:ring-2 focus-visible:ring-red-400 rounded px-2 py-1"
          >Disconnect</button>
        </div>
        <div id="repo-grid" class="grid gap-4 sm:grid-cols-2 xl:grid-cols-3">
          <div class="flex items-center justify-center py-8 col-span-full">
            <div class="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-400"></div>
          </div>
        </div>
      </div>

    </div>
  `;

  _bindGitHubTabEvents(panel, status);

  if (status.configured) {
    await _loadRepos(panel);
  }
}

// ---------------------------------------------------------------------------
// Status banner
// ---------------------------------------------------------------------------

function _renderStatusBanner(status) {
  if (status.configured) {
    const user = status.user;
    const label = status.type === "app" ? "GitHub App" : "Personal Access Token";
    return `
      <div class="flex items-center gap-3 rounded-lg border border-green-700 bg-green-900/30 px-4 py-3"
           role="status" aria-live="polite">
        ${user?.avatar_url
          ? `<img src="${_esc(user.avatar_url)}" alt="" class="w-8 h-8 rounded-full" aria-hidden="true">`
          : `<div class="w-8 h-8 rounded-full bg-green-700 flex items-center justify-center text-green-200 text-xs font-bold">${_esc(user?.login?.[0] ?? "G").toUpperCase()}</div>`
        }
        <div>
          <p class="text-sm font-medium text-green-300">
            Connected via ${_esc(label)}
            ${user?.login ? `as <strong>${_esc(user.login)}</strong>` : ""}
          </p>
          ${user?.name ? `<p class="text-xs text-green-400">${_esc(user.name)}</p>` : ""}
        </div>
        <span class="ml-auto flex h-2 w-2 rounded-full bg-green-400" aria-hidden="true"></span>
      </div>
    `;
  }
  return `
    <div class="flex items-center gap-3 rounded-lg border border-slate-600 bg-slate-800 px-4 py-3"
         role="status" aria-live="polite">
      <span class="flex h-2 w-2 rounded-full bg-slate-500" aria-hidden="true"></span>
      <p class="text-sm text-slate-400">GitHub is not connected. Configure a token below to get started.</p>
    </div>
  `;
}

// ---------------------------------------------------------------------------
// PAT guide steps
// ---------------------------------------------------------------------------

function _renderPATGuideSteps(steps) {
  if (!steps.length) return "";
  return `
    <ol class="mt-4 mb-5 space-y-3 text-sm" aria-label="Setup steps">
      ${steps.map((s) => `
        <li class="flex gap-3">
          <span class="flex-none flex items-center justify-center w-5 h-5 rounded-full
                       bg-blue-600 text-white text-xs font-bold shrink-0 mt-0.5"
                aria-label="Step ${_esc(String(s.step))}">
            ${_esc(String(s.step))}
          </span>
          <div>
            <p class="font-medium text-slate-200">${_esc(s.title)}</p>
            <p class="text-slate-400 mt-0.5">${_esc(s.description)}${
              s.url
                ? ` <a href="${_esc(s.url)}" target="_blank" rel="noopener noreferrer"
                        class="text-blue-400 hover:underline focus:outline-none
                               focus-visible:ring-2 focus-visible:ring-blue-400 rounded">
                       Open GitHub Settings
                     </a>`
                : ""
            }</p>
          </div>
        </li>
      `).join("")}
    </ol>
  `;
}

// ---------------------------------------------------------------------------
// PAT form
// ---------------------------------------------------------------------------

function _renderPATForm() {
  return `
    <form id="pat-form" novalidate>
      <div class="space-y-4">
        <div>
          <label for="pat-token-input" class="block text-sm font-medium text-slate-300 mb-1">
            Personal Access Token
          </label>
          <div class="flex gap-2">
            <div class="relative flex-1">
              <input
                id="pat-token-input"
                type="password"
                name="token"
                autocomplete="off"
                spellcheck="false"
                placeholder="ghp_xxxxxxxxxxxxxxxxxxxx"
                aria-describedby="pat-token-help pat-verify-status"
                class="w-full rounded-md bg-slate-900 border border-slate-600 text-white px-3 py-2 text-sm
                       font-mono placeholder-slate-500
                       focus:outline-none focus:border-blue-500 focus-visible:ring-2 focus-visible:ring-blue-500"
              >
              <button
                type="button"
                id="pat-toggle-visibility"
                aria-label="Show token"
                aria-pressed="false"
                class="absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-white
                       focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 rounded"
              >
                <svg id="pat-eye-icon" xmlns="http://www.w3.org/2000/svg" class="w-4 h-4" viewBox="0 0 24 24"
                     fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true" focusable="false">
                  <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z"/>
                  <circle cx="12" cy="12" r="3"/>
                </svg>
              </button>
            </div>
            <button
              type="button"
              id="verify-pat-btn"
              class="flex-none px-4 py-2 rounded-md bg-slate-700 text-white text-sm font-medium
                     hover:bg-slate-600 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-500
                     disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Verify
            </button>
          </div>
          <p id="pat-token-help" class="mt-1 text-xs text-slate-500">
            Requires: Contents (read), Deployments (read), Environments (read), Pull Requests (read)
          </p>
        </div>

        <!-- Verify result banner -->
        <div id="pat-verify-status" role="alert" aria-live="polite" class="hidden"></div>

        <!-- Save button (shown after successful verify) -->
        <button
          type="submit"
          id="save-pat-btn"
          class="hidden w-full px-4 py-2 rounded-md bg-blue-600 text-white text-sm font-semibold
                 hover:bg-blue-500 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-400
                 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Save &amp; Connect
        </button>
      </div>
    </form>
  `;
}

// ---------------------------------------------------------------------------
// GitHub App guide steps
// ---------------------------------------------------------------------------

function _renderAppGuideSteps(steps) {
  if (!steps.length) return "";
  return `
    <ol class="mt-4 mb-5 space-y-3 text-sm" aria-label="GitHub App setup steps">
      ${steps.map((s) => `
        <li class="flex gap-3">
          <span class="flex-none flex items-center justify-center w-5 h-5 rounded-full
                       bg-slate-600 text-white text-xs font-bold shrink-0 mt-0.5"
                aria-label="Step ${_esc(String(s.step))}">
            ${_esc(String(s.step))}
          </span>
          <div>
            <p class="font-medium text-slate-200">${_esc(s.title)}</p>
            <p class="text-slate-400 mt-0.5">${_esc(s.description)}</p>
          </div>
        </li>
      `).join("")}
    </ol>
  `;
}

// ---------------------------------------------------------------------------
// GitHub App form
// ---------------------------------------------------------------------------

function _renderAppForm() {
  return `
    <form id="app-form" novalidate>
      <div class="space-y-4">
        <div>
          <label for="app-id-input" class="block text-sm font-medium text-slate-300 mb-1">
            App ID
          </label>
          <input
            id="app-id-input"
            type="text"
            name="app_id"
            autocomplete="off"
            placeholder="123456"
            aria-describedby="app-id-help"
            class="w-full rounded-md bg-slate-900 border border-slate-600 text-white px-3 py-2 text-sm
                   focus:outline-none focus:border-blue-500 focus-visible:ring-2 focus-visible:ring-blue-500"
          >
          <p id="app-id-help" class="mt-1 text-xs text-slate-500">Found in your GitHub App settings page.</p>
        </div>

        <div>
          <label for="app-private-key-input" class="block text-sm font-medium text-slate-300 mb-1">
            Private Key (PEM)
          </label>
          <textarea
            id="app-private-key-input"
            name="private_key"
            rows="6"
            autocomplete="off"
            spellcheck="false"
            placeholder="-----BEGIN RSA PRIVATE KEY-----&#10;...&#10;-----END RSA PRIVATE KEY-----"
            aria-describedby="app-key-help"
            class="w-full rounded-md bg-slate-900 border border-slate-600 text-white px-3 py-2 text-sm
                   font-mono resize-y
                   focus:outline-none focus:border-blue-500 focus-visible:ring-2 focus-visible:ring-blue-500"
          ></textarea>
          <p id="app-key-help" class="mt-1 text-xs text-slate-500">
            Paste the full contents of the .pem file downloaded from GitHub.
          </p>
        </div>

        <div>
          <label for="app-webhook-secret-input" class="block text-sm font-medium text-slate-300 mb-1">
            Webhook Secret
          </label>
          <input
            id="app-webhook-secret-input"
            type="password"
            name="webhook_secret"
            autocomplete="off"
            placeholder="Your webhook secret"
            class="w-full rounded-md bg-slate-900 border border-slate-600 text-white px-3 py-2 text-sm
                   focus:outline-none focus:border-blue-500 focus-visible:ring-2 focus-visible:ring-blue-500"
          >
        </div>

        <!-- App setup status -->
        <div id="app-setup-status" role="alert" aria-live="polite" class="hidden"></div>

        <button
          type="submit"
          class="w-full px-4 py-2 rounded-md bg-blue-600 text-white text-sm font-semibold
                 hover:bg-blue-500 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-400
                 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Configure GitHub App
        </button>
      </div>
    </form>
  `;
}

// ---------------------------------------------------------------------------
// Repo grid
// ---------------------------------------------------------------------------

async function _loadRepos(panel) {
  const grid = panel.querySelector("#repo-grid");
  if (!grid) return;

  try {
    const repos = await api.request("GET", "/integrations/github/repos");
    if (!repos.length) {
      grid.innerHTML = `
        <p class="col-span-full text-sm text-slate-400 text-center py-6">
          No repositories found. Make sure your token has the required permissions.
        </p>
      `;
      return;
    }
    grid.innerHTML = repos.map((repo) => _renderRepoCard(repo)).join("");
    _bindRepoImportEvents(grid);
  } catch (err) {
    grid.innerHTML = `
      <div class="col-span-full rounded-md border border-red-700 bg-red-900/30 px-4 py-3" role="alert">
        <p class="text-sm text-red-300">Failed to load repositories: ${_esc(err.message)}</p>
      </div>
    `;
  }
}

function _renderRepoCard(repo) {
  const langColors = {
    Python: "bg-blue-500",
    JavaScript: "bg-yellow-400",
    TypeScript: "bg-blue-400",
    Go: "bg-cyan-400",
    Rust: "bg-orange-500",
    Ruby: "bg-red-500",
    Java: "bg-orange-400",
    "C#": "bg-purple-500",
    PHP: "bg-indigo-400",
  };
  const langColor = langColors[repo.language] || "bg-slate-500";

  return `
    <article
      class="rounded-lg border border-slate-700 bg-slate-800 p-4 flex flex-col gap-3"
      data-repo="${_esc(repo.full_name)}"
    >
      <div class="flex items-start gap-2">
        <div class="flex-1 min-w-0">
          <h3 class="text-sm font-semibold text-white truncate" title="${_esc(repo.full_name)}">
            <a href="${_esc(repo.html_url)}" target="_blank" rel="noopener noreferrer"
               class="hover:underline focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-400 rounded">
              ${_esc(repo.full_name)}
            </a>
          </h3>
          ${repo.description
            ? `<p class="text-xs text-slate-400 mt-0.5 line-clamp-2">${_esc(repo.description)}</p>`
            : ""}
        </div>
        ${repo.private
          ? `<span class="flex-none text-xs text-slate-400 border border-slate-600 rounded px-1.5 py-0.5">Private</span>`
          : ""}
      </div>

      <div class="flex items-center gap-3 text-xs text-slate-400">
        ${repo.language
          ? `<span class="flex items-center gap-1">
               <span class="w-2 h-2 rounded-full ${langColor}" aria-hidden="true"></span>
               ${_esc(repo.language)}
             </span>`
          : ""}
        <span>Branch: ${_esc(repo.default_branch || "main")}</span>
      </div>

      <div class="mt-auto">
        <button
          type="button"
          class="import-repo-btn w-full px-3 py-1.5 rounded-md bg-blue-600 text-white text-xs font-medium
                 hover:bg-blue-500 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-400
                 disabled:opacity-50 disabled:cursor-not-allowed"
          data-repo="${_esc(repo.full_name)}"
          aria-label="Import ${_esc(repo.full_name)} to TINAA"
        >
          Import to TINAA
        </button>
      </div>
    </article>
  `;
}

function _bindRepoImportEvents(grid) {
  grid.querySelectorAll(".import-repo-btn").forEach((btn) => {
    btn.addEventListener("click", async () => {
      const repoName = btn.dataset.repo;
      btn.disabled = true;
      btn.textContent = "Importing…";

      try {
        const result = await api.request("POST", "/integrations/github/repos/import", {
          repo_full_name: repoName,
        });

        btn.textContent = "Imported";
        btn.classList.remove("bg-blue-600", "hover:bg-blue-500");
        btn.classList.add("bg-green-700", "cursor-default");

        const card = btn.closest("article");
        if (card && result.product_slug) {
          const link = document.createElement("a");
          link.href = `#/products/${result.product_slug}`;
          link.className =
            "block text-center text-xs text-green-400 hover:underline mt-1 " +
            "focus:outline-none focus-visible:ring-2 focus-visible:ring-green-400 rounded";
          link.textContent = "View product";
          btn.insertAdjacentElement("afterend", link);
        }
      } catch (err) {
        btn.disabled = false;
        btn.textContent = "Import to TINAA";

        const card = btn.closest("article");
        if (card) {
          const errEl = document.createElement("p");
          errEl.className = "text-xs text-red-400 mt-1";
          errEl.textContent = `Import failed: ${err.message}`;
          btn.insertAdjacentElement("afterend", errEl);
          setTimeout(() => errEl.remove(), 5000);
        }
      }
    });
  });
}

// ---------------------------------------------------------------------------
// Event bindings for the GitHub tab
// ---------------------------------------------------------------------------

function _bindGitHubTabEvents(panel, initialStatus) {
  // Collapsible card toggles
  const patToggle = panel.querySelector("#pat-card-toggle");
  const patBody = panel.querySelector("#pat-card-body");
  const patChevron = panel.querySelector("#pat-chevron");

  const appToggle = panel.querySelector("#app-card-toggle");
  const appBody = panel.querySelector("#app-card-body");
  const appChevron = panel.querySelector("#app-chevron");

  if (patToggle) {
    patToggle.addEventListener("click", () => {
      const expanded = patToggle.getAttribute("aria-expanded") === "true";
      patToggle.setAttribute("aria-expanded", String(!expanded));
      patBody?.classList.toggle("hidden", expanded);
      patChevron?.classList.toggle("rotate-180", expanded);
    });
  }

  if (appToggle) {
    appToggle.addEventListener("click", () => {
      const expanded = appToggle.getAttribute("aria-expanded") === "true";
      appToggle.setAttribute("aria-expanded", String(!expanded));
      appBody?.classList.toggle("hidden", expanded);
      appChevron?.classList.toggle("rotate-180", expanded);
    });
  }

  // PAT token show/hide toggle
  const patInput = panel.querySelector("#pat-token-input");
  const patVisToggle = panel.querySelector("#pat-toggle-visibility");

  if (patVisToggle && patInput) {
    patVisToggle.addEventListener("click", () => {
      const isPassword = patInput.type === "password";
      patInput.type = isPassword ? "text" : "password";
      patVisToggle.setAttribute("aria-label", isPassword ? "Hide token" : "Show token");
      patVisToggle.setAttribute("aria-pressed", String(isPassword));
    });
  }

  // Verify PAT
  const verifyBtn = panel.querySelector("#verify-pat-btn");
  const verifyStatus = panel.querySelector("#pat-verify-status");
  const saveBtn = panel.querySelector("#save-pat-btn");

  if (verifyBtn && patInput) {
    verifyBtn.addEventListener("click", async () => {
      const token = patInput.value.trim();
      if (!token) {
        _showStatus(verifyStatus, "error", "Please enter a token first.");
        return;
      }

      verifyBtn.disabled = true;
      verifyBtn.textContent = "Verifying…";
      _hideStatus(verifyStatus);

      try {
        const result = await api.request("POST", "/integrations/github/pat/verify", { token });

        if (result.valid) {
          const user = result.user;
          _showStatus(
            verifyStatus,
            "success",
            `Token valid. Connected as ${user.login}${user.name ? ` (${user.name})` : ""}.` +
            ` ${result.repos.length} repo(s) accessible.`,
            user.avatar_url
          );
          if (saveBtn) saveBtn.classList.remove("hidden");
        }
      } catch (err) {
        _showStatus(verifyStatus, "error", `Token invalid: ${err.message}`);
        if (saveBtn) saveBtn.classList.add("hidden");
      } finally {
        verifyBtn.disabled = false;
        verifyBtn.textContent = "Verify";
      }
    });
  }

  // Save PAT
  const patForm = panel.querySelector("#pat-form");
  if (patForm) {
    patForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const token = patInput?.value.trim();
      if (!token) return;

      if (saveBtn) {
        saveBtn.disabled = true;
        saveBtn.textContent = "Saving…";
      }

      try {
        await api.request("POST", "/integrations/github/pat/save", { token });
        // Reload the tab to show the connected state
        await _renderGitHubTab(panel);
      } catch (err) {
        _showStatus(verifyStatus, "error", `Failed to save token: ${err.message}`);
        if (saveBtn) {
          saveBtn.disabled = false;
          saveBtn.textContent = "Save & Connect";
        }
      }
    });
  }

  // GitHub App form
  const appForm = panel.querySelector("#app-form");
  const appStatus = panel.querySelector("#app-setup-status");

  if (appForm) {
    appForm.addEventListener("submit", async (e) => {
      e.preventDefault();
      const fd = new FormData(appForm);
      const appId = String(fd.get("app_id") ?? "").trim();
      const privateKey = String(fd.get("private_key") ?? "").trim();
      const webhookSecret = String(fd.get("webhook_secret") ?? "").trim();

      if (!appId || !privateKey || !webhookSecret) {
        _showStatus(appStatus, "error", "All fields are required.");
        return;
      }

      const submitBtn = appForm.querySelector("[type=submit]");
      if (submitBtn) {
        submitBtn.disabled = true;
        submitBtn.textContent = "Configuring…";
      }

      try {
        await api.request("POST", "/integrations/github/app/setup", {
          app_id: appId,
          private_key: privateKey,
          webhook_secret: webhookSecret,
        });
        await _renderGitHubTab(panel);
      } catch (err) {
        _showStatus(appStatus, "error", `Configuration failed: ${err.message}`);
        if (submitBtn) {
          submitBtn.disabled = false;
          submitBtn.textContent = "Configure GitHub App";
        }
      }
    });
  }

  // Disconnect
  const disconnectBtn = panel.querySelector("#disconnect-github-btn");
  if (disconnectBtn) {
    disconnectBtn.addEventListener("click", async () => {
      // Clear by saving empty state (backend: post empty, then refresh)
      // For now reload to "not configured" by refreshing the tab
      await _renderGitHubTab(panel);
    });
  }
}

// ---------------------------------------------------------------------------
// Status helpers
// ---------------------------------------------------------------------------

function _showStatus(el, type, message, avatarUrl) {
  if (!el) return;
  const isSuccess = type === "success";
  el.className = [
    "flex items-center gap-2 rounded-md px-3 py-2 text-sm",
    isSuccess
      ? "border border-green-700 bg-green-900/30 text-green-300"
      : "border border-red-700 bg-red-900/30 text-red-300",
  ].join(" ");
  el.removeAttribute("hidden");
  el.classList.remove("hidden");

  el.innerHTML = `
    ${avatarUrl
      ? `<img src="${_esc(avatarUrl)}" alt="" class="w-5 h-5 rounded-full flex-none" aria-hidden="true">`
      : `<span aria-hidden="true">${isSuccess ? "✓" : "✗"}</span>`
    }
    <span>${_esc(message)}</span>
  `;
}

function _hideStatus(el) {
  if (!el) return;
  el.className = "hidden";
  el.innerHTML = "";
}

// ---------------------------------------------------------------------------
// Alert Channels tab (placeholder for future implementation)
// ---------------------------------------------------------------------------

function _renderAlertChannelsTab(panel) {
  panel.innerHTML = `
    <div class="rounded-lg border border-slate-700 bg-slate-800 p-8 text-center">
      <div class="inline-flex items-center justify-center w-12 h-12 rounded-full bg-slate-700 mb-4"
           aria-hidden="true">
        <svg xmlns="http://www.w3.org/2000/svg" class="w-6 h-6 text-slate-400" viewBox="0 0 24 24"
             fill="none" stroke="currentColor" stroke-width="2">
          <path d="M22 17H2a3 3 0 0 0 3-3V9a7 7 0 0 1 14 0v5a3 3 0 0 0 3 3z"/>
          <path d="M13.73 21a2 2 0 0 1-3.46 0"/>
        </svg>
      </div>
      <h2 class="text-base font-semibold text-white mb-2">Alert Channels</h2>
      <p class="text-sm text-slate-400 max-w-sm mx-auto">
        Configure Slack, Microsoft Teams, PagerDuty, and email notification channels.
        This feature is coming soon.
      </p>
    </div>
  `;
}
