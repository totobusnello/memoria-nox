#!/usr/bin/env python3
"""C2 shadow study, step 4 (SHADOW-PREREGISTRATION.md §3 and §6): write the questions from the frozen
blocks.

  python3 -I s-generate.py --private <dir> --repo <clone> --freeze-ref <commit of SHADOW-FREEZE>
  python3 -I s-generate.py --private <dir> --smoke

Refuses unless the freeze commitment was pushed after the tag, written once, and is byte-equal to
<dir>/SHADOW-FREEZE-COMMITMENT.json, the running code is the tag's, and every frozen file matches
the committed manifest. Then, block by block (by date, then line), sends the block to the writer
(glm-5.3, temperature 0, Paper A's caller as in Paper D) under Paper D's two prompts, each asked
for up to 2 facts per block (§3), every call cached in <dir>/gen-cache.sqlite; validates every
fact with Paper D's rules; and draws 400 per set when a set has more (seed of §3 for the primary
set, seed + 1 for the secondary). The two sets are never pooled.

VALIDATION (Paper D's, unchanged; d-generate.py). A fact is dropped, and the reason counted, when:
  malformed              it is not an object with a question and an answer
  answer_too_long        the answer has more than 25 words
  category_outside       its category is not one the prompt allows for that set
  no_citation            it has no citation
  citation_not_verbatim  a citation is not a byte-exact substring of the block

Writes <dir>/validated.jsonl (every valid question), <dir>/questions.jsonl (the drawn sets) and
<dir>/SHADOW-QUESTIONS-COMMITMENT.json (public: hashes and counts only). Copy the commitment into
this directory, commit and push it before s-run.py.
"""
import argparse
import collections
import importlib.util
import json
import pathlib
import random
import sys

HERE = pathlib.Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("scommon", HERE / "s-common.py")
C = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(C)
GEN = C.load("dgen_shadow", HERE / "d-generate.py")    # Paper D's generator: prompts, rules, callers
SM, L, G = GEN.SM, GEN.L, GEN.G
MAX_FACTS = 2                                           # §3: up to 2 facts per block, each set
PROMPTS = {"primary": SM.PRIMARY.replace("Extraia até 4 fatos", f"Extraia até {MAX_FACTS} fatos"),
           "secondary": SM.SECONDARY.replace("Extraia até 3 fatos", f"Extraia até {MAX_FACTS} fatos")}
assert PROMPTS["primary"] != SM.PRIMARY and PROMPTS["secondary"] != SM.SECONDARY
ALLOWED, MAX_ANSWER_WORDS = GEN.ALLOWED, GEN.MAX_ANSWER_WORDS


def check_freeze(a, P):
    got = C.chain(a.repo, P, [("SHADOW-FREEZE", a.freeze_ref)], a.smoke)
    fb, fc = got["SHADOW-FREEZE"]
    if not a.smoke:
        C.same_as_tag(a.repo)
        if fc["seed"] != C.tag_seed(a.repo):
            sys.exit("refusing: the freeze commitment's seed is not the tag commit's (§3)")
    C.check_manifest(P / "freeze", fc["manifest_sha256"])
    return fc, C.sha_bytes(fb)


def facts(cache, gen, set_name, block, ask):
    """The writer's facts for one block under one prompt; cached, so a block is never sent twice
    under the same prompt."""
    prompt = PROMPTS[set_name]
    key = L.h("gen", G.MODEL, prompt, block)
    hit = cache.get(key)
    if hit is None:
        txt, served = ask(prompt + "\n\nTRECHO:\n" + block)
        hit = {"text": txt, "served": served}
        cache.put(key, "gen", hit)
        gen["writer_calls"] += 1
    gen["served"][hit.get("served") or "?"] += 1
    return SM.parse(hit["text"]) or []


def validate(f, set_name, block, d):
    """Paper D's validation (d-generate.session_questions) on a block instead of a window. Returns
    (category, question, answer, citations, lo, hi) or None, counting the drop in d."""
    if not isinstance(f, dict) or not f.get("pergunta") or not f.get("resposta"):
        d["malformed"] += 1
        return None
    if len(str(f["resposta"]).split()) > MAX_ANSWER_WORDS:
        d["answer_too_long"] += 1
        return None
    if f.get("categoria") not in ALLOWED[set_name]:
        d["category_outside"] += 1
        return None
    cits = [x for x in f.get("citacoes") or [] if isinstance(x, str) and x]
    if not cits:
        d["no_citation"] += 1
        return None
    locs = [(block.find(x), block.find(x) + len(x)) for x in cits]
    if any(b < 0 for b, _ in locs):
        d["citation_not_verbatim"] += 1
        return None
    lo, hi = min(b for b, _ in locs), max(e for _, e in locs)
    return f["categoria"], str(f["pergunta"]), str(f["resposta"]), cits, lo, hi


def block_questions(cache, gen, drops, over, bid, date, rec, ask):
    block = C.r_block(rec)
    out = []
    for set_name in C.SETS:
        fs = facts(cache, gen, set_name, block, ask)
        if isinstance(fs, list) and len(fs) > MAX_FACTS:
            over[set_name] += 1            # counted, not cut: the validation rules are D's, unchanged
        for f in fs:                       # iterated as d-generate.py does
            v = validate(f, set_name, block, drops[set_name])
            if v is None:
                continue
            cat, q, ref, cits, lo, hi = v
            out.append({"block": bid, "uuid": C.r_session(rec), "agent": C.r_agent(rec), "date": date,
                        "set": set_name, "category": cat, "question": q, "ref": ref, "citations": cits,
                        "ev_lo": max(0, lo - C.PAD), "ev_hi": min(len(block), hi + C.PAD)})
    return out


def draw(rows, seed, n):
    """§3: if a set has more than n questions, n are drawn uniformly with the seed; else all."""
    if len(rows) <= n:
        return list(rows)
    pick = random.Random(seed).sample(sorted(rows, key=lambda r: r["qid"]), n)
    return sorted(pick, key=lambda r: r["qid"])


def main(argv=None, ask=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--private", required=True)
    ap.add_argument("--repo", default=str(C.ROOT))
    ap.add_argument("--freeze-ref")
    ap.add_argument("--smoke", action="store_true")
    a = ap.parse_args(argv)
    if not a.smoke and not a.freeze_ref:
        sys.exit("--freeze-ref is required (or --smoke)")
    ask = ask or G.ask
    P = C.private(a.private)
    fc, fc_sha = check_freeze(a, P)
    seed = fc["seed"]
    recs = C.frozen_records(P / "freeze")
    cache = L.Cache(str(P / "gen-cache.sqlite"))
    gen = {"writer_calls": 0, "served": collections.Counter()}
    drops = {s: collections.Counter() for s in C.SETS}
    over = collections.Counter()
    rows = []
    for bid, date, rec in recs:
        rows += block_questions(cache, gen, drops, over, bid, date, rec, ask)
    for i, r in enumerate(rows):
        r["qid"] = f"q{i:05d}"
    valid = {s: [r for r in rows if r["set"] == s] for s in C.SETS}
    drawn = {"primary": draw(valid["primary"], seed, C.N_DRAW),
             "secondary": draw(valid["secondary"], seed + 1, C.N_DRAW)}
    final = sorted(drawn["primary"] + drawn["secondary"], key=lambda r: r["qid"])
    vbody = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)
    qbody = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in final)
    C.write_private(P / "validated.jsonl", vbody)
    C.write_private(P / "questions.jsonl", qbody)
    by_cat = {s: dict(collections.Counter(r["category"] for r in drawn[s])) for s in C.SETS}
    out = {"smoke": bool(a.smoke), "freeze_commitment_sha256": fc_sha, "seed": seed,
           "secondary_seed": seed + 1, "draw_size": C.N_DRAW, "max_facts_per_block": MAX_FACTS,
           "validated_sha256": C.sha_bytes(vbody.encode("utf-8")),
           "questions_sha256": C.sha_bytes(qbody.encode("utf-8")),
           "prompts_sha256": C.sha_json(PROMPTS),
           "script_sha256": {f: C.sha_file(HERE / f) for f in
                             ("s-generate.py", "s-common.py", "d-generate.py", "d-smoke.py")},
           "writer_model": G.MODEL, "writer_served": dict(gen["served"]),
           "writer_calls_this_run": gen["writer_calls"],
           "writer_calls_total": len(recs) * len(C.SETS),
           "writer_usd": None if C.WRITER_USD_PER_CALL is None
           else round(len(recs) * len(C.SETS) * C.WRITER_USD_PER_CALL, 4),
           "writer_cache_sha256": C.sha_file(P / "gen-cache.sqlite"),
           "blocks": len(recs), "sessions": len({C.r_session(r) for _, _, r in recs}),
           "blocks_with_questions": {s: len({r["block"] for r in valid[s]}) for s in C.SETS},
           "validated": {s: len(valid[s]) for s in C.SETS},
           "questions": {s: len(drawn[s]) for s in C.SETS},
           "sessions_with_questions": {s: len({r["uuid"] for r in drawn[s]}) for s in C.SETS},
           "by_category": by_cat, "drops": {s: dict(d) for s, d in drops.items()},
           "writer_over_max_facts": {s: over[s] for s in C.SETS}}
    C.write_private(P / "SHADOW-QUESTIONS-COMMITMENT.json", json.dumps(out, indent=1) + "\n")
    C.lock_down(P)
    print(f"blocks {len(recs)} · validated {out['validated']} · drawn {out['questions']} · "
          f"drops {out['drops']} · writer calls {gen['writer_calls']}")
    print(f"next: cp {P / 'SHADOW-QUESTIONS-COMMITMENT.json'} {C.D}/ ; commit; push; then s-run.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
