#!/usr/bin/env node
/**
 * graphify-ingest.ts — Fase 2: ingest graphify output into nox-mem
 *
 * Converte graph.json (graphify) em chunks no nox-mem com rate-limit.
 * Cada node graphify vira 1 chunk com chunk_type='graph_node', source_type='external',
 * is_compiled=1. Edges são embutidas no chunk_text como "Links: rel → target".
 *
 * Rate-limit: batch 500 chunks, pause 5min (300s) entre batches.
 * Janela proibida: 22:30-01:30 BRT (não concorre com nightly-maintenance).
 *
 * Usage:
 *   node dist/graphify-ingest.js <graph.json path> <repo-name>
 *
 * Example:
 *   node dist/graphify-ingest.js /root/vault/projetos/Granix-App/graphify-out/graph.json Granix-App
 */

import { readFileSync } from "fs";
import { getDb, closeDb } from "./db.js";

// Load sqlite-vec extension before accessing DB (required because vec_chunks is a virtual table)
async function loadVec() {
  try {
    const sqliteVec = await import("sqlite-vec");
    const db = getDb();
    sqliteVec.load(db);
  } catch (err) {
    console.warn("[graphify-ingest] sqlite-vec load failed (continuing without semantic index):", (err as Error).message);
  }
}

interface GraphNode {
  id: string;
  label: string;
  file_type?: string;
  source_file?: string;
  source_location?: string | null;
  source_url?: string | null;
  author?: string | null;
  community?: number;
}

interface GraphEdge {
  source: string;
  target: string;
  relation: string;
  confidence: string;
  confidence_score: number;
}

interface GraphJson {
  nodes?: GraphNode[];
  links?: GraphEdge[]; // networkx export uses "links"
  edges?: GraphEdge[];
}

function isInForbiddenWindow(): boolean {
  const now = new Date();
  // BRT = UTC-3
  const brtHour = (now.getUTCHours() - 3 + 24) % 24;
  const brtMin = now.getUTCMinutes();
  const totalMin = brtHour * 60 + brtMin;
  // 22:30 = 1350, 01:30 = 90 (wraps past midnight)
  return totalMin >= 1350 || totalMin < 90;
}

async function ingestGraph(
  graphPath: string,
  repoName: string,
  opts: { batchSize?: number; pauseMs?: number; dryRun?: boolean } = {},
): Promise<number> {
  const batchSize = opts.batchSize ?? 500;
  const pauseMs = opts.pauseMs ?? 300_000;
  const dryRun = opts.dryRun ?? false;

  if (isInForbiddenWindow()) {
    console.error("[graphify-ingest] ❌ Currently in forbidden window (22:30-01:30 BRT). Aborting to avoid conflict with nightly-maintenance.");
    process.exit(1);
  }

  await loadVec();

  const raw = readFileSync(graphPath, "utf-8");
  const graph = JSON.parse(raw) as GraphJson;
  const nodes = graph.nodes ?? [];
  const edges = graph.edges ?? graph.links ?? [];

  console.log(`[graphify-ingest] Loaded ${nodes.length} nodes, ${edges.length} edges from ${graphPath}`);
  console.log(`[graphify-ingest] Repo: ${repoName}`);
  console.log(`[graphify-ingest] Rate limit: batch=${batchSize}, pause=${pauseMs / 1000}s`);
  if (dryRun) console.log(`[graphify-ingest] DRY RUN — no writes`);

  // Build adjacency for context in chunk_text
  const adj = new Map<string, GraphEdge[]>();
  for (const e of edges) {
    if (!adj.has(e.source)) adj.set(e.source, []);
    adj.get(e.source)!.push(e);
  }
  const nodeById = new Map<string, GraphNode>();
  for (const n of nodes) nodeById.set(n.id, n);

  const db = getDb();

  // Delete previous chunks from this repo (idempotent re-ingest)
  const prefix = `graphify:${repoName}:`;
  if (!dryRun) {
    const deleted = db.prepare("DELETE FROM chunks WHERE source_file LIKE ? || '%'").run(prefix);
    console.log(`[graphify-ingest] Cleared ${deleted.changes} previous chunks from ${repoName}`);
  }

  const insertChunk = db.prepare(`
    INSERT INTO chunks (source_file, chunk_text, chunk_type, source_date, is_compiled, source_type, metadata)
    VALUES (?, ?, 'graph_node', ?, 1, 'external', ?)
  `);

  const today = new Date().toISOString().slice(0, 10);
  let count = 0;
  let batchStart = Date.now();

  for (let i = 0; i < nodes.length; i++) {
    const n = nodes[i];
    const neighbors = (adj.get(n.id) || []).slice(0, 8);
    const context = neighbors
      .map((e) => `${e.relation} → ${nodeById.get(e.target)?.label ?? e.target}`)
      .join("; ");

    const textParts = [
      n.label,
      n.file_type ? `Type: ${n.file_type}` : "",
      n.source_file ? `Origem: ${n.source_file}` : "",
      context ? `Conexões: ${context}` : "",
    ].filter(Boolean);
    const chunkText = textParts.join("\n");

    const sourceFile = `graphify:${repoName}:${n.id}`;
    const metadata = JSON.stringify({
      graphify_id: n.id,
      repo: repoName,
      community: n.community ?? null,
      file_type: n.file_type ?? null,
      source_original: n.source_file ?? null,
      source_url: n.source_url ?? null,
      author: n.author ?? null,
    });

    if (!dryRun) {
      insertChunk.run(sourceFile, chunkText, today, metadata);
    }
    count++;

    if (count % batchSize === 0 && i < nodes.length - 1) {
      const elapsed = ((Date.now() - batchStart) / 1000).toFixed(1);
      console.log(`[graphify-ingest] ${count}/${nodes.length} chunks inserted in ${elapsed}s — pausing ${pauseMs / 1000}s`);
      if (!dryRun) {
        await new Promise((r) => setTimeout(r, pauseMs));
      }
      batchStart = Date.now();
    }
  }

  console.log(`[graphify-ingest] ✓ Done: ${count} chunks from ${repoName} → nox-mem`);
  return count;
}

// ─── CLI ────────────────────────────────────────────────────────────────
const args = process.argv.slice(2);
if (args.length < 2) {
  console.error("Usage: graphify-ingest <graph.json path> <repo-name> [--dry-run] [--batch-size N] [--pause-ms MS]");
  process.exit(1);
}
const graphPath = args[0];
const repoName = args[1];
const dryRun = args.includes("--dry-run");
const batchIdx = args.indexOf("--batch-size");
const pauseIdx = args.indexOf("--pause-ms");
const batchSize = batchIdx >= 0 ? parseInt(args[batchIdx + 1]) : 500;
const pauseMs = pauseIdx >= 0 ? parseInt(args[pauseIdx + 1]) : 300_000;

try {
  await ingestGraph(graphPath, repoName, { batchSize, pauseMs, dryRun });
  closeDb();
} catch (err) {
  console.error(`[graphify-ingest] Failed: ${(err as Error).message}`);
  closeDb();
  process.exit(1);
}
