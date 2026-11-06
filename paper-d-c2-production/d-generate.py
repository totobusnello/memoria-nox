#!/usr/bin/env python3
"""Paper D, step 3 (PREREGISTRATION.md §3 and §6): write the questions from the frozen sessions.

  python3 -I d-generate.py --private <dir> --freeze-ref <commit that pushed FREEZE-COMMITMENT.json>
  python3 -I d-generate.py --private <dir> --smoke          (reads <dir>/FREEZE-COMMITMENT.json)

Refuses unless the freeze commitment was pushed after the tag, written once, is byte-equal to
<dir>/FREEZE-COMMITMENT.json, and every frozen file matches its manifest. Then, session by session
in the drawn order, writes questions from each window with the two prompts of d-smoke.py (writer
glm-5.3, temperature 0, every call cached in <dir>/gen-cache.sqlite), validates them, and applies
the extension rule: after the first 80 sessions, while fewer than 232 primary questions exist and
fewer than 120 sessions are in, the next 10 sessions of the order are added. The rule reads only
the count of primary questions.

VALIDATION (fixed with the pre-registration, §3). A fact is dropped, and the reason counted, when:
  malformed            it is not an object with a question and an answer
  answer_too_long      the answer has more than 25 words (the prompt's own limit)
  category_outside     its category is not one the prompt allows for that set
  no_citation          it has no citation
  citation_not_verbatim  a citation is not a byte-exact substring of its window

Writes <dir>/questions.jsonl (private) and <dir>/QUESTIONS-COMMITMENT.json (public: hashes and
counts only). Copy the commitment into this directory, commit and push it before d-run.sh.
"""
import argparse
import collections
import importlib.util
import json
import pathlib
import sys

HERE = pathlib.Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("dcommon", HERE / "d-common.py")
C = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(C)
SM = C.load("dsmoke", HERE / "d-smoke.py")          # PRIMARY, SECONDARY, parse; loads L and G
L, G, S = SM.L, SM.G, SM.S
PROMPTS = {"primary": SM.PRIMARY, "secondary": SM.SECONDARY}
ALLOWED = {"primary": {"decision", "preference", "lesson", "context"},
           "secondary": {"identificador", "passagem"}}
MAX_ANSWER_WORDS = 25


def check_freeze(a, P):
    local = (P / "FREEZE-COMMITMENT.json").read_bytes()
    if not a.smoke:
        got = C.ordered(C.ROOT, [("FREEZE", a.freeze_ref)])["FREEZE"]
        pub = C.git(C.ROOT, "show", f"{got['_commit']}:{C.D}/FREEZE-COMMITMENT.json").stdout.encode()
        if pub != local:
            sys.exit("refusing: the published freeze commitment is not <dir>/FREEZE-COMMITMENT.json")
    fc = json.loads(local)
    if fc["smoke"] is not bool(a.smoke):
        sys.exit(f"refusing: the freeze commitment says smoke={fc['smoke']}")
    F = P / "freeze"
    if C.sha_file(F / "manifest.json") != fc["manifest_sha256"]:
        sys.exit("refusing: the manifest is not the committed one")
    for f, h in json.loads((F / "manifest.json").read_text(encoding="utf-8")).items():
        if C.sha_file(F / f) != h:
            sys.exit(f"refusing: {f} does not match the manifest")
    return fc, C.sha_bytes(local)


def facts(cache, gen, set_name, w):
    prompt = PROMPTS[set_name]
    key = L.h("gen", G.MODEL, prompt, w)
    hit = cache.get(key)
    if hit is None:
        txt, served = G.ask(prompt + "\n\nTRECHO:\n" + w)
        hit = {"text": txt, "served": served}
        cache.put(key, "gen", hit)
        gen["writer_calls"] += 1
    gen["served"][hit.get("served") or "?"] += 1
    return SM.parse(hit["text"]) or []


def session_questions(cache, gen, drops, u, path, date):
    ts = C.turns(path, S)
    full, _ = C.layout(ts)
    out = []
    for off, w in sorted(C.windows(full).items()):
        for set_name in ("primary", "secondary"):
            for f in facts(cache, gen, set_name, w):
                d = drops[set_name]
                if not isinstance(f, dict) or not f.get("pergunta") or not f.get("resposta"):
                    d["malformed"] += 1
                    continue
                if len(str(f["resposta"]).split()) > MAX_ANSWER_WORDS:
                    d["answer_too_long"] += 1
                    continue
                if f.get("categoria") not in ALLOWED[set_name]:
                    d["category_outside"] += 1
                    continue
                cits = [x for x in f.get("citacoes") or [] if isinstance(x, str) and x]
                if not cits:
                    d["no_citation"] += 1
                    continue
                locs = [(w.find(x), w.find(x) + len(x)) for x in cits]
                if any(b < 0 for b, _ in locs):
                    d["citation_not_verbatim"] += 1
                    continue
                lo, hi = min(b for b, _ in locs), max(e for _, e in locs)
                out.append({"uuid": u, "set": set_name, "window": off, "category": f["categoria"],
                            "question": str(f["pergunta"]), "ref": str(f["resposta"]),
                            "citations": cits, "date": date,
                            "ev_lo": off + max(0, lo - C.PAD), "ev_hi": off + min(len(w), hi + C.PAD)})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--private", required=True)
    ap.add_argument("--freeze-ref")
    ap.add_argument("--smoke", action="store_true")
    a = ap.parse_args()
    if not a.smoke and not a.freeze_ref:
        sys.exit("--freeze-ref is required (or --smoke)")
    P = C.private(a.private)
    fc, fc_sha = check_freeze(a, P)
    order = json.loads((P / "freeze" / "frame.json").read_text(encoding="utf-8"))["order"]
    cache = L.Cache(str(P / "gen-cache.sqlite"))
    gen = {"writer_calls": 0, "served": collections.Counter()}
    drops = {s: collections.Counter() for s in PROMPTS}
    rows, used = [], 0
    n_target = min(C.N_SESSIONS, len(order))
    while used < n_target:
        o = order[used]
        rows += session_questions(cache, gen, drops, o["uuid"],
                                  P / "freeze" / "sessions" / f"{o['uuid']}.jsonl", o["last_event"])
        used += 1
        if used == n_target and n_target < min(C.N_MAX, len(order)) and \
                sum(r["set"] == "primary" for r in rows) < C.TARGET_PRIMARY:
            n_target = min(n_target + C.BLOCK, C.N_MAX, len(order))
    for i, r in enumerate(rows):
        r["qid"] = f"q{i:04d}"
    body = "".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows)
    (P / "questions.jsonl").write_text(body, encoding="utf-8")
    counts = {s: dict(collections.Counter(r["category"] for r in rows if r["set"] == s)) for s in PROMPTS}
    out = {"smoke": bool(a.smoke), "freeze_commitment_sha256": fc_sha,
           "questions_sha256": C.sha_bytes(body.encode("utf-8")),
           "prompts_sha256": C.sha_json(PROMPTS), "script_sha256": C.sha_file(HERE / "d-generate.py"),
           "prompts_script_sha256": C.sha_file(HERE / "d-smoke.py"),
           "writer_model": G.MODEL, "writer_served": dict(gen["served"]),
           "writer_calls_this_run": gen["writer_calls"],
           "writer_cache_sha256": C.sha_file(P / "gen-cache.sqlite"),
           "sessions_used": used, "extension_sessions": used - min(C.N_SESSIONS, len(order)),
           "sessions_with_questions": len({r["uuid"] for r in rows}),
           "questions": {s: sum(counts[s].values()) for s in PROMPTS}, "by_category": counts,
           "drops": {s: dict(d) for s, d in drops.items()}}
    (P / "QUESTIONS-COMMITMENT.json").write_text(json.dumps(out, indent=1) + "\n", encoding="utf-8")
    print(f"sessions {used} (extension {out['extension_sessions']}) · questions {out['questions']} · "
          f"drops {out['drops']} · writer calls {gen['writer_calls']}")
    print(f"next: cp {P / 'QUESTIONS-COMMITMENT.json'} {C.D}/ ; commit; push; then d-run.sh")


if __name__ == "__main__":
    main()
