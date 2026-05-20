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
 */

// ─── Types ────────────────────────────────────────────────────────────────────

export type TemporalSignalSource = "iso_date" | "month_year" | "year" | "adverbial" | null;

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
}

export function rerankByTemporalProximity<T extends RerankableResult>(
  results: T[],
  query: string,
  opts: Partial<TemporalPathMode> = {},
  nowMs: number = Date.now(),
): { results: T[]; report: RerankReport } {
  const cfg = { ...getTemporalPathMode(), ...opts };
  const intent = detectTemporal(query, nowMs);

  const baseReport: RerankReport = {
    applied: false,
    isTemporal: intent.isTemporal,
    signalSource: intent.signalSource,
    anchorIso: intent.anchor ? intent.anchor.toISOString().slice(0, 10) : null,
    kReranked: 0,
    top1DeltaDays: null,
    rangeStart: intent.anchorRange ? intent.anchorRange[0].toISOString().slice(0, 10) : null,
    rangeEnd: intent.anchorRange ? intent.anchorRange[1].toISOString().slice(0, 10) : null,
  };

  // Short-circuit: off mode OR no anchor (adverbial-only delegates to E13)
  if (cfg.mode === "off" || !intent.isTemporal || !intent.anchor) {
    return { results, report: baseReport };
  }

  const k = Math.min(cfg.kRerank, results.length);
  const top = results.slice(0, k);
  const tail = results.slice(k);

  let top1DeltaDays: number | null = null;

  const reranked = top.map((r, idx) => {
    const refStr = r.source_date ?? (r.created_at as string | null | undefined) ?? null;
    const delta = proximityDelta(refStr, intent.anchor, cfg.sigmaDays);

    if (idx === 0 && refStr) {
      const ms = Date.parse(refStr);
      if (Number.isFinite(ms) && intent.anchor) {
        top1DeltaDays = Math.round(Math.abs(ms - intent.anchor.getTime()) / 86_400_000);
      }
    }

    if (cfg.mode !== "active") return r; // shadow mode: don't mutate score

    // Active: aditivo (mesmo padrão boost-stack staged-1.7a/edits/search.ts).
    // baseScore * (1 + boostSum) → aqui já temos score final, então:
    //   new = old * (1 + delta) — manteria semântica, mas spike opta por
    //   somar absoluto (mais previsível em RRF-fused scores ~1-100 range).
    const adjusted = { ...r, score: r.score + delta * 10 };
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
};
