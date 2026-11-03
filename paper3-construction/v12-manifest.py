#!/usr/bin/env python3
"""The confirmatory sample of amendment v1.2 (§13.7), drawn BEFORE any calibration call.

Stage 1 failed the answerable floor (STAGE1-RESULT.md). Its 200 instances and the 8 smoke
instances are spent: their contrasts were printed. What is left of the 462-instance universe is
262 instances nobody has run, and v1.2 confirms on all of them, in one stage.

The draws, in this order, from seed 20261104:
  1. confirm             the 462 universe minus stage 1 — no draw, all 262
  2. dose subsample      60 of confirm, the v1.1 allocation rule (proportional, largest remainder)
  3. control subsample   40 of confirm, same rule
  4. counterfactual      the same 31 rewrites as v1.1 (a control on the four primary cells; no draw)

The allocation function is imported from stage1-manifest.py, not copied, so the rule is the one
v1.1 registered. smoke, stage1 and excluded_abs are carried over so the runner can refuse overlap.

  python3 -I v12-manifest.py <longmemeval_s_cleaned.json>          writes v12-manifest.json
  python3 -I v12-manifest.py <json> --check                        exit 1 unless identical
"""
import importlib.util
import json
import pathlib
import random
import sys

SEED = 20261104
HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE / "v12-manifest.json"

spec = importlib.util.spec_from_file_location("s1m", HERE / "stage1-manifest.py")
s1m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(s1m)


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    path = sys.argv[1]
    if s1m.sha256(path) != s1m.EXPECTED_SHA256:
        sys.exit("dataset sha256 differs: wrong file or revision")
    chk = s1m.OUT.read_text()
    v11 = json.loads(chk)
    data = json.load(open(path))
    byid = {r["question_id"]: r for r in data}
    answerable = [r for r in data if not r["question_id"].endswith("_abs")]
    spent = set(v11["smoke"]) | set(v11["stage1"])
    confirm = sorted(r["question_id"] for r in answerable if r["question_id"] not in spent)
    assert len(confirm) == 262, len(confirm)

    rng = random.Random(SEED)
    pool = [byid[i] for i in confirm]
    dose, alloc_d = s1m.allocate(pool, 60, rng)
    controls, alloc_c = s1m.allocate(pool, 40, rng)
    alloc = {}
    for i in confirm:
        alloc[byid[i]["question_type"]] = alloc.get(byid[i]["question_type"], 0) + 1

    man = {
        "amendment": "v1.2", "seed": SEED, "dataset": v11["dataset"],
        "dataset_revision": v11["dataset_revision"], "sha256": v11["sha256"],
        "v11_manifest_sha256": __import__("hashlib").sha256(chk.encode()).hexdigest(),
        "excluded_abs": v11["excluded_abs"], "smoke": v11["smoke"], "stage1": v11["stage1"],
        "confirm": confirm, "confirm_allocation": dict(sorted(alloc.items())),
        "dose_subsample": dose, "dose_allocation": alloc_d,
        "control_subsample": controls, "control_allocation": alloc_c,
        "counterfactual": v11["counterfactual"],
        "counterfactual_rewrite": v11["counterfactual_rewrite"],
    }
    text = json.dumps(man, indent=1, sort_keys=True) + "\n"
    if "--check" in sys.argv:
        same = OUT.exists() and OUT.read_text() == text
        print("manifest identical" if same else "MANIFEST DIFFERS")
        sys.exit(0 if same else 1)
    OUT.write_text(text)
    print(f"seed {SEED} · confirm {len(confirm)} {man['confirm_allocation']}")
    print(f"dose {len(dose)} {alloc_d}")
    print(f"controls {len(controls)} {alloc_c}")
    print(f"counterfactual {len(man['counterfactual'])} "
          f"(in confirm: {len(set(man['counterfactual']) & set(confirm))})")


if __name__ == "__main__":
    main()
