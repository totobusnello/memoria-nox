#!/usr/bin/env python3
"""Parity check rc7 -> rc8 of Paper A after the last Codex pass over rc7.

Usage:
    python3 parity-rc8.py [OLD] [NEW]            # default: A-v1.1-rc7.md vs A-v1.1-rc8.md
    python3 parity-rc8.py --selftest [OLD] [NEW]

Exit 0 = every difference is accounted for; 1 = an unaccounted difference; 2 = usage/IO error.

Same contract as parity-rc7.py:

  numbers   the multiset delta of numeric tokens must equal EXPECTED_DELTA exactly. rc8 recomputes
            and changes no number; every token change is in the rc8 addendum (section label, date,
            receipt path, count words) or in the two §1 sentences, each justified in EXPECTED_DELTA.
  owners    every changed hunk must contain a REGISTRY anchor, every anchor must land in a changed
            hunk, and no anchor may occur on the other side.
  headings  no heading changes in rc8.
  fences    no fenced-block changes.
  classes   none of the categorical phrasings in FORBIDDEN may occur anywhere in NEW outside the
            F-5 addenda (which quote them as history). rc8 keeps every rc6 and rc7 class and adds
            the two phrasings the rc8 pass replaced in §1: "path-and-age" (eligibility named by two
            of its three components) and "shortage of relevance" (a categorical exclusion).

--selftest first requires OLD vs NEW to pass, then applies mutations and requires each to FAIL on
the expected check: (1) a number in untouched prose, (2) a heading changed, (3) an anchor planted
in OLD inside a hunk (novelty rule), then one reintroduction per rc8 class inside an
already-changed hunk and outside every REGISTRY anchor, so that only the classes check can see it: (4) "path-and-age", (5) "path and age",
(6) "shortage of relevance", and two rc7 classes reintroduced in the same hunk, to prove the
inherited list still bites: (7) "set by eligibility", (8) "relevance acts". Then three that keep
the deposit-status entry narrow: (9) another number inside the status hunk, (10) a different
version DOI, (11) a different concept DOI.

DEPOSIT-STATUS-2026-10-05 (added 2026-10-05, after deposit): the status block at line 10 was
rewritten when the text was deposited as v1.1 (Zenodo draft 23163119). That hunk is owned by
three anchors (the header date, the version DOI, the concept DOI) and its numeric tokens are pinned
in DEPOSIT_STATUS_DELTA; nothing else in the checks changed.

Finding IDs: Codex-rc8 = the two §1 sentences taken verbatim from the Codex pass over rc7
(receipt .remember/adversary-receipt-codex-2026-10-05T100118-80790.txt, exit 0); see the F-5
"Addendum, rc8" in A-v1.1-rc8.md.
"""
import difflib
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_OLD = HERE.parent / "A-v1.1-rc7.md"
DEFAULT_NEW = HERE.parent / "A-v1.1-rc8.md"

NUM_RE = re.compile(r"(?<![\w.,])[−-]?\d+(?:[.,]\d+)*%?")
NUM_WORDS = ("two three four five six seven eight nine ten eleven twelve thirteen fourteen "
             "fifteen sixteen seventeen eighteen nineteen twenty hundred thousand million billion").split()
NUM_WORD_RE = re.compile(r"\b(" + "|".join(NUM_WORDS) + r")\b", re.I)

HEADING_CHANGES = {}
FENCE_CHANGES = {}

# Every token delta, with where it comes from. Nothing here is a recomputed or changed value.
EXPECTED_DELTA = {
    # rc8 addendum: "two §1 sentences" (header) and "two §1 sentences" (body)
    "1": 2,
    # rc8 addendum: header "rc8 (2026-10-05)" and receipt path "...codex-2026-10-05T100118-80790.txt"
    # (the "100118" after "T" is not a token: it is preceded by a word character)
    "2026": 2, "10": 2, "05": 2, "80790": 1,
    # rc8 addendum: "exit 0" in the receipt citation
    "0": 1,
    # rc8 addendum count words: "two §1 sentences" x2, "named two of the three components",
    # the quoted old phrasing "for two reasons", and the quoted new phrasing "two distinct constraints"
    "two": 5, "three": 1,
}
# DEPOSIT-STATUS-2026-10-05: the status block (line 10) was rewritten at deposit, after this gate
# was written: "**Status (2026-10-04).** ... not yet deposited as a new version" became
# "**Status (2026-10-05).** ... deposited on 2026-10-05 as v1.1 of that record, DOI
# `10.5281/zenodo.23163119` (version 2 of concept `10.5281/zenodo.22181414`)". Its token delta,
# added to the rc8 one above (not merged into it, so each source stays readable):
#   header date 2026-10-04 -> 2026-10-05:   "04" -1, "05" +1
#   deposit date 2026-10-05:                "2026" +1, "10" +1, "05" +1
#   the two DOIs:                           "10.5281" +2 (the record numbers 23163119 and
#                                           22181414 follow a "." and are not tokens; the three
#                                           REGISTRY anchors below pin them verbatim)
#   "version 2 of concept":                 "2" +1
DEPOSIT_STATUS_DELTA = {"04": -1, "05": 2, "2026": 1, "10": 1, "10.5281": 2, "2": 1}
for _k, _v in DEPOSIT_STATUS_DELTA.items():
    EXPECTED_DELTA[_k] = EXPECTED_DELTA.get(_k, 0) + _v

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
    # --- rc8 classes ---
    # eligibility named by two of its three components (the importance/pain floor omitted)
    ("Codex-rc8", r"path[-\s]+and[-\s]+age"),
    # categorical exclusion of relevance as a constraint
    ("Codex-rc8", r"shortage\s+of\s+relevance"),
]

REGISTRY = [
    ["Codex-rc8(§1 a)", "new", "exhausted a pool of 108 chunks selected by path patterns, the importance/pain floor and age windows in the measured regime", 0],
    ["Codex-rc8(§1 b)", "new", "That channel has two distinct constraints: eligibility (path patterns, the importance/pain floor and age windows) bounds daily reach;", 0],
    ["F-5(rc8 addendum)", "new", "**Addendum, rc8 (2026-10-05): two §1 sentences that the rc7 class search missed.**", 0],
    # status block rewritten at deposit (see DEPOSIT_STATUS_DELTA); one anchor per changed fact
    ["DEPOSIT-STATUS-2026-10-05(date)", "new", "> **Status (2026-10-05).** v1.0 of this manuscript", 0],
    ["DEPOSIT-STATUS-2026-10-05(DOI)", "new", "deposited on 2026-10-05 as v1.1 of that record, DOI `10.5281/zenodo.23163119` (version 2 of", 0],
    ["DEPOSIT-STATUS-2026-10-05(concept)", "new", "concept `10.5281/zenodo.22181414`). Rule of this file", 0],
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
         lambda t: t.replace("That channel is the one that fails, for two reasons,",
                             "That channel has two distinct constraints: eligibility (path patterns, the importance/pain floor and age windows) bounds daily reach; for two reasons,", 1)),
        ("rc8: 'path-and-age' back in §1", "classes", "Codex-rc8", "new",
         lambda t: t.replace("channel: the coverage channel exhausted a pool of 108",
                             "channel: the coverage channel, a path-and-age channel, exhausted a pool of 108", 1)),
        ("rc8: 'path and age' (unhyphenated) back in §1", "classes", "Codex-rc8", "new",
         lambda t: t.replace("channel: the coverage channel exhausted a pool of 108",
                             "channel: the coverage channel, cut by path and age, exhausted a pool of 108", 1)),
        ("rc8: 'shortage of relevance' back in §1", "classes", "Codex-rc8", "new",
         lambda t: t.replace("only within `last_served` ties:\n\n1. **Calendar:**",
                             "only within `last_served` ties, neither a shortage of relevance:\n\n1. **Calendar:**", 1)),
        ("rc7 class 'set by eligibility' in an rc8 hunk", "classes", "Codex-R7-rc7", "new",
         lambda t: t.replace("daily reach; holding eligibility fixed, an additive",
                             "daily reach; holding fixed what is set by eligibility, an additive", 1)),
        ("rc7 class 'relevance acts' in an rc8 hunk", "classes", "Codex-R7-rc7", "new",
         lambda t: t.replace("changes per-brief selection only within",
                             "changes per-brief selection, where relevance acts, only within", 1)),
        # DEPOSIT-STATUS-2026-10-05 must not become a blanket pass for the status hunk:
        ("deposit status: a token changed inside the owned hunk", "numbers", "", "new",
         lambda t: t.replace("(version 2 of\n", "(version 3 of\n", 1)),
        ("deposit status: a different version DOI", "owners", "DEPOSIT-STATUS-2026-10-05(DOI)", "new",
         lambda t: t.replace("`10.5281/zenodo.23163119` (version 2 of", "`10.5281/zenodo.23163118` (version 2 of", 1)),
        ("deposit status: a different concept DOI", "owners", "DEPOSIT-STATUS-2026-10-05(concept)", "new",
         lambda t: t.replace("concept `10.5281/zenodo.22181414`)", "concept `10.5281/zenodo.22181415`)", 1)),
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
