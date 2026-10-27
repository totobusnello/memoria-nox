"""Does the sparse coupling touch the OUTCOME, or only the distractors?

The overlap measured is 4.30% of pairs sharing at most 3 of ~48 sessions. Whether
that threatens the inference depends on WHICH sessions are shared: a shared
distractor session changes the haystack two instances must search; a shared
ANSWER session means two instances' outcomes depend on the same evidence, which
is the coupling that actually propagates into the estimate.
"""
import json, statistics, sys
from collections import Counter, defaultdict

rows = json.load(open(sys.argv[1]))
hay = [set(r.get("haystack_session_ids") or []) for r in rows]
ans = [set(r.get("answer_session_ids") or []) for r in rows]

cnt_hay, cnt_ans = Counter(), Counter()
for s in hay: cnt_hay.update(s)
for s in ans: cnt_ans.update(s)

print(f"answer sessions: {sum(len(s) for s in ans)} slots · "
      f"{len(cnt_ans):,} distinct")
reused_ans = {k: v for k, v in cnt_ans.items() if v > 1}
print(f"ANSWER sessions used by more than one instance: {len(reused_ans):,} "
      f"= {len(reused_ans)/len(cnt_ans):.2%} of distinct answer sessions")
if reused_ans:
    print(f"  reuse count: max {max(reused_ans.values())} · "
          f"median {statistics.median(list(reused_ans.values())):.0f}")

# pairs coupled THROUGH EVIDENCE
idx = defaultdict(list)
for i, s in enumerate(ans):
    for x in s:
        idx[x].append(i)
pair = Counter()
for x, m in idx.items():
    if len(m) > 1:
        for a in range(len(m)):
            for b in range(a + 1, len(m)):
                pair[(m[a], m[b])] += 1
n = len(rows); tot = n * (n - 1) // 2
print(f"\npairs sharing an ANSWER session: {len(pair):,} of {tot:,} = "
      f"{len(pair)/tot:.3%}")
coupled = {i for p in pair for i in p}
print(f"instances touched by evidence coupling: {len(coupled)} of {n} = "
      f"{len(coupled)/n:.1%}")

# and is a shared session an answer for one and a distractor for the other?
cross = 0
for x, m in idx.items():
    for i in range(n):
        if x in hay[i] and x not in ans[i]:
            cross += 1
            break
print(f"\nanswer sessions that are a DISTRACTOR for some other instance: {cross:,} "
      f"of {len(cnt_ans):,} = {cross/len(cnt_ans):.1%}")
print("  (that direction is harmless for the estimate: the other instance's")
print("   outcome does not depend on it being found)")

print(f"\n⇒ effective-n implication: {len(coupled)} of {n} instances sit in an")
print(f"   evidence-coupled pair. A cluster-robust SE over answer-session groups")
print(f"   is {'NEEDED' if len(pair) else 'not needed'}; the inflation is bounded by that share.")
