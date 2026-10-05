#!/usr/bin/env python3
"""Parity check rc5 -> rc6 of Paper A after the final Codex pass over rc5.

Usage:
    python3 parity-rc6.py [OLD] [NEW]            # default: A-v1.1-rc5.md vs A-v1.1-rc6.md
    python3 parity-rc6.py --selftest [OLD] [NEW]

Exit 0 = every difference is accounted for; 1 = an unaccounted difference; 2 = usage/IO error.

Same contract as parity-rc5.py (numbers / owners with the novelty rule / headings / fences), plus
one check that rc6 exists for:

  numbers   the multiset delta of numeric tokens must equal EXPECTED_DELTA exactly. rc6 recomputes
            and changes no number; every token change is a citation (section label, file line) or
            an existing number quoted by new scope prose, each justified in EXPECTED_DELTA.
  owners    every changed hunk must contain a REGISTRY anchor, every anchor must land in a changed
            hunk, and no anchor may occur on the other side.
  headings  exactly one documented heading change (§4.1, Codex-R3).
  fences    no fenced-block changes.
  classes   (new in rc6) the four classes the Codex pass found fixed only locally are fixed as a
            class: none of the categorical phrasings in FORBIDDEN may occur anywhere in NEW outside
            the two F-5 addenda (which quote them as history). rc4 -> rc5 fixed each finding at the
            quoted line and left siblings elsewhere; this check is what would have seen that.

--selftest first requires OLD vs NEW to pass, then applies mutations and requires each to FAIL on
the expected check: (1) a number in untouched prose, (2) a heading changed, (3) the §4.1 heading
reverted, (4) the R3 scope sentence removed from the Abstract, (5) the R4 order reverted in pure
prose, (6) an anchor planted in OLD inside a hunk (novelty rule), (7) "initiated by the agent"
reintroduced inside an already-changed hunk, which only the classes check can see.

Finding IDs: Codex-R2/R3/R4/R7 = the four rc4 corrections that the final Codex pass over rc5
(receipt .remember/adversary-receipt-codex-2026-10-05T074945-16991.txt, exit 0) found applied only
locally; see ../APPLY-A-rc6.md.
"""
import difflib
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_OLD = HERE.parent / "A-v1.1-rc5.md"
DEFAULT_NEW = HERE.parent / "A-v1.1-rc6.md"

NUM_RE = re.compile(r"(?<![\w.,])[−-]?\d+(?:[.,]\d+)*%?")
NUM_WORDS = ("two three four five six seven eight nine ten eleven twelve thirteen fourteen "
             "fifteen sixteen seventeen eighteen nineteen twenty hundred thousand million billion").split()
NUM_WORD_RE = re.compile(r"\b(" + "|".join(NUM_WORDS) + r")\b", re.I)

HEADING_CHANGES = {
    "### 4.1 Exposure: 83.78% of the corpus was never exposed — and 74.75% of what passes the "
    "coverage channel's importance floor":
    ("### 4.1 Exposure: 83.78% of the corpus has no exposure record — and 74.75% of what passes "
     "the coverage channel's importance floor", "Codex-R3"),
}
FENCE_CHANGES = {}

# Every token delta, with where it comes from. Nothing here is a recomputed or changed value.
EXPECTED_DELTA = {
    # "(§3.1)" pointers carried by the new scope/counter prose: Abstract x2 (R3 sentence, traffic
    # sentence), §1 x2 (R3, R2), §2, §4.2, §4.3.2 traffic, §4.5, §7, §8.1, §8.2, §9 traffic,
    # F-2 row (13 in body), + 2 in the rc6 addendum
    "3.1": 15,
    # 56,288 quoted by the R3 scope sentence (Abstract, §4.1 text, §8.1); 83.78% quoted twice more
    # (§4.1 text, rc6 addendum); neither value changes
    "56,288": 3, "83.78%": 2,
    # file lines of the canary comment, serving-search.ts:377-396 (§3.1 and the addendum)
    "377": 2, "396": 2,
    # file lines of pickDedup phases 0-4, serving-brief.ts:438-480 (§4.3.1, §4.3.2, addendum)
    "438": 3, "480": 3,
    # pickDedup phase labels: "phase 0" in §4.3.1, §4.3.2 and the addendum (R4)
    "0": 3,
    # "phase 1" in §4.3.1 and §4.3.2 (R4); "§1" three times in the addendum (R2, R3, R7 lists)
    "1": 5,
    # §5.5 (R7): the replay ceiling quoted as "17/350"; addendum quotes it again
    "17": 2, "350": 2,
    # §5.5 (R7) cites §4.3.1 for exhaustion; addendum cites §4.3.1 twice
    "4.3.1": 3,
    # §4.3.1 (R7) cites §5.3, §5.4; addendum cites §5.5
    "5.3": 1, "5.4": 1, "5.5": 1,
    # addendum section lists only: §4.1, §4.1.1 x2, §4.2 x2, §4.3.2 x4 (R2 list, R4 text, R7 list
    # x2), §4.5, §7, §8.1, §8.2, §9 x3 (R2, R3, R7 lists); "2" x3 = "F-2 table", "§2" (R3 list),
    # "defined in §2" ("Codex-R2" does not tokenise)
    "4.1": 1, "4.1.1": 2, "4.2": 2, "4.3.2": 4, "4.5": 1, "7": 1, "8.1": 1, "8.2": 1, "9": 3, "2": 3,
    # addendum header and record path: "rc6 (2026-10-05)", "_sprint-2026-10-04/APPLY-A-rc6.md"
    "2026": 2, "10": 2, "05": 1, "04": 1,
    # addendum count words: "four rc4 corrections" (x2: header, body), "six of the ten"
    "four": 2, "six": 1, "ten": 1,
    # §5.5 (R7): "two parts that must be kept apart"
    "two": 1,
}

ADDENDA_START = "**Addendum, rc5 (2026-10-05)"
ADDENDA_END = "## Open items"

# Categorical phrasings of the four classes. None may survive in NEW outside the F-5 addenda.
FORBIDDEN = [
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
]

REGISTRY = [
    ["Codex-R3(abstract)", "new", "brief-log record nor a positive search counter. This is a lower bound on non-delivery by the brief and by tracked search; non-delivery across all agent-facing search is not established (§3.1). The change", 0],
    ["Codex-R2(abstract)", "new", "whoever initiated the call (automated callers included) and whether or not the chunk was then returned", 0],
    ["Codex-R2(abstract traffic)", "new", "Tracked search traffic from months ago, whoever initiated it (§3.1), determined", 0],
    ["Codex-R7(abstract)", "new", "has its daily reach set by eligibility, which fixes its candidate population and which it exhausted in that regime;", 0],
    ["Codex-R2(abstract caveat)", "new", "that records candidacy in a tracked call, not who initiated it;", 0],
    ["Codex-R3(§1)", "new", "Adding search, 83.78% of the corpus has no exposure record on either surface, a lower bound on", 0],
    ["Codex-R3(§1 arrive)", "new", "the aggregate number measures what has no record of arriving", 0],
    ["Codex-R7(§1a)", "new", "for two reasons, neither of them a shortage of", 0],
    ["Codex-R2(§1)", "new", "decided by the system; the other, search, is instrumented by a counter of candidacy in tracked", 0],
    ["Codex-R7(§1b)", "new", "in which the score decides only within ties of the dominant coordinate. Whether", 0],
    ["Codex-R3(contributions)", "new", "and yet 83.78% has no exposure record on either surface, a lower bound on non-delivery by the", 0],
    ["Codex-R3(§2)", "new", "the records, not an inference: it is the absence of a record in both. Read as non-delivery, it is a", 0],
    ["Codex-R2(§3.1 table)", "new", "incremented for the top candidates of each tracked search sub-query", 0],
    ["Codex-R2(§3.1)", "new", "leaves no counter. Tracking is also the default, and the counter is cumulative", 0],
    ["Codex-R3(§3.1)", "new", "(83.78%) is a lower bound, and", 0],
    ["Codex-R3(§4.1 heading)", "new", "### 4.1 Exposure: 83.78% of the corpus has no exposure record", 0],
    ["Codex-R2(§4.1 table)", "new", "| positive search counter (live) | 9,755 |", 0],
    ["Codex-R3(§4.1 table)", "new", "| **no record on either** = 67,187", 0],
    ["Codex-R3(§4.1a)", "new", "The complement row is exact as a count of its predicate: 56,288 live chunks", 0],
    ["Codex-R3(§4.1b)", "new", "10,008 = 74.75% have no exposure record.", 0],
    ["Codex-R3(§4.1c)", "new", "reading: the numerator counts the absence of a record on both surfaces (brief ∪ tracked search),", 0],
    ["Codex-R3(§4.1d)", "new", "of the 56,288 with no record, 46,280", 0],
    ["Codex-R3(§4.1e)", "new", "importance floor and that neither the brief nor tracked search has a record of showing.", 0],
    ["Codex-R2(§4.1.1)", "new", "The two surfaces are not the same kind of thing, and only one of them is a decision of the", 0],
    ["Codex-R3(§4.1.1)", "new", "lower bound on non-delivery by the brief and by tracked search), but it restricts", 0],
    ["Codex-R3(§4.1.1 arrive)", "new", "record of arriving, not what the ranker refused. The claims", 0],
    ["Codex-R2(§4.2)", "new", "This needs saying because most of the records are search-counter", 0],
    ["Codex-R7(§4.2)", "new", "The relevance assigned by the system predicts exposure", 0],
    ["Codex-R7(§4.3.1)", "new", "This is a result in its own right, and it concerns the channel's daily reach, not its per-brief", 0],
    ["Codex-R4(§4.3.1)", "new", "F7 is listed last but runs first: it is phase 0 of", 0],
    ["Codex-R7(§4.3.2a)", "new", "by a bounded response to the score. It has another cause", 0],
    ["Codex-R2(§4.3.2)", "new", "determined by tracked search traffic from months", 0],
    ["Codex-R4(§4.3.2)", "new", "nominal quota of five in the quota pass (phase 1 of `pickDedup`), which runs after the pinned", 0],
    ["Codex-R7(§4.3.2b)", "new", "eligible pool), and within a brief it responds to score only within `last_served` ties", 0],
    ["Codex-R3(§4.5)", "new", "83.78% of the corpus has no record of reaching the agent through the brief or tracked search", 0],
    ["Codex-R7(§5.5)", "new", "It is the same conclusion as §4, reached by another route, and it has two parts that must be kept", 0],
    ["Codex-R4(§5.6)", "new", "then `pickDedup`, which places the", 0],
    ["Codex-R2(§7)", "new", "`access_count` is \"a top candidate of at least one tracked search sub-query\", whoever", 0],
    ["Codex-R3(§8.1)", "new", "That is the population this paper measures, within a", 0],
    ["Codex-R2(§8.2)", "new", "encoding of past tracked search traffic, whoever initiated", 0],
    ["Codex-R2(§9)", "new", "determined by tracked search traffic from months ago, whoever initiated it (§3.1; measured", 0],
    ["Codex-R7(§9)", "new", "eligible pool), and within a brief it responds to score only within `last_served` ties", 1],
    ["Codex-R3(§9)", "new", "That the 83.78% without an", 0],
    ["Codex-R2(F-2)", "new", "records are search-counter records, not brief deliveries", 0],
    ["Codex-R4(F-5)", "new", "pinning precedes the quota pass and backfill follows it, rc6", 0],
    ["F-5(rc6 addendum)", "new", "**Addendum, rc6 (2026-10-05): four rc4 corrections that were applied only where they were quoted.**", 0],
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
    new_h41 = HEADING_CHANGES[next(iter(HEADING_CHANGES))][0]
    old_h41 = next(iter(HEADING_CHANGES))
    # (name, expected check, substring the failure message must carry, side mutated, mutation)
    mutations = [
        ("number in untouched prose", "numbers", "", "new",
         lambda t: t.replace("fleet of 6 agents: a proactive", "fleet of 7 agents: a proactive", 1)),
        ("heading changed", "headings", "", "new",
         lambda t: t.replace("## 7. Threats to validity", "## 7. Threats to the validity", 1)),
        ("§4.1 heading reverted", "headings", "", "new",
         lambda t: t.replace(new_h41, old_h41, 1)),
        ("R3 scope sentence removed from the Abstract", "numbers", "", "new",
         lambda t: t.replace(" This is a lower bound on non-delivery by the brief and by tracked search; "
                             "non-delivery across all agent-facing search is not established (§3.1).", "", 1)),
        ("R4 order reverted in pure prose", "owners", "", "new",
         lambda t: t.replace("which runs after the pinned", "which runs before the pinned", 1)),
        ("anchor pre-existing in OLD", "owners", "also occurs on the other side", "old",
         lambda t: t.replace("| exposed in search (live) | 9,755 |", "| positive search counter (live) | 9,755 |", 1)),
        ("R2 class phrase reintroduced inside a changed hunk", "classes", "Codex-R2", "new",
         lambda t: t.replace("is delivery the system decides on its own. This",
                             "is delivery the system decides on its own, and search is initiated by the agent. This", 1)),
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
