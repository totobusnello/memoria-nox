#!/usr/bin/env python3
"""Step 2 population: the (query, chunk) pairs the judges read, and the truth for each.

Deterministic and offline. Reads the frozen step-1 inputs (plan, 3.11.1 baseline chunks and BM25
rankings) and writes stage2/pairs.json. `--check` rebuilds in memory and fails if the committed file
differs, so the population cannot drift after the pre-registration tag.

Truth T for a pair: the chunk contains, verbatim, the planted primary sentence or a planted paraphrase
listed in the query's T (step 1's rule). Every pair of a false-premise query is false. R: same rule
over the query's R.
"""
import json
import pathlib
import random
import sys

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
PLAN = ROOT / "plan" / "plan.json"
BASE = ROOT / "results" / "3.11.1"
OUT = HERE / "pairs.json"
SHEET = HERE / "human" / "SHEET.md"
SEED = 20261126
SEED_A_CONTROL = 20261027  # the seed of Paper A's random-chunk control
TOP = 10


def build():
    plan = json.loads(PLAN.read_text())
    chunks = json.loads((BASE / "chunks-baseline.json").read_text())
    rankings = json.loads((BASE / "rankings.json").read_text())
    text = {c["id"]: c["text"] for c in chunks}
    facts = {f["id"]: f for f in plan["facts"]}
    rng = random.Random(SEED)
    rng_ctl = random.Random(SEED_A_CONTROL)
    all_ids = sorted(text)
    pairs, gold_check = [], []
    for q in plan["queries"]:
        top = [x["id"] for x in rankings[q["id"]]][:TOP]
        T = R = N = set()
        if q["kind"] == "fact":
            f = facts[q["fact"]]
            items = {f["primary"]["id"]: f["primary"]["text"],
                     **{a["id"]: a["text"] for a in f["paraphrases"]}}
            T = {cid for cid, t in text.items() if any(items[i] in t for i in q["T"])}
            R = {cid for cid, t in text.items() if any(items[i] in t for i in q["R"])}
            negs = [n["text"] for n in f["negatives"]]
            N = {cid for cid, t in text.items() if any(n in t for n in negs)}
        source = {}
        for rank, cid in enumerate(top, 1):
            source[cid] = f"top{rank}"
        for cid in sorted(T - source.keys()):
            source[cid] = "truth_outside_top"
        for cid in sorted(N - source.keys()):
            source[cid] = "context_negative"
        rest = sorted(cid for cid in text if cid not in source)
        rnd = rng.choice(rest)
        source[rnd] = "random"
        for cid, src in source.items():
            pairs.append({"query": q["id"], "kind": q["kind"], "chunk": cid, "source": src,
                          "T": cid in T, "R": cid in R, "context_negative": cid in N})
        for cid in sorted(R):
            gold_check.append({"query": q["id"], "chunk": cid, "as_gold": "correct", "T": cid in T})
        for cid in sorted(N):
            gold_check.append({"query": q["id"], "chunk": cid, "as_gold": "wrong_superseded_or_rejected", "T": cid in T})
        # Paper A's control: any chunk id, redrawn while equal to the query's first gold chunk
        first_gold = min(R) if R else None
        while True:
            ctl = rng_ctl.choice(all_ids)
            if ctl != first_gold:
                break
        gold_check.append({"query": q["id"], "chunk": ctl, "as_gold": "random", "T": ctl in T,
                           "in_population": ctl in source})
    # human sample (§6): strata and sizes fixed by the pre-registration
    srng = random.Random(SEED)
    T_pos = [i for i, p in enumerate(pairs) if p["T"]]
    ctx = [i for i, p in enumerate(pairs) if p["context_negative"]]
    fp = [i for i, p in enumerate(pairs) if p["kind"] == "false_premise"]
    other = [i for i, p in enumerate(pairs)
             if p["kind"] == "fact" and not p["T"] and not p["context_negative"]]
    fp_by_q = {}
    for i in fp:
        fp_by_q.setdefault(pairs[i]["query"], []).append(i)
    strata = {"truth": (T_pos, srng.sample(T_pos, 30)),
              "context_negative": (ctx, list(ctx)),
              "false_premise": (fp, [i for qid in sorted(fp_by_q) for i in srng.sample(fp_by_q[qid], 2)]),
              "other_false": (other, srng.sample(other, 45))}
    sample = []
    for name, (pop, chosen) in strata.items():
        for i in chosen:
            sample.append({"pair": i, "stratum": name, "inclusion": len(chosen) / len(pop)})
    srng.shuffle(sample)
    for row, s_ in enumerate(sample, 1):
        s_["row"] = row
    # J-premise sample: the 55 false-premise pairs and 30 + 25 fact pairs
    prng = random.Random(SEED + 1)
    fact_T = [i for i, p in enumerate(pairs) if p["kind"] == "fact" and p["T"]]
    fact_F = [i for i, p in enumerate(pairs) if p["kind"] == "fact" and not p["T"]]
    premise = sorted(fp) + sorted(prng.sample(fact_T, 30)) + sorted(prng.sample(fact_F, 25))
    counts = {
        "pairs": len(pairs),
        "by_source": {k: sum(1 for p in pairs if p["source"].startswith(k))
                      for k in ("top", "truth_outside_top", "context_negative", "random")},
        "T_true": sum(p["T"] for p in pairs),
        "R_true": sum(p["R"] for p in pairs),
        "context_negative_pairs": sum(p["context_negative"] for p in pairs),
        "gold_check": {k: sum(1 for g in gold_check if g["as_gold"] == k)
                       for k in ("correct", "wrong_superseded_or_rejected", "random")},
        "gold_controls_outside_population": sum(1 for g in gold_check
                                                if g["as_gold"] == "random" and not g["in_population"]),
        "human_sample": {k: sum(1 for x in sample if x["stratum"] == k)
                         for k in ("truth", "context_negative", "false_premise", "other_false")},
        "premise_pairs": len(premise),
    }
    return {"seed": SEED, "inputs": {"plan": "plan/plan.json", "baseline": "results/3.11.1"},
            "counts": counts, "pairs": pairs, "gold_check": gold_check,
            "human_sample": sample, "premise_pairs": premise}


def dump(obj):
    return json.dumps(obj, ensure_ascii=False, indent=1) + "\n"


def sheet(data):
    """The blind sheet of §6: question and chunk only, in the sample's shuffled order."""
    plan = json.loads(PLAN.read_text())
    qtext = {q["id"]: q["text"] for q in plan["queries"]}
    chunks = json.loads((BASE / "chunks-baseline.json").read_text())
    text = {c["id"]: c["text"] for c in chunks}
    out = ["# Step 2 human sheet (blind)", "",
           "For each row, read the question and the passage and write one code in the second",
           "column of `human/annotations.tsv` (row, code, note; tab-separated):",
           "C complete, P partial, D discarded (value marked rejected, superseded or negated),",
           "M mention without the datum, F off, ? cannot decide (with a note).",
           "Do not open pairs.json or any other file of stage2/ while reading.", ""]
    for s_ in sorted(data["human_sample"], key=lambda x: x["row"]):
        p = data["pairs"][s_["pair"]]
        body = text[p["chunk"]].replace("\n", "\n> ")
        out += [f"## Row {s_['row']}", "", f"**Question:** {qtext[p['query']]}", "", "> " + body, ""]
    return "\n".join(out) + "\n"


def main():
    data = build()
    if "--check" in sys.argv:
        if not OUT.exists() or OUT.read_text() != dump(data):
            sys.exit("pairs.json drifted from pairs.py: rebuild and review")
        if not SHEET.exists() or SHEET.read_text() != sheet(data):
            sys.exit("human/SHEET.md drifted from pairs.py: rebuild and review")
        print("pairs: ok", json.dumps(data["counts"]))
        return
    OUT.write_text(dump(data))
    SHEET.parent.mkdir(exist_ok=True)
    SHEET.write_text(sheet(data))
    print(json.dumps(data["counts"], indent=1))


if __name__ == "__main__":
    main()
