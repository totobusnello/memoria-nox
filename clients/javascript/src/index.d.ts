/**
 * TypeScript declarations for @noxmem/client.
 */

export interface HealthSnapshot {
  chunksTotal: number;
  vecCoverage: number;
  salienceMode: string;
  kgEntities: number;
  kgRelations: number;
  uptime: string;
  indicators: Record<string, unknown>;
}

export interface SearchResult {
  id: string;
  score: number;
  sourceFile: string;
  snippet: string;
  section: string | null;
  pain: number | null;
}

export interface AnswerResponse {
  answer: string;
  citations: SearchResult[];
  sessionId: string | null;
  latencyMs: number | null;
}

export interface NoxMemClientOptions {
  baseUrl?: string;
  timeout?: number;
  fetch?: typeof globalThis.fetch;
}

export interface SearchOptions {
  limit?: number;
  userId?: string | null;
}

export interface AnswerOptions {
  sessionId?: string | null;
  options?: Record<string, unknown>;
}

export interface KgSearchOptions {
  limit?: number;
}

/**
 * Error thrown when the API returns a non-OK HTTP status.
 */
export class NoxMemError extends Error {
  readonly statusCode: number;
  constructor(statusCode: number, message: string);
}

/**
 * Client for the nox-mem hybrid memory API.
 *
 * @example
 * import { NoxMemClient } from "@noxmem/client";
 * const client = new NoxMemClient();
 * const results = await client.search("pain-weighted retrieval");
 */
export class NoxMemClient {
  readonly baseUrl: string;
  readonly timeout: number;

  constructor(options?: NoxMemClientOptions);

  /**
   * Retrieve API health metrics.
   */
  health(): Promise<HealthSnapshot>;

  /**
   * Hybrid BM25 + semantic search over memory chunks.
   */
  search(query: string, options?: SearchOptions): Promise<SearchResult[]>;

  /**
   * Generate a grounded answer from memory.
   */
  answer(query: string, options?: AnswerOptions): Promise<AnswerResponse>;

  /**
   * Search knowledge graph entities by name.
   */
  kgSearch(entity: string, options?: KgSearchOptions): Promise<Record<string, unknown>[]>;

  /**
   * Find shortest path between two KG entities.
   */
  kgPath(source: string, target: string): Promise<Record<string, unknown>[]>;

  /**
   * Return raw observability/health JSON.
   */
  observabilityHealth(): Promise<Record<string, unknown>>;
}
