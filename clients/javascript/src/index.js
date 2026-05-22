/**
 * @module @noxmem/client
 * JavaScript/TypeScript client for the nox-mem hybrid memory API.
 * Requires Node 20+ or any modern browser with native fetch.
 */

const DEFAULT_BASE_URL = "http://187.77.234.79:18802";
const MAX_RETRIES = 3;
const RETRY_BACKOFF_BASE_MS = 500;

/**
 * Error thrown when the API returns a non-OK response.
 */
export class NoxMemError extends Error {
  /**
   * @param {number} statusCode
   * @param {string} message
   */
  constructor(statusCode, message) {
    super(`HTTP ${statusCode}: ${message}`);
    this.name = "NoxMemError";
    this.statusCode = statusCode;
  }
}

/**
 * @param {number} ms
 * @returns {Promise<void>}
 */
function sleep(ms) {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Client for the nox-mem hybrid memory API.
 *
 * @example
 * import { NoxMemClient } from "@noxmem/client";
 * const client = new NoxMemClient();
 * const results = await client.search("pain-weighted retrieval");
 * console.log(results[0].snippet);
 */
export class NoxMemClient {
  /**
   * @param {object} [options]
   * @param {string} [options.baseUrl="http://187.77.234.79:18802"]
   * @param {number} [options.timeout=30000] - Timeout in milliseconds.
   * @param {typeof globalThis.fetch} [options.fetch] - Custom fetch implementation.
   */
  constructor({
    baseUrl = DEFAULT_BASE_URL,
    timeout = 30000,
    fetch: fetchImpl = globalThis.fetch,
  } = {}) {
    this.baseUrl = baseUrl.replace(/\/$/, "");
    this.timeout = timeout;
    this._fetch = fetchImpl;
  }

  /**
   * Build a full URL from an API path.
   * @param {string} path
   * @returns {string}
   */
  _url(path) {
    return `${this.baseUrl}/${path.replace(/^\//, "")}`;
  }

  /**
   * Execute an HTTP request with retry on 5xx errors.
   * @param {string} method
   * @param {string} path
   * @param {object} [opts]
   * @param {Record<string,string|number>} [opts.params]
   * @param {unknown} [opts.body]
   * @returns {Promise<unknown>}
   */
  async _request(method, path, { params, body } = {}) {
    let url = this._url(path);
    if (params) {
      const qs = new URLSearchParams(
        Object.entries(params)
          .filter(([, v]) => v != null)
          .map(([k, v]) => [k, String(v)])
      );
      url = `${url}?${qs}`;
    }

    let lastError;
    for (let attempt = 0; attempt < MAX_RETRIES; attempt++) {
      const controller = new AbortController();
      const timer = setTimeout(() => controller.abort(), this.timeout);

      try {
        const init = {
          method,
          signal: controller.signal,
          headers: { "Content-Type": "application/json" },
        };
        if (body !== undefined) {
          init.body = JSON.stringify(body);
        }

        const resp = await this._fetch(url, init);
        clearTimeout(timer);

        if (resp.status >= 500) {
          if (attempt < MAX_RETRIES - 1) {
            await sleep(RETRY_BACKOFF_BASE_MS * 2 ** attempt);
            continue;
          }
          const text = await resp.text();
          throw new NoxMemError(resp.status, text.slice(0, 200));
        }

        if (!resp.ok) {
          const text = await resp.text();
          throw new NoxMemError(resp.status, text.slice(0, 200));
        }

        return await resp.json();
      } catch (err) {
        clearTimeout(timer);
        if (err instanceof NoxMemError) throw err;
        lastError = err;
        if (attempt < MAX_RETRIES - 1) {
          await sleep(RETRY_BACKOFF_BASE_MS * 2 ** attempt);
        }
      }
    }

    throw new NoxMemError(0, `Request failed after ${MAX_RETRIES} attempts: ${lastError?.message}`);
  }

  // -----------------------------------------------------------------------
  // Public API
  // -----------------------------------------------------------------------

  /**
   * Retrieve API health metrics.
   * @returns {Promise<HealthSnapshot>}
   */
  async health() {
    const data = await this._request("GET", "/api/health");
    return {
      chunksTotal: data.chunksTotal ?? 0,
      vecCoverage: data.vectorCoverage ?? 0,
      salienceMode: data.salienceMode ?? "unknown",
      kgEntities: data.kgEntities ?? 0,
      kgRelations: data.kgRelations ?? 0,
      uptime: data.uptime ?? "",
      indicators: data.indicators ?? {},
    };
  }

  /**
   * Hybrid BM25 + semantic search over memory chunks.
   * @param {string} query
   * @param {object} [options]
   * @param {number} [options.limit=5]
   * @param {string|null} [options.userId=null]
   * @returns {Promise<SearchResult[]>}
   */
  async search(query, { limit = 5, userId = null } = {}) {
    const params = { q: query, limit };
    if (userId) params.userId = userId;
    const data = await this._request("GET", "/api/search", { params });
    const raw = Array.isArray(data) ? data : (data.results ?? []);
    return raw.map((r) => ({
      id: String(r.id ?? ""),
      score: r.score ?? 0,
      sourceFile: r.sourceFile ?? r.source_file ?? "",
      snippet: r.snippet ?? r.content ?? "",
      section: r.section ?? null,
      pain: r.pain ?? null,
    }));
  }

  /**
   * Generate a grounded answer from memory.
   * @param {string} query
   * @param {object} [options]
   * @param {string|null} [options.sessionId=null]
   * @param {object} [options.options={}]
   * @returns {Promise<AnswerResponse>}
   */
  async answer(query, { sessionId = null, options = {} } = {}) {
    const body = { query, ...options };
    if (sessionId) body.sessionId = sessionId;
    const data = await this._request("POST", "/api/answer", { body });
    const rawCitations = data.citations ?? data.sources ?? [];
    return {
      answer: data.answer ?? "",
      citations: rawCitations.map((c) => ({
        id: String(c.id ?? ""),
        score: c.score ?? 0,
        sourceFile: c.sourceFile ?? c.source_file ?? "",
        snippet: c.snippet ?? c.content ?? "",
        section: c.section ?? null,
        pain: c.pain ?? null,
      })),
      sessionId: data.sessionId ?? data.session_id ?? null,
      latencyMs: data.latencyMs ?? data.latency_ms ?? null,
    };
  }

  /**
   * Search knowledge graph entities by name.
   * @param {string} entity
   * @param {object} [options]
   * @param {number} [options.limit=10]
   * @returns {Promise<object[]>}
   */
  async kgSearch(entity, { limit = 10 } = {}) {
    const data = await this._request("GET", "/api/kg", { params: { q: entity, limit } });
    return Array.isArray(data) ? data : (data.entities ?? []);
  }

  /**
   * Find shortest path between two KG entities.
   * @param {string} source
   * @param {string} target
   * @returns {Promise<object[]>}
   */
  async kgPath(source, target) {
    const data = await this._request("GET", "/api/kg/path", { params: { source, target } });
    return Array.isArray(data) ? data : (data.path ?? []);
  }

  /**
   * Return raw observability/health JSON.
   * @returns {Promise<object>}
   */
  async observabilityHealth() {
    return this._request("GET", "/api/health");
  }
}

/**
 * @typedef {object} HealthSnapshot
 * @property {number} chunksTotal
 * @property {number} vecCoverage
 * @property {string} salienceMode
 * @property {number} kgEntities
 * @property {number} kgRelations
 * @property {string} uptime
 * @property {object} indicators
 */

/**
 * @typedef {object} SearchResult
 * @property {string} id
 * @property {number} score
 * @property {string} sourceFile
 * @property {string} snippet
 * @property {string|null} section
 * @property {number|null} pain
 */

/**
 * @typedef {object} AnswerResponse
 * @property {string} answer
 * @property {SearchResult[]} citations
 * @property {string|null} sessionId
 * @property {number|null} latencyMs
 */
