/**
 * T2 — Manifest schema, canonical writer, parser.
 *
 * Canonical JSON serialization (sorted keys, no extra whitespace, UTF-8) is
 * mandatory because the manifest plaintext is the AAD source for AES-256-GCM.
 * Any whitespace or key-order drift between writer and parser would break
 * `sha256(manifestBytes)` equality on the receiving end → all encrypted files
 * fail decrypt. T2 owns this invariant.
 */

import { createHash } from "node:crypto";
import {
  ENCRYPTION_FORMAT_VERSION,
  EncryptionMetadata,
  MANIFEST_FORMAT_VERSION,
  ManifestCounts,
  ManifestError,
  ManifestFilters,
  ManifestV1,
} from "./types.js";

const SUPPORTED_FORMAT_VERSIONS = new Set([MANIFEST_FORMAT_VERSION]);

export interface ManifestSeed {
  schema_version: number;
  source_hostname: string;
  source_nox_mem_version: string;
  embedding_provider: string;
  embedding_model: string;
  embedding_dim: number;
  sqlite_vec_version?: string | null;
  includes: ManifestV1["includes"];
  filters?: Partial<ManifestFilters>;
  counts: ManifestCounts;
  checksums: Record<string, string>;
  encryption?: EncryptionMetadata;
  integrity_warnings?: string[];
  created_at?: string;
}

/** Build an in-memory ManifestV1 from a seed. Encryption defaults to disabled. */
export function buildManifest(seed: ManifestSeed): ManifestV1 {
  return {
    format_version: MANIFEST_FORMAT_VERSION,
    schema_version: seed.schema_version,
    created_at: seed.created_at ?? new Date().toISOString(),
    source_hostname: seed.source_hostname,
    source_nox_mem_version: seed.source_nox_mem_version,
    embedding_provider: seed.embedding_provider,
    embedding_model: seed.embedding_model,
    embedding_dim: seed.embedding_dim,
    sqlite_vec_version: seed.sqlite_vec_version ?? null,
    includes: seed.includes,
    filters: {
      project: seed.filters?.project ?? null,
      since: seed.filters?.since ?? null,
      until: seed.filters?.until ?? null,
    },
    counts: seed.counts,
    checksums: seed.checksums,
    encryption: seed.encryption ?? defaultEncryptionDisabled(),
    integrity_warnings: seed.integrity_warnings ?? [],
  };
}

export function defaultEncryptionDisabled(): EncryptionMetadata {
  return {
    enabled: false,
    algorithm: null,
    kdf: null,
    kdf_params: null,
    kdf_salt_b64: null,
    files: {},
    aad_source: null,
    format_version: ENCRYPTION_FORMAT_VERSION,
  };
}

/**
 * Canonical JSON serializer. Sorts object keys recursively, no whitespace.
 * Stable across Node versions (does NOT depend on V8 object insertion order).
 */
export function canonicalize(value: unknown): string {
  return canon(value);
}

function canon(value: unknown): string {
  if (value === null) return "null";
  if (typeof value === "boolean") return value ? "true" : "false";
  if (typeof value === "number") {
    if (!Number.isFinite(value)) {
      throw new ManifestError(`Cannot canonicalize non-finite number: ${value}`);
    }
    return Number.isInteger(value) ? value.toString() : JSON.stringify(value);
  }
  if (typeof value === "string") return JSON.stringify(value);
  if (Array.isArray(value)) {
    return "[" + value.map(canon).join(",") + "]";
  }
  if (typeof value === "object") {
    const obj = value as Record<string, unknown>;
    const keys = Object.keys(obj).sort();
    return (
      "{" +
      keys
        .map((k) => JSON.stringify(k) + ":" + canon(obj[k]))
        .join(",") +
      "}"
    );
  }
  throw new ManifestError(`Cannot canonicalize ${typeof value}`);
}

/** Serialize manifest to a UTF-8 Buffer using canonical JSON. */
export function writeManifest(m: ManifestV1): Buffer {
  validateManifest(m);
  return Buffer.from(canonicalize(m), "utf8");
}

/** Parse manifest bytes. Throws ManifestError on schema mismatch. */
export function parseManifest(buf: Buffer): ManifestV1 {
  let raw: unknown;
  try {
    raw = JSON.parse(buf.toString("utf8"));
  } catch (err) {
    throw new ManifestError(
      `Manifest JSON parse failed: ${(err as Error).message}`,
    );
  }
  if (!raw || typeof raw !== "object" || Array.isArray(raw)) {
    throw new ManifestError("Manifest must be a JSON object");
  }
  const r = raw as Record<string, unknown>;
  if (
    typeof r.format_version !== "string" ||
    !SUPPORTED_FORMAT_VERSIONS.has(r.format_version as typeof MANIFEST_FORMAT_VERSION)
  ) {
    throw new ManifestError(
      `Unsupported manifest format_version: ${String(r.format_version)}`,
    );
  }
  // Normalize: re-build manifest through buildManifest to ensure invariants.
  const seed: ManifestSeed = {
    schema_version: asNumber(r.schema_version, "schema_version"),
    source_hostname: asString(r.source_hostname, "source_hostname"),
    source_nox_mem_version: asString(
      r.source_nox_mem_version,
      "source_nox_mem_version",
    ),
    embedding_provider: asString(r.embedding_provider, "embedding_provider"),
    embedding_model: asString(r.embedding_model, "embedding_model"),
    embedding_dim: asNumber(r.embedding_dim, "embedding_dim"),
    sqlite_vec_version: (r.sqlite_vec_version as string | null) ?? null,
    includes: asArray(r.includes, "includes") as ManifestV1["includes"],
    filters: (r.filters as ManifestFilters | undefined) ?? undefined,
    counts: r.counts as ManifestCounts,
    checksums: r.checksums as Record<string, string>,
    encryption: r.encryption as EncryptionMetadata | undefined,
    integrity_warnings: (r.integrity_warnings as string[] | undefined) ?? [],
    created_at: r.created_at as string,
  };
  return buildManifest(seed);
}

/**
 * AAD source: sha256 of the canonical manifest bytes computed BEFORE any
 * encryption metadata is filled in. The full encryption block (enabled flag,
 * algorithm, KDF params, salt, per-file nonces/tags, etc.) is stripped to the
 * "disabled" sentinel so the AAD is identical pre/post-encrypt write.
 *
 * Pipeline:
 *   1. Build manifest with `encryption: defaultEncryptionDisabled()`
 *   2. AAD = sha256(manifestAADSource(this))
 *   3. Encrypt files using that AAD
 *   4. Re-assemble manifest with full `encryption: ...` filled in
 *   5. AAD source still produces the SAME bytes → tag verifies on decrypt
 */
export function manifestAADSource(m: ManifestV1): Buffer {
  const stripped: ManifestV1 = {
    ...m,
    encryption: defaultEncryptionDisabled(),
  };
  return writeManifest(stripped);
}

export function manifestAADHash(m: ManifestV1): Buffer {
  return createHash("sha256").update(manifestAADSource(m)).digest();
}

function asString(v: unknown, field: string): string {
  if (typeof v !== "string") {
    throw new ManifestError(`Manifest field ${field} must be a string`);
  }
  return v;
}

function asNumber(v: unknown, field: string): number {
  if (typeof v !== "number" || !Number.isFinite(v)) {
    throw new ManifestError(`Manifest field ${field} must be a finite number`);
  }
  return v;
}

function asArray(v: unknown, field: string): unknown[] {
  if (!Array.isArray(v)) {
    throw new ManifestError(`Manifest field ${field} must be an array`);
  }
  return v;
}

function validateManifest(m: ManifestV1): void {
  if (!SUPPORTED_FORMAT_VERSIONS.has(m.format_version)) {
    throw new ManifestError(
      `Unsupported manifest format_version: ${m.format_version}`,
    );
  }
  if (!Number.isInteger(m.schema_version) || m.schema_version < 1) {
    throw new ManifestError(`Invalid schema_version: ${m.schema_version}`);
  }
  if (!m.created_at || !/^\d{4}-\d{2}-\d{2}T/.test(m.created_at)) {
    throw new ManifestError(`Invalid created_at: ${m.created_at}`);
  }
  if (m.embedding_dim < 1) {
    throw new ManifestError(`Invalid embedding_dim: ${m.embedding_dim}`);
  }
  for (const [name, hash] of Object.entries(m.checksums)) {
    if (!/^[0-9a-f]{64}$/.test(hash)) {
      throw new ManifestError(`Invalid sha256 hex for ${name}: ${hash}`);
    }
  }
}
