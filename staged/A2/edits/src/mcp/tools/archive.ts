/**
 * T14 — MCP tools `archive_export` + `archive_import`.
 *
 * Adds 2 tools to the existing 16 → 18 MCP tools served by nox-mem.
 * Schema follows the MCP convention: name, description, inputSchema (JSON
 * Schema draft-07-ish), result type. The MCP server in the parent repo wires
 * these into its registry.
 *
 * Security:
 *   - `passphrase` parameter accepted ONLY when the MCP transport is
 *     authenticated (stdio over OS pipe, OR HTTPS). Parent server enforces
 *     transport-level auth; this module does not re-validate.
 *   - `passphrase_env` is the preferred parameter — the MCP server expands it
 *     from its own process env, never the client's argv.
 */

import {
  runExport,
  runImport,
  ExportRequest,
  ImportRequest,
} from "../../lib/archive/orchestrator.js";
import {
  ChunkRow,
  KgEntityRow,
  KgRelationRow,
  OpsAuditRow,
} from "../../lib/archive/types.js";

// -- JSON Schemas -------------------------------------------------------------

export const archiveExportToolSchema = {
  name: "archive_export",
  description:
    "Export nox-mem memory state to a portable .tgz archive. Encrypt-by-default (D41 #2). " +
    "Returns archive bytes base64 + manifest summary.",
  inputSchema: {
    type: "object",
    properties: {
      unencrypted: { type: "boolean", default: false },
      passphrase: {
        type: "string",
        description:
          "Passphrase for AES-256-GCM. Required unless unencrypted=true. " +
          "PREFER passphrase_env for automation.",
      },
      passphrase_env: {
        type: "string",
        description:
          "Name of an env var on the MCP server process containing the passphrase. " +
          "Server reads it; the value never crosses the wire.",
      },
      project: { type: "string" },
      since: { type: "string", format: "date-time" },
      until: { type: "string", format: "date-time" },
      exclude_embeddings: { type: "boolean", default: false },
    },
  },
} as const;

export const archiveImportToolSchema = {
  name: "archive_import",
  description:
    "Import a nox-mem archive. Auto-detects encryption via manifest. " +
    "Validates schema version + checksums BEFORE writing.",
  inputSchema: {
    type: "object",
    required: ["archive_b64"],
    properties: {
      archive_b64: { type: "string", description: "Base64-encoded archive." },
      passphrase: { type: "string" },
      passphrase_env: { type: "string" },
      mode: { enum: ["merge", "replace"], default: "merge" },
      dry_run: { type: "boolean", default: false },
      verify_only: { type: "boolean", default: false },
    },
  },
} as const;

// -- Inputs -------------------------------------------------------------------

export interface ArchiveExportInput {
  unencrypted?: boolean;
  passphrase?: string;
  passphrase_env?: string;
  project?: string;
  since?: string;
  until?: string;
  exclude_embeddings?: boolean;
}

export interface ArchiveImportInput {
  archive_b64: string;
  passphrase?: string;
  passphrase_env?: string;
  mode?: "merge" | "replace";
  dry_run?: boolean;
  verify_only?: boolean;
}

// -- Results ------------------------------------------------------------------

export interface ArchiveExportResult {
  success: true;
  archive_b64: string;
  bytes: number;
  encrypted: boolean;
  manifest: {
    schema_version: number;
    counts: import("../../lib/archive/types.js").ManifestCounts;
    created_at: string;
  };
  duration_ms: number;
}

export interface ArchiveExportError {
  success: false;
  error: string;
  code?: string;
}

export interface ArchiveImportResult {
  success: true;
  encrypted: boolean;
  applied: boolean;
  schema_version_archive: number;
  schema_version_target: number;
  stats: import("../../lib/archive/orchestrator.js").ImportResult["stats"];
  duration_ms: number;
}

export interface ArchiveImportError {
  success: false;
  error: string;
  code?: string;
}

// -- Deps + handlers ----------------------------------------------------------

export interface McpExportDeps {
  dbReader: () => Promise<Omit<ExportRequest, "passphrase" | "unencrypted" | "signal" | "onProgress">>;
  env?: NodeJS.ProcessEnv;
  signal?: AbortSignal;
}

export async function archiveExportTool(
  input: ArchiveExportInput,
  deps: McpExportDeps,
): Promise<ArchiveExportResult | ArchiveExportError> {
  const env = deps.env ?? process.env;
  let passphrase = input.passphrase;
  if (input.passphrase_env) {
    const v = env[input.passphrase_env];
    if (typeof v !== "string" || v.length === 0) {
      return {
        success: false,
        error: `passphrase_env ${input.passphrase_env} not set on server`,
        code: "MISSING_ENV",
      };
    }
    passphrase = v;
  }
  if (
    !input.unencrypted &&
    (typeof passphrase !== "string" || passphrase.length === 0)
  ) {
    return {
      success: false,
      error:
        "passphrase required (D41 #2 encrypt-by-default) — pass passphrase or passphrase_env",
      code: "PASSPHRASE_REQUIRED",
    };
  }
  const corpus = await deps.dbReader();
  if (input.exclude_embeddings) corpus.embeddings = undefined;
  try {
    const out = await runExport({
      ...corpus,
      filters: {
        project: input.project ?? null,
        since: input.since ?? null,
        until: input.until ?? null,
      },
      unencrypted: input.unencrypted === true,
      passphrase,
      signal: deps.signal,
    });
    return {
      success: true,
      archive_b64: out.archive.toString("base64"),
      bytes: out.size_bytes,
      encrypted: out.manifest.encryption.enabled,
      manifest: {
        schema_version: out.manifest.schema_version,
        counts: out.manifest.counts,
        created_at: out.manifest.created_at,
      },
      duration_ms: out.duration_ms,
    };
  } catch (err) {
    return {
      success: false,
      error: (err as Error).message,
    };
  }
}

export interface McpImportDeps {
  loadExisting: () => Promise<{
    chunks: ChunkRow[];
    kg_entities: KgEntityRow[];
    kg_relations: KgRelationRow[];
    ops_audit: OpsAuditRow[];
  }>;
  currentSchemaVersion: () => Promise<number>;
  persist?: (
    resolved: import("../../lib/archive/orchestrator.js").ImportResult["resolved"],
  ) => Promise<void>;
  env?: NodeJS.ProcessEnv;
  signal?: AbortSignal;
}

export async function archiveImportTool(
  input: ArchiveImportInput,
  deps: McpImportDeps,
): Promise<ArchiveImportResult | ArchiveImportError> {
  if (!input.archive_b64) {
    return { success: false, error: "archive_b64 required" };
  }
  const env = deps.env ?? process.env;
  let passphrase = input.passphrase;
  if (input.passphrase_env) {
    const v = env[input.passphrase_env];
    if (typeof v !== "string" || v.length === 0) {
      return {
        success: false,
        error: `passphrase_env ${input.passphrase_env} not set on server`,
      };
    }
    passphrase = v;
  }
  let archive: Buffer;
  try {
    archive = Buffer.from(input.archive_b64, "base64");
  } catch (err) {
    return { success: false, error: `bad base64: ${(err as Error).message}` };
  }
  const existing = await deps.loadExisting();
  const currentSchemaVersion = await deps.currentSchemaVersion();
  const req: ImportRequest = {
    archive,
    passphrase,
    mode: input.mode ?? "merge",
    dry_run: input.dry_run === true,
    verify_only: input.verify_only === true,
    current_schema_version: currentSchemaVersion,
    existing,
    signal: deps.signal,
  };
  try {
    const out = await runImport(req);
    if (!input.dry_run && !input.verify_only && deps.persist) {
      await deps.persist(out.resolved);
    }
    return {
      success: true,
      encrypted: out.manifest.encryption.enabled,
      applied: out.applied,
      schema_version_archive: out.manifest.schema_version,
      schema_version_target: currentSchemaVersion,
      stats: out.stats,
      duration_ms: out.duration_ms,
    };
  } catch (err) {
    return { success: false, error: (err as Error).message };
  }
}
