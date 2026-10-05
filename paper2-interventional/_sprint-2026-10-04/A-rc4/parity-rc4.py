#!/usr/bin/env python3
"""Parity check rc3 -> rc4 of Paper A after a round of verified corrections.

Usage:
    python3 parity-rc4.py [OLD] [NEW]            # default: A-v1.1-rc3.md vs A-v1.1-rc4.md
    python3 parity-rc4.py --selftest [OLD] [NEW]

Exit 0 = every difference is accounted for; 1 = an unaccounted difference; 2 = usage/IO error.

Unlike parity-rc3.py (a prose pass, where numbers had to be identical), rc4 changes numbers on
purpose. So the contract is: every change is pinned and every change has an owner.

  numbers   the multiset delta of numeric tokens (digits with sign, decimal/thousands
            separators and %, plus the cardinal words two..twenty/hundred/thousand/million/
            billion) must equal EXPECTED_DELTA exactly, token by token. A token that changes
            and is not listed, or a listed change that did not happen, fails.
  owners    the line-level diff is grouped into hunks (changed runs separated by <= 2 equal
            lines). Every hunk must contain at least one REGISTRY anchor (a string of the new
            text, or of the old text for a pure deletion, that does not occur on the other side),
            and every anchor must land inside a changed hunk. Each token delta is then
            attributed to the finding IDs of the hunks it changes in, and listed.
  headings  the ordered list of heading lines may differ only by HEADING_CHANGES.
  fences    the multiset of fenced code blocks may differ only by FENCE_CHANGES.

--selftest first requires OLD vs NEW to pass, then applies mutations to NEW in memory and
requires each to FAIL on the expected check: (1) a number changed in prose the round did not
touch, (2) a heading changed, (3) one registered correction reverted (GLM-3, 104 -> 98 s).
"""
import difflib
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
DEFAULT_OLD = HERE.parent / "A-v1.1-rc3.md"
DEFAULT_NEW = HERE.parent / "A-v1.1-rc4.md"

NUM_RE = re.compile(r"(?<![\w.,])[−-]?\d+(?:[.,]\d+)*%?")
NUM_WORDS = ("two three four five six seven eight nine ten eleven twelve thirteen fourteen "
             "fifteen sixteen seventeen eighteen nineteen twenty hundred thousand million billion").split()
NUM_WORD_RE = re.compile(r"\b(" + "|".join(NUM_WORDS) + r")\b", re.I)

HEADING_CHANGES = {
    # old heading (or None for an insertion) -> (new heading, finding id)
    "### 3.1 The two surfaces, and why the count is exact":
        ("### 3.1 The two surfaces, and what the count is exact about", "Codex-1a"),
    "## 6. Instrument defects: reporting them is part of the contribution":
        ("## 6. Instrument defects: what an auditor of these numbers needs", "Codex#15"),
    None: ("### F-5 — 2026-10-05: two verified reviews of rc3, applied in rc4", "F-5(new)"),
}
FENCE_CHANGES = {
    # fenced block text -> (expected delta, finding id)
    "```\nb* = max over states  ( s(c_K) − s(d) )   <  ∞\n```": (-1, "Codex-5"),
}

EXPECTED_DELTA = {
    "0": 3, "0.02": 3, "0.043": 2, "0.0473": 3, "0.0946": 2, "0.16%": 1,
    "0.2": 2, "0.25": 4, "0.4": 1, "0.5": 5, "0.59": 3, "0.69": 7,
    "0.7": 2, "0.73%": 3, "0.8": 2, "0.874": 2, "0.9": 1, "0.90": 3,
    "00": 2, "01": 1, "02": 3, "03": 3, "04": 8, "05": 21,
    "07": 3, "08": 24, "09": 9, "1": 18, "1,024": 1, "1,056": 1,
    "1,139": 1, "1,197": 2, "1,635": 3, "1,656": 4, "1,787": 2, "1,971": 2,
    "1.0": 1, "1.18%": -2, "1.79": 2, "10": 38, "10,926": 2, "100": 1,
    "100%": 2, "1014": 1, "1019": 1, "102": 1, "104": 2, "108": 4,
    "11": 3, "112": 1, "119": 3, "12": 2, "12.96%": 1, "123": -1,
    "124": -1, "126": -1, "128": -1, "13": 4, "131": -1, "14": 4,
    "144": 1, "149": 4, "15": 2, "15.87%": -1, "152": 1, "16": 1,
    "17": 7, "175": -1, "176": -1, "178": -1, "18": 2, "181": -1,
    "183": -1, "186": 1, "196": 2, "2": 7, "2,058": 1, "20": 5,
    "20.5": 2, "20.72%": 1, "200": 3, "201": 1, "2026": 62, "21": 4,
    "212": 1, "22": 3, "22%": 2, "22,52": 1, "220": -1, "23": 6,
    "238": 1, "25": 2, "26": 9, "26.7%": 2, "269": 1, "27": 5,
    "277": 1, "28": 6, "28.66%": -1, "280": 3, "288": 2, "29": 5,
    "29.7%": 1, "297": 1, "3": 6, "3.1": 4, "3.3": 1, "3.67": 1,
    "30": 3, "30.6%": 1, "31": -1, "311": 1, "322": 1, "325": 1,
    "327": 4, "33": 1, "34": 2, "344": 1, "35": 3, "350": 11,
    "359": 1, "365": 2, "37": 1, "39,130": 2, "396": 1, "398": 1,
    "4": 9, "4.0": 1, "4.1": 3, "4.1.1": 2, "4.12%": 1, "4.2": 4,
    "4.3": 1, "4.3.1": 14, "4.3.2": 10, "4.4": 7, "4.5": 1, "4.66%": -1,
    "40": 2, "42": 4, "43": 2, "44": 9, "45": 3, "46": 11,
    "462": 1, "466": 2, "47": 4, "472": 2, "5": 4, "5,376": 1,
    "5.3": 6, "5.4": 5, "5.5": 2, "5.6": 2, "5.7": 1, "5.7.1": 5,
    "5.7.2": 1, "50": 2, "500": 1, "51": 1, "52": 8, "53": 1,
    "54": 2, "56": 2, "56,288": 2, "57": 3, "579": 1, "58": 1,
    "583,763": 2, "59": 2, "6": 8, "6.2": 1, "61": 1, "616": 1,
    "663": 1, "67,187": 2, "672": 3, "676": 1, "68": 1, "7": 3,
    "71": 1, "749": 1, "76": 4, "77": 2, "78": 1, "79": 4,
    "8": 3, "8.17": 1, "8.2": 1, "87": 2, "89": 1, "9": 8,
    "9,755": 1, "91": 1, "917": 1, "944": 1, "951": 1, "96": 1,
    "98": 2, "99.98%": 1, "five": 3, "nine": 1, "three": 9, "twelve": -1,
    "two": 12,
    "24": 2,  # CHECK D-A1 (2026-10-05)
    "95": 1,  # CHECK D-A1 (2026-10-05)
}
REGISTRY = [
    ["GLM-5", "new", "it exhausts the eligible pool at 100% on every m", 0],
    ["REV#5+Kimi-3+Kimi-1", "new", "> 7,908 (81%) of §4.3.2; the 5.6× partial-day re", 0],
    ["Codex#16", "new", "(The 99.98% expected coverage under uniform rand", 0],
    ["Codex-1e(abstract)", "new", "the system: 9,755 of the 10,899 exposed chunks h", 0],
    ["Codex-2+REV#8(superseded)+Kimi-3", "new", "sent in 100% of the 4,632 briefs of the week occ", 0],
    ["GLM-2+REV#5(abstract)", "new", "two path patterns together with the channel's im", 0],
    ["REV#7(abstract)", "new", "designed to compensate for the main pool, respon", 0],
    ["REV#3(abstract)", "new", "4.86% of briefs (measured on the 2026-08-26 corp", 0],
    ["Codex-4(abstract)", "new", "order and a bonus on the subordinate coordinate ", 0],
    ["Codex-1e(l.91)", "new", "First, of the 10,899 exposed chunks, 9,755 have ", 0],
    ["REV#12(§1)", "new", "set from 2026-08-24 to 2026-09-19) from 5,376 ma", 0],
    ["REV#3(§1)", "new", ".0, 4.4]`, with a ceiling of 4.86% of briefs (me", 0],
    ["GLM-2(§1 gap)", "new", "is governed by an eligibility predicate (two pat", 0],
    ["GLM-2(§1 contrib)", "new", "ks (0.16% of the corpus), cut by path patterns, ", 0],
    ["REV#6", "old", "**Caveat.** State explicitly that it is one syst", 0],
    ["Codex-1a", "new", "### 3.1 The two surfaces, and what the count is ", 0],
    ["Codex-1b", "new", "Both instruments cover the period from the start", 0],
    ["Codex-1c", "new", "Hence the historical union of 11,051 is not a bo", 0],
    ["Kimi-13a", "new", "`brief.ts`, `brief-diversity.ts`, `salience.ts` ", 0],
    ["Codex-1d", "new", "the historical brief with live search and is not", 0],
    ["GLM-2(l.410)", "new", "and what keeps them from reaching it is the elig", 0],
    ["REV#9+Codex#7", "new", "The young cohorts do not drive the headline. The", 0],
    ["Codex#16(§4.1.1)", "new", "this is why the uniform counterfactual (99.98%, ", 0],
    ["Codex-1e(l.471)", "new", "he 10,899 live chunks already exposed, 9,755 hav", 0],
    ["Codex#11", "new", "system delivered. For live chunks the two contri", 0],
    ["REV#5(§4.3.1)", "new", " to the quantity, and disappears the next day. (", 0],
    ["REV#10", "new", "same 108 ids (spanning 308214 to 308496, not con", 0],
    ["REV#11", "new", "with it the tie structure that sets the ceiling)", 0],
    ["Kimi-8", "new", "slots in 100% of the briefs of each day with row", 0],
    ["REV#14", "new", "distinct chunks, every measurable day from 2026-", 0],
    ["Codex-3", "new", "Recency is `2^(−age/retention)`, with age measur", 0],
    ["Kimi-3(dates)", "new", "(The dates are read from a copy of the 2026-09-0", 0],
    ["Codex-2(l.901)", "new", "zeroing the access component takes them from 1/3", 0],
    ["Codex-2(table)", "new", "| 116467 | 0.80 | 1.00 | 911 | **1** | **44–46**", 0],
    ["Codex-2(l.910)", "new", "zero, through the production function `calculate", 0],
    ["Codex-2(l.931)", "new", "(`RECON-52-e-sondas-2026-10-04.json` for the res", 0],
    ["Codex-2(l.946)+Kimi-3+D-A2", "new", "not unique. Between 22 and 44 other chunks", 0],
    ["D-A1", "new", "with no access history at all (`prod_noacc`, which", 0],
    ["D-A3", "new", "`out/TIEBREAK-EXPOSURE-PROD-SHARED-2026-10-05.json`, the same run with", 0],
    ["D-A3(App D row)", "new", "(`--shared-plus 1` for the second file)", 0],
    ["F-5(D-A1..3)", "new", "- Independent check of rc4 (`_sprint-2026-10-04/CHECK-A-rc4-B-rc4.md`, D-A1 to D-A3)", 0],
    ["REV#7+#3(table)", "new", " regime, §4.3.1); **lexicographic** order | **on", 0],
    ["REV#7(§4.3.2)", "new", "designed to compensate for the main pool, respon", 1],
    ["Kimi-10", "new", "the fraction of briefs in which the cut of the c", 0],
    ["Codex#6", "new", "`w ∈ (4.0, 4.4]`: on a fine grid of 23 doses (0.", 0],
    ["Codex-14b", "new", "The quantity that governs is distance, not step,", 0],
    ["Codex#9", "new", "d on 2026-08-27, 325 of 343 rows (94.8%) fall wi", 0],
    ["Codex-4(§5)", "new", "form, serving a prefix of one lexicographic orde", 0],
    ["Kimi-11", "new", "`if (freshGot >= freshSlots || picked.length >= ", 0],
    ["Codex-4(l.1158)", "new", "The derivation assumes that the coverage pool se", 0],
    ["REV#2", "new", "dominant coordinate. In nox-mem these are the st", 0],
    ["Codex-5+Codex#6", "new", "um that crosses the cut, the order is by `−s_b`,", 0],
    ["Codex-14", "new", "1}))`, the largest step between adjacent items a", 0],
    ["GLM-7", "new", "| the **capacity** `K` | moves the cut along the", 0],
    ["Codex-5(b* row)", "new", "e~~ | bounded by Corollary 2, saturating at a fi", 0],
    ["Kimi-4(§5.6)", "new", "`FRESH_CANDIDATE_POOL` and `GLOBAL_FRESH_PATTERN", 0],
    ["Kimi-3(strata)", "new", "distinct strata (counts not preserved in any art", 0],
    ["Codex#8", "new", "With 8 alternatives, two of the nine results sha", 0],
    ["REV#4(recompute)", "new", "ience`, the comparator does not separate them; t", 0],
    ["REV#4(survives)", "new", "on the comparator's key the exposure grows 28–35", 0],
    ["GLM-3", "new", "The field came into existence in the 104 seconds", 0],
    ["Codex#15(heading)", "new", "## 6. Instrument defects: what an auditor of the", 0],
    ["Codex#15(intro)", "new", "This section serves contribution (iv), the execu", 0],
    ["REV#13", "new", "nalysis stratum of the interventional study, whe", 0],
    ["Kimi-4(§6 table)", "new", "(the coverage pool is not returned by any export", 0],
    ["Codex#12", "new", "subject to any window. Eligibility excludes but ", 0],
    ["Codex-4(§7)", "new", "der and a bonus on the subordinate coordinate th", 1],
    ["GLM-4+Codex#10", "new", "- in the windows from which this paper's rates a", 0],
    ["Codex#13", "new", "> That literature presupposes that exposure resp", 0],
    ["REV#1(l.1861)", "new", "the brief served 1,635 distinct live chunks (1,7", 0],
    ["DeepSeek#1(§9)", "new", "through the `slots/distinct` ratio (printed then", 0],
    ["GLM-2(§9)", "new", "and the two patterns of `GLOBAL_FRESH_PATTERNS`,", 0],
    ["REV#3(§9)", "new", "and whose value, 4.86% under the conventions in ", 0],
    ["REV#7+#1(§9)", "new", "designed to compensate for the main pool, respon", 2],
    ["Codex-4(§9)", "new", "and a bonus on the subordinate coordinate that s", 2],
    ["Codex#10(App A)", "new", "depends on the trial having run: the surface cen", 0],
    ["GLM-6", "new", "**closed** on 2026-08-26: the seed declaration w", 0],
    ["Kimi-6", "new", "The full list of deviations lives in `DEVIATIONS", 0],
    ["GLM-1(intro)", "new", "Scripts are in `measurement/`, except `claims_ch", 0],
    ["GLM-1(intro)", "new", "`A-recon/RECON-52-e-sondas-2026-10-04.json`; `A-recon/ORGANICO", 0],
    ["REV#4(App D row)", "new", "| exposure to arbitrary tie-breaking on the comp", 0],
    ["Kimi-2", "new", "e-tamanho.py` · `robustez-tamanho-exposicao.py -", 0],
    ["Codex-2(App D row)", "new", "| top-of-pool counterfactual, production salienc", 0],
    ["Kimi-1(a)", "new", "ort the diff. Measured before touching anything ", 0],
    ["Kimi-1(b)", "new", "§5 stayed between 8% and 17% (per-section counts", 0],
    ["Codex#15(App F)", "new", "The material serves the executable diagnostic (c", 0],
    ["DeepSeek#1(F-1a)", "new", "with 325 printed, though the locked numbers give", 0],
    ["DeepSeek#1(F-1b)", "new", "`slots / distinct` ratio (325 as printed then; ≈", 0],
    ["REV#12(Open items)", "new", "(33 distinct chunks, 0.61% of the 5,376 main slo", 0],
    ["F-5(new)", "new", "### F-5 — 2026-10-05: two verified reviews of rc", 0],
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
    mutations = [
        ("number in untouched prose", "numbers",
         lambda t: t.replace("fleet of 6 agents: a proactive", "fleet of 7 agents: a proactive", 1)),
        ("heading changed", "headings",
         lambda t: t.replace("## 7. Threats to validity", "## 7. Threats to the validity", 1)),
        ("registered correction reverted (GLM-3)", "owners",
         lambda t: t.replace("in the 104 seconds between the two", "in the 98 seconds between the two", 1)),
    ]
    ok = True
    for name, expect, mut in mutations:
        m = mut(new)
        if m == new:
            print(f"SELFTEST: mutation '{name}' did not apply")
            ok = False
            continue
        got = {c for c, _ in check(old, m, verbose=False)}
        bit = expect in got
        print(f"SELFTEST mutation '{name}': fails on {sorted(got)} -> {'BITES' if bit else 'MISSED'}")
        ok &= bit
    print("SELFTEST OK" if ok else "SELFTEST FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
