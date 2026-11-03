"""Census of LongMemEval, on the downloaded data rather than on its README.

Why this runs before any design is written: §4 of the pre-registration died
because the unit of inference is the SESSION and production has 12 with window
variance, not 194. LoCoMo would repeat it exactly — 1,986 questions over list[10]
conversations. The claim that LongMemEval does not is a claim about its shape,
and the README is a document that can go stale (this repository's ROADMAP said
SHIPPED for features the product did not have). So it is counted here.

What the design needs from this corpus, and what is therefore measured:
  1. independent units          -> how many instances, each with its own haystack
  2. window variance            -> distribution of haystack size in chars
  3. a manipulable window       -> is haystack_sessions a list we can truncate
  4. abstention variants        -> the _abs suffix, which connects to item 8
"""
import json, statistics, sys
from collections import Counter

P = sys.argv[1] if len(sys.argv) > 1 else "lme-oracle.json"
d = json.load(open(P))
rows = d if isinstance(d, list) else d.get("data") or list(d.values())[0]
print(f"{P}: {type(d).__name__}, {len(rows)} instances")
print(f"fields: {sorted(rows[0])}")

cat = Counter(r.get("question_type", "?") for r in rows)
print(f"\ncategories ({len(cat)}):")
for k, v in cat.most_common():
    print(f"  {k:34s} {v:4d}")
# v1.0 tested question_type here and printed 0 — the field was wrong. LongMemEval marks an
# abstention instance by the _abs suffix of its question_id (Wu et al. 2024, §3; the dataset's
# own ids, e.g. gpt4_70e84552_abs). Corrected 2026-11-03, amendment v1.1 §12.1.
abst_wrong = sum(1 for r in rows if str(r.get("question_type", "")).endswith("_abs"))
abs_rows = [r for r in rows if str(r.get("question_id", "")).endswith("_abs")]
abst = len(abs_rows)
print(f"\nabstention variants (_abs on question_id): {abst} of {len(rows)} = {abst/len(rows):.1%}")
print(f"  (the v1.0 predicate, _abs on question_type: {abst_wrong})")
print(f"  by category: {dict(Counter(r['question_type'] for r in abs_rows))}")
# Positive control: a predicate that counts zero must be shown able to count one. A known
# abstention id from the dataset has to be found, or the census refuses to report.
KNOWN_ABS = "gpt4_70e84552_abs"
if any(r.get("question_id") == KNOWN_ABS for r in rows) and not any(
        r.get("question_id") == KNOWN_ABS for r in abs_rows):
    sys.exit(f"CONTROL FAILED: known abstention id {KNOWN_ABS} not matched by the predicate")
if not any(r.get("question_id") == KNOWN_ABS for r in rows):
    sys.exit(f"CONTROL UNAVAILABLE: {KNOWN_ABS} absent — wrong file or revision")

# unit of inference: does each instance carry its OWN haystack?
hs = [len(r.get("haystack_sessions") or []) for r in rows]
ids = [tuple(sorted(r.get("haystack_session_ids") or [])) for r in rows]
shared = len(ids) - len(set(ids))
print(f"\nhaystack sessions per instance: min {min(hs)} · median "
      f"{statistics.median(hs):.0f} · max {max(hs)} · mean {statistics.mean(hs):.1f}")
print(f"instances sharing an IDENTICAL haystack: {shared} "
      f"({'independent units' if shared == 0 else 'CLUSTERING — the unit is not the instance'})")

def chars(r):
    tot = 0
    for s in r.get("haystack_sessions") or []:
        turns = s if isinstance(s, list) else (s or {}).get("turns") or []
        for t in turns:
            if isinstance(t, dict):
                tot += len(t.get("content") or t.get("text") or "")
            elif isinstance(t, str):
                tot += len(t)
    return tot

cs = [chars(r) for r in rows]
cs_s = sorted(cs)
q = lambda f: cs_s[int(f * (len(cs_s) - 1))]
print(f"\nhaystack chars: min {min(cs):,} · p25 {q(.25):,} · median {q(.5):,} · "
      f"p75 {q(.75):,} · max {max(cs):,}")
print(f"  (production's worst band was 200k-1M chars; instances >= 200k here: "
      f"{sum(1 for c in cs if c >= 200_000)})")

# how many answer-bearing sessions, i.e. what truncation would have to preserve
ans = [len(r.get("answer_session_ids") or []) for r in rows]
print(f"\nanswer-bearing sessions per instance: median {statistics.median(ans):.0f} · "
      f"max {max(ans)} · instances with 0: {sum(1 for a in ans if a == 0)}")
print(f"evidence is session-level, so a truncation that drops an answer session "
      f"makes the question\n  unanswerable BY CONSTRUCTION — that is the "
      f"positive control the design needs, not a bug.")
