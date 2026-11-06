#!/usr/bin/env python3
"""Paper D, step 4 (PREREGISTRATION.md §4, §5.3 and §6): distil, answer and judge every arm.

Called by d-run.sh from the tree it extracts from the tag; not run by hand.

  python3 -I d-run.py --repo <clone> --private <dir> --freeze-ref <c> --questions-ref <c> [--yes]
  python3 -I d-run.py --repo <clone> --private <dir> --smoke [--yes]

Before any paid call it checks the order of the public history (tag -> freeze -> questions, each
written once), that both published commitments are byte-equal to the private copies, that the
questions commitment names this freeze and the tag's prompts and generator, and that every frozen
file and the questions file match their hashes. Without --yes it stops there and prints what the
run would call.

Arms (§4), all over the same questions:
  A       the question's evidence region (citations +/- 1,500 chars inside the window)
  C0, C2  every unit distilled under that criterion from the session's complete prose
  C2-cut  C2 on the prose with every evidence region of the session's questions removed
  P       the units production stored for the session (freeze-day snapshot)
  V       C0 on the visible prefix (turns up to processed_at); a session whose log row records
          fewer than 3 messages gets no unit: production skipped it without calling the model
          (session-distill.ts). The recount of those messages from the transcript is reported
  C0-cf, C2-cf  §5.3: the session rewritten with the reference's digit run altered; checked by
          string match, not judged
Reader R0 and both judges on every row of A, C0, C2, C2-cut, P and V. Every call is cached in
<dir>/run/cache.sqlite under the hash of its input, so a stopped run resumes without paying twice.

Writes <dir>/run/results.json (private) and prints counts, cost and its sha256, no accuracy.
"""
import argparse
import collections
import importlib.util
import json
import pathlib
import random
import sys
from concurrent.futures import ThreadPoolExecutor

HERE = pathlib.Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("dcommon", HERE / "d-common.py")
C = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(C)
GEN = C.load("dgen", HERE / "d-generate.py")
L, S = GEN.L, GEN.S
ARMS = ("A", "C0", "C2", "C2-cut", "P", "V")
CF_MAX, WORKERS = 30, 8


def checks(a, P):
    fc_local = (P / "FREEZE-COMMITMENT.json").read_bytes()
    qc_local = (P / "QUESTIONS-COMMITMENT.json").read_bytes()
    if not a.smoke:
        got = C.ordered(a.repo, [("FREEZE", a.freeze_ref), ("QUESTIONS", a.questions_ref)])
        for name, local in (("FREEZE", fc_local), ("QUESTIONS", qc_local)):
            pub = C.git(a.repo, "show", f"{got[name]['_commit']}:{C.D}/{name}-COMMITMENT.json").stdout
            if pub.encode() != local:
                sys.exit(f"refusing: the published {name} commitment is not the private copy")
        want_gen = C.tag_file_sha(a.repo, f"{C.D}/d-generate.py")
        want_smoke = C.tag_file_sha(a.repo, f"{C.D}/d-smoke.py")
    else:
        want_gen, want_smoke = C.sha_file(HERE / "d-generate.py"), C.sha_file(HERE / "d-smoke.py")
    fc, qc = json.loads(fc_local), json.loads(qc_local)
    for name, c in (("freeze", fc), ("questions", qc)):
        if c["smoke"] is not bool(a.smoke):
            sys.exit(f"refusing: the {name} commitment says smoke={c['smoke']}")
    if qc["freeze_commitment_sha256"] != C.sha_bytes(fc_local):
        sys.exit("refusing: the questions commitment names another freeze")
    if (qc["script_sha256"], qc["prompts_script_sha256"], qc["prompts_sha256"]) != \
            (want_gen, want_smoke, C.sha_json(GEN.PROMPTS)):
        sys.exit("refusing: the questions were not written by the tag's generator and prompts")
    F = P / "freeze"
    if C.sha_file(F / "manifest.json") != fc["manifest_sha256"]:
        sys.exit("refusing: the manifest is not the committed one")
    for f, h in json.loads((F / "manifest.json").read_text(encoding="utf-8")).items():
        if C.sha_file(F / f) != h:
            sys.exit(f"refusing: {f} does not match the manifest")
    if C.sha_file(P / "questions.jsonl") != qc["questions_sha256"]:
        sys.exit("refusing: questions.jsonl is not the committed one")
    return fc, qc


def blocks_for(sess):
    return L.session_blocks(sess)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--private", required=True)
    ap.add_argument("--freeze-ref")
    ap.add_argument("--questions-ref")
    ap.add_argument("--smoke", action="store_true")
    ap.add_argument("--yes", action="store_true")
    ap.add_argument("--cap", type=float, default=10.0)
    a = ap.parse_args()
    if a.cap > 10.0:
        sys.exit("refusing: the registered spend cap is US$ 10")
    if not a.smoke and not (a.freeze_ref and a.questions_ref):
        sys.exit("--freeze-ref and --questions-ref are required (or --smoke)")
    P = C.private(a.private)
    fc, qc = checks(a, P)
    F = P / "freeze"
    qs = [json.loads(l) for l in open(P / "questions.jsonl", encoding="utf-8")]
    prod = json.loads((F / "production.json").read_text(encoding="utf-8"))
    by_s = collections.defaultdict(list)
    for q in qs:
        by_s[q["uuid"]].append(q)

    # ---------------------------------------------------------------- what each session needs
    sess = {}
    for u, qq in by_s.items():
        ts = C.turns(F / "sessions" / f"{u}.jsonl", S)
        full, spans = C.layout(ts)
        vis = C.visible_prefix(ts, prod[u]["processed_at"])
        nmsg = C.visible_count(C.prod_messages(F / "sessions" / f"{u}.jsonl"), prod[u]["processed_at"])
        cut = C.cut_regions(ts, spans, [(q["ev_lo"], q["ev_hi"]) for q in qq])
        sess[u] = {"ts": ts, "full": full, "date": qq[0]["date"],
                   "need": {"C0": ("C0", blocks_for(ts)), "C2": ("C2", blocks_for(ts)),
                            "C2-cut": ("C2", blocks_for(cut)),
                            "V": ("C0", blocks_for(vis) if prod[u]["message_count"] >= 3 else [])},
                   "visible_turns": len(vis), "turns": len(ts), "visible_messages": nmsg}
    elig = sorted((q for q in qs if q["set"] == "primary" and C.cf_run(q["ref"], q["citations"])),
                  key=lambda q: q["qid"])
    cf = random.Random(C.SEED).sample(elig, min(CF_MAX, len(elig)))
    cf.sort(key=lambda q: q["qid"])
    for q in cf:
        run = C.cf_run(q["ref"], q["citations"])
        rw = C.cf_rewrite(sess[q["uuid"]]["ts"], run)
        q["_cf"] = {"run": run, "altered": C.cf_alter(run),
                    "need": {"C0-cf": ("C0", blocks_for(rw)), "C2-cf": ("C2", blocks_for(rw))}}

    jobs = {}
    for s in sess.values():
        for crit, bl in s["need"].values():
            for b in bl:
                jobs[(crit, b)] = None
    for q in cf:
        for crit, bl in q["_cf"]["need"].values():
            for b in bl:
                jobs[(crit, b)] = None
    n_rows = len(qs) * len(ARMS)
    print(f"sessions {len(sess)} · questions {len(qs)} ({qc['questions']}) · "
          f"distill blocks {len(jobs)} · answer rows {n_rows} + counterfactual {2 * len(cf)} "
          f"(eligible {len(elig)}) · judge calls {2 * n_rows}")
    if not a.yes:
        print("estimate only: add --yes to run")
        return 0
    (P / "run").mkdir(exist_ok=True)
    cache, led = L.Cache(str(P / "run" / "cache.sqlite")), L.Ledger(a.cap)
    errors = []

    def safe(fn, *args):
        try:
            return fn(*args)
        except SystemExit:
            raise
        except Exception as e:
            errors.append(f"{fn.__name__}: {str(e)[:160]}")
            return None

    with ThreadPoolExecutor(WORKERS) as ex:
        keys = list(jobs)
        for k, v in zip(keys, ex.map(lambda k: safe(L.distill, cache, led, k[0], k[1]), keys)):
            jobs[k] = v
    if errors:
        sys.exit(f"{len(errors)} distillation errors (first: {errors[0]}); rerun to resume")

    def units(crit, bl):
        return [jobs[(crit, b)]["units"] for b in bl]

    def failed(crit, bl):
        return sum(bool(jobs[(crit, b)].get("failed")) for b in bl)

    material, summary = {}, {}
    for u, s in sess.items():
        m = {arm: C.serve(units(*s["need"][arm]), s["date"]) for arm in ("C0", "C2", "C2-cut", "V")}
        pu = sorted(prod[u]["units"], key=lambda x: x["id"])
        m["P"] = C.serve([pu], s["date"])
        material[u] = m
        summary[u] = {"prose_chars": len(s["full"]), "turns": s["turns"],
                      "visible_turns": s["visible_turns"], "questions": len(by_s[u]),
                      "units": {arm: sum(len(x) for x in units(*s["need"][arm]))
                                for arm in ("C0", "C2", "C2-cut", "V")} | {"P": len(pu)},
                      "blocks": {arm: len(s["need"][arm][1]) for arm in ("C0", "C2", "C2-cut", "V")},
                      "failed_blocks": {arm: failed(*s["need"][arm]) for arm in ("C0", "C2", "C2-cut", "V")},
                      "visible_messages": s["visible_messages"],
                      "message_count_log": prod[u]["message_count"],
                      "chunks_extracted": prod[u]["chunks_extracted"]}

    def row(q, arm):
        mat = sess[q["uuid"]]["full"][q["ev_lo"]:q["ev_hi"]] if arm == "A" else material[q["uuid"]][arm]
        ans = L.answer(cache, led, mat, "PERGUNTA: " + q["question"], reader="R0")
        j1 = L.judge(cache, led, q["ref"], ans["text"], q["question"])
        j2 = L.judge2(cache, led, q["ref"], ans["text"], q["question"])
        return {"qid": q["qid"], "arm": arm, "answer": ans["text"], "finish": ans.get("finish"),
                "j1_contem": j1["contem"], "j1_contradiz": j1["contradiz"],
                "j1": (j1["contem"] or 0) > L.THR, "j1_contradiz_bin": (j1["contradiz"] or 0) > L.THR,
                "j2": bool(j2["correta"])}

    def cf_row(q, arm):
        bl = q["_cf"]["need"][arm]
        mat = C.serve(units(*bl), sess[q["uuid"]]["date"])
        ans = L.answer(cache, led, mat, "PERGUNTA: " + q["question"], reader="R0")["text"]
        return {"qid": q["qid"], "arm": arm, "run": q["_cf"]["run"], "altered": q["_cf"]["altered"],
                "answer": ans, "has_original": C.has_token(ans, q["_cf"]["run"]),
                "has_altered": C.has_token(ans, q["_cf"]["altered"]),
                "units": sum(len(x) for x in units(*bl)), "failed_blocks": failed(*bl)}

    tasks = [(row, q, arm) for q in qs for arm in ARMS] + \
            [(cf_row, q, arm) for q in cf for arm in ("C0-cf", "C2-cf")]
    with ThreadPoolExecutor(WORKERS) as ex:
        out = list(ex.map(lambda t: safe(t[0], t[1], t[2]), tasks))
    if errors:
        sys.exit(f"{len(errors)} answer or judge errors (first: {errors[0]}); rerun to resume")
    rows = [r for (fn, _, _), r in zip(tasks, out) if fn is row]
    cfs = [r for (fn, _, _), r in zip(tasks, out) if fn is cf_row]
    head = C.git(a.repo, "rev-parse", "HEAD" if a.smoke else f"{C.TAG}^{{commit}}").stdout.strip()
    res = {"meta": {"smoke": bool(a.smoke), "code_commit": head,
                    "freeze_commitment_sha256": qc["freeze_commitment_sha256"],
                    "questions_sha256": qc["questions_sha256"], "usd": round(led.usd, 4),
                    "calls": led.n, "cf_eligible": len(elig), "cap": a.cap},
           "sessions": summary, "rows": rows, "counterfactual": cfs}
    body = json.dumps(res, ensure_ascii=False, indent=1)
    (P / "run" / "results.json").write_text(body, encoding="utf-8")
    print(f"rows {len(rows)} · counterfactual rows {len(cfs)} · calls {led.n} · US$ {led.usd:.4f}")
    print(f"results.json sha256 {C.sha_bytes(body.encode('utf-8'))}")
    print("next: d-human.py make; grade blind; d-human.py commit; push HUMAN-COMMITMENT.json; d-read.sh")
    return 0


if __name__ == "__main__":
    sys.exit(main())
