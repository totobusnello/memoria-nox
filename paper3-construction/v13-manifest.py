#!/usr/bin/env python3
"""The confirmatory sample of amendment v1.3 (§14.9), drawn by PROVENANCE, before any C2 call on it.

The adversarial pass on §14 (Codex, 2026-11-03) found that v1.2's "262 untouched" was defined by
qid only (smoke ∪ stage 1), and that is not enough:

  1. the 31 counterfactual instances all ran in stage 1 as rewritten variants (four primary cells,
     C0 and C1, judged); 17 of them are among the 262;
  2. 3 more of the 262 share an ANSWER session id with a smoke or stage-1 instance, so their
     evidence was distilled, served and judged there.

v1.3 removes both. What remains is 242 instances. Every LongMemEval instance shares DISTRACTOR
sessions with others (the haystacks come from one pool); that is the corpus's construction, it is
not exposure of the evidence, and it is stated rather than filtered.

The draws, in this order, from seed 20261104 (v1.2's seed, kept so the seed is not chosen after
seeing anything):
  1. confirm             v1.2's 262 minus the exposed 20 — no draw
  2. dose subsample      60 of confirm, the v1.1 allocation rule (imported, not copied)
  3. control subsample   40 of confirm, same rule
  4. counterfactual      the same 31 rewrites, declared a REGRESSION control: all 31 were seen in
                         stage 1, so this control checks the instrument, not new instances

  python3 -I v13-manifest.py <longmemeval_s_cleaned.json>          writes v13-manifest.json
  python3 -I v13-manifest.py <json> --check                        exit 1 unless identical
"""
import hashlib
import importlib.util
import json
import pathlib
import random
import sys

SEED = 20261104
HERE = pathlib.Path(__file__).resolve().parent
OUT = HERE / "v13-manifest.json"

spec = importlib.util.spec_from_file_location("s1m", HERE / "stage1-manifest.py")
s1m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(s1m)


def exposed(data, v12):
    """qid -> reason, for every v1.2 confirm instance whose question or evidence was already run."""
    byid = {r["question_id"]: r for r in data}
    spent = set(v12["smoke"]) | set(v12["stage1"])
    spent_ev = set().union(*(set(byid[q]["answer_session_ids"]) for q in spent))
    out = {}
    for q in v12["confirm"]:
        if q in v12["counterfactual"]:
            out[q] = "counterfactual variant ran in stage 1"
        elif set(byid[q]["answer_session_ids"]) & spent_ev:
            out[q] = "shares an answer session with a smoke/stage-1 instance"
    return out


def main():
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    path = sys.argv[1]
    if s1m.sha256(path) != s1m.EXPECTED_SHA256:
        sys.exit("dataset sha256 differs: wrong file or revision")
    v12_text = (HERE / "v12-manifest.json").read_text()
    v12 = json.loads(v12_text)
    data = json.load(open(path))
    byid = {r["question_id"]: r for r in data}
    ex = exposed(data, v12)
    assert len(ex) == 20, len(ex)
    confirm = sorted(q for q in v12["confirm"] if q not in ex)
    assert len(confirm) == 242, len(confirm)

    rng = random.Random(SEED)
    pool = [byid[i] for i in confirm]
    dose, alloc_d = s1m.allocate(pool, 60, rng)
    controls, alloc_c = s1m.allocate(pool, 40, rng)
    alloc = {}
    for i in confirm:
        alloc[byid[i]["question_type"]] = alloc.get(byid[i]["question_type"], 0) + 1

    man = {
        "amendment": "v1.3", "seed": SEED, "dataset": v12["dataset"],
        "dataset_revision": v12["dataset_revision"], "sha256": v12["sha256"],
        "v12_manifest_sha256": hashlib.sha256(v12_text.encode()).hexdigest(),
        "excluded_abs": v12["excluded_abs"], "smoke": v12["smoke"], "stage1": v12["stage1"],
        "exposed": dict(sorted(ex.items())),
        "confirm": confirm, "confirm_allocation": dict(sorted(alloc.items())),
        "dose_subsample": dose, "dose_allocation": alloc_d,
        "control_subsample": controls, "control_allocation": alloc_c,
        "counterfactual": v12["counterfactual"],
        "counterfactual_rewrite": v12["counterfactual_rewrite"],
        "counterfactual_role": "regression control: all 31 ran in stage 1",
    }
    text = json.dumps(man, indent=1, sort_keys=True) + "\n"
    if "--check" in sys.argv:
        same = OUT.exists() and OUT.read_text() == text
        print("manifest identical" if same else "MANIFEST DIFFERS")
        sys.exit(0 if same else 1)
    OUT.write_text(text)
    print(f"seed {SEED} · exposed {len(ex)} · confirm {len(confirm)} {man['confirm_allocation']}")
    print(f"dose {len(dose)} {alloc_d}")
    print(f"controls {len(controls)} {alloc_c}")


if __name__ == "__main__":
    main()
