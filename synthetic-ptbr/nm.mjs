// Calls into an installed nox-mem package, the way its own CLI and watcher do. Used by
// method-tests.py; NOX_DB_PATH, OPENCLAW_WORKSPACE and HOME come from the caller, always isolated.
//
//   node nm.mjs <dist dir> search <queries.json>     -> {"<qid>": [{"id","score","source_file"}...]}
//   node nm.mjs <dist dir> watcher-unlink <rel path>  -> what the version's watcher does when a
//                                                        file leaves the disk
//
// search: the FTS path of `nox-mem search --no-hybrid` (search() in search.js), top 10, with
// trackAccess = false so a probe query never feeds the ranking signals it is measuring.
// watcher-unlink: 3.11.1's watch.js tombstones the file's chunks (tombstoneFile, chunks KEPT);
// 3.5.2's watch.js returns on a missing path (`return; // deleted`) and does nothing. Both are
// reproduced by calling the version's own code when it has it, never by re-implementing it.
import { existsSync, readFileSync } from "node:fs";
import { join, resolve } from "node:path";
import { pathToFileURL } from "node:url";

const [dist, cmd, arg] = process.argv.slice(2);
const mod = (p) => import(pathToFileURL(join(dist, p)).href);
const out = (o) => process.stdout.write(JSON.stringify(o) + "\n");

if (cmd === "search") {
  const { search } = await mod("search.js");
  const { closeDb } = await mod("db.js");
  const queries = JSON.parse(readFileSync(arg, "utf8"));
  const res = {};
  for (const q of queries) {
    res[q.id] = search(q.text, 10, false).map((r) => ({ id: r.id, score: r.score, source_file: r.source_file }));
  }
  closeDb();
  out(res);
} else if (cmd === "watcher-unlink") {
  if (!existsSync(join(dist, "lib", "tombstone.js"))) {
    out({ action: "none", why: "this version's watcher returns on a missing path" });
  } else {
    const { tombstoneFile } = await mod("lib/tombstone.js");
    const { getDb, closeDb } = await mod("db.js");
    const abs = resolve(process.env.OPENCLAW_WORKSPACE, arg);
    const r = tombstoneFile(getDb(), arg, existsSync(abs), "deleted");
    closeDb();
    out({ action: "tombstoneFile", result: r });
  }
} else {
  console.error("usage: nm.mjs <dist> search <queries.json> | watcher-unlink <rel path>");
  process.exit(2);
}
