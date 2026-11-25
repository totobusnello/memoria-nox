#!/usr/bin/env python3
"""Step 1 of the synthetic corpus: the method tests of Paper A, run on the published nox-mem
package at two pinned versions. PLANO.md, «Objetivo (2026-11-25)», «Desenho da etapa 1».

  python3 -I synthetic-ptbr/method-tests.py --run --work <scratch dir>   ingest, rank, operate;
                                                                         freezes results/<version>/
  python3 -I synthetic-ptbr/method-tests.py --analyze                    results/etapa1.{txt,json}
  python3 -I synthetic-ptbr/method-tests.py --analyze --check            gate «S: reanálise»: the
                                                                         committed etapa1.txt is
                                                                         what the frozen files give

--run needs npm and the network (it installs nox-mem@3.5.2 and @3.11.1 under --work); nothing it
touches lives outside --work except the frozen files it writes under results/. Every nox-mem
process runs with NOX_DB_PATH, OPENCLAW_WORKSPACE and HOME inside --work.

What is measured, and the rules, fixed in this file before the first run:

FINDING 1 (anchor x id). For each of the 30 operation-target facts, two references are recorded on
the freshly ingested database: the id of the one chunk holding the primary sentence, and the anchor
(recorded path, the whole sentence). Then each file gets its operation, through the package:
  reingest_unchanged       `nox-mem ingest <file>`
  edit_outside_span        a sentence appended to a section that does not hold the primary; ingest
  edit_inside_span         the primary's value replaced by words; ingest (the evidence is gone)
  rename_with_reingest     mv; the version's watcher on the old path; `nox-mem ingest <new path>`
  rename_without_reingest  mv; nothing (watcher down)
  delete                   rm; the version's watcher on the old path
After all operations each reference is classified:
  live   it reaches a chunk holding the whole sentence, under the key of the file that holds the
         sentence on disk now, and that file is not tombstoned;
  stale  it reaches a chunk holding the sentence, but not live (file gone, moved, tombstoned);
  none   it reaches no chunk holding the sentence.
The anchor is resolved by eval/resolve-gold-anchors.py with ANCHOR_PREFIX above any sentence length
(whole-anchor mode). Every outcome is reported, including an id beating an anchor.

FINDING 2 (an unjudged result is not a miss). For each fact query, on the frozen baseline top 10:
  T (latent truth)  chunks holding any planted positive of the fact;
  R (registered)    chunks holding any positive kept in the plan's R (drawn before any ranking);
  P (pooled)        R plus the chunks of T found in the top 10.
nDCG@10 with the gold ideal under each; per query, R and P against T: how many fall, tie, rise.
Control: removing exactly the pooled additions gives back R's score on every query.

FINDING 4 (ideal). Under T, the gold ideal against the ranking ideal: on how many queries the score
changes, by how much, and on how many the ranking ideal is undefined (nothing relevant retrieved).
"""
import argparse
import collections
import json
import os
import pathlib
import shutil
import sqlite3
import subprocess
import sys

HERE = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import s_common as C  # noqa: E402
import importlib.util  # noqa: E402

_spec = importlib.util.spec_from_file_location("metrics", HERE / "metrics.py")
M = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(M)

VERSIONS = ["3.5.2", "3.11.1"]
RESULTS = HERE / "results"
RESOLVER = HERE.parent / "eval" / "resolve-gold-anchors.py"
EDIT_OUTSIDE = " Registro complementar acrescentado depois da revisão deste trecho."
EDIT_INSIDE_WORDS = "um valor ainda em aberto"


# ── run ─────────────────────────────────────────────────────────────────────────────────────────
def sh(cmd, env=None, cwd=None):
    r = subprocess.run(cmd, env=env, cwd=cwd, capture_output=True, text=True)
    if r.returncode != 0:
        raise SystemExit(f"command failed ({r.returncode}): {' '.join(map(str, cmd[:4]))} ...\n{r.stderr[-800:]}")
    return r.stdout


def chunks_of(db):
    con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
    rows = con.execute("SELECT id, source_file, section, chunk_text FROM chunks ORDER BY id").fetchall()
    tomb = set()
    # 3.11.1 keeps tombstones in chunk_tombstones (lib/tombstone.js); 3.5.2 has no such table
    if con.execute("SELECT 1 FROM sqlite_master WHERE name='chunk_tombstones'").fetchone():
        tomb = {r[0] for r in con.execute("SELECT source_file FROM chunk_tombstones").fetchall()}
    con.close()
    return [{"id": r[0], "source_file": r[1], "section": r[2], "text": r[3] or ""} for r in rows], tomb


def run_version(v, plan, work):
    pkg = work / f"pkg-{v}"
    if not (pkg / "node_modules" / "nox-mem" / "package.json").exists():
        sh(["npm", "install", "--prefix", str(pkg), f"nox-mem@{v}", "--no-audit", "--no-fund",
            "--loglevel=error"])
    dist = pkg / "node_modules" / "nox-mem" / "dist"
    installed = json.loads((pkg / "node_modules" / "nox-mem" / "package.json").read_text())["version"]
    bsq = json.loads((pkg / "node_modules" / "better-sqlite3" / "package.json").read_text())["version"]
    if installed != v:
        raise SystemExit(f"installed {installed}, wanted {v}")
    ws, db, home = work / f"ws-{v}", work / f"db-{v}.sqlite", work / "home"
    for p in (ws,):
        shutil.rmtree(p, ignore_errors=True)
    for p in work.glob(f"db-{v}.sqlite*"):
        p.unlink()
    home.mkdir(exist_ok=True)
    shutil.copytree(HERE / "corpus", ws)
    env = {"PATH": os.environ["PATH"], "HOME": str(home), "OPENCLAW_WORKSPACE": str(ws),
           "NOX_DB_PATH": str(db)}
    cli = ["node", str(dist / "index.js")]
    files = [f["path"] for f in plan["files"]]
    sh(cli + ["ingest"] + files, env=env, cwd=ws)
    base, _ = chunks_of(db)

    qfile = work / "queries.json"
    qfile.write_text(json.dumps([{"id": q["id"], "text": q["text"]} for q in plan["queries"]],
                                ensure_ascii=False))
    rankings = json.loads(sh(["node", str(HERE / "nm.mjs"), str(dist), "search", str(qfile)], env=env, cwd=ws))

    # references, recorded before any operation
    refs = []
    for f in plan["facts"]:
        if not f["operation"]:
            continue
        sent = f["primary"]["text"]
        holders = [c["id"] for c in base if sent in c["text"]]
        if len(holders) != 1:
            raise SystemExit(f"{f['id']}: primary in {len(holders)} chunks; run check-ingest first")
        refs.append({"fact": f["id"], "operation": f["operation"], "path": f["primary"]["path"],
                     "sentence": sent, "literal": f["literal"], "id": holders[0]})

    log = []
    for r in sorted(refs, key=lambda x: x["fact"]):
        p, op = ws / r["path"], r["operation"]
        new_rel = r["path"][:-3] + "-movido.md"
        step = {"fact": r["fact"], "operation": op, "commands": []}
        if op == "reingest_unchanged":
            sh(cli + ["ingest", r["path"]], env=env, cwd=ws)
            step["commands"].append("ingest")
        elif op == "edit_outside_span":
            blocks = p.read_text(encoding="utf-8").split("\n## ")
            k = next(i for i, b in enumerate(blocks) if r["sentence"] not in b)
            blocks[k] = blocks[k].rstrip("\n") + EDIT_OUTSIDE + ("\n" if k < len(blocks) - 1 else "\n")
            p.write_text("\n## ".join(blocks), encoding="utf-8")
            sh(cli + ["ingest", r["path"]], env=env, cwd=ws)
            step["commands"] += [f"append to section {k}", "ingest"]
        elif op == "edit_inside_span":
            t = p.read_text(encoding="utf-8")
            p.write_text(t.replace(r["sentence"], r["sentence"].replace(r["literal"], EDIT_INSIDE_WORDS)),
                         encoding="utf-8")
            sh(cli + ["ingest", r["path"]], env=env, cwd=ws)
            step["commands"] += ["value replaced", "ingest"]
        elif op in ("rename_with_reingest", "rename_without_reingest"):
            p.rename(ws / new_rel)
            step["commands"].append("mv")
            if op == "rename_with_reingest":
                w = json.loads(sh(["node", str(HERE / "nm.mjs"), str(dist), "watcher-unlink", r["path"]],
                                  env=env, cwd=ws))
                sh(cli + ["ingest", new_rel], env=env, cwd=ws)
                step["commands"] += [f"watcher on old path: {w['action']}", "ingest new path"]
        elif op == "delete":
            p.unlink()
            w = json.loads(sh(["node", str(HERE / "nm.mjs"), str(dist), "watcher-unlink", r["path"]],
                              env=env, cwd=ws))
            step["commands"] += ["rm", f"watcher on old path: {w['action']}"]
        log.append(step)

    after, tomb = chunks_of(db)
    gold = work / f"gold-{v}.jsonl"
    gold.write_text("".join(json.dumps({"query_id": i, "gold": [
        {"source_file": r["path"], "anchor": r["sentence"], "chunk_id": r["id"]}]}, ensure_ascii=False) + "\n"
        for i, r in enumerate(refs)), encoding="utf-8")
    rout = work / f"resolved-{v}.json"
    rout.unlink(missing_ok=True)  # a failed run must not leave an earlier run's output to be read
    rr = subprocess.run([sys.executable, "-I", str(RESOLVER), str(gold), str(rout)], capture_output=True,
                        env={**os.environ, "GOLD_DB": str(db), "ANCHOR_PREFIX": "100000"})
    # rc 1 is the resolver's own verdict when an anchor is ambiguous or unresolved; anything else is a failure
    if rr.returncode not in (0, 1) or not rout.exists():
        raise SystemExit(f"resolver failed (rc {rr.returncode}): {rr.stderr.decode()[-400:]}")
    resolved = json.loads(rout.read_text())["entries"]
    on_disk = {}
    for r in refs:
        hits = [str(q.relative_to(ws)) for q in ws.rglob("*.md") if r["sentence"] in q.read_text(encoding="utf-8")]
        on_disk[r["fact"]] = hits
    ids_after = {c["id"]: c for c in after}
    for i, r in enumerate(refs):
        c = ids_after.get(r["id"])
        r["after"] = {
            "id_row": None if c is None else {"source_file": c["source_file"],
                                              "has_sentence": r["sentence"] in c["text"]},
            "anchor": {"state": resolved[i]["state"], "ids": resolved[i]["resolved_ids"]},
            "anchor_rows": [{"id": x, "source_file": ids_after[x]["source_file"],
                             "has_sentence": r["sentence"] in ids_after[x]["text"]}
                            for x in resolved[i]["resolved_ids"] if x in ids_after],
            "sentence_on_disk_at": on_disk[r["fact"]],
        }

    out = RESULTS / v
    out.mkdir(parents=True, exist_ok=True)
    (out / "chunks-baseline.json").write_text(C.dump_json(base), encoding="utf-8")
    (out / "rankings.json").write_text(C.dump_json(rankings), encoding="utf-8")
    (out / "operations.json").write_text(C.dump_json({
        "version": installed, "better_sqlite3": bsq, "node": sh(["node", "--version"]).strip(),
        "tombstoned_files": sorted(tomb), "chunks_after": len(after), "log": log, "refs": refs}),
        encoding="utf-8")
    print(f"run {v}: {len(base)} chunks, {len(rankings)} rankings, {len(refs)} references")


# ── analyze ────────────────────────────────────────────────────────────────────────────────────
def classify(row_list, live_paths, tombstoned):
    """row_list: the chunks a reference reaches. live_paths: where the sentence is on disk now."""
    with_sentence = [r for r in row_list if r and r["has_sentence"]]
    if not with_sentence:
        return "none"
    if any(r["source_file"] in live_paths and r["source_file"] not in tombstoned for r in with_sentence):
        return "live"
    return "stale"


def analyze(plan):
    report = {"versions": {}}
    lines = ["# Synthetic PT-BR corpus, step 1: method tests on nox-mem (generated by method-tests.py)", ""]
    for v in VERSIONS:
        d = RESULTS / v
        base = json.loads((d / "chunks-baseline.json").read_text())
        rankings = json.loads((d / "rankings.json").read_text())
        ops = json.loads((d / "operations.json").read_text())
        tomb = set(ops["tombstoned_files"])

        # finding 1
        table = collections.defaultdict(collections.Counter)
        for r in ops["refs"]:
            live = set(r["after"]["sentence_on_disk_at"])
            idc = classify([r["after"]["id_row"]], live, tomb)
            anc = classify(r["after"]["anchor_rows"], live, tomb)
            table[r["operation"]][f"id:{idc}"] += 1
            table[r["operation"]][f"anchor:{anc}"] += 1
            table[r["operation"]][f"anchor_state:{r['after']['anchor']['state']}"] += 1

        # finding 2 and 4
        text = {c["id"]: c["text"] for c in base}
        # every count is written, zeros included: an absent key reads as «not measured»
        f2 = collections.Counter({k: 0 for k in (
            "control_failed", "strict_below", "strict_equal", "strict_above", "pooled_below",
            "pooled_equal", "pooled_above", "queries_with_negative_above_first_positive")})
        ideal = collections.Counter({k: 0 for k in ("changed", "unchanged", "ranking_ideal_undefined")})
        diffs = []
        per_q = []
        raw = collections.defaultdict(list)  # unrounded scores: means are taken over these, not over per_q
        zero_r_top = zero_r_rel = 0
        for q in plan["queries"]:
            if q["kind"] != "fact":
                continue
            fact = next(f for f in plan["facts"] if f["id"] == q["fact"])
            items = {fact["primary"]["id"]: fact["primary"]["text"],
                     **{a["id"]: a["text"] for a in fact["paraphrases"]}}
            T = {cid for cid, t in text.items() if any(items[i] in t for i in q["T"])}
            R = {cid for cid, t in text.items() if any(items[i] in t for i in q["R"])}
            rank = [x["id"] for x in rankings[q["id"]]]
            P = M.pooled(R, T, rank)
            st, po, tr = M.ndcg_gold(rank, R), M.ndcg_gold(rank, P), M.ndcg_gold(rank, T)
            back = M.ndcg_gold(rank, P - (P - R))
            if back != st:
                f2["control_failed"] += 1
            for name, s in (("strict", st), ("pooled", po)):
                f2[f"{name}_" + ("below" if s < tr - 1e-12 else "above" if s > tr + 1e-12 else "equal")] += 1
            if st == 0:
                zero_r_top += len(rank)
                zero_r_rel += sum(1 for x in rank if x in T)
            ri = M.ndcg_ranking_ideal(rank, T)
            if ri is None:
                ideal["ranking_ideal_undefined"] += 1
            elif abs(ri - tr) > 1e-12:
                ideal["changed"] += 1
                diffs.append(ri - tr)
            else:
                ideal["unchanged"] += 1
            negs = {cid for cid, t in text.items()
                    if any(n["text"] in t for n in fact["negatives"])}
            first_pos = next((i for i, x in enumerate(rank) if x in T), None)
            neg_above = sum(1 for i, x in enumerate(rank) if x in negs and (first_pos is None or i < first_pos))
            f2["queries_with_negative_above_first_positive"] += 1 if neg_above else 0
            raw["strict"].append(st); raw["pooled"].append(po); raw["true"].append(tr)
            per_q.append({"query": q["id"], "T": len(T), "R": len(R), "P": len(P),
                          "strict": round(st, 4), "pooled": round(po, 4), "true": round(tr, 4),
                          "ranking_ideal": None if ri is None else round(ri, 4)})
        n = len(per_q)
        mean = lambda k: round(sum(raw[k]) / n, 4)  # noqa: E731
        f2_out = {"queries": n, "mean_strict": mean("strict"), "mean_pooled": mean("pooled"),
                  "mean_true": mean("true"), **dict(sorted(f2.items())),
                  "zero_strict_top10_slots": zero_r_top, "of_which_truly_relevant": zero_r_rel}
        ideal_out = {**dict(sorted(ideal.items())),
                     "mean_change_when_changed": round(sum(diffs) / len(diffs), 4) if diffs else None,
                     "max_change": round(max(diffs), 4) if diffs else None}
        report["versions"][v] = {"package": ops["version"], "better_sqlite3": ops["better_sqlite3"],
                                 "node": ops["node"], "chunks": len(base),
                                 "finding1": {k: dict(sorted(c.items())) for k, c in sorted(table.items())},
                                 "finding2": f2_out, "finding4": ideal_out, "per_query": per_q}

        lines += [f"## nox-mem {ops['version']} (better-sqlite3 {ops['better_sqlite3']}, node {ops['node']}); "
                  f"{len(base)} chunks", "",
                  "Finding 1: after each operation (5 facts each), where each reference lands", "",
                  "| operation | id live | id stale | id none | anchor live | anchor stale | anchor none |",
                  "|---|---|---|---|---|---|---|"]
        for op in plan["operations"]:
            c = table[op]
            lines.append(f"| {op} | " + " | ".join(str(c[f'{k}:{s}']) for k in ('id', 'anchor')
                                                    for s in ('live', 'stale', 'none')) + " |")
        lines += ["", "Finding 2: nDCG@10, same ranking, three label sets", ""]
        lines += [f"- {k}: {v2}" for k, v2 in f2_out.items()]
        lines += ["", "Finding 4: ranking ideal against gold ideal, labels T", ""]
        lines += [f"- {k}: {v2}" for k, v2 in ideal_out.items()]
        lines.append("")
    return report, "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--run", action="store_true")
    ap.add_argument("--work")
    ap.add_argument("--analyze", action="store_true")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    plan = C.load_plan()
    if a.run:
        if not a.work:
            raise SystemExit("--run needs --work <scratch dir>")
        work = pathlib.Path(a.work).resolve()
        work.mkdir(parents=True, exist_ok=True)
        for v in VERSIONS:
            run_version(v, plan, work)
    if a.analyze:
        report, txt = analyze(plan)
        if a.check:
            same = (RESULTS / "etapa1.txt").read_text(encoding="utf-8") == txt
            print(f"method-tests --analyze --check: {'ok' if same else 'FAIL, etapa1.txt differs'}")
            return 0 if same else 1
        (RESULTS / "etapa1.json").write_text(C.dump_json(report), encoding="utf-8")
        (RESULTS / "etapa1.txt").write_text(txt, encoding="utf-8")
        print(txt)
    return 0


if __name__ == "__main__":
    sys.exit(main())
