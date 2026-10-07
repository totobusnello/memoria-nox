#!/usr/bin/env python3
"""Parity check B-v2-rc25.md -> B-v2-rc26.md (Paper B, sprint 2026-10-04; rc26 2026-10-07).

rc26 is the deposit header and nothing else. The author's decisions for the deposit (recorded in
deposit/paperB/READY.md): the deposited text must not read "STATUS: DRAFT", "has not been
reviewed" or "still not done: deposit"; it states that it is version 2.0 of the pre-registration
record (concept DOI as in the v1.12 snapshot), that two model families reviewed it in full with GO
(Fable on rc23 and on the rc23 -> rc24 diff; Codex on rc23, receipt in receipts/), and carries ONE
placeholder token for the version DOI, which the deposit build substitutes.

Checks (exit 1 if any fails):
  A  byte parity: rc26 with its header replaced by rc25's header and its rc26 changelog block
     removed is byte-identical to rc25 (pinned sha). So nothing outside the header and the block moved.
  B  carried locks: parity-rc25.py's whole check (pinned sha), run rc24 -> rc26, must fail with
     EXACTLY the declared set below and nothing else. Every declared failure is caused by the header
     rewrite (old status marks, numbers, struck spans, DOIs, hedges and qualifiers that lived only in
     the old header) or by changelog item 207. A new failure, or a declared one that no longer
     occurs, fails rc26. Dict literals inside messages are compared order-free (set order varies).
  C  the new header: the placeholder occurs exactly once in the whole text, inside the header, and
     nowhere else; no "DRAFT", "has not been reviewed", "not done"; concept DOI and v1.12 DOI equal
     the v1.12 snapshot (B-rc18/zenodo-22110203-record.json); the Codex receipt named exists in
     receipts/ with `exit: 0` and the rc23 Codex verdict file says GO; the version in the header is
     the VERSION of deposit/paperB/build-package.py; the facts carried from the rc25 header
     (9.991/§4.7, 11,812 states of 18 epochs, job-janela2 completion stamp, 21/21) are still there.
  D  changelog: one rc26 block after rc25's, items numbered 149..207, item 207 only, naming the
     header and that nothing else changes.

Usage:  python3 parity-rc26.py | --report | --self-test     Reads; writes nothing.
"""
import ast
import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPRINT = HERE.parent
P2 = SPRINT.parent
RC24F, OLD, NEW = SPRINT / "B-v2-rc24.md", SPRINT / "B-v2-rc25.md", SPRINT / "B-v2-rc26.md"
RC25 = SPRINT / "B-rc25" / "parity-rc25.py"
RC25_SHA = "9564a6cb50fb12822b1e6dc2f7f6d14b5fe049805afe1010f81eb319272d3069"
OLD_SHA = "fba9fdda028a52d494c4d2b9c9bf0359580d8eced25de97fb4029ab9554ae511"
SNAP = SPRINT / "B-rc18" / "zenodo-22110203-record.json"
RECEIPT = SPRINT / "receipts" / "adversary-receipt-codex-2026-10-07T093115-73165.txt"
VERDICT = SPRINT / "REVIEW-B-rc23-codex-2026-10-07.md"
BUILD = P2 / "deposit" / "paperB" / "build-package.py"
PLACEHOLDER = "[VERSION-DOI]"
H_OPEN = "\n\n> **"
H_CLOSE = "\n>\n> **Caveat.**"
CL26 = "\n\n**rc26: header for the deposit**"

assert hashlib.sha256(RC25.read_bytes()).hexdigest() == RC25_SHA, \
    "parity-rc25.py changed: the locks carried from it are no longer the ones rc25 ran"
_spec = importlib.util.spec_from_file_location("parity_rc25", RC25)
R25 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(R25)
flat, body, tail = R25.flat, R25.body, R25.tail

# ------------------------------------------------------------------ B: what rc25's check must report, and only this
EXPECTED_RC25_FAILS = [
    "S22/W4: the status header no longer dates the draft 2026-09-21",
    "S24/F4: status sentence not in the form the files give: 'changed 790 of the 11,812 reconstructible brief states against 449–583 for 20 matched shams, `p = 1/21`'",
    "hedge: hunks [?] move hedge words by {'not': -14, 'no': -8, 'only': 1, 'could': -1, 'registered': -10, 'deposited': -3, 'sensitivity': -1, 'every': -3, 'any': -1, 'still': -2}; JUSTIFIED_HEDGE declares {}",
    "hedge: hunks [ST] move hedge words by {}; JUSTIFIED_HEDGE declares {'only': 1}",
    "hunk rc24 (3, 58) rc25 (3, 17) has no ID: '> **Status: version 2.0 of the pre-registration record.** This text is version 2'",
    "invariant: DOIs changed: {'10.5281/zenodo.22110203': 1, '10.5281/zenodo.21964093': 1}",
    "invariant: struck spans moved by {'~~still not done: **the valid sham replay** (§4.0.1c) and **deposit**~~': -1, '~~figures, related work, and deposit~~': -1}; rc25 declares {}",
    "numbers: token '09-20' removed 1x; JUSTIFIED_REMOVED declares 0x",
    "numbers: token '1' removed 1x; JUSTIFIED_REMOVED declares 0x",
    "numbers: token '1.12' added 1x is neither in rc24 nor derived",
    "numbers: token '10' removed 1x; JUSTIFIED_REMOVED declares 0x",
    "numbers: token '11,812' removed 1x; JUSTIFIED_REMOVED declares 0x",
    "numbers: token '115' removed 1x; JUSTIFIED_REMOVED declares 0x",
    "numbers: token '12:01Z' removed 1x; JUSTIFIED_REMOVED declares 0x",
    "numbers: token '14:01Z' removed 1x; JUSTIFIED_REMOVED declares 0x",
    "numbers: token '15' removed 1x; JUSTIFIED_REMOVED declares 0x",
    "numbers: token '17' removed 1x; JUSTIFIED_REMOVED declares 0x",
    "numbers: token '19' removed 2x; JUSTIFIED_REMOVED declares 0x",
    "numbers: token '20' removed 2x; JUSTIFIED_REMOVED declares 0x",
    "numbers: token '2026' removed 1x; JUSTIFIED_REMOVED declares 0x",
    "numbers: token '2026-08-17' removed 1x; JUSTIFIED_REMOVED declares 0x",
    "numbers: token '2026-09-09' removed 1x; JUSTIFIED_REMOVED declares 0x",
    "numbers: token '2026-09-21' removed 1x; JUSTIFIED_REMOVED declares 0x",
    "numbers: token '2026-10-04' removed 1x; JUSTIFIED_REMOVED declares 0x",
    "numbers: token '2026-10-05' removed 16x; JUSTIFIED_REMOVED declares 0x",
    "numbers: token '2026-10-06' removed 3x; JUSTIFIED_REMOVED declares 0x",
    "numbers: token '2026-10-07' removed 2x; JUSTIFIED_REMOVED declares 0x",
    "numbers: token '21' removed 1x; JUSTIFIED_REMOVED declares 0x",
    "numbers: token '449' removed 1x; JUSTIFIED_REMOVED declares 0x",
    "numbers: token '583' removed 1x; JUSTIFIED_REMOVED declares 0x",
    "numbers: token '60502' removed 1x; JUSTIFIED_REMOVED declares 0x",
    "numbers: token '790' removed 1x; JUSTIFIED_REMOVED declares 0x",
    "qualifier: 'excludes zero' occurs 31x in rc25 against 32x in rc24, not justified",
    "qualifier: 'in the registered analysis' occurs 11x in rc25 against 12x in rc24, not justified",
    "qualifier: 'not deposited' occurs 16x in rc25 against 17x in rc24, not justified",
    "status: header does not record \"rc22 prepared 2026-10-06 (Codex's final read\"",
    "status: header does not record 'adversary-receipt-codex-2026-10-06T133927-60502.txt'",
    "status: header does not record 'rc14 prepared 2026-10-05'",
    "status: header does not record 'rc15 prepared'",
    "status: header does not record 'rc16 prepared 2026-10-05 (review of rc15 applied:'",
    "status: header does not record 'rc17 prepared 2026-10-05 (review of rc16 applied:'",
    "status: header does not record 'rc18 prepared 2026-10-05'",
    "status: header does not record 'rc19 prepared 2026-10-05 (review of rc18 applied:'",
    "status: header does not record 'rc20 prepared 2026-10-06 (review of rc19 applied:'",
    "status: header does not record 'rc21 prepared 2026-10-06 (review'",
    "status: header does not record 'rc22 is the text frozen until the whole-window sham result is integrated'",
    "status: header does not record 'rc23 had two full reads, Fable and Codex, both GO with no MEDIUM or HIGH'",
    "status: header does not record 'rc23 prepared 2026-10-07 (the whole-window sham result integrated'",
    "status: header does not record 'rc24 changes wording only'",
    "status: header does not record 'rc24 had a diff check by Fable, rc23 → rc24, GO with three LOW in Appendix B and B.1'",
    "status: header does not record 'rc24 prepared 2026-10-07 (the LOW wording fixes of those two reads applied'",
    "status: header does not record 'rc25 has not been reviewed'",
    "status: header does not record 'rc25 prepared 2026-10-07 (those three LOW applied; rc25 changes wording only'",
    "tail: rc14-rc25 changelog items are [200, 201, 202, 203, 204, 205, 206, 207]…, expected 149..206",
]

# ------------------------------------------------------------------ C: the new header
HEADER_MUST = [
    "**Status: version 2.0 of the pre-registration record.**",
    "the DOI of this version is `[VERSION-DOI]`",
    "Versions 1.0 to 1.12 of the record are the registration and its amendments; this version reports the trial.",
    "The text was reviewed in full by two model families, both GO with no MEDIUM or HIGH: Fable read rc23 in full "
    "and checked the rc23 → rc24 diff, and Codex read rc23 in full (receipt "
    "`adversary-receipt-codex-2026-10-07T093115-73165.txt`, in `receipts/`).",
    "rc24 and rc25 apply the LOW findings of those reads and change wording only; rc26 changes only this header.",
    # carried from the rc25 header
    "Every number below is measured; §B names its artifact, and B.1 declares the one number (9.991, §4.7) held by no artifact.",
    "(11,812 reconstructible states of 18 epochs; job `job-janela2`, completed 2026-10-07T02:09:46Z, 21/21 runs validated)",
    "The v2 release candidates, rc3 to rc26, are listed in the changelog at the end.",
]
HEADER_FORBID = [r"DRAFT", r"has not been\s+reviewed", r"not\s+done", r"still not", r"not been\s+reviewed"]
CL_207 = "207. Status header: rewritten for the deposit."


def header(t):
    i = t.find(H_OPEN)
    j = t.find(H_CLOSE)
    assert 0 <= i < j, "header bounds not found"
    return i, j


def _norm(msg):
    def sub(m):
        try:
            d = ast.literal_eval(m.group(0))
        except Exception:
            return m.group(0)
        return repr(sorted(d.items())) if isinstance(d, dict) else m.group(0)
    return re.sub(r"\{[^{}]*\}", sub, msg)


def snapshot():
    d = json.loads(SNAP.read_text(encoding="utf-8"))
    return d["conceptdoi"], d["doi"]


def build_version():
    m = re.search(r'^VERSION = "([^"]+)"', BUILD.read_text(encoding="utf-8"), re.M)
    return m.group(1) if m else None


def check(rc24, old, new, verbose=True, report=False, receipt=None, verdict=None, snap=None, bver=None):
    fails = []
    receipt = RECEIPT.read_text(encoding="utf-8") if receipt is None else receipt
    verdict = VERDICT.read_text(encoding="utf-8") if verdict is None else verdict
    snap = snap or snapshot()
    bver = bver if bver is not None else build_version()
    if hashlib.sha256(old.encode()).hexdigest() != OLD_SHA:
        fails.append("rc25 is not the fba9fdda… bytes rc25's parity passed on")
    # A: byte parity outside the header and the rc26 block
    try:
        oi, oj = header(old)
        ni, nj = header(new)
    except AssertionError as e:
        return fails + [f"A: {e}"]
    k = new.find(CL26)
    if k < 0:
        fails.append("D: the rc26 changelog block is missing")
        k = len(new)
    elif not new.endswith("\n"):
        fails.append("D: rc26 does not end with a newline")
    reverted = new[:ni] + old[oi:oj] + new[nj:k] + ("\n" if k < len(new) and not new[nj:k].endswith("\n") else "")
    if reverted != old:
        a, b = reverted, old
        n = next((x for x in range(min(len(a), len(b))) if a[x] != b[x]), min(len(a), len(b)))
        fails.append(f"A: outside the header and the rc26 block, rc26 differs from rc25 at char {n}: "
                     f"{a[max(0, n - 40):n + 40]!r} vs {b[max(0, n - 40):n + 40]!r}")
    # B: rc25's whole check, rc24 -> rc26, must fail with exactly the declared set
    got = R25.check(rc24, new, verbose=False)
    gn, en = {_norm(x) for x in got}, {_norm(x) for x in EXPECTED_RC25_FAILS}
    for x in sorted(gn - en):
        fails.append(f"B: rc25's check reports an undeclared failure: {x[:200]}")
    for x in sorted(en - gn):
        fails.append(f"B: a declared rc25-check failure no longer occurs (stale declaration): {x[:200]}")
    # C: header
    head = new[ni:nj]
    fh = flat(head.replace("> ", " "))
    if new.count(PLACEHOLDER) != 1 or head.count(PLACEHOLDER) != 1:
        fails.append(f"C: the placeholder {PLACEHOLDER} occurs {new.count(PLACEHOLDER)}x in rc26 and "
                     f"{head.count(PLACEHOLDER)}x in the header; exactly once, in the header, is required")
    for s in HEADER_MUST:
        if flat(s) not in fh:
            fails.append(f"C: header sentence missing: {s[:80]!r}")
    for pat in HEADER_FORBID:
        if re.search(pat, fh):
            fails.append(f"C: header still says {pat!r}")
    concept, v112 = snap
    if f"concept DOI `{concept}`" not in fh or f"snapshot of v1.12, `{v112}`" not in fh:
        fails.append(f"C: header DOIs are not the v1.12 snapshot's (concept {concept}, v1.12 {v112})")
    if bver is None or f"version {bver} of the" not in fh:
        fails.append(f"C: header version does not match build-package.py VERSION ({bver})")
    if not re.search(r"^exit: 0$", receipt, re.M) or "voice: codex" not in receipt:
        fails.append("C: the named Codex receipt is not a codex receipt with exit: 0")
    if not re.search(r"^\*\*GO\*\*", verdict, re.M):
        fails.append("C: the rc23 Codex verdict file does not say GO")
    # D: changelog
    blk = new[k:] if k < len(new) else ""
    tn = tail(new)
    i = tn.find("\n**rc14: writing pass**")
    nums = [int(x) for x in re.findall(r"^(\d+)\. ", tn[i:] if i >= 0 else "", re.M)]
    if nums != list(range(149, 208)):
        fails.append(f"D: rc14-rc26 changelog items are {nums[-6:]}…, expected 149..207")
    if [int(x) for x in re.findall(r"^(\d+)\. ", blk, re.M)] != [207] or CL_207 not in blk:
        fails.append("D: the rc26 block does not hold exactly item 207, the header rewrite")
    fb = flat(blk)
    if "nothing else in the text changes" not in fb or "no number of the analysis or of the sham results moves" not in fb:
        fails.append("D: the rc26 block does not say that nothing else changes and no number moves")
    if PLACEHOLDER in blk:
        fails.append("D: the placeholder token is written in the changelog (it would be substituted there too)")
    if verbose:
        print(f"A: rc26 minus header and rc26 block == rc25: {reverted == old}")
        print(f"B: rc25's check on rc24 -> rc26: {len(got)} failures, declared {len(EXPECTED_RC25_FAILS)}, "
              f"undeclared {len(gn - en)}, stale {len(en - gn)}")
        print(f"C: placeholder {new.count(PLACEHOLDER)}x; concept {concept}; v1.12 {v112}; build VERSION {bver}")
        print(f"words: rc25 {len(old.split())}, rc26 {len(new.split())}; header {len(old[oi:oj].split())} -> {len(head.split())}")
    if report:
        print("\nrc25's check on rc24 -> rc26:")
        for x in got:
            print("  ", x[:220])
    return fails


def main():
    rc24, old, new = (p.read_text(encoding="utf-8") for p in (RC24F, OLD, NEW))
    if "--self-test" in sys.argv:
        return self_test(rc24, old, new)
    f = check(rc24, old, new, verbose=True, report="--report" in sys.argv)
    for x in f:
        print("FAIL", x)
    print("PARITY: PASS" if not f else f"PARITY: FAIL ({len(f)})")
    return 0 if not f else 1


def self_test(rc24, old, new):
    rcpt, verd, snap, bver = RECEIPT.read_text(encoding="utf-8"), VERDICT.read_text(encoding="utf-8"), snapshot(), build_version()
    kw0 = dict(receipt=rcpt, verdict=verd, snap=snap, bver=bver)
    rep1 = lambda a, b: (new.replace(a, b, 1), a in new)  # noqa: E731
    i, j = header(new)
    mutations = [
        ("C: placeholder removed", rep1("`[VERSION-DOI]`", "`10.5281/zenodo.0`")),
        ("C: placeholder doubled (also in the changelog)", rep1("as a single placeholder token", "as `[VERSION-DOI]`")),
        ("C: 'DRAFT' back in the header", rep1("**Status: version 2.0", "**STATUS: DRAFT; version 2.0")),
        ("C: 'has not been reviewed' back in the header", rep1("rc26 changes only this header.",
                                                                "rc26 changes only this header; rc26 has not been reviewed.")),
        ("C: concept DOI wrong", rep1("`10.5281/zenodo.21964093`, as recorded", "`10.5281/zenodo.21964094`, as recorded")),
        ("C: Codex read dropped", rep1(", and Codex read rc23 in full", "")),
        ("C: carried 21/21 dropped", rep1("21/21 runs\n> validated", "runs\n> validated")),
        ("A: body number moved (H1c p)", rep1("`p = 0.4006`", "`p = 0.4106`")),
        ("A: working-list line edited", rep1("the deposit itself is not done.)*", "the deposit is done.)*")),
        ("A: a word outside the header", rep1("This is Paper B of the split", "This is Paper B from the split")),
        ("D: item 207 renumbered", rep1("\n207. Status header", "\n208. Status header")),
        ("D: 'nothing else' sentence dropped", rep1("nothing else in the\ntext changes, and ", "")),
        ("D: rc26 block removed", (new[:new.find(CL26)] + "\n", True)),
        ("B: an undeclared qualifier delta in the header", (new[:i] + new[i:j].replace(
            "Figures (B1, B2), related work", "Figures (B1, B2), not deposited before, related work", 1) + new[j:], True)),
    ]
    ok = True
    for name, (mut, applied) in mutations:
        assert applied and mut != new, f"mutation did not apply: {name}"
        leg = name.split(":")[0]
        f = [x for x in check(rc24, old, mut, verbose=False, **kw0) if x.startswith(leg + ":")]   # caught by ITS leg
        print(f"mutation [{name}]: {'CAUGHT' if f else 'MISSED'}" + (f" -> {f[0][:140]}" if f else ""))
        ok &= bool(f)
    integ = [
        ("C: receipt exit 1", dict(kw0, receipt=rcpt.replace("\nexit: 0\n", "\nexit: 1\n", 1))),
        ("C: verdict NO-GO", dict(kw0, verdict=verd.replace("**GO**", "**NO-GO**", 1))),
        ("C: snapshot concept differs", dict(kw0, snap=("10.5281/zenodo.1", snap[1]))),
        ("C: build VERSION 2.1", dict(kw0, bver="2.1")),
    ]
    for name, kw in integ:
        f = [x for x in check(rc24, old, new, verbose=False, **kw) if x.startswith("C:")]
        print(f"mutation [{name}] (integrity): {'CAUGHT' if f else 'MISSED'}" + (f" -> {f[0][:140]}" if f else ""))
        ok &= bool(f)
    base = check(rc24, old, new, verbose=False, **kw0)
    print(f"unmutated rc26: {'PASS' if not base else 'FAIL'}" + (f" -> {base}" if base else ""))
    print(f"mutations: {len(mutations) + len(integ)}")
    return 0 if ok and not base else 1


if __name__ == "__main__":
    sys.exit(main())
