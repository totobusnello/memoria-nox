#!/usr/bin/env python3
"""Parity check v1.0.5 -> v1.0.6 of paper/paper-tecnico-nox-mem.md (final text).

v1.0.6 was produced in two passes on the same day:
  pass 1 (scorer correction): the front-matter version line, the two rewritten sentences of
         §6.3.2 (e) (S1 scorer; S2 per-query outputs), and the 22 listed old -> new values of
         SCORER-FIX.md section 4 plus the rounded abstract figure 0.406 -> 0.403;
  pass 2 (wording corrections after the Codex and Fable reviews): 11 lines of §6.3.2 and of
         the passages that repeat its conclusions (§6.5, §6.7, §7.1, §8), WORDING_LINES below.

The first version of this script (run at 20:56 on an intermediate text, sha256 76d01388…)
covered pass 1 only and fails on the final text. This version covers both passes.

Leg A (token diff, non-wording lines): with the version line masked and the 11 wording lines
       set aside on both sides, a word-level diff of the rest of the document consists only of
       single-token substitutions, and their multiset equals EXPECTED_A exactly (19 of the 22).
Leg B (byte reconstruction): applying EXPECTED_A at the positions the diff found reproduces
       the masked v1.0.6 byte for byte.
Leg C (line census): the changed lines are exactly the version line, the scorer lines
       SCORER_LINES and the 11 WORDING_LINES, and every wording line did change.
Leg D (wording lines, numbers): for each wording line, the multiset of numbers added and
       removed equals WORDING_NUMBERS exactly. This carries the other 3 of the 22 scorer
       substitutions (lines 1020 and 1024), the numbers the wording pass added (132, 20, 17,
       33, 504, 6,822, 2,482) and the removed "§6.3 → §6.3.2" reference.
Leg E (sentences): S1 and S2 (new) appear exactly once in v1.0.6 and their v1.0.5 forms are
       gone; the phrases the wording pass retired are absent from v1.0.6.

Usage: python3 parity-v106.py OLD.md NEW.md > PARITY.txt   (exit 0 = parity holds)
The v1.0.5 baseline is kept beside this script: legacy-input/paper-tecnico-nox-mem.v1.0.5.md.
"""
import collections, difflib, hashlib, re, sys

old_t = open(sys.argv[1], encoding="utf-8").read()
new_t = open(sys.argv[2], encoding="utf-8").read()

VERSION_OLD = re.compile(r"^\*\*Version\*\* v1\.0\.5 .*$", re.M)
VERSION_NEW = re.compile(r"^\*\*Version\*\* v1\.0\.6 .*$", re.M)
S1_OLD = "Scoring is by id, so a collision cannot mis-score a retrieval; "
S1_NEW_RE = re.compile(r"Scoring is by id, and each retrieved id counts once,.*?no order or sign changed\. ")
S2_OLD = "The per-query outputs are not distributed; "
S2_NEW_RE = re.compile(r"The stripped per-query outputs are in the evidence dataset "
                       r"\[10\.5281/zenodo\.23146656\]\(https://doi\.org/10\.5281/zenodo\.23146656\), "
                       r"with a verifier that checks 132 Section 6 values and statements.*?"
                       r"listed there with the reason; ")

# (old, new, occurrences) — SCORER-FIX.md section 4, plus the abstract's rounded 0.406.
EXPECTED = [
    ("0.406;", "0.403;", 1),          # abstract, LongMemEval Mem0 (3 decimals)
    ("0.4061", "0.4030", 3),          # 6.3.2 table; 6.3.3 and 6.3.4 tables
    ("0.4061),", "0.4030),", 1),      # 6.3.2 ablation sentence            (wording line 1024)
    ("0.036", "0.035", 1),            # 6.3.2 table CI half-width
    ("0.4337", "0.4331", 3),          # 6.3.2 table; 6.3.3 and 6.3.4 tables
    ("(0.4337)", "(0.4331)", 1),      # 6.3.2 ablation sentence            (wording line 1024)
    ("+0.119,", "+0.123,", 1),        # 6.3.2 Result                       (wording line 1020)
    ("0.5852", "0.5842", 2),          # 6.3.3, 6.3.4 R@10
    ("0.4570", "0.4565", 1),          # 6.4 table temporal
    ("0.4570;", "0.4565;", 1),        # 6.4 ablation sentence temporal
    ("+0.093", "+0.094", 1),          # 6.4 table temporal delta
    ("(+0.093).", "(+0.094).", 1),    # 6.4 prose
    ("0.2955", "0.2930", 1),          # 6.4 table adversarial
    ("0.2955;", "0.2930;", 1),        # 6.4 ablation sentence
    ("+0.142", "+0.144", 1),          # 6.4 table adversarial delta
    ("(+0.142)", "(+0.144)", 1),      # 6.4 prose
    ("+0.142)", "+0.144)", 1),        # 6.4 bucket composition
]  # 22 = the 21 manuscript occurrences of SCORER-FIX.md section 4 + the abstract

# the 3 scorer substitutions that sit on wording lines, checked in leg D
ON_WORDING = {("0.4061),", "0.4030),"): 1, ("(0.4337)", "(0.4331)"): 1, ("+0.119,", "+0.123,"): 1}

VERSION_LINE = 7
SCORER_LINES = {15, 1016, 1045, 1069, 1115, 1116, 1120, 1122}
WORDING_LINES = [1011, 1018, 1020, 1022, 1024, 1035, 1132, 1156, 1214, 1218, 1270]

NUM = re.compile(r"(?<![A-Za-z0-9_.])[+−-]?§?\d+(?:[.,]\d+)*(?:–§?\d+(?:\.\d+)*)?")
# per wording line: (numbers added, numbers removed), as multisets
WORDING_NUMBERS = {
    1011: ({}, {}),
    1018: ({}, {}),
    1020: ({"+0.123": 1}, {"+0.119": 1}),
    1022: ({"132": 1, "20": 1, "17": 1, "6,822": 1, "2,482": 1,          # wording pass
            "3": 1, "0.004": 1, "§6.3.2–§6.4": 1, "10": 1,               # S1 ("3 queries", "top 10")
            "10.5281": 2, "6": 2},                                       # S2 (DOI; "Section 6" ×2)
           {}),
    1024: ({"0.4331": 1, "0.4030": 1, "33": 1, "504": 1},
           {"0.4337": 1, "0.4061": 1, "§6.3": 1, "§6.3.2": 1}),
    1035: ({}, {}),
    1132: ({}, {}),
    1156: ({}, {}),
    1214: ({}, {}),
    1218: ({}, {}),
    1270: ({}, {}),
}
RETIRED = ["ablated away", "ruled out", "won anyway", "can only lower", "neutraliz",
           "at most 0.34", "against the arm that won", "handicap stands", "known to favor",
           "shown not to drive", "does not explain the §6.3 → §6.3.2 inversion"]

problems = []
out = []
lo, ln = old_t.splitlines(), new_t.splitlines()
out.append(f"v1.0.5 sha256 {hashlib.sha256(old_t.encode()).hexdigest()}")
out.append(f"v1.0.6 sha256 {hashlib.sha256(new_t.encode()).hexdigest()}")
if len(lo) != len(ln):
    problems.append(f"line count differs: {len(lo)} vs {len(ln)}")


def masked(lines, ver_re):
    t = "\n".join(f"<<W{i + 1}>>" if (i + 1) in WORDING_LINES else l for i, l in enumerate(lines))
    n_v = len(ver_re.findall(t))
    return ver_re.sub("<<VERSION>>", t), n_v


mo, vo = masked(lo, VERSION_OLD)
mn, vn = masked(ln, VERSION_NEW)
out.append(f"version line found: v1.0.5 {vo}, v1.0.6 {vn}; wording lines set aside: {len(WORDING_LINES)}")
if (vo, vn) != (1, 1):
    problems.append("version line not found exactly once on each side")

# Leg A
tok_o, tok_n = mo.split(" "), mn.split(" ")
subs = collections.Counter()
sm = difflib.SequenceMatcher(None, tok_o, tok_n, autojunk=False)
for op, i1, i2, j1, j2 in sm.get_opcodes():
    if op == "equal":
        continue
    if op == "replace" and (i2 - i1) == (j2 - j1):
        for a, b in zip(tok_o[i1:i2], tok_n[j1:j2]):
            subs[(a.strip("\n|*"), b.strip("\n|*"))] += 1
    else:
        problems.append(f"leg A non-substitution edit {op}: {tok_o[i1:i2]!r} -> {tok_n[j1:j2]!r}")
exp_all = collections.Counter({(a, b): n for a, b, n in EXPECTED})
exp_a = exp_all - collections.Counter(ON_WORDING)
out.append("")
out.append("Leg A — token substitutions outside the wording lines (old -> new : count):")
for (a, b), n in sorted(subs.items()):
    flag = "" if exp_a.get((a, b)) == n else "   <-- NOT EXPECTED / WRONG COUNT"
    out.append(f"  {a!r:>12} -> {b!r:<12} : {n}{flag}")
if subs != exp_a:
    problems.append(f"leg A multiset differs; missing {dict(exp_a - subs)}, extra {dict(subs - exp_a)}")
out.append(f"  total: {sum(subs.values())} (expected {sum(exp_a.values())}; "
           f"the other {sum(ON_WORDING.values())} of {sum(exp_all.values())} are in leg D)")

# Leg B
rec_toks = list(tok_o)
for op, i1, i2, j1, j2 in sm.get_opcodes():
    if op == "replace" and (i2 - i1) == (j2 - j1):
        for k in range(i2 - i1):
            a = tok_o[i1 + k]
            for o_, n_, _ in sorted(EXPECTED, key=lambda x: -len(x[0])):
                if o_ in a:
                    rec_toks[i1 + k] = a.replace(o_, n_, 1)
                    break
legB = " ".join(rec_toks) == mn
out.append("")
out.append(f"Leg B — v1.0.5 (masked) + EXPECTED_A reproduces v1.0.6 (masked) byte for byte: {legB}")
if not legB:
    problems.append("leg B: reconstruction differs")

# Leg C
changed = [i + 1 for i, (a, b) in enumerate(zip(lo, ln)) if a != b]
allowed = {VERSION_LINE} | SCORER_LINES | set(WORDING_LINES)
out.append("")
out.append(f"Leg C — line count v1.0.5 {len(lo)}, v1.0.6 {len(ln)}; changed lines ({len(changed)}): {changed}")
if set(changed) != allowed:
    problems.append(f"leg C: unexpected changed lines {sorted(set(changed) - allowed)}, "
                    f"unchanged expected lines {sorted(allowed - set(changed))}")

# Leg D
out.append("")
out.append("Leg D — wording lines: numbers added / removed (multisets)")
for L in WORDING_LINES:
    a = collections.Counter(NUM.findall(lo[L - 1]))
    b = collections.Counter(NUM.findall(ln[L - 1]))
    add, rem = dict(b - a), dict(a - b)
    ea, er = WORDING_NUMBERS[L]
    ok = add == ea and rem == er
    out.append(f"  l.{L}: added {add or '{}'}; removed {rem or '{}'}{'' if ok else '   <-- NOT EXPECTED'}")
    if not ok:
        problems.append(f"leg D l.{L}: added {add} (expected {ea}), removed {rem} (expected {er})")
for (o_, n_), k in ON_WORDING.items():
    hit = [L for L in WORDING_LINES if lo[L - 1].count(o_) and ln[L - 1].count(n_) and not ln[L - 1].count(o_)]
    out.append(f"  scorer substitution {o_!r} -> {n_!r} on wording line(s) {hit}")
    if len(hit) != k:
        problems.append(f"leg D: scorer substitution {o_!r} -> {n_!r} not found on exactly {k} wording line")

# Leg E
out.append("")
n1, n2 = len(S1_NEW_RE.findall(new_t)), len(S2_NEW_RE.findall(new_t))
o1, o2 = new_t.count(S1_OLD), new_t.count(S2_OLD)
out.append(f"Leg E — S1 new ×{n1}, S2 new ×{n2} in v1.0.6; S1 old ×{o1}, S2 old ×{o2} in v1.0.6; "
           f"S1 old ×{old_t.count(S1_OLD)}, S2 old ×{old_t.count(S2_OLD)} in v1.0.5")
if (n1, n2, o1, o2) != (1, 1, 0, 0) or (old_t.count(S1_OLD), old_t.count(S2_OLD)) != (1, 1):
    problems.append("leg E: S1/S2 not exactly as expected")
left = {p: new_t.count(p) for p in RETIRED if new_t.count(p)}
out.append(f"  retired phrases still in v1.0.6: {left or 'none'}")
if left:
    problems.append(f"leg E: retired phrases present {left}")

out.append("")
m1, m2 = S1_NEW_RE.search(new_t), S2_NEW_RE.search(new_t)
out.append("  S1: " + (m1.group(0).strip() if m1 else "MISSING"))
out.append("  S2: " + (m2.group(0).strip() if m2 else "MISSING"))
m = VERSION_NEW.search(new_t)
out.append("Front matter (v1.0.6): " + (m.group(0) if m else "MISSING"))
out.append("")
out.append("PARITY OK" if not problems else "PARITY FAILED:\n  " + "\n  ".join(problems))
print("\n".join(out))
sys.exit(1 if problems else 0)
