#!/usr/bin/env python3
"""Parity check B-v2-rc13.md -> B-v2-rc14.md (Paper B, sprint 2026-10-04; rc14 2026-10-05).

rc14 is a writing pass (avoid-ai-writing, mode edit, voice technical, context research paper)
over the prose changed since rc6 (the last writing pass) plus the Abstract and §9 in full
(`APPLY-B-rc14.md`). It changes wording only: no number, unit, interval, p-value, quotation,
code span, path, hash, citation, cross-reference, heading, table cell, struck span or changelog
line, and no claim moves.

Hunks (difflib on lines) must each carry an edit ID, assigned by an anchor substring of the rc14
hunk (E1..E12, one per edit listed in APPLY-B-rc14.md).

Checks (exit 1 if any fails):
  1. hunks: every hunk has an edit ID.
  2. invariants, rc13 -> rc14 multiset-equal: numeric tokens (rc11's tokenizer), § cross-references,
     code spans, italic quotations (*"..."*), straight-quoted strings, path-like tokens, citations,
     footnote markers, DOIs, struck spans (~~...~~), table lines, image links. Headings identical.
     The working list and the changelog (from "## Working list" to the end) byte-identical.
  3. SHAM-JANELA: 10 blocks byte-identical to rc13.
  4. carried locks: rc13's `claims_rc13` (which carries rc12's and rc11's locks (a)-(l)) is clean
     on rc14, and every headline of rc11, rc12 (minus the §7 "drifted" sentence rc13 rewrote) and
     rc13 is present.
  5. qualifier set: (a) every LOCKED phrase (the reviewers' qualifiers, rc13's census marks and
     every carried headline) occurs in rc14 exactly as many times as in rc13; (b) the multiset of
     hedge/qualifier words (HEDGE) over the body, struck text removed, is unchanged except for the
     deltas listed in JUSTIFIED, each with the edit that causes it and why no claim moves.
  6. carried integrity: rc11's script integrity (13), rc12's census record (14), rc13's B-censo
     paths and bridges (15).
  7. no REANALISE marker; bold balanced per paragraph.

Usage:  python3 parity-rc14.py | --report | --self-test     Reads; writes nothing.
"""
import collections
import hashlib
import importlib.util
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPRINT = HERE.parent
OLD = SPRINT / "B-v2-rc13.md"
NEW = SPRINT / "B-v2-rc14.md"
RC13 = SPRINT / "B-rc13" / "parity-rc13.py"
RC13_SHA = "89172df4780d4a3b9100803254a3be9be4ecae8f1332064f498bc6888278ba64"

assert hashlib.sha256(RC13.read_bytes()).hexdigest() == RC13_SHA, \
    "parity-rc13.py changed: the locks carried from it are no longer the ones rc13 ran"
_spec = importlib.util.spec_from_file_location("parity_rc13", RC13)
R13 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(R13)
R12, R11 = R13.R12, R13.R11

ANCHORS = [
    ("E1", "analysis specification, written on 2026-09-10 (ten days before the window closed and"),
    ("E2", "Our two statements about uncertainty, the planning power approximation and the realized"),
    ("E3", "test's non-rejection of the sharp null neither establishes absence of effect nor"),
    ("E4", "That ground holds: `09-02` is empty"),
    ("E5", "In the registered analysis there is no disagreement left to explain."),
    ("E6", "The same limit disciplines §4.3"),
    ("E6", "denominator argument, not to read those as findings. The limit applies to every"),
    ("E7", "may therefore be under-represented in every interval that uses stratum B"),
    ("E8", "linking it to an action opportunity. Those occurrences were approximately uniform across"),
    ("E9", "30-day window is a documented default. The two were never read against each other, and no"),
    ("E10", "then called M10 (§4.6), had no artifact at all; an ad-hoc script computed them, and they"),
    ("E11", "Several of these are outside the repository and several are large."),
]

# 5(a): qualifiers the reviewers fought over, plus the scope qualifiers that recur in the body
QUALIFIERS = [
    "deposited reading", "not robust", "not that the dose had no effect",
    "under the registered BCa construction only", "no contemporaneous record", "did not reproduce",
    "declared before its first call", "dated by our commit log", "not deposited", "undeposited",
    "planning definition", "does not reject", "did not reject", "not rejected", "contains zero",
    "contain zero", "excludes zero", "exclude zero", "may under-cover", "not been established",
    "not established", "descriptive only", "not a calibrated", "post-hoc", "pre-committed",
    "as far as we found", "approximately", "after unblinding", "point only", "by construction",
    "under either reading", "in the registered analysis", "in the sensitivity analysis",
    "under the switch", "not executed", "may have been", "would have", "non-rejection",
]
# 5(b): single-word hedges/qualifiers, counted case-insensitively over the body (struck text removed)
HEDGE = ["not", "no", "never", "neither", "nor", "cannot", "only", "may", "might", "could", "would",
         "approximately", "about", "almost", "nearly", "likely", "possibly", "indicative", "descriptive",
         "exploratory", "registered", "deposited", "undeposited", "sensitivity", "unless", "except",
         "alone", "without", "all", "every", "none", "any", "either", "still", "rather", "therefore"]
# deltas in 5(b) that an edit causes; (word, rc14 count − rc13 count) -> reason
JUSTIFIED = {
    ("neither", -1): "E9: 'Neither document was wrong' restated 'each number is correct in isolation' in the "
                     "preceding sentence and was cut. No claim moves.",
    ("alone", -1): "E9: the closer 'two locks that each look complete alone, with no step … whose job is to cross "
                   "them' became 'no step in the process had the job of crossing them'; 'each number is correct in "
                   "isolation' two sentences earlier carries 'alone'. No claim moves.",
    ("would", -1): "E5: the cut closing sentence 'We would rather have found this before an adversarial reviewer "
                   "told us the test was missing.' restated §4.0.1's opening ('Both were found by adversarial "
                   "review of this manuscript, not by us.'), which stands. No claim moves.",
    ("rather", -1): "E5: the same cut sentence ('We would rather have found this…'). No claim moves.",
    ("therefore", -1): "E8: 'the present measurement therefore does not test' became 'because they are not the "
                       "covered action opportunities…, the present measurement does not test': the inference is "
                       "kept as 'because'. No claim moves.",
}
# 'not' nets to zero: E3 removes one ('The primary test does not reject the sharp null.'), E8 adds one
# ('because they are not the covered action opportunities').
JUSTIFIED_PHRASE = {  # (phrase, rc14 count − rc13 count) -> reason
    ("does not reject", -1): "E3: the abstract's 'The primary test does not reject the sharp null.' restated its own "
                             "earlier 'the registered re-randomization test does not reject the sharp null for H1c' and "
                             "was folded into the next sentence as 'the primary test's non-rejection of the sharp null'. "
                             "No claim moves.",
    ("non-rejection", +1): "E3: the same fold: 'the primary test's non-rejection of the sharp null'. No claim moves.",
}
TABLE = re.compile(r"^\|.*\|\s*$", re.M)
STRUCK = re.compile(r"~~.*?~~", re.S)
STRAIGHT = re.compile(r'(?<![*\w])"[^"\n]{1,200}"(?![*\w])')
PATHLIKE = re.compile(r"[\w.\-]*/[\w.\-/…*{},]*\.(?:py|json|md|svg|png|ndjson|jsonl|sh|tgz|txt|ts|sha256|db)\b")
IMG = re.compile(r"!\[[^\]]*\]\([^)]*\)")
FOOT = re.compile(r"\[\^[^\]]+\]")


def flat(t):
    return " ".join(t.split())


def body(t):
    return t[:t.find("\n## Working list")]


def tail(t):
    return t[t.find("\n## Working list"):]


def hedge_counts(t):
    b = R11.strip_struck(body(t)).lower()
    words = collections.Counter(re.findall(r"[a-z][a-z\-]*", b))
    return {w: words.get(w, 0) for w in HEDGE}


def all_headlines(cz):
    import json
    itt = json.loads(R12.ART["ITT-2026-09-21"].read_text())
    reg = json.loads(R12.ART["ITT-REGISTRADO-v3"].read_text())
    chk = json.loads(R12.ART["checks-rc10"].read_text())
    f4 = json.loads(R12.ART["f4-w4"].read_text())
    f3 = json.loads(R12.ART["f3-abort"].read_text())
    heads = dict(R11.headline(reg, chk, f4, f3, itt))
    heads.update({"rc12 " + k: v for k, v in R12.headline_rc12(cz).items() if k != "drift §7"})
    heads.update({"rc13 " + k: v for k, v in R13.headline_rc13(cz).items()})
    return heads


CENSUS_MARKS = ["census adjudication of the live study", "An attempt to restore the census",
                "the deposited census of the live study", "post-unblinding attempt"]


def check(old, new, verbose=True, report=False, cz=None, st=None):
    cz = cz or R13.load_rc13()
    st = st or R13.load_paths()
    fails, rep = [], []
    # 1 hunks
    R11.ANCHORS[:] = ANCHORS
    hs = R11.hunks(old, new)
    for h in hs:
        if not h["ids"]:
            fails.append(f"hunk rc13 {h['rc10']} rc14 {h['rc11']} has no edit ID: {h['new'][:70]!r}")
    # 2 invariants
    inv = {
        "numeric tokens": (R11.numbers(old), R11.numbers(new)),
        "§ cross-references": (collections.Counter(m.group(0) for m in R11.SECREF.finditer(old)),
                               collections.Counter(m.group(0) for m in R11.SECREF.finditer(new))),
        "code spans": (collections.Counter(R11.CODE.findall(old)), collections.Counter(R11.CODE.findall(new))),
        "italic quotations": (collections.Counter(R11.QUOTE.findall(old)), collections.Counter(R11.QUOTE.findall(new))),
        "straight-quoted strings": (collections.Counter(STRAIGHT.findall(old)), collections.Counter(STRAIGHT.findall(new))),
        "path-like tokens": (collections.Counter(PATHLIKE.findall(old)), collections.Counter(PATHLIKE.findall(new))),
        "citations": (collections.Counter(R11.CITE.findall(old)), collections.Counter(R11.CITE.findall(new))),
        "footnote markers": (collections.Counter(FOOT.findall(old)), collections.Counter(FOOT.findall(new))),
        "DOIs": (collections.Counter(R11.DOI.findall(old)), collections.Counter(R11.DOI.findall(new))),
        "struck spans": (collections.Counter(STRUCK.findall(old)), collections.Counter(STRUCK.findall(new))),
        "table lines": (collections.Counter(TABLE.findall(old)), collections.Counter(TABLE.findall(new))),
        "image links": (collections.Counter(IMG.findall(old)), collections.Counter(IMG.findall(new))),
    }
    for name, (a, b) in inv.items():
        if a != b:
            d = {k: b[k] - a[k] for k in set(a) | set(b) if a[k] != b[k]}
            fails.append(f"invariant: {name} changed: {dict(list(d.items())[:4])}")
        rep.append(f"{name}: {sum(a.values())} -> {sum(b.values())}, multiset equal: {a == b}")
    if R11.headings(old) != R11.headings(new):
        fails.append("invariant: heading list changed")
    if tail(old) != tail(new):
        fails.append("invariant: working list / changelog not byte-identical to rc13")
    # 3 SHAM-JANELA
    so, eo = R11.sham_spans(old)
    sn, en = R11.sham_spans(new)
    fails += eo + en
    if len(sn) != R11.EXPECTED_SHAM or len(so) != R11.EXPECTED_SHAM:
        fails.append(f"sham: {len(sn)} blocks in rc14 and {len(so)} in rc13, expected {R11.EXPECTED_SHAM}")
    for i, (x, y) in enumerate(zip(so, sn), 1):
        if x != y:
            fails.append(f"sham: block {i} ({y.strip()[:50]!r}…) is not byte-identical to rc13")
    # 4 carried locks and headlines
    fails += R13.claims_rc13(new, cz)
    heads = all_headlines(cz)
    fn = flat(new)
    for k, v in heads.items():
        if flat(v) not in fn:
            fails.append(f"headline: {k} — expected text {v!r} not found in rc14")
    # 5 qualifier set
    fo = flat(old)
    locked = list(dict.fromkeys(QUALIFIERS + CENSUS_MARKS + [flat(v) for v in heads.values()]))
    pdeltas = {}
    for ph in locked:
        a, b = fo.count(ph), fn.count(ph)
        if a != b:
            pdeltas[ph] = b - a
            if (ph, b - a) not in JUSTIFIED_PHRASE:
                fails.append(f"qualifier: {ph[:60]!r} occurs {b}x in rc14 against {a}x in rc13, not justified")
    for (ph, d) in JUSTIFIED_PHRASE:
        if pdeltas.get(ph) != d:
            fails.append(f"qualifier: JUSTIFIED_PHRASE lists {ph!r} {d:+d} but the measured delta is {pdeltas.get(ph, 0):+d}")
    ho, hn = hedge_counts(old), hedge_counts(new)
    deltas = {w: hn[w] - ho[w] for w in HEDGE if hn[w] != ho[w]}
    for w, d in deltas.items():
        if (w, d) not in JUSTIFIED:
            fails.append(f"qualifier: hedge word {w!r} changed by {d:+d} and is not justified")
    for (w, d), why in JUSTIFIED.items():
        if deltas.get(w) != d:
            fails.append(f"qualifier: JUSTIFIED lists {w!r} {d:+d} but the measured delta is {deltas.get(w, 0):+d}")
    rep.append(f"locked phrases checked: {len(locked)}; phrase deltas: {pdeltas}; hedge-word deltas: {deltas}")
    # 6 carried integrity
    fails += R11.script_integrity(**R11.load_integrity_inputs())
    fails += R12.census_integrity(cz)
    f15, warns = R13.paths_integrity(st)
    fails += f15
    # 7 REANALISE, bold
    if R11.R_ANY.search(new):
        fails.append("reanalise: a REANALISE marker is present in rc14")
    noncode = re.sub(r"```.*?```", "", new, flags=re.S)
    for k, para in enumerate(re.split(r"\n\s*\n", noncode)):
        if para.count("**") % 2:
            fails.append(f"bold: odd number of ** in paragraph {k}: {para.strip()[:60]!r}")
    if verbose:
        print(f"hunks: {len(hs)}, all with an edit ID: {all(h['ids'] for h in hs)} "
              f"({sorted({i for h in hs for i in h['ids']}, key=lambda x: int(x[1:]))})")
        for r in rep:
            print(r)
        print(f"headings: {len(R11.headings(new))}, unchanged: {R11.headings(old) == R11.headings(new)}")
        print(f"SHAM-JANELA blocks: {len(sn)}, byte-identical to rc13: {sum(1 for x, y in zip(so, sn) if x == y)}")
        print(f"headlines checked: {len(heads)}")
        print(f"words: rc13 {len(old.split())} (body {len(body(old).split())}), "
              f"rc14 {len(new.split())} (body {len(body(new).split())})")
        for w in warns:
            print(w)
    if report:
        for h in hs:
            print(f"\n[{'+'.join(h['ids']) or '?'}] rc13 l.{h['rc10'][0]}-{h['rc10'][1]} -> rc14 l.{h['rc11'][0]}-{h['rc11'][1]}")
            print("  - " + "\n  - ".join(h["old"].splitlines()))
            print("  + " + "\n  + ".join(h["new"].splitlines()))
    return fails


def main():
    old, new = OLD.read_text(encoding="utf-8"), NEW.read_text(encoding="utf-8")
    if "--report" in sys.argv:
        f = check(old, new, verbose=True, report=True)
        print("\n" + ("\n".join("FAIL " + x for x in f) or "no failures"))
        return 0
    if "--self-test" in sys.argv:
        cz, st = R13.load_rc13(), R13.load_paths()
        rep1 = lambda a, b: (new.replace(a, b, 1), a in new)  # noqa: E731
        mutations = [
            # edited paragraphs
            ("number changed in an edited paragraph (E7)", rep1("sampled failure in B enters as 6.945", "sampled failure in B enters as 6.954")),
            ("cross-reference changed in an edited paragraph (E10)", rep1("then called M10 (§4.6), had no", "then called M10 (§4.5), had no")),
            ("hedge added in an edited sentence (E9)", rep1("The two were never read against each other", "The two may never have been read against each other")),
            ("qualifier dropped in an edited sentence (E1)", rep1("dated by our commit log and not deposited with the\nregistration", "dated by our commit log, with the\nregistration")),
            ("E3 non-rejection turned into rejection", rep1("test's non-rejection of the sharp null", "test's rejection of the sharp null")),
            # reviewers' qualifiers
            ("'only' dropped from the H2 BCa qualifier", rep1("under the registered BCa construction only", "under the registered BCa construction")),
            ("'deposited reading' dropped once", rep1("tested alone at α = 0.05, as the\ndeposited reading has it", "tested alone at α = 0.05, as the\nregistration has it")),
            ("dose qualifier inverted", rep1("not robust to the registered rule, not\nthat the dose had no effect", "not robust to the registered rule, and\nthat the dose had no effect")),
            ("'no contemporaneous record' weakened", rep1("We found no contemporaneous record of evaluating", "We found no record of evaluating")),
            ("'did not reproduce' replaced by 'drifted'", rep1("verdicts did not reproduce at the label\nlevel", "verdicts drifted at the label\nlevel")),
            ("'declared before its first call' weakened", rep1("a test-retest gate declared before its first call", "a test-retest gate declared")),
            ("hedge 'may' removed from §4.1.2", rep1("intervals reported here may be optimistic", "intervals reported here are optimistic")),
            ("negation removed in §4.3", rep1("and the registered test does not reject under either\nreading", "and the registered test rejects under either\nreading")),
            # structure
            ("code span changed", rep1("`ASSIGNMENT-SERVING.json` relabels", "`ASSIGNMENT-SERVED.json` relabels")),
            ("italic quotation changed", rep1("*\"all post-washout session-hours\"*); on", "*\"all session-hours\"*); on")),
            ("table cell changed", rep1("| registered design | 234 |", "| registered design | 233 |")),
            ("heading renamed", rep1("## 7. Threats to validity", "## 7. Threats to validity (rc14)")),
            ("struck text changed", rep1("~~Coverage 100%.~~", "~~Coverage 99%.~~")),
            ("changelog changed", rep1("**rc13: review of rc12 applied**", "**rc13: review of rc12 applied (edited)**")),
            ("SHAM-JANELA block changed", rep1("**Our error, stated.**", "**Our error.**")),
            ("citation removed", rep1(" [@kaplan2015nullnhlbi]", "")),
            ("unmapped hunk with no anchor", rep1("**Benchmarks compare systems on fixed tasks.**",
                                                   "Benchmarks are compared.\n\n**Benchmarks compare systems on fixed tasks.**")),
            ("carried rc13: abstract back to two commitments", rep1("Three commitments made before the seed", "Two commitments made before the seed")),
            ("carried rc11: H1a presented as rejected", rep1("and it is not rejected. Sources:", "and it is rejected. Sources:")),
        ]
        ok = True
        for name, (mutated, applied) in mutations:
            assert applied and mutated != new, f"mutation did not apply: {name}"
            # a mutation must be caught by a substantive check, not merely because its hunk lost its anchor,
            # except the one whose point is the hunk-ID check
            f = [x for x in check(old, mutated, verbose=False, cz=cz, st=st)
                 if name.startswith("unmapped") or "has no edit ID" not in x]
            print(f"mutation [{name}]: {'CAUGHT' if f else 'MISSED'}" + (f" -> {f[0][:140]}" if f else ""))
            ok &= bool(f)
        F = st["files"]
        integ = [
            ("carried rc13: absolute path put back in run_census.sh", dict(st, files=dict(F, **{"run_census.sh": F["run_census.sh"].replace(
                b'B=$(cd "$(dirname "$0")" && pwd)', ("B=" + str(Path.home()) + "/x").encode())})), "personal path"),
            ("carried rc13: RESULTADO-v3 number changed", dict(st, resultado=st["resultado"].replace(
                b"139.96 weighted opportunities", b"139.69 weighted opportunities")), "pre-rc13 file"),
        ]
        for name, kst, esperado in integ:
            f = [x for x in R13.paths_integrity(kst)[0] if esperado in x]
            print(f"mutation [{name}] (paths): {'CAUGHT' if f else 'MISSED'}" + (f" -> {f[0][:140]}" if f else ""))
            ok &= bool(f)
        kz = dict(cz, gates=cz["gates"].replace("VERDICT: FAIL", "VERDICT: PASS"))
        f = [x for x in R12.census_integrity(kz) if "no longer says FAIL" in x]
        print(f"mutation [carried rc12: GATES.md says PASS] (census record): {'CAUGHT' if f else 'MISSED'}")
        ok &= bool(f)
        base = check(old, new, verbose=False, cz=cz, st=st)
        print(f"unmutated rc14: {'PASS' if not base else 'FAIL'}" + (f" -> {base}" if base else ""))
        print(f"mutations: {len(mutations) + len(integ) + 1}")
        return 0 if ok and not base else 1
    fails = check(old, new)
    for f in fails:
        print("FAIL", f)
    print("PARITY: PASS" if not fails else f"PARITY: FAIL ({len(fails)})")
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
