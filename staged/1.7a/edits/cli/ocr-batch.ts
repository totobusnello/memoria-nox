// cli/ocr-batch.ts — E12 Tier 3 OCR batch command.
// Spec: memoria-nox/specs/2026-05-07-E12-tier3-ocr.md §9.6
//
// Modes:
//   --dry-run       → enumera PDFs, roda shouldRouteToOcr, estima cost — JSON output, sem mutação.
//   --smoke-test P  → executa engine em 1 PDF, dump JSON {textPreview, pageCount, costUsd}, sem DB.
//   sem flags       → real run: enqueue + executar engine + ingest + markJobStatus,
//                     sob withOpAudit (snapshot atômico). Hard-cap OCR_COST_CAP_USD.
//
// PESSOAL guard: OCR_PESSOAL_CLOUD_ALLOWED=1 (Toto autorizou) → cloud OK; =0 (default) → força tesseract.
// Cache OCR markdown: OPENCLAW_WORKSPACE/tools/nox-mem/cache/ocr/<sha256>.md (rastreabilidade).

import { mkdirSync, readdirSync, statSync, writeFileSync, existsSync } from "node:fs";
import { join, resolve } from "node:path";
import { homedir } from "node:os";
import { shouldRouteToOcr } from "../lib/ocr-detector.js";
import {
  enqueueOcrJob,
  getJobStats,
  listPendingJobs,
  markJobStatus,
  sha256OfFile,
} from "../lib/ocr-jobs.js";
import { createEngine, type OcrEngine } from "../lib/ocr-engine-stub.js";
import { withOpAudit, recordHeartbeat } from "../lib/op-audit.js";
import { routeIngest } from "../lib/ingest-router.js";
import { getDb } from "../db.js";

export interface OcrBatchOpts {
  folder?: string;
  engine: string;
  forceOcr: boolean;
  limit: number;
  dryRun: boolean;
  smokeTest?: string;
  retryFailed?: boolean;
}

interface PdfCandidate {
  path: string;
  sizeBytes: number;
}

interface DryRunReport {
  scanned: number;
  pdfsFound: number;
  wouldRoute: number;
  wouldSkip: number;
  estimatedTotalCostUsd: number;
  estimatedAvgPagesPerDoc: number;
  engine: string;
  folder: string;
  forceOcr: boolean;
  candidates: Array<{
    path: string;
    sizeBytes: number;
    decision: { route: boolean; reason: string };
    estimatedPages: number;
    estimatedCostUsd: number;
    engineUsed: string;
  }>;
}

const PAGES_PER_MB_HEURISTIC = 2; // 2 pages/MB conservador.
const DEFAULT_PAGES_PER_DOC = 30;
const DEFAULT_COST_CAP_USD = 50;
const TEXT_PREVIEW_CHARS = 800;

function getCostCap(): number {
  const v = parseFloat(process.env.OCR_COST_CAP_USD ?? "");
  return Number.isFinite(v) && v > 0 ? v : DEFAULT_COST_CAP_USD;
}

function pessoalCloudAllowed(): boolean {
  return process.env.OCR_PESSOAL_CLOUD_ALLOWED === "1";
}

function isPessoalPath(p: string): boolean {
  return /\/PESSOAL(\/|$)/i.test(p);
}

function getCacheDir(): string {
  const ws = process.env.OPENCLAW_WORKSPACE || "/root/.openclaw/workspace";
  const dir = join(ws, "tools/nox-mem/cache/ocr");
  if (!existsSync(dir)) mkdirSync(dir, { recursive: true, mode: 0o700 });
  return dir;
}

function listFailedJobsAsCandidates(limit = 0, overrideEngine?: string): PdfCandidate[] {
  // Re-run failed OCR jobs by rebuilding PdfCandidate list from ocr_jobs status=failed.
  // Workflow: re-enqueue (idempotent via sha256) flips status queued; runRealBatch reprocesses.
  // After successful retry, sha256 conflict resolves to existing job_id and status updates.
  //
  // CRITICAL (2026-05-08 bug fix): runRealBatch uses job.engine (column) NOT opts.engine.
  // Retry without overriding engine column = re-run via SAME engine (cloud → cloud).
  // Pass overrideEngine to UPDATE engine column, ensuring CLI --engine tesseract takes effect.
  const db = getDb();
  const sql = limit > 0
    ? `SELECT source_path, source_size_bytes FROM ocr_jobs WHERE status = 'failed' ORDER BY id DESC LIMIT ?`
    : `SELECT source_path, source_size_bytes FROM ocr_jobs WHERE status = 'failed' ORDER BY id DESC`;
  const rows = limit > 0 ? db.prepare(sql).all(limit) : db.prepare(sql).all();
  const out: PdfCandidate[] = [];
  for (const r of rows as Array<{ source_path: string; source_size_bytes: number | null }>) {
    if (existsSync(r.source_path)) {
      out.push({ path: r.source_path, sizeBytes: r.source_size_bytes ?? 0 });
    }
  }
  if (out.length > 0) {
    const placeholders = out.map(() => "?").join(",");
    if (overrideEngine) {
      // Reset status AND override engine column atomically.
      const reset = db.prepare(
        `UPDATE ocr_jobs SET status = 'queued', error_message = NULL, engine = ? WHERE status = 'failed' AND source_path IN (${placeholders})`,
      );
      reset.run(overrideEngine, ...out.map((c) => c.path));
    } else {
      // Reset status only — keep original engine.
      const reset = db.prepare(
        `UPDATE ocr_jobs SET status = 'queued', error_message = NULL WHERE status = 'failed' AND source_path IN (${placeholders})`,
      );
      reset.run(...out.map((c) => c.path));
    }
  }
  return out;
}

function listPdfs(root: string, limit = 0): PdfCandidate[] {
  const out: PdfCandidate[] = [];
  function walk(dir: string): void {
    if (limit > 0 && out.length >= limit) return;
    let entries: string[] = [];
    try {
      entries = readdirSync(dir);
    } catch {
      return;
    }
    for (const name of entries) {
      if (limit > 0 && out.length >= limit) return;
      const full = join(dir, name);
      let st;
      try {
        st = statSync(full);
      } catch {
        continue;
      }
      if (st.isDirectory()) {
        if (name.startsWith(".") || name === "node_modules") continue;
        walk(full);
      } else if (st.isFile() && name.toLowerCase().endsWith(".pdf")) {
        out.push({ path: full, sizeBytes: st.size });
      }
    }
  }
  walk(root);
  return out;
}

function estimatePages(sizeBytes: number): number {
  const mb = sizeBytes / (1024 * 1024);
  return Math.max(1, Math.round(mb * PAGES_PER_MB_HEURISTIC));
}

/**
 * Resolve qual engine usar pra um arquivo específico, aplicando PESSOAL guard.
 * Returns engine name string + warning se downgrade aconteceu.
 */
function resolveEngineForFile(
  filePath: string,
  requestedEngine: string,
): { engineName: string; warning?: string } {
  if (requestedEngine === "tesseract") return { engineName: "tesseract" };
  if (isPessoalPath(filePath) && !pessoalCloudAllowed()) {
    return {
      engineName: "tesseract",
      warning: `PESSOAL/ + OCR_PESSOAL_CLOUD_ALLOWED!=1 → forced tesseract: ${filePath}`,
    };
  }
  return { engineName: requestedEngine };
}

export async function ocrBatch(opts: OcrBatchOpts): Promise<void> {
  // Smoke test: bypass tudo, só testa engine end-to-end em 1 PDF.
  if (opts.smokeTest) {
    await runSmokeTest(opts.smokeTest, opts.engine);
    return;
  }

  const folder = resolve(opts.folder ?? join(homedir(), "Documents"));
  const limit = opts.limit > 0 ? opts.limit : 0;

  // Validate engine name early (creates throws errors com mensagem clara).
  let probeEngine: OcrEngine;
  try {
    probeEngine = createEngine(opts.engine);
  } catch (err: any) {
    console.error(`[ocr-batch] engine init failed: ${err.message}`);
    process.exit(1);
  }

  let candidates: PdfCandidate[];
  if (opts.retryFailed) {
    console.error(`[ocr-batch] retry mode: rebuilding candidates from ocr_jobs WHERE status=failed`);
    // Pass opts.engine as override to update jobs.engine column (fixes 2026-05-07 bug
    // where Phase 2 tesseract retry actually re-ran cloud because job.engine was sticky).
    candidates = listFailedJobsAsCandidates(limit, opts.engine);
    console.error(`[ocr-batch] found ${candidates.length} failed jobs to retry (engine override → ${opts.engine})`);
  } else {
    console.error(`[ocr-batch] scanning ${folder} (limit=${limit || "none"})`);
    candidates = listPdfs(folder, limit);
    console.error(`[ocr-batch] found ${candidates.length} PDFs`);
  }

  if (opts.dryRun) {
    const report = await runDryRun(candidates, probeEngine, opts);
    process.stdout.write(JSON.stringify(report, null, 2) + "\n");
    return;
  }

  await runRealBatch(candidates, opts);
}

async function runSmokeTest(pdfPath: string, engineName: string): Promise<void> {
  const abs = resolve(pdfPath);
  if (!existsSync(abs)) {
    console.error(`[smoke-test] file not found: ${abs}`);
    process.exit(1);
  }
  const { engineName: resolved, warning } = resolveEngineForFile(abs, engineName);
  if (warning) console.error(`[smoke-test] ${warning}`);

  const engine = createEngine(resolved);
  console.error(`[smoke-test] engine=${resolved} file=${abs}`);
  const t0 = Date.now();
  let result;
  try {
    result = await engine.ocrFile(abs);
  } catch (err: any) {
    process.stdout.write(
      JSON.stringify(
        {
          ok: false,
          file: abs,
          engine: resolved,
          error: err?.message ?? String(err),
          durationMs: Date.now() - t0,
        },
        null,
        2,
      ) + "\n",
    );
    process.exit(2);
  }
  const preview = (result.markdown ?? "").slice(0, TEXT_PREVIEW_CHARS);
  process.stdout.write(
    JSON.stringify(
      {
        ok: true,
        file: abs,
        engine: resolved,
        pageCount: result.pageCount,
        costUsd: Number(result.costUsd.toFixed(4)),
        charCount: (result.markdown ?? "").length,
        textPreview: preview,
        truncatedPreview: (result.markdown ?? "").length > TEXT_PREVIEW_CHARS,
        durationMs: Date.now() - t0,
      },
      null,
      2,
    ) + "\n",
  );
}

async function runRealBatch(candidates: PdfCandidate[], opts: OcrBatchOpts): Promise<void> {
  const costCap = getCostCap();
  const cacheDir = getCacheDir();

  // Safeguard (2026-05-08): refuse if another ocr-batch is already running (>30min ago).
  // Prevents zombie batch from end-of-day Claude protocol or accidental dual-run.
  // Override via OCR_BATCH_FORCE=1 (escape hatch for legitimate cases like prior crash).
  const db = getDb();
  const activeRow = db
    .prepare(
      `SELECT id, started_at, pid FROM ops_audit
       WHERE op_name = 'ocr-batch-cloud' AND status IN ('running','started')
       AND (julianday('now') - julianday(started_at)) * 1440 < 30
       LIMIT 1`,
    )
    .get() as { id: number; started_at: string; pid: number } | undefined;
  if (activeRow && process.env.OCR_BATCH_FORCE !== "1") {
    console.error(
      `[ocr-batch] REFUSE: another ocr-batch-cloud op is active (id=${activeRow.id}, pid=${activeRow.pid}, started=${activeRow.started_at}). ` +
        `If this is stale and you're sure it's safe, set OCR_BATCH_FORCE=1.`,
    );
    process.exit(3);
  }

  // Fase 3 / Gap D (2026-05-15) — hard timeout + heartbeat.
  // Default 3h (Forge Q9, 2026-05-15); env override pra batches grandes ocasionais.
  const HARD_TIMEOUT_MS = parseInt(process.env.OCR_HARD_TIMEOUT_MS ?? "10800000", 10);
  const HEARTBEAT_INTERVAL_MS = 5 * 60 * 1000; // 5min
  console.log(`[ocr-batch] hard timeout: ${(HARD_TIMEOUT_MS / 1000 / 60).toFixed(0)}min, heartbeat: 5min`);

  // Hard timeout: SIGTERM o próprio processo se exceder. Exit code 124 = standard timeout.
  // op-audit reapZombies vai detectar e marcar row como crashed.
  const hardTimeoutId = setTimeout(() => {
    console.error(
      `[ocr-batch] HARD TIMEOUT exceeded (${HARD_TIMEOUT_MS}ms). Terminating to prevent zombie.`,
    );
    process.exit(124);
  }, HARD_TIMEOUT_MS);
  hardTimeoutId.unref(); // não bloqueia event loop em caso de finish normal antes do timeout

  // Heartbeat interval: marca last_heartbeat_at a cada 5min pra watchdog detectar staleness.
  const heartbeatIntervalId = setInterval(() => {
    try {
      recordHeartbeat("ocr-batch-cloud");
    } catch (err) {
      console.error(`[ocr-batch] heartbeat write failed: ${(err as Error).message}`);
    }
  }, HEARTBEAT_INTERVAL_MS);
  heartbeatIntervalId.unref();

  // Issue #3B (2026-05-21): db_source is now explicit — 'main' (prod nox-mem.db).
  await withOpAudit("ocr-batch-cloud", { db_source: 'main' }, async () => {
    let enqueued = 0;
    let alreadyExisting = 0;
    let routeDeclined = 0;
    let processed = 0;
    let failed = 0;
    let totalCostUsd = 0;
    const errors: Array<{ path: string; error: string }> = [];

    // Phase 1: enqueue all eligible PDFs.
    for (const cand of candidates) {
      const decision = await shouldRouteToOcr(cand.path, { force: opts.forceOcr });
      if (!decision.route) {
        routeDeclined++;
        continue;
      }
      const { engineName: resolved, warning } = resolveEngineForFile(cand.path, opts.engine);
      if (warning) console.error(`[ocr-batch] ${warning}`);
      try {
        const r = await enqueueOcrJob(cand.path, resolved);
        if (r.alreadyExists) alreadyExisting++;
        else enqueued++;
      } catch (err: any) {
        errors.push({ path: cand.path, error: err.message });
      }
    }

    // Phase 2: process pending jobs.
    // Cap-aware loop: pre-flight cost estimate per job, abort se total > cap.
    const pending = listPendingJobs(10_000);
    const engineCache = new Map<string, OcrEngine>();
    function getEng(name: string): OcrEngine {
      let e = engineCache.get(name);
      if (!e) {
        e = createEngine(name);
        engineCache.set(name, e);
      }
      return e;
    }

    for (const job of pending) {
      const eng = getEng(job.engine);
      let estimatedPages = 0;
      try {
        estimatedPages = estimatePages(statSync(job.source_path).size);
      } catch {
        estimatedPages = DEFAULT_PAGES_PER_DOC;
      }
      const estCost = eng.estimateCostUsd(estimatedPages);
      if (totalCostUsd + estCost > costCap) {
        console.error(
          `[ocr-batch] HARD CAP HIT: spent=$${totalCostUsd.toFixed(2)} + est=$${estCost.toFixed(2)} > cap=$${costCap.toFixed(2)}. ` +
            `Aborting remaining ${pending.length - processed - failed} jobs.`,
        );
        break;
      }

      markJobStatus(job.id, "running");
      try {
        const result = await eng.ocrFile(job.source_path);
        const md = result.markdown ?? "";
        const cachedMdPath = join(cacheDir, `${job.source_sha256}.md`);
        writeFileSync(cachedMdPath, md, { mode: 0o600 });

        // Re-route via routeIngest (kind=markdown, originalSourcePath preserved).
        // Force kind=markdown pra evitar re-trigger de OCR probe sobre o .md gerado.
        await routeIngest(cachedMdPath, { forceKind: "markdown" });

        // Tag chunks com ocr_status + ocr_engine pra rastreabilidade
        // (foundation impl deixou null; retroactive UPDATE no DB fixou os 2487 da Phase 1).
        // Aqui aplica a cada batch novo, evitando regression.
        getDb()
          .prepare(
            `UPDATE chunks SET ocr_status = 'success', ocr_engine = ? WHERE source_file LIKE ? AND ocr_status IS NULL`,
          )
          .run(job.engine, `%cache/ocr/${job.source_sha256}.md`);

        markJobStatus(job.id, "success", {
          charCount: md.length,
          costUsd: result.costUsd,
          pageCount: result.pageCount,
        });
        totalCostUsd += result.costUsd;
        processed++;
        console.error(
          `[ocr-batch] [${processed}/${pending.length}] ok engine=${job.engine} ` +
            `pages=${result.pageCount} chars=${md.length} cost=$${result.costUsd.toFixed(4)} ` +
            `total=$${totalCostUsd.toFixed(2)} ${job.source_path}`,
        );
      } catch (err: any) {
        markJobStatus(job.id, "failed", { error: err?.message ?? String(err) });
        failed++;
        errors.push({ path: job.source_path, error: err?.message ?? String(err) });
        console.error(`[ocr-batch] FAIL ${job.source_path}: ${err?.message ?? err}`);
      }
    }

    const stats = getJobStats();
    const summary = {
      candidates: candidates.length,
      enqueued,
      alreadyExisting,
      routeDeclined,
      processed,
      failed,
      totalCostUsd: Number(totalCostUsd.toFixed(4)),
      costCapUsd: costCap,
      stats,
      errors: errors.slice(0, 50),
    };
    process.stdout.write(JSON.stringify(summary, null, 2) + "\n");
    return {
      affected_rows: processed,
      notes: `processed=${processed} failed=${failed} cost=$${totalCostUsd.toFixed(2)}`,
    };
  });

  // Cleanup Fase 3 / Gap D timers — execução normal chega aqui sem hard timeout
  clearTimeout(hardTimeoutId);
  clearInterval(heartbeatIntervalId);
}

async function runDryRun(
  candidates: PdfCandidate[],
  defaultEngine: OcrEngine,
  opts: OcrBatchOpts,
): Promise<DryRunReport> {
  const decisions: DryRunReport["candidates"] = [];
  let totalCost = 0;
  let totalPages = 0;
  let routeCount = 0;
  let skipCount = 0;
  // Engine cache per name (Tesseract instances cheap, but skip dup work).
  const engineCache = new Map<string, OcrEngine>([[defaultEngine.name, defaultEngine]]);
  function getEng(name: string): OcrEngine {
    let e = engineCache.get(name);
    if (!e) {
      e = createEngine(name);
      engineCache.set(name, e);
    }
    return e;
  }

  for (const cand of candidates) {
    const decision = await shouldRouteToOcr(cand.path, { force: opts.forceOcr });
    const { engineName: resolved } = resolveEngineForFile(cand.path, opts.engine);
    const eng = getEng(resolved);
    const pages = estimatePages(cand.sizeBytes);
    const cost = decision.route ? eng.estimateCostUsd(pages) : 0;
    if (decision.route) {
      routeCount++;
      totalCost += cost;
      totalPages += pages;
    } else {
      skipCount++;
    }
    decisions.push({
      path: cand.path,
      sizeBytes: cand.sizeBytes,
      decision,
      estimatedPages: pages,
      estimatedCostUsd: Number(cost.toFixed(4)),
      engineUsed: resolved,
    });
  }

  return {
    scanned: candidates.length,
    pdfsFound: candidates.length,
    wouldRoute: routeCount,
    wouldSkip: skipCount,
    estimatedTotalCostUsd: Number(totalCost.toFixed(2)),
    estimatedAvgPagesPerDoc:
      routeCount > 0 ? Math.round(totalPages / routeCount) : DEFAULT_PAGES_PER_DOC,
    engine: opts.engine,
    folder: resolve(opts.folder ?? join(homedir(), "Documents")),
    forceOcr: opts.forceOcr,
    candidates: decisions,
  };
}
