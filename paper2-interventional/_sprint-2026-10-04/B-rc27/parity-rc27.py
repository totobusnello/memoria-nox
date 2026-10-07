#!/usr/bin/env python3
"""Parity check B-v2-rc26.md -> B-v2-rc27.md (Paper B, sprint 2026-10-04; rc27 2026-10-07).

rc27 closes the working list for the deposit and nothing else. The author's decision (recorded in
deposit/paperB/READY.md): the deposited text must not read as pending. Item 8 ("the deposit itself is
not done") closes as deposited, with the version DOI written as the SAME placeholder token the status
header carries (the deposit build replaces every occurrence); item 24 ("rc25 has not been reviewed")
closes by recording what was and was not read, and that the deposited package gets a final read by
Grok, Codex and Fable before publication (stated as planned, never as done). The other lines that read
as open (6, 7, 11, 13, 14, 16, 19, 21) get a dated rc27 note. Items are closed the way the list closes
items: title struck, history kept, a dated note appended.

Checks (exit 1 if any fails):
  A  byte parity: rc27 with its working list replaced by rc26's and its rc27 changelog block removed
     is byte-identical to rc26 (pinned sha). So the header and the body did not move.
  H  history kept: inside the working list, with every `~~` removed from both sides, rc26 -> rc27 is
     insertions only (word level: no deletion, no replacement), and every inserted run is dated rc27.
  B  carried locks: parity-rc26.py's whole check (pinned sha), run rc24/rc25 -> rc27, must fail with
     EXACTLY the declared set below and nothing else. Every declared failure is caused by the working
     list closings, the second placeholder (item 8) or changelog items 208-210. Dict literals inside
     messages are compared order-free.
  C  the closings: item 8 says it was deposited as version <build VERSION> of the registration record,
     with the placeholder; the placeholder occurs exactly PLACEHOLDER_COUNT times (read from
     build-package.py), once in the header and once in item 8, never in the changelog; item 24 carries
     the required statements and no claim that the final read happened; every item's title is struck;
     every open-sounding phrase (outside struck spans) is followed in its item by a closing arrow or an
     rc27 note (one declared exception: the wording of item 25's own closing); the items that need an
     rc27 note carry one; the open-line detector, run on rc26, flags exactly the items rc27 closes
     (positive control); the parity scripts item 24 names exist.
  D  changelog: one rc27 block after rc26's, items numbered 149..210, the block holding 208, 209, 210,
     saying that nothing else changes and no number moves.

Usage:  python3 parity-rc27.py | --report | --self-test     Reads; writes nothing.
"""
import ast
import difflib
import hashlib
import importlib.util
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPRINT = HERE.parent
P2 = SPRINT.parent
RC24F, RC25F, OLD, NEW = (SPRINT / f"B-v2-rc{n}.md" for n in (24, 25, 26, 27))
RC26 = SPRINT / "B-rc26" / "parity-rc26.py"
RC26_SHA = "6c353d955ed4e785973837ec2e4baf2422ff52d620173c14b1f981184f64d48e"
OLD_SHA = "368878bf7be6255c1469733747ad9ed81fb32c1d4794055ee4213821251533b3"
BUILD = P2 / "deposit" / "paperB" / "build-package.py"
PLACEHOLDER = "[VERSION-DOI]"
WL_OPEN = "\n## Working list: struck in the commit that closes it\n"
WL_CLOSE = "\n\n**Caveat.** Items 2 and 3"
CL26 = "\n\n**rc26: header for the deposit**"
CL27 = "\n\n**rc27: working list closed for the deposit**"
H_OPEN, H_CLOSE = "\n\n> **", "\n>\n> **Caveat.**"

assert hashlib.sha256(RC26.read_bytes()).hexdigest() == RC26_SHA, \
    "parity-rc26.py changed: the locks carried from it are no longer the ones rc26 ran"
_spec = importlib.util.spec_from_file_location("parity_rc26", RC26)
R26 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(R26)
flat, tail = R26.flat, R26.tail

# ------------------------------------------------------------------ B: what rc26's check must report, and only this
EXPECTED_RC26_FAILS = [
    "A: outside the header and the rc26 block, rc26 differs from rc25 at char 253053: 'th the caption title of §4.2 (item 11).\\n   *(rc27, 2026-10-07: the caveat is clo' vs \"th the caption title of §4.2 (item 11).\\n7. ~~**Related work** — Paper A's §8 cov\"",
    "B: rc25's check reports an undeclared failure: hunk rc24 (2838, 2837) rc25 (2797, 2798) has no ID: \"   *(rc27, 2026-10-07: the caveat is closed by item 11's rc8 note; the registere\"",
    "B: rc25's check reports an undeclared failure: hunk rc24 (2843, 2845) rc25 (2804, 2807) has no ID: '   full. *(rc27, 2026-10-07: neither check was done; both concern submission to '",
    "B: rc25's check reports an undeclared failure: hunk rc24 (2853, 2853) rc25 (2815, 2816) has no ID: '   the deposit itself is not done.)* → **Done, rc27 (2026-10-07)**: deposited as'",
    "B: rc25's check reports an undeclared failure: hunk rc24 (2878, 2878) rc25 (2841, 2841) has no ID: '11. ~~**Traceability of §4.7 and Figure B1**~~: save the `control` distribution '",
    "B: rc25's check reports an undeclared failure: hunk rc24 (2883, 2883) rc25 (2846, 2849) has no ID: '    §4.7 part stays open.)* → **Closed, rc27 (2026-10-07), as a declared gap**: '",
    "B: rc25's check reports an undeclared failure: hunk rc24 (2888, 2888) rc25 (2854, 2854) has no ID: \"13. ~~**Two computations rc2 declares as not done**~~: ~~the H1c MDE at the ITT'\"",
    "B: rc25's check reports an undeclared failure: hunk rc24 (2892, 2891) rc25 (2858, 2859) has no ID: '    → **Closed, rc27 (2026-10-07), the second not computed**: §4.6 declares the '",
    "B: rc25's check reports an undeclared failure: hunk rc24 (2895, 2894) rc25 (2863, 2863) has no ID: '    *(rc27, 2026-10-07: superseded; rc4, built on rc3, had the regression review'",
    "B: rc25's check reports an undeclared failure: hunk rc24 (2909, 2909) rc25 (2878, 2879) has no ID: '    not been reviewed. *(rc27, 2026-10-07: superseded; rc6, built on rc5, had th'",
    "B: rc25's check reports an undeclared failure: hunk rc24 (2956, 2955) rc25 (2926, 2926) has no ID: '    *(rc27, 2026-10-07: superseded; rc8, built on rc7, had the two full reads of'",
    "B: rc25's check reports an undeclared failure: hunk rc24 (2962, 2962) rc25 (2933, 2933) has no ID: '21. ~~**Review of rc9**~~: the washout switch, the multiplicity under both readi'",
    "B: rc25's check reports an undeclared failure: hunk rc24 (2964, 2964) rc25 (2935, 2937) has no ID: '    reviewed by any voice. → **Closed, rc27 (2026-10-07), superseded**: rc9 had '",
    "B: rc25's check reports an undeclared failure: hunk rc24 (2979, 2979) rc25 (2952, 2952) has no ID: '24. ~~**Review of rc11**~~: the census deviation, the stratum contrasts and the '",
    "B: rc25's check reports an undeclared failure: tail: rc14-rc25 changelog items are [203, 204, 205, 206, 207, 208, 209, 210]…, expected 149..206",
    "B: rc25's check reports an undeclared failure: tail: working list / changelog, with the declared insertions reverted and the rc25 block removed, is not byte-identical to rc24",
    "B: a declared rc25-check failure no longer occurs (stale declaration): tail: rc14-rc25 changelog items are [200, 201, 202, 203, 204, 205, 206, 207]…, expected 149..206",
    "C: the placeholder [VERSION-DOI] occurs 2x in rc26 and 1x in the header; exactly once, in the header, is required",
    "D: rc14-rc26 changelog items are [205, 206, 207, 208, 209, 210]…, expected 149..207",
    "D: the rc26 block does not hold exactly item 207, the header rewrite",
]

# ------------------------------------------------------------------ C: the closings
ITEM8_MUST = "deposited as version {v}\n of the registration record, version DOI `[VERSION-DOI]`."
ITEM24_MUST = [
    "→ **Closed, rc27 (2026-10-07)**: rc24 had Fable's diff check (rc23 → rc24), GO.",
    "rc25 changes wording only and rc26 changes only the status header (and adds its changelog block); "
    "neither had a read of its own, and each passed a parity check against its predecessor "
    "(`B-rc25/parity-rc25.py`, `B-rc26/parity-rc26.py`).",
    "rc27 changes only this working list and the changelog (`B-rc27/parity-rc27.py`).",
    "The deposited package gets a final read by Grok, Codex and Fable before publication.",
]
# a final read stated as having happened (in the rc27 additions)
CLAIM_DONE = [r"\b(Grok|Codex|Fable)\b[^.]*\b(gave|returned|found|reported)\b",
              r"\bhad (a|the|its) final read\b", r"\bfinal read\b[^.]*\b(was|were) (done|run|made)\b",
              r"\b(Grok|Codex|Fable)\b(?![^.]*\bdiff\b)[^.]*\bGO\b", r"\bafter publication\b"]
OPEN_RE = re.compile(r"ha(s|ve)\s+not\s+been\s+reviewed|not\s+done|stays\s+open|still\s+open|still\s+reads|"
                     r"before\s+submission|before\s+deposit|blocks\s+the\s+deposit|pending|not\s+run", re.I)
CLOSER_RE = re.compile(r"→ \*\*(Done|Closed)|\*\(rc27, 2026-10-07|rc27 \(2026-10-07\)")
OPEN_OK = {(25, "not run")}                         # item 25's own closing: "attempted, gates failed, not run"
NEED_RC27 = {6, 7, 8, 11, 13, 14, 16, 19, 21, 24}   # the items rc27 closes or annotates
ITEM_COUNT = 25
SCRIPTS_NAMED = [SPRINT / "B-rc25" / "parity-rc25.py", SPRINT / "B-rc26" / "parity-rc26.py", HERE / "parity-rc27.py"]


def _norm(msg):
    def sub(m):
        try:
            d = ast.literal_eval(m.group(0))
        except Exception:
            return m.group(0)
        return repr(sorted(d.items())) if isinstance(d, dict) else m.group(0)
    return re.sub(r"\{[^{}]*\}", sub, msg)


def wl_bounds(t):
    i, j = t.find(WL_OPEN), t.find(WL_CLOSE)
    assert 0 <= i < j, "working list bounds not found"
    return i, j


def items(t):
    i, j = wl_bounds(t)
    out = {}
    for it in re.split(r"\n(?=\d+\. )", t[i:j])[1:]:
        out[int(it.split(".", 1)[0])] = it
    return out


def open_lines(t):
    """Items with an open-sounding phrase (outside struck spans) not followed by a closing in the item."""
    bad = {}
    for n, it in items(t).items():
        s = re.sub(r"~~.*?~~", lambda m: " " * len(m.group(0)), it, flags=re.S)
        for m in OPEN_RE.finditer(s):
            if (n, flat(m.group(0)).lower()) in OPEN_OK:
                continue
            if not CLOSER_RE.search(s, m.end()):
                bad.setdefault(n, []).append(flat(m.group(0)))
    return bad


def build_consts():
    b = BUILD.read_text(encoding="utf-8")
    v = re.search(r'^VERSION = "([^"]+)"', b, re.M)
    c = re.search(r"^PLACEHOLDER_COUNT = (\d+)", b, re.M)
    return (v.group(1) if v else None), (int(c.group(1)) if c else None)


def check(rc24, rc25, old, new, verbose=True, report=False, consts=None):
    fails = []
    bver, bcount = consts or build_consts()
    if hashlib.sha256(old.encode()).hexdigest() != OLD_SHA:
        fails.append("rc26 is not the 368878bf… bytes rc26's parity passed on")
    # A: byte parity outside the working list and the rc27 block
    try:
        oi, oj = wl_bounds(old)
        ni, nj = wl_bounds(new)
    except AssertionError as e:
        return fails + [f"A: {e}"]
    k = new.find(CL27)
    if k < 0:
        fails.append("D: the rc27 changelog block is missing")
        k = len(new)
    elif not new.endswith("\n"):
        fails.append("D: rc27 does not end with a newline")
    reverted = new[:ni] + old[oi:oj] + new[nj:k] + ("\n" if k < len(new) else "")
    if reverted != old:
        a, b = reverted, old
        n = next((x for x in range(min(len(a), len(b))) if a[x] != b[x]), min(len(a), len(b)))
        fails.append(f"A: outside the working list and the rc27 block, rc27 differs from rc26 at char {n}: "
                     f"{a[max(0, n - 40):n + 40]!r} vs {b[max(0, n - 40):n + 40]!r}")
    # H: history kept: insertions only (after removing strike marks), each inserted run dated rc27
    ow, nw = old[oi:oj].replace("~~", "").split(), new[ni:nj].replace("~~", "").split()
    ins = []
    for op, a1, a2, b1, b2 in difflib.SequenceMatcher(None, ow, nw, autojunk=False).get_opcodes():
        if op in ("delete", "replace"):
            fails.append(f"H: working-list text of rc26 removed or rewritten: {' '.join(ow[a1:a2])[:120]!r} -> "
                         f"{' '.join(nw[b1:b2])[:120]!r}")
        elif op == "insert":
            ins.append(" ".join(nw[b1:b2]))
    for run in ins:
        if "rc27" not in run or "2026-10-07" not in run:
            fails.append(f"H: an inserted run is not a dated rc27 note: {run[:120]!r}")
    added = " ".join(ins)
    # B: rc26's whole check, rc24/rc25 -> rc27, must fail with exactly the declared set
    got = R26.check(rc24, rc25, new, verbose=False)
    gn, en = {_norm(x) for x in got}, {_norm(x) for x in EXPECTED_RC26_FAILS}
    for x in sorted(gn - en):
        fails.append(f"B: rc26's check reports an undeclared failure: {x[:220]}")
    for x in sorted(en - gn):
        fails.append(f"B: a declared rc26-check failure no longer occurs (stale declaration): {x[:220]}")
    # C: the closings
    its = items(new)
    if sorted(its) != list(range(1, ITEM_COUNT + 1)):
        fails.append(f"C: working list items are {sorted(its)}, expected 1..{ITEM_COUNT}")
    for n, it in its.items():
        if not it.startswith(f"{n}. ~~"):
            fails.append(f"C: item {n}'s title is not struck")
    hi, hj = new.find(H_OPEN), new.find(H_CLOSE)
    i8 = its.get(8, "")
    blk = new[k:]
    if bcount is None:
        fails.append("C: build-package.py has no PLACEHOLDER_COUNT")
    if (new.count(PLACEHOLDER), new[hi:hj].count(PLACEHOLDER), i8.count(PLACEHOLDER), blk.count(PLACEHOLDER)) != (bcount, 1, 1, 0):
        fails.append(f"C: placeholder {new.count(PLACEHOLDER)}x in rc27 (build expects {bcount}), "
                     f"{new[hi:hj].count(PLACEHOLDER)}x in the header, {i8.count(PLACEHOLDER)}x in item 8, "
                     f"{blk.count(PLACEHOLDER)}x in the rc27 block; required: {bcount}, 1, 1, 0")
    if bver is None or flat(ITEM8_MUST.format(v=bver)) not in flat(i8):
        fails.append(f"C: item 8 does not close as deposited as version {bver} of the registration record "
                     "with the placeholder")
    f24 = flat(its.get(24, ""))
    for s in ITEM24_MUST:
        if flat(s) not in f24:
            fails.append(f"C: item 24 statement missing: {s[:90]!r}")
    for pat in CLAIM_DONE:
        m = re.search(pat, flat(added) + " " + flat(blk))
        if m:
            fails.append(f"C: the rc27 text states the final read as done: {m.group(0)[:100]!r}")
    for n, hits in sorted(open_lines(new).items()):
        fails.append(f"C: item {n} still reads as open: {hits}")
    for n in sorted(NEED_RC27):
        if "rc27" not in its.get(n, ""):
            fails.append(f"C: item {n} has no rc27 note")
    ctrl = set(open_lines(old))
    if ctrl != NEED_RC27:
        fails.append(f"C: positive control: the detector flags {sorted(ctrl)} in rc26, expected {sorted(NEED_RC27)}")
    for p in SCRIPTS_NAMED:
        if not p.exists():
            fails.append(f"C: item 24 names {p.relative_to(SPRINT)}, which does not exist")
    # D: changelog
    tn = tail(new)
    i = tn.find("\n**rc14: writing pass**")
    nums = [int(x) for x in re.findall(r"^(\d+)\. ", tn[i:] if i >= 0 else "", re.M)]
    if nums != list(range(149, 211)):
        fails.append(f"D: rc14-rc27 changelog items are {nums[-6:]}…, expected 149..210")
    if k > len(new) - 1 or new.find(CL26) > k:
        fails.append("D: the rc27 block is not after the rc26 block")
    if [int(x) for x in re.findall(r"^(\d+)\. ", blk, re.M)] != [208, 209, 210]:
        fails.append("D: the rc27 block does not hold exactly items 208, 209, 210")
    fb = flat(blk)
    for s in ("the status header and everything else in the text are rc26 byte for byte",
              "no number of the analysis or of the sham results moves",
              "208. Working list 8 (deposit)", "209. Working list 24", "210. Working list, other lines"):
        if flat(s) not in fb:
            fails.append(f"D: the rc27 block does not say {s!r}")
    if verbose:
        print(f"A: rc27 minus working list and rc27 block == rc26: {reverted == old}")
        print(f"H: working list rc26 -> rc27: {len(ins)} inserted runs, all dated rc27: "
              f"{all('rc27' in r and '2026-10-07' in r for r in ins)}")
        print(f"B: rc26's check on rc24/rc25 -> rc27: {len(got)} failures, declared {len(EXPECTED_RC26_FAILS)}, "
              f"undeclared {len(gn - en)}, stale {len(en - gn)}")
        print(f"C: placeholder {new.count(PLACEHOLDER)}x (build PLACEHOLDER_COUNT {bcount}); build VERSION {bver}; "
              f"open lines rc26 {sorted(ctrl)} -> rc27 {sorted(open_lines(new))}")
        print(f"words: rc26 {len(old.split())}, rc27 {len(new.split())}")
    if report:
        print("\nrc26's check on rc24/rc25 -> rc27:")
        for x in got:
            print("  ", x[:220])
    return fails


def main():
    rc24, rc25, old, new = (p.read_text(encoding="utf-8") for p in (RC24F, RC25F, OLD, NEW))
    if "--self-test" in sys.argv:
        return self_test(rc24, rc25, old, new)
    f = check(rc24, rc25, old, new, verbose=True, report="--report" in sys.argv)
    for x in f:
        print("FAIL", x)
    print("PARITY: PASS" if not f else f"PARITY: FAIL ({len(f)})")
    return 0 if not f else 1


def self_test(rc24, rc25, old, new):
    consts = build_consts()
    rep1 = lambda a, b: (new.replace(a, b, 1), a in new)  # noqa: E731
    mutations = [
        ("A: a word in the header", rep1("This text is version 2.0 of the", "This text is version 2.0 in the")),
        ("A: body number moved (H1c p)", rep1("`p = 0.4006`", "`p = 0.4106`")),
        ("A: a changelog item of rc26 edited", rep1("207. Status header: rewritten for the deposit.",
                                                    "207. Status header: rewritten for deposit.")),
        ("H: working-list history deleted", rep1("the deposit itself is not done.)*", ")*")),
        ("H: working-list history reworded", rep1("rc5 itself has\n    not been reviewed.", "rc5 itself was\n    not reviewed.")),
        ("H: undated insertion", rep1("**Done, 2026-09-22**: 20 artifacts", "**Done, 2026-09-22**: all 20 artifacts")),
        ("C: item 8 placeholder replaced by a DOI", rep1("version DOI `[VERSION-DOI]`.", "version DOI `10.5281/zenodo.1`.")),
        ("C: item 8 says version 2.1", rep1("deposited as version 2.0\n", "deposited as version 2.1\n")),
        ("C: placeholder written in the rc27 block", rep1("written as the same placeholder token", "written as `[VERSION-DOI]`")),
        ("C: final read claimed as done", rep1("before publication.\n25.", "before publication. The package had a final read.\n25.")),
        ("C: Grok verdict claimed", rep1("before publication.\n25.", "before publication. Grok gave GO.\n25.")),
        ("C: item 24 omits rc26", rep1("and rc26 changes only the status header (and adds its changelog block);\n    neither",
                                       ";\n    neither")),
        ("C: item 14 note removed", rep1("\n    *(rc27, 2026-10-07: superseded; rc4, built on rc3, had the regression review of item 16.)*", "")),
        ("C: item 21 title unstruck", rep1("21. ~~**Review of rc9**~~:", "21. **Review of rc9**:")),
        ("D: item 210 dropped", (new[:new.find("\n210. Working list")] + "\n", True)),
        ("D: 'no number moves' dropped", rep1("and no number of the\nanalysis or of the sham results moves", "and the rest is unchanged")),
        ("D: rc27 block removed", (new[:new.find(CL27)] + "\n", True)),
    ]
    ok = True
    for name, (mut, applied) in mutations:
        assert applied and mut != new, f"mutation did not apply: {name}"
        leg = name.split(":")[0]
        f = [x for x in check(rc24, rc25, old, mut, verbose=False, consts=consts) if x.startswith(leg + ":")]
        print(f"mutation [{name}]: {'CAUGHT' if f else 'MISSED'}" + (f" -> {f[0][:140]}" if f else ""))
        ok &= bool(f)
    for name, c in (("C: build PLACEHOLDER_COUNT 1", (consts[0], 1)), ("C: build VERSION 2.1", ("2.1", consts[1])),
                    ("C: build PLACEHOLDER_COUNT missing", (consts[0], None))):
        f = [x for x in check(rc24, rc25, old, new, verbose=False, consts=c) if x.startswith("C:")]
        print(f"mutation [{name}] (integrity): {'CAUGHT' if f else 'MISSED'}" + (f" -> {f[0][:140]}" if f else ""))
        ok &= bool(f)
    base = check(rc24, rc25, old, new, verbose=False, consts=consts)
    print(f"unmutated rc27: {'PASS' if not base else 'FAIL'}" + (f" -> {base}" if base else ""))
    print(f"mutations: {len(mutations) + 3}")
    return 0 if ok and not base else 1


if __name__ == "__main__":
    sys.exit(main())
