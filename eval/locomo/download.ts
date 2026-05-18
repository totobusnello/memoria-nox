/**
 * download.ts — fetch the LoCoMo dataset for memoria-nox evaluation.
 *
 * Source: https://github.com/snap-research/locomo  (CC BY-NC 4.0)
 * Citation: Maharana et al. 2024, arXiv:2402.17753
 *
 * Writes:
 *   eval/locomo/data/locomo10.json    (gitignored — license-restricted)
 *   eval/locomo/dataset.lock.json     (gitignored — local commit SHA + sha256)
 *
 * Usage:
 *   npx tsx eval/locomo/download.ts            # default mirror, main HEAD
 *   npx tsx eval/locomo/download.ts --sha abc  # pin to a specific commit
 *   npx tsx eval/locomo/download.ts --check    # verify cached file vs sha256 in lock
 *
 * No npm deps required. Uses node:fetch (Node ≥18) + node:crypto.
 */

import { createHash } from "node:crypto";
import { mkdir, readFile, writeFile, stat } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const __filename = fileURLToPath(import.meta.url);
const HERE = dirname(__filename);
const DATA_DIR = resolve(HERE, "data");
const DATA_FILE = resolve(DATA_DIR, "locomo10.json");
const LOCK_FILE = resolve(HERE, "dataset.lock.json");

const RAW_BASE = "https://raw.githubusercontent.com/snap-research/locomo";
const API_BASE = "https://api.github.com/repos/snap-research/locomo";
const FILE_PATH = "data/locomo10.json";

interface DatasetLock {
  source_repo: string;
  file_path: string;
  resolved_sha: string;
  resolved_at: string;
  sha256: string;
  size_bytes: number;
  license: string;
  citation: string;
}

async function resolveSha(ref: string): Promise<string> {
  // Map a ref like "main" or a tag to a commit SHA via the GitHub API.
  const r = await fetch(`${API_BASE}/commits/${encodeURIComponent(ref)}`, {
    headers: { "User-Agent": "memoria-nox-locomo-eval/0.1" },
  });
  if (!r.ok) {
    throw new Error(`GitHub API ${r.status} resolving ref "${ref}": ${await r.text()}`);
  }
  const j = (await r.json()) as { sha: string };
  return j.sha;
}

async function fetchAtSha(sha: string): Promise<Buffer> {
  const url = `${RAW_BASE}/${sha}/${FILE_PATH}`;
  const r = await fetch(url, { headers: { "User-Agent": "memoria-nox-locomo-eval/0.1" } });
  if (!r.ok) throw new Error(`Fetch ${url} → ${r.status}`);
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

async function main(): Promise<void> {
  const argv = process.argv.slice(2);
  const checkOnly = argv.includes("--check");
  const shaIdx = argv.indexOf("--sha");
  const refIdx = argv.indexOf("--ref");
  const force = argv.includes("--force");

  const ref =
    shaIdx >= 0 ? argv[shaIdx + 1]
    : refIdx >= 0 ? argv[refIdx + 1]
    : "main";

  await mkdir(DATA_DIR, { recursive: true });

  if (checkOnly) {
    if (!(await exists(DATA_FILE))) {
      console.error("[check] no cached dataset at", DATA_FILE);
      process.exit(2);
    }
    if (!(await exists(LOCK_FILE))) {
      console.error("[check] no lock file; run without --check first");
      process.exit(2);
    }
    const buf = await readFile(DATA_FILE);
    const lock: DatasetLock = JSON.parse(await readFile(LOCK_FILE, "utf8"));
    const have = sha256(buf);
    if (have !== lock.sha256) {
      console.error(`[check] sha256 mismatch: file=${have} lock=${lock.sha256}`);
      process.exit(1);
    }
    console.log(`[check] OK sha256=${have} bytes=${buf.length} sha=${lock.resolved_sha}`);
    return;
  }

  if (!force && (await exists(DATA_FILE)) && (await exists(LOCK_FILE))) {
    const lock: DatasetLock = JSON.parse(await readFile(LOCK_FILE, "utf8"));
    console.error(`[download] cached at ${DATA_FILE} (sha=${lock.resolved_sha})`);
    console.error("[download] pass --force to re-download");
    return;
  }

  console.error(`[download] resolving ref "${ref}"...`);
  const sha = ref.length === 40 && /^[0-9a-f]{40}$/i.test(ref) ? ref : await resolveSha(ref);
  console.error(`[download] resolved → ${sha}`);

  console.error(`[download] fetching ${FILE_PATH} @ ${sha.slice(0, 10)}...`);
  const buf = await fetchAtSha(sha);
  const hex = sha256(buf);

  await writeFile(DATA_FILE, buf);
  const lock: DatasetLock = {
    source_repo: "snap-research/locomo",
    file_path: FILE_PATH,
    resolved_sha: sha,
    resolved_at: new Date().toISOString(),
    sha256: hex,
    size_bytes: buf.length,
    license: "CC BY-NC 4.0",
    citation:
      "Maharana, Lee, Tulyakov, Bansal, Barbieri, Fang. Evaluating Very Long-Term Conversational Memory of LLM Agents. arXiv:2402.17753, 2024.",
  };
  await writeFile(LOCK_FILE, JSON.stringify(lock, null, 2));

  console.error(`[download] wrote ${DATA_FILE} (${buf.length.toLocaleString()} bytes)`);
  console.error(`[download] wrote ${LOCK_FILE}`);
  console.error(`[download] sha256=${hex}`);
}

main().catch((e) => {
  console.error("[download] ERROR:", e instanceof Error ? e.message : e);
  process.exit(1);
});
