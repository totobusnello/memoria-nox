#!/usr/bin/env python3
"""Paper B2 (PREREGISTRATION.md): the repair pass, the judges on the rewrites, the blind sheet and
the reading, one subcommand per committed step.

  python3 -I b2.py repair --private <P2> --b-private <PB> --b-freeze-ref <c>
  python3 -I b2.py judge  --private <P2> --b-private <PB> --b-freeze-ref <c> --refs <repair>
  python3 -I b2.py sheet  --private <P2> --b-private <PB> --b-freeze-ref <c> --refs <repair>,<judges>
  python3 -I b2.py grades --private <P2> --b-private <PB> --b-freeze-ref <c> --refs <r>,<j>,<sheet>
  python3 -I b2.py read   --private <P2> --b-private <PB> --b-refs <f>,<j>,<s>,<h> --refs <r>,<j>,<s>,<h>

<PB> is Paper B's private directory (freeze.json, judges.json, human-sheet.csv); <P2> is B2's.
Every step refuses unless the earlier commitments are on the public main branch, in order, after
the tag, and byte-equal to the private files. Only counts, rates, intervals and hashes are written
into the repository.
"""
import argparse
import collections
import csv
import datetime
import importlib.util
import json
import pathlib
import random
import sys
from concurrent.futures import ThreadPoolExecutor

HERE = pathlib.Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("b2common", HERE / "b2-common.py")
C = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(C)
B = C.B
BDIR = C.ROOT / "paper-b-kg"
BH = B.load("bhuman", BDIR / "b-human.py")
BR = B.load("bread", BDIR / "b-read.py")

N_RANDOM = 30                 # §4: random agreed rewrites on the sheet
MISMATCH_KEEP_MAX = 0.10      # §5: positive control
N_BOOT = 10_000               # §5
SCRIPTS = ("b2-common.py", "b2.py")
GRADING = BH.GRADING.replace("Paper B: como graduar", "Paper B2: como graduar").replace(
    "Não abra freeze.json, judges.json nem o cache",
    "Não abra repairs.json, judges.json nem os caches")


def scripts():
    return {p: B.sha_file(HERE / p) for p in SCRIPTS}


# ------------------------------------------------------------------ inputs
def b_freeze(pb, ref, repo=C.ROOT):
    com = B.ordered(repo, [("FREEZE", ref)])
    B.same_private(com["FREEZE"], "freeze_json_sha256", pb / "freeze.json")
    return com["FREEZE"], json.loads((pb / "freeze.json").read_text(encoding="utf-8"))


def b_labels(pb, refs, repo=C.ROOT):
    """Paper B's final labels and controls, recomputed under b-read.py's own checks."""
    f, j, s, h = refs
    com = B.ordered(repo, [("FREEZE", f), ("JUDGES", j), ("SHEET", s), ("HUMAN", h)])
    B.same_private(com["FREEZE"], "freeze_json_sha256", pb / "freeze.json")
    B.same_private(com["JUDGES"], "judges_json_sha256", pb / "judges.json")
    B.same_private(com["HUMAN"], "graded_sheet_sha256", pb / "human-sheet.csv")
    fz = json.loads((pb / "freeze.json").read_text(encoding="utf-8"))
    res = json.loads((pb / "judges.json").read_text(encoding="utf-8"))
    sel = BH.select(fz, res, fz["seed"])
    if B.sha_json(sel) != com["SHEET"]["selection_sha256"]:
        raise SystemExit("refusing: Paper B's recomputed selection is not the committed one")
    graded = BH.read_sheet(pb / "human-sheet.csv", fz, sel)
    if B.sha_json(graded) != com["HUMAN"]["grades_sha256"]:
        raise SystemExit("refusing: Paper B's grades are not the committed ones")
    human = {i: (o, g) for i, o, g in graded}
    ctl = BR.controls(fz, res, human, fz["seed"])
    return fz, BR.final_labels(fz, res, human, ctl), ctl, {n: com[n]["_commit"] for n in B.COMMITS}


def load_step(p2, refs, files, repo=C.ROOT):
    """B2's commitments for the given refs, each private file checked against its hash."""
    com = C.ordered(repo, list(zip(C.COMMITS, refs)))
    for name, key, fn in files:
        if name in com:
            B.same_private(com[name], key, p2 / fn)
    return com


def jread(p):
    return json.loads(p.read_text(encoding="utf-8"))


# ------------------------------------------------------------------ step 1: repair
def repair_jobs(fz):
    by_id = {r["relation_id"]: r for r in fz["sample"]}
    out = [("primary", r["relation_id"], r, r["chunk_text"]) for r in fz["sample"]]
    out += [("mismatch", m["relation_id"], by_id[m["relation_id"]], m["chunk_text"])
            for m in fz["mismatch"]]
    return out


def run_repair(fz, cache, led, caller=C.call_claude, workers=4):
    res, errors = {"primary": {}, "mismatch": {}}, []

    def one(job):
        kind, rid, item, text = job
        try:
            return kind, rid, C.repair_one(cache, led, item, text, caller)
        except SystemExit:
            raise
        except Exception as e:
            errors.append(f"{kind} {rid}: {str(e)[:160]}")
            return kind, rid, None

    with ThreadPoolExecutor(max_workers=workers) as ex:
        for kind, rid, v in ex.map(one, repair_jobs(fz)):
            if v is not None:
                res[kind][str(rid)] = v
    return res, errors


def repair(a, caller=C.call_claude, repo=C.ROOT):
    p2, pb = B.private(a.private), pathlib.Path(a.b_private)
    if (p2 / "repairs.json").exists():
        sys.exit("refusing: repairs.json exists; the pass runs once")
    t = C.tag_commit(repo)
    fzc, fz = b_freeze(pb, a.b_freeze_ref, repo)
    cache, led = B.Cache(p2 / "repair-cache.sqlite"), B.Ledger(cap=C.CAP_USD)
    res, errors = run_repair(fz, cache, led, caller)
    print(f"calls {led.calls} · cached {led.cached} · US$ {led.usd:.4f} · errors {len(errors)}")
    if errors:
        sys.exit(f"{len(errors)} calls failed (first: {errors[0]}); rerun to resume from the cache")
    body = json.dumps(res, ensure_ascii=False, indent=1, sort_keys=True)
    B.write_private(p2 / "repairs.json", body)
    allv = [v for k in res.values() for v in k.values()]
    B.write_public(HERE / "REPAIR-COMMITMENT.json", {
        "step": "REPAIR", "tag_commit": t, "seed": B.seed_of(t),
        "b_freeze_commit": fzc["_commit"], "b_freeze_json_sha256": fzc["freeze_json_sha256"],
        "repairer": {"model": C.REPAIRER["model"], "effort": C.REPAIRER["effort"], "route": "claude -p",
                     "served": sorted({m for v in allv for m in v["served"]})},
        "answers": {k: len(v) for k, v in res.items()},
        "calls_this_run": led.calls, "cached_this_run": led.cached,
        "usd_this_run": round(led.usd, 4), "cap_usd": led.cap,
        "usd_all_answers": round(sum(v["usd"] for v in allv), 4),
        "tokens_all_answers": {"in": sum(v["tin"] for v in allv), "out": sum(v["tout"] for v in allv),
                               "thinking": sum(v["thinking"] for v in allv)},
        "repairs_json_sha256": B.sha_bytes(body.encode("utf-8")), "script_sha256": scripts()})
    print("next: commit REPAIR-COMMITMENT.json alone, merge, then b2.py judge")


# ------------------------------------------------------------------ step 2: judges on rewrites
def rewrites(fz, rep):
    """[(relation_id, new item, chunk)] for every rewrite of a sampled relation."""
    out = []
    for r in fz["sample"]:
        v = rep["primary"][str(r["relation_id"])]
        if v["action"] == "rewrite" and v.get("new"):
            out.append((r["relation_id"], dict(v["new"]), r["chunk_text"]))
    return out


def run_judges(rw, cache, led, callers=None, workers=6):
    res, errors = {}, []
    for j in (B.JUDGE1, B.JUDGE2):
        res[j["name"]] = {}

        def one(job, j=j):
            rid, item, text = job
            try:
                return rid, B.judge_one(j, cache, led, item, text, (callers or {}).get(j["name"]))
            except SystemExit:
                raise
            except Exception as e:
                errors.append(f"{j['name']} {rid}: {str(e)[:120]}")
                return rid, None

        with ThreadPoolExecutor(max_workers=workers) as ex:
            for rid, v in ex.map(one, rw):
                if v is not None:
                    res[j["name"]][str(rid)] = v
    return res, errors


def judge(a, callers=None, repo=C.ROOT):
    p2, pb = B.private(a.private), pathlib.Path(a.b_private)
    if (p2 / "judges.json").exists():
        sys.exit("refusing: judges.json exists; the judges run once")
    if callers is None:
        for j in (B.JUDGE1, B.JUDGE2):
            B.ready(j)
    com = load_step(p2, a.refs, [("REPAIR", "repairs_json_sha256", "repairs.json")], repo)
    _, fz = b_freeze(pb, a.b_freeze_ref, repo)
    rw = rewrites(fz, jread(p2 / "repairs.json"))
    cap = round(C.CAP_USD - com["REPAIR"]["usd_all_answers"], 4)
    cache, led = B.Cache(p2 / "judge-cache.sqlite"), B.Ledger(cap=cap)
    res, errors = run_judges(rw, cache, led, callers)
    print(f"rewrites {len(rw)} · calls {led.calls} · cached {led.cached} · US$ {led.usd:.4f}")
    if errors:
        sys.exit(f"{len(errors)} calls failed (first: {errors[0]}); rerun to resume from the cache")
    body = json.dumps(res, ensure_ascii=False, indent=1, sort_keys=True)
    B.write_private(p2 / "judges.json", body)
    allv = [(j, v) for j in (B.JUDGE1, B.JUDGE2) for v in res[j["name"]].values()]
    B.write_public(HERE / "JUDGES-COMMITMENT.json", {
        "step": "JUDGES", "repair_commit": com["REPAIR"]["_commit"],
        "judges": {j["name"]: {"model": j["model"],
                               "served": sorted({v["served"] or "" for v in res[j["name"]].values()})}
                   for j in (B.JUDGE1, B.JUDGE2)},
        "verdicts": {n: len(v) for n, v in res.items()},
        "calls_this_run": led.calls, "cached_this_run": led.cached,
        "usd_this_run": round(led.usd, 4), "cap_usd": cap,
        "usd_all_verdicts": round(sum(v["tin"] * j["usd_in"] + v["tout"] * j["usd_out"]
                                      for j, v in allv), 4),
        "judges_json_sha256": B.sha_bytes(body.encode("utf-8")), "script_sha256": scripts()})
    print("next: commit JUDGES-COMMITMENT.json alone, merge, then b2.py sheet")


# ------------------------------------------------------------------ step 3: the blind sheet
def select(rw, res, seed, n_random=N_RANDOM):
    """[(relation_id, origin)] in sheet order: every rewrite the judges disagree on, and n_random
    of the rest drawn with seed + 1; shuffled with seed + 2 (§4)."""
    j1, j2 = res["judge1"], res["judge2"]
    ids = sorted(rid for rid, _, _ in rw)
    origin = {i: "disagree" for i in ids if j1[str(i)]["verified"] != j2[str(i)]["verified"]}
    rest = [i for i in ids if i not in origin]
    for i in random.Random(seed + 1).sample(rest, min(n_random, len(rest))):
        origin[i] = "random"
    pick = sorted(origin)
    random.Random(seed + 2).shuffle(pick)
    return [(i, origin[i]) for i in pick]


def _sheet_inputs(a, repo, upto):
    p2, pb = B.private(a.private), pathlib.Path(a.b_private)
    com = load_step(p2, a.refs[:upto], [("REPAIR", "repairs_json_sha256", "repairs.json"),
                                        ("JUDGES", "judges_json_sha256", "judges.json")], repo)
    _, fz = b_freeze(pb, a.b_freeze_ref, repo)
    rw = rewrites(fz, jread(p2 / "repairs.json"))
    res = jread(p2 / "judges.json")
    sel = select(rw, res, com["REPAIR"]["seed"])
    return p2, com, rw, res, sel


def write_sheet(path, rw, sel):
    by_id = {rid: (item, text) for rid, item, text in rw}
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh)
        w.writerow(BH.COLS)
        for k, (i, _) in enumerate(sel, 1):
            item, text = by_id[i]
            w.writerow([k, BH.triple(item), text[:B.CHUNK_CHARS], ""])


def read_sheet(path, rw, sel):
    """[(relation_id, origin, grade)], refusing anything `sheet` did not write."""
    text = open(path, encoding="utf-8-sig", newline="").read()
    first = text.split("\n", 1)[0]
    delim = ";" if first.count(";") > first.count(",") else ","
    got = list(csv.DictReader(text.splitlines(keepends=True), delimiter=delim))
    if not got or {"item", "tripla", "trecho"} - set(got[0]) or not any(
            c.startswith("sustenta") for c in got[0]):
        raise SystemExit("refusing: the sheet does not have the columns sheet wrote")
    gcol = next(c for c in got[0] if c.startswith("sustenta"))
    if sorted(int(r["item"]) for r in got) != list(range(1, len(sel) + 1)):
        raise SystemExit("refusing: the sheet's items are not the registered selection")
    by_id = {rid: (item, t) for rid, item, t in rw}
    out = []
    for r in got:
        i, origin = sel[int(r["item"]) - 1]
        item, t = by_id[i]
        if (BH.ws(r["tripla"]), BH.ws(r["trecho"])) != (BH.ws(BH.triple(item)), BH.ws(t[:B.CHUNK_CHARS])):
            raise SystemExit(f"refusing: item {r['item']}: the texts are not what sheet wrote")
        v = (r[gcol] or "").strip().lower()
        if v not in ("s", "n"):
            raise SystemExit(f"refusing: item {r['item']} is graded {v!r}, expected s or n")
        out.append((i, origin, int(v == "s")))
    return out


def counts(sel):
    return dict(collections.Counter(o for _, o in sel))


def sheet(a, repo=C.ROOT):
    p2, com, rw, res, sel = _sheet_inputs(a, repo, 2)
    out = p2 / "human-sheet.csv"
    if out.exists():
        sys.exit(f"refusing: {out} exists; the sheet is made once")
    write_sheet(out, rw, sel)
    out.chmod(0o600)
    B.write_private(p2 / "GRADING.txt", GRADING)
    B.write_public(HERE / "SHEET-COMMITMENT.json", {
        "step": "SHEET", "judges_commit": com["JUDGES"]["_commit"], "rewrites": len(rw),
        "rows": len(sel), "by_origin": counts(sel), "sheet_sha256": B.sha_file(out),
        "selection_sha256": B.sha_json(sel), "script_sha256": scripts()})
    print(f"{len(sel)} rows written to {out} {counts(sel)}; commit SHEET-COMMITMENT.json, then grade")


def grades(a, repo=C.ROOT):
    p2, com, rw, res, sel = _sheet_inputs(a, repo, 3)
    if B.sha_json(sel) != com["SHEET"]["selection_sha256"]:
        sys.exit("refusing: the recomputed selection is not the committed one")
    graded = read_sheet(p2 / "human-sheet.csv", rw, sel)
    B.write_public(HERE / "HUMAN-COMMITMENT.json", {
        "step": "HUMAN", "sheet_commit": com["SHEET"]["_commit"], "rows": len(graded),
        "graded_sheet_sha256": B.sha_file(p2 / "human-sheet.csv"),
        "grades_sha256": B.sha_json(graded), "script_sha256": scripts()})
    print(f"{len(graded)} grades recorded; commit HUMAN-COMMITMENT.json, then b2.py read")


# ------------------------------------------------------------------ step 4: the reading
def rewrite_labels(rw, res, human, ok):
    """{relation_id: label} for the rewrites: the human grade where there is one, else the label
    the judges that passed Paper B's controls agree on; none if no judge passed."""
    out = {}
    for rid, _, _ in rw:
        if rid in human:
            out[rid] = human[rid][1]
        elif ok:
            labs = {int(res[n][str(rid)]["verified"]) for n in ok}
            if len(labs) != 1:
                raise SystemExit(f"relation {rid}: passing judges disagree off the sheet")
            out[rid] = labs.pop()
    return out


def bootstrap(pairs, seed, n=N_BOOT):
    """Paired bootstrap of precision after minus before over relations. pairs = [(before,
    after or None for deleted)]."""
    rng = random.Random(seed + 3)
    diffs = []
    for _ in range(n):
        s = [pairs[rng.randrange(len(pairs))] for _ in pairs]
        kept = [aft for _, aft in s if aft is not None]
        if not kept:
            continue
        diffs.append(sum(kept) / len(kept) - sum(b for b, _ in s) / len(s))
    diffs.sort()
    if not diffs:
        return None
    return [round(diffs[int(0.025 * len(diffs))], 4), round(diffs[int(0.975 * len(diffs)) - 1], 4)]


def reading(fz, fin_b, ctl_b, rep, rw, res, graded, seed):
    human = {i: (o, g) for i, o, g in graded}
    ok = [n for n in ("judge1", "judge2") if ctl_b[n]["passes"]]
    rlab = rewrite_labels(rw, res, human, ok)
    prim, mm = rep["primary"], rep["mismatch"]
    pairs, excluded = {}, collections.Counter()
    for r in fz["sample"]:
        i = r["relation_id"]
        if i not in fin_b:
            excluded["no_paper_b_label"] += 1
            continue
        before, act = fin_b[i][0], prim[str(i)]["action"]
        if act == "delete":
            after = None
        elif act == "rewrite":
            if i not in rlab:
                excluded["rewrite_without_label"] += 1
                continue
            after = rlab[i]
        else:
            after = before
        pairs[i] = (before, after, act)
    S = [i for i, (b, _, _) in pairs.items() if b == 1]
    U = [i for i, (b, _, _) in pairs.items() if b == 0]
    kept = [aft for _, aft, _ in pairs.values() if aft is not None]
    keep_mm = sum(1 for v in mm.values() if v["action"] == "keep")
    mm_rate = keep_mm / len(mm) if mm else None
    positive_ok = mm_rate is not None and mm_rate <= MISMATCH_KEEP_MAX
    rnd = sorted(i for i, (o, _) in human.items() if o == "random")
    answers = list(prim.values()) + list(mm.values())
    return {
        "instrument": {"positive_control_passes": positive_ok,
                       "interpreted": positive_ok},
        "B2_P": {"n_before": len(pairs), "precision_before": BR.rate([b for b, _, _ in pairs.values()]),
                 "precision_after": BR.rate(kept),
                 "difference": (round(sum(kept) / len(kept) - sum(b for b, _, _ in pairs.values())
                                      / len(pairs), 4) if kept and pairs else None),
                 "difference_bootstrap95": bootstrap([(b, a) for b, a, _ in pairs.values()], seed)},
        "B2_R": BR.rate([int(pairs[i][1] == 1) for i in S]),
        "controls": {
            "positive_mismatch": {"n": len(mm), "kept": keep_mm,
                                  "rate": None if mm_rate is None else round(mm_rate, 4),
                                  "passes": positive_ok},
            "repairer_quote_check": {
                "answers_keep_or_rewrite": sum(1 for v in answers if v["action"] != "delete"
                                               and not v.get("no_answer")),
                "quote_ok": sum(1 for v in answers if v["action"] != "delete" and v["quote_ok"])},
            "kappa_human_vs_judge_random_rewrites": {
                n: {"n": len(rnd), "kappa": B.kappa([human[i][1] for i in rnd],
                                                    [int(res[n][str(i)]["verified"]) for i in rnd])}
                for n in ("judge1", "judge2")},
            "paper_b_judges_passing": ok},
        "reported_not_interpreted": {
            "actions": dict(collections.Counter(a for _, _, a in pairs.values())),
            "no_answer": sum(1 for v in answers if v.get("no_answer")),
            "correction_rate_on_paper_b_unsupported": BR.rate(
                [int(pairs[i][1] is None or pairs[i][1] == 1) for i in U]),
            "damage_rate_on_paper_b_supported": BR.rate(
                [int(pairs[i][1] is None or pairs[i][1] == 0) for i in S]),
            "excluded": dict(excluded),
            "rewrites": len(rw), "rewrite_label_source": dict(collections.Counter(
                "human" if i in human else "judges" for i in rlab)),
            "by_relation_reason": _by(fz, pairs, "relation_reason"),
            "by_evidence_bucket": _by(fz, pairs, "bucket")}}


def _by(fz, pairs, key):
    g = collections.defaultdict(list)
    for r in fz["sample"]:
        if r["relation_id"] in pairs:
            g[str(r[key])].append(pairs[r["relation_id"]][2])
    return {k: dict(collections.Counter(v)) for k, v in sorted(g.items())}


def read(a, repo=C.ROOT):
    p2, pb = B.private(a.private), pathlib.Path(a.b_private)
    fz, fin_b, ctl_b, bcommits = b_labels(pb, a.b_refs, repo)
    com = load_step(p2, a.refs, [("REPAIR", "repairs_json_sha256", "repairs.json"),
                                 ("JUDGES", "judges_json_sha256", "judges.json"),
                                 ("HUMAN", "graded_sheet_sha256", "human-sheet.csv")], repo)
    if com["REPAIR"]["b_freeze_commit"] != bcommits["FREEZE"]:
        sys.exit("refusing: the repair ran on another Paper B freeze")
    rep, res = jread(p2 / "repairs.json"), jread(p2 / "judges.json")
    rw = rewrites(fz, rep)
    seed = com["REPAIR"]["seed"]
    sel = select(rw, res, seed)
    if B.sha_json(sel) != com["SHEET"]["selection_sha256"]:
        sys.exit("refusing: the recomputed selection is not the committed one")
    graded = read_sheet(p2 / "human-sheet.csv", rw, sel)
    if B.sha_json(graded) != com["HUMAN"]["grades_sha256"]:
        sys.exit("refusing: the grades are not the committed ones")
    out = reading(fz, fin_b, ctl_b, rep, rw, res, graded, seed)
    out["commits"] = {n: com[n]["_commit"] for n in C.COMMITS}
    out["paper_b_commits"] = bcommits
    out["tag_commit"] = com["_tag"]
    B.write_public(HERE / f"READING-{datetime.date.today().isoformat()}.json", out)
    print(json.dumps({"B2_P": out["B2_P"]["difference"], "B2_R": out["B2_R"]["rate"],
                      "positive_control": out["controls"]["positive_mismatch"]["passes"]}))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=("repair", "judge", "sheet", "grades", "read"))
    ap.add_argument("--private", required=True)
    ap.add_argument("--b-private", required=True)
    ap.add_argument("--b-freeze-ref")
    ap.add_argument("--b-refs", type=lambda s: s.split(","))
    ap.add_argument("--refs", type=lambda s: s.split(","), default=[])
    a = ap.parse_args(argv)
    need = {"repair": 0, "judge": 1, "sheet": 2, "grades": 3, "read": 4}[a.step]
    if len(a.refs) != need:
        sys.exit(f"{a.step} needs --refs with {need} B2 commitment(s)")
    if a.step == "read":
        if not a.b_refs or len(a.b_refs) != 4:
            sys.exit("read needs --b-refs with Paper B's four commitments")
    elif not a.b_freeze_ref:
        sys.exit(f"{a.step} needs --b-freeze-ref")
    {"repair": repair, "judge": judge, "sheet": sheet, "grades": grades, "read": read}[a.step](a)


if __name__ == "__main__":
    main()
