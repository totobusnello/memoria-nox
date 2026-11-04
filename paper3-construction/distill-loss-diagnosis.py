#!/usr/bin/env python3
"""Where distillation loses the answer — exploratory, cache only, no API call.

READER-CEILING.md found that R3 answers 83.0% from the raw evidence sessions and 47.5% from their
C1 units. This takes the instances R3 gets right on E-raw and wrong on E-dist ("lost", 77) and the
ones it gets right on both ("kept"), and measures, mechanically, what C1 did to the turn that
carries the answer (LongMemEval marks it `has_answer`):

  block_empty     the 2,000-char block holding an answer turn produced ZERO units
                  (nothing at importance >= 0.5, or the call failed)
  role            whether the answer turns are the user's or the assistant's
  key_raw/units   share of the reference's content words (>= 4 letters) found in the answer turns
                  vs in the units of the evidence sessions — a recall proxy, not a verdict
  categories      the C1 category of the units served from evidence sessions

  python3 -I distill-loss-diagnosis.py --stage1-cache <cache.sqlite> [--examples N]
"""
import argparse
import collections
import importlib.util
import json
import os
import pathlib
import re

HERE = pathlib.Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("lr", HERE / "lme-run.py")
lr = importlib.util.module_from_spec(spec)
spec.loader.exec_module(lr)
ROWS = HERE / "runs" / "ceiling-2026-11-03" / "rows-ceiling.ndjson"
STOP = set("that this with from have what when where which were they them their there about would "
           "could should after before your into than then also been being just only some more most "
           "over very much many such each other does doing done".split())


def words(s):
    return {w for w in re.findall(r"[a-zà-ú]{4,}", s.lower()) if w not in STOP}


def answer_blocks(sess):
    """blocks of a session (as lr.session_blocks builds them) and which hold an answer turn."""
    kept = [t for t in sess if not lr.is_noise_static(t.get("content") or "")]
    lines = [f"[{(t.get('role') or 'unknown').upper()}]: {t.get('content') or ''}" for t in kept]
    # lr.blocks_of, replayed with turn indices so each block knows which turns it holds
    blocks, flags, cur, hit = [], [], "", False
    for t, line in zip(kept, lines):
        if len(cur) + len(line) > lr.BLOCK_SIZE and cur:
            blocks.append(cur.strip())
            flags.append(hit)
            cur, hit = line + "\n", bool(t.get("has_answer"))
        else:
            cur += line + "\n"
            hit = hit or bool(t.get("has_answer"))
    if cur.strip():
        blocks.append(cur.strip())
        flags.append(hit)
    assert blocks == lr.blocks_of(lines)
    return blocks, flags, [t for t in sess if t.get("has_answer")]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage1-cache", required=True)
    ap.add_argument("--data", default=os.path.expanduser(
        "~/datasets/longmemeval/longmemeval_s_cleaned.json"))
    ap.add_argument("--examples", type=int, default=0)
    a = ap.parse_args()
    data = {r["question_id"]: r for r in json.load(open(a.data))}
    cache = lr.Cache(a.stage1_cache)
    rows = [json.loads(l) for l in open(ROWS)]
    ok = {(x["qid"], x["arm"]): x["correct"] for x in rows if x["reader"] == "R3"}
    qids = sorted({x["qid"] for x in rows})
    groups = {"lost": [q for q in qids if ok[(q, "E-raw")] and not ok[(q, "E-dist")]],
              "kept": [q for q in qids if ok[(q, "E-raw")] and ok[(q, "E-dist")]]}

    out = {}
    for g, qs in groups.items():
        st = collections.Counter()
        cats = collections.Counter()
        roles = collections.Counter()
        by_type = collections.Counter()
        kr, ku = [], []
        ex = []
        for q in qs:
            r = data[q]
            by_type[r["question_type"]] += 1
            ref = words(str(r["answer"]))
            ans_text, unit_text = "", ""
            any_empty = all_empty = None
            for i in sorted(lr.evidence(r)):
                blocks, flags, ans = answer_blocks(r["haystack_sessions"][i])
                for t in ans:
                    roles[t.get("role")] += 1
                    ans_text += " " + (t.get("content") or "")
                for b, f in zip(blocks, flags):
                    v = cache.get(lr.h("distill", "C1", lr.PROMPTS["C1"], b))
                    us = v["units"] if v else []
                    for u in us:
                        cats[u.get("category")] += 1
                        unit_text += " " + (u.get("text") or "")
                    if f:
                        e = len(us) == 0
                        any_empty = e if any_empty is None else (any_empty or e)
                        all_empty = e if all_empty is None else (all_empty and e)
            st["no_marked_turn"] += any_empty is None
            st["some_answer_block_empty"] += bool(any_empty)
            st["all_answer_blocks_empty"] += bool(all_empty)
            if ref:
                kr.append(len(ref & words(ans_text)) / len(ref))
                ku.append(len(ref & words(unit_text)) / len(ref))
            if len(ex) < a.examples:
                ex.append({"qid": q, "type": r["question_type"], "question": r["question"],
                           "reference": str(r["answer"]),
                           "e_dist_answer": next(x["answer"] for x in rows if x["qid"] == q
                                                 and x["reader"] == "R3" and x["arm"] == "E-dist")})
        n = len(qs)
        out[g] = {"n": n, "by_type": dict(by_type), "roles_of_answer_turns": dict(roles),
                  "no_marked_turn": st["no_marked_turn"],
                  "some_answer_block_empty": st["some_answer_block_empty"],
                  "all_answer_blocks_empty": st["all_answer_blocks_empty"],
                  "key_words_in_answer_turns": sum(kr) / len(kr) if kr else None,
                  "key_words_in_units": sum(ku) / len(ku) if ku else None,
                  "n_with_key_words": len(kr),
                  "unit_categories": dict(cats.most_common())}
        if ex:
            out[g]["examples"] = ex
    print(json.dumps(out, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
