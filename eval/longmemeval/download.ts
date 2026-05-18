/**
 * download.ts — fetch a LongMemEval split for memoria-nox evaluation.
 *
 * Source: https://huggingface.co/datasets/xiaowu0162/longmemeval-cleaned  (MIT)
 * Citation: Di Wu et al. LongMemEval: Benchmarking Chat Assistants on Long-Term
 *           Interactive Memory. ICLR 2025. arXiv:2410.10813.
 *
 * Deprecation: the original `xiaowu0162/longmemeval` was deprecated 2025-09-19.
 * Always use `longmemeval-cleaned`.
 *
 * Writes:
 *   eval/longmemeval/data/<split>.json    (gitignored — keep cache local)
 *   eval/longmemeval/dataset.lock.json    (gitignored — append per-split SHA + sha256)
 *
 * Usage:
 *   npx tsx eval/longmemeval/download.ts --split oracle
 *   npx tsx eval/longmemeval/download.ts --split s_cleaned
 *   npx tsx eval/longmemeval/download.ts --split m_cleaned --revision <commit>
 *   npx tsx eval/longmemeval/download.ts --split oracle --check
 *   npx tsx eval/longmemeval/download.ts --split oracle --force
 *
 * No npm deps required. Uses node:fetch (Node ≥18) + node:crypto.
 *
 * HuggingFace path conventions:
 *   - Dataset repo: xiaowu0162/longmemeval-cleaned
 *   - Resolved-file URL: https://huggingface.co/datasets/<repo>/resolve/<rev>/<path>
 *   - API commit: https://huggingface.co/api/datasets/<repo>/commits/main
 *   - File names in this dataset (verified 2026-05-17):
 *       longmemeval_oracle.json
 *       longmemeval_s_cleaned.json
 *       longmemeval_m_cleaned.json
 */

import { createHash } from "node:crypto";
import { mkdir, readFile, writeFile, stat } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const HERE = dirname(__filename);
const DATA_DIR = resolve(HERE, "data");
const LOCK_FILE = resolve(HERE, "dataset.lock.json");

const REPO = "xiaowu0162/longmemeval-cleaned";
const HF_RESOLVE = "https://huggingface.co/datasets";
const HF_API = "https://huggingface.co/api/datasets";
// Pin resolved on 2026-05-17 (latest commit at the time of scaffold).
const DEFAULT_REV = "98d7416c24c778c2fee6e6f3006e7a073259d48f";

const VALID_SPLITS = new Set(["oracle", "s_cleaned", "m_cleaned"]);

function fileNameFor(split: string): string {
  return `longmemeval_${split}.json`;
}

interface SplitLock {
  split: string;
  file_name: string;
  resolved_revision: string;
  resolved_at: string;
  sha256: string;
  size_bytes: number;
}

interface DatasetLock {
  source_repo: string;
  source_url: string;
  license: string;
  citation: string;
  splits: Record<string, SplitLock>;
}

async function resolveRevision(ref: string): Promise<string> {
  if (/^[0-9a-f]{40}$/i.test(ref)) return ref;
  // HF API lists commits in reverse-chrono order; first entry is HEAD of the branch.
  const r = await fetch(`${HF_API}/${REPO}/commits/${encodeURIComponent(ref)}`, {
    headers: { "User-Agent": "memoria-nox-longmemeval-eval/0.1" },
  });
  if (!r.ok) {
    throw new Error(`HF API ${r.status} resolving ref "${ref}": ${await r.text()}`);
  }
  const j = (await r.json()) as Array<{ id?: string; commit?: { id?: string } }> | { id?: string };
  if (Array.isArray(j)) {
    const head = j[0];
    const sha = head?.id ?? head?.commit?.id;
    if (!sha) throw new Error(`HF API returned no SHA for ref "${ref}"`);
    return sha;
  }
  const sha = j.id;
  if (!sha) throw new Error(`HF API returned no SHA for ref "${ref}"`);
  return sha;
}

async function fetchAtRevision(split: string, revision: string): Promise<Buffer> {
  const url = `${HF_RESOLVE}/${REPO}/resolve/${revision}/${fileNameFor(split)}`;
  const r = await fetch(url, {
    headers: { "User-Agent": "memoria-nox-longmemeval-eval/0.1" },
    redirect: "follow",
  });
  if (!r.ok) throw new Error(`Fetch ${url} → ${r.status} ${r.statusText}`);
  const ab = await r.arrayBuffer();
  return Buffer.from(ab);
}

function sha256(buf: Buffer): string {
  return createHash("sha256").update(buf).digest("hex");
}

async function exists(p: string): Promise<boolean> {
  try {
    await stat(p);
    return true;
  } catch {
    return false;
  }
}

async function readLock(): Promise<DatasetLock> {
  if (!(await exists(LOCK_FILE))) {
    return {
      source_repo: REPO,
      source_url: `https://huggingface.co/datasets/${REPO}`,
      license: "MIT",
      citation:
        "Di Wu et al. LongMemEval: Benchmarking Chat Assistants on Long-Term Interactive Memory. ICLR 2025. arXiv:2410.10813.",
      splits: {},
    };
  }
  return JSON.parse(await readFile(LOCK_FILE, "utf8")) as DatasetLock;
}

function arg(name: string, fallback?: string): string | undefined {
  const i = process.argv.indexOf(name);
  if (i < 0) return fallback;
  return process.argv[i + 1] ?? fallback;
}

async function main(): Promise<void> {
  const split = arg("--split");
  if (!split || !VALID_SPLITS.has(split)) {
    console.error(`Usage: download.ts --split (oracle|s_cleaned|m_cleaned) [--revision <sha|ref>] [--check] [--force]`);
    console.error(`Got: --split ${split ?? "<missing>"}`);
    process.exit(2);
  }
  const checkOnly = process.argv.includes("--check");
  const force = process.argv.includes("--force");
  const ref = arg("--revision", DEFAULT_REV)!;

  await mkdir(DATA_DIR, { recursive: true });
  const dataFile = resolve(DATA_DIR, fileNameFor(split));

  if (checkOnly) {
    const lock = await readLock();
    const splitLock = lock.splits[split];
    if (!splitLock) {
      console.error(`[check] split "${split}" not present in lock; run without --check first`);
      process.exit(2);
    }
    if (!(await exists(dataFile))) {
      console.error(`[check] no cached file at ${dataFile}`);
      process.exit(2);
    }
    const buf = await readFile(dataFile);
    const have = sha256(buf);
    if (have !== splitLock.sha256) {
      console.error(`[check] sha256 mismatch on ${split}: file=${have} lock=${splitLock.sha256}`);
      process.exit(1);
    }
    console.log(`[check] OK split=${split} sha256=${have} bytes=${buf.length} rev=${splitLock.resolved_revision}`);
    return;
  }

  const lock = await readLock();
  if (!force && lock.splits[split] && (await exists(dataFile))) {
    console.error(`[download] cached: split=${split} file=${dataFile} rev=${lock.splits[split].resolved_revision}`);
    console.error(`[download] pass --force to re-download`);
    return;
  }

  console.error(`[download] resolving ref "${ref}"...`);
  const revision = await resolveRevision(ref);
  console.error(`[download] resolved → ${revision}`);

  console.error(`[download] fetching ${fileNameFor(split)} @ ${revision.slice(0, 10)}...`);
  const buf = await fetchAtRevision(split, revision);
  const hex = sha256(buf);

  await writeFile(dataFile, buf);
  lock.splits[split] = {
    split,
    file_name: fileNameFor(split),
    resolved_revision: revision,
    resolved_at: new Date().toISOString(),
    sha256: hex,
    size_bytes: buf.length,
  };
  await writeFile(LOCK_FILE, JSON.stringify(lock, null, 2));

  console.error(`[download] wrote ${dataFile} (${buf.length.toLocaleString()} bytes)`);
  console.error(`[download] wrote ${LOCK_FILE} (now tracks ${Object.keys(lock.splits).length} split(s))`);
  console.error(`[download] sha256=${hex}`);
}

main().catch((e) => {
  console.error("[download] ERROR:", e instanceof Error ? e.message : e);
  process.exit(1);
});
