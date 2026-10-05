#!/usr/bin/env python3
"""Parity check rc14 -> rc15 of Paper A after the Fable and Codex reviews of rc14.

Usage:
    python3 parity-rc15.py [OLD] [NEW] [--deposit PATH]
    python3 parity-rc15.py --selftest [OLD] [NEW] [--deposit PATH]

Exit 0 = parity holds; 1 = at least one check fails; 2 = usage/IO error.

rc15 applies the findings of `_sprint-2026-10-04/REVIEW-A-rc14-2026-10-05.md`: Fable FB1, FB2
(FB3 touches the deposit package, not the text) and Codex CX1..CX7 (IDs as in
`APPLY-A-rc15.md`). rc15 may change numbers, references, code spans and two table rows, but only
the ones a finding declares. The F-5 "Addendum, rc15" is cut out of NEW (between its header and
"## Open items") before the delta checks; the "addendum" check requires that it exists exactly
once, right after the rc14 addendum and right before "## Open items".

The rc14 addendum is part of the same unpublished version (v1.1 draft), so rc15 corrects its CR1
item in place (FB1 qualifier, FB2 dates); those edits are inside the delta checks and are declared
like any other. The addenda rc5..rc13 stay byte-identical.

Checks, OLD vs NEW-without-the-rc15-addendum (the extractors come from A-rc14/parity-rc14.py,
which takes them from A-rc13 back to A-rc9, so the tokenisation cannot drift):

  numbers     net multiset delta of numeric tokens + cardinal number words == DECLARED["numbers"]
  footnotes   net delta of [^x] markers and (↩ F-x) back-references == DECLARED (empty)
  refs        net delta of §n, Appendix X, F-n, Table/Figure/... references == DECLARED["refs"]
  code        net delta of inline backtick spans and fenced blocks == DECLARED["code"]
  links       net delta of link targets, bare URLs and DOIs == DECLARED (empty)
  headings    OLD headings == NEW headings, in order (no heading changes in rc15)
  tables      OLD table rows == NEW table rows, in order, except the 2 DECLARED replacements
  history     F-5 addenda rc5..rc13 byte-identical; the rc14 addendum occurs exactly once
  qualifiers  carried: every rc6-rc14 scope qualifier keeps its rc14 count (outside the addenda)
              plus the DECLARED delta (none in rc15), and is >= 1; full scope clause in the
              Abstract and in §3.1; *no-record* defined exactly once, in §3.1
  classes     carried: none of the 35 forbidden phrasings of A-rc8/parity-rc8.py occurs in NEW
              outside the F-5 addenda
  withdrawn   carried and extended: none of the 28 phrasings withdrawn in rc11..rc14, nor the 27
              rc14 phrasings withdrawn here, occurs in NEW outside the F-5 addenda
  dashes      em dashes in running prose outside the carve-outs <= 0 (as in rc14)
  addendum    the rc15 addendum exists exactly once, in place
  deposit     deposit/paperA-v1.1/spare-capacity-narrow-surface-v1.1.md is byte-identical to NEW

Every DECLARED entry carries the finding ID that justifies it. A delta that is not declared, or a
declared delta that did not happen, fails the check.

--selftest first requires OLD vs NEW to pass, then applies one mutation per check to NEW (or to
the deposit copy) and requires each mutated copy to FAIL on the expected check.
"""
import importlib.util
import re
import sys
from collections import Counter
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPRINT = HERE.parent
DEFAULT_OLD = SPRINT / "A-v1.1-rc14.md"
DEFAULT_NEW = SPRINT / "A-v1.1-rc15.md"
DEFAULT_DEPOSIT = SPRINT.parent / "deposit" / "paperA-v1.1" / "spare-capacity-narrow-surface-v1.1.md"

_spec = importlib.util.spec_from_file_location("parity_rc14", SPRINT / "A-rc14" / "parity-rc14.py")
_rc14 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_rc14)
FORBIDDEN = list(_rc14.FORBIDDEN)
assert len(FORBIDDEN) == 35, f"expected 35 forbidden phrasings, got {len(FORBIDDEN)}"
extract, norm, outside_addenda, prose_dashes = _rc14.extract, _rc14.norm, _rc14.outside_addenda, _rc14.prose_dashes
QUALIFIERS = list(_rc14.QUALIFIERS)
SCOPE_FULL, NO_RECORD_DEF = _rc14.SCOPE_FULL, _rc14.NO_RECORD_DEF
section, declared_counter, delta = _rc14.section, _rc14.declared_counter, _rc14.delta
first_prose, sub_at, qualifier_counts = _rc14.first_prose, _rc14.sub_at, _rc14.qualifier_counts

ADDENDA_START = "**Addendum, rc5 (2026-10-05)"
RC13_ADDENDUM = "**Addendum, rc13 (2026-10-05)"
RC14_ADDENDUM = "**Addendum, rc14 (2026-10-05)"
RC15_ADDENDUM = "**Addendum, rc15 (2026-10-05)"
OPEN_ITEMS = "\n## Open items"
PROSE_DASH_MAX = 0

# ---------------------------------------------------------------------------------------------
# Declared deltas: (finding, token, net change NEW - OLD).
# FB1 = the coverage set and the 33 + 108 identity are counts over the 10-row agent briefs; the
#       five 5-row probes of 2026-08-26 are outside them (§1, §2, §4.3.1 x3, Appendix A, F-4,
#       rc14 addendum); §4.3.1 names the 146 of `brief_log` on 2026-08-26 (RECON artifact);
# FB2 = minimum served age dated: 0.92 on 2026-08-23 to 6.92 on 2026-08-29, 0.72 on 2026-08-22
#       (§1, rc14 addendum);
# CX1 = the survey's metrics: Abstract, §1 (opening and gap bullet), §8.1 (Table 3 named);
# CX2 = §5.6 is a same-stratum matching check, not a falsifier (dedup is order-dependent);
# CX3 = the ceiling was measured with the recorded severity labels held fixed (§5.1, App. C);
# CX4 = §5.5: 17/350 is not a maximum over all additive adjustments (17 to 26, §5.7.1);
# CX5 = §6 last row: 245 vs 151 under different predicates establishes no lead;
# CX6 = §5.7.1: `churn` counts treated-only ids (`would_enter`);
# CX7 = utility of uniform serving not measured (Abstract, §1, §4.1.1, §9): no tokens.
# ---------------------------------------------------------------------------------------------
D_NUMBERS = [
    # FB1 §1: 'over its 10-row agent briefs ... (...; the five agent-less health probes of
    # 2026-08-26 are outside that count, §4.3.1)'
    ("FB1 §1 '10-row agent briefs'", "10", +1),
    ("FB1 §1 'the five agent-less health probes'", "five", +1),
    ("FB1 §1 'of 2026-08-26'", "2026", +1),
    ("FB1 §1 'of 2026-08-26'", "08", +1),
    ("FB1 §1 'of 2026-08-26'", "26", +1),
    ("FB1 §1 pointer '§4.3.1'", "4.3.1", +1),
    # FB2 §1: 'from 0.92 on 2026-08-23 to 6.92 on 2026-08-29 ... (0.72 on 2026-08-22; ...'
    ("FB2 §1 '0.92 on 2026-08-23', '6.92 on 2026-08-29', '0.72 on 2026-08-22'", "2026", +3),
    ("FB2 §1 the same three dates", "08", +3),
    ("FB2 §1 '2026-08-23'", "23", +1),
    ("FB2 §1 '2026-08-29'", "29", +1),
    ("FB2 §1 '2026-08-22'", "22", +1),
    ("FB2 §1 '(0.72 on 2026-08-22'", "0.72", +1),
    # FB1 §4.3.1 method: 'over the 10-row agent briefs (... the five 5-row probes of 2026-08-26,
    # §4.3, are outside this count and served 5 further chunks that day)'
    ("FB1 §4.3.1 '10-row agent briefs'", "10", +1),
    ("FB1 §4.3.1 'the five 5-row probes'", "five", +1),
    ("FB1 §4.3.1 '5-row', 'served 5 further chunks'", "5", +2),
    ("FB1 §4.3.1 'of 2026-08-26'", "2026", +1),
    ("FB1 §4.3.1 'of 2026-08-26'", "08", +1),
    ("FB1 §4.3.1 'of 2026-08-26'", "26", +1),
    ("FB1 §4.3.1 pointer '§4.3'", "4.3", +1),
    # FB1 §4.3.1 identity: '(...; on 2026-08-26 `brief_log` as a whole holds 146 distinct chunks,
    # the 5 probe-only chunks of §4.3 included: `RECON-52-e-sondas-2026-10-04.json`, ...)'
    ("FB1 §4.3.1 '2026-08-26' and the RECON file date", "2026", +2),
    ("FB1 §4.3.1 '2026-08-26'", "08", +1),
    ("FB1 §4.3.1 '2026-08-26'", "26", +1),
    ("FB1 §4.3.1 'holds 146 distinct chunks'", "146", +1),
    ("FB1 §4.3.1 'the 5 probe-only chunks'", "5", +1),
    ("FB1 §4.3.1 pointer '§4.3'", "4.3", +1),
    ("FB1 §4.3.1 RECON file name '-52-'", "52", +1),
    ("FB1 §4.3.1 RECON file name '2026-10-04'", "10", +1),
    ("FB1 §4.3.1 RECON file name '2026-10-04'", "04", +1),
    # FB1 + FB2 rc14 addendum CR1 item: 'in its 10-row agent briefs'; 'from 0.92 on 2026-08-23 to
    # 6.92 on 2026-08-29 ... (0.72 on 2026-08-22)'
    ("FB1 rc14 addendum 'in its 10-row agent briefs'", "10", +1),
    ("FB2 rc14 addendum three dates", "2026", +3),
    ("FB2 rc14 addendum three dates", "08", +3),
    ("FB2 rc14 addendum '2026-08-23'", "23", +1),
    ("FB2 rc14 addendum '2026-08-29'", "29", +1),
    ("FB2 rc14 addendum '2026-08-22'", "22", +1),
    ("FB2 rc14 addendum '(0.72 on 2026-08-22)'", "0.72", +1),
    # CX1 §8.1: 'all three score the representation' removed; '(survey §7.1, Table 3)' added
    ("CX1 §8.1 'and all three score the representation' removed", "three", -1),
    ("CX1 §8.1 'survey §7.1'", "7.1", +1),
    ("CX1 §8.1 'Table 3'", "3", +1),
    # CX2 §5.6: '(`brief.ts:420-433`, §5.3)', 'When deduplication ... (§5.3)', 'two
    # near-duplicates', Proposition 1 named once more; table row 'Proposition 1' gone;
    # 'All 20 observed entries'
    ("CX2 §5.6 'does not intervene (§5.3)', '`brief.ts:420-433`, §5.3'", "5.3", +2),
    ("CX2 §5.6 '`brief.ts:420-433`'", "420", +1),
    ("CX2 §5.6 '`brief.ts:420-433`'", "433", +1),
    ("CX2 §5.6 'which of two near-duplicates'", "two", +1),
    ("CX2 §5.6 'falsifier of Proposition 1' + 'refute Proposition 1' vs old 'Proposition 1 is "
     "false'; table row 'Proposition 1' removed", "1", 0),
    ("CX2 §5.6 'All 20 observed entries'", "20", +1),
    # CX3 §5.1: 'One of the two numbers in §5' -> 'Both numbers in §5'; 'the relative differences
    # between multipliers ... two designated items'; Appendix C rewritten ('in two ways', 'both
    # numbers in §5', the 'all §5 needs' clause folded)
    ("CX3 §5.1 'One of the two numbers' -> 'Both numbers'", "two", -1),
    ("CX3 §5.1 'when two designated items share a stratum'", "two", +1),
    ("CX3 Appendix C 'all §5 needs' folded into the §5.1 pointer", "5", -1),
    # CX4 §5.5: 'saturated at 17/350 states'; 'other designations give 17 to 26 of 350 (§5.7.1)'
    ("CX4 §5.5 '17 to 26'", "17", +1),
    ("CX4 §5.5 '17 to 26'", "26", +1),
    ("CX4 §5.5 'of 350'", "350", +1),
    ("CX4 §5.5 pointer '§5.7.1'", "5.7.1", +1),
    # CX5 §6 last row: '`last_accessed_at` on or after 2026-06-04'
    ("CX5 §6 'on or after 2026-06-04'", "2026", +1),
    ("CX5 §6 'on or after 2026-06-04'", "06", +1),
    ("CX5 §6 'on or after 2026-06-04'", "04", +1),
    # CX6 §5.7.1: '`churn` is the symmetric difference of two sets' removed
    ("CX6 §5.7.1 'symmetric difference of two sets' removed", "two", -1),
]
D_FOOTNOTES = []
D_REFS = [
    ("FB1 §1 pointer to §4.3.1 for the probes", "§4.3.1", +1),
    ("FB1 §4.3.1 method sentence, probes of §4.3", "§4.3", +1),
    ("FB1 §4.3.1 identity, probe-only chunks of §4.3", "§4.3", +1),
    ("CX1 §8.1 'survey §7.1'", "§7.1", +1),
    ("CX1 §8.1 'Table 3' (the survey's)", "Table 3", +1),
    ("CX2 §5.6 'does not intervene (§5.3)', '(`brief.ts:420-433`, §5.3)'", "§5.3", +2),
    ("CX2 §5.6 'refute Proposition 1' added; table row 'Proposition 1' removed", "Proposition 1", 0),
    ("CX3 Appendix C 'all §5 needs' folded", "§5", -1),
    ("CX4 §5.5 '(§5.7.1)'", "§5.7.1", +1),
]
D_CODE = [
    ("FB1 §4.3.1 the 146 is a `brief_log` count", "`brief_log`", +1),
    ("FB1 §4.3.1 RECON artifact", "`RECON-52-e-sondas-2026-10-04.json`", +1),
    ("FB1 §4.3.1 RECON field", "`por_dia_utc`", +1),
    ("CX2 §5.6 deduplication", "`pickDedup`", +1),
    ("CX2 §5.6 tryPick lines", "`brief.ts:420-433`", +1),
    ("CX3 §5.1 'raising `w` does not remove the relative differences'", "`w`", +1),
    ("CX5 §6 search predicate", "`last_accessed_at`", +1),
    ("CX6 §5.7.1 churn counts `would_enter`", "`would_enter`", +1),
]
D_LINKS = []
D_HEADINGS = []
D_TABLES = [
    ("CX2 §5.6 result row",
     "| Proposition 1 | **survives** |",
     "| same-stratum matching check | **passes** |"),
    ("CX5 §6 last row",
     "| comparison of a **filtered** count with an **unfiltered** one | inverted the sign of a "
     "conclusion: over the 865 curated entities, cumulatively search leads the brief 617 to 245, but "
     "in the window both instruments share (from 2026-06-04) the brief leads 245 to ≥151 "
     "(`out/superficie.json`, `janela_comum`; the 617 has no preserved field) |",
     "| comparison of a **filtered** count with an **unfiltered** one | produced opposite readings: "
     "over the 865 curated entities, cumulatively search leads the brief 617 to 245; in the window "
     "both instruments share (from 2026-06-04), the common-window artifact reports 245 live curated "
     "entities with brief records and 151 with `last_accessed_at` on or after 2026-06-04 "
     "(`out/superficie.json`, `janela_comum`). These different record predicates do not establish "
     "which surface delivered more distinct entities; the 617 has no preserved field |"),
]

# Declared qualifier deltas (rc15 - rc14), counted outside the addenda: none. ('with eligibility
# held fixed' keeps its single occurrence, now in the CX4 sentence of §5.5.)
D_QUALIFIERS = {}

# Withdrawn phrasings: the 28 of rc11..rc14 (carried), plus the ones this review withdrew. None
# may come back outside the F-5 addenda.
WITHDRAWN = list(_rc14.WITHDRAWN) + [
    ("FB1", "Daily, the two channels are disjoint and add up"),
    ("FB1", "the same 33 main and 108 coverage ids on every measurable day"),
    ("FB1", "the served coverage set stayed the same 108 ids"),
    ("FB1", "on which the served coverage set did not change"),
    ("FB1", "coverage-side ids on every day from 2026-08-23 to 2026-08-29 (the log-only method"),
    ("FB2", "from 0.92 to 6.92 days"),
    ("CX1", "classifies every metric in use as a score over a set of queries"),
    ("CX1", "all three score the representation"),
    ("CX1", "evaluated by retrieval quality"),
    ("CX1", "is judged today by retrieval quality"),
    ("CX1", "Benchmarks measure nDCG/recall over sets of queries"),
    ("CX2", "the bonus crossed a stratum and Proposition 1 is false"),
    ("CX2", "Proposition 1 | **survives**"),
    ("CX2", "The derivation is falsifiable"),
    ("CX3", "independent of the severity label"),
    ("CX3", "a dose at which the multiplier saturates"),
    ("CX3", "One of the two numbers in §5 inherits that provenance"),
    ("CX3", "which of the two numbers in §5 depends"),
    ("CX3", "the panel enters in one way only"),
    ("CX4", "no additive salience adjustment could change selection there beyond the ceiling"),
    ("CX5", "the brief leads 245 to"),
    ("CX5", "inverted the sign of a conclusion"),
    ("CX6", "is the symmetric difference of two sets"),
    ("CX6", "moves both in an uncorrelated way"),
    ("CX7", "serving uniformly would be useless"),
    ("CX7", "serving memory at random would be worse"),
    ("CX7", "serving uniformly would destroy its value"),
]
assert len(WITHDRAWN) == 55, f"expected 55 withdrawn phrasings, got {len(WITHDRAWN)}"


def cut_addendum(new):
    n = new.count(RC15_ADDENDUM)
    if n != 1:
        return new, f"rc15 addendum header occurs {n} times (expected 1)"
    a = new.find(RC15_ADDENDUM)
    b = new.find(OPEN_ITEMS, a)
    r14 = new.find(RC14_ADDENDUM)
    if b < 0:
        return new, "no '## Open items' after the rc15 addendum"
    if r14 < 0 or r14 > a:
        return new, "rc15 addendum is not after the rc14 addendum"
    if new[a:b].count("\n## ") or new[a:b].count("\n### "):
        return new, "a heading sits between the rc15 addendum and '## Open items'"
    return new[:a].rstrip("\n") + "\n" + new[b:], None


def compare(old, new, deposit=None):
    results = {}
    stripped, problem = cut_addendum(new)
    results["addendum"] = (problem is None, 1, problem or "")
    eo, en = extract(old), extract(stripped)
    for key, decl in (("numbers", D_NUMBERS), ("footnotes", D_FOOTNOTES), ("refs", D_REFS),
                      ("code", D_CODE), ("links", D_LINKS)):
        actual = delta(eo[key], en[key])
        want = Counter({k: v for k, v in declared_counter(decl).items() if v})
        ok = actual == want
        detail = ""
        if not ok:
            undeclared = {k: v for k, v in actual.items() if want.get(k) != v}
            missing = {k: v for k, v in want.items() if actual.get(k) != v}
            detail = f"undeclared/other={undeclared} declared-not-seen={missing}"
        results[key] = (ok, len(decl), detail)
    for key, decl in (("headings", D_HEADINGS), ("tables", D_TABLES)):
        expect, bad = list(eo[key]), []
        for fid, o, n in decl:
            if expect.count(o) != 1:
                bad.append(f"{fid}: OLD line occurs {expect.count(o)} times")
                continue
            expect[expect.index(o)] = n
        if expect != en[key]:
            diffs = [(i, x[:80], y[:80]) for i, (x, y) in enumerate(zip(expect, en[key])) if x != y][:3]
            bad.append(f"len {len(expect)}->{len(en[key])}; first diffs {diffs}")
        results[key] = (not bad, len(decl), "; ".join(bad))

    # history: the addenda rc5..rc13 are byte-identical; the rc14 addendum (same unpublished
    # version) may be corrected, but must still occur exactly once
    def region(t, a_mark, b_mark):
        a = t.find(a_mark)
        b = t.find(b_mark, a) if a >= 0 else -1
        return t[a:b] if a >= 0 and b >= 0 else None
    ho, hn = region(old, ADDENDA_START, RC14_ADDENDUM), region(stripped, ADDENDA_START, RC14_ADDENDUM)
    bad = []
    if ho is None or hn is None or ho != hn:
        bad.append("F-5 addenda rc5..rc13 differ or not found")
    if stripped.count(RC14_ADDENDUM) != 1:
        bad.append(f"rc14 addendum header occurs {stripped.count(RC14_ADDENDUM)} times (expected 1)")
    results["history"] = (not bad, len(ho or ""), "; ".join(bad))

    # qualifiers (carried): rc14 counts + declared delta must hold in rc15, and each >= 1
    co, cn = qualifier_counts(old), qualifier_counts(stripped)
    bad = []
    for q, want, why in QUALIFIERS:
        if cn[q] < 1:
            bad.append(f"{q!r}: absent (meaning lost)")
        elif cn[q] != co[q] + D_QUALIFIERS.get(q, (0, ""))[0]:
            bad.append(f"{q!r}: {cn[q]} (rc14 has {co[q]}, declared delta "
                       f"{D_QUALIFIERS.get(q, (0, 'none'))[0]:+d})")
    abstract = norm(section(stripped, "## Abstract", "## 1. Introduction"))
    s31 = norm(section(stripped, "### 3.1 ", "### 3.2 "))
    if SCOPE_FULL not in abstract:
        bad.append("full scope clause missing from the Abstract")
    if SCOPE_FULL not in s31:
        bad.append("full scope clause missing from §3.1")
    if stripped.count(NO_RECORD_DEF) != 1 or NO_RECORD_DEF not in section(stripped, "### 3.1 ", "### 3.2 "):
        bad.append("no-record is not defined exactly once, in §3.1")
    results["qualifiers"] = (not bad, len(QUALIFIERS), "; ".join(bad))

    # classes (carried) and withdrawn (carried + extended), both outside the F-5 addenda
    body, found = outside_addenda(new)
    residual = [] if found else ["F-5 addenda region not found"]
    for fid, pat in FORBIDDEN:
        for m in re.finditer(pat, body, re.I):
            residual.append(f"{fid} /{pat}/ at body line {body.count(chr(10), 0, m.start()) + 1}: {m.group(0)!r}")
    results["classes"] = (not residual, len(FORBIDDEN), "; ".join(residual))
    nbody = norm(body)
    back = [f"{fid}: {p!r}" for fid, p in WITHDRAWN if norm(p).lower() in nbody.lower()]
    results["withdrawn"] = (not back and found, len(WITHDRAWN), "; ".join(back))

    d = prose_dashes(stripped)
    results["dashes"] = (len(d) <= PROSE_DASH_MAX, len(d),
                         "" if len(d) <= PROSE_DASH_MAX else f"{len(d)} > {PROSE_DASH_MAX} at lines {d[:10]}")
    if deposit is None:
        results["deposit"] = (False, 0, "deposit copy not found")
    else:
        same = deposit == new
        results["deposit"] = (same, len(deposit), "" if same else "deposit copy differs from NEW")
    return results


def report(results, label):
    print(f"== {label}")
    for key, (ok, size, detail) in results.items():
        print(f"  {'PASS' if ok else 'FAIL'}  {key:<10} n={size}" + (f"  {detail[:500]}" if detail else ""))
    allok = all(ok for ok, _, _ in results.values())
    print(f"  => {'PARITY OK' if allok else 'PARITY BROKEN'}")
    return allok


R2_SLOTS = "the 3 shared slots are what `mainTarget` leaves after the agent quota"
FB2_S1 = "2026-08-23 to 6.92 on 2026-08-29 in daily increments of 1.00 (0.72 on 2026-08-22;"
CX1_ABS = "survey (218 papers) covers retrieval, memory-quality, response-quality and end-to-end task"
CX7_S1 = "concentrate. Uniform serving is used only as a capacity reference; its effect on agent utility"
FB1_ID = "never reached. Daily, in the agent briefs, the two channels are disjoint and add up to the"


def main(argv):
    selftest = "--selftest" in argv
    dep_p = DEFAULT_DEPOSIT
    args = []
    it = iter(argv)
    for a in it:
        if a == "--deposit":
            dep_p = Path(next(it))
        elif not a.startswith("--"):
            args.append(a)
    old_p = Path(args[0]) if args else DEFAULT_OLD
    new_p = Path(args[1]) if len(args) > 1 else DEFAULT_NEW
    try:
        old, new = old_p.read_text(), new_p.read_text()
    except OSError as e:
        print(e)
        return 2
    deposit = dep_p.read_text() if dep_p.exists() else None
    print(f"OLD {old_p}\nNEW {new_p}\nDEPOSIT {dep_p}")
    base_ok = report(compare(old, new, deposit), "baseline OLD vs NEW")
    if not selftest:
        return 0 if base_ok else 1
    if not base_ok:
        print("SELFTEST: baseline does not pass; mutations not meaningful")
        return 1
    rc12_line = "review found no wrong number in rc11. What changed:"
    mutations = [
        ("declared number changed (FB1: 146 -> 147 in §4.3.1)", "numbers",
         lambda t: sub_at(t, "as a whole holds 146 distinct chunks", "as a whole holds 147 distinct chunks")),
        ("undeclared number", "numbers", lambda t: sub_at(t, "fleet of 6 agents", "fleet of 7 agents")),
        ("FB2 date of the 0.72 dropped from §1 (declared tokens not seen)", "numbers",
         lambda t: sub_at(t, FB2_S1, FB2_S1.replace("(0.72 on 2026-08-22;", "("))),
        ("unit mutation is NOT caught (documented limit, as in rc14) -> expect no failure", None,
         lambda t: sub_at(t, "232 characters", "232 words")),
        ("heading edited", "headings",
         lambda t: t.replace("the exposure record of a production agent-memory system",
                             "the exposure record of an agent-memory system", 1)),
        ("§ reference in prose (DS3 pointer §3.1 -> §3.2)", "refs",
         lambda t: sub_at(t, "the absence of a record in both (§3.1),", "the absence of a record in both (§3.2),")),
        ("code span (FB1 RECON field dropped)", "code",
         lambda t: sub_at(t, "`RECON-52-e-sondas-2026-10-04.json`, `por_dia_utc`)",
                          "`RECON-52-e-sondas-2026-10-04.json`)")),
        ("code span (CX2 tryPick range narrowed)", "code",
         lambda t: sub_at(t, "(`brief.ts:420-433`, §5.3)", "(`brief.ts:420`, §5.3)")),
        ("table row reverted (CX2 'Proposition 1 | survives')", "tables",
         lambda t: t.replace("| same-stratum matching check | **passes** |", "| Proposition 1 | **survives** |", 1)),
        ("DOI", "links", lambda t: t.replace("`10.5281/zenodo.22110203`, v1.12",
                                             "`10.5281/zenodo.22110204`, v1.12", 1)),
        ("history: rc12 addendum edited", "history",
         lambda t: t.replace(rc12_line, rc12_line.replace("no wrong number", "no incorrect number"), 1)),
        ("history: rc13 addendum edited (now frozen)", "history",
         lambda t: t.replace("(This item was corrected in rc14; see below.)",
                             "(This item was corrected in rc14 and rc15; see below.)", 1)),
        ("history: rc14 addendum header duplicated", "history",
         lambda t: t.replace(RC15_ADDENDUM, RC14_ADDENDUM + " " + RC15_ADDENDUM, 1)),
        ("scope clause dropped from §3.1 definition", "qualifiers",
         lambda t: t.replace("together; non-delivery across all agent-facing search is not established, because untracked",
                             "together, because untracked", 1)),
        ("qualifier dropped: in that regime", "qualifiers",
         lambda t: sub_at(t, "describe the channel in that regime", "describe the channel")),
        ("qualifier dropped: 'with eligibility held fixed' (CX4 sentence keeps the only one)", "qualifiers",
         lambda t: sub_at(t, "with eligibility held fixed, other designations", "with eligibility fixed, other designations")),
        ("rc8 class 'path-and-age' reintroduced", "classes",
         lambda t: sub_at(t, "There are two choices, one per", "There are two path-and-age choices, one per")),
        ("R11-2 withdrawn wording back (carried, no token changes)", "withdrawn",
         lambda t: sub_at(t, R2_SLOTS, R2_SLOTS.replace("are what", "are taken by the high-pain floor, what"))),
        ("DS6 withdrawn wording back (carried, no token changes)", "withdrawn",
         lambda t: sub_at(t, "they fill the three shared main-pool slots", "they fill the three corpus-wide slots")),
        ("FB1 withdrawn wording back: unqualified 33 + 108 identity", "withdrawn",
         lambda t: sub_at(t, FB1_ID, FB1_ID.replace("Daily, in the agent briefs, the two", "Daily, the two"))),
        ("FB2 withdrawn wording back: undated 0.92 to 6.92", "withdrawn",
         lambda t: sub_at(t, FB2_S1, "2026-08-23 to 2026-08-29, from 0.92 to 6.92 days in daily increments of 1.00 (0.72 on 2026-08-22;")),
        ("CX1 withdrawn wording back in the Abstract (no token changes)", "withdrawn",
         lambda t: sub_at(t, CX1_ABS, CX1_ABS.replace("covers retrieval",
                                                      "classifies every metric in use as a score over a set of queries; it covers retrieval"))),
        ("CX2 withdrawn wording back (no token changes)", "withdrawn",
         lambda t: sub_at(t, "The derivation can be checked against recorded quantities.", "The derivation is falsifiable.")),
        ("CX3 withdrawn wording back (no token changes)", "withdrawn",
         lambda t: sub_at(t, "  labels can decide which of them is served;",
                          "  labels can decide which of them is served. It is independent of the severity label;")),
        ("CX4 withdrawn wording back (no token changes)", "withdrawn",
         lambda t: sub_at(t, "This is not a maximum over all additive salience adjustments:",
                          "So no additive salience adjustment could change selection there beyond the ceiling:")),
        ("CX5 withdrawn wording back in the §6 row", "withdrawn",
         lambda t: t.replace("| produced opposite readings:", "| inverted the sign of a conclusion:", 1)),
        ("CX6 withdrawn wording back", "withdrawn",
         lambda t: sub_at(t, "`churn` counts the treated-only ids", "`churn` is the symmetric difference of two sets, the treated-only ids")),
        ("CX7 withdrawn wording back in §1 (no token changes)", "withdrawn",
         lambda t: sub_at(t, CX7_S1, CX7_S1.replace("concentrate. Uniform", "concentrate; serving memory at random would be worse. Uniform"))),
        ("em dash back in prose", "dashes",
         lambda t: sub_at(t, "- **redundancy:** under minute,", "- **redundancy** — under minute,")),
        ("rc15 addendum removed", "addendum", lambda t: t.replace(RC15_ADDENDUM, "**Note, rc15 (2026-10-05)", 1)),
    ]
    ok = True
    for name, expect, mut in mutations:
        m = mut(new)
        if m == new:
            print(f"SELFTEST mutation '{name}': did not apply -> MISSED")
            ok = False
            continue
        res = compare(old, m, m)
        failed = sorted(k for k, (good, _, _) in res.items() if not good)
        if expect is None:
            good = not failed
            print(f"SELFTEST mutation '{name}': fails on {failed} -> {'AS DOCUMENTED' if good else 'UNEXPECTED'}")
        else:
            good = expect in failed
            print(f"SELFTEST mutation '{name}': fails on {failed} (expect {expect}) -> {'BITES' if good else 'MISSED'}")
        ok &= good
    dep_mut = new.replace("reserved before deposit; the record is published", "reserved at deposit; the record is published", 1)
    res = compare(old, new, dep_mut)
    bit = dep_mut != new and not res["deposit"][0] and all(g for k, (g, _, _) in res.items() if k != "deposit")
    print(f"SELFTEST mutation 'deposit copy diverges': fails on "
          f"{sorted(k for k, (g, _, _) in res.items() if not g)} (expect deposit) -> {'BITES' if bit else 'MISSED'}")
    ok &= bit
    print("SELFTEST OK" if ok else "SELFTEST FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
