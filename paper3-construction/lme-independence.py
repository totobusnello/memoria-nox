"""Codex finding 6: does "0 instances share a haystack" establish independent units?

My census compared the SORTED TUPLE of haystack_session_ids — i.e. it detects
only instances whose haystack is identical as a whole. Codex's point is that
instances can share COMPONENT sessions without sharing the whole haystack, and
then the unit of inference is not the instance and §11 repeats §4's defect with
a larger nominal n.

This measures the thing I should have measured: pairwise session overlap.
"""
import json, statistics, sys
from collections import Counter, defaultdict

P = sys.argv[1]
rows = json.load(open(P))
ids = [set(r.get("haystack_session_ids") or []) for r in rows]
n = len(rows)
print(f"{n} instances · {sum(len(s) for s in ids)} session slots")

allsess = Counter()
for s in ids:
    allsess.update(s)
print(f"distinct session ids across the corpus: {len(allsess):,}")
reused = {k: v for k, v in allsess.items() if v > 1}
print(f"session ids appearing in MORE THAN ONE instance: {len(reused):,} "
      f"= {len(reused)/len(allsess):.1%} of distinct sessions")
if reused:
    rc = sorted(reused.values(), reverse=True)
    print(f"  reuse count: max {rc[0]} instances · median {statistics.median(rc):.0f}")

# per-instance: what share of my haystack is shared with any other instance?
shared_share = []
for s in ids:
    if not s:
        continue
    shared_share.append(sum(1 for x in s if allsess[x] > 1) / len(s))
if shared_share:
    ss = sorted(shared_share)
    q = lambda f: ss[int(f * (len(ss) - 1))]
    print(f"\nshare of an instance's haystack that is NOT exclusive to it:")
    print(f"  min {min(ss):.1%} · p25 {q(.25):.1%} · median {q(.5):.1%} · "
          f"p75 {q(.75):.1%} · max {max(ss):.1%}")
    print(f"  instances with ZERO shared sessions: "
          f"{sum(1 for x in ss if x == 0)} of {len(ss)}")

# pairwise: how many pairs overlap at all, and by how much
idx = defaultdict(list)
for i, s in enumerate(ids):
    for x in s:
        idx[x].append(i)
pair = Counter()
for x, members in idx.items():
    if len(members) > 1:
        for a in range(len(members)):
            for b in range(a + 1, len(members)):
                pair[(members[a], members[b])] += 1
tot_pairs = n * (n - 1) // 2
print(f"\npairs of instances sharing >=1 session: {len(pair):,} of {tot_pairs:,} "
      f"= {len(pair)/tot_pairs:.2%}")
if pair:
    ov = sorted(pair.values(), reverse=True)
    print(f"  shared sessions per overlapping pair: max {ov[0]} · "
          f"median {statistics.median(ov):.0f}")
    big = sum(1 for v in ov if v >= 10)
    print(f"  pairs sharing >=10 sessions: {big:,}")

print(f"\n⇒ {'INDEPENDENT: the instance IS the unit' if not reused else 'NOT independent as claimed — the instance is not a clean unit'}")
