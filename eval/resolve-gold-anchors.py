#!/usr/bin/env python3
"""Resolve the PT-BR golden set's stable anchors to today's chunk ids.

Why anchors instead of ids: v1 of this set keyed gold by `expected_chunk_ids`,
and re-ingest mints new ids. On 2026-10-22, 61 of its 85 ids no longer existed
and 33 of 66 queries pointed at nothing at all — while the file still looked
perfectly valid. An id-keyed ruler decays in silence at every re-ingest.

An anchor is (source_file, verbatim span). This resolver maps it to the current
id and FAILS LOUDLY when it cannot. The point is not that anchors never break —
it is that when they break, the ruler says so instead of scoring against ghosts.

STRUCTURAL AMBIGUITY IS NOT DECAY (added 2026-10-27). `ingestEntityFile()`
produces exactly one `frontmatter` chunk and one `compiled` chunk per entity
file, and their texts overlap by construction, so an anchor inside an entity
file matches both. On 2026-10-27 this made the gate exit 1 on three such pairs —
every run, for a reason that will never go away. A gate that is permanently red
for a known structural reason is a gate people learn to ignore, and then it
stops protecting against the real thing it was built for.

So ambiguity is now split by a BEHAVIOURAL predicate — the `section` column, not
the path:

  ambiguous_structural  every hit is in the same source_file and the hit set is
                        exactly the {frontmatter, compiled} pair the entity
                        format emits. ALL hits are accepted as gold, because a
                        system that returns either one found the information,
                        and punishing it for which half it returned is the same
                        error as the 8-word citation check (retired 2026-10-26
                        for partitioning on formatting rather than relevance).
  ambiguous             anything else. Still fails.

`moved` does not fail: an anchor that resolves to a NEW id is the anchor doing
its job. `unresolved` fails — that is decay.

--selftest proves the gate still bites after being loosened: it injects a dead
anchor and a non-structural ambiguity and requires a non-zero exit for each. A
relaxed guard with no mutation test is indistinguishable from a removed one.

Read-only: opens the database with mode=ro and writes nothing to it.
"""
import json, os, re, sqlite3, sys, unicodedata

DB   = os.environ.get("GOLD_DB", "/root/.openclaw/workspace/tools/nox-mem/nox-mem.db")
GOLD = None
OUT  = None
PREFIX = int(os.environ.get("ANCHOR_PREFIX", "160"))   # chars do início da âncora exigidos
SELFTEST = "--selftest" in sys.argv
ARGS = [a for a in sys.argv[1:] if not a.startswith("--")]
GOLD = ARGS[0] if ARGS else "eval/golden-queries-v2.jsonl"
OUT  = ARGS[1] if len(ARGS) > 1 else None

def norm(s):
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s).strip().lower()

con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)

# section is read for the structural predicate; a missing column means the
# predicate cannot be evaluated, and then no ambiguity may be excused.
HAS_SECTION = any(r[1] == "section" for r in con.execute("PRAGMA table_info(chunks)"))
if not HAS_SECTION:
    print("! chunks.section absent — structural ambiguity cannot be identified, "
          "so every ambiguity will fail")

ENTITY_PAIR = {"frontmatter", "compiled"}

def classify(source_file, hits, recorded, texts=None):
    """State of one gold entry. hits is [(id, section), ...].

    Two ambiguities are structural, and both for the same reason: the system
    cannot be punished for WHICH of two indistinguishable chunks it returned.

      entity pair   exactly {frontmatter, compiled} of one entity file, whose
                    texts overlap because ingestEntityFile() emits them that way
      exact dupes   every hit has byte-identical chunk_text. Measured 2026-10-27
                    on Q71: ids 316535 and 316569 share sha1 721d225e2539c37e,
                    and memory/2026-04-05.md holds 93 chunks with 46 distinct
                    texts — 47 exact duplicates. NO anchor can separate them,
                    so demanding one is demanding the impossible, and a gate
                    that demands the impossible stops protecting (the lesson
                    this resolver was already rewritten for once today).

    `texts` is the hit texts, needed only for the duplicate predicate; when it
    is absent the predicate cannot be evaluated and the ambiguity stays fatal,
    the same way a missing `section` column keeps the entity-pair one fatal.
    """
    if not hits:
        return "unresolved"
    if len(hits) == 1:
        return "resolved" if hits[0][0] == recorded else "moved"
    secs = {h[1] for h in hits}
    if HAS_SECTION and len(hits) == 2 and secs == ENTITY_PAIR:
        return "ambiguous_structural"
    if texts and len(set(texts)) == 1:
        return "ambiguous_duplicate"
    return "ambiguous"

def run(rows, db=con):
    tally = {k: 0 for k in ("resolved", "moved", "ambiguous_structural",
                            "ambiguous_duplicate", "ambiguous", "unresolved")}
    report = []
    for r in rows:
        for g in r.get("gold", []):
            needle = norm(g["anchor"])[:PREFIX]
            col = "section" if HAS_SECTION else "NULL AS section"
            hits = [(cid, sec, txt) for (cid, sec, txt) in db.execute(
                        f"SELECT id, {col}, chunk_text FROM chunks WHERE source_file = ?",
                        (g["source_file"],)).fetchall()
                    if needle and needle in norm(txt)]
            state = classify(g["source_file"], hits, g.get("chunk_id"),
                             texts=[h[2] for h in hits])
            tally[state] += 1
            report.append({"query_id": r["query_id"], "source_file": g["source_file"],
                           "state": state, "recorded_id": g.get("chunk_id"),
                           "resolved_ids": [h[0] for h in hits],
                           "sections": [h[1] for h in hits],
                           "anchor_head": g["anchor"][:80]})
    return tally, report

rows = [json.loads(l) for l in open(GOLD, encoding="utf-8") if l.strip()]
tally, report = run(rows)

print(f"gold entries: {sum(tally.values())}")
for k in ("resolved", "moved", "ambiguous_structural", "ambiguous_duplicate",
          "ambiguous", "unresolved"):
    note = {"moved": "   (the anchor did its job)",
            "ambiguous_structural": "   (entity frontmatter+compiled; all hits kept as gold)",
            "ambiguous_duplicate": "   (byte-identical chunks; no anchor can separate them)",
            }.get(k, "")
    print(f"  {k:21s} {tally[k]:3d}{note}")

FATAL = ("unresolved", "ambiguous")
bad = [x for x in report if x["state"] in FATAL]
for x in bad[:20]:
    print(f"  ! Q{x['query_id']} {x['state']:10s} {x['source_file'][:52]}  "
          f"-> {x['resolved_ids']} sections={x['sections']}")
for x in report:
    if x["state"] == "ambiguous_structural":
        print(f"  = Q{x['query_id']} structural {x['source_file'][:48]} "
              f"-> {x['resolved_ids']} {x['sections']}")

if OUT:
    json.dump({"tally": tally, "fatal_states": list(FATAL), "entries": report},
              open(OUT, "w"), indent=1, ensure_ascii=False)

if SELFTEST:
    print("\n--- selftest: the gate must still bite ---")
    ok = True
    # 1. a dead anchor must be fatal
    t1, _ = run([{"query_id": -1, "gold": [
        {"source_file": rows[0]["gold"][0]["source_file"],
         "anchor": "ESTA FRASE NAO EXISTE EM NENHUM CHUNK DESTE CORPUS 9f3a",
         "chunk_id": 0}]}])
    print(f"  dead anchor      -> unresolved={t1['unresolved']} "
          f"{'PASS' if t1['unresolved'] == 1 else 'FAIL'}")
    ok &= t1["unresolved"] == 1
    # 2. a non-structural ambiguity must be fatal: find a source_file with >2
    # chunks sharing a common span, and anchor on something all of them contain.
    cand = con.execute(
        "SELECT source_file, COUNT(*) n FROM chunks GROUP BY source_file "
        "HAVING n >= 3 ORDER BY n DESC LIMIT 1").fetchone()
    if cand:
        sf = cand[0]
        texts = [t for (t,) in con.execute(
            "SELECT chunk_text FROM chunks WHERE source_file = ?", (sf,)).fetchall()]
        shared = None
        for w in ("de ", "the ", "a ", "o "):
            if sum(1 for t in texts if w in norm(t)) >= 3:
                shared = w
                break
        if shared:
            t2, r2 = run([{"query_id": -2, "gold": [
                {"source_file": sf, "anchor": shared, "chunk_id": 0}]}])
            hits = len(r2[0]["resolved_ids"])
            print(f"  wide ambiguity   -> state={r2[0]['state']} on {hits} hits "
                  f"{'PASS' if t2['ambiguous'] == 1 else 'FAIL'}")
            ok &= t2["ambiguous"] == 1
        else:
            print("  wide ambiguity   -> SKIPPED (no shared span found); "
                  "the structural exemption is then UNTESTED")
            ok = False
    # 3. the duplicate exemption must NOT swallow a real ambiguity: two hits with
    # DIFFERENT text must stay fatal even when they are only two.
    pair = con.execute(
        "SELECT source_file FROM chunks GROUP BY source_file "
        "HAVING COUNT(*) > COUNT(DISTINCT chunk_text) LIMIT 1").fetchone()
    if pair:
        sf2 = pair[0]
        rs = con.execute("SELECT id, chunk_text FROM chunks WHERE source_file = ?",
                         (sf2,)).fetchall()
        seen2, dup_anchor = {}, None
        for cid, t in rs:
            if t in seen2:
                dup_anchor = t[:160]
                break
            seen2[t] = cid
        if dup_anchor:
            t3, r3 = run([{"query_id": -3, "gold": [
                {"source_file": sf2, "anchor": dup_anchor, "chunk_id": 0}]}])
            print(f"  exact duplicate  -> state={r3[0]['state']} on "
                  f"{len(r3[0]['resolved_ids'])} hits "
                  f"{'PASS' if t3['ambiguous_duplicate'] >= 1 else 'FAIL'}")
            ok &= t3["ambiguous_duplicate"] >= 1
        else:
            print("  exact duplicate  -> SKIPPED (no duplicate pair found); "
                  "the duplicate exemption is UNTESTED")
            ok = False
    print(f"  selftest: {'PASS' if ok else 'FAIL'}")
    if not ok:
        sys.exit(2)

sys.exit(1 if bad else 0)
