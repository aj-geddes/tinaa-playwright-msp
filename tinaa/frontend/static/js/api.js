/**
 * api.js — TINAA MSP API client.
 *
 * Thin fetch wrapper for all /api/v1/* endpoints.
 * All methods return Promises that resolve to parsed JSON or reject with an
 * Error whose message contains the HTTP status code.
 */

export class TINAAClient {
  /**
   * @param {string} baseUrl - API base URL (default: /api/v1)
   */
  constructor(baseUrl = "/api/v1") {
    this.baseUrl = baseUrl;
  }

  /**
   * Execute an HTTP request and return parsed JSON.
   *
   * @param {string} method  - HTTP method (GET, POST, PATCH, DELETE, etc.)
   * @param {string} path    - Path relative to baseUrl (starts with /)
   * @param {object|null} body - Request body (serialised to JSON)
   * @returns {Promise<any>}
   */
  async request(method, path, body = null) {
    const opts = {
      method,
      headers: { "Content-Type": "application/json" },
    };
    if (body !== null) {
      opts.body = JSON.stringify(body);
    }
    const resp = await fetch(`${this.baseUrl}${path}`, opts);
    if (!resp.ok) {
      const detail = await resp.text().catch(() => "");
      throw new Error(`API error ${resp.status}: ${detail || resp.statusText}`);
    }
    // 204 No Content — return null
    if (resp.status === 204) return null;
    return resp.json();
  }

  // ---------------------------------------------------------------- Products

  /** @returns {Promise<Array>} list of products */
  listProducts() {
    return this.request("GET", "/products");
  }

  /**
   * @param {string} productId
   * @returns {Promise<object>}
   */
  getProduct(productId) {
    return this.request("GET", `/products/${productId}`);
  }

  /**
   * @param {object} data - { name, description, repository_url, environments }
   * @returns {Promise<object>}
   */
  createProduct(data) {
    return this.request("POST", "/products", data);
  }

  /**
   * @param {string} productId
   * @param {object} data
   * @returns {Promise<object>}
   */
  updateProduct(productId, data) {
    return this.request("PATCH", `/products/${productId}`, data);
  }

  /**
   * @param {string} productId
   * @returns {Promise<null>}
   */
  deleteProduct(productId) {
    return this.request("DELETE", `/products/${productId}`);
  }

  // ------------------------------------------------------------ Environments

  /**
   * @param {string} productId
   * @returns {Promise<Array>}
   */
  listEnvironments(productId) {
    return this.request("GET", `/products/${productId}/environments`);
  }

  /**
   * @param {string} productId
   * @param {object} data - { name, base_url, env_type, monitoring_interval_seconds }
   * @returns {Promise<object>}
   */
  createEnvironment(productId, data) {
    return this.request("POST", `/products/${productId}/environments`, data);
  }

  // --------------------------------------------------------------- Endpoints

  /**
   * @param {string} productId
   * @param {string} envId
   * @returns {Promise<Array>}
   */
  listEndpoints(productId, envId) {
    return this.request(
      "GET",
      `/products/${productId}/environments/${envId}/endpoints`
    );
  }

  /**
   * @param {string} productId
   * @param {string} envId
   * @param {object} data - { path, method, endpoint_type, performance_budget_ms }
   * @returns {Promise<object>}
   */
  createEndpoint(productId, envId, data) {
    return this.request(
      "POST",
      `/products/${productId}/environments/${envId}/endpoints`,
      data
    );
  }

  // ----------------------------------------------------------------- Quality

  /**
   * @param {string} productId
   * @param {string} [environment="production"]
   * @returns {Promise<object>}
   */
  getQualityScore(productId, environment = "production") {
    return this.request(
      "GET",
      `/products/${productId}/quality?environment=${environment}`
    );
  }

  /**
   * @param {string} productId
   * @param {number} [days=30]
   * @returns {Promise<Array>}
   */
  getQualityHistory(productId, days = 30) {
    return this.request(
      "GET",
      `/products/${productId}/quality/history?days=${days}`
    );
  }

  /**
   * @param {string} productId
   * @returns {Promise<object>}
   */
  getQualityReport(productId) {
    return this.request("GET", `/products/${productId}/quality/report`);
  }

  /**
   * @param {string} productId
   * @param {string} [environment="production"]
   * @returns {Promise<object>}
   */
  evaluateQualityGate(productId, environment = "production") {
    return this.request(
      "GET",
      `/products/${productId}/quality/gate?environment=${environment}`
    );
  }

  // --------------------------------------------------------------- Playbooks

  /**
   * @param {string} productId
   * @returns {Promise<Array>}
   */
  listPlaybooks(productId) {
    return this.request("GET", `/products/${productId}/playbooks`);
  }

  /**
   * @param {string} productId
   * @param {object} data
   * @returns {Promise<object>}
   */
  createPlaybook(productId, data) {
    return this.request("POST", `/products/${productId}/playbooks`, data);
  }

  /**
   * @param {string} playbookId
   * @returns {Promise<object>}
   */
  getPlaybook(playbookId) {
    return this.request("GET", `/playbooks/${playbookId}`);
  }

  /**
   * @param {string} playbookId
   * @param {object} data
   * @returns {Promise<object>}
   */
  updatePlaybook(playbookId, data) {
    return this.request("PATCH", `/playbooks/${playbookId}`, data);
  }

  /**
   * @param {string} playbookId
   * @returns {Promise<null>}
   */
  deletePlaybook(playbookId) {
    return this.request("DELETE", `/playbooks/${playbookId}`);
  }

  /**
   * @param {string} playbookId
   * @param {string} [environment]
   * @returns {Promise<object>}
   */
  executePlaybook(playbookId, environment = null) {
    const qs = environment ? `?environment=${environment}` : "";
    return this.request("POST", `/playbooks/${playbookId}/execute${qs}`);
  }

  /**
   * @param {object} data - playbook definition to validate
   * @returns {Promise<{valid: boolean, errors: string[]}>}
   */
  validatePlaybook(data) {
    return this.request("POST", "/playbooks/validate", data);
  }

  // --------------------------------------------------------------- Test Runs

  /**
   * @param {string} productId
   * @returns {Promise<Array>}
   */
  listTestRuns(productId) {
    return this.request("GET", `/products/${productId}/runs`);
  }

  /**
   * @param {string} runId
   * @returns {Promise<object>}
   */
  getTestRun(runId) {
    return this.request("GET", `/runs/${runId}`);
  }

  /**
   * @param {string} productId
   * @param {object} data
   * @returns {Promise<object>}
   */
  triggerTestRun(productId, data) {
    return this.request("POST", `/products/${productId}/runs`, data);
  }

  // ----------------------------------------------------------------- Metrics

  /**
   * @param {string} productId
   * @param {object} params - { hours, metric_type }
   * @returns {Promise<object>}
   */
  getMetrics(productId, params = {}) {
    const qs = new URLSearchParams(params).toString();
    return this.request("GET", `/products/${productId}/metrics${qs ? "?" + qs : ""}`);
  }

  /**
   * @param {string} endpointId
   * @param {object} params - { hours, metric_type }
   * @returns {Promise<object>}
   */
  getEndpointMetrics(endpointId, params = {}) {
    const qs = new URLSearchParams(params).toString();
    return this.request("GET", `/endpoints/${endpointId}/metrics${qs ? "?" + qs : ""}`);
  }

  /**
   * @param {string} productId
   * @returns {Promise<Array>}
   */
  getBaselines(productId) {
    return this.request("GET", `/products/${productId}/metrics/baselines`);
  }

  /**
   * @param {string} productId
   * @param {number} [hours=24]
   * @returns {Promise<Array>}
   */
  getAnomalies(productId, hours = 24) {
    return this.request(
      "GET",
      `/products/${productId}/metrics/anomalies?hours=${hours}`
    );
  }

  // ------------------------------------------------------------------ Health

  /** @returns {Promise<object>} */
  getHealth() {
    return fetch("/health").then((r) => r.json());
  }
}

/** Singleton API client instance shared across all modules. */
export const api = new TINAAClient();
