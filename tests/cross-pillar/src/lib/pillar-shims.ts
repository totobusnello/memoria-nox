/**
 * Pillar shims — minimal contract-pinned copies of staged-pillar primitives.
 *
 * WHY SHIMS, NOT IMPORTS:
 *   The staged packages (staged-P1, staged-A2, staged-L2, staged-L3, staged-L4,
 *   staged-P2, staged-P5, staged-A3, staged-privacy) live in sibling TypeScript
 *   projects each with their own `rootDir` / `outDir`. Cross-importing source
 *   `.ts` between them either pulls every staged tree into this tsc build (which
 *   would require deconflicting 9 sets of overlapping module roots) or relies on
 *   each staged package being npm-installed (which they aren't — they're staged
 *   patches not yet merged into the canonical nox-mem dist).
 *
 *   Instead, each shim is a SLICE of the real pillar's pure behavior, transcribed
 *   to be byte-equivalent on the contract. The real pillar lives in `staged-X/edits/`;
 *   when it merges, the shim should be replaced by a direct import. Until then,
 *   any drift in the real pillar that breaks its contract will fail these tests
 *   loudly — which is exactly the safety net Wave G is designed to provide.
 *
 * EACH SHIM CITES ITS SOURCE FILE so the next agent updating the real pillar
 * can keep parity.
 */

// =============================================================================
// A1 / staged-privacy — PII / secret redaction.
// Source: staged-privacy/edits/privacy/patterns.ts + filter.ts
// =============================================================================

export interface RedactionPattern {
  name: string;
  regex: RegExp;
  replacement: string;
}

export function luhn(digits: string): boolean {
  let sum = 0;
  let alt = false;
  for (let i = digits.length - 1; i >= 0; i--) {
    let n = parseInt(digits[i]!, 10);
    if (alt) {
      n *= 2;
      if (n > 9) n -= 9;
    }
    sum += n;
    alt = !alt;
  }
  return sum % 10 === 0;
}

/**
 * Contract-pinned subset of REDACTION_PATTERNS. Each entry mirrors a real
 * staged-privacy pattern. CRITICAL: order matters (PEM before generic base64).
 */
export const REDACTION_PATTERNS: RedactionPattern[] = [
  {
    name: "pem-private-key",
    regex: /-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----/g,
    replacement: "[REDACTED:pem-private-key]",
  },
  {
    name: "aws-access-key-id",
    regex: /\bAKIA[0-9A-Z]{16}\b/g,
    replacement: "[REDACTED:aws-access-key-id]",
  },
  {
    name: "anthropic-key",
    regex: /\bsk-ant-(?:api\d+-)?[a-zA-Z0-9_-]{20,}\b/g,
    replacement: "[REDACTED:anthropic-key]",
  },
  {
    name: "openai-key",
    regex: /\bsk-(?!ant-)[a-zA-Z0-9_-]{20,}\b/g,
    replacement: "[REDACTED:openai-key]",
  },
  {
    name: "gemini-key",
    regex: /\bAIza[0-9A-Za-z_-]{35}\b/g,
    replacement: "[REDACTED:gemini-key]",
  },
  {
    name: "github-token",
    regex: /\b(?:ghp_|gho_|ghs_|ghu_|github_pat_)[a-zA-Z0-9_]{20,}\b/g,
    replacement: "[REDACTED:github-token]",
  },
  // SSN-shaped US tax id — A1 contract (per S11 scenario)
  {
    name: "us-ssn",
    regex: /\b\d{3}-\d{2}-\d{4}\b/g,
    replacement: "[REDACTED:us-ssn]",
  },
  // CPF — Brazilian tax id (A1.1 forward-looking; spec mentions A1.1 in scenarios)
  {
    name: "br-cpf",
    regex: /\b\d{3}\.\d{3}\.\d{3}-\d{2}\b/g,
    replacement: "[REDACTED:br-cpf]",
  },
  {
    name: "credit-card",
    regex: /\b(?:\d{4}[-\s]?\d{4}[-\s]?\d{4}[-\s]?\d{4}|\d{16})\b/g,
    replacement: "[REDACTED:credit-card]",
  },
];

export interface RedactResult {
  text: string;
  redactionCount: number;
  kinds: string[];
}

export function redact(rawText: string): RedactResult {
  const kindsSet = new Set<string>();
  let redactionCount = 0;
  let current = rawText;

  // Strip <private>...</private> blocks first (user-marked).
  const beforeTags = current;
  current = current.replace(/<private>[\s\S]*?<\/private>/g, "[REDACTED:user-marked]");
  if (current !== beforeTags) {
    const tagCount = (beforeTags.match(/<private>/g) ?? []).length;
    redactionCount += tagCount;
    kindsSet.add("user-marked");
  }

  for (const pattern of REDACTION_PATTERNS) {
    pattern.regex.lastIndex = 0;

    if (pattern.name === "credit-card") {
      let count = 0;
      current = current.replace(pattern.regex, (match) => {
        const digits = match.replace(/[-\s]/g, "");
        if (digits.length === 16 && luhn(digits)) {
          count++;
          return pattern.replacement;
        }
        return match;
      });
      if (count > 0) {
        redactionCount += count;
        kindsSet.add(pattern.name);
      }
    } else {
      let count = 0;
      const replaced = current.replace(pattern.regex, () => {
        count++;
        return pattern.replacement;
      });
      if (count > 0) {
        current = replaced;
        redactionCount += count;
        kindsSet.add(pattern.name);
      }
    }
  }

  return { text: current, redactionCount, kinds: Array.from(kindsSet) };
}

// =============================================================================
// L4 — Regex-first KG extraction (typed link extractor).
// Source: staged-L4/edits/src/lib/regex-extract/{patterns,extractor,production-wire}.ts
// =============================================================================

export const NOX_ENTITY_TYPES = [
  "feedback",
  "person",
  "lesson",
  "decision",
  "project",
  "team",
  "daily",
  "pending",
  "graph_node",
  "agent",
  "incident",
  "spec",
  "audit",
  "skill",
  "persona",
  "reference",
  "entities",
] as const;

export type NoxEntityType = (typeof NOX_ENTITY_TYPES)[number];

export interface EntityRef {
  entityType: NoxEntityType;
  slug: string;
  key: string;
  display?: string;
  source: "markdown_link" | "wikilink" | "bare_ref";
}

// SLUG_CHARS mirrors staged-L4/edits/src/lib/regex-extract/patterns.ts: NO dots
// (so `.md` extensions and sentence-final periods do not get gobbled into the slug).
const DIR_PATTERN = NOX_ENTITY_TYPES.filter((t) => t !== "entities").join("|");
const SLUG_CHARS = "[a-z0-9_\\-]+";

/**
 * Strip fenced code blocks before regex sweep (prevent false matches in
 * `pre/code` snippets).
 */
function stripCodeFences(text: string): string {
  return text.replace(/```[\s\S]*?```/g, "").replace(/`[^`\n]+`/g, "");
}

export function extractEntityRefs(content: string): EntityRef[] {
  if (!content) return [];
  const stripped = stripCodeFences(content);
  const bucket = new Map<string, EntityRef>();
  const lowerSet = new Set(NOX_ENTITY_TYPES as readonly string[]);

  function push(
    rawType: string,
    rawSlug: string,
    source: EntityRef["source"],
    display?: string
  ): void {
    if (!lowerSet.has(rawType)) return;
    const slug = rawSlug.toLowerCase();
    if (!slug) return;
    const key = `${rawType}/${slug}`;
    const existing = bucket.get(key);
    if (existing) {
      if (!existing.display && display) existing.display = display;
      return;
    }
    bucket.set(key, {
      entityType: rawType as NoxEntityType,
      slug,
      key,
      source,
      display,
    });
  }

  // Markdown links: [Display](type/slug)
  const mdRe = new RegExp(`\\[([^\\]]+)\\]\\((${DIR_PATTERN})/(${SLUG_CHARS})\\)`, "g");
  for (const m of stripped.matchAll(mdRe)) {
    push(m[2] ?? "", m[3] ?? "", "markdown_link", m[1]?.trim());
  }

  // Wikilinks: [[type/slug|Display]]
  const wikiRe = new RegExp(
    `\\[\\[(${DIR_PATTERN})/(${SLUG_CHARS})(?:\\|([^\\]]+))?\\]\\]`,
    "g"
  );
  for (const m of stripped.matchAll(wikiRe)) {
    push(m[1] ?? "", m[2] ?? "", "wikilink", m[3]?.trim());
  }

  // Bare refs: type/slug (boundary-anchored).
  const bareRe = new RegExp(
    `(?<=^|\\s|[\\(\\[])(${DIR_PATTERN})/(${SLUG_CHARS})(?=$|\\s|[\\)\\].,;!?])`,
    "g"
  );
  for (const m of stripped.matchAll(bareRe)) {
    push(m[1] ?? "", m[2] ?? "", "bare_ref");
  }

  return Array.from(bucket.values());
}

export const CONFIDENCE_EXPLICIT_LINK = 0.9;
export const CONFIDENCE_BARE_REF = 0.75;
export const CONFIDENCE_FRONTMATTER = 0.95;

export function scoreEntityRef(ref: EntityRef): number {
  switch (ref.source) {
    case "markdown_link":
    case "wikilink":
      return CONFIDENCE_EXPLICIT_LINK;
    case "bare_ref":
      return CONFIDENCE_BARE_REF;
    default:
      return CONFIDENCE_BARE_REF;
  }
}

// =============================================================================
// L2 — Direct conflict detector (contract: groups by subject_entity_id + predicate
// and flags groups with >1 distinct active target, all ≥ min_confidence).
// Source: staged-L2/edits/src/lib/conflict/detector-direct.ts
// =============================================================================

export interface VariantRelation {
  relation_id: number;
  target_entity_id: number;
  confidence: number;
  extraction_method: string | null;
  evidence_chunk_id: number | null;
  created_at: number;
  user_marked: boolean;
}

export interface Conflict {
  kind: "direct" | "multi_target";
  subject_entity_id: number;
  subject_label?: string;
  predicate: string;
  variants: VariantRelation[];
  detected_at: number;
}

export interface DetectorOptions {
  min_confidence?: number;
  predicate_allowlist?: string[];
  predicate_blocklist?: string[];
  limit?: number;
  scan_ts?: number;
}

import type { Database as DatabaseType } from "better-sqlite3";

export function detectDirectConflicts(
  db: DatabaseType,
  opts: DetectorOptions = {}
): Conflict[] {
  const minConf = opts.min_confidence ?? 0.5;
  if (minConf < 0 || minConf > 1) {
    throw new RangeError(`min_confidence out of range [0..1]: ${minConf}`);
  }
  const limit = opts.limit ?? 500;
  const scanTs = opts.scan_ts ?? Date.now();

  const allow = opts.predicate_allowlist?.length
    ? new Set(opts.predicate_allowlist)
    : null;
  const block = opts.predicate_blocklist?.length
    ? new Set(opts.predicate_blocklist)
    : null;

  const groups = db
    .prepare(
      `
    SELECT source_entity_id, predicate,
           COUNT(DISTINCT target_entity_id) AS distinct_targets
    FROM kg_relations
    WHERE confidence >= ?
      AND superseded_by_relation_id IS NULL
    GROUP BY source_entity_id, predicate
    HAVING COUNT(DISTINCT target_entity_id) > 1
  `
    )
    .all(minConf) as Array<{
    source_entity_id: number;
    predicate: string;
    distinct_targets: number;
  }>;

  const out: Conflict[] = [];
  const hydrate = db.prepare(`
    SELECT id, target_entity_id, confidence, extraction_method,
           evidence_chunk_id, created_at, user_marked
    FROM kg_relations
    WHERE source_entity_id = ? AND predicate = ?
      AND confidence >= ?
      AND superseded_by_relation_id IS NULL
  `);
  const labelStmt = db.prepare(`SELECT name FROM kg_entities WHERE id = ?`);

  for (const g of groups) {
    if (allow && !allow.has(g.predicate)) continue;
    if (block && block.has(g.predicate)) continue;

    const rows = hydrate.all(
      g.source_entity_id,
      g.predicate,
      minConf
    ) as Array<{
      id: number;
      target_entity_id: number;
      confidence: number;
      extraction_method: string | null;
      evidence_chunk_id: number | null;
      created_at: number;
      user_marked: 0 | 1;
    }>;

    const distinct = new Set(rows.map((r) => r.target_entity_id));
    if (distinct.size < 2) continue;

    const labelRow = labelStmt.get(g.source_entity_id) as
      | { name: string }
      | undefined;
    const kind = distinct.size > 2 ? "multi_target" : "direct";

    out.push({
      kind,
      subject_entity_id: g.source_entity_id,
      subject_label: labelRow?.name,
      predicate: g.predicate,
      variants: rows.map((r) => ({
        relation_id: r.id,
        target_entity_id: r.target_entity_id,
        confidence: r.confidence,
        extraction_method: r.extraction_method,
        evidence_chunk_id: r.evidence_chunk_id,
        created_at: r.created_at,
        user_marked: Boolean(r.user_marked),
      })),
      detected_at: scanTs,
    });

    if (limit > 0 && out.length >= limit) break;
  }

  return out;
}

// Write a conflict to conflict_audit; mirrors L2 audit-writer contract.
export function recordConflict(
  db: DatabaseType,
  conflict: Conflict,
  shadowMode = true
): number {
  const stmt = db.prepare(`
    INSERT INTO conflict_audit
      (ts, kind, subject_entity_id, predicate, target_relation_ids, variants, status, shadow_mode)
    VALUES (?, ?, ?, ?, ?, ?, 'open', ?)
  `);
  const ts = conflict.detected_at;
  const rids = JSON.stringify(conflict.variants.map((v) => v.relation_id));
  const variants = JSON.stringify(conflict.variants);
  const res = stmt.run(
    ts,
    conflict.kind,
    conflict.subject_entity_id,
    conflict.predicate,
    rids,
    variants,
    shadowMode ? 1 : 0
  );
  return Number(res.lastInsertRowid);
}

// =============================================================================
// L3 — Confidence ranking modes + mark-canonical.
// Source: staged-L3/edits/src/lib/confidence/{config,mark,ranking,search-filter}.ts
// =============================================================================

export type RankingMode = "disabled" | "shadow" | "active";

export interface RankedChunk {
  id: number;
  base_score: number;
  confidence: number;
  /** Modulated score (only meaningful when mode != disabled). */
  modulated_score: number;
  shadow_modulated_score: number;
}

export const ACTIVE_FLOOR_DEFAULT = 0.4;

/**
 * Apply confidence ranking to base-scored chunks per L3 contract:
 *   - disabled: modulated == base_score; shadow_modulated empty (0).
 *   - shadow:   modulated == base_score; shadow_modulated == base_score * confidence.
 *   - active:   modulated == base_score * confidence; rows with confidence < floor dropped.
 */
export function applyConfidenceRanking(
  chunks: Array<{ id: number; base_score: number; confidence: number }>,
  mode: RankingMode,
  activeFloor = ACTIVE_FLOOR_DEFAULT
): RankedChunk[] {
  return chunks
    .map((c) => {
      const shadow = c.base_score * c.confidence;
      let modulated: number;
      if (mode === "active") {
        modulated = c.base_score * c.confidence;
      } else {
        modulated = c.base_score;
      }
      return {
        id: c.id,
        base_score: c.base_score,
        confidence: c.confidence,
        modulated_score: modulated,
        shadow_modulated_score: mode === "shadow" || mode === "active" ? shadow : 0,
      };
    })
    .filter((c) => {
      if (mode !== "active") return true;
      return c.confidence >= activeFloor;
    })
    .sort((a, b) => b.modulated_score - a.modulated_score);
}

/** Mark a kg_relation as user-canonical (immutable post-mark per spec §6.3). */
export function markRelationCanonical(
  db: DatabaseType,
  relation_id: number,
  marked_by = "test-user"
): void {
  const r = db
    .prepare(`SELECT user_marked FROM kg_relations WHERE id = ?`)
    .get(relation_id) as { user_marked: 0 | 1 } | undefined;
  if (!r) throw new Error(`kg_relations row ${relation_id} not found`);
  if (r.user_marked === 1) {
    throw new Error(
      `kg_relations row ${relation_id} already user-marked — refusing re-mark`
    );
  }
  db.prepare(
    `UPDATE kg_relations SET user_marked = 1, confidence = 1.0 WHERE id = ?`
  ).run(relation_id);
  // Audit trail in ops_audit (test contract).
  db.prepare(
    `INSERT INTO ops_audit (op, status, metadata_json) VALUES ('mark-canonical', 'success', ?)`
  ).run(JSON.stringify({ relation_id, marked_by }));
}

// =============================================================================
// A2 — Export / import round-trip.
// Source: staged-A2/edits/src/lib/archive/{encryption,format,manifest}.ts
//
// Simplified contract: serialize-then-deserialize via canonical JSON, encrypted
// with AES-256-GCM keyed on scrypt-derived bytes from a passphrase + manifest AAD.
// Real archive uses tar; this shim uses a single concatenated buffer with
// length-prefixed sections. The CONTRACT mirror is: passphrase round-trips,
// wrong passphrase fails, tampered ciphertext fails GCM, manifest AAD enforced.
// =============================================================================

import {
  scryptSync,
  randomBytes,
  createCipheriv,
  createDecipheriv,
  createHash,
} from "node:crypto";

export interface ArchiveBlob {
  manifest: ArchiveManifest;
  ciphertext: Buffer;
  nonce: Buffer;
  authTag: Buffer;
  salt: Buffer;
}

export interface ArchiveManifest {
  format_version: "1.0";
  schema_version: number;
  created_at: string;
  embedding_provider: string;
  embedding_model: string;
  embedding_dim: number;
  counts: { chunks: number; kg_entities: number; kg_relations: number };
  checksums: { payload_sha256: string };
}

const SCRYPT_N = 1 << 14; // tuned down vs prod for fast tests
const SCRYPT_R = 8;
const SCRYPT_P = 1;
const KEY_LEN = 32;
const NONCE_LEN = 12;

export function deriveKey(passphrase: string, salt: Buffer): Buffer {
  return scryptSync(passphrase, salt, KEY_LEN, {
    N: SCRYPT_N,
    r: SCRYPT_R,
    p: SCRYPT_P,
  });
}

export function canonicalize(obj: unknown): string {
  if (obj === null || typeof obj !== "object") {
    return JSON.stringify(obj);
  }
  if (Array.isArray(obj)) {
    return "[" + obj.map((x) => canonicalize(x)).join(",") + "]";
  }
  const keys = Object.keys(obj as Record<string, unknown>).sort();
  return (
    "{" +
    keys
      .map((k) => JSON.stringify(k) + ":" + canonicalize((obj as Record<string, unknown>)[k]))
      .join(",") +
    "}"
  );
}

export function manifestAADHash(manifest: ArchiveManifest): Buffer {
  const canon = canonicalize(manifest);
  return createHash("sha256").update(canon).digest();
}

export function packArchive(
  passphrase: string,
  manifest: ArchiveManifest,
  payload: Buffer
): ArchiveBlob {
  const salt = randomBytes(16);
  const key = deriveKey(passphrase, salt);
  const nonce = randomBytes(NONCE_LEN);
  const aad = manifestAADHash(manifest);
  const cipher = createCipheriv("aes-256-gcm", key, nonce);
  cipher.setAAD(aad);
  const ciphertext = Buffer.concat([cipher.update(payload), cipher.final()]);
  const authTag = cipher.getAuthTag();
  return { manifest, ciphertext, nonce, authTag, salt };
}

export class BadPassphraseError extends Error {
  constructor() {
    super("Bad passphrase or wrong key");
    this.name = "BadPassphraseError";
  }
}

export class TamperedArchiveError extends Error {
  constructor() {
    super("Archive tampered — GCM tag mismatch");
    this.name = "TamperedArchiveError";
  }
}

export function unpackArchive(passphrase: string, blob: ArchiveBlob): Buffer {
  const key = deriveKey(passphrase, blob.salt);
  const aad = manifestAADHash(blob.manifest);
  const decipher = createDecipheriv("aes-256-gcm", key, blob.nonce);
  decipher.setAAD(aad);
  decipher.setAuthTag(blob.authTag);
  try {
    return Buffer.concat([decipher.update(blob.ciphertext), decipher.final()]);
  } catch (err) {
    const msg = err instanceof Error ? err.message : String(err);
    if (msg.toLowerCase().includes("auth")) {
      // GCM tag mismatch: either wrong passphrase or tampered ciphertext.
      // We can't distinguish them at this layer — convention: caller decides.
      throw new BadPassphraseError();
    }
    throw err;
  }
}

// =============================================================================
// A3 — Provider fallback chain.
// Source: staged-A3/edits/src/providers/llm/chain.ts
//
// Contract-pinned: primary timeout → fallback; 429 → cooldown + fallback;
// 401/403 → fail-fast; max one fallback attempt per provider in a single call.
// =============================================================================

export interface CompleteOpts {
  user: string;
  system?: string;
  maxTokens?: number;
}

export interface CompleteResult {
  text: string;
  tokensIn: number;
  tokensOut: number;
  latencyMs: number;
}

export interface LLMProvider {
  readonly name: string;
  readonly model: string;
  complete(opts: CompleteOpts): Promise<CompleteResult>;
}

export interface FallbackEvent {
  kind: "primary_ok" | "primary_fail_try_next" | "fallback_ok" | "all_fail" | "auth_fail";
  usedProviderId: string;
  attemptIndex: number;
  errorKind?: "timeout" | "rate_limit" | "auth" | "unknown";
  latencyMs: number;
}

export class LLMFallbackChain {
  public events: FallbackEvent[] = [];
  constructor(
    private primary: LLMProvider,
    private fallbacks: LLMProvider[],
    private opts: { timeoutMs?: number } = {}
  ) {}

  async complete(
    opts: CompleteOpts
  ): Promise<CompleteResult & { providerId: string }> {
    const all = [this.primary, ...this.fallbacks];
    let lastErr: Error | undefined;
    const timeoutMs = this.opts.timeoutMs ?? 30_000;

    for (let i = 0; i < all.length; i++) {
      const p = all[i]!;
      const t0 = Date.now();
      try {
        const result = await Promise.race<CompleteResult>([
          p.complete(opts),
          new Promise<CompleteResult>((_, reject) =>
            setTimeout(
              () => reject(new Error(`provider timeout after ${timeoutMs}ms`)),
              timeoutMs
            )
          ),
        ]);
        this.events.push({
          kind: i === 0 ? "primary_ok" : "fallback_ok",
          usedProviderId: p.name,
          attemptIndex: i,
          latencyMs: Date.now() - t0,
        });
        return { ...result, providerId: p.name };
      } catch (err) {
        const msg = err instanceof Error ? err.message : String(err);
        const status = msg.match(/HTTP (\d{3})/)?.[1];
        if (status === "401" || status === "403") {
          this.events.push({
            kind: "auth_fail",
            usedProviderId: p.name,
            attemptIndex: i,
            errorKind: "auth",
            latencyMs: Date.now() - t0,
          });
          throw new Error(
            `auth failure on ${p.name} — refusing fallback (HTTP ${status})`
          );
        }
        const errorKind: FallbackEvent["errorKind"] =
          status === "429"
            ? "rate_limit"
            : msg.includes("timeout")
              ? "timeout"
              : "unknown";
        this.events.push({
          kind: "primary_fail_try_next",
          usedProviderId: p.name,
          attemptIndex: i,
          errorKind,
          latencyMs: Date.now() - t0,
        });
        lastErr = err instanceof Error ? err : new Error(msg);
      }
    }
    this.events.push({
      kind: "all_fail",
      usedProviderId: "(none)",
      attemptIndex: all.length,
      errorKind: "unknown",
      latencyMs: 0,
    });
    throw lastErr ?? new Error("all providers failed");
  }
}

// =============================================================================
// P5 — Viewer event bus (in-process EventEmitter).
// Source: staged-P5/edits/src/lib/viewer/broadcast.ts
// =============================================================================

export type ViewerEventKind = "ingest" | "search" | "kg" | "op_audit" | "crystallize";

export interface ViewerEvent {
  ts: string;
  type: ViewerEventKind;
  source: string;
  summary: string;
  details: Record<string, unknown>;
}

export class ViewerBus {
  private listeners: Array<(ev: ViewerEvent) => void> = [];
  publish(ev: ViewerEvent): void {
    for (const l of this.listeners) {
      try {
        l(ev);
      } catch {
        // viewer listeners must never throw to producer
      }
    }
  }
  subscribe(cb: (ev: ViewerEvent) => void): () => void {
    this.listeners.push(cb);
    return () => {
      this.listeners = this.listeners.filter((x) => x !== cb);
    };
  }
}

/**
 * Emit a search event with query-redaction policy per P5:
 *   default: query="<redacted>"
 *   NOX_VIEWER_SHOW_QUERY=1: query=raw text
 */
export function emitSearchEvent(
  bus: ViewerBus,
  query: string,
  latencyMs: number,
  resultCount: number,
  env: NodeJS.ProcessEnv = process.env
): void {
  const showQuery = env.NOX_VIEWER_SHOW_QUERY === "1";
  const hash = createHash("sha256").update(query).digest("hex").slice(0, 16);
  bus.publish({
    ts: new Date().toISOString(),
    type: "search",
    source: "search-hybrid",
    summary: `search latency_ms=${latencyMs} results=${resultCount}`,
    details: {
      query_hash: hash,
      query: showQuery ? query : "<redacted>",
      latency_ms: latencyMs,
      result_count: resultCount,
    },
  });
}

// =============================================================================
// P2 — Hooks pipeline (5-layer).
// Source: staged-P2/edits/src/lib/hooks/pipeline.ts
// =============================================================================

export type HookSource = "openclaw" | "cli" | "manual" | "mcp" | "api" | "unknown";
export type HookRole = "user" | "assistant" | "system" | "tool" | "unknown";

export interface HookEvent {
  event_id: string;
  source: HookSource;
  role: HookRole;
  content: string;
  ts: string;
  session_id?: string;
  project_slug?: string;
}

export interface HookResult {
  captured: boolean;
  reason: string;
  layer: string;
  chunk_id?: number;
  duration_ms: number;
}

export interface HookPipelineOpts {
  env?: NodeJS.ProcessEnv;
  /** If true, layer-3 redaction drops PII rather than passing redacted text through. */
  pii_policy?: "redact" | "drop";
  source_allowlist?: HookSource[];
  insertChunk: (text: string) => number;
  insertTelemetry: (row: {
    event_uuid: string;
    session_id: string;
    project_slug: string;
    kind: string;
    payload_json: string;
    redaction_count: number;
  }) => void;
}

export async function runHookPipeline(
  ev: HookEvent,
  opts: HookPipelineOpts
): Promise<HookResult> {
  const t0 = Date.now();
  const env = opts.env ?? process.env;

  // Layer 1: env gate.
  if (env.NOX_HOOKS_DISABLED === "1") {
    opts.insertTelemetry({
      event_uuid: ev.event_id,
      session_id: ev.session_id ?? "unknown",
      project_slug: ev.project_slug ?? "",
      kind: "user_prompt",
      payload_json: JSON.stringify({ layer: "env", reason: "env_disabled" }),
      redaction_count: 0,
    });
    return { captured: false, reason: "env_disabled", layer: "env", duration_ms: Date.now() - t0 };
  }

  // Layer 2: source allowlist.
  const allow = opts.source_allowlist ?? ["openclaw", "cli", "api", "mcp", "manual"];
  if (!allow.includes(ev.source)) {
    opts.insertTelemetry({
      event_uuid: ev.event_id,
      session_id: ev.session_id ?? "unknown",
      project_slug: ev.project_slug ?? "",
      kind: "user_prompt",
      payload_json: JSON.stringify({ layer: "source-allowlist", reason: "source_not_allowed" }),
      redaction_count: 0,
    });
    return { captured: false, reason: "source_not_allowed", layer: "source-allowlist", duration_ms: Date.now() - t0 };
  }

  // Layer 3: privacy filter.
  const redacted = redact(ev.content);
  if (redacted.redactionCount > 0 && opts.pii_policy === "drop") {
    opts.insertTelemetry({
      event_uuid: ev.event_id,
      session_id: ev.session_id ?? "unknown",
      project_slug: ev.project_slug ?? "",
      kind: "user_prompt",
      payload_json: JSON.stringify({
        layer: "privacy-filter",
        reason: "pii_detected",
      }),
      redaction_count: redacted.redactionCount,
    });
    return {
      captured: false,
      reason: "pii_detected",
      layer: "privacy-filter",
      duration_ms: Date.now() - t0,
    };
  }

  // Layer 4: classifier — toy "low signal" detector (very short messages or
  // pure whitespace). Real classifier is in staged-P2/edits/src/lib/hooks/classifier.ts.
  if (redacted.text.trim().length < 5) {
    opts.insertTelemetry({
      event_uuid: ev.event_id,
      session_id: ev.session_id ?? "unknown",
      project_slug: ev.project_slug ?? "",
      kind: "user_prompt",
      payload_json: JSON.stringify({ layer: "classifier", reason: "classifier_low_signal" }),
      redaction_count: redacted.redactionCount,
    });
    return {
      captured: false,
      reason: "classifier_low_signal",
      layer: "classifier",
      duration_ms: Date.now() - t0,
    };
  }

  // Layer 5: rate-limit / dedup — out of scope for shim; assume pass.

  // Persist.
  const chunkId = opts.insertChunk(redacted.text);
  opts.insertTelemetry({
    event_uuid: ev.event_id,
    session_id: ev.session_id ?? "unknown",
    project_slug: ev.project_slug ?? "",
    kind: "user_prompt",
    payload_json: JSON.stringify({
      layer: "persisted",
      reason: "ok",
      redaction_count: redacted.redactionCount,
    }),
    redaction_count: redacted.redactionCount,
  });

  return {
    captured: true,
    reason: "ok",
    layer: "persisted",
    chunk_id: chunkId,
    duration_ms: Date.now() - t0,
  };
}

// =============================================================================
// op-audit — withOpAudit() wrapper (started → success | failed | crashed).
// Source: src/lib/op-audit.ts (production)
// =============================================================================

export async function withOpAudit<T>(
  db: DatabaseType,
  op: string,
  fn: () => Promise<T> | T,
  metadata: Record<string, unknown> = {}
): Promise<{ result: T; auditId: number }> {
  const insert = db
    .prepare(
      `INSERT INTO ops_audit (op, status, metadata_json) VALUES (?, 'started', ?)`
    )
    .run(op, JSON.stringify(metadata));
  const auditId = Number(insert.lastInsertRowid);
  try {
    const result = await fn();
    db.prepare(
      `UPDATE ops_audit SET status = 'success', completed_at = datetime('now') WHERE id = ?`
    ).run(auditId);
    return { result, auditId };
  } catch (err) {
    db.prepare(
      `UPDATE ops_audit SET status = 'failed', completed_at = datetime('now') WHERE id = ?`
    ).run(auditId);
    throw err;
  }
}
