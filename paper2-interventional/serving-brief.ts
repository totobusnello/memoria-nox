/**
 * F1 — GET /api/brief (Session Priming Loop, fase 1)
 *
 * Pointer-pattern priming digest: top-N chunks por salience filtrados por
 * escopo. Toda sessão (agente OpenClaw, Claude Code Mac, qualquer cliente
 * MCP/HTTP) nasce contextualizada sem search cego.
 *
 * Specs (memoria-nox):
 *   - PRD:  specs/2026-06-04-session-priming-loop.md (§6 contrato)
 *   - Impl: specs/2026-06-04-F1-api-brief-implementation.md (T0 findings)
 *
 * Invariantes:
 *   - Read-only sobre `chunks`. NÃO toca `chunks.access_count` — o sinal
 *     orgânico fica 100% puro pro audit mensal do Cipher (high-pain órfãos).
 *     Tracking de serving vai pra tabela própria `brief_log`.
 *   - NÃO altera scoring de search (regra #5 do repo) — consome
 *     `calculateSalience` canônica as-is, sem fork nem pesos próprios.
 *   - Framework-agnostic (mesmo padrão de src/api/conflict.ts): handler puro
 *     testável; api-server.ts faz o dispatch HTTP.
 *
 * Scope mapping (T0 2026-06-04, validado em prod 100.5k chunks):
 *   - agent  → `sessions/<persona>/%`           (cipher 7.6k, atlas 3.8k…)
 *   - scope  → `memory/mac-docs/<scope>/%`      (NUVIVI, PESSOAL, PPR…)
 *            | `shared/imports/Claude/Projetos/<scope>/%`
 *            | `shared/imports/<scope>/%`
 *            | `<scope>/%`                      (namespaces top-level)
 *   - global → sem filtro de path
 *
 * Changelog:
 *   - v1.1 (gate T7): age por source_date; dedup exato (title,one_liner);
 *     strip HTML no one_liner.
 *   - v1.2 (gate F3 real, Nox): (a) collapse de near-dups por Jaccard de
 *     tokens; (b) com `agent`, união garantida agente ∪ scope/global
 *     (~n/2 slots cada, backfill mútuo).
 */

import { randomUUID } from "node:crypto";
import { compareBriefs } from "../lib/epoch-shadow.js";
import { recordShadowComparison } from "../lib/shadow-tracker.js";
import { calculateSalience, type SalienceInput } from "../salience.js";
import {
  type DiversityConfig,
  type BriefDiff,
  coverageCompare,
  diffBriefs,
  diversityConfigFromEnv,
  interleaveFresh,
} from "./brief-diversity.js";
import {
  boostsParaCandidatos,
  carregarDesignados,
  doseDeShadow,
  epochInicioISO,
  epochInicioMs,
  logarDecisaoDeServing,
  parseP2Mode,
  resolverBraco,
} from "../paper2/brief-outcome.js";

// ─── Tipos estruturais (espelha lib/conflict/db.ts::DBHandle) ────────────────

interface PreparedStatement {
  all(...args: unknown[]): unknown[];
  get(...args: unknown[]): unknown;
  run(...args: unknown[]): unknown;
}

export interface BriefDb {
  prepare(sql: string): PreparedStatement;
  exec(sql: string): void;
}

// ─── Contrato ────────────────────────────────────────────────────────────────

export interface BriefItem {
  id: number;
  title: string;
  one_liner: string;
  type: string | null;
  pain: number;
  salience: number;
  age_days: number;
}

export interface BriefResult {
  scope: string;
  agent?: string;
  generated_at: string;
  items: BriefItem[];
  token_estimate: number;
}

export type BriefResponse =
  | { status: number; body: unknown }
  | { status: number; text: string };

// ─── Constantes ──────────────────────────────────────────────────────────────

const DEFAULT_N = 10;
const MAX_N = 25;
/** Pool de candidatos pré-ranqueado em SQL antes do re-rank exato por salience.
 *  Proxy barato (importance + pain + access binário) aproxima a fórmula v2
 *  aditiva; 500 rows re-ranqueadas em JS mantém p50 < 100ms em corpus 100k+. */
const CANDIDATE_POOL = 500;
/** Pool de candidatos do freshness slot (parte B). Cobre todo o pool elegível
 *  (≈189 curados globais hoje) pra o novelty-penalty escolher os menos-servidos.
 *  O valor antigo (freshSlots*4=8, por recência de ingest) enxergava só ~2% do
 *  pool — tune(brief) 06-18. Bump 100→400 quando o fresh trocou exclusão-dura por
 *  penalty-suave (senão o LIMIT cortaria não-servidos sob proxy uniforme) —
 *  tune(brief) 06-23. */
const FRESH_CANDIDATE_POOL = 400;
/** Sub-pool curado global do freshness slot: lições/decisões/people no entity
 *  store. Invisível aos briefs `global+agent` — scopePatterns só devolve
 *  `sessions/<agent>/%` quando scope=global, nunca `memory/entities/%`. O
 *  split-slot (interleaveFresh) destrava conhecimento curado fresco que nenhum
 *  agente via, com janela própria (freshGlobalMaxAgeDays). tune(brief) 06-20. */
/**
 * Sub-pool global do caminho de cobertura.
 *
 * ⚠️ `memory/lessons.md` adicionado 2026-08-20. O padrão original apontava só
 * para `memory/entities/%`, o formato de 3 seções — e a memória migrou para o
 * agregado plano `memory/lessons.md` em julho/2026. O padrão ficou **órfão** e o
 * mecanismo de cobertura (2 de 10 slots do brief) ficou **inerte por semanas**:
 * 0 candidatos elegíveis sob o padrão antigo, contra 52 em `memory/lessons.md` e
 * 103+ no total fora dos padrões.
 *
 * Não é feature nova — é restaurar comportamento que o D2/D3 construiu e que uma
 * migração de formato quebrou em silêncio.
 *
 * `memory/decisions.md` e os outros agregados planos foram deixados de fora de
 * propósito: `decisions.md` tem `importance` 0,95 (salience 0,7925 contra 0,7347
 * das lições), o que elevaria a barra e tornaria o pool heterogêneo. Um pool
 * homogêneo é o que faz a barra ser um número estável.
 */
const GLOBAL_FRESH_PATTERNS = ["memory/entities/%", "memory/lessons.md"];
/** Budget do digest em tokens estimados (chars/4) — princípio 4.3 do PRD. */
const TOKEN_BUDGET = 1200;
const ONE_LINER_MAX = 140;

const SCOPE_RE = /^[\p{L}\p{N}][\p{L}\p{N}._-]{0,63}$/u;
const AGENT_RE = /^[a-z0-9][a-z0-9-]{0,31}$/;
const SINCE_RE = /^(\d{1,4})([hdw])$/;

// ─── Validação e parsing ─────────────────────────────────────────────────────

export interface BriefParams {
  scope: string;
  agent?: string;
  n: number;
  format: "json" | "text";
  sinceSql?: string;
}

export function parseBriefParams(
  q: Record<string, string>,
): { ok: true; params: BriefParams } | { ok: false; error: string } {
  const scope = (q.scope || "").trim();
  if (!scope) return { ok: false, error: "scope é obrigatório" };
  if (!SCOPE_RE.test(scope)) {
    return { ok: false, error: "scope inválido (alfanumérico + ._- , máx 64)" };
  }

  let agent: string | undefined;
  if (q.agent !== undefined && q.agent !== "") {
    if (!AGENT_RE.test(q.agent)) {
      return { ok: false, error: "agent inválido (slug a-z0-9-, máx 32)" };
    }
    agent = q.agent;
  }

  let n = DEFAULT_N;
  if (q.n !== undefined && q.n !== "") {
    const parsed = parseInt(q.n, 10);
    if (!Number.isFinite(parsed) || parsed < 1) {
      return { ok: false, error: "n inválido (inteiro ≥ 1)" };
    }
    n = Math.min(parsed, MAX_N);
  }

  const format = q.format === "text" ? "text" : "json";

  let sinceSql: string | undefined;
  if (q.since !== undefined && q.since !== "") {
    const m = SINCE_RE.exec(q.since);
    if (!m) return { ok: false, error: "since inválido (ex: 24h, 30d, 2w)" };
    const unit = { h: "hours", d: "days", w: "days" }[m[2] as "h" | "d" | "w"];
    const qty = m[2] === "w" ? parseInt(m[1], 10) * 7 : parseInt(m[1], 10);
    sinceSql = `-${qty} ${unit}`;
  }

  return { ok: true, params: { scope, agent, n, format, sinceSql } };
}

// ─── Scope → LIKE patterns ───────────────────────────────────────────────────

/** Escapa metachars do LIKE (`%`, `_`, `\`) no trecho dinâmico — os wildcards
 *  `%` dos patterns são adicionados depois. Queries usam `ESCAPE '\'`. */
export function escapeLike(s: string): string {
  return s.replace(/[\\%_]/g, (c) => `\\${c}`);
}

export function scopePatterns(scope: string, agent?: string): string[] {
  const patterns: string[] = [];
  if (scope !== "global") {
    const esc = escapeLike(scope);
    patterns.push(
      `memory/mac-docs/${esc}/%`,
      `shared/imports/Claude/Projetos/${esc}/%`,
      `shared/imports/${esc}/%`,
      `${esc}/%`,
    );
  }
  if (agent) patterns.push(`sessions/${escapeLike(agent)}/%`);
  return patterns;
}

// ─── Extração de digest ──────────────────────────────────────────────────────

/** v1.2a — assinatura de tokens pra collapse de near-duplicates.
 *  Gate F3 real (2026-06-04): 4/10 itens do brief do Nox eram variantes de
 *  "Ler/Usar/Seguir HEARTBEAT.md ... estritamente" — dedup exato não pega.
 *
 *  Métrica: CONTAINMENT (interseção / menor assinatura), não Jaccard —
 *  variantes curtas vs longas do mesmo assunto diluem o Jaccard mas mantêm
 *  containment alto. Guarda: assinaturas < MIN_SIG tokens só dedupam por
 *  match exato (containment em sets minúsculos over-colapsa). Mantém sempre
 *  o candidato de maior salience. */
const NEAR_DUP_CONTAINMENT = 0.6;
const MIN_SIG_TOKENS = 3;

export function tokenSignature(title: string, oneLiner: string): Set<string> {
  const tokens = `${title} ${oneLiner}`
    .toLowerCase()
    .split(/[^\p{L}\p{N}.]+/u)
    .filter((t) => t.length >= 4);
  return new Set(tokens);
}

export function isNearDup(a: Set<string>, b: Set<string>): boolean {
  if (a.size < MIN_SIG_TOKENS || b.size < MIN_SIG_TOKENS) return false;
  let inter = 0;
  for (const t of a) if (b.has(t)) inter++;
  return inter / Math.min(a.size, b.size) >= NEAR_DUP_CONTAINMENT;
}

/** Primeira linha "de conteúdo": pula vazias, fences de frontmatter (---) e
 *  marcação estrutural; strip de tags HTML (docs OCR/import vazam <u> etc.),
 *  heading/list markers; cap ONE_LINER_MAX. */
export function extractOneLiner(text: string | null | undefined): string {
  if (!text) return "";
  for (const raw of text.split("\n")) {
    const line = raw.replace(/<[^>]*>/g, " ").replace(/\s+/g, " ").trim();
    if (!line || line === "---" || line === "```") continue;
    const cleaned = line
      .replace(/^#{1,6}\s+/, "")
      .replace(/^[-*>]\s+/, "")
      .replace(/\*\*/g, "")
      .trim();
    if (!cleaned) continue;
    return cleaned.length > ONE_LINER_MAX
      ? cleaned.slice(0, ONE_LINER_MAX - 1) + "…"
      : cleaned;
  }
  return "";
}

/** Datas do SQLite vêm "YYYY-MM-DD HH:MM:SS" (UTC) ou "YYYY-MM-DD" (source_date).
 *  Date.parse direto trata date-only como UTC; o formato com espaço precisa
 *  virar ISO + Z explícito pra não cair em timezone local. */
export function parseDbDateMs(ref: string): number {
  if (ref.includes(" ")) return Date.parse(ref.replace(" ", "T") + "Z");
  return Date.parse(ref);
}

export function titleFromSourceFile(sourceFile: string | null | undefined): string {
  if (!sourceFile) return "(sem origem)";
  const base = sourceFile.split("/").pop() || sourceFile;
  return base.replace(/\.(md|txt|json|jsonl)$/i, "");
}

// ─── brief_log (única escrita do endpoint — schema próprio, zero ALTER) ─────

let briefLogReady = false;

export function ensureBriefLog(db: BriefDb): void {
  if (briefLogReady) return;
  db.exec(`
    CREATE TABLE IF NOT EXISTS brief_log (
      id INTEGER PRIMARY KEY,
      chunk_id INTEGER NOT NULL,
      scope TEXT NOT NULL,
      agent TEXT,
      served_at TEXT NOT NULL DEFAULT (datetime('now')),
      brief_id TEXT
    );
    CREATE INDEX IF NOT EXISTS idx_brief_log_chunk ON brief_log(chunk_id, served_at);
  `);
  // Migracao idempotente do `brief_id` (P2S1 T2b) para instalacoes que ja
  // tinham a tabela. Sem ele, dois briefs servidos DENTRO DO MESMO SEGUNDO sao
  // indistinguiveis: `served_at` tem resolucao de 1s e nao ha outra chave.
  // Medido em 2026-07-25: acontece em ~9% dos briefs, e agrupar por
  // (scope, agent, served_at) funde os dois e produz falso positivo de
  // "chunk repetido" (10,34% que nao existe). O desfecho do Paper 2 e medido
  // POR BRIEF, entao isso precisa existir antes do estudo comecar.
  // ADD COLUMN e O(1) no SQLite e a coluna e nullable: linhas antigas ficam
  // NULL e nada existente quebra.
  const briefLogCols = db
    .prepare("SELECT name FROM pragma_table_info('brief_log')")
    .all() as Array<{ name: string }>;
  if (!briefLogCols.some((c) => c.name === "brief_id")) {
    db.exec("ALTER TABLE brief_log ADD COLUMN brief_id TEXT");
  }
  db.exec(
    "CREATE INDEX IF NOT EXISTS idx_brief_log_brief ON brief_log(brief_id)",
  );
  briefLogReady = true;
}

/** Test-only: reseta o memo de criação (cada DB de teste é novo). */
export function _resetBriefLogMemo(): void {
  briefLogReady = false;
}

// ─── Core ────────────────────────────────────────────────────────────────────

interface CandidateRow {
  id: number;
  source_file: string | null;
  chunk_text: string | null;
  chunk_type: string | null;
  source_type: string | null;
  tier: string | null;
  pain: number | null;
  importance: number | null;
  retention_days: number | null;
  source_date: string | null;
  created_at: string | null;
  updated_at: string | null;
  last_accessed_at: string | null;
  access_count: number | null;
}

interface RankedCandidate {
  row: CandidateRow;
  salience: number;
  /** D2: salience − novelty penalty (re-rank pós-salience). Default = salience. */
  briefScore?: number;
  /** D2: marcado quando entrou via freshness slot (parte B). */
  fresh?: boolean;
}

interface Picked extends RankedCandidate {
  title: string;
  oneLiner: string;
}

/** Pool de candidatos: pré-rank SQL barato (proxy da fórmula v2 aditiva)
 *  → LIMIT 500 → re-rank exato com calculateSalience. */
function fetchRankedPool(
  db: BriefDb,
  patterns: string[],
  sinceSql: string | undefined,
  nowMs: number,
): RankedCandidate[] {
  const where: string[] = [];
  const args: unknown[] = [];
  if (patterns.length > 0) {
    where.push(`(${patterns.map(() => "source_file LIKE ? ESCAPE '\\'").join(" OR ")})`);
    args.push(...patterns);
  }
  if (sinceSql) {
    where.push("updated_at >= datetime('now', ?)");
    args.push(sinceSql);
  }
  const whereSql = where.length ? `WHERE ${where.join(" AND ")}` : "";

  const rows = db
    .prepare(
      `SELECT id, source_file, chunk_text, chunk_type, source_type, tier,
              pain, importance, retention_days, source_date, created_at,
              updated_at, last_accessed_at, access_count
         FROM chunks
         ${whereSql}
        ORDER BY (0.55 * COALESCE(importance, 0.5)
                + 0.10 * COALESCE(pain, 0.2)
                + CASE WHEN COALESCE(access_count, 0) > 0 THEN 0.1 ELSE 0 END) DESC,
                 updated_at DESC
        LIMIT ${CANDIDATE_POOL}`,
    )
    .all(...args) as CandidateRow[];

  return rows
    .map((r) => ({
      row: r,
      salience: calculateSalience(r as SalienceInput, nowMs),
    }))
    .sort((a, b) => b.salience - a.salience);
}

/** Seleção com dedup global (exato por id + near-dup por assinatura de tokens,
 *  v1.2a) — mantém sempre o candidato de maior score. Parametrizado por
 *  `scoreOf` (salience pura em todos os modos desde tune 06-26) e por freshness
 *  slots (parte B): reserva `freshSlots` dos `n`, preenchidos com `freshPool`
 *  (coverage) após os slots principais; backfill cobre fresh insuficiente. Com
 *  freshSlots=0 reproduz exatamente o pick v1.2 (off bit-idêntico). */
function pickDedup(
  pools: RankedCandidate[][],
  quotas: number[],
  n: number,
  scoreOf: (c: RankedCandidate) => number,
  freshPool: RankedCandidate[] = [],
  freshSlots = 0,
  pinnedIds: Set<number> = new Set(),
): Picked[] {
  const picked: Picked[] = [];
  const seenIds = new Set<number>();
  const seenKeys = new Set<string>();
  const seenSigs: Set<string>[] = [];

  const tryPick = (cand: RankedCandidate, asFresh = false): boolean => {
    if (seenIds.has(cand.row.id)) return false;
    const title = titleFromSourceFile(cand.row.source_file);
    const oneLiner = extractOneLiner(cand.row.chunk_text);
    // Dedup exato (v1.1) — cinto de segurança pra assinaturas < MIN_SIG_TOKENS.
    const key = `${title}|${oneLiner}`;
    if (seenKeys.has(key)) return false;
    const sig = tokenSignature(title, oneLiner);
    for (const s of seenSigs) if (isNearDup(s, sig)) return false;
    seenIds.add(cand.row.id);
    seenKeys.add(key);
    seenSigs.push(sig);
    picked.push({ ...cand, fresh: asFresh || cand.fresh, title, oneLiner });
    return true;
  };

  const mainTarget = Math.max(0, n - freshSlots);

  // Fase 0 (D2 floor — invariante #4): pinned = high-pain que JÁ estavam no
  // brief atual. Entram primeiro e nunca são expulsos pelo freshness slot (que
  // reserva slots e empurraria os últimos por salience pra fora). Sem isto, B
  // podia esconder incident pain≥0.9. Pinned excedente come dos fresh slots.
  if (pinnedIds.size > 0) {
    const pinnedCands = pools
      .flat()
      .filter((c) => pinnedIds.has(c.row.id))
      .sort((a, b) => scoreOf(b) - scoreOf(a));
    for (const c of pinnedCands) {
      if (picked.length >= n) break;
      tryPick(c);
    }
  }

  // Fase 1: cotas por pool (ordem de score dentro de cada pool).
  pools.forEach((pool, i) => {
    let got = 0;
    for (const cand of pool) {
      if (got >= quotas[i] || picked.length >= mainTarget) break;
      if (tryPick(cand)) got++;
    }
  });
  // Fase 2: backfill até mainTarget com as sobras de todos os pools (score global).
  if (picked.length < mainTarget) {
    const leftovers = pools.flat().sort((a, b) => scoreOf(b) - scoreOf(a));
    for (const cand of leftovers) {
      if (picked.length >= mainTarget) break;
      tryPick(cand);
    }
  }
  // Fase 3 (D2 parte B): freshness slots — novidade recente relevante.
  let freshGot = 0;
  for (const cand of freshPool) {
    if (freshGot >= freshSlots || picked.length >= n) break;
    if (tryPick(cand, true)) freshGot++;
  }
  // Fase 4: backfill restante até n (fresh insuficiente cai pros pools).
  if (picked.length < n) {
    const leftovers = pools.flat().sort((a, b) => scoreOf(b) - scoreOf(a));
    for (const cand of leftovers) {
      if (picked.length >= n) break;
      tryPick(cand);
    }
  }
  picked.sort((a, b) => scoreOf(b) - scoreOf(a));
  return picked;
}

function toItems(picked: Picked[], nowMs: number): BriefItem[] {
  return picked.map(({ row, salience, title, oneLiner }) => {
    // v1.1: idade do CONTEÚDO (source_date ?? created_at), não do último toque.
    const ref = row.source_date ?? row.created_at ?? row.updated_at;
    const refMs = ref ? parseDbDateMs(ref) : NaN;
    const ageDays = Number.isFinite(refMs)
      ? Math.max(0, Math.floor((nowMs - refMs) / 86_400_000))
      : 0;
    return {
      id: row.id,
      title,
      one_liner: oneLiner,
      type: row.chunk_type,
      pain: row.pain ?? 0.2,
      salience: Math.round(salience * 10_000) / 10_000,
      age_days: ageDays,
    };
  });
}

function assembleResult(params: BriefParams, items: BriefItem[], nowMs: number): BriefResult {
  const tokenEstimate = Math.ceil(
    items.reduce((acc, i) => acc + i.title.length + i.one_liner.length + 24, 0) / 4,
  );
  return {
    scope: params.scope,
    ...(params.agent ? { agent: params.agent } : {}),
    generated_at: new Date(nowMs).toISOString(),
    items,
    token_estimate: tokenEstimate,
  };
}

/** Monta os pools (união agente ∪ scope/global) + cotas — v1.2b. */
function buildPools(
  db: BriefDb,
  params: BriefParams,
  nowMs: number,
): { pools: RankedCandidate[][]; quotas: number[] } {
  const scopeOnly = scopePatterns(params.scope);
  const pools: RankedCandidate[][] = [];
  const quotas: number[] = [];
  if (params.agent) {
    pools.push(fetchRankedPool(db, scopePatterns("global", params.agent), params.sinceSql, nowMs));
    quotas.push(Math.ceil(params.n / 2));
    pools.push(fetchRankedPool(db, scopeOnly, params.sinceSql, nowMs));
    quotas.push(Math.floor(params.n / 2));
  } else {
    pools.push(fetchRankedPool(db, scopeOnly, params.sinceSql, nowMs));
    quotas.push(params.n);
  }
  return { pools, quotas };
}

export function buildBrief(
  db: BriefDb,
  params: BriefParams,
  nowMs: number = Date.now(),
): BriefResult {
  // v1.2b: com `agent`, o brief é UNIÃO GARANTIDA — ~metade dos slots pro
  // pool do agente, ~metade pro scope/global, backfill mútuo se um vier magro.
  const { pools, quotas } = buildPools(db, params, nowMs);
  const picked = pickDedup(pools, quotas, params.n, (c) => c.salience);
  return assembleResult(params, toItems(picked, nowMs), nowMs);
}

// ─── D2: serve-history + freshness (queries; lógica pura em brief-diversity) ──

/** Parte A — nº de serves por chunk na janela T (1 query agregada, índice
 *  idx_brief_log_chunk). Read-only sobre brief_log; tabela própria. */
export function serveCounts(
  db: BriefDb,
  ids: number[],
  windowSql: string,
): Map<number, number> {
  const counts = new Map<number, number>();
  if (ids.length === 0) return counts;
  try {
    const placeholders = ids.map(() => "?").join(",");
    const rows = db
      .prepare(
        `SELECT chunk_id, COUNT(*) AS n
           FROM brief_log
          WHERE chunk_id IN (${placeholders})
            AND served_at > datetime('now', ?)
          GROUP BY chunk_id`,
      )
      .all(...ids, windowSql) as { chunk_id: number; n: number }[];
    for (const r of rows) counts.set(r.chunk_id, r.n);
  } catch {
    // fail-open (invariante #3): sem serve-history ⇒ penalty 0 pra todos.
  }
  return counts;
}

/** Parte B — candidatos de freshness: recentes e relevantes, re-ranqueados por
 *  COVERAGE (mechanism B', tune 06-26): tempo-desde-último-serve, nunca-servido
 *  primeiro, tie por salience. Sem teto que sature — varre o pool inteiro
 *  continuamente. Substitui o novelty-penalty (mechanism A), que sob volume ≫
 *  pool saturava em pMax e reconvergia ao top-salience em ~1 janela de 72h (gate
 *  active 06-24→26: rotação 146→67→3). A exclusão-dura anterior (`id NOT IN
 *  brief_log`) era pior ainda — esvaziava o pool num dia (190 no flip → 1). O
 *  high-pain floor é honrado a montante pelo pinned-set do pick (não há demote
 *  aqui a anular). Exportado pra teste de unidade. */
/**
 * Provedor de ajuste de score para o ranking de cobertura (estagio (b)).
 * Recebe os candidatos com a salience BASE e devolve id -> ajuste aditivo.
 * Injetado de fora para que este modulo nao conheca o Paper 2.
 */
export type ProvedorDeBoost = (cands: { id: number }[]) => Map<number, number>;

/**
 * Ordena o pool de cobertura e descarta `lastServedMs`.
 *
 * Sem `provedor`, o score efetivo E `salience` -- a ordenacao fica identica a
 * anterior por construcao, nao so por teste. E essa a garantia de invariancia do
 * caminho de controle.
 */
function ordenarCobertura(
  ranked: (RankedCandidate & { lastServedMs: number | null })[],
  provedor?: ProvedorDeBoost,
): RankedCandidate[] {
  const boosts = provedor
    ? provedor(ranked.map((c) => ({ id: c.row.id })))
    : undefined;
  const eff = (c: RankedCandidate & { lastServedMs: number | null }) =>
    c.salience + (boosts?.get(c.row.id) ?? 0);
  ranked.sort((a, b) => coverageCompare(a.lastServedMs, eff(a), b.lastServedMs, eff(b)));
  return ranked.map(({ lastServedMs: _drop, ...c }) => c);
}

export function fetchFreshCandidates(
  db: BriefDb,
  patterns: string[],
  cfg: DiversityConfig,
  nowMs: number,
  /**
   * Handle do store VIVO para o serving-state (P2S1 T3). Quando `db` é um
   * snapshot de epoch, `brief_log` não está nele — e nao pode estar, porque a
   * rotação de cobertura precisa continuar viva dentro do epoch (achado A3).
   *
   * Omitido ou igual a `db` ⇒ caminho original, query única, bit-idêntico.
   * Diferente ⇒ duas queries + junção em JS, porque better-sqlite3 não
   * atravessa bancos com ATTACH de forma confiável.
   */
  liveForServeState?: BriefDb,
  /** Paper 2, componente 2: ajuste aditivo no estagio (b). */
  provedorDeBoost?: ProvedorDeBoost,
): RankedCandidate[] {
  const where: string[] = [];
  const args: unknown[] = [];
  if (patterns.length > 0) {
    where.push(`(${patterns.map(() => "source_file LIKE ? ESCAPE '\\'").join(" OR ")})`);
    args.push(...patterns);
  }
  where.push("(COALESCE(importance, 0) >= ? OR COALESCE(pain, 0) >= ?)");
  args.push(cfg.freshMinImp, cfg.freshMinPain);
  where.push(
    "julianday('now') - julianday(COALESCE(source_date, created_at)) <= ?",
  );
  args.push(cfg.freshMaxAgeDays);

  const split = liveForServeState !== undefined && liveForServeState !== db;

  if (split) {
    try {
      // Sem last_served aqui: ele vive no outro banco. Traz-se o conjunto
      // elegível inteiro e faz-se o corte em JS, replicando a ordenação que o
      // SQLite aplicava. Escala: medido em produção 2026-07-26, o WHERE devolve
      // 170 linhas (janela do agente) e 693 (global) — o teto abaixo é rede,
      // não regime de operação.
      const elegiveis = db
        .prepare(
          `SELECT id, source_file, chunk_text, chunk_type, source_type, tier,
                  pain, importance, retention_days, source_date, created_at,
                  updated_at, last_accessed_at, access_count
             FROM chunks
            WHERE ${where.join(" AND ")}
            LIMIT ${FRESH_CANDIDATE_POOL * 25}`,
        )
        .all(...args) as CandidateRow[];

      if (elegiveis.length === 0) return [];

      // serving-state do LIVE, só para os ids que interessam
      const ids = elegiveis.map((r) => r.id);
      const servedAt = new Map<number, string>();
      const CHUNK = 500; // teto de variáveis por statement no SQLite
      for (let i = 0; i < ids.length; i += CHUNK) {
        const lote = ids.slice(i, i + CHUNK);
        const linhas = liveForServeState!
          .prepare(
            `SELECT chunk_id, MAX(served_at) AS last_served
               FROM brief_log
              WHERE chunk_id IN (${lote.map(() => "?").join(",")})
              GROUP BY chunk_id`,
          )
          .all(...lote) as Array<{ chunk_id: number; last_served: string | null }>;
        for (const l of linhas) if (l.last_served) servedAt.set(l.chunk_id, l.last_served);
      }

      // Replica `ORDER BY last_served ASC, <salience-expr> DESC` do SQLite.
      // Em ASC o SQLite põe NULL primeiro — nunca-servido lidera, que é o
      // mecanismo de cobertura. Inverter isso mataria a rotação.
      const salienceExpr = (r: CandidateRow): number =>
        0.55 * (r.importance ?? 0.5) +
        0.10 * (r.pain ?? 0.2) +
        ((r.access_count ?? 0) > 0 ? 0.1 : 0);

      const ordenado = elegiveis
        .map((r) => ({ r, ls: servedAt.get(r.id) ?? null }))
        .sort((a, b) => {
          if (a.ls === null && b.ls !== null) return -1;
          if (a.ls !== null && b.ls === null) return 1;
          if (a.ls !== null && b.ls !== null && a.ls !== b.ls) return a.ls < b.ls ? -1 : 1;
          return salienceExpr(b.r) - salienceExpr(a.r);
        })
        .slice(0, FRESH_CANDIDATE_POOL);

      const ranked = ordenado.map(({ r, ls }) => ({
        row: r,
        salience: calculateSalience(r as SalienceInput, nowMs),
        fresh: true as const,
        lastServedMs: ls ? parseDbDateMs(ls) : null,
      }));
      return ordenarCobertura(ranked, provedorDeBoost);
    } catch {
      return []; // fail-open, igual ao caminho original
    }
  }

  try {
    // O LIMIT corta pelos MENOS-recentemente-servidos (last_served ASC ⇒ NULLs
    // first em SQLite): assim a janela de 400 candidatos rotaciona com o tráfego
    // (o que acabou de ser servido sai do topo, o nunca-servido sobe) e o pool
    // inteiro elegível é varrido ao longo do tempo — não um subconjunto congelado
    // por rowid sob datas empatadas (era o caso: todo o entity store com
    // created_at idêntico cabia num LIMIT por proxy estável).
    const rows = db
      .prepare(
        `SELECT id, source_file, chunk_text, chunk_type, source_type, tier,
                pain, importance, retention_days, source_date, created_at,
                updated_at, last_accessed_at, access_count,
                (SELECT MAX(bl.served_at) FROM brief_log bl
                  WHERE bl.chunk_id = chunks.id) AS last_served
           FROM chunks
          WHERE ${where.join(" AND ")}
          ORDER BY last_served ASC,
                   (0.55 * COALESCE(importance, 0.5)
                  + 0.10 * COALESCE(pain, 0.2)
                  + CASE WHEN COALESCE(access_count, 0) > 0 THEN 0.1 ELSE 0 END) DESC
          LIMIT ${FRESH_CANDIDATE_POOL}`,
      )
      .all(...args) as (CandidateRow & { last_served: string | null })[];
    // Coverage rank (mechanism B'): ordena por tempo-desde-último-serve
    // (nunca-servido primeiro), tie por salience. Sem teto que sature — gira a
    // variedade continuamente, ao contrário do novelty-penalty que reconvergia
    // ao top-salience em ~1 janela sob volume ≫ pool (gate 06-24→26: 146→67→3).
    const ranked = rows.map((r) => ({
      row: r as CandidateRow,
      salience: calculateSalience(r as SalienceInput, nowMs),
      fresh: true as const,
      lastServedMs: r.last_served ? parseDbDateMs(r.last_served) : null,
    }));
    return ordenarCobertura(ranked, provedorDeBoost);
  } catch {
    return []; // fail-open
  }
}

/** D2 — buildBrief com diversidade (A novelty penalty + B freshness slot).
 *  Retorna o surface do `mode` + o brief atual + o diff (pra shadow log). */
export function buildBriefDiverse(
  db: BriefDb,
  params: BriefParams,
  cfg: DiversityConfig,
  nowMs: number = Date.now(),
  /** Store vivo p/ serving-state quando `db` e snapshot de epoch (P2S1 T3). */
  liveForServeState?: BriefDb,
  /** Paper 2 componente 2: presente => computa a composicao tratada. */
  provedorDeBoost?: ProvedorDeBoost,
): {
  current: BriefResult;
  alt: BriefResult;
  diff: BriefDiff;
  /** Composicao com W_OUTCOME. Ausente quando nao ha provedor. */
  altBoosted?: BriefResult;
  /** Deslocamento alt -> altBoosted: o contrafactual por brief. */
  diffP2?: BriefDiff;
} {
  // Garante brief_log antes de lê-lo (1ª chamada em DB fresco vem antes do
  // insert de handleBrief; em prod já existe). Idempotente (memo interno).
  ensureBriefLog(db);
  const { pools, quotas } = buildPools(db, params, nowMs);

  // Brief atual (baseline, score = salience) — o que está em prod hoje.
  const currentPicked = pickDedup(pools, quotas, params.n, (c) => c.salience);
  const current = assembleResult(params, toItems(currentPicked, nowMs), nowMs);

  // Mechanism A (novelty penalty sobre os pools) APOSENTADO — tune(brief) 06-26.
  // O pick principal volta a salience pura: relevância estável no brief base. A
  // diversidade fica concentrada no fresh slot (coverage), que é onde cobertura
  // pertence. Aplicar o penalty ao pool inteiro despriorizava conteúdo de alta
  // relevância E reconvergia mesmo assim sob volume ≫ pool (gate active 06-24→26:
  // distinct entity 146→67→3 — o penalty saturava em pMax < gap de salience). Ver
  // brief-diversity.ts::noveltyPenalty para o histórico e o knob residual.

  // Parte B: pool de freshness — split-slot (tune(brief) 2026-06-20). Dois
  // sub-pools intercalados garantem que os freshSlots tragam tanto recente do
  // agente quanto curado global fresco (memory/entities/%) — antes o pool do
  // agente (scope homogêneo) realizava só ~2 distintos e o curado global era
  // invisível (gate 2026-06-19). O sub-pool global usa janela própria mais
  // longa (entity store consolida em rajadas; 7d o deixaria vazio).
  let freshPool: RankedCandidate[] = [];
  if (cfg.freshSlots > 0) {
    const agentFreshPatterns = params.agent
      ? scopePatterns(params.scope, params.agent)
      : scopePatterns(params.scope);
    const agentFresh = fetchFreshCandidates(db, agentFreshPatterns, cfg, nowMs, liveForServeState);
    const globalFresh = fetchFreshCandidates(
      db,
      GLOBAL_FRESH_PATTERNS,
      { ...cfg, freshMaxAgeDays: cfg.freshGlobalMaxAgeDays },
      nowMs,
      liveForServeState,
    );
    freshPool = interleaveFresh(agentFresh, globalFresh);
  }

  // Floor (invariante #4): high-pain que já estavam no brief atual viram
  // pinned — nunca expulsos pelo freshness slot. Sem isto, B escondia incidents
  // pain≥0.9 (detectado pelo gate report no 1º shadow: would_leave pain=1.0).
  const pinnedIds = new Set(
    current.items.filter((i) => (i.pain ?? 0) >= cfg.painFloor).map((i) => i.id),
  );
  const altPicked = pickDedup(pools, quotas, params.n, (c) => c.salience, freshPool, cfg.freshSlots, pinnedIds);
  const alt = assembleResult(params, toItems(altPicked, nowMs), nowMs);

  const freshIds = altPicked.filter((p) => p.fresh).map((p) => p.row.id);
  const diff = diffBriefs(
    current.items.map((i) => i.id),
    alt.items.map((i) => i.id),
    freshIds,
  );

  // Paper 2 componente 2 -- dual-compute. Funcao-zero sem provedor: nada abaixo
  // roda, e `alt` (o que se serve hoje) sai intocado.
  let altBoosted: BriefResult | undefined;
  let diffP2: BriefDiff | undefined;
  if (provedorDeBoost && cfg.freshSlots > 0) {
    const patternsAgente = params.agent
      ? scopePatterns(params.scope, params.agent)
      : scopePatterns(params.scope);
    const poolB = interleaveFresh(
      fetchFreshCandidates(db, patternsAgente, cfg, nowMs, liveForServeState, provedorDeBoost),
      fetchFreshCandidates(
        db,
        GLOBAL_FRESH_PATTERNS,
        { ...cfg, freshMaxAgeDays: cfg.freshGlobalMaxAgeDays },
        nowMs,
        liveForServeState,
        provedorDeBoost,
      ),
    );
    const pickedB = pickDedup(
      pools, quotas, params.n, (c) => c.salience, poolB, cfg.freshSlots, pinnedIds,
    );
    altBoosted = assembleResult(params, toItems(pickedB, nowMs), nowMs);
    diffP2 = diffBriefs(
      alt.items.map((i) => i.id),
      altBoosted.items.map((i) => i.id),
      pickedB.filter((p) => p.fresh).map((p) => p.row.id),
    );
  }

  return { current, alt, diff, altBoosted, diffP2 };
}

// ─── Render text (stdout-ready pra hooks SessionStart) ──────────────────────

export function renderBriefText(result: BriefResult): string {
  const head = `# nox-mem brief — scope=${result.scope}${
    result.agent ? ` agent=${result.agent}` : ""
  } — ${result.generated_at} — ${result.items.length} items`;
  const lines: string[] = [head];
  let budget = TOKEN_BUDGET - Math.ceil(head.length / 4);
  for (const item of result.items) {
    const line = `[${item.type ?? "?"}|pain ${item.pain.toFixed(1)}|${item.age_days}d] ${item.title} — ${item.one_liner} (chk ${item.id})`;
    const cost = Math.ceil(line.length / 4);
    if (cost > budget) break;
    lines.push(line);
    budget -= cost;
  }
  return lines.join("\n") + "\n";
}

// ─── Handler HTTP-agnostic (api-server.ts despacha) ──────────────────────────

/**
 * `dbs` aceita um handle so (compatibilidade: corpus e serving no mesmo banco,
 * caminho bit-identico ao anterior) ou o par `{corpus, live}` do P2S1 T3, em
 * que o corpus vem de um snapshot de epoch e `brief_log` continua no vivo.
 */
/**
 * Composição do brief, sem NENHUM efeito colateral.
 *
 * Extraída de `handleBrief` para que o braço servido e o braço shadow do P2S1
 * passem pelo **mesmo** código. Se cada um tivesse seu caminho, a divergência
 * medida misturaria diferença de corpus com diferença de implementação, e a
 * comparação não provaria nada.
 *
 * `logDiff` existe porque o log de shadow do D2 vai para stderr: chamar duas
 * vezes duplicaria a linha e inflaria o gate do D2 pela metade.
 */
function composeBrief(
  corpus: BriefDb,
  live: BriefDb,
  params: BriefParams,
  cfg: ReturnType<typeof diversityConfigFromEnv>,
  logDiff: boolean,
): BriefResult {
  // D2 — diversidade (NOX_BRIEF_DIVERSITY=off|shadow|active). off ⇒ caminho
  // v1.2 intocado. shadow ⇒ computa o alt, loga o diff, serve o atual. active
  // ⇒ serve o alt. Fail-open: qualquer erro cai no brief atual (invariante #3).
  if (cfg.mode === "off") return buildBrief(corpus, params);

  // ── Paper 2, componente 2 ──────────────────────────────────────────────────
  // `shadow` NAO resolve braco: mede ativacao antes do sorteio, com dose
  // declarada em NOX_P2_SHADOW_W. `active` resolve braco no ASSIGNMENT.json.
  const p2 = parseP2Mode(process.env.NOX_P2_OUTCOME);
  if (!p2.reconhecido) {
    console.error(
      JSON.stringify({ tag: "p2_mode_invalido", bruto: p2.bruto, efetivo: "off" }),
    );
  }
  let provedor: ProvedorDeBoost | undefined;
  // Uniao dos boosts efetivamente emitidos, e o conjunto designado congelado.
  // Ambos entram no log de replay: o primeiro e o que o codigo FEZ, o segundo e o
  // que a regra DIZ, e a comparacao dos dois e a verificacao.
  const p2BoostPorId = new Map<number, number>();
  let p2Designados = new Set<number>();
  let servirTratado = false;
  let p2w = 0;
  if (p2.mode !== "off") {
    if (p2.mode === "shadow") {
      p2w = doseDeShadow();
    } else {
      const epoch = epochInicioISO(Date.now());
      const r = resolverBraco(epoch);
      if (!r.ok) {
        // NAO neutro: converte tratamento em controle e enviesa pro nulo.
        // Contagem e quantidade pre-comprometida de reporte.
        console.error(
          JSON.stringify({ tag: "p2_arm_unresolved", epoch, motivo: r.motivo ?? null }),
        );
      }
      if (r.arm === "treatment" && r.w > 0) {
        p2w = r.w;
        servirTratado = true;
      }
    }
    if (p2w > 0) {
      // Gate de maturidade: o chunk nao pode agir no epoch em que foi escrito.
      const inicio = epochInicioMs(epochInicioISO(Date.now()));
      // Acumula a UNIAO dos boosts das >=2 invocacoes por brief
      // (`ordenarCobertura` chama em :714 e :753; `fetchFreshCandidates` em
      // :843-851). O Map de cada chamada morre no `sort`, e sem este acumulador o
      // log nao teria como provar que o codigo boostou o conjunto designado — a
      // diferenca entre "a regra diz" e "o codigo fez".
      p2Designados = carregarDesignados().ids;
      provedor = (cands) => {
        const m = boostsParaCandidatos(live, cands, p2w, inicio);
        for (const [id, b] of m) p2BoostPorId.set(id, b);
        return m;
      };
    }
    // `active` sem o D2 `active` nao tem canal: os slots de cobertura nem sao
    // servidos. Grita em vez de fingir que trata.
    if (p2.mode === "active" && cfg.mode !== "active") {
      console.error(
        JSON.stringify({ tag: "p2_sem_canal", diversity_mode: cfg.mode, p2_mode: p2.mode }),
      );
      servirTratado = false;
    }
  }

  try {
    const { current, alt, diff, altBoosted, diffP2 } = buildBriefDiverse(
      corpus, params, cfg, Date.now(), live, provedor,
    );
    // `logDiff` distingue a composicao SERVIDA da comparacao com o snapshot
    // (handleBrief chama composeBrief duas vezes) — sem ele, cada decisao
    // entraria duplicada no log de replay.
    if (logDiff && diffP2 && altBoosted) {
      // Persistido em NDJSON, nao so em stderr: o snapshot e podado em 3 dias e
      // o replay depende so deste log. Inclui as DUAS listas de ids porque o
      // contrafactual por brief E o dado — nao se reconstroi depois.
      logarDecisaoDeServing({
        tag: "p2_outcome",
        epoch: epochInicioISO(Date.now()),
        modo: p2.mode,
        w: p2w,
        servido: servirTratado ? "tratado" : "controle",
        scope: params.scope,
        agent: params.agent ?? null,
        ids_controle: alt.items.map((i) => i.id),
        ids_tratado: altBoosted.items.map((i) => i.id),
        churn: diffP2.churn,
        would_enter: diffP2.would_enter,
        would_leave: diffP2.would_leave,
        fresh_added: diffP2.fresh_added,
        // Aditivos 2026-08-26, item 4 do §5.3. `designated_ids` e o conjunto
        // congelado inteiro (19 ids); `boost_by_id` so os que estavam no pool E
        // passaram o gate de maturidade. `boost_by_id` vazio com
        // `designated_ids` cheio NAO e defeito — e o caso normal de um brief cujo
        // pool nao tocou nenhum designado.
        designated_ids: [...p2Designados].sort((a, b) => a - b),
        boost_by_id: Object.fromEntries(
          [...p2BoostPorId.entries()].sort((a, b) => a[0] - b[0]),
        ),
      });
    }
    if (cfg.mode === "shadow") {
      if (logDiff && diff.churn > 0) {
        // stderr → journalctl. Gate D2 mede sobre estes ids × tabela chunks.
        console.error(
          JSON.stringify({
            tag: "brief_diversity_shadow",
            scope: params.scope,
            agent: params.agent ?? null,
            n: params.n,
            churn: diff.churn,
            would_enter: diff.would_enter,
            would_leave: diff.would_leave,
            fresh_added: diff.fresh_added,
          }),
        );
      }
      return current;
    }
    return servirTratado && altBoosted ? altBoosted : alt;
  } catch {
    return buildBrief(corpus, params); // fail-open
  }
}

export function handleBrief(
  dbs: BriefDb | { corpus: BriefDb; live: BriefDb; shadow?: BriefDb; shadowTakenAt?: string | null },
  query: Record<string, string>,
): BriefResponse {
  const db: BriefDb = "corpus" in dbs ? dbs.corpus : dbs;
  const live: BriefDb = "corpus" in dbs ? dbs.live : dbs;
  const shadowDb: BriefDb | undefined = "corpus" in dbs ? dbs.shadow : undefined;
  const parsed = parseBriefParams(query);
  if (!parsed.ok) return { status: 400, body: { error: parsed.error } };

  const cfg = diversityConfigFromEnv();
  const result = composeBrief(db, live, parsed.params, cfg, true);

  // P2S1 T6 — braço shadow: computa o brief do snapshot e mede a divergência,
  // sem servi-lo e sem tocar em `brief_log`.
  //
  // **A ordem é a parte que importa e não pode ser trocada:** isto roda ANTES
  // do INSERT em `brief_log` logo abaixo. O ordenador de cobertura do D2 lê
  // `MAX(served_at)` do vivo — se o INSERT do brief servido acontecesse antes,
  // o braço shadow veria um estado de serving diferente e o slot fresh giraria
  // por outro motivo. A divergência resultante seria atribuída ao corpus sendo
  // artefato do instrumento, exatamente o falso positivo que o T2 já produziu
  // uma vez com o agrupamento ingênuo de `brief_log`.
  if (shadowDb) {
    try {
      const alt = composeBrief(shadowDb, live, parsed.params, cfg, false);
      const div = compareBriefs(result, alt, "corpus" in dbs ? dbs.shadowTakenAt : null);
      recordShadowComparison(
        "p2s1-epoch-snapshot",
        `${parsed.params.scope}:${parsed.params.agent ?? "*"}:${parsed.params.n}`,
        result.items.map((i) => ({ id: i.id })),
        alt.items.map((i) => ({ id: i.id })),
        {
          identical: div.identical ? 1 : 0,
          jaccard: div.jaccard,
          positional_matches: div.positional_matches,
          n_live: div.n_live,
          n_snapshot: div.n_snapshot,
          snapshot_age_s: div.snapshot_age_s ?? -1,
          only_live: div.only_live.join(","),
          only_snapshot: div.only_snapshot.join(","),
        },
      );
    } catch {
      // O braço shadow NUNCA pode derrubar o servido. Ele é medição.
    }
  }

  // Tracking de serving — brief_log próprio; chunks.access_count INTOCADO.
  try {
    // brief_log SEMPRE no vivo — nunca no snapshot (achado A3).
    ensureBriefLog(live);
    const ins = live.prepare(
      "INSERT INTO brief_log (chunk_id, scope, agent, brief_id) VALUES (?, ?, ?, ?)",
    );
    // Um id por brief servido: torna o slot atribuivel ao seu brief mesmo
    // quando dois briefs caem no mesmo segundo (P2S1 T2b).
    const briefId = randomUUID();
    for (const item of result.items) {
      ins.run(
        item.id,
        parsed.params.scope,
        parsed.params.agent ?? null,
        briefId,
      );
    }
  } catch {
    // fail-open: tracking nunca derruba o priming
  }

  if (parsed.params.format === "text") {
    return { status: 200, text: renderBriefText(result) };
  }
  return { status: 200, body: result };
}