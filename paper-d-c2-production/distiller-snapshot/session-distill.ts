/**
 * session-distill.ts — Pipeline de destilação de sessões históricas
 *
 * Extrai decisões, preferências e contexto de conversas armazenadas
 * nos arquivos JSONL de sessão dos agentes OpenClaw.
 *
 * Fluxo:
 *   1. scan: lista sessões JSONL por agente, filtra já processadas
 *   2. chunk: extrai blocos user+assistant, aplica noise filter
 *   3. distill: envia para Gemini Flash-Lite → memories
 *   4. import: dedup semântico + ingest como chunk_type="distilled"
 */

import { readdirSync, readFileSync, existsSync, statSync, appendFileSync } from "fs";
import { homedir } from "os";
import { resolve } from "path";
import { getDb } from "./db.js";
import { tracked } from "./lib/provider-cost.js";
import { isNoise } from "./noise-filter.js";
import { isDuplicate } from "./dedup.js";
import { incrementMetric } from "./metrics.js";
import { ShadowRun } from "./distill-shadow.js";

// One line of counts per real run (2026-11-14). The `Blocks by outcome` summary went only to the
// stdout of the cron agent that runs this, and nothing kept it. Counts and agent ids only: no
// block text, no memory text. Kept apart from the C2 shadow dir, whose collection is blinded.
// No mkdir: a recursive mkdirSync under /proc spun forever in the smoke test; a missing dir
// fails the append at once and only warns.
export const OUTCOMES_PATH = process.env.NOX_DISTILL_OUTCOMES_PATH ?? "/var/lib/nox-mem/distill-outcomes.jsonl";
// tier-manager not imported here: distilled chunks use LLM-provided importance to determine tier
// (importance >= 0.8 → working, else peripheral) — more nuanced than static getInitialTier("distilled")

const WORKSPACE = process.env.OPENCLAW_WORKSPACE || "/root/.openclaw/workspace";
const AGENTS_DIR = resolve(WORKSPACE, "agents");

// ─── Session source directories ──────────────────────────────────────────────
// A migração da VPS trocou o runtime dos agentes: as sessões deixaram de ser
// escritas em <workspace>/agents/<id>/sessions/ (último arquivo: 2026-08-05) e
// passaram a ser transcripts do Claude CLI, sob
// ~/.claude-nuvini-team/projects/-root--openclaw-workspace[-agents-<id>]/.
// O distill continuou lendo só o endereço antigo e por isso passou 28 dias
// imprimindo "No unprocessed sessions found" com exit 0 — silêncio por falta
// de dado, não por ausência de trabalho. Manter os DOIS endereços: o legado
// ainda guarda sessões anteriores a 05/08 que podem não ter sido destiladas.
// O Claude CLI guarda o transcript sob <projectsDir>/<slug>, onde <slug> é o cwd
// da sessão com "/" e "." trocados por "-"
// (/root/.openclaw/workspace -> -root--openclaw-workspace). Derivar em vez de
// fixar o slug mantém isto válido em qualquer instalação. O default é o
// ~/.claude/projects do Claude CLI; esta VPS roda o CLI do team, cujo home é
// .claude-nuvini-team, e por isso define NOX_CLAUDE_PROJECTS_DIR no .env.
function claudeProjectSlug(cwd: string): string {
  return cwd.replace(/[/.]/g, "-");
}

// O home do Claude CLI varia por instalação: ~/.claude é o padrão, mas uma
// conta de team usa ~/.claude-<team> (nesta VPS, ~/.claude-nuvini-team).
// Descobrir os candidatos em vez de exigir configuração: pôr a variável no
// .env só passaria a valer para os crons depois de um restart do gateway, que
// lê o arquivo como EnvironmentFile no start.
function claudeProjectsDirs(): string[] {
  const explicit = process.env.NOX_CLAUDE_PROJECTS_DIR;
  if (explicit) return [explicit];
  const home = homedir();
  try {
    return readdirSync(home)
      .filter((d) => d === ".claude" || d.startsWith(".claude-"))
      .map((d) => resolve(home, d, "projects"))
      .filter((d) => existsSync(d));
  } catch {
    return [];
  }
}

function sessionDirsFor(agentId: string): string[] {
  // O agente "main" roda no próprio workspace; os demais em agents/<id>.
  const cwd = agentId === "main" ? WORKSPACE : resolve(AGENTS_DIR, agentId);
  const slug = claudeProjectSlug(cwd);
  return [
    resolve(AGENTS_DIR, agentId, "sessions"), // legado (pré-migração)
    ...claudeProjectsDirs().map((d) => resolve(d, slug)), // Claude CLI (atual)
  ];
}

// Agents to process (those with direct Toto interaction)
// "main" entra na lista: apos a migracao e o diretorio de maior volume
// (44 transcripts em 7 dias contra 7 do nox), e ficava de fora por desenho
// anterior a ela.
const DEFAULT_AGENTS = ["main", "nox", "forge", "atlas", "cipher", "boris", "lex"];

interface SessionEvent {
  type: string;
  timestamp?: string;
  message?: {
    role: "user" | "assistant";
    content: string | Array<{ type: string; text?: string }>;
  };
}

interface DistilledMemory {
  text: string;
  category: "decision" | "preference" | "lesson" | "context" | "project";
  importance: number;
}

interface DistillResult {
  memories: DistilledMemory[];
}

// ─── Schema ──────────────────────────────────────────────────────────────────

export function ensureDistillTable(db: ReturnType<typeof getDb>): void {
  db.exec(`
    CREATE TABLE IF NOT EXISTS session_distill_log (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      session_key TEXT NOT NULL UNIQUE,
      agent TEXT NOT NULL,
      processed_at TEXT DEFAULT (datetime('now')),
      chunks_extracted INTEGER DEFAULT 0,
      message_count INTEGER DEFAULT 0
    );
  `);
}

// ─── Session scanning ────────────────────────────────────────────────────────

function listUnprocessedSessions(
  db: ReturnType<typeof getDb>,
  agentIds: string[],
  lookbackDays: number
): Array<{ agentId: string; sessionFile: string; sessionKey: string; mtimeMs: number }> {
  const cutoff = new Date(Date.now() - lookbackDays * 24 * 60 * 60 * 1000).toISOString();
  const sessions: Array<{ agentId: string; sessionFile: string; sessionKey: string; mtimeMs: number }> = [];

  for (const agentId of agentIds) {
    for (const sessionsDir of sessionDirsFor(agentId)) {
    if (!existsSync(sessionsDir)) continue;

    let files: string[];
    try {
      files = readdirSync(sessionsDir).filter((f) => f.endsWith(".jsonl"));
    } catch {
      continue;
    }

    for (const file of files) {
      const sessionKey = `${agentId}:${file.replace(".jsonl", "")}`;

      // Skip already processed
      const already = db.prepare(
        "SELECT id FROM session_distill_log WHERE session_key = ?"
      ).get(sessionKey);
      if (already) continue;

      // Check file modification time against lookback
      const filePath = resolve(sessionsDir, file);
      let mtimeMs: number;
      try {
        mtimeMs = statSync(filePath).mtimeMs;
        if (new Date(mtimeMs).toISOString() < cutoff) continue;
      } catch {
        continue;
      }

      sessions.push({ agentId, sessionFile: filePath, sessionKey, mtimeMs });
    }
    }
  }

  // Oldest first (2026-11-06). The list used to be readdir order, agent by agent, and the
  // caller cuts it at maxSessionsPerRun. With more than the cap pending (the backlog left by
  // the 2026-09-08 address fix: 118 sessions of one week never logged), which sessions ran
  // was arbitrary, and the ones closest to leaving the lookback could wait behind new ones
  // until they aged out. Oldest first, a backlog drains before any of it expires.
  sessions.sort((a, b) => a.mtimeMs - b.mtimeMs || a.sessionKey.localeCompare(b.sessionKey));
  return sessions;
}

/** A session with fewer messages than this holds only init events: nothing to distill. */
export const MIN_SESSION_MESSAGES = 3;

/**
 * Walks `pending` in order and splits it into the sessions to distill now (at most `max`, each
 * with its messages already read) and the short ones, which are logged as done without counting
 * against `max`. Reading stops once `max` sessions are taken; `left` is how many were not read.
 *
 * The budget used to be cut before the short sessions were set aside, so they spent it: 43 to 48
 * of the 50 sessions taken each night since 2026-11-10 were short, 2 to 7 were distilled, and the
 * ~35 left over aged out of the 1-day lookback before the next run (nox-mem#69, 2026-11-15).
 */
export function partitionPending<P, M>(
  pending: readonly P[],
  max: number,
  read: (s: P) => M[]
): { take: Array<{ session: P; messages: M[] }>; short: Array<{ session: P; count: number }>; left: number } {
  const take: Array<{ session: P; messages: M[] }> = [];
  const short: Array<{ session: P; count: number }> = [];
  let i = 0;
  for (; i < pending.length && take.length < max; i++) {
    const messages = read(pending[i]);
    if (messages.length < MIN_SESSION_MESSAGES) short.push({ session: pending[i], count: messages.length });
    else take.push({ session: pending[i], messages });
  }
  return { take, short, left: pending.length - i };
}

// ─── Message extraction ───────────────────────────────────────────────────────

function extractMessages(sessionFile: string): Array<{ role: string; text: string; timestamp: string }> {
  const messages: Array<{ role: string; text: string; timestamp: string }> = [];

  let content: string;
  try {
    content = readFileSync(sessionFile, "utf-8");
  } catch {
    return messages;
  }

  for (const line of content.split("\n")) {
    if (!line.trim()) continue;
    let event: SessionEvent;
    try {
      event = JSON.parse(line) as SessionEvent;
    } catch {
      continue;
    }

    // A migração trouxe DOIS schemas: o legado do OpenClaw marca type
    // "message"; os transcripts do Claude CLI marcam type "user"/"assistant"
    // (medido: 0 linhas com type=="message" num transcript de hoje). Recusar o
    // novo fazia o parser descartar 100% das linhas sem erro nenhum.
    if (!event.message) continue;
    if (
      event.type !== "message" &&
      event.type !== "user" &&
      event.type !== "assistant"
    )
      continue;
    const { role, content: contentParts } = event.message;
    if (role !== "user" && role !== "assistant") continue;

    // Extract text from content parts (may be string or array)
    const text = typeof contentParts === "string"
      ? contentParts.trim()
      : Array.isArray(contentParts)
        ? contentParts
            .filter((c) => c.type === "text" && c.text)
            .map((c) => c.text!)
            .join("\n")
            .trim()
        : "";

    if (!text) continue;

    // Skip system messages (cron triggers, heartbeats, metadata)
    // Filter both user prompts AND assistant responses to avoid distilling
    // HEARTBEAT loop sessions into thousands of near-dup memories (incident 2026-04-27).
    const isHeartbeatNoise =
      text.startsWith("[cron:") ||
      text.startsWith("HEARTBEAT") ||
      text.startsWith("The conversation history before this point") ||
      text.length < 5 ||
      /^heartbeat[_ ]ok\b/i.test(text);

    if (isHeartbeatNoise) continue;

    messages.push({ role, text, timestamp: event.timestamp ?? "" });
  }

  // Heuristic: if 70%+ of original turns were heartbeat-noise (now filtered),
  // the survivors are noisy paraphrases and not worth N^2 cosine dedup.
  // Caller checks messages.length < 3 already; here we add a stronger signal.
  return messages;
}

// ─── Distillation (LLM) ───────────────────────────────────────────────────────

const DISTILL_SYSTEM = `Você é um extrator de memória de conversas de IA.
Analise a conversa e extraia APENAS informações que merecem ser lembradas a longo prazo:
- Decisões tomadas pelo usuário ou pelo agente
- Preferências do usuário (como ele quer as coisas feitas)
- Lições aprendidas (erros, fixes, insights técnicos)
- Contexto de projetos relevantes (nomes, status, detalhes)

Ignore: cumprimentos, confirmações (ok, feito, obrigado), listas de tarefas genéricas, conteúdo repetido.

Responda APENAS com JSON válido:
{"memories": [{"text": "...", "category": "decision|preference|lesson|context|project", "importance": 0.0-1.0}]}

Importância: 0.9+ = crítico, 0.7-0.9 = importante, 0.5-0.7 = útil, <0.5 = ignorar.
Retorne [] se não houver nada relevante. Máximo 10 itens.`;

// Why a block yielded what it yielded. Until 2026-11-13 every failure returned [] exactly like
// "the model found nothing", and the caller fell back on `length > 0` (DECISIONS 2026-10-27 #6).
// What reaches the DB is unchanged: any outcome other than "ok" still contributes no memories.
export type DistillOutcome = "ok" | "empty" | "no_key" | "http_error" | "network_error" | "no_text" | "bad_json";

// Groq left on 2026-11-13 (A6): session-distill.groq failed 21 of 21 calls (2026-09-13..11-11)
// with the key present, and Groq is not part of the stack (Toto, 2026-11-11).
async function distillWithGemini(conversationBlock: string): Promise<{ outcome: DistillOutcome; memories: DistilledMemory[] }> {
  const apiKey = process.env.GEMINI_API_KEY;
  if (!apiKey) return { outcome: "no_key", memories: [] };

  let response: Response;
  try {
    response = await tracked({
      caller: "session-distill.gemini", provider: "gemini", model: "gemini-2.5-flash-lite",
    })(
      `https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-lite:generateContent?key=${apiKey}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          contents: [
            { role: "user", parts: [{ text: DISTILL_SYSTEM + "\n\nConversa:\n" + conversationBlock }] }
          ],
          generationConfig: { responseMimeType: "application/json", temperature: 0.1 },
        }),
        signal: AbortSignal.timeout(30_000),
      }
    );
  } catch {
    return { outcome: "network_error", memories: [] };
  }
  if (!response.ok) return { outcome: "http_error", memories: [] };

  let text: string | undefined;
  try {
    const data = await response.json() as { candidates?: Array<{ content?: { parts?: Array<{ text?: string }> } }> };
    text = data.candidates?.[0]?.content?.parts?.[0]?.text;
  } catch {
    return { outcome: "bad_json", memories: [] };
  }
  if (!text) return { outcome: "no_text", memories: [] };

  try {
    const parsed = JSON.parse(text) as DistillResult;
    const memories = (parsed.memories ?? []).filter((m) => m.importance >= 0.5);
    return { outcome: memories.length > 0 ? "ok" : "empty", memories };
  } catch {
    return { outcome: "bad_json", memories: [] };
  }
}



// ─── Main pipeline ────────────────────────────────────────────────────────────

export interface DistillOptions {
  agentIds?: string[];
  maxSessionsPerRun?: number;
  lookbackDays?: number;
  dryRun?: boolean;
}

export interface DistillStats {
  processedSessions: number;
  skippedSessions: number;
  messagesRead: number;
  memoriesExtracted: number;
  memoriesDeduplicated: number;
  memoriesIngested: number;
  /** blocks per DistillOutcome (dry runs call no model and count nothing) */
  blockOutcomes: Partial<Record<DistillOutcome, number>>;
}

function recordOutcomes(dryRun: boolean, agentIds: readonly string[], lookbackDays: number, pending: number, stats: DistillStats): void {
  if (dryRun) return;
  try {
    appendFileSync(OUTCOMES_PATH, JSON.stringify({
      ts: new Date().toISOString(),
      agents: agentIds,
      lookback_days: lookbackDays,
      pending,
      processed: stats.processedSessions,
      skipped: stats.skippedSessions,
      extracted: stats.memoriesExtracted,
      deduped: stats.memoriesDeduplicated,
      ingested: stats.memoriesIngested,
      block_outcomes: stats.blockOutcomes,
    }) + "\n");
  } catch (e) {
    console.warn(`[DISTILL] could not record outcomes in ${OUTCOMES_PATH}: ${(e as Error).message}`);
  }
}

export async function distillSessions(options: DistillOptions = {}): Promise<DistillStats> {
  const {
    agentIds = DEFAULT_AGENTS,
    maxSessionsPerRun = 50,
    lookbackDays = 30,
    dryRun = false,
  } = options;

  const db = getDb();
  ensureDistillTable(db);

  const stats: DistillStats = {
    processedSessions: 0,
    skippedSessions: 0,
    messagesRead: 0,
    memoriesExtracted: 0,
    memoriesDeduplicated: 0,
    memoriesIngested: 0,
    blockOutcomes: {},
  };

  const pending = listUnprocessedSessions(db, agentIds, lookbackDays);
  const { take: sessions, short, left } = partitionPending(pending, maxSessionsPerRun, (s) => extractMessages(s.sessionFile));

  // Short sessions (just init events) are logged as done and do not count against the budget.
  for (const { session, count } of short) {
    stats.skippedSessions++;
    if (!dryRun) {
      db.prepare(
        "INSERT OR IGNORE INTO session_distill_log (session_key, agent, chunks_extracted, message_count) VALUES (?, ?, 0, ?)"
      ).run(session.sessionKey, session.agentId, count);
    }
  }
  if (left > 0) {
    // A full list on every run is the backlog signal: say how much is left, in the log the
    // nightly job keeps, instead of leaving it to be found by a census.
    console.log(`[DISTILL] Backlog: ${pending.length} unprocessed in the lookback; ${short.length} short logged, taking the ${sessions.length} oldest; ${left} left for the next run`);
  }

  if (sessions.length === 0) {
    console.log(short.length ? `[DISTILL] ${short.length} short sessions logged, none to distill` : "[DISTILL] No unprocessed sessions found");
    recordOutcomes(dryRun, agentIds, lookbackDays, pending.length, stats);
    return stats;
  }

  console.log(`[DISTILL] Processing ${sessions.length} sessions (lookback: ${lookbackDays}d; ${short.length} short logged)`);

  // Group messages into blocks of ~2000 chars for the LLM
  const BLOCK_SIZE = 2000;
  // C2 in shadow (2026-11-06): off unless its ENABLED flag exists; never touches the DB
  const shadow = new ShadowRun(DISTILL_SYSTEM, dryRun);

  for (const { session: { agentId, sessionFile, sessionKey, mtimeMs }, messages } of sessions) {

    stats.messagesRead += messages.length;

    // Build conversation text, apply noise filter
    const conversationLines = messages
      .filter((m) => !isNoise(m.text, db))
      .map((m) => `[${m.role.toUpperCase()}]: ${m.text}`);

    if (conversationLines.length === 0) {
      stats.skippedSessions++;
      continue;
    }

    // Split into blocks
    const blocks: string[] = [];
    let currentBlock = "";
    for (const line of conversationLines) {
      if (currentBlock.length + line.length > BLOCK_SIZE && currentBlock) {
        blocks.push(currentBlock.trim());
        currentBlock = line + "\n";
      } else {
        currentBlock += line + "\n";
      }
    }
    if (currentBlock.trim()) blocks.push(currentBlock.trim());

    let sessionExtracted = 0;

    for (const [blockIndex, block] of blocks.entries()) {
      if (dryRun) {
        console.log(`[DRY RUN] Would distill block (${block.length} chars) from ${agentId}`);
        continue;
      }

      const { outcome, memories } = await distillWithGemini(block);
      stats.blockOutcomes[outcome] = (stats.blockOutcomes[outcome] ?? 0) + 1;
      stats.memoriesExtracted += memories.length;

      for (const memory of memories) {
        // Skip low importance
        if (memory.importance < 0.5) continue;

        // Dedup check
        let isDup = false;
        try {
          isDup = await isDuplicate(memory.text, sessionKey, "distilled");
        } catch {
          // Fallback: keyword check
          const existing = db.prepare(
            "SELECT id FROM chunks WHERE chunk_type = 'distilled' AND chunk_text LIKE ? LIMIT 1"
          ).get(`%${memory.text.substring(0, 50)}%`);
          isDup = !!existing;
        }

        if (isDup) {
          stats.memoriesDeduplicated++;
          continue;
        }

        // Ingest
        const chunkType = "distilled";
        const tier = memory.importance >= 0.8 ? "working" : "peripheral";
        const today = new Date().toISOString().split("T")[0];

        db.prepare(`
          INSERT INTO chunks (source_file, chunk_text, chunk_type, source_date, metadata, tier, importance, retention_days)
          VALUES (?, ?, ?, ?, ?, ?, ?, NULL)
        `).run(
          `sessions/${agentId}/${sessionKey}`,
          `[${memory.category}|${agentId}] ${memory.text}`,
          chunkType,
          today,
          JSON.stringify({ category: memory.category, source_agent: agentId, session: sessionKey }),
          tier,
          memory.importance
        );

        stats.memoriesIngested++;
        sessionExtracted++;
        incrementMetric("chunks_added");
      }

      await shadow.block({ sessionKey, agentId, blockIndex, nBlocks: blocks.length,
                           messageCount: messages.length, sessionMtimeMs: mtimeMs }, block, memories);

      // Rate limit: ~1 call/sec to Gemini
      await new Promise((r) => setTimeout(r, 1000));
    }

    stats.processedSessions++;

    if (!dryRun) {
      db.prepare(`
        INSERT OR REPLACE INTO session_distill_log
          (session_key, agent, chunks_extracted, message_count, processed_at)
        VALUES (?, ?, ?, ?, datetime('now'))
      `).run(sessionKey, agentId, sessionExtracted, messages.length);
    }

    console.log(`[DISTILL] ${agentId} ${sessionKey.split(":")[1]?.substring(0, 8)} → ${sessionExtracted} memories`);
  }

  shadow.summary();
  console.log(`[DISTILL] Blocks by outcome: ${JSON.stringify(stats.blockOutcomes)}`);
  console.log(`[DISTILL] Done: ${stats.processedSessions} sessions, ${stats.memoriesIngested} ingested, ${stats.memoriesDeduplicated} deduped`);
  recordOutcomes(dryRun, agentIds, lookbackDays, pending.length, stats);
  return stats;
}
