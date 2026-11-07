"""Paper B2 smoke (PREREGISTRATION.md §6, approved 2026-11-07 «01. Ok»): the repairer on five
relations drawn from OUTSIDE Paper B's 330, to measure output tokens before the tag. The five are
discarded afterwards; nothing here enters an estimate.

    python3 -I b2-smoke.py --db <snapshot.db> --freeze <B's freeze.json> --private <dir>

Prints counts, tokens and cost only. The answers stay in <dir> (mode 700).
"""
import argparse
import importlib.util
import json
import pathlib
import random
import statistics

H = pathlib.Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("b2c", H / "b2-common.py")
C = importlib.util.module_from_spec(spec)
spec.loader.exec_module(C)
B = C.B

SMOKE_SEED = "paper-b2-smoke-2026-11-07"   # fixed and public; not the study's seed
N = 5


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--freeze", required=True)
    ap.add_argument("--private", required=True)
    a = ap.parse_args()
    P = B.private(a.private)
    fz = json.loads(pathlib.Path(a.freeze).read_text())
    used = {r["relation_id"] for r in fz["sample"]} | {r["relation_id"] for r in fz["mismatch"]}
    con = B.ro(a.db)
    pop = [i for i in B.population(con) if i not in used]
    ids = sorted(random.Random(SMOKE_SEED).sample(pop, N))
    cache = B.Cache(P / "smoke-cache.sqlite")
    led = B.Ledger(cap=1.0)
    out = []
    for rid in ids:
        it = B.row(con, rid, lambda s: "")
        out.append(C.repair_one(cache, led, it, it["chunk_text"]))
    B.write_private(P / "smoke.json", json.dumps(out, ensure_ascii=False, indent=1))
    acts = {k: sum(1 for v in out if v["action"] == k) for k in ("keep", "rewrite", "delete")}
    print("served", sorted({m for v in out for m in v["served"]}))
    print("actions", acts, "no_answer", sum(v["no_answer"] for v in out),
          "quote_ok", sum(v["quote_ok"] for v in out))
    for f in ("tin", "tout", "thinking"):
        xs = [v[f] for v in out]
        print(f, "median", statistics.median(xs), "max", max(xs))
    usd = [v["usd"] for v in out]
    print(f"usd total {sum(usd):.4f} per call {sum(usd)/len(usd):.4f} "
          f"-> 330 calls {330*sum(usd)/len(usd):.2f}")


if __name__ == "__main__":
    main()
