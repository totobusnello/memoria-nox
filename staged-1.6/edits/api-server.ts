#!/usr/bin/env node
/**
 * nox-mem API Server — lightweight HTTP API for dashboard consumption
 * Port 18800, CORS enabled, JSON responses
 */
import { createServer, IncomingMessage, ServerResponse } from "http";
import { getDb, closeDb } from "./db.js";
import { searchHybrid } from "./search.js";
import { getGraphStats, formatEntityQuery } from "./knowledge-graph.js";
import { profileAllAgents, mergeCrossKnowledgeGraphs, findPath } from "./cross-agent-v2.js";
import { getStats } from "./stats.js";
import { reflect, getReflectCacheStats } from "./reflect.js";
import { crystallize, validateProcedure, listProcedures, type ValidationOptions } from "./crystallize.js";
import { execFileSync } from "child_process";

const PORT = parseInt(process.env.NOX_API_PORT || "18800");

function json(res: ServerResponse, data: unknown, status = 200) {
  res.writeHead(status, {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
  });
  res.end(JSON.stringify(data));
}

function parseQuery(url: string): Record<string, string> {
  const idx = url.indexOf("?");
  if (idx === -1) return {};
  const params: Record<string, string> = {};
  for (const part of url.substring(idx + 1).split("&")) {
    const [k, v] = part.split("=");
    if (k) params[decodeURIComponent(k)] = decodeURIComponent(v || "");
  }
  return params;
}

function readBody(req: IncomingMessage, limit = 65536): Promise<string> {
  return new Promise((resolve, reject) => {
    let data = "";
    let size = 0;
    req.on("data", (chunk) => {
      size += chunk.length;
      if (size > limit) { reject(new Error("Payload too large")); req.destroy(); return; }
      data += chunk;
    });
    req.on("end", () => resolve(data));
    req.on("error", reject);
  });
}

async function readJson<T = unknown>(req: IncomingMessage): Promise<T> {
  const raw = await readBody(req);
  if (!raw) return {} as T;
  try { return JSON.parse(raw) as T; }
  catch { throw new Error("Invalid JSON body"); }
}

const ALLOWED_SERVICES = new Set([
  "openclaw-gateway",
  "nox-mem-watcher",
  "nox-mem-api",
  "ollama",
  "tailscaled",
  "relayplane-proxy",
]);

function serviceStatus(name: string): boolean {
  if (!ALLOWED_SERVICES.has(name)) return false;
  try {
    const out = execFileSync("systemctl", ["is-active", name], { encoding: "utf-8" });
    return out.trim() === "active";
  } catch { return false; }
}

async function handleRequest(req: IncomingMessage, res: ServerResponse) {
  const url = req.url || "/";
  const path = url.split("?")[0];

  if (req.method === "OPTIONS") { json(res, {}); return; }

  try {
    switch (path) {
      case "/api/health": {
        const db = getDb();
        const total = (db.prepare("SELECT COUNT(*) as c FROM chunks").get() as { c: number }).c;
        const types = db.prepare("SELECT chunk_type, COUNT(*) as c FROM chunks GROUP BY chunk_type ORDER BY c DESC").all();
        const consolidated = db.prepare("SELECT COUNT(*) as c FROM consolidated_files WHERE status = 1").get() as { c: number };
        const failed = db.prepare("SELECT COUNT(*) as c FROM consolidated_files WHERE status = -1").get() as { c: number };
        const lastCon = db.prepare("SELECT MAX(processed_at) as d FROM consolidated_files").get() as { d: string | null };
        // Count ONLY vec_chunk_map entries whose chunk_id still exists in chunks.
        // Previously this counted all map rows (including orphans from consolidation/dedup
        // that never cleaned vec_chunk_map), silently claiming embeddings we don't have.
        let embedded = 0;
        let embeddingOrphans = 0;
        try {
          const sqliteVec = await import("sqlite-vec"); sqliteVec.load(db);
          embedded = (db.prepare(
            "SELECT COUNT(DISTINCT m.chunk_id) as c FROM vec_chunk_map m INNER JOIN chunks c ON c.id = m.chunk_id"
          ).get() as { c: number }).c;
          const totalMap = (db.prepare("SELECT COUNT(*) as c FROM vec_chunk_map").get() as { c: number }).c;
          embeddingOrphans = Math.max(0, totalMap - embedded);
        } catch {
          try {
            embedded = (db.prepare(
              "SELECT COUNT(DISTINCT m.chunk_id) as c FROM vec_chunk_map m INNER JOIN chunks c ON c.id = m.chunk_id"
            ).get() as { c: number }).c;
          } catch {}
        }

        // KG stats
        let kgEntities = 0, kgRelations = 0;
        try {
          kgEntities = (db.prepare("SELECT COUNT(*) as c FROM kg_entities").get() as { c: number }).c;
          kgRelations = (db.prepare("SELECT COUNT(*) as c FROM kg_relations").get() as { c: number }).c;
        } catch {}

        // Reflect cache stats (entries, total hits, top queries)
        let reflectCache: { entries: number; total_hits: number; top_queries: Array<{ query: string; hits: number; last_hit_at: string | null }> } = {
          entries: 0, total_hits: 0, top_queries: []
        };
        try { reflectCache = getReflectCacheStats(); } catch {}

        // Procedures count
        let procedures = 0;
        try {
          procedures = (db.prepare("SELECT COUNT(*) as c FROM chunks WHERE chunk_type = 'procedure'").get() as { c: number }).c;
        } catch {}

        // Fase 1.6 — search telemetry (last 24h rolling window)
        let searchTelemetry: {
          count_24h: number;
          avg_results: number;
          semantic_ratio: number;
          p95_latency_ms: number;
          expansion_enabled: boolean;
          skip_reasons: Record<string, number>;
        } = {
          count_24h: 0, avg_results: 0, semantic_ratio: 0, p95_latency_ms: 0,
          expansion_enabled: true, skip_reasons: {},
        };
        try {
          const agg = db.prepare(`
            SELECT COUNT(*) as c,
                   COALESCE(AVG(results_count), 0) as avg_r,
                   COALESCE(AVG(has_semantic), 0) as sem_ratio
            FROM search_telemetry
            WHERE ts >= datetime('now', '-24 hours')
          `).get() as { c: number; avg_r: number; sem_ratio: number };
          const latencies = db.prepare(`
            SELECT latency_ms FROM search_telemetry
            WHERE ts >= datetime('now', '-24 hours')
            ORDER BY latency_ms ASC
          `).all() as Array<{ latency_ms: number }>;
          const p95Idx = Math.max(0, Math.floor(latencies.length * 0.95) - 1);
          const p95 = latencies.length > 0 ? latencies[p95Idx].latency_ms : 0;
          const reasons = db.prepare(`
            SELECT expansion_skipped_reason as r, COUNT(*) as c
            FROM search_telemetry
            WHERE ts >= datetime('now', '-24 hours') AND expansion_skipped_reason IS NOT NULL
            GROUP BY expansion_skipped_reason
          `).all() as Array<{ r: string; c: number }>;
          const cfg = db.prepare("SELECT value FROM meta WHERE key = 'expansion_enabled'").get() as { value: string } | undefined;
          searchTelemetry = {
            count_24h: agg.c,
            avg_results: Math.round(agg.avg_r * 100) / 100,
            semantic_ratio: Math.round(agg.sem_ratio * 1000) / 1000,
            p95_latency_ms: p95,
            expansion_enabled: !cfg || (cfg.value !== "false" && cfg.value !== "0"),
            skip_reasons: Object.fromEntries(reasons.map((r) => [r.r, r.c])),
          };
        } catch {}

        const services = {
          "openclaw-gateway": serviceStatus("openclaw-gateway"),
          "nox-mem-watcher": serviceStatus("nox-mem-watcher"),
          "ollama": serviceStatus("ollama"),
          "tailscaled": serviceStatus("tailscaled"),
        };

        json(res, {
          chunks: { total, types },
          consolidation: { done: consolidated.c, failed: failed.c, last: lastCon.d },
          vectorCoverage: { embedded, total, orphans: embeddingOrphans },
          knowledgeGraph: { entities: kgEntities, relations: kgRelations },
          reflectCache,
          procedures,
          searchTelemetry,
          services,
          dbSizeMB: Math.round((db.prepare("SELECT page_count * page_size as s FROM pragma_page_count(), pragma_page_size()").get() as { s: number }).s / 1024 / 1024 * 10) / 10,
        });
        break;
      }

      case "/api/agents": {
        json(res, profileAllAgents());
        break;
      }

      case "/api/kg": {
        const db = getDb();
        try {
          const entities = db.prepare("SELECT id, name, entity_type as type, mention_count as mentions FROM kg_entities ORDER BY mention_count DESC LIMIT 200").all();
          const relations = db.prepare(`
            SELECT e1.name as source, r.relation_type as relation, e2.name as target, r.confidence
            FROM kg_relations r
            JOIN kg_entities e1 ON e1.id = r.source_entity_id
            JOIN kg_entities e2 ON e2.id = r.target_entity_id
            ORDER BY r.confidence DESC LIMIT 500
          `).all();
          json(res, { entities, relations });
        } catch { json(res, { entities: [], relations: [] }); }
        break;
      }

      case "/api/kg/path": {
        const q = parseQuery(url);
        if (!q.from || !q.to) { json(res, { error: "from and to required" }, 400); break; }
        const result = findPath(q.from, q.to);
        json(res, { path: result });
        break;
      }

      case "/api/search": {
        const q = parseQuery(url);
        if (!q.q) { json(res, { error: "q parameter required" }, 400); break; }
        const limit = parseInt(q.limit || "10");
        const results = await searchHybrid(q.q, limit);
        json(res, results);
        break;
      }

      case "/api/cross-kg": {
        json(res, mergeCrossKnowledgeGraphs());
        break;
      }

      case "/api/reflect": {
        const q = parseQuery(url);
        if (!q.q) { json(res, { error: "q parameter required" }, 400); break; }
        const noCache = q.nocache === "1" || q.nocache === "true";
        const result = await reflect(q.q, { noCache });
        json(res, result);
        break;
      }

      case "/api/procedures": {
        json(res, { procedures: listProcedures() });
        break;
      }

      case "/api/crystallize": {
        if (req.method !== "POST") { json(res, { error: "POST required" }, 405); break; }
        const body = await readJson<{
          title?: string; steps?: string[]; agent?: string;
          tags?: string[]; preconditions?: string[];
        }>(req);
        if (!body.title || !Array.isArray(body.steps) || body.steps.length === 0) {
          json(res, { error: "title and steps[] required" }, 400); break;
        }
        const id = await crystallize({
          title: body.title,
          steps: body.steps,
          agent: body.agent,
          tags: body.tags,
          preconditions: body.preconditions,
        });
        json(res, { id, ok: true });
        break;
      }

      case "/api/crystallize/validate": {
        if (req.method !== "POST") { json(res, { error: "POST required" }, 405); break; }
        const q = parseQuery(url);
        const id = parseInt(q.id || "0");
        if (!id) { json(res, { error: "id query param required" }, 400); break; }
        // Optional structured validation payload
        let opts: ValidationOptions = {};
        try {
          const body = await readJson<ValidationOptions>(req);
          if (body && typeof body === "object") {
            if (body.outcome && ["success","failure","partial"].includes(body.outcome)) opts.outcome = body.outcome;
            if (typeof body.agent === "string") opts.agent = body.agent;
            if (typeof body.notes === "string") opts.notes = body.notes;
          }
        } catch { /* no body, use defaults */ }
        try { validateProcedure(id, opts); json(res, { id, ok: true, applied: opts }); }
        catch (err) { json(res, { error: String(err) }, 404); }
        break;
      }

      default:
        json(res, {
          error: "Not found",
          endpoints: [
            "/api/health", "/api/agents", "/api/kg", "/api/kg/path",
            "/api/search", "/api/cross-kg", "/api/reflect",
            "/api/procedures", "/api/crystallize", "/api/crystallize/validate"
          ]
        }, 404);
    }
  } catch (err) {
    json(res, { error: String(err) }, 500);
  }
}

const server = createServer(handleRequest);
server.listen(PORT, "0.0.0.0", () => {
  console.log(`[nox-mem-api] Listening on http://0.0.0.0:${PORT}`);
});
