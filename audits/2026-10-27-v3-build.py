"""Build golden-queries-v3.jsonl. v2 is NOT touched — it is the artifact the
published interval was measured on, same rule that kept v1 intact.

Composition rules, each traceable to a measurement:
  accepted gold (57 entries)      kept verbatim
  rejected gold (38 entries)      replaced by the repaired chunk where one was
                                  found (file-level pass: 6; corpus-wide: 21),
                                  dropped where none was
  Q99                             status invalid_gold — its recorded gold is a
                                  per-call Groq limit against a question about
                                  storage capacity, and 0 of 40 candidates
                                  anywhere in the corpus answer it
  Q108, Q72                       added as accepted, built by the oracle pass
  Q52                             added as accepted_marginal, flagged
"""
import json, sqlite3
from collections import Counter

DB = "file:/root/.openclaw/workspace/tools/nox-mem/nox-mem.db?mode=ro"
THR = 0.5
con = sqlite3.connect(DB, uri=True)
rows = [json.loads(l) for l in
        open("/root/medicoes/golden-queries-v2.jsonl", encoding="utf-8") if l.strip()]
audit = json.load(open("/root/medicoes/gold-audit-2026-10-27.json"))
resel = json.load(open("/root/medicoes/v3-reselect-2026-10-27.json"))
wide = json.load(open("/root/medicoes/v3-corpuswide-2026-10-27.json"))

acc = {(r["query_id"], r["chunk_id"]) for r in audit
       if r["kind"] == "gold" and (r.get("responde") or 0) > THR}
rej = {(r["query_id"], r["chunk_id"]) for r in audit
       if r["kind"] == "gold" and (r.get("responde") or 0) <= THR}

def best_from(src, kind="candidate"):
    out = {}
    for r in src:
        if r["kind"] != kind or "responde" not in r:
            continue
        if (r["responde"] or 0) > THR:
            b = out.get(r["query_id"])
            if b is None or r["responde"] > b["responde"]:
                out[r["query_id"]] = r
    return out

rep_file, rep_wide = best_from(resel), best_from(wide)
print(f"repairs available: file-level {len(rep_file)} · corpus-wide {len(rep_wide)}")


def unique_anchor(source_file, chunk_id, text, start=200, cap=600):
    """An anchor must resolve to ONE chunk, and a 200-char prefix need not.

    Measured: the first build produced an anchor for Q71 that matched two chunks
    of memory/2026-04-05.md (316535, 316569), neither of them the structural
    frontmatter+compiled pair, so the resolver failed it as `ambiguous` — which
    is the gate working, not a false alarm. Chunks of the same file can share a
    prefix, and the fix is to lengthen the span until it is unique within the
    file, then fall back to a distinctive interior slice.
    """
    import unicodedata as _u, re as _re
    def _n(x):
        x = _u.normalize("NFKD", x or "")
        x = "".join(c for c in x if not _u.combining(c))
        return _re.sub(r"\s+", " ", x).strip().lower()
    sibs = [(cid, t) for (cid, t) in con.execute(
        "SELECT id, chunk_text FROM chunks WHERE source_file = ?", (source_file,))]
    def hits(a):
        nd = _n(a)[:160]
        return [cid for cid, t in sibs if nd and nd in _n(t)]
    for ln in range(start, cap + 1, 100):
        a = text[:ln]
        h = hits(a)
        if h == [chunk_id]:
            return a
    # prefix never disambiguates: take an interior slice, which a shared header
    # cannot cover
    for off in range(200, max(len(text) - 200, 201), 200):
        a = text[off:off + 300]
        if hits(a) == [chunk_id]:
            return a
    return text[:start]   # resolver will flag it; better flagged than silent

NEW = {
 108: ("memory/entities/systems/nox-mem.md",
       "**2026-04-27** — [milestone] Corpus tripled: 20.831 → 62.836 chunks via Claude workspace + GitHub repos + Mac local imports.", "accepted"),
 72: ("events/mac/memoria-nox/cmem-memoria-nox-2026-03-20.md",
      "**completed:** Deployed 7 new TypeScript modules: cross-search.ts (7-database search), dedup.ts", "accepted"),
 52: ("memory/state-snapshot.md",
      "`nox-mem reindex` → rebuild index (safe, idempotent)", "accepted_marginal"),
}

out, stats = [], Counter()
for r in rows:
    q = r["query_id"]
    new = dict(r)
    if q in NEW and r.get("status") != "accepted":
        sf, anc, st = NEW[q]
        hit = con.execute(
            "SELECT id FROM chunks WHERE source_file = ? AND instr(chunk_text, ?) > 0",
            (sf, anc[:60])).fetchone()
        if hit:
            new["gold"] = [{"source_file": sf, "anchor": anc, "chunk_id": hit[0]}]
            new["status"] = st
            new["provenance"] = "oracle-pass-2026-10-27"
            stats[f"added_{st}"] += 1
            out.append(new); continue
        stats["added_failed_to_resolve"] += 1

    if r.get("status") != "accepted":
        out.append(new); continue

    kept = [g for g in r.get("gold", []) if (q, g.get("chunk_id")) in acc]
    stats["gold_kept"] += len(kept)
    dropped = [g for g in r.get("gold", []) if (q, g.get("chunk_id")) in rej]
    if dropped:
        b = rep_file.get(q) or rep_wide.get(q)
        if b:
            txt = con.execute("SELECT chunk_text FROM chunks WHERE id=?",
                              (b["chunk_id"],)).fetchone()
            kept.append({"source_file": b["source_file"],
                         "anchor": unique_anchor(b["source_file"], b["chunk_id"],
                                                 txt[0] if txt else b.get("anchor", "")),
                         "chunk_id": b["chunk_id"],
                         "provenance": ("reselect-file-2026-10-27" if q in rep_file
                                        else "reselect-corpus-2026-10-27"),
                         "judge_responde": round(b["responde"], 3)})
            stats["gold_repaired"] += 1
        else:
            stats["gold_dropped_unrepairable"] += len(dropped)
    new["gold"] = kept
    if not kept:
        new["status"] = "invalid_gold"
        new["invalid_reason"] = ("recorded gold does not answer the question and 0 of 40 "
                                "candidates anywhere in the corpus do")
        stats["became_invalid"] += 1
    out.append(new)

P = "/root/medicoes/golden-queries-v3.jsonl"
with open(P, "w", encoding="utf-8") as f:
    for r in out:
        f.write(json.dumps(r, ensure_ascii=False) + "\n")

print(f"\nv3 written: {len(out)} queries · {sum(len(r.get('gold') or []) for r in out)} gold entries")
print("stats:", dict(stats))
st = Counter(r.get("status") for r in out)
print("status:", dict(st))
scorable = [r for r in out if r.get("status") in ("accepted", "accepted_marginal")]
print(f"\nscorable: {len(scorable)} (v2 had 55) · "
      f"invalid_gold: {st.get('invalid_gold', 0)}")
noprov = sum(1 for r in scorable for g in r["gold"] if "provenance" not in g)
print(f"gold entries unchanged from v2: {noprov} · repaired or added: "
      f"{sum(len(r['gold']) for r in scorable) - noprov}")
