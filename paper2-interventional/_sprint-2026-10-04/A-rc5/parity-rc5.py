#!/usr/bin/env python3
"""Parity check rc4 -> rc5 of Paper A after the Codex regression review of rc4.

Usage:
    python3 parity-rc5.py [OLD] [NEW]            # default: A-v1.1-rc4.md vs A-v1.1-rc5.md
    python3 parity-rc5.py --selftest [OLD] [NEW]

Exit 0 = every difference is accounted for; 1 = an unaccounted difference; 2 = usage/IO error.

Same contract as parity-rc4.py (every change pinned, every change owned), one check stricter:

  numbers   the multiset delta of numeric tokens must equal EXPECTED_DELTA exactly. rc5
            recomputes nothing; every token change is a citation (section, line, date, file
            line) or a count word carried by new prose, and each is justified in EXPECTED_DELTA.
  owners    every changed hunk (changed runs separated by <= 2 equal lines) must contain at least
            one REGISTRY anchor, every anchor must land in a changed hunk, and (new in rc5) an
            anchor must NOT occur on the other side: an anchor that already existed in rc4 could
            land in a hunk without proving that the hunk carries that correction.
  headings  no heading changes in rc5 (the addendum is a paragraph inside F-5).
  fences    no fenced-block changes in rc5 (the §5.4 equality case is prose after the fence).

--selftest first requires OLD vs NEW to pass, then applies mutations to NEW in memory and
requires each to FAIL on the expected check: (1) a number changed in prose the round did not
touch, (2) a heading changed, (3) the R4 correction reverted with its numeral ("five" -> "5"),
(4) the R9 correction reverted in pure prose (no number involved), (5) an anchor planted in OLD
inside a hunk that changes anyway, which only the novelty rule can catch (it mutates OLD).

Finding IDs: Codex-R1..R10 = the ten findings of the Codex regression review of rc4
(A-rc4/CODEX-REGRESSAO-rc4-VERBATIM.md), all confirmed; see ../APPLY-A-rc5.md.
"""
import difflib
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_OLD = HERE.parent / "A-v1.1-rc4.md"
DEFAULT_NEW = HERE.parent / "A-v1.1-rc5.md"

NUM_RE = re.compile(r"(?<![\w.,])[−-]?\d+(?:[.,]\d+)*%?")
NUM_WORDS = ("two three four five six seven eight nine ten eleven twelve thirteen fourteen "
             "fifteen sixteen seventeen eighteen nineteen twenty hundred thousand million billion").split()
NUM_WORD_RE = re.compile(r"\b(" + "|".join(NUM_WORDS) + r")\b", re.I)

HEADING_CHANGES = {}
FENCE_CHANGES = {}

# Every token delta, with where it comes from. Nothing here is a recomputed value.
EXPECTED_DELTA = {
    # §3.1 (R3): file lines of the trackAccess comment in the deposited serving-search.ts:379-380
    "379": 1, "380": 1,
    # §4.3.2 (R4): "at most 5 slots" (-1 "5") -> "nominal quota of five" (+1 "five")
    "five": 1,
    # §5.4 (R8): "the comparator returns 0"
    "0": 1,
    # §4.4 (R1): "(§5.4)" and "(§5.6)"; §5.3 consequence 1 (R1): "(§5.4)"; §5.5 (R7): "(§5.3, §5.4)";
    # addendum: "premises of §5.3", "§5.3 consequence 1", "§5.4 and the Codex-4/...", "§5.5 and §9"
    "5.6": 1, "5.4": 4, "5.3": 3, "5.5": 1,
    # Appendix A (R6): "from 2026-08-24 to 2026-09-19" added (the 2026-08-21/09-21 span is kept)
    # => 2026 +2, 08 +1, 24 +1, 09 +1, 19 +1. The addendum adds: "rc5 (2026-10-05)",
    # "_sprint-2026-10-04/APPLY-A-rc5.md", "2026-08-24 to 2026-09-19", "2026-08-21 to 2026-09-21",
    # "COVERAGE-SET-FROM-LOG-2026-10-04.json" => 2026 +7, 10 +3, 05 +1, 04 +2, 08 +2, 24 +1,
    # 09 +2, 19 +1, 21 +2; and "10" twice more from "Kimi-10" and "top-10".
    "2026": 9, "08": 3, "09": 3, "24": 2, "19": 2, "21": 2, "10": 5, "05": 1, "04": 2,
    # addendum only: "consequence 1", "§1", "Codex-1" => 1 +3; "Codex-4" => 4 +1;
    # "Codex-5" and "At most 5 slots" (+2) with the §4.3.2 "5" removed (-1) => 5 +1; "§9" => 9 +1
    "1": 3, "4": 1, "5": 1, "9": 1,
    # addendum section citations: "§3.1, §1, §4.1", "§4.3.2" (twice), "§4.4"
    "3.1": 1, "4.1": 1, "4.3.2": 2, "4.4": 1,
    # addendum names the corrected figures: "positions 23–47" (R5), "33 + 108 set" (R6)
    "23": 1, "47": 1, "33": 1, "108": 1,
    # addendum words: "ten findings", "all ten"; "the three themselves" (R4), "takes the three" (R9)
    "ten": 2, "three": 2,
}

REGISTRY = [
    ["Codex-R2(abstract)", "new", "Most of that recorded exposure is not a delivery the system decided", 0],
    ["Codex-R3(§1)", "new", "tracked search returned (§3.1), and search is initiated by the agent; only", 0],
    ["Codex-R3(§3.1)", "new", "Tracking is switched off per call by `trackAccess = false`", 0],
    ["Codex-R3(§3.1b)", "new", "non-delivery by the brief and by tracked search, the 56,288", 0],
    ["Codex-R3(§4.1)", "new", "tracked search returned (§3.1), and search is initiated by the agent. Exposure", 0],
    ["Codex-R5", "new", "a sensitivity range, not a reconstructed historical serving position", 0],
    ["Codex-R4", "new", "nominal quota of five in the first pass", 0],
    ["Codex-R1(§4.4)", "new", "so their fraction bounds the alterable briefs from above", 0],
    ["Codex-R1(§5.3)", "new", "1. under these premises, the fraction of states", 0],
    ["Codex-R8(§5.4)", "new", "or to equality with the tie-break placing `d` ahead of `c_K`", 0],
    ["Codex-R7(§5.5a)", "new", "coordinate only within ties of the dominant one, and that response is bounded", 0],
    ["Codex-R7(§5.5b)", "new", "whose response to relevance adjustments is bounded by", 0],
    ["Codex-R7(§5.5c)", "new", "could change it there beyond the ceiling", 0],
    ["Codex-R7(§9)", "new", "and by responding to the score only within", 0],
    ["Codex-R6", "new", "coverage ids on every measurable day from 2026-08-24 to 2026-09-19)", 0],
    ["Codex-R10", "new", "Three quantities were recomputed rather than relabelled", 0],
    ["Codex-R9", "new", "The claim that zeroing the access component takes the three out of the top-10 stands.", 0],
    ["Codex-R3(F-5)", "new", "marks a top candidate of some tracked search sub-query", 0],
    ["Codex-R8(F-5)", "new", "and then with equality admitting `d` when the tie-break", 0],
    ["F-5(rc5 addendum)", "new", "**Addendum, rc5 (2026-10-05): a regression review of rc4.**", 0],
]


def tokens(s):
    return Counter(NUM_RE.findall(s)) + Counter(w.lower() for w in NUM_WORD_RE.findall(s))


def headings(text):
    out, inside = [], False
    for line in text.split("\n"):
        if line.lstrip().startswith("```"):
            inside = not inside
        elif not inside and line.startswith("#"):
            out.append(line)
    return out


def fences(text):
    blocks, cur, inside = [], [], False
    for line in text.split("\n"):
        if line.lstrip().startswith("```"):
            cur.append(line)
            if inside:
                blocks.append("\n".join(cur))
                cur = []
            inside = not inside
        elif inside:
            cur.append(line)
    return Counter(blocks)


def hunks(a_lines, b_lines, gap=2):
    ops = [op for op in difflib.SequenceMatcher(None, a_lines, b_lines, autojunk=False).get_opcodes()
           if op[0] != "equal"]
    out = []
    for tag, i1, i2, j1, j2 in ops:
        if out and i1 - out[-1][1] <= gap and j1 - out[-1][3] <= gap:
            out[-1] = (out[-1][0], i2, out[-1][2], j2)
        else:
            out.append((i1, i2, j1, j2))
    return out


def line_of(text, needle, occ):
    pos = -1
    for _ in range(occ + 1):
        pos = text.find(needle, pos + 1)
        if pos < 0:
            return None
    return text.count("\n", 0, pos)


def check(old, new, verbose=True):
    fails = []
    # numbers: pinned delta
    ta, tb = tokens(old), tokens(new)
    delta = {k: tb[k] - ta[k] for k in set(ta) | set(tb) if tb[k] != ta[k]}
    unexpected = {k: v for k, v in delta.items() if EXPECTED_DELTA.get(k) != v}
    missing = {k: v for k, v in EXPECTED_DELTA.items() if delta.get(k) != v}
    if unexpected or missing:
        fails.append(("numbers", f"unexpected {dict(sorted(unexpected.items()))}; "
                                 f"expected but absent/different {dict(sorted(missing.items()))}"))
    # owners: hunk coverage
    al, bl = old.split("\n"), new.split("\n")
    hs = hunks(al, bl)
    owners = defaultdict(set)
    landed = set()
    for fid, side, anchor, occ in REGISTRY:
        other = old if side == "new" else new
        if anchor in other:
            fails.append(("owners", f"{fid}: anchor also occurs on the other side ({side}): {anchor!r}"))
        ln = line_of(new if side == "new" else old, anchor, occ)
        if ln is None:
            fails.append(("owners", f"{fid}: anchor not found ({side}): {anchor!r}"))
            continue
        for k, (i1, i2, j1, j2) in enumerate(hs):
            lo, hi = (j1, j2) if side == "new" else (i1, i2)
            if lo <= ln < hi:
                owners[k].add(fid)
                landed.add((fid, anchor))
                break
        else:
            fails.append(("owners", f"{fid}: anchor is not inside a changed hunk ({side} line {ln + 1})"))
    attribution = defaultdict(set)
    for k, (i1, i2, j1, j2) in enumerate(hs):
        if not owners[k]:
            snippet = " / ".join(x for x in bl[j1:j2] or al[i1:i2])[:160]
            fails.append(("owners", f"hunk old {i1 + 1}-{i2} new {j1 + 1}-{j2} has no finding: {snippet!r}"))
        d = tokens("\n".join(bl[j1:j2]))
        d.subtract(tokens("\n".join(al[i1:i2])))
        for tkn, v in d.items():
            if v:
                attribution[tkn] |= owners[k] or {"UNOWNED"}
    # headings
    ha, hb = headings(old), headings(new)
    exp = []
    for h in ha:
        exp.append(HEADING_CHANGES[h][0] if h in HEADING_CHANGES else h)
    ins = HEADING_CHANGES.get(None)
    if ins:
        anchor_after = "### F-4 — 2026-10-04: a verified adversarial review of v1.1"
        if anchor_after in exp:
            exp.insert(exp.index(anchor_after) + 1, ins[0])
    if exp != hb:
        diff = [l for l in difflib.unified_diff(exp, hb, lineterm="", n=0) if l[:1] in "+-" and l[:3] not in ("+++", "---")]
        fails.append(("headings", f"undocumented heading change: {diff}"))
    # fences
    fa, fb = fences(old), fences(new)
    fd = {k: fb[k] - fa[k] for k in set(fa) | set(fb) if fb[k] != fa[k]}
    fexp = {k: v[0] for k, v in FENCE_CHANGES.items()}
    if fd != fexp:
        fails.append(("fences", f"fenced-block delta {fd} != documented {fexp}"))
    if verbose:
        print(f"hunks: {len(hs)}; registry anchors landed: {len(landed)}/{len(REGISTRY)}")
        print(f"numeric tokens that change: {len(delta)}")
        for k in sorted(delta, key=lambda x: (x.lstrip('−-').replace(',', '').replace('%', '') or x, x)):
            print(f"  {k!r:>14} {delta[k]:+d}  <- {', '.join(sorted(attribution.get(k, {'?'})))}")
        print("headings changed:", [f"{v[1]}: {(k or '(inserted)')} -> {v[0]}" for k, v in HEADING_CHANGES.items()])
        print("fenced blocks changed:", [f"{v[1]}: {v[0]:+d}" for v in FENCE_CHANGES.values()])
    return fails


def main(argv):
    selftest = "--selftest" in argv
    args = [a for a in argv if a != "--selftest"]
    try:
        old = Path(args[0] if args else DEFAULT_OLD).read_text()
        new = Path(args[1] if len(args) > 1 else DEFAULT_NEW).read_text()
    except (OSError, IndexError) as e:
        print(f"usage/IO error: {e}", file=sys.stderr)
        return 2
    fails = check(old, new)
    for c, m in fails:
        print(f"FAIL [{c}] {m}")
    if not selftest:
        print("PARITY OK" if not fails else f"PARITY FAILED ({len(fails)})")
        return 0 if not fails else 1
    if fails:
        print("SELFTEST: baseline does not pass; mutations not meaningful")
        return 1
    # (name, expected check, substring the failure message must carry, side mutated, mutation)
    mutations = [
        ("number in untouched prose", "numbers", "", "new",
         lambda t: t.replace("fleet of 6 agents: a proactive", "fleet of 7 agents: a proactive", 1)),
        ("heading changed", "headings", "", "new",
         lambda t: t.replace("## 7. Threats to validity", "## 7. Threats to the validity", 1)),
        ("R4 reverted with its numeral", "numbers", "", "new",
         lambda t: t.replace("nominal quota of five in the first pass", "nominal quota of 5 in the first pass", 1)),
        ("R9 reverted in pure prose", "owners", "", "new",
         lambda t: t.replace("The claim that zeroing the access component takes the three",
                             "The claim that access takes the three", 1)),
        # an anchor that already existed in the OLD text, inside a hunk that changes anyway:
        # only the novelty rule (new in rc5) can see it
        ("anchor pre-existing in OLD", "owners", "also occurs on the other side", "old",
         lambda t: t.replace("with a designated item on the non-selected side (§5.3).",
                             "with a designated item on the non-selected side (§5.3); so their "
                             "fraction bounds the alterable briefs from above.", 1)),
    ]
    ok = True
    for name, expect, needle, side, mut in mutations:
        base = new if side == "new" else old
        m = mut(base)
        if m == base:
            print(f"SELFTEST: mutation '{name}' did not apply")
            ok = False
            continue
        res = check(old, m, verbose=False) if side == "new" else check(m, new, verbose=False)
        got = {c for c, _ in res}
        bit = any(c == expect and needle in msg for c, msg in res)
        print(f"SELFTEST mutation '{name}': fails on {sorted(got)} -> {'BITES' if bit else 'MISSED'}")
        ok &= bit
    print("SELFTEST OK" if ok else "SELFTEST FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
