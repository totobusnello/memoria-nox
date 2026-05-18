/**
 * benchmark/scripts/accumulate-history.ts — History accumulation script.
 *
 * Reads all benchmark/history/YYYY-MM-DD.json files, generates:
 *   - benchmark/history/TIMESERIES.md  — markdown table for contributors
 *   - benchmark/history/timeseries.json — chart-friendly JSON for dashboard
 *
 * Also detects step changes (>20% sudden drift between consecutive days)
 * and flags them in both outputs.
 *
 * Runs on each PR merge (post-merge hook) or manually:
 *   npx tsx benchmark/scripts/accumulate-history.ts
 *   npx tsx benchmark/scripts/accumulate-history.ts --step-change-threshold=15
 *   npx tsx benchmark/scripts/accumulate-history.ts --window=60   # 60-day window
 *
 * Environment:
 *   NOX_STEP_CHANGE_THRESHOLD_PCT  — step-change detection threshold (default: 20)
 *   NOX_HISTORY_WINDOW_DAYS        — rolling window (default: 30)
 */

import { readdirSync, readFileSync, writeFileSync, existsSync, mkdirSync } from 'node:fs';
import { resolve, join, dirname } from 'node:path';
import { fileURLToPath } from 'node:url';

// ─── Config ───────────────────────────────────────────────────────────────────

const argv = process.argv.slice(2);

const stepChangeThreshold = (() => {
  const m = argv.find(a => a.startsWith('--step-change-threshold='));
  if (m) return parseFloat(m.split('=')[1]!);
  return parseFloat(process.env['NOX_STEP_CHANGE_THRESHOLD_PCT'] ?? '20');
})();

const windowDays = (() => {
  const m = argv.find(a => a.startsWith('--window='));
  if (m) return parseInt(m.split('=')[1]!, 10);
  return parseInt(process.env['NOX_HISTORY_WINDOW_DAYS'] ?? '30', 10);
})();

const __dirname_fallback = dirname(fileURLToPath(import.meta.url));
const REPO_ROOT = resolve(__dirname_fallback, '..', '..');
const HISTORY_DIR = join(REPO_ROOT, 'benchmark', 'history');

// ─── Types ────────────────────────────────────────────────────────────────────

interface MetricResult {
  metric_key: string;
  baseline: number;
  measured: number | null;
  drift_pct: number | null;
  status: 'PASS' | 'FAIL' | 'SKIP' | 'BASELINE_ONLY';
  unit: string;
}

interface NightlyReport {
  version: string;
  baseline_timestamp: string;
  run_timestamp: string;
  overall_status: 'PASS' | 'FAIL' | 'SKIP';
  drift_threshold_pct: number;
  nightly_threshold_pct?: number;
  nightly_date?: string;
  github_run_id?: string;
  github_sha?: string;
  passed: number;
  failed: number;
  skipped: number;
  baseline_only: number;
  results: MetricResult[];
}

interface DayRow {
  date: string;
  overall: string;
  passed: number;
  failed: number;
  skipped: number;
  metrics: Record<string, number | null>;
  drifts: Record<string, number | null>;
}

interface StepChange {
  date: string;
  prev_date: string;
  metric_key: string;
  unit: string;
  prev_value: number;
  curr_value: number;
  change_pct: number;
}

interface TimeseriesJson {
  generated: string;
  window_days: number;
  step_change_threshold_pct: number;
  all_metric_keys: string[];
  rows: Array<{
    date: string;
    overall: string;
    passed: number;
    failed: number;
    metrics: Record<string, number | null>;
    drifts: Record<string, number | null>;
  }>;
  step_changes: StepChange[];
}

// ─── Helpers ─────────────────────────────────────────────────────────────────

function isDateInWindow(dateStr: string, windowDays: number): boolean {
  const cutoff = new Date();
  cutoff.setUTCDate(cutoff.getUTCDate() - windowDays);
  const cutoffStr = cutoff.toISOString().slice(0, 10);
  return dateStr >= cutoffStr;
}

function formatPct(pct: number | null): string {
  if (pct === null) return '—';
  const sign = pct > 0 ? '+' : '';
  return `${sign}${pct.toFixed(2)}%`;
}

// ─── Load history files ───────────────────────────────────────────────────────

function loadHistory(): DayRow[] {
  if (!existsSync(HISTORY_DIR)) {
    process.stderr.write(`[accumulate-history] History dir not found: ${HISTORY_DIR}\n`);
    return [];
  }

  const files = readdirSync(HISTORY_DIR)
    .filter(f => /^\d{4}-\d{2}-\d{2}\.json$/.test(f))
    .sort();

  const rows: DayRow[] = [];

  for (const f of files) {
    const date = f.replace('.json', '');
    if (!isDateInWindow(date, windowDays)) continue;

    let report: NightlyReport;
    try {
      report = JSON.parse(readFileSync(join(HISTORY_DIR, f), 'utf-8')) as NightlyReport;
    } catch (e) {
      process.stderr.write(`[accumulate-history] WARN: could not parse ${f}: ${(e as Error).message}\n`);
      continue;
    }

    const metrics: Record<string, number | null> = {};
    const drifts: Record<string, number | null> = {};

    for (const r of report.results ?? []) {
      metrics[r.metric_key] = r.measured;
      drifts[r.metric_key] = r.drift_pct;
    }

    rows.push({
      date,
      overall: report.overall_status,
      passed: report.passed ?? 0,
      failed: report.failed ?? 0,
      skipped: report.skipped ?? 0,
      metrics,
      drifts,
    });
  }

  return rows;
}

// ─── Step change detection ────────────────────────────────────────────────────

function detectStepChanges(rows: DayRow[], allKeys: string[]): StepChange[] {
  const changes: StepChange[] = [];

  for (let i = 1; i < rows.length; i++) {
    const prev = rows[i - 1]!;
    const curr = rows[i]!;

    for (const key of allKeys) {
      const prevVal = prev.metrics[key];
      const currVal = curr.metrics[key];

      if (prevVal == null || currVal == null) continue;
      if (prevVal === 0) continue; // avoid division by zero

      const changePct = ((currVal - prevVal) / Math.abs(prevVal)) * 100;

      if (Math.abs(changePct) > stepChangeThreshold) {
        changes.push({
          date: curr.date,
          prev_date: prev.date,
          metric_key: key,
          unit: '',           // unit info not stored in DayRow; omit for now
          prev_value: prevVal,
          curr_value: currVal,
          change_pct: changePct,
        });
      }
    }
  }

  return changes;
}

// ─── Generate TIMESERIES.md ───────────────────────────────────────────────────

function generateMarkdown(rows: DayRow[], allKeys: string[], stepChanges: StepChange[]): string {
  const lines: string[] = [];

  lines.push('# Benchmark History — Timeseries');
  lines.push('');
  lines.push(`_Updated: ${new Date().toISOString().slice(0, 10)} | Window: ${windowDays} days | Step-change threshold: ${stepChangeThreshold}%_`);
  lines.push('');

  if (rows.length === 0) {
    lines.push('> No history files found in the rolling window.');
    return lines.join('\n');
  }

  // Show up to 8 measured keys in the main table for readability.
  // Full data is in timeseries.json.
  const SHOWN_KEYS = allKeys.filter(k => rows.some(r => r.metrics[k] != null)).slice(0, 8);

  // Main table header.
  const headerCells = ['Date', 'Overall', 'Pass', 'Fail', ...SHOWN_KEYS];
  lines.push('| ' + headerCells.join(' | ') + ' |');
  lines.push('| ' + ['---', ':---:', '---:', '---:', ...SHOWN_KEYS.map(() => '---:')].join(' | ') + ' |');

  for (const row of rows) {
    const overallIcon = row.overall === 'PASS' ? 'PASS' : row.overall === 'FAIL' ? '**FAIL**' : row.overall;
    const cells = [
      row.date,
      overallIcon,
      String(row.passed),
      row.failed > 0 ? `**${row.failed}**` : '0',
      ...SHOWN_KEYS.map(k => {
        const v = row.metrics[k];
        const d = row.drifts[k];
        if (v == null) return '—';
        const dStr = d != null ? ` (${formatPct(d)})` : '';
        return `${v}${dStr}`;
      }),
    ];
    lines.push('| ' + cells.join(' | ') + ' |');
  }

  lines.push('');
  lines.push(`> Showing ${SHOWN_KEYS.length} of ${allKeys.length} metrics. Full data in [\`timeseries.json\`](timeseries.json).`);
  lines.push('');

  // Step changes section.
  if (stepChanges.length > 0) {
    lines.push('## Step Changes Detected');
    lines.push('');
    lines.push(`Sudden drifts > ${stepChangeThreshold}% between consecutive days:`);
    lines.push('');
    lines.push('| Date | Metric | Prev | Curr | Change |');
    lines.push('|------|--------|-----:|-----:|-------:|');
    for (const sc of stepChanges) {
      const changeStr = formatPct(sc.change_pct);
      lines.push(`| ${sc.date} | \`${sc.metric_key}\` | ${sc.prev_value} | ${sc.curr_value} | **${changeStr}** |`);
    }
    lines.push('');
    lines.push('> Step changes may indicate an architectural shift, hardware variance, or unintended regression.');
    lines.push('> Review the corresponding nightly run artifact for root cause.');
    lines.push('');
  } else {
    lines.push('## Step Changes');
    lines.push('');
    lines.push(`No step changes > ${stepChangeThreshold}% detected in the rolling ${windowDays}-day window.`);
    lines.push('');
  }

  lines.push('---');
  lines.push('');
  lines.push('## How to update the baseline');
  lines.push('');
  lines.push('If a step change reflects an intentional improvement, update the baseline:');
  lines.push('');
  lines.push('```bash');
  lines.push('# 1. Run the bench locally to capture new numbers:');
  lines.push('npx tsx benchmark/regression-detector.ts --json-only > /tmp/new-report.json');
  lines.push('');
  lines.push('# 2. Extract and merge new metric values into baseline-2026-05-18.json');
  lines.push('#    (update only the metrics that intentionally changed).');
  lines.push('');
  lines.push('# 3. Commit with a clear message:');
  lines.push('git add benchmark/baseline-2026-05-18.json');
  lines.push('git commit -m "tune(bench): update baseline after [description of change]"');
  lines.push('```');
  lines.push('');
  lines.push('See [`docs/perf-regression.md`](../../docs/perf-regression.md) for full guidance.');

  return lines.join('\n');
}

// ─── Main ─────────────────────────────────────────────────────────────────────

async function main(): Promise<void> {
  process.stderr.write(`[accumulate-history] Loading history (window=${windowDays}d, step-threshold=${stepChangeThreshold}%)…\n`);

  const rows = loadHistory();

  if (rows.length === 0) {
    process.stderr.write('[accumulate-history] No history rows found. Writing empty outputs.\n');
  } else {
    process.stderr.write(`[accumulate-history] Loaded ${rows.length} day(s): ${rows[0]!.date} → ${rows[rows.length - 1]!.date}\n`);
  }

  // Collect all metric keys seen across all rows.
  const allKeysSet = new Set<string>();
  for (const row of rows) {
    for (const k of Object.keys(row.metrics)) {
      allKeysSet.add(k);
    }
  }
  const allKeys = [...allKeysSet].sort();

  // Detect step changes.
  const stepChanges = detectStepChanges(rows, allKeys);
  if (stepChanges.length > 0) {
    process.stderr.write(`[accumulate-history] ${stepChanges.length} step change(s) detected:\n`);
    for (const sc of stepChanges) {
      const dir = sc.change_pct > 0 ? '↑' : '↓';
      process.stderr.write(`  ${sc.date} ${sc.metric_key}: ${sc.prev_value} → ${sc.curr_value} (${dir}${Math.abs(sc.change_pct).toFixed(1)}%)\n`);
    }
  }

  // Ensure output dir exists.
  if (!existsSync(HISTORY_DIR)) {
    mkdirSync(HISTORY_DIR, { recursive: true });
  }

  // Write TIMESERIES.md.
  const md = generateMarkdown(rows, allKeys, stepChanges);
  const mdPath = join(HISTORY_DIR, 'TIMESERIES.md');
  writeFileSync(mdPath, md, 'utf-8');
  process.stderr.write(`[accumulate-history] Written: ${mdPath}\n`);

  // Write timeseries.json.
  const tsJson: TimeseriesJson = {
    generated: new Date().toISOString(),
    window_days: windowDays,
    step_change_threshold_pct: stepChangeThreshold,
    all_metric_keys: allKeys,
    rows: rows.map(row => ({
      date: row.date,
      overall: row.overall,
      passed: row.passed,
      failed: row.failed,
      metrics: Object.fromEntries(allKeys.map(k => [k, row.metrics[k] ?? null])),
      drifts: Object.fromEntries(allKeys.map(k => [k, row.drifts[k] ?? null])),
    })),
    step_changes: stepChanges,
  };
  const tsJsonPath = join(HISTORY_DIR, 'timeseries.json');
  writeFileSync(tsJsonPath, JSON.stringify(tsJson, null, 2), 'utf-8');
  process.stderr.write(`[accumulate-history] Written: ${tsJsonPath}\n`);

  // Print summary to stdout.
  const summary = {
    rows: rows.length,
    all_metric_keys: allKeys.length,
    step_changes: stepChanges.length,
    window_days: windowDays,
    step_change_threshold_pct: stepChangeThreshold,
    outputs: [mdPath, tsJsonPath],
  };
  process.stdout.write(JSON.stringify(summary, null, 2) + '\n');
}

main().catch(err => {
  process.stderr.write(`[accumulate-history] fatal: ${(err as Error).stack ?? err}\n`);
  process.exit(1);
});
