"""EXPLORATORY, NOT PRE-REGISTERED. Stage 1 failed the answerable floor (acc(11) = 0.210 < 0.50,
§12.5); this asks where cell 11 loses the answer. Cache only, no API call.
Usage: python3 -I stage1-floor-diagnosis.py <run dir holding cache.sqlite and rows.ndjson>
The cache (115 MB) is not versioned; rows.ndjson is, under runs/stage1-2026-11-03/."""
import importlib.util, json, os, re, sys, statistics as st, collections
HERE = os.path.dirname(os.path.abspath(__file__))
spec = importlib.util.spec_from_file_location("lr", f"{HERE}/lme-run.py")
lr = importlib.util.module_from_spec(spec); spec.loader.exec_module(lr)
O = sys.argv[1]
cache = lr.Cache(f"{O}/cache.sqlite")
man = json.load(open(f"{HERE}/stage1-manifest.json"))
data = {r["question_id"]: r for r in json.load(open(os.path.expanduser("~/datasets/longmemeval/longmemeval_s_cleaned.json")))}
rows = {(x["variant"], x["cell"]): x for x in map(json.loads, open(f"{O}/rows.ndjson"))}
norm = lambda s: re.sub(r"\s+", " ", str(s)).strip().lower()
def units(r, c):
    out = []
    for s in r["haystack_sessions"]:
        sb = []
        for b in lr.session_blocks(s):
            v = cache.get(lr.h("distill", c, lr.PROMPTS[c], b))
            sb.append(v["units"] if v else [])
        out.append(sb)
    return out
stats = collections.Counter(); ranks = []; by = collections.defaultdict(list)
for q in man["stage1"]:
    r = data[q]; ev = lr.evidence(r); ref = norm(r["answer"]); row = rows[(q, "11")]
    ub = units(r, "C1")
    ans_turns = [t["content"] for i in ev for t in r["haystack_sessions"][i] if t.get("has_answer")]
    noise_dropped = sum(1 for t in ans_turns if lr.is_noise_static(t))
    ev_units = [u for i in ev for bl in ub[i] for u in bl]
    served = lr.serve(ub, list(range(len(r["haystack_sessions"]))), r)
    lines = served.split("\n")
    ev_texts = {u["text"] for u in ev_units}
    first = next((k for k, l in enumerate(lines) if any(t and t in l for t in ev_texts)), None)
    short = len(ref) <= 40
    raw_has = short and any(ref in norm(t) for t in ans_turns)
    unit_has = short and any(ref in norm(u["text"]) for u in ev_units)
    key = ("ev_units>0" if ev_units else "ev_units=0")
    by[key].append(row["correct"])
    stats["noise_dropped_answer_turn"] += noise_dropped > 0
    if short:
        stats["short_ref"] += 1; stats["raw_has_ref"] += raw_has; stats["units_have_ref"] += unit_has
        if raw_has: by["raw_has&units_have" if unit_has else "raw_has&units_lost"].append(row["correct"])
    if first is not None: ranks.append(first / max(1, len(lines)))
    stats["n"] += 1
print(dict(stats))
for k, v in by.items(): print(f"{k:22s} n={len(v):3d} acc11={sum(v)/len(v):.3f}")
print("relative position of first evidence unit in served list: median %.2f, p25 %.2f, p75 %.2f (n=%d)" % (
    st.median(ranks), *st.quantiles(ranks, n=4)[0::2], len(ranks)))

print("\n--- answer present verbatim in served units, cell 11 wrong ---")
ab = 0; wrong = []
for q in man["stage1"]:
    r = data[q]; ref = norm(r["answer"]); row = rows[(q, "11")]
    if len(ref) > 40 or row["correct"]: continue
    ub = units(r, "C1"); ev = lr.evidence(r)
    if not any(ref in norm(u["text"]) for i in ev for bl in ub[i] for u in bl): continue
    ab += row["abstained"]; wrong.append((q, r["question_type"], ref, row["answer"][:140], row["judge"].get("contem")))
print(f"wrong {len(wrong)}, of which abstained {ab}")
for w in wrong[:12]: print(w)

print("\n--- strict: reference has letters and >= 4 chars ---")
c = collections.Counter()
for q in man["stage1"]:
    r = data[q]; ref = norm(r["answer"]); row = rows[(q, "11")]
    if len(ref) > 40 or len(ref) < 4 or not re.search(r"[a-z]", ref): continue
    ub = units(r, "C1"); ev = lr.evidence(r)
    raw = any(ref in norm(t["content"]) for i in ev for t in r["haystack_sessions"][i] if t.get("has_answer"))
    inu = any(ref in norm(u["text"]) for i in ev for bl in ub[i] for u in bl)
    c["n"] += 1; c["raw"] += raw; c["units"] += inu
    if inu:
        c["in_units_correct"] += row["correct"]; c["in_units_abstained"] += row["abstained"]
    if raw and not inu: c["raw_not_units"] += 1
print(dict(c))
