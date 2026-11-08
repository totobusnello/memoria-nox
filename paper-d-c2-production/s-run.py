#!/usr/bin/env python3
"""C2 shadow study, step 5 (SHADOW-PREREGISTRATION.md §4 and §6): serve, answer and judge every arm.

  python3 -I s-run.py --repo <clone> --private <dir> --freeze-ref <c> --questions-ref <c> [--yes]
  python3 -I s-run.py --repo <clone> --private <dir> --smoke [--yes]

Before any paid call it checks the order of the public history (tag -> freeze -> questions, each
written once and byte-equal to the private copy), that the running code is the tag's, that the
questions commitment names this freeze and the tag's generator and prompts, and that every frozen
file and the questions file match their hashes. Without --yes it stops there and prints what the
run would call.

Arms (§4), over the same questions:
  A       the question's evidence region: citations plus 1,500 characters each side, inside the block
  C0      every C0 unit production returned for the session's frozen blocks, as recorded
  C2      every C2 unit the shadow returned for the same blocks, as recorded
  C2-cut  the C2 units of the session, with the question's block re-distilled under C2 (Paper 3's
          lme-run.distill) after removing every evidence region of that block's questions
Serving is Paper D's (d-common.serve): importance descending, ties by block then position,
"[<date>] [<category>] <text>", "(vazio)" when there is none; no retrieval and no dedup. Reader R0
(lme-run.answer), judge 1 (lme-run.judge) and judge 2 (lme-run.judge2) on every row. Every call
is cached in <dir>/run/cache.sqlite, so a stopped run resumes without paying twice; the ledger
starts from the writer's spend (§4) and stops the run at US$ 5.

Writes <dir>/run/results.json (private) and <dir>/SHADOW-RESULTS-COMMITMENT.json (hashes and
counts, no accuracy); prints counts, cost and hashes only.
"""
import argparse
import collections
import importlib.util
import json
import pathlib
import sys
from concurrent.futures import ThreadPoolExecutor

HERE = pathlib.Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("scommon", HERE / "s-common.py")
C = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(C)
SG = C.load("sgen_run", HERE / "s-generate.py")
L = SG.L
WORKERS = 8
GEN_FILES = ("s-generate.py", "s-common.py", "d-generate.py", "d-smoke.py")


def checks(a, P):
    got = C.chain(a.repo, P, [("SHADOW-FREEZE", a.freeze_ref), ("SHADOW-QUESTIONS", a.questions_ref)], a.smoke)
    (fb, fc), (qb, qc) = got["SHADOW-FREEZE"], got["SHADOW-QUESTIONS"]
    if a.smoke:
        want = {f: C.sha_file(HERE / f) for f in GEN_FILES}
    else:
        C.same_as_tag(a.repo)
        want = {f: C.DC.tag_file_sha(a.repo, f"{C.D}/{f}") for f in GEN_FILES}
    if qc["freeze_commitment_sha256"] != C.sha_bytes(fb):
        sys.exit("refusing: the questions commitment names another freeze")
    if (qc["script_sha256"], qc["prompts_sha256"]) != (want, C.sha_json(SG.PROMPTS)):
        sys.exit("refusing: the questions were not written by the tag's generator and prompts")
    if qc["seed"] != fc["seed"]:
        sys.exit("refusing: the questions commitment's seed is not the freeze's")
    C.check_manifest(P / "freeze", fc["manifest_sha256"])
    if C.sha_file(P / "questions.jsonl") != qc["questions_sha256"]:
        sys.exit("refusing: questions.jsonl is not the committed one")
    if C.sha_file(P / "validated.jsonl") != qc["validated_sha256"]:
        sys.exit("refusing: validated.jsonl is not the committed one")
    return fb, fc, qb, qc


def cut_block(block, regions):
    """The block with every character inside `regions` ([lo, hi) in the block) removed: Paper D's
    cut_regions on a single turn whose prose starts at the block's first character."""
    pre = "x: "
    out = C.DC.cut_regions([{"role": "x", "content": block}], [(-len(pre), len(block))], regions)
    return out[0]["content"] if out else ""


def plan(recs, qs):
    """What each session needs: its blocks in order, the date it is served under, and for every
    block with questions the cut text C2-cut re-distils."""
    sess = collections.OrderedDict()
    for bid, date, rec in recs:
        s = sess.setdefault(C.r_session(rec), {"blocks": [], "agent": C.r_agent(rec), "date": date})
        s["blocks"].append((bid, rec))
        s["date"] = max(s["date"], date)
    by_block = collections.defaultdict(list)
    for q in qs:
        by_block[q["block"]].append(q)
    text = {bid: C.r_block(rec) for bid, _, rec in recs}
    cuts = {bid: cut_block(text[bid], [(q["ev_lo"], q["ev_hi"]) for q in qq]) for bid, qq in by_block.items()}
    return sess, text, cuts


def main(argv=None, post=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=str(C.ROOT))
    ap.add_argument("--private", required=True)
    ap.add_argument("--freeze-ref")
    ap.add_argument("--questions-ref")
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--yes", action="store_true")
    ap.add_argument("--cap", type=float, default=C.CAP_USD)
    a = ap.parse_args(argv)
    if a.cap > C.CAP_USD:
        sys.exit(f"refusing: the registered spend cap is US$ {C.CAP_USD:g}")
    if not a.smoke and not (a.freeze_ref and a.questions_ref):
        sys.exit("--freeze-ref and --questions-ref are required (or --smoke)")
    if post is not None:
        L.post = post
    P = C.private(a.private)
    fb, fc, qb, qc = checks(a, P)
    recs = C.frozen_records(P / "freeze")
    qs = [json.loads(x) for x in open(P / "questions.jsonl", encoding="utf-8")]
    sess, text, cuts = plan(recs, qs)
    to_distill = sorted(b for b, t in cuts.items() if t.strip())
    n_rows = len(qs) * len(C.ARMS)
    print(f"sessions {len(sess)} · blocks {len(recs)} · questions {len(qs)} ({qc['questions']}) · "
          f"C2-cut distill calls {len(to_distill)} (empty after the cut {len(cuts) - len(to_distill)}) · "
          f"answer rows {n_rows} · judge calls {2 * n_rows}")
    if not a.yes:
        print("estimate only: add --yes to run")
        return 0
    (P / "run").mkdir(exist_ok=True)
    cache, led = L.Cache(str(P / "run" / "cache.sqlite")), L.Ledger(a.cap)
    led.n["writer"] = qc["writer_calls_total"]
    if qc.get("writer_usd") is not None:    # §4: the writer's spend counts against the same cap
        led.usd += qc["writer_usd"]
        if led.usd > a.cap:
            sys.exit(f"CAP REACHED: the writer alone spent US$ {led.usd:.2f} > {a.cap}")
    errors = []

    def safe(fn, *args):
        try:
            return fn(*args)
        except SystemExit:
            raise
        except Exception as e:
            errors.append(f"{fn.__name__}: {type(e).__name__}")
            return None

    with ThreadPoolExecutor(WORKERS) as ex:
        got = list(ex.map(lambda b: safe(L.distill, cache, led, "C2", cuts[b]), to_distill))
    if errors:
        sys.exit(f"{len(errors)} distillation errors (first: {errors[0]}); rerun to resume")
    cut_res = dict(zip(to_distill, got))
    for b in cuts:
        cut_res.setdefault(b, {"units": [], "failed": False, "empty": True, "tin": 0, "tout": 0})

    def units(s, arm, cut_bid=None):
        out = []
        for bid, rec in sess[s]["blocks"]:
            if arm == "C0":
                out.append(C.r_c0_units(rec))
            elif arm == "C2-cut" and bid == cut_bid:
                out.append(cut_res[bid]["units"])
            else:
                out.append(C.r_c2_units(rec))
        return out

    def material(q, arm):
        if arm == "A":
            return text[q["block"]][q["ev_lo"]:q["ev_hi"]]
        return C.serve(units(q["uuid"], arm, q["block"]), sess[q["uuid"]]["date"])

    def row(q, arm):
        ans = L.answer(cache, led, material(q, arm), "PERGUNTA: " + q["question"], reader="R0")
        j1 = L.judge(cache, led, q["ref"], ans["text"], q["question"])
        j2 = L.judge2(cache, led, q["ref"], ans["text"], q["question"])
        return {"qid": q["qid"], "arm": arm, "answer": ans["text"], "finish": ans.get("finish"),
                "tin": ans.get("tin", 0), "tout": ans.get("tout", 0),
                "j1_contem": j1["contem"], "j1_contradiz": j1["contradiz"],
                "j1": (j1["contem"] or 0) > L.THR, "j1_contradiz_bin": (j1["contradiz"] or 0) > L.THR,
                "j2": bool(j2["correta"])}

    tasks = [(q, arm) for q in qs for arm in C.ARMS]
    with ThreadPoolExecutor(WORKERS) as ex:
        rows = list(ex.map(lambda t: safe(row, *t), tasks))
    if errors:
        sys.exit(f"{len(errors)} answer or judge errors (first: {errors[0]}); rerun to resume")
    summary = {}
    for s, v in sess.items():
        summary[s] = {"agent": v["agent"], "date": v["date"], "blocks": len(v["blocks"]),
                      "questions": sum(q["uuid"] == s for q in qs),
                      "units": {"C0": sum(len(C.r_c0_units(r)) for _, r in v["blocks"]),
                                "C2": sum(len(C.r_c2_units(r)) for _, r in v["blocks"])}}
    blocks = {b: {"cut_chars": len(cuts[b]), "cut_units": len(cut_res[b]["units"]),
                  "cut_failed": bool(cut_res[b].get("failed")), "cut_empty": bool(cut_res[b].get("empty")),
                  "cut_tin": cut_res[b].get("tin", 0), "cut_tout": cut_res[b].get("tout", 0)} for b in cuts}
    head = C.git(a.repo, "rev-parse", "HEAD" if a.smoke else f"{C.TAG}^{{commit}}").stdout.strip()
    res = {"meta": {"smoke": bool(a.smoke), "code_commit": head, "seed": fc["seed"],
                    "freeze_commitment_sha256": C.sha_bytes(fb), "questions_sha256": qc["questions_sha256"],
                    "questions_commitment_sha256": C.sha_bytes(qb), "usd": round(led.usd, 4),
                    "calls": led.n, "cap": a.cap, "writer_usd": qc.get("writer_usd")},
           "sessions": summary, "cut_blocks": blocks, "rows": rows}
    body = json.dumps(res, ensure_ascii=False, indent=1)
    C.write_private(P / "run" / "results.json", body)
    com = {"smoke": bool(a.smoke), "code_commit": head,
           "freeze_commitment_sha256": C.sha_bytes(fb), "questions_commitment_sha256": C.sha_bytes(qb),
           "results_sha256": C.sha_bytes(body.encode("utf-8")),
           "rows": dict(collections.Counter(r["arm"] for r in rows)),
           "c2_cut": {"blocks": len(cuts), "distilled": len(to_distill),
                      "failed": sum(v["cut_failed"] for v in blocks.values())},
           "usd": round(led.usd, 4), "writer_usd": qc.get("writer_usd"), "calls": led.n, "cap": a.cap,
           "script_sha256": {f: C.sha_file(HERE / f) for f in ("s-run.py",) + GEN_FILES + ("d-common.py",)},
           "lme_run_sha256": C.sha_file(C.ROOT / "paper3-construction/lme-run.py")}
    C.write_private(P / "SHADOW-RESULTS-COMMITMENT.json", json.dumps(com, indent=1) + "\n")
    C.lock_down(P)
    print(f"rows {len(rows)} · C2-cut distilled {len(to_distill)} · calls {led.n} · US$ {led.usd:.4f}")
    print(f"results.json sha256 {com['results_sha256']}")
    print(f"next: cp {P / 'SHADOW-RESULTS-COMMITMENT.json'} {C.D}/ ; commit; push; then s-human.py make")
    return 0


if __name__ == "__main__":
    sys.exit(main())
