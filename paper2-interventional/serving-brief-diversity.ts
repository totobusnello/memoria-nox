/**
 * D2 — Brief diversity/novelty term (re-rank pós-salience DENTRO do brief).
 *
 * Spec (memoria-nox): specs/2026-06-07-D2-brief-diversity-term.md
 * Origem: D1 (feedback loop do canário, 2026-06-07) + D3 (medição limpa,
 * 2026-06-13). D3 cravou: 83 chunks distintos servem ~6.700 serves/dia
 * (0,18% diversidade), mediana 48d, 19/81 high-pain≥0.9, e 510-931 chunks
 * recentes relevantes nunca servidos. Follow-up rate via search/answer é
 * NÃO-mensurável (3 buscas genuínas / 0 answers em 7d) — gate redesenhado
 * sobre diversidade + freshness + high-pain floor, sem follow-up.
 *
 * Invariantes (§2 da spec — NÃO violar):
 *   1. NÃO forka `calculateSalience` (regra #5/#17 do repo). O termo de
 *      diversidade é re-rank pós-salience APENAS dentro do brief — nunca
 *      um peso novo na fórmula (que afetaria search também).
 *   2. Read-only sobre `chunks` (promessa F1: access_count intocado). A
 *      serve-history vem de `brief_log` (tabela própria).
 *   3. Fail-open: diversidade nunca derruba o priming.
 *   4. High-pain floor: incidents pain ≥ PAIN_FLOOR são imunes ao penalty.
 *
 * Este módulo só carrega lógica PURA (config + penalty + diff). As queries
 * (serveCounts, fetchFreshCandidates) e a integração com buildBrief vivem em
 * brief.ts, onde o pool/pick já existem.
 */

export type DiversityMode = "off" | "shadow" | "active";

export interface DiversityConfig {
  mode: DiversityMode;
  /** Janela "já servido" pro penalty (SQL modifier, ex "-72 hours"). */
  windowSql: string;
  /** Força do novelty penalty. penalty = min(pMax, λ·log1p(n_serves)). */
  lambda: number;
  /** Teto do penalty (≈ 1 termo de salience). Impede zerar candidatos. */
  pMax: number;
  /** pain ≥ painFloor ⇒ penalty = 0 (incidents críticos imunes). */
  painFloor: number;
  /** Nº de slots reservados pra freshness (novidade recente relevante). */
  freshSlots: number;
  /** Piso de relevância pro freshness slot (não trazer lixo recente). */
  freshMinImp: number;
  freshMinPain: number;
  /** Idade máx (dias) pra contar como "recente" no freshness slot (agente). */
  freshMaxAgeDays: number;
  /** Idade máx (dias) do sub-pool curado global (memory/entities/%). Janela
   *  separada e mais longa que a do agente: o entity store é consolidado em
   *  rajadas (escala de semanas), não diário — 7d o deixaria vazio (recheck
   *  2026-06-20: 0 elegíveis ≤14d, 188 ≤21d). */
  freshGlobalMaxAgeDays: number;
}

/** Defaults conservadores calibrados em D3 (2026-06-13). */
export const DIVERSITY_DEFAULTS: Omit<DiversityConfig, "mode"> = {
  windowSql: "-72 hours",
  lambda: 0.05,
  pMax: 0.15,
  painFloor: 0.9,
  freshSlots: 2,
  freshMinImp: 0.7,
  freshMinPain: 0.7,
  freshMaxAgeDays: 7,
  freshGlobalMaxAgeDays: 30,
};

function parseMode(raw: string | undefined): DiversityMode {
  if (raw === "shadow" || raw === "active") return raw;
  return "off";
}

function parseNum(raw: string | undefined, fallback: number): number {
  if (raw === undefined || raw === "") return fallback;
  const n = Number(raw);
  return Number.isFinite(n) ? n : fallback;
}

/** Lê NOX_BRIEF_DIVERSITY* do env; default off + calibração D3. */
export function diversityConfigFromEnv(
  env: Record<string, string | undefined> = process.env,
): DiversityConfig {
  const windowHours = parseNum(env.NOX_BRIEF_DIV_WINDOW_HOURS, 72);
  return {
    mode: parseMode(env.NOX_BRIEF_DIVERSITY),
    windowSql: `-${Math.max(1, Math.round(windowHours))} hours`,
    lambda: parseNum(env.NOX_BRIEF_DIV_LAMBDA, DIVERSITY_DEFAULTS.lambda),
    pMax: parseNum(env.NOX_BRIEF_DIV_PMAX, DIVERSITY_DEFAULTS.pMax),
    painFloor: parseNum(env.NOX_BRIEF_DIV_PAIN_FLOOR, DIVERSITY_DEFAULTS.painFloor),
    freshSlots: Math.max(0, Math.round(parseNum(env.NOX_BRIEF_DIV_FRESH_SLOTS, DIVERSITY_DEFAULTS.freshSlots))),
    freshMinImp: parseNum(env.NOX_BRIEF_DIV_FRESH_MIN_IMP, DIVERSITY_DEFAULTS.freshMinImp),
    freshMinPain: parseNum(env.NOX_BRIEF_DIV_FRESH_MIN_PAIN, DIVERSITY_DEFAULTS.freshMinPain),
    freshMaxAgeDays: Math.max(1, Math.round(parseNum(env.NOX_BRIEF_DIV_FRESH_MAX_AGE_DAYS, DIVERSITY_DEFAULTS.freshMaxAgeDays))),
    freshGlobalMaxAgeDays: Math.max(1, Math.round(parseNum(env.NOX_BRIEF_DIV_FRESH_GLOBAL_MAX_AGE_DAYS, DIVERSITY_DEFAULTS.freshGlobalMaxAgeDays))),
  };
}

/**
 * Novelty penalty (mechanism A — LEGACY, superseded by coverage 2026-06-26).
 * Satura em log pra que servir 2.000× ≈ servir 100×; cap em pMax; floor de pain.
 *
 * Por que foi aposentado como ranker do fresh slot: o cap `pMax` (0.15) é menor
 * que o gap de salience-base entre os poucos outliers (decisões imp 0.9 + access
 * alto) e o corpo homogêneo do pool curado. Sob volume de produção (~6.8k
 * briefs/dia) o penalty satura em ~1 janela de 72h e o pick reconverge ao
 * top-salience: o gate active mediu rotação 146 (24/06) → 67 (25/06) → 3 (26/06).
 * A cobertura por tempo-desde-serve (`coverageCompare`) não tem teto e gira o
 * pool inteiro. Mantido exportado: matemática pura, base dos testes de unidade e
 * disponível como knob (`NOX_BRIEF_DIV_*`) caso um pool sem outliers o justifique.
 */
export function noveltyPenalty(nServes: number, pain: number, cfg: DiversityConfig): number {
  if (pain >= cfg.painFloor) return 0; // high-pain floor (invariante #4)
  if (nServes <= 0) return 0;
  return Math.min(cfg.pMax, cfg.lambda * Math.log1p(nServes));
}

/** brief_score = salience − penalty (mechanism A LEGACY — ver noveltyPenalty). */
export function briefScore(salience: number, nServes: number, pain: number, cfg: DiversityConfig): number {
  return salience - noveltyPenalty(nServes, pain, cfg);
}

/**
 * Coverage rank (mechanism B' — ranker do fresh slot desde tune(brief) 06-26).
 * Substitui o novelty-penalty: em vez de despriorizar por CONTAGEM de serves —
 * que satura em `pMax` e reconverge sob volume ≫ pool — ordena por TEMPO desde
 * o último serve. Nunca-servido primeiro (cobertura máxima), depois o servido
 * há mais tempo; tie-break por salience DESC (relevância entre iguais). Varre o
 * pool inteiro continuamente, independente do gap de salience, sem teto que
 * sature. Determinístico (sem Math.random): testável e reprodutível. O
 * high-pain floor é honrado a montante pelo pinned-set do pick (invariante #4),
 * não aqui — coverage não rebaixa nada, só ordena por novidade-de-exposição.
 */
export function coverageCompare(
  aLastServedMs: number | null,
  aSalience: number,
  bLastServedMs: number | null,
  bSalience: number,
): number {
  const al = aLastServedMs ?? Number.NEGATIVE_INFINITY; // nunca-servido = "há mais tempo"
  const bl = bLastServedMs ?? Number.NEGATIVE_INFINITY;
  if (al !== bl) return al - bl; // ASC: menos-recentemente-servido primeiro
  return bSalience - aSalience; // tie: maior salience
}

export interface BriefDiff {
  current_ids: number[];
  alt_ids: number[];
  would_enter: number[]; // no alt, não no current
  would_leave: number[]; // no current, não no alt
  fresh_added: number[]; // slots de freshness preenchidos
  churn: number; // |would_enter| (= |would_leave| quando n igual)
}

/** Diff estrutural pro shadow log (gate D2 mede sobre isto + brief_log real). */
export function diffBriefs(
  currentIds: number[],
  altIds: number[],
  freshIds: number[] = [],
): BriefDiff {
  const cur = new Set(currentIds);
  const alt = new Set(altIds);
  const wouldEnter = altIds.filter((id) => !cur.has(id));
  const wouldLeave = currentIds.filter((id) => !alt.has(id));
  return {
    current_ids: currentIds,
    alt_ids: altIds,
    would_enter: wouldEnter,
    would_leave: wouldLeave,
    fresh_added: freshIds,
    churn: wouldEnter.length,
  };
}

/**
 * Split-slot do freshness (parte B, tune(brief) 2026-06-20): intercala
 * (round-robin) dois sub-pools já ranqueados — fresh do agente vs curado global
 * (memory/entities/%) — dedup por id. Garante que os primeiros `freshSlots`
 * picks tragam AMBOS os tipos (ex: 1 recente do agente + 1 lição/decisão global
 * fresca), em vez de o sub-pool de maior salience starvar o outro. Num scope
 * `sessions/<agent>/%` homogêneo o pool do agente realizava só ~2 distintos e o
 * curado global era invisível (gate 2026-06-19). Lógica pura, sem deps.
 */
export function interleaveFresh<T extends { row: { id: number } }>(
  a: T[],
  b: T[],
): T[] {
  const out: T[] = [];
  const seen = new Set<number>();
  const max = Math.max(a.length, b.length);
  for (let i = 0; i < max; i++) {
    for (const arr of [a, b]) {
      const c = arr[i];
      if (c && !seen.has(c.row.id)) {
        seen.add(c.row.id);
        out.push(c);
      }
    }
  }
  return out;
}
