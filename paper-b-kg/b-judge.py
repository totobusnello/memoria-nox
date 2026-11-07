#!/usr/bin/env python3
"""Paper B, step 2 (PREREGISTRATION.md §4, §6, §7.2): both judges and the mismatched control.

  python3 -I b-judge.py --private <dir> --freeze-ref <commit>

Refuses unless FREEZE-COMMITMENT.json is on the public main branch, after the tag, written once,
and its freeze_json_sha256 is the private freeze.json. Each judge sees the 300 sampled triples
with their own chunk and the 30 mismatched triples with the other document's chunk, temperature
0, the same prompt. Calls are cached in <dir>/judge-cache.sqlite, so a rerun after an error
resumes without paying twice. The spend cap is US$ 1 for both judges together; above it the run
aborts.

Writes <dir>/judges.json (private: quotes and reasons) and JUDGES-COMMITMENT.json (calls, cost,
the models the providers served, hashes; no rate and no label). Commit and push it, alone, before
b-sheet.py.
"""
import argparse
import importlib.util
import json
import pathlib
import sys
from concurrent.futures import ThreadPoolExecutor

HERE = pathlib.Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("bcommon", HERE / "b-common.py")
C = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(C)


def jobs(fz):
    """(kind, relation_id, item, text) for every call one judge makes."""
    by_id = {r["relation_id"]: r for r in fz["sample"]}
    out = [("primary", r["relation_id"], r, r["chunk_text"]) for r in fz["sample"]]
    out += [("mismatch", m["relation_id"], by_id[m["relation_id"]], m["chunk_text"])
            for m in fz["mismatch"]]
    return out


def run(fz, judges, cache, led, callers=None, workers=6):
    """{judge name: {kind: {relation_id: verdict}}} and the list of failures."""
    res, errors = {}, []
    for j in judges:
        res[j["name"]] = {"primary": {}, "mismatch": {}}
        js = jobs(fz)

        def one(job, j=j):
            kind, rid, item, text = job
            try:
                return kind, rid, C.judge_one(j, cache, led, item, text,
                                              (callers or {}).get(j["name"]))
            except SystemExit:
                raise
            except Exception as e:
                errors.append(f"{j['name']} {kind} {rid}: {str(e)[:120]}")
                return kind, rid, None

        with ThreadPoolExecutor(max_workers=workers) as ex:
            for kind, rid, v in ex.map(one, js):
                if v is not None:
                    res[j["name"]][kind][str(rid)] = v
    return res, errors


def commitment(fz_c, res, led, body):
    served = {name: sorted({v["served"] or "" for k in r.values() for v in k.values()})
              for name, r in res.items()}
    return {"step": "JUDGES", "freeze_commit": fz_c["_commit"],
            "freeze_json_sha256": fz_c["freeze_json_sha256"],
            "judges": {j["name"]: {"model": j["model"], "served": served[j["name"]]}
                       for j in (C.JUDGE1, C.JUDGE2)},
            "verdicts": {name: {k: len(v) for k, v in r.items()} for name, r in res.items()},
            "calls": led.calls, "cached": led.cached, "usd": round(led.usd, 4), "cap_usd": led.cap,
            "judges_json_sha256": C.sha_bytes(body.encode("utf-8")),
            "script_sha256": {p: C.sha_file(HERE / p) for p in ("b-common.py", "b-judge.py")}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--private", required=True)
    ap.add_argument("--freeze-ref", required=True)
    a = ap.parse_args()
    for j in (C.JUDGE1, C.JUDGE2):
        C.ready(j)
    P = C.private(a.private)
    if (P / "judges.json").exists():
        sys.exit("refusing: judges.json exists; the judges run once")
    com = C.ordered(C.ROOT, [("FREEZE", a.freeze_ref)])
    C.same_private(com["FREEZE"], "freeze_json_sha256", P / "freeze.json")
    fz = json.loads((P / "freeze.json").read_text(encoding="utf-8"))
    cache, led = C.Cache(P / "judge-cache.sqlite"), C.Ledger()
    res, errors = run(fz, (C.JUDGE1, C.JUDGE2), cache, led)
    print(f"calls {led.calls} · cached {led.cached} · US$ {led.usd:.4f} · errors {len(errors)}")
    if errors:
        sys.exit(f"{len(errors)} calls failed (first: {errors[0]}); rerun to resume from the cache")
    body = json.dumps(res, ensure_ascii=False, indent=1, sort_keys=True)
    C.write_private(P / "judges.json", body)
    C.write_public(HERE / "JUDGES-COMMITMENT.json", commitment(com["FREEZE"], res, led, body))
    print("next: commit JUDGES-COMMITMENT.json alone, merge, then b-sheet.py make")


if __name__ == "__main__":
    main()
