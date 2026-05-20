/**
 * staged-temporal-spike/edits/temporal-retrieval.ts
 *
 * Q1 R&D spike — temporal-aware retrieval path.
 *
 * Não é deploy. Módulo isolado pra investigar proximity-rerank temporal como
 * camada complementar a E13 (specs/2026-05-06-E13-temporal-aware-ranking.md).
 *
 *   detectTemporal(query)            → { isTemporal, anchor, anchorRange, signalSource }
 *   proximityDelta(chunkDate, anchor, sigmaDays) → number em [0, 0.5]
 *   rerankByTemporalProximity(results, query, opts) → SearchResult[]
 *
 * Boost segue padrão aditivo (CLAUDE.md regra crítica #5) — retorna delta
 * que o caller soma a `boostSum`, NUNCA multiplica.
 *
 * Env (opt-in, padrão shadow discipline):
 *   NOX_TEMPORAL_PATH=off|shadow|active   (default: off)
 *   NOX_TEMPORAL_SIGMA_DAYS=30            (gaussian width)
 *   NOX_TEMPORAL_K_RERANK=20              (top-K reranked)
 *
 * Não importa src/db.ts nem search.ts — design isolado, testável em vacuo.
 *
 * ─── HISTORY ─────────────────────────────────────────────────────────────────
 *
 *   v1 (PR #176, 2026-05-20):
 *     PATCH 1 — detector cobre "data em que / dia em que / momento em que"
 *     PATCH 2 — inferAnchorFromTopK (mode YYYY-MM majority threshold ≥50%)
 *     PATCH 3 — proximityBoost gap-aware (substitui fixed *10 multiplier)
 *
 *   Smoke #179 (PR #176 re-rodado contra Q105-Q110): Δ −32.29%. Wins isolados
 *   em Q107/Q109/Q110, mas Q105/Q106 caíram 9-11 posições no rank cada (anchor
 *   inferido `2026-04-15` é viesado pra abril porque o corpus tem volume
 *   abril). Veredito: NÃO deployar v1 como está.
 *
 *   v2 (este arquivo, 2026-05-20 pós PR #179):
 *     PATCH 2 v2 — Anchor guard dois estágios:
 *       Stage A: extractAnchorFromQuery — regex de mês/ano DIRETO da query
 *                (não mais top-K). Confidence alta.
 *       Stage B: inferAnchorFromTopKAge — median (não mode) das datas top-K,
 *                como fallback. Confidence baixa, score multiplicado por 0.3.
 *
 *     PATCH 3 v2 — Confidence tiers no boost:
 *       iso_date                    → 1.0
 *       month_year                  → 0.8
 *       adverbial_keyword_inferred  → 0.6
 *       adverbial_topk_inferred     → 0.3
 *       adverbial / adverbial_inferred (legacy) → 0.0 (off)
 *
 *     Objetivo: queries que mencionam mês/ano explicitamente (mesmo só "abril")
 *     usam Stage A com alta confiança; queries puramente adverbiais usam
 *     Stage B com baixa confiança, limitando o impacto de inferência errada.
 */

// ─── Types ────────────────────────────────────────────────────────────────────

export type TemporalSignalSource =
  | "iso_date"
  | "month_year"
  | "year"
  | "adverbial"
  | "adverbial_inferred"            // legacy v1 (deprecated, kept p/ backward-compat de telemetria)
  | "adverbial_keyword_inferred"    // PATCH 2 v2 Stage A
  | "adverbial_topk_inferred"       // PATCH 2 v2 Stage B
  | null;

export interface TemporalIntent {
  isTemporal: boolean;
  anchor: Date | null;
  anchorRange: [Date, Date] | null;
  signalSource: TemporalSignalSource;
}

export interface TemporalPathMode {
  mode: "off" | "shadow" | "active";
  sigmaDays: number;
  kRerank: number;
}

// Mirror do SearchResult shape staged-1.7a/edits/search.ts — duplicated propositalmente
// pra manter spike standalone (não importar de search.ts).
export interface RerankableResult {
  score: number;
  source_date: string | null;
  created_at?: string | null;
  [k: string]: unknown;
}

// ─── Mode helper ──────────────────────────────────────────────────────────────

export function getTemporalPathMode(): TemporalPathMode {
  const raw = (process.env.NOX_TEMPORAL_PATH ?? "off").toLowerCase();
  const mode: TemporalPathMode["mode"] =
    raw === "shadow" || raw === "active" ? raw : "off";
  const sigmaDays = Number.parseFloat(process.env.NOX_TEMPORAL_SIGMA_DAYS ?? "30");
  const kRerank = Number.parseInt(process.env.NOX_TEMPORAL_K_RERANK ?? "20", 10);
  return {
    mode,
    sigmaDays: Number.isFinite(sigmaDays) && sigmaDays > 0 ? sigmaDays : 30,
    kRerank: Number.isFinite(kRerank) && kRerank > 0 ? kRerank : 20,
  };
}

// ─── Detector ─────────────────────────────────────────────────────────────────
//
// Reuso parcial dos patterns E13 (specs/2026-05-06-E13-temporal-aware-ranking.md)
// + extensão pra anchors temporais explícitos (ISO/mes-ano/ano).
// JS regex \b falha em Unicode (ê, ã, ç) — usar look-around (memoria-nox CLAUDE.md
// memo: feedback_js_regex_unicode_word_boundary_fails).

const ADVERBIAL_PATTERNS: RegExp[] = [
  /(?:^|\s)(quando|que\s+dia|que\s+data|qual\s+(?:data|dia)|em\s+que\s+(?:dia|data))(?=\s|[.,?!]|$)/iu,
  /(?:^|\s)(primeir[ao]|últim[ao]|inicial)(?=\s|[.,?!]|$)/iu,
  /(?:^|\s)(deploy(?:ado|ed|amento)|ativad[ao]|subiu|lançad[ao]|started|aconteceu|inici(?:ou|ado))(?=\s|[.,?!]|$)/iu,
  /(?:^|\s)(when|before|after|during)(?=\s|[.,?!]|$)/iu,
  // PATCH 1 (2026-05-20): cobertura do gap Q107 — "data em que X foi Y"
  // não matchava nenhum pattern existente. Adicionar variantes PT-BR
  // ("data em que / dia em que / momento em que") + EN cognates
  // ("date when / day when / moment when") via look-around Unicode-safe.
  /(?:^|\s)(data\s+em\s+que|dia\s+em\s+que|momento\s+em\s+que)(?=\s|[.,?!]|$)/iu,
  /(?:^|\s)(date\s+when|day\s+when|moment\s+when)(?=\s|[.,?!]|$)/iu,
];

const ISO_DATE = /\b(\d{4})-(\d{2})-(\d{2})\b/;

// PT-BR meses + EN months. Use look-around (Unicode-safe) ao invés de \b.
const MONTH_NAMES: Record<string, number> = {
  janeiro: 0, fevereiro: 1, "março": 2, marco: 2, abril: 3, maio: 4, junho: 5,
  julho: 6, agosto: 7, setembro: 8, outubro: 9, novembro: 10, dezembro: 11,
  january: 0, february: 1, march: 2, april: 3, may: 4, june: 5,
  july: 6, august: 7, september: 8, october: 9, november: 10, december: 11,
  jan: 0, feb: 1, mar: 2, apr: 3, jun: 5,
  jul: 6, aug: 7, sep: 8, sept: 8, oct: 9, nov: 10, dec: 11,
};

// Pre-build single regex from MONTH_NAMES keys (longer first → "setembro" before "set").
const MONTH_REGEX_SOURCE = Object.keys(MONTH_NAMES)
  .sort((a, b) => b.length - a.length)
  .join("|");
const MONTH_YEAR = new RegExp(
  `(?:^|\\s)(${MONTH_REGEX_SOURCE})(?:\\s+(?:de\\s+|of\\s+)?(\\d{4}))?(?=\\s|[.,?!]|$)`,
  "iu",
);
const BARE_YEAR = /(?:^|\s)(20\d{2})(?=\s|[.,?!]|$)/u;

export function detectTemporal(query: string, nowMs: number = Date.now()): TemporalIntent {
  if (!query || query.length < 3) {
    return { isTemporal: false, anchor: null, anchorRange: null, signalSource: null };
  }

  // 1. ISO date — strongest signal, exact anchor
  const isoMatch = query.match(ISO_DATE);
  if (isoMatch) {
    const [_, y, mo, d] = isoMatch;
    const anchor = new Date(Date.UTC(Number(y), Number(mo) - 1, Number(d)));
    if (!Number.isNaN(anchor.getTime())) {
      return {
        isTemporal: true,
        anchor,
        anchorRange: [anchor, anchor],
        signalSource: "iso_date",
      };
    }
  }

  // 2. Month + year (or month alone → fall back to current/most-recent year)
  const monthMatch = query.match(MONTH_YEAR);
  if (monthMatch) {
    const monthKey = monthMatch[1]!.toLowerCase();
    const month = MONTH_NAMES[monthKey];
    if (month !== undefined) {
      const now = new Date(nowMs);
      const explicitYear = monthMatch[2] ? Number(monthMatch[2]) : undefined;
      // Year resolution: explicit > current year (or previous if month is in the future)
      let year = explicitYear;
      if (year === undefined) {
        year = now.getUTCFullYear();
        const candidate = new Date(Date.UTC(year, month, 15));
        if (candidate.getTime() > nowMs) year = year - 1;
      }
      const start = new Date(Date.UTC(year, month, 1));
      const end = new Date(Date.UTC(year, month + 1, 0)); // last day of month
      const midpoint = new Date((start.getTime() + end.getTime()) / 2);
      return {
        isTemporal: true,
        anchor: midpoint,
        anchorRange: [start, end],
        signalSource: "month_year",
      };
    }
  }

  // 3. Adverbial-only (E13 path) — no anchor → still temporal, no proximity rerank
  for (const re of ADVERBIAL_PATTERNS) {
    if (re.test(query)) {
      return {
        isTemporal: true,
        anchor: null,
        anchorRange: null,
        signalSource: "adverbial",
      };
    }
  }

  // 4. Bare year — weak signal, wide range
  const yearMatch = query.match(BARE_YEAR);
  if (yearMatch) {
    const y = Number(yearMatch[1]);
    const start = new Date(Date.UTC(y, 0, 1));
    const end = new Date(Date.UTC(y, 11, 31));
    const midpoint = new Date(Date.UTC(y, 5, 30));
    return {
      isTemporal: true,
      anchor: midpoint,
      anchorRange: [start, end],
      signalSource: "year",
    };
  }

  return { isTemporal: false, anchor: null, anchorRange: null, signalSource: null };
}

// ─── Proximity delta ──────────────────────────────────────────────────────────
//
// Gaussiana truncada: bump máximo de +0.5 em Δdays=0, decai exponencialmente.
// Aditivo (regra #5). Retorna 0 se chunk não tem date data.

export function proximityDelta(
  chunkDateStr: string | null | undefined,
  anchor: Date | null,
  sigmaDays: number = 30,
): number {
  if (!anchor || !chunkDateStr) return 0;
  const chunkMs = Date.parse(chunkDateStr);
  if (!Number.isFinite(chunkMs)) return 0;
  const deltaDays = Math.abs(chunkMs - anchor.getTime()) / (1000 * 60 * 60 * 24);
  // Gaussian: 0.5 * exp(-Δ² / 2σ²)
  const sigma = sigmaDays > 0 ? sigmaDays : 30;
  const exponent = -(deltaDays * deltaDays) / (2 * sigma * sigma);
  return 0.5 * Math.exp(exponent);
}

// ─── Adverbial-to-anchor fallback v2 (PATCH 2 v2) ─────────────────────────────
//
// Quando o detector retorna `signalSource:'adverbial'` SEM anchor parseável,
// o spike v1 (PR #176) inferia mid-month-15 do mês majoritário (mode) do
// top-K. Smoke #179 mostrou que isso vira self-reinforcing bias quando o
// corpus é temporalmente concentrado (Q105 gold maio 2026, anchor inferido
// fixo `2026-04-15` → −32.29% Δ médio).
//
// v2 — duas etapas:
//
//   Stage A: extractAnchorFromQuery — regex de mês/ano DIRETO na string da
//            query (não na metadata do top-K). Cobre "abril 2026", "em maio
//            2026", "may 2026", e fallback de ano isolado ("2026"). Confidence
//            ALTA (0.6 no proximityBoost).
//
//   Stage B: inferAnchorFromTopKAge — median (não mode) das datas dos top-K.
//            Mais robusto a outliers que o mode majority. Não normaliza pra
//            mid-month (preserva o dia exato). Confidence BAIXA (0.3).
//
// Combined em applyProximityRerank (rerankByTemporalProximity): tenta A primeiro;
// se Stage A null, tenta Stage B; se ambos null, NÃO rerank (bail).

const QUERY_MONTH_PATTERNS_PT_BR: Record<string, string> = {
  janeiro: "01", fevereiro: "02", "março": "03", marco: "03",
  abril: "04", maio: "05", junho: "06", julho: "07",
  agosto: "08", setembro: "09", outubro: "10", novembro: "11", dezembro: "12",
};
const QUERY_MONTH_PATTERNS_EN: Record<string, string> = {
  january: "01", february: "02", march: "03", april: "04",
  may: "05", june: "06", july: "07", august: "08",
  september: "09", october: "10", november: "11", december: "12",
};
const QUERY_MONTH_PATTERNS: Record<string, string> = {
  ...QUERY_MONTH_PATTERNS_PT_BR,
  ...QUERY_MONTH_PATTERNS_EN,
};
// Build regex once (longer keys first to avoid prefix collision: "march" before "mar")
const QUERY_MONTH_KEYS_SORTED = Object.keys(QUERY_MONTH_PATTERNS)
  .sort((a, b) => b.length - a.length);
const QUERY_MONTH_YEAR_RX = new RegExp(
  `(?:^|\\s)(${QUERY_MONTH_KEYS_SORTED.join("|")})(?:\\s+(?:de\\s+|of\\s+)?(20\\d{2}))?(?=\\s|[.,?!]|$)`,
  "iu",
);
const QUERY_BARE_YEAR_RX = /(?:^|\s)(20\d{2})(?=\s|[.,?!]|$)/u;

/**
 * Stage A da PATCH 2 v2.
 *
 * Tenta extrair anchor (YYYY-MM-DD) DIRETO da string da query via regex de
 * mês/ano. Retorna `null` se não encontrar.
 *
 * Heuristics:
 *   - "abril 2026" / "em abril 2026" / "abril de 2026" / "april 2026" → "2026-04-15"
 *   - "abril" sozinho → ano implícito = ano atual (se mês passado) ou ano
 *      anterior (se mês futuro), midpoint dia 15
 *   - apenas "2026" sem mês → "2026-06-15" (mid-year)
 *   - nada → null
 */
export function extractAnchorFromQuery(query: string, nowMs: number = Date.now()): string | null {
  if (!query) return null;
  const monthMatch = query.match(QUERY_MONTH_YEAR_RX);
  if (monthMatch) {
    const monthKey = monthMatch[1]!.toLowerCase();
    const monthMM = QUERY_MONTH_PATTERNS[monthKey];
    if (monthMM) {
      let yearStr = monthMatch[2];
      if (!yearStr) {
        // Ano implícito: presente se mês passado, anterior se mês futuro
        const now = new Date(nowMs);
        const monthIdx = Number(monthMM) - 1;
        const candidateThisYear = new Date(Date.UTC(now.getUTCFullYear(), monthIdx, 15));
        yearStr = candidateThisYear.getTime() > nowMs
          ? String(now.getUTCFullYear() - 1)
          : String(now.getUTCFullYear());
      }
      return `${yearStr}-${monthMM}-15`;
    }
  }
  // Year-only fallback (less specific)
  const yearOnly = query.match(QUERY_BARE_YEAR_RX);
  if (yearOnly) {
    return `${yearOnly[1]}-06-15`;
  }
  return null;
}

/**
 * Stage B da PATCH 2 v2.
 *
 * Inferência fraca: median (não mode) das datas do top-K. Preserva o dia
 * exato (não normaliza pra mid-month) — assim consegue ancorar em
 * "2026-05-05" se o top-K for {2026-04-30, 2026-05-05, 2026-05-10} ao invés
 * de cair sempre em `2026-05-15`.
 *
 * Retorna null se < 2 datas no top-K.
 */
export function inferAnchorFromTopKAge<T extends RerankableResult>(
  results: T[],
  k: number = 5,
): string | null {
  if (!results || results.length === 0) return null;
  const slice = results.slice(0, Math.min(k, results.length));

  const dateMs: number[] = [];
  for (const r of slice) {
    const refStr = r.source_date ?? (r.created_at as string | null | undefined) ?? null;
    if (!refStr) continue;
    const ms = Date.parse(refStr);
    if (Number.isFinite(ms)) dateMs.push(ms);
  }
  if (dateMs.length < 2) return null;

  dateMs.sort((a, b) => a - b);
  const median = dateMs[Math.floor(dateMs.length / 2)]!;
  return new Date(median).toISOString().substring(0, 10);
}

/**
 * Legacy v1 — kept p/ backward-compat de tests e telemetria histórica.
 * Não usar em código novo (usa mode YYYY-MM majority threshold ≥50%).
 *
 * @deprecated Use extractAnchorFromQuery (Stage A) + inferAnchorFromTopKAge (Stage B) em v2.
 */
export function inferAnchorFromTopK<T extends RerankableResult>(
  results: T[],
  k: number = 5,
): string | null {
  if (!results || results.length === 0) return null;
  const slice = results.slice(0, Math.min(k, results.length));

  const dates: string[] = [];
  for (const r of slice) {
    const refStr = r.source_date ?? (r.created_at as string | null | undefined) ?? null;
    if (refStr && /^\d{4}-\d{2}/.test(refStr)) dates.push(refStr);
  }
  if (dates.length < 2) return null;

  const groups = new Map<string, number>();
  for (const d of dates) {
    const ym = d.substring(0, 7); // "YYYY-MM"
    groups.set(ym, (groups.get(ym) ?? 0) + 1);
  }

  const threshold = Math.ceil(dates.length * 0.5);
  let winner: [string, number] | null = null;
  for (const [ym, count] of groups) {
    if (count >= threshold) {
      if (!winner || count > winner[1]) winner = [ym, count];
    }
  }

  return winner ? `${winner[0]}-15` : null;
}

// ─── Confidence multipliers (PATCH 3 v2) ──────────────────────────────────────
//
// Tier-down do boost por nível de confiança no signal. Tiers calibrados pra
// limitar dano de inferências fracas:
//
//   iso_date                   → 1.0  exato, confiança total
//   month_year                 → 0.8  explicit mês/ano da query, alta
//   year                       → 0.5  só ano, médio (range muito amplo)
//   adverbial_keyword_inferred → 0.6  Stage A, alta (regex da query)
//   adverbial_topk_inferred    → 0.3  Stage B, baixa (median top-K)
//   adverbial / adverbial_inferred → 0.0  legacy / sem anchor / inference v1
//
// Aplicado em rerankByTemporalProximity multiplicado ao gap-aware bump.
// Confidence = 0 → não rerank (short-circuit antes do map).

export function getConfidenceMultiplier(signalSource: TemporalSignalSource): number {
  switch (signalSource) {
    case "iso_date":
      return 1.0;
    case "month_year":
      return 0.8;
    case "year":
      return 0.5;
    case "adverbial_keyword_inferred":
      return 0.6;
    case "adverbial_topk_inferred":
      return 0.3;
    case "adverbial":
    case "adverbial_inferred":
      return 0.0; // legacy v1 — sem anchor, ou inference v1 (deprecated)
    default:
      return 0.0;
  }
}

// ─── Proximity boost (PATCH 3 helper, pure & testable) ───────────────────────
//
// Boost gap-aware: scale-by-distance ao top-1 em score base. Substitui o
// boost fixo `delta * 10` (que diluía em cluster temporal denso, Q109).
//
//   dayFactor    ∈ [0, 1]  — normalização do gaussian (delta * 2, clamped)
//   scoreGap     ≥ 0       — top-1 minus candidate (floor 0.1 evita zero)
//   baseFactor   default 1
//
// Contract:
//   • proximityBoost(deltaGaussian=0.5, gap)  ≈ gap * baseFactor  (max boost)
//   • proximityBoost(deltaGaussian, 0)        ≈ 0.1 * dayFactor   (floor)
//   • monotonic: maior delta gaussian → maior bump (mesmo gap)

export function proximityBoost(
  deltaGaussian: number,
  scoreGapToTop1: number,
  baseFactor: number = 1.0,
): number {
  if (!Number.isFinite(deltaGaussian) || deltaGaussian <= 0) return 0;
  const dayFactor = Math.min(deltaGaussian * 2, 1);
  const gap = Math.max(scoreGapToTop1, 0.1);
  return baseFactor * dayFactor * gap;
}

// ─── Rerank application ───────────────────────────────────────────────────────
//
// Aplica proximity delta aditivamente (regra #5) sobre top-K. Mode `shadow`
// computa o delta mas NÃO muta score (apenas loga). Mode `active` muta.
// Mode `off` ou query não-temporal sem anchor → no-op.

export interface RerankReport {
  applied: boolean;
  isTemporal: boolean;
  signalSource: TemporalSignalSource;
  anchorIso: string | null;
  kReranked: number;
  top1DeltaDays: number | null;
  rangeStart: string | null;
  rangeEnd: string | null;
  confidence: number; // PATCH 3 v2 — multiplier efetivo (0.0 - 1.0)
}

export function rerankByTemporalProximity<T extends RerankableResult>(
  results: T[],
  query: string,
  opts: Partial<TemporalPathMode> = {},
  nowMs: number = Date.now(),
): { results: T[]; report: RerankReport } {
  const cfg = { ...getTemporalPathMode(), ...opts };
  const intent = detectTemporal(query, nowMs);

  // Mutable signal source — pode ser promovido pra:
  //   - "adverbial_keyword_inferred" via PATCH 2 v2 Stage A (regex query)
  //   - "adverbial_topk_inferred" via PATCH 2 v2 Stage B (median top-K)
  let signalSource: TemporalSignalSource = intent.signalSource;
  let effectiveAnchor: Date | null = intent.anchor;

  // PATCH 2 v2: adverbial-only sem anchor → tentar Stage A → fallback Stage B
  if (cfg.mode !== "off" && intent.isTemporal && !effectiveAnchor && intent.signalSource === "adverbial") {
    // Stage A: regex de mês/ano DIRETO na query
    const stageAIso = extractAnchorFromQuery(query, nowMs);
    if (stageAIso) {
      const parsed = new Date(stageAIso + "T00:00:00Z");
      if (!Number.isNaN(parsed.getTime())) {
        effectiveAnchor = parsed;
        signalSource = "adverbial_keyword_inferred";
      }
    }
    // Stage B: median age do top-K (fallback)
    if (!effectiveAnchor) {
      const stageBIso = inferAnchorFromTopKAge(results, 5);
      if (stageBIso) {
        const parsed = new Date(stageBIso + "T00:00:00Z");
        if (!Number.isNaN(parsed.getTime())) {
          effectiveAnchor = parsed;
          signalSource = "adverbial_topk_inferred";
        }
      }
    }
  }

  // PATCH 3 v2: confidence multiplier baseado em signalSource
  const confidence = getConfidenceMultiplier(signalSource);

  const baseReport: RerankReport = {
    applied: false,
    isTemporal: intent.isTemporal,
    signalSource,
    anchorIso: effectiveAnchor ? effectiveAnchor.toISOString().slice(0, 10) : null,
    kReranked: 0,
    top1DeltaDays: null,
    rangeStart: intent.anchorRange ? intent.anchorRange[0].toISOString().slice(0, 10) : null,
    rangeEnd: intent.anchorRange ? intent.anchorRange[1].toISOString().slice(0, 10) : null,
    confidence,
  };

  // Short-circuit: off mode OR no anchor OR confidence=0 (não aplicar)
  if (cfg.mode === "off" || !intent.isTemporal || !effectiveAnchor || confidence <= 0) {
    return { results, report: baseReport };
  }

  const k = Math.min(cfg.kRerank, results.length);
  const top = results.slice(0, k);
  const tail = results.slice(k);

  // PATCH 3: boost proporcional ao GAP entre top-1 e candidato (não fixo *10).
  // PATCH 3 v2: bump final escalado por `confidence` (0.0 - 1.0).
  const top1Score = top.length > 0 ? top[0]!.score : 0;

  let top1DeltaDays: number | null = null;

  const reranked = top.map((r, idx) => {
    const refStr = r.source_date ?? (r.created_at as string | null | undefined) ?? null;
    const delta = proximityDelta(refStr, effectiveAnchor, cfg.sigmaDays);

    if (idx === 0 && refStr) {
      const ms = Date.parse(refStr);
      if (Number.isFinite(ms) && effectiveAnchor) {
        top1DeltaDays = Math.round(Math.abs(ms - effectiveAnchor.getTime()) / 86_400_000);
      }
    }

    if (cfg.mode !== "active") return r; // shadow mode: don't mutate score

    // Active: aditivo (regra #5). PATCH 3 v2 — gap-aware + confidence-scaled.
    const dayFactor = Math.min(delta * 2, 1);
    const gapBoost = idx === 0 ? 0 : Math.max(top1Score - r.score, 0.1);
    const bump = dayFactor * gapBoost * confidence;
    const adjusted = { ...r, score: r.score + bump };
    return adjusted as T;
  });

  // Re-sort top, keep tail
  reranked.sort((a, b) => b.score - a.score);

  return {
    results: [...reranked, ...tail],
    report: {
      ...baseReport,
      applied: cfg.mode === "active",
      kReranked: k,
      top1DeltaDays,
    },
  };
}

// ─── Telemetry (stderr JSON line — pattern E13/salience shadow probes) ────────

export function logTemporalProbe(report: RerankReport, queryHash: string): void {
  if (process.env.NOX_TEMPORAL_PATH === undefined) return;
  if (process.env.NOX_TEMPORAL_PATH === "off") return;
  try {
    process.stderr.write(
      JSON.stringify({
        type: "temporal_path",
        query_hash: queryHash,
        ts: Date.now(),
        ...report,
      }) + "\n",
    );
  } catch {
    /* observability must not throw */
  }
}

// ─── Test-only exports ────────────────────────────────────────────────────────

export const _internals = {
  ADVERBIAL_PATTERNS,
  MONTH_NAMES,
  ISO_DATE,
  MONTH_YEAR,
  BARE_YEAR,
  QUERY_MONTH_YEAR_RX,
  QUERY_BARE_YEAR_RX,
};
