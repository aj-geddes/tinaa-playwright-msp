/**
 * products.js — Products listing page.
 *
 * Dedicated page for browsing, searching, and managing all registered products.
 * Distinct from the Dashboard which shows a summary overview.
 */

import { api } from "../api.js";

/**
 * Render the products list page.
 * @param {HTMLElement} container
 */
export async function renderProducts(container) {
  let products = [];
  try {
    products = await api.listProducts();
    if (!Array.isArray(products)) products = [];
  } catch {
    products = [];
  }

  container.innerHTML = `
    <div class="space-y-6">
      <!-- Page heading -->
      <div class="flex items-center justify-between flex-wrap gap-4">
        <div>
          <h1 class="text-2xl font-bold text-white">Products</h1>
          <p class="text-sm text-slate-400 mt-1">
            All applications registered for quality management.
          </p>
        </div>
        <button
          id="btn-register-product"
          class="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700
                 text-white text-sm font-medium rounded-lg transition-colors
                 focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-400
                 focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900"
          aria-label="Register a new product"
        >
          <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor"
               stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <line x1="12" y1="5" x2="12" y2="19"/><line x1="5" y1="12" x2="19" y2="12"/>
          </svg>
          Register Product
        </button>
      </div>

      <!-- Search & filter bar -->
      <div class="flex items-center gap-3 flex-wrap">
        <div class="relative flex-1 min-w-[200px] max-w-md">
          <svg class="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400"
               viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
               stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>
          </svg>
          <input
            id="product-search"
            type="search"
            placeholder="Search products..."
            class="w-full pl-10 pr-4 py-2 bg-slate-800 border border-slate-700 rounded-lg
                   text-slate-200 text-sm placeholder-slate-500
                   focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            aria-label="Search products by name"
          />
        </div>
        <div class="flex items-center gap-2">
          <label for="status-filter" class="text-sm text-slate-400">Status:</label>
          <select
            id="status-filter"
            class="px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-sm text-slate-200
                   focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">All</option>
            <option value="active">Active</option>
            <option value="paused">Paused</option>
            <option value="archived">Archived</option>
          </select>
        </div>
        <div class="flex items-center gap-2">
          <label for="sort-by" class="text-sm text-slate-400">Sort:</label>
          <select
            id="sort-by"
            class="px-3 py-2 bg-slate-800 border border-slate-700 rounded-lg text-sm text-slate-200
                   focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="name">Name</option>
            <option value="score">Quality Score</option>
            <option value="updated">Last Updated</option>
          </select>
        </div>
      </div>

      <!-- Product count -->
      <p class="text-sm text-slate-500" aria-live="polite" id="product-count">
        ${products.length} product${products.length !== 1 ? "s" : ""} registered
      </p>

      <!-- Products grid -->
      <div id="products-grid" role="list" aria-label="Registered products">
        ${products.length > 0 ? _renderProductCards(products) : _renderEmptyState()}
      </div>
    </div>
  `;

  // Wire up register button
  const registerBtn = container.querySelector("#btn-register-product");
  if (registerBtn) {
    registerBtn.addEventListener("click", () => {
      window.location.hash = "#/settings";
    });
  }

  // Wire up search
  const searchInput = container.querySelector("#product-search");
  if (searchInput) {
    searchInput.addEventListener("input", () => {
      _filterProducts(container, products, searchInput.value);
    });
  }
}

/**
 * Render product cards grid.
 */
function _renderProductCards(products) {
  return `
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      ${products.map((p) => _renderProductCard(p)).join("")}
    </div>
  `;
}

/**
 * Render a single product card.
 */
function _renderProductCard(product) {
  const score = product.quality_score ?? "—";
  const scoreColor =
    score === "—" ? "text-slate-400"
    : score >= 85 ? "text-green-400"
    : score >= 70 ? "text-blue-400"
    : score >= 55 ? "text-yellow-400"
    : "text-red-400";

  const statusBadge = {
    active: "bg-green-500/20 text-green-400",
    paused: "bg-yellow-500/20 text-yellow-400",
    archived: "bg-slate-500/20 text-slate-400",
  }[product.status] || "bg-slate-500/20 text-slate-400";

  const envCount = product.environments?.length ?? 0;

  return `
    <a href="#/products/${product.id || product.slug}"
       class="block bg-slate-800 border border-slate-700 rounded-xl p-5 hover:border-blue-500/50
              hover:bg-slate-800/80 transition-all group
              focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-400
              focus-visible:ring-offset-2 focus-visible:ring-offset-slate-900"
       role="listitem"
       aria-label="${product.name}, quality score ${score}">
      <div class="flex items-start justify-between mb-3">
        <div>
          <h3 class="text-lg font-semibold text-white group-hover:text-blue-400 transition-colors">
            ${_escapeHtml(product.name)}
          </h3>
          <p class="text-xs text-slate-500 mt-0.5">${_escapeHtml(product.slug || "")}</p>
        </div>
        <span class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium ${statusBadge}">
          ${product.status || "active"}
        </span>
      </div>

      ${product.description ? `<p class="text-sm text-slate-400 mb-3 line-clamp-2">${_escapeHtml(product.description)}</p>` : ""}

      <div class="flex items-center justify-between pt-3 border-t border-slate-700/50">
        <div class="flex items-center gap-4 text-sm">
          <div class="flex items-center gap-1.5">
            <span class="text-slate-500">Score:</span>
            <span class="font-semibold ${scoreColor}">${score}</span>
          </div>
          <div class="flex items-center gap-1.5">
            <span class="text-slate-500">Envs:</span>
            <span class="text-slate-300">${envCount}</span>
          </div>
        </div>
        <svg class="w-4 h-4 text-slate-600 group-hover:text-blue-400 transition-colors"
             viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"
             stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
          <polyline points="9 18 15 12 9 6"/>
        </svg>
      </div>
    </a>
  `;
}

/**
 * Render empty state when no products are registered.
 */
function _renderEmptyState() {
  return `
    <div class="text-center py-16">
      <svg class="w-16 h-16 mx-auto text-slate-600 mb-4" viewBox="0 0 24 24" fill="none"
           stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"
           aria-hidden="true">
        <rect x="2" y="3" width="20" height="14" rx="2" ry="2"/>
        <line x1="8" y1="21" x2="16" y2="21"/>
        <line x1="12" y1="17" x2="12" y2="21"/>
      </svg>
      <h3 class="text-lg font-semibold text-slate-300 mb-2">No products registered</h3>
      <p class="text-sm text-slate-500 mb-6 max-w-md mx-auto">
        Products represent the applications TINAA manages quality for.
        Register your first product to start monitoring quality, running tests,
        and tracking performance.
      </p>
      <div class="flex items-center justify-center gap-3">
        <a href="#/integrations"
           class="inline-flex items-center gap-2 px-4 py-2 bg-blue-600 hover:bg-blue-700
                  text-white text-sm font-medium rounded-lg transition-colors
                  focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-400">
          <svg class="w-4 h-4" viewBox="0 0 24 24" fill="none" stroke="currentColor"
               stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
            <path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/>
            <path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>
          </svg>
          Import from GitHub
        </a>
        <a href="#/settings"
           class="inline-flex items-center gap-2 px-4 py-2 bg-slate-700 hover:bg-slate-600
                  text-slate-200 text-sm font-medium rounded-lg transition-colors
                  focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-400">
          Register Manually
        </a>
      </div>
    </div>
  `;
}

/**
 * Filter products based on search text.
 */
function _filterProducts(container, products, query) {
  const grid = container.querySelector("#products-grid");
  const countEl = container.querySelector("#product-count");
  const q = query.toLowerCase().trim();

  if (!q) {
    grid.innerHTML = products.length > 0 ? _renderProductCards(products) : _renderEmptyState();
    countEl.textContent = `${products.length} product${products.length !== 1 ? "s" : ""} registered`;
    return;
  }

  const filtered = products.filter(
    (p) =>
      p.name.toLowerCase().includes(q) ||
      (p.slug || "").toLowerCase().includes(q) ||
      (p.description || "").toLowerCase().includes(q)
  );

  grid.innerHTML = filtered.length > 0
    ? _renderProductCards(filtered)
    : `<p class="text-center text-slate-500 py-8">No products match "${_escapeHtml(query)}"</p>`;
  countEl.textContent = `${filtered.length} of ${products.length} product${products.length !== 1 ? "s" : ""}`;
}

/**
 * Escape HTML to prevent XSS.
 */
function _escapeHtml(str) {
  const div = document.createElement("div");
  div.appendChild(document.createTextNode(str));
  return div.innerHTML;
}
