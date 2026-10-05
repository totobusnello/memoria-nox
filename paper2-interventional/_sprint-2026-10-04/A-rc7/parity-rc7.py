#!/usr/bin/env python3
"""Parity check rc6 -> rc7 of Paper A after the Codex pass over rc6.

Usage:
    python3 parity-rc7.py [OLD] [NEW]            # default: A-v1.1-rc6.md vs A-v1.1-rc7.md
    python3 parity-rc7.py --selftest [OLD] [NEW]

Exit 0 = every difference is accounted for; 1 = an unaccounted difference; 2 = usage/IO error.

Same contract as parity-rc6.py:

  numbers   the multiset delta of numeric tokens must equal EXPECTED_DELTA exactly. rc7 recomputes
            and changes no number; every token change is a citation (section label, file line) or
            an existing number quoted by new prose, each justified in EXPECTED_DELTA.
  owners    every changed hunk must contain a REGISTRY anchor, every anchor must land in a changed
            hunk, and no anchor may occur on the other side.
  headings  no heading changes in rc7.
  fences    no fenced-block changes.
  classes   none of the categorical phrasings in FORBIDDEN may occur anywhere in NEW outside the
            F-5 addenda (which quote them as history). rc7 keeps every rc6 class and adds the
            phrasings of the four rc7 findings: exclusive attribution of decision to the system,
            the union read as exposure, the unscoped "does not show", and eligibility reduced to
            paths or summarised as "set by eligibility".

--selftest first requires OLD vs NEW to pass, then applies mutations and requires each to FAIL on
the expected check: (1) a number in untouched prose, (2) a heading changed, (3) an anchor planted
in OLD inside a hunk (novelty rule), and then one reintroduction per rc7 class inside an
already-changed hunk, which only the classes check can see: (4) "only the brief is decided by the
system", (5) "only one of them is a decision of the system", (6) "the surface does not show",
(7) "counts what was exposed", (8) "which file paths", (9) "set by eligibility", (10) "relevance
acts", (11) "of which one can say".

Finding IDs: Codex-R2/R3/R7 (rc7) = the four medium findings of the Codex pass over rc6
(receipt .remember/adversary-receipt-codex-2026-10-05T095025-69718.txt, exit 0); see
../APPLY-A-rc7.md.
"""
import difflib
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_OLD = HERE.parent / "A-v1.1-rc6.md"
DEFAULT_NEW = HERE.parent / "A-v1.1-rc7.md"

NUM_RE = re.compile(r"(?<![\w.,])[−-]?\d+(?:[.,]\d+)*%?")
NUM_WORDS = ("two three four five six seven eight nine ten eleven twelve thirteen fourteen "
             "fifteen sixteen seventeen eighteen nineteen twenty hundred thousand million billion").split()
NUM_WORD_RE = re.compile(r"\b(" + "|".join(NUM_WORDS) + r")\b", re.I)

HEADING_CHANGES = {}
FENCE_CHANGES = {}

# Every token delta, with where it comes from. Nothing here is a recomputed or changed value.
EXPECTED_DELTA = {
    # "(↩ F-3.4; §3.1)" in the §4.1 scope sentence (R3); "§3.1" in the rc7 addendum
    "3.1": 2,
    # §4.3.1 (R7): the replay ceiling quoted as "17/350 replay states" (value unchanged, §4.4)
    "17": 1, "350": 1,
    # rc7 addendum: eligibility predicate lines, brief.ts:638-647
    "638": 1, "647": 1,
    # rc7 addendum section lists: §4.1 x2 ("§4.1 finding", "§4.1 said"), §4.1.1 x2 (union, R2
    # list), §1 (R2 list), §4.3.1, §5.5, §4.3.2, §9 (R7 list)
    "4.1": 2, "4.1.1": 2, "1": 1, "4.3.1": 1, "5.5": 1, "4.3.2": 1, "9": 1,
    # addendum header "rc7 (2026-10-05)" and record path "_sprint-2026-10-04/APPLY-A-rc7.md"
    "2026": 2, "10": 2, "05": 1, "04": 1,
    # addendum count words: "four rc6 phrasings" (header), "four medium findings" (body)
    "four": 2,
}

ADDENDA_START = "**Addendum, rc5 (2026-10-05)"
ADDENDA_END = "## Open items"

# Categorical phrasings. None may survive in NEW outside the F-5 addenda.
FORBIDDEN = [
    # --- rc6 classes, kept so they cannot return ---
    ("Codex-R2", r"initiated\s+by\s+the\s+agent"),
    ("Codex-R2", r"agent-initiated\s+search"),
    ("Codex-R2", r"the\s+agent\s+initiates"),
    ("Codex-R2", r"accounts\s+for\s+most\s+of\s+the\s+exposure"),
    ("Codex-R2", r"most\s+of\s+that\s+recorded\s+exposure"),
    ("Codex-R2", r"accessed\s+by\s+search\s+at\s+least\s+once"),
    ("Codex-R3", r"never\s+exposed\s+by\s+either"),
    ("Codex-R3", r"never\s+reached\s+the\s+agent"),
    ("Codex-R3", r"no\s+surface\s+ever\s+showed"),
    ("Codex-R3", r"83\.78%\s+of\s+the\s+corpus\s+was\s+never"),
    ("Codex-R3", r"measures\s+what\s+did\s+not\s+arrive"),
    ("Codex-R4", r"before\s+pinning"),
    ("Codex-R4", r"pinning\s+and\s+backfill\s+follow"),
    ("Codex-R7", r"nothing\s+to\s+do\s+with\s+relevance"),
    ("Codex-R7", r"not\s+governed\s+by\s+relevance"),
    ("Codex-R7", r"in\s+which\s+the\s+score\s+does\s+not\s+decide"),
    ("Codex-R7", r"deaf(ness)?\s+to\s+the\s+score"),
    ("Codex-R7", r"\bimmune\b"),
    ("Codex-R7", r"not\s+by\s+relevance"),
    ("Codex-R7", r"does\s+not\s+predict\s+exposure"),
    # --- rc7 classes ---
    # R2: exclusive attribution of decision to the system ("only the brief's capacity" is not one)
    ("Codex-R2-rc7", r"\bonly\s+the\s+brief\b(?!'s)"),
    ("Codex-R2-rc7", r"only\s+one\s+of\s+them\s+is\s+a\s+decision"),
    ("Codex-R2-rc7", r"decided\s+by\s+the\s+system"),
    ("Codex-R2-rc7", r"decision\s+of\s+the\s+system"),
    ("Codex-R2-rc7", r"the\s+system\s+decides"),
    # R2/R3: the historical union read as exposure; the live corpus as "never exposed" population
    ("Codex-R2R3-rc7", r"counts\s+what\s+was\s+exposed"),
    ("Codex-R2R3-rc7", r"of\s+which\s+one\s+can\s+say"),
    # R3: unscoped non-delivery in §4.1 ("this measurement does not show X" is not one)
    ("Codex-R3-rc7", r"surface\s+does\s+not\s+show"),
    # R7: eligibility reduced to paths, or summarised without its components
    ("Codex-R7-rc7", r"which\s+(file\s+)?paths"),
    ("Codex-R7-rc7", r"file\s+paths\s+the\s+channel"),
    ("Codex-R7-rc7", r"paths\s+enter\s+the\s+pool"),
    ("Codex-R7-rc7", r"set\s+by\s+eligibility"),
    ("Codex-R7-rc7", r"relevance\s+acts"),
]

REGISTRY = [
    ["Codex-R2-rc7(abstract a)", "new", "The brief, the surface that proactively selects content for delivery, exposed", 0],
    ["Codex-R7-rc7(abstract)", "new", "has a daily reach bounded by its eligible population (path patterns, the importance/pain floor and age windows), which it exhausted in that regime;", 0],
    ["Codex-R2-rc7(abstract b)", "new", "not who initiated it; the brief proactively selects content for delivery, and the mechanism claims", 0],
    ["Codex-R2-rc7(§1)", "new", "proactively selects content for delivery; the other, search, is instrumented", 0],
    ["Codex-R3-rc7(§4.1)", "new", "it concerns fragments that pass the coverage channel's importance floor and have neither a brief-log record", 0],
    ["Codex-R2-rc7(§4.1.1 a)", "new", "The two surfaces are not the same kind of thing. The brief proactively selects content for", 0],
    ["Codex-R2-rc7(§4.1.1 b)", "new", "records what was selected for delivery. This", 0],
    ["Codex-R2R3-rc7(§4.1.1 union)", "new", "brief-log membership with positive search counters on live chunks; it includes 152 chunks served", 0],
    ["Codex-R7-rc7(§4.3.1)", "new", "selection. Eligibility combines path patterns, the importance/pain floor and age windows. In the", 0],
    ["Codex-R7-rc7(§4.3.2)", "new", "importance/pain floor and age windows), which it exhausted in the measured regime, and within a brief", 0],
    ["Codex-R7-rc7(§5.5)", "new", "apart. The first is the channel's daily reach, bounded by its eligible population. Eligibility", 0],
    ["Codex-R7-rc7(§9)", "new", "importance/pain floor and age windows), which it exhausted in the measured regime, and within a brief", 1],
    ["F-5(rc7 addendum)", "new", "**Addendum, rc7 (2026-10-05): four rc6 phrasings that kept an exclusive or unscoped reading.**", 0],
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


def outside_addenda(text):
    a = text.find(ADDENDA_START)
    b = text.find(ADDENDA_END, a) if a >= 0 else -1
    if a < 0 or b < 0:
        return text, False
    return text[:a] + text[b:], True


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
                landed.add((fid, anchor, occ))
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
    exp = [HEADING_CHANGES[h][0] if h in HEADING_CHANGES else h for h in ha]
    if exp != hb:
        diff = [l for l in difflib.unified_diff(exp, hb, lineterm="", n=0) if l[:1] in "+-" and l[:3] not in ("+++", "---")]
        fails.append(("headings", f"undocumented heading change: {diff}"))
    # fences
    fa, fb = fences(old), fences(new)
    fd = {k: fb[k] - fa[k] for k in set(fa) | set(fb) if fb[k] != fa[k]}
    fexp = {k: v[0] for k, v in FENCE_CHANGES.items()}
    if fd != fexp:
        fails.append(("fences", f"fenced-block delta {fd} != documented {fexp}"))
    # classes: categorical phrasings must be gone outside the F-5 addenda
    body, found = outside_addenda(new)
    if not found:
        fails.append(("classes", "F-5 addenda region not found; cannot exclude quoted history"))
    residual = []
    for fid, pat in FORBIDDEN:
        for m in re.finditer(pat, body, re.I):
            ln = body.count("\n", 0, m.start()) + 1
            residual.append(f"{fid} /{pat}/ at body line {ln}: {m.group(0)!r}")
    if residual:
        fails.append(("classes", "; ".join(residual)))
    if verbose:
        print(f"hunks: {len(hs)}; registry anchors landed: {len(landed)}/{len(REGISTRY)}")
        print(f"numeric tokens that change: {len(delta)}")
        for k in sorted(delta, key=lambda x: (x.lstrip('−-').replace(',', '').replace('%', '') or x, x)):
            print(f"  {k!r:>14} {delta[k]:+d}  <- {', '.join(sorted(attribution.get(k, {'?'})))}")
        print("headings changed:", [f"{v[1]}: {k} -> {v[0]}" for k, v in HEADING_CHANGES.items()])
        print("fenced blocks changed:", [f"{v[1]}: {v[0]:+d}" for v in FENCE_CHANGES.values()])
        print(f"classes: {len(FORBIDDEN)} forbidden phrasings, {len(residual)} residual outside the addenda")
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
        ("anchor pre-existing in OLD", "owners", "also occurs on the other side", "old",
         lambda t: t.replace("is delivery the system decides on its own. This",
                             "records what was selected for delivery. This", 1)),
        ("R2: 'only the brief ... decided by the system' back in the Abstract", "classes", "Codex-R2-rc7", "new",
         lambda t: t.replace("not who initiated it; the brief proactively selects content for delivery,",
                             "not who initiated it; only the brief is a delivery decided by the system,", 1)),
        ("R2: 'only one of them is a decision' back in §4.1.1", "classes", "Codex-R2-rc7", "new",
         lambda t: t.replace("The two surfaces are not the same kind of thing. The brief",
                             "The two surfaces are not the same kind of thing, and only one of them is a decision of the system. The brief", 1)),
        ("R3: 'the surface does not show' back in §4.1", "classes", "Codex-R3-rc7", "new",
         lambda t: t.replace("lessons\"; it concerns fragments that pass",
                             "lessons\"; the surface does not show fragments that pass", 1)),
        ("R2/R3: 'counts what was exposed' back in §4.1.1", "classes", "Codex-R2R3-rc7", "new",
         lambda t: t.replace("and does not count delivered exposure. The complement",
                             "and counts what was exposed at some point. The complement", 1)),
        ("R2/R3: 'of which one can say' back in §4.1.1", "classes", "Codex-R2R3-rc7", "new",
         lambda t: t.replace("over which\nthis record predicate is measured.",
                             "of which one can say \"never exposed\".", 1)),
        ("R7: 'which file paths' back in §4.3.1", "classes", "Codex-R7-rc7", "new",
         lambda t: t.replace("selection. Eligibility combines path patterns,",
                             "selection. Eligibility, which file paths the channel sees, combines path patterns,", 1)),
        ("R7: 'set by eligibility' back in §9", "classes", "Codex-R7-rc7", "new",
         lambda t: t[::-1].replace("has a daily reach bounded by its eligible population"[::-1],
                                   "has its daily reach set by eligibility"[::-1], 1)[::-1]),
        ("R7: 'relevance acts' back in §5.5", "classes", "Codex-R7-rc7", "new",
         lambda t: t.replace("The second is\nper-brief selection.",
                             "The second is\nper-brief selection, where relevance acts.", 1)),
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
