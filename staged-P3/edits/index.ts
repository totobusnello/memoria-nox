/**
 * src/index.ts — P3 temporal queries CLI patch
 *
 * APPLIES ON TOP OF: staged-1.7a/edits/index.ts
 *
 * Changes: replace the "search" command definition with the P3 version
 * that adds --as-of and --changed-since flags.
 *
 * Replace this block in index.ts:
 *
 *   program
 *     .command("search <query>")
 *     .description("Search memory (FTS5 + boost + recency)")
 *     .option("-n, --limit <n>", "Number of results", "5")
 *     .option("--no-hybrid", "Disable semantic search (FTS5 only)")
 *     .action(async (query: string, opts: { limit: string; hybrid: boolean }) => {
 *       if (opts.hybrid) {
 *         const results = await searchHybrid(query, parseInt(opts.limit, 10));
 *         console.log(formatResults(results));
 *       } else {
 *         console.log(formatResults(search(query, parseInt(opts.limit, 10))));
 *       }
 *       closeDb();
 *     });
 *
 * WITH:
 */

// ── Add this import near the top of index.ts ─────────────────────────────────
// import { parseFlexibleDate } from "./dates.js";
// (dates.ts must be deployed alongside search.ts)

program
  .command("search <query>")
  .description("Search memory (FTS5 + boost + recency)")
  .option("-n, --limit <n>", "Number of results", "5")
  .option("--no-hybrid", "Disable semantic search (FTS5 only)")
  .option(
    "--as-of <date>",
    'Time-travel: only chunks that existed on this date. ' +
    'Accepts ISO 8601 ("2026-05-01", "2026-05-01T00:00:00Z") or relative ("7d", "1w", "2h", "15m").'
  )
  .option(
    "--changed-since <date>",
    'Only chunks created or updated after this date. ' +
    'Accepts ISO 8601 or relative ("7d", "1w", "2h", "15m").'
  )
  .action(async (query: string, opts: {
    limit: string;
    hybrid: boolean;
    asOf?: string;
    changedSince?: string;
  }) => {
    const { parseFlexibleDate } = await import("./dates.js");

    // Parse temporal flags — error early with clear message
    let asOf: Date | undefined;
    let changedSince: Date | undefined;

    try {
      if (opts.asOf) asOf = parseFlexibleDate(opts.asOf);
      if (opts.changedSince) changedSince = parseFlexibleDate(opts.changedSince);
    } catch (err) {
      console.error(`[ERROR] ${(err as Error).message}`);
      process.exit(1);
    }

    const filter = { asOf, changedSince };
    const limit = parseInt(opts.limit, 10);

    if (opts.hybrid) {
      const results = await searchHybrid(query, limit, filter);
      console.log(formatResults(results));
    } else {
      console.log(formatResults(search(query, limit, filter)));
    }
    closeDb();
  });
