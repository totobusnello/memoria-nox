#!/usr/bin/env node
import { Command } from "commander";
import { search, searchHybrid, formatResults } from "./search.js";
import { ingestFile } from "./ingest.js";
import { reindex } from "./reindex.js";
import { primer } from "./primer.js";
import { getStats } from "./stats.js";
import { getDb, closeDb } from "./db.js";
import { syncProjectContexts, listProjects } from "./project-context-gen.js";
import { crossSearch, formatCrossResults, getCrossStats } from "./cross-search.js";
import { compact } from "./compact.js";
import { getMetrics } from "./metrics.js";
import { updateSessionState } from "./session-update.js";
import { buildGraph, getGraphStats, formatEntityQuery, mergeEntities, pruneKnowledgeGraph, formatPruneResult, upsertDecision, getDecisionHistory, listDecisions, getCurrentDecision } from "./knowledge-graph.js";
import { shareInsight, pullSharedInsights, listShared, sharedStats } from "./shared-memory.js";
import { selfImprove } from "./self-improve.js";
import { getTierStats, evaluateTiers } from "./tier-manager.js";
import { getNoiseStats, isNoise } from "./noise-filter.js";
import { distillSessions } from "./session-distill.js";
import { startWatch } from "./watch.js";



const program = new Command();

program.name("nox-mem").description("Nox Supermem — search, consolidate, recover").version("2.3.0");

program
  .command("search <query>")
  .description("Search memory (FTS5 + boost + recency)")
  .option("-n, --limit <n>", "Number of results", "5")
  .option("--no-hybrid", "Disable semantic search (FTS5 only)")
  .action(async (query: string, opts: { limit: string; hybrid: boolean }) => {
    if (opts.hybrid) {
      const results = await searchHybrid(query, parseInt(opts.limit, 10));
      console.log(formatResults(results));
    } else {
      console.log(formatResults(search(query, parseInt(opts.limit, 10))));
    }
    closeDb();
  });

program
  .command("vectorize")
  .description("Build/update vector index for all chunks (semantic search)")
  .option("--force", "Re-embed all chunks, even already indexed", false)
  .action(async (opts: { force: boolean }) => {
    const { vectorize } = await import("./vectorize.js");
    const result = await vectorize({ force: opts.force });
    console.log(`[INFO] Vectorize complete: ${result.embedded} embedded, ${result.skipped} skipped, ${result.total} total`);
    closeDb();
  });

program
  .command("ingest <file>")
  .description("Index a specific .md or .json file")
  .action(async (file: string) => {
    const result = await ingestFile(file);
    console.log(`[INFO] Ingested ${file}: ${result.chunks} chunks`);
    closeDb();
  });

program
  .command("reindex")
  .description("Rebuild entire index from markdown files (preserves consolidation state)")
  .action(async () => {
    const result = await reindex();
    console.log(`[INFO] Reindexed ${result.files} files, ${result.chunks} chunks`);
  });

program
  .command("primer")
  .description("Generate context recovery summary (~500 tokens)")
  .action(async () => {
    console.log(primer());
    closeDb();
  });

program
  .command("stats")
  .description("Show memory statistics")
  .action(async () => {
    console.log(getStats());
    closeDb();
  });

program
  .command("consolidate")
  .description("Consolidate daily notes into topic files (requires Ollama)")
  .action(async () => {
    const { consolidate } = await import("./consolidate.js");
    const { syncToNotion } = await import("./notion-sync.js");
    const result = await consolidate();
    if (result.notionItems.length > 0) {
      await syncToNotion(result.notionItems);
    }
    if (result.remaining > 0) {
      console.log(`[INFO] ${result.remaining} daily notes still pending — run again or wait for next cron`);
    }
    closeDb();
  });

program
  .command("retry-failed")
  .description("Retry consolidation of previously failed daily notes")
  .action(async () => {
    const { consolidate } = await import("./consolidate.js");
    const { syncToNotion } = await import("./notion-sync.js");
    const result = await consolidate({ retryFailed: true });
    if (result.notionItems.length > 0) {
      await syncToNotion(result.notionItems);
    }
    closeDb();
  });

program
  .command("digest")
  .description("Generate weekly digest")
  .action(async () => {
    const { digest } = await import("./digest.js");
    await digest();
    closeDb();
  });

program
  .command("sync-notion")
  .description("Re-sync last consolidation items to Notion")
  .action(async () => {
    const { syncToNotion, loadSyncLog } = await import("./notion-sync.js");
    const items = loadSyncLog();
    if (items.length === 0) {
      console.log("[INFO] No items to sync — run consolidate first");
      return;
    }
    console.log(`[INFO] Re-syncing ${items.length} items from last consolidation...`);
    await syncToNotion(items);
  });

program
  .command("doctor")
  .description("Diagnostic check — Ollama, SQLite, FTS5, watcher, Notion")
  .action(async () => {
    const { doctor } = await import("./doctor.js");
    await doctor();
    closeDb();
  });

program
  .command("projects")
  .description("List all projects with last update date")
  .action(async () => {
    listProjects();
    closeDb();
  });

program
  .command("project-sync")
  .description("Sync PROJECT_CONTEXT.md files from memory database")
  .action(async () => {
    const result = syncProjectContexts();
    console.log(`[PROJECT-SYNC] Updated: ${result.updated}, Created: ${result.created}, Errors: ${result.errors}`);
    closeDb();
  });


program
  .command("cross-search <query>")
  .description("Search across ALL agent memory databases")
  .option("-n, --limit <n>", "Number of results", "10")
  .action((query: string, opts: { limit: string }) => {
    const results = crossSearch(query, parseInt(opts.limit, 10));
    console.log(formatCrossResults(results));
  });

program
  .command("cross-stats")
  .description("Show chunk counts across all agent databases")
  .action(async () => {
    console.log(getCrossStats());
  });

program
  .command("compact")
  .description("Compress old chunks (>30 days) into summaries")
  .option("--age <days>", "Minimum age in days", "30")
  .option("--dry-run", "Preview without making changes", false)
  .action(async (opts: { age: string; dryRun: boolean }) => {
    const result = await compact(parseInt(opts.age, 10), opts.dryRun);
    console.log("[COMPACT] Done: " + result.compacted + " compacted, " + result.summaries + " summaries, " + result.deleted + " removed");
    closeDb();
  });

program
  .command("metrics")
  .description("Show daily observability metrics")
  .option("-d, --days <n>", "Number of days to show", "7")
  .action((opts: { days: string }) => {
    console.log(getMetrics(parseInt(opts.days, 10)));
    closeDb();
  });

program
  .command("update-session")
  .description("Auto-update SESSION-STATE.md from latest memory")
  .action(async () => {
    updateSessionState();
    closeDb();
  });


program
  .command("kg-build")
  .description("Build knowledge graph from memory chunks (incremental)")
  .option("-n, --limit <n>", "Max chunks to process", "200")
  .action(async (opts: { limit: string }) => {
    const result = buildGraph(parseInt(opts.limit, 10));
    console.log("[KG] Built: " + result.entities + " entities, " + result.relations + " relations");
    closeDb();
  });

program
  .command("kg-query <entity>")
  .description("Query knowledge graph for an entity and its relations")
  .action(async (entity: string) => {
    console.log(formatEntityQuery(entity));
    closeDb();
  });

program
  .command("kg-stats")
  .description("Show knowledge graph statistics")
  .action(async () => {
    console.log(getGraphStats());
    closeDb();
  });

program
  .command("self-improve")
  .description("Run agent self-improvement analysis (contradictions, patterns, gaps)")
  .action(async () => {
    const report = await selfImprove();
    console.log(report);
    closeDb();
  });


program
  .command("kg-merge")
  .description("Merge duplicate entities in knowledge graph (normalizes names)")
  .action(async () => {
    const result = mergeEntities();
    console.log("[KG] Merged " + result.merged + " duplicate entities");
    closeDb();
  });

program
  .command("kg-prune")
  .description("Prune expired/low-confidence relations from knowledge graph (TTL decay)")
  .option("--dry-run", "Show what would be pruned without deleting")
  .action(async (opts: { dryRun?: boolean }) => {
    const result = pruneKnowledgeGraph(opts.dryRun ?? false);
    console.log(formatPruneResult(result));
    if (opts.dryRun) console.log("[KG-PRUNE] Dry run — no changes made");
    closeDb();
  });

// ─── Decision versioning ────────────────────────────────────────────────────
program
  .command("decision-set <key> <content>")
  .description("Set/update a versioned decision (tracks full history)")
  .option("--author <name>", "Author name", "system")
  .action((key: string, content: string, opts: { author: string }) => {
    const v = upsertDecision(key, content, undefined, opts.author);
    console.log(`✅ Decision "${key}" → v${v}`);
    closeDb();
  });

program
  .command("decision-get <key>")
  .description("Get current value of a decision")
  .action((key: string) => {
    const current = getCurrentDecision(key);
    if (!current) { console.log(`Decision "${key}" not found`); }
    else { console.log(current); }
    closeDb();
  });

program
  .command("decision-history <key>")
  .description("Show full version history of a decision")
  .action((key: string) => {
    const history = getDecisionHistory(key);
    if (history.length === 0) { console.log(`No history for "${key}"`); closeDb(); return; }
    for (const h of history) {
      const flag = h.is_current ? " [CURRENT]" : ` [superseded ${h.superseded_at}]`;
      console.log(`v${h.version}${flag} — ${h.created_at}`);
      console.log(`  ${h.content}\n`);
    }
    closeDb();
  });

program
  .command("decision-list")
  .description("List all current decisions")
  .action(() => {
    const decisions = listDecisions();
    if (decisions.length === 0) { console.log("No decisions recorded"); closeDb(); return; }
    for (const d of decisions) {
      console.log(`[${d.decision_key}] v${d.version} (${d.created_at})`);
      console.log(`  ${d.content.substring(0, 120)}\n`);
    }
    closeDb();
  });

// ─── Shared memory (cross-agent) ────────────────────────────────────────────
program
  .command("share <text>")
  .description("Share an insight to the cross-agent shared memory pool")
  .option("--type <type>", "Chunk type", "insight")
  .option("--tags <tags>", "Comma-separated tags", "")
  .option("--reason <reason>", "Why sharing this")
  .action(async (text: string, opts: { type: string; tags: string; reason?: string }) => {
    const tags = opts.tags ? opts.tags.split(",").map(t => t.trim()) : [];
    const id = shareInsight(text, opts.type, tags, opts.reason);
    console.log(`✅ Shared (id=${id})`);
    closeDb();
  });

program
  .command("pull-shared")
  .description("Pull unprocessed shared insights from other agents into this DB")
  .option("--agent <name>", "Agent name to pull for")
  .action(async (opts: { agent?: string }) => {
    const imported = await pullSharedInsights(opts.agent);
    console.log(`✅ Imported ${imported} shared insights`);
    closeDb();
  });

program
  .command("shared-stats")
  .description("Show stats on the cross-agent shared memory pool")
  .action(() => {
    const stats = sharedStats();
    console.log(`Total shared: ${stats.total}`);
    for (const a of stats.byAgent) console.log(`  ${a.agent}: ${a.count}`);
    closeDb();
  });


// ─── Knowledge Graph v2: LLM extraction ──────────────────────────────────────

program
  .command("kg-extract")
  .description("Extract entities/relations from chunks using LLM (Ollama)")
  .option("-n, --limit <n>", "Chunks to process", "50")
  .action(async (opts: { limit: string }) => {
    const { extractWithLLM } = await import("./kg-llm.js");
    const { ensureGraphTables, buildGraph } = await import("./knowledge-graph.js");
    const { getDb, closeDb } = await import("./db.js");
    ensureGraphTables();
    const db = getDb();
    
    const lastProcessed = (db.prepare(
      "SELECT value FROM meta WHERE key = 'kg_llm_last_chunk_id'"
    ).get() as { value: string } | undefined)?.value || "0";
    
    const chunks = db.prepare(
      "SELECT id, chunk_text, chunk_type FROM chunks WHERE id > ? ORDER BY id ASC LIMIT ?"
    ).all(parseInt(lastProcessed), parseInt(opts.limit)) as Array<{
      id: number; chunk_text: string; chunk_type: string;
    }>;
    
    if (chunks.length === 0) { console.log("[KG-LLM] No new chunks"); closeDb(); return; }
    
    let totalE = 0, totalR = 0, maxId = parseInt(lastProcessed);
    let fastPathChunks = 0, llmChunks = 0;
    for (const chunk of chunks) {
      const result = await extractWithLLM(chunk.chunk_text);
      if (result.fast_path_used) fastPathChunks++; else llmChunks++;
      for (const e of result.entities) {
        // Fase 1.7a: ontology attributes — merge JSON ao upsert.
        const newAttrs = e.attributes || null;
        const existing = db.prepare(
          "SELECT id, attributes FROM kg_entities WHERE name = ? AND entity_type = ?"
        ).get(e.name, e.type) as { id: number; attributes: string | null } | undefined;

        if (existing) {
          // Merge: preserva attributes existentes; chaves novas sobrescrevem.
          let merged: Record<string, unknown> = {};
          try {
            merged = existing.attributes ? JSON.parse(existing.attributes) as Record<string, unknown> : {};
          } catch { merged = {}; }
          if (newAttrs) merged = { ...merged, ...newAttrs };
          const mergedJson = Object.keys(merged).length > 0 ? JSON.stringify(merged) : null;
          db.prepare(
            "UPDATE kg_entities SET mention_count = mention_count + 1, last_seen = datetime('now'), attributes = ? WHERE id = ?"
          ).run(mergedJson, existing.id);
        } else {
          db.prepare(
            "INSERT INTO kg_entities (name, entity_type, attributes) VALUES (?, ?, ?)"
          ).run(e.name, e.type, newAttrs ? JSON.stringify(newAttrs) : null);
        }
        totalE++;
      }
      for (const r of result.relations) {
        const src = db.prepare("SELECT id FROM kg_entities WHERE name = ?").get(r.source) as { id: number } | undefined;
        const tgt = db.prepare("SELECT id FROM kg_entities WHERE name = ?").get(r.target) as { id: number } | undefined;
        if (src && tgt) {
          db.prepare(
            "INSERT OR IGNORE INTO kg_relations (source_entity_id, relation_type, target_entity_id, evidence_chunk_id) VALUES (?, ?, ?, ?)"
          ).run(src.id, r.relation, tgt.id, chunk.id);
          totalR++;
        }
      }
      maxId = Math.max(maxId, chunk.id);
      process.stdout.write(`\r[KG-LLM] ${chunks.indexOf(chunk) + 1}/${chunks.length} — ${totalE}E ${totalR}R (fast:${fastPathChunks} llm:${llmChunks})`);
    }

    db.prepare("INSERT OR REPLACE INTO meta (key, value) VALUES ('kg_llm_last_chunk_id', ?)").run(String(maxId));
    const savedPct = chunks.length > 0 ? Math.round((fastPathChunks / chunks.length) * 100) : 0;
    console.log(`\n[KG-LLM] Done: ${totalE} entities, ${totalR} relations from ${chunks.length} chunks · fast-path ${savedPct}% (${fastPathChunks}/${chunks.length}) — Gemini calls saved`);
    closeDb();
  });

// ─── Cross-Agent Intelligence v2 ─────────────────────────────────────────────

program
  .command("agent-profiles")
  .description("Show expertise profiles for all agents")
  .action(async () => {
    const { profileAllAgents, formatProfiles } = await import("./cross-agent-v2.js");
    console.log(formatProfiles(profileAllAgents()));
  });

program
  .command("agent-insights")
  .description("Pull lessons and decisions from all agents")
  .option("--from <agent>", "Pull from specific agent")
  .option("-n, --limit <n>", "Results per agent", "5")
  .action(async (opts: { from?: string; limit: string }) => {
    const { pullInsightsFrom, pullAllInsights } = await import("./cross-agent-v2.js");
    const limit = parseInt(opts.limit);
    const insights = opts.from
      ? pullInsightsFrom(opts.from, ["decision", "lesson"], limit)
      : pullAllInsights(undefined, ["decision", "lesson"], limit);
    
    if (insights.length === 0) { console.log("No insights found."); return; }
    for (const i of insights) {
      const preview = i.text.substring(0, 200).replace(/\n/g, " ");
      console.log(`[@${i.agent}] [${i.type}] ${i.date || "?"}`);
      console.log(`  ${preview}...\n`);
    }
  });

program
  .command("cross-kg")
  .description("Merge and display knowledge graphs across all agents")
  .action(async () => {
    const { mergeCrossKnowledgeGraphs, formatCrossKG } = await import("./cross-agent-v2.js");
    console.log(formatCrossKG(mergeCrossKnowledgeGraphs()));
  });

program
  .command("kg-path <from> <to>")
  .description("Find relationship path between two entities")
  .action(async (from: string, to: string) => {
    const { findPath, formatPath } = await import("./cross-agent-v2.js");
    console.log(formatPath(findPath(from, to)));
  });


// ─── Session distill ──────────────────────────────────────────────────────────

program
  .command("session-distill")
  .description("Distill memories from historical agent session JSONL files")
  .option("--agents <ids>", "Comma-separated agent ids (default: nox,forge,atlas,cipher,boris,lex)")
  .option("--lookback-days <n>", "Days to look back (default: 30)", "30")
  .option("--max-sessions <n>", "Max sessions per run (default: 50)", "50")
  .option("--dry-run", "Show what would be processed without ingesting", false)
  .action(async (opts: { agents?: string; lookbackDays: string; maxSessions: string; dryRun: boolean }) => {
    const agentIds = opts.agents ? opts.agents.split(",").map((s) => s.trim()) : undefined;
    const result = await distillSessions({
      agentIds,
      lookbackDays: parseInt(opts.lookbackDays, 10),
      maxSessionsPerRun: parseInt(opts.maxSessions, 10),
      dryRun: opts.dryRun,
    });
    console.log("\nSummary:");
    console.log(`  Sessions processed:   ${result.processedSessions}`);
    console.log(`  Sessions skipped:     ${result.skippedSessions}`);
    console.log(`  Messages read:        ${result.messagesRead}`);
    console.log(`  Memories extracted:   ${result.memoriesExtracted}`);
    console.log(`  Memories deduped:     ${result.memoriesDeduplicated}`);
    console.log(`  Memories ingested:    ${result.memoriesIngested}`);
    closeDb();
  });

// ─── Noise filter ─────────────────────────────────────────────────────────────

const noiseCmd = program.command("noise").description("Noise filter management");

noiseCmd
  .command("stats")
  .description("Show noise filter stats")
  .action(() => {
    const db = getDb();
    const stats = getNoiseStats(db);
    console.log("Noise filter:");
    console.log(`  Built-in prototypes: ${stats.builtin}`);
    console.log(`  Learned prototypes:  ${stats.learned}`);
    console.log(`  Total hits:          ${stats.totalHits}`);
    closeDb();
  });

noiseCmd
  .command("check <text>")
  .description("Check if a text would be filtered as noise")
  .action((text: string) => {
    const db = getDb();
    const result = isNoise(text, db);
    console.log(result ? `[NOISE] Would be filtered: "${text}"` : `[OK] Would pass: "${text}"`);
    closeDb();
  });

// ─── Tier management ──────────────────────────────────────────────────────────

const tiersCmd = program.command("tiers").description("Manage memory tiers (core/working/peripheral)");

tiersCmd
  .command("stats")
  .description("Show chunk distribution by tier")
  .action(() => {
    const db = getDb();
    const stats = getTierStats(db);
    const total = Object.values(stats).reduce((a, b) => a + b, 0) || 1;
    console.log("Tier distribution:");
    console.log(`  🔵 core:       ${stats.core ?? 0} (${((stats.core ?? 0) / total * 100).toFixed(1)}%)`);
    console.log(`  🟡 working:    ${stats.working ?? 0} (${((stats.working ?? 0) / total * 100).toFixed(1)}%)`);
    console.log(`  ⬜ peripheral: ${stats.peripheral ?? 0} (${((stats.peripheral ?? 0) / total * 100).toFixed(1)}%)`);
    closeDb();
  });

tiersCmd
  .command("evaluate")
  .description("Evaluate and adjust tiers based on access patterns")
  .action(() => {
    const db = getDb();
    const result = evaluateTiers(db);
    console.log(`Tier evaluation complete:`);
    console.log(`  Promoted: ${result.promoted} chunks`);
    console.log(`  Demoted:  ${result.demoted} chunks`);
    const stats = getTierStats(db);
    console.log(`\nCurrent distribution:`);
    console.log(`  🔵 core:       ${stats.core ?? 0}`);
    console.log(`  🟡 working:    ${stats.working ?? 0}`);
    console.log(`  ⬜ peripheral: ${stats.peripheral ?? 0}`);
    closeDb();
  });

// ─── Watch mode ───────────────────────────────────────────────────────────────

program
  .command("watch")
  .description("Watch memory directories and auto-ingest on change (real-time)")
  .option("-v, --verbose", "Show skipped directories", false)
  .action((opts: { verbose: boolean }) => {
    startWatch(opts.verbose);
    // Keep process alive
    process.on("SIGINT", () => {
      console.log("\n[WATCH] Stopped.");
      closeDb();
      process.exit(0);
    });
    process.on("SIGTERM", () => {
      closeDb();
      process.exit(0);
    });
  });


// ─── Reflect (deep KG synthesis) ──────────────────────────────────────────────

program
  .command("reflect <question>")
  .description("Deep synthesis over memory + KG — reasons over evidence, not just retrieves")
  .option("--no-cache", "Force fresh synthesis")
  .action(async (question: string, opts: { cache?: boolean }) => {
    const { reflect, formatReflect } = await import("./reflect.js");
    const result = await reflect(question, { noCache: !opts.cache });
    console.log(formatReflect(result));
  });

// ─── Crystallize (save procedure) ─────────────────────────────────────────────

program
  .command("crystallize")
  .description("Save a multi-step procedure as a reusable skill")
  .requiredOption("--title <title>", "Procedure title")
  .option("--agent <agent>", "Origin agent", "system")
  .option("--tags <tags>", "Comma-separated tags")
  .action(async (opts: { title: string; agent: string; tags?: string }) => {
    const readline = await import("readline");
    const rl = readline.createInterface({ input: process.stdin, output: process.stdout });
    console.log("Enter steps (one per line, empty line to finish):");
    const steps: string[] = [];
    const askStep = (): Promise<void> => new Promise((resolve) => {
      rl.question(`  Step ${steps.length + 1}: `, (line: string) => {
        if (line.trim() === "") { rl.close(); resolve(); return; }
        steps.push(line.trim());
        askStep().then(resolve);
      });
    });
    await askStep();
    if (steps.length === 0) { console.log("No steps — aborted."); return; }
    const { crystallize } = await import("./crystallize.js");
    const id = await crystallize({ title: opts.title, steps, agent: opts.agent, tags: opts.tags?.split(",").map(t => t.trim()) || [] });
    console.log(`✅ Crystallized as chunk #${id}: "${opts.title}" (${steps.length} steps)`);
  });

program
  .command("crystallize-validate <id>")
  .description("Record a validation run for a procedure (tracks outcome + agent + notes)")
  .option("--outcome <outcome>", "success | failure | partial", "success")
  .option("--agent <agent>", "Agent running the validation", "system")
  .option("--notes <notes>", "Free-form notes about the run")
  .action(async (id: string, opts: { outcome: string; agent: string; notes?: string }) => {
    const { validateProcedure } = await import("./crystallize.js");
    const outcome = (["success","failure","partial"].includes(opts.outcome) ? opts.outcome : "success") as "success" | "failure" | "partial";
    validateProcedure(parseInt(id, 10), { outcome, agent: opts.agent, notes: opts.notes });
    console.log(`✅ Procedure #${id} validation recorded: outcome=${outcome} agent=${opts.agent}`);
  });

program.parse();
