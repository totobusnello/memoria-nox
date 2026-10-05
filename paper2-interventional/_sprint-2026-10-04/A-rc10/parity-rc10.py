#!/usr/bin/env python3
"""Parity check rc9 -> rc10 of Paper A after the Fable/Codex review of rc9.

Usage:
    python3 parity-rc10.py [OLD] [NEW] [--deposit PATH]
    python3 parity-rc10.py --selftest [OLD] [NEW] [--deposit PATH]

Exit 0 = parity holds; 1 = at least one check fails; 2 = usage/IO error.

rc10 applies the findings of `_sprint-2026-10-04/REVIEW-A-rc9-2026-10-05.md` (Fable F1-F13,
Codex C1-C2). Unlike rc9 it is allowed to change numbers, references, code spans, links, one
heading and one table row, but only the ones a finding declares. The F-5 "Addendum, rc10" is cut
out of NEW (between its header and "## Open items") before the delta checks; the "addendum" check
requires that it exists exactly once, right after the rc9 addendum and right before "## Open items".

Checks, OLD vs NEW-without-the-rc10-addendum (the extractors are imported from A-rc9/parity-rc9.py
so the tokenisation cannot drift):

  numbers     net multiset delta of numeric tokens + cardinal number words == DECLARED["numbers"]
  footnotes   net delta of [^x] markers and (↩ F-x) back-references == DECLARED (empty)
  refs        net delta of §n, Appendix X, F-n, Table/Figure/... references == DECLARED["refs"]
  code        net delta of inline backtick spans and fenced blocks == DECLARED["code"]
  links       net delta of link targets, bare URLs and DOIs == DECLARED["links"]
  headings    OLD headings with the DECLARED replacements applied == NEW headings, in order
  tables      OLD table rows with the DECLARED replacements applied == NEW table rows, in order
  history     F-5 addenda rc5..rc8 byte-identical; the rc9 addendum byte-identical after the one
              declared C2 replacement
  qualifiers  for every rc6-rc9 scope qualifier, the NEW count (outside the addenda) equals the
              DECLARED count and is >= 1 (the meaning survives somewhere); the full scope clause is
              present in the Abstract and in §3.1; *no-record* is defined exactly once, in §3.1
  classes     none of the 35 forbidden phrasings of A-rc8/parity-rc8.py (imported via parity-rc9)
              occurs in NEW outside the F-5 addenda
  dashes      em dashes in running prose outside the carve-outs <= 0 (as in rc9)
  addendum    the rc10 addendum exists exactly once, in place
  deposit     deposit/paperA-v1.1/MANUSCRIPT-v1.1.md is byte-identical to NEW (F1: rc10 is the
              single source of the deposited text)

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
DEFAULT_OLD = SPRINT / "A-v1.1-rc9.md"
DEFAULT_NEW = SPRINT / "A-v1.1-rc10.md"
DEFAULT_DEPOSIT = SPRINT.parent / "deposit" / "paperA-v1.1" / "MANUSCRIPT-v1.1.md"

_spec = importlib.util.spec_from_file_location("parity_rc9", SPRINT / "A-rc9" / "parity-rc9.py")
_rc9 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_rc9)
FORBIDDEN = list(_rc9.FORBIDDEN)
assert len(FORBIDDEN) == 35, f"expected 35 forbidden phrasings, got {len(FORBIDDEN)}"
extract, norm, outside_addenda, prose_dashes = _rc9.extract, _rc9.norm, _rc9.outside_addenda, _rc9.prose_dashes

ADDENDA_START = "**Addendum, rc5 (2026-10-05)"
RC9_ADDENDUM = "**Addendum, rc9 (writing pass"
RC10_ADDENDUM = "**Addendum, rc10 (2026-10-05)"
OPEN_ITEMS = "\n## Open items"
PROSE_DASH_MAX = 0

# ---------------------------------------------------------------------------------------------
# Declared deltas. Format: (finding, token, net change NEW - OLD). Net, because a token can be
# removed by one finding and added by another; the justification string says who did what.
# ---------------------------------------------------------------------------------------------
D_NUMBERS = [
    ("F7 title note 2026-10-05 +1; F8 2026-08-23 +1; F6 +5 (09-03, 09-07, 08-21, 08-22T19:09Z, 08-22); F2 §4.3.2 +2 (08-21, 09-07); F10 2026-06-04 +1; F5 2026-08-30 -1", "2026", +9),
    ("F8 +1; F6 +4 (08-21, 08-23, 08-22, 08-22); F2 +1; F5 -1", "08", +5),
    ("F5: 2026-08-30 of the Abstract's correction narrative", "30", -1),
    ("F7 title note 2026-10-05", "10", +1),
    ("F7 title note 2026-10-05", "05", +1),
    ("F6 09-03, 09-07, 19:09Z; F2 09-07", "09", +4),
    ("F6 08-21; F2 08-21", "21", +2),
    ("F6 08-22 twice", "22", +2),
    ("F8 08-23; F6 08-23", "23", +2),
    ("F6 09-07; F2 09-07", "07", +2),
    ("F6 09-03", "03", +1),
    ("F10 2026-06-04", "04", +1),
    ("F10 2026-06-04", "06", +1),
    ("F1 reserved version DOI in Appendix D and Open items 4", "10.5281", +2),
    ("F10 table row of §6 + status block", "617", +2),
    ("F10 the 865 curated entities", "865", +1),
    ("F10 status block: 'the last table row of §6'", "6", +1),
    ("F12 status block: 'the 0 of 32'", "32", +1),
    ("F12 status block: 'the 0 of 32'", "0", +1),
    ("F4 no-record pointers (§1, contributions, §4.1, §4.1.1 x2 ... net of the removed scope clauses)", "3.1", +4),
    ("F2 §4.3.2 pin sentence '(F7, §4.3.1)'", "4.3.1", +1),
    ("F6 '8 ids'", "8", +1),
    ("F6 '9 ids'", "9", +1),
    ("F6 stricter fidelity range", "94.3", +1),
    ("F6 stricter fidelity range", "97.9%", +1),
    ("F6 08-21..08-23 fidelity", "85.8%", +1),
    ("F6 08-21..08-23 fidelity", "85.7%", +1),
    ("F6 08-21..08-23 fidelity", "98.0%", +1),
    ("F6 the boris slot", "298048", +2),
    ("F6 the boris slot", "285042", +1),
    ("F2 Abstract: 149 served chunks", "149", +1),
    ("F2 Abstract: ranks 44-46", "44", +1),
    ("F2 Abstract: ranks 44-46", "46", +1),
    ("F2 brief.ts:819-821 in Abstract and §4.3.2", "819", +2),
    ("F2 brief.ts:819-821 in Abstract and §4.3.2", "821", +2),
    ("F2 §4.3.2 lift_F7_pinned", "116107", +1),
    ("F2 §4.3.2 +1; F11 +1", "227328", +2),
    ("F11", "109163", +1),
    ("F11 the month's 37-id main union", "37", +1),
    ("F11 'all ten slots'", "ten", +1),
    ("F5 Abstract third axis: the 25 rows", "25", +1),
    ("F8 '34 on 2026-08-23'", "34", +1),
    ("F9 brief.ts:462-466 -> 470-474", "470", +1),
    ("F9 brief.ts:462-466 -> 470-474", "474", +1),
    ("F9 brief.ts:462-466 -> 470-474", "462", -1),
    ("F9 brief.ts:462-466 -> 470-474", "466", -1),
    ("F4/F5 Abstract: third copy of the 1,635/1,787 pair removed", "1,635", -1),
    ("F4/F5 Abstract: third copy of the 1,635/1,787 pair removed", "1,787", -1),
    ("F4/F5 Abstract: third copy of the 1,635/1,787 pair removed", "152", -1),
    ("F5 Abstract: second Caveat note (repeats §3.1) dropped", "10,899", -1),
    ("F5 Abstract: second Caveat note (repeats §3.1) dropped", "9,755", -1),
    ("F5 Abstract: correction narrative 'from 17/350 (4.86%)' dropped", "17", -1),
    ("F5 Abstract: correction narrative 'from 17/350 (4.86%)' dropped", "350", -1),
    ("F5 Abstract: correction narrative 'from 17/350 (4.86%)' dropped", "4.86%", -1),
    ("F5 Abstract: 'along two axes' and 'two notes on reading' dropped", "two", -2),
    ("F5 Abstract: 'eight times over' (duplicate of 'eight times') dropped", "eight", -1),
    ("XREF Abstract+§1 'no downstream outcome is instrumented' pointed to §5.4; it lives in §4.5", "4.5", +2),
    ("XREF Abstract+§1 'no downstream outcome is instrumented' pointed to §5.4; it lives in §4.5", "5.4", -2),
]
D_FOOTNOTES = []
D_REFS = [
    ("F4 no-record pointers to §3.1", "§3.1", +4),
    ("F2 §4.3.2 pin sentence", "§4.3.1", +1),
    ("F10 status block", "§6", +1),
    ("F1 F-5 and Open items 4 point to Appendix D", "Appendix D", +2),
    ("XREF 'no downstream outcome is instrumented' (Abstract, §1): §5.4 -> §4.5", "§4.5", +2),
    ("XREF 'no downstream outcome is instrumented' (Abstract, §1): §5.4 -> §4.5", "§5.4", -2),
]
D_CODE = [
    ("F9", "`brief.ts:462-466`", -1),
    ("F9", "`brief.ts:470-474`", +1),
    ("F1 Open items 4 no longer awaits the TODO", "`[TODO at deposit]`", -1),
    ("F1 Appendix D + Open items 4", "`10.5281/zenodo.23163119`", +2),
    ("F2 Abstract + §4.3.2", "`brief.ts:819-821`", +2),
    ("F2 §4.3.2", "`lift_F7_pinned`", +1),
    ("F2 §4.3.2 + F11 §4.3.1", "`A-filters-disaggregation/out-ord0826.json`", +2),
    ("F4 §3.1 definition of no-record", "`brief_log`", +1),
    ("F6", "`fresh_added`", +3),
    ("F6", "`out-ord0826.json`", +1),
    ("F6", "`fidelity`", +1),
    ("F6", "`boris`", +1),
    ("F6", "`A-filters-disaggregation/diag-out.txt`", +1),
    ("F10", "`out/superficie.json`", +1),
    ("F10", "`janela_comum`", +1),
]
D_LINKS = [
    ("F1 reserved version DOI in Appendix D and Open items 4", "10.5281/zenodo.23163119", +2),
]
D_HEADINGS = [
    ("F7 title",
     "# Spare capacity, narrow surface: what a production agent-memory system actually surfaces",
     "# Spare capacity, narrow surface: the exposure record of a production agent-memory system"),
]
D_TABLES = [
    ("F10 §6 last row",
     "| comparison of a **filtered** count with an **unfiltered** one | inverted the sign of a conclusion: 617×245 cumulative becomes 245×≥151 in the common window |",
     "| comparison of a **filtered** count with an **unfiltered** one | inverted the sign of a conclusion: over the 865 curated entities, cumulatively search leads the brief 617 to 245, but in the window both instruments share (from 2026-06-04) the brief leads 245 to ≥151 (`out/superficie.json`, `janela_comum`; the 617 has no preserved field) |"),
]
C2_OLD = ("Codex in rc8. No number, unit, cross-reference, code span, path, line citation, DOI, quotation,\n"
          "heading or table row changed, and every scope qualifier of rc6 to rc8 is still present with the\n"
          "same count; `_sprint-2026-10-04/A-rc9/parity-rc9.py` checks all of that against rc8, together\n"
          "with the class check inherited from rc8.")
C2_NEW = ("Codex in rc8. `_sprint-2026-10-04/A-rc9/parity-rc9.py` checks, against rc8: the multisets of\n"
          "numeric tokens and number words, footnote markers and back-references, cross-references, inline\n"
          "code spans and fenced blocks (which carry the paths and line citations), and link targets and\n"
          "DOIs; headings and table rows, byte for byte; the rc5 to rc8 addenda, byte for byte; the count\n"
          "of each rc6 to rc8 scope qualifier; the class check inherited from rc8; and em dashes in running\n"
          "prose. It does not check units, quotations outside code spans or the wording around a number;\n"
          "that these did not change rests on manual review of the before-and-after list.")

# Qualifiers (rc6-rc9 list + the F4 term): expected NEW count outside the addenda, with the reason.
SCOPE_FULL = "non-delivery across all agent-facing search is not established"
QUALIFIERS = [
    ("lower bound on non-delivery by the brief and by tracked search", 1,
     "F4: kept in the Abstract; the repeats became 'no-record (§3.1)'"),
    ("lower bound on non-delivery by the brief and tracked search", 1, "F4: repeats became the term"),
    (SCOPE_FULL, 3, "F4: Abstract once, §3.1 twice (argument + definition)"),
    ("not established", 8, "F4: the 4 scope-clause repeats removed"),
    ("in the measured regime", 5, "unchanged"),
    ("in that regime", 2, "unchanged"),
    ("holding eligibility fixed", 3, "unchanged"),
    ("with eligibility held fixed", 1, "unchanged"),
    ("within `last_served` ties", 9, "unchanged"),
    ("path patterns, the importance/pain floor and age windows", 7, "unchanged"),
    ("path patterns, an importance floor and age windows", 1, "unchanged"),
    ("two path patterns, an importance floor and an age", 1, "unchanged"),
    ("the importance/pain floor", 7, "unchanged"),
    ("whoever initiated", 4, "F4: thinned in the Abstract (2->1), §4.1.1 and §4.3.2"),
    ("phase 0", 2, "unchanged"),
    ("phase 1", 2, "unchanged"),
    ("before the F6 quota pass", 1, "unchanged"),
    ("after the pinned", 2, "unchanged"),
    ("toward `mainTarget`", 2, "unchanged"),
    ("defective-ingestion", 5, "F4: thinned in the Abstract and §9 ('same regime')"),
    ("defective session ingestion", 3, "unchanged"),
    ("no-record", 11, "F4: defined in §3.1, used with a pointer"),
]
NO_RECORD_DEF = "We call this quantity *no-record*"


def cut_addendum(new):
    n = new.count(RC10_ADDENDUM)
    if n != 1:
        return new, f"rc10 addendum header occurs {n} times (expected 1)"
    a = new.find(RC10_ADDENDUM)
    b = new.find(OPEN_ITEMS, a)
    r9 = new.find(RC9_ADDENDUM)
    if b < 0:
        return new, "no '## Open items' after the rc10 addendum"
    if r9 < 0 or r9 > a:
        return new, "rc10 addendum is not after the rc9 addendum"
    if new[a:b].count("\n## ") or new[a:b].count("\n### "):
        return new, "a heading sits between the rc10 addendum and '## Open items'"
    return new[:a].rstrip("\n") + "\n" + new[b:], None


def section(text, start, end):
    a = text.find(start)
    b = text.find(end, a + 1) if a >= 0 else -1
    return text[a:b] if a >= 0 and b >= 0 else ""


def declared_counter(decl):
    c = Counter()
    for _, tok, n in decl:
        c[tok] += n
    return c


def delta(a, b):
    d = Counter()
    for k in set(a) | set(b):
        v = b.get(k, 0) - a.get(k, 0)
        if v:
            d[k] = v
    return d


def compare(old, new, deposit=None):
    results = {}
    stripped, problem = cut_addendum(new)
    results["addendum"] = (problem is None, 1, problem or "")
    eo, en = extract(old), extract(stripped)
    for key, decl in (("numbers", D_NUMBERS), ("footnotes", D_FOOTNOTES), ("refs", D_REFS),
                      ("code", D_CODE), ("links", D_LINKS)):
        actual, want = delta(eo[key], en[key]), declared_counter(decl)
        want = Counter({k: v for k, v in want.items() if v})
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
    # history
    def region(t, a_mark, b_mark):
        a = t.find(a_mark)
        b = t.find(b_mark, a) if a >= 0 else -1
        return t[a:b] if a >= 0 and b >= 0 else None
    bad = []
    ho, hn = region(old, ADDENDA_START, RC9_ADDENDUM), region(stripped, ADDENDA_START, RC9_ADDENDUM)
    if ho is None or ho != hn:
        bad.append("F-5 addenda rc5..rc8 differ or not found")
    r9o, r9n = region(old, RC9_ADDENDUM, OPEN_ITEMS), region(stripped, RC9_ADDENDUM, OPEN_ITEMS)
    if r9o is None or r9o.count(C2_OLD) != 1:
        bad.append("C2: the rc9 sentence to replace is not in OLD once")
    elif r9o.replace(C2_OLD, C2_NEW).rstrip("\n") != (r9n or "").rstrip("\n"):
        bad.append("rc9 addendum differs from OLD + the declared C2 replacement")
    results["history"] = (not bad, len(ho or ""), "; ".join(bad))
    # qualifiers
    qn = norm(outside_addenda(stripped)[0])
    bad = []
    for q, want, why in QUALIFIERS:
        cn = len(re.findall(re.escape(q), qn, re.I))
        if cn < 1:
            bad.append(f"{q!r}: absent (meaning lost)")
        elif cn != want:
            bad.append(f"{q!r}: {cn} (declared {want}: {why})")
    abstract = norm(section(stripped, "## Abstract", "## 1. Introduction"))
    s31 = norm(section(stripped, "### 3.1 ", "### 3.2 "))
    if SCOPE_FULL not in abstract:
        bad.append("full scope clause missing from the Abstract")
    if SCOPE_FULL not in s31:
        bad.append("full scope clause missing from §3.1")
    if stripped.count(NO_RECORD_DEF) != 1 or NO_RECORD_DEF not in section(stripped, "### 3.1 ", "### 3.2 "):
        bad.append("no-record is not defined exactly once, in §3.1")
    results["qualifiers"] = (not bad, len(QUALIFIERS), "; ".join(bad))
    # classes
    body, found = outside_addenda(new)
    residual = [] if found else ["F-5 addenda region not found"]
    for fid, pat in FORBIDDEN:
        for m in re.finditer(pat, body, re.I):
            residual.append(f"{fid} /{pat}/ at body line {body.count(chr(10), 0, m.start()) + 1}: {m.group(0)!r}")
    results["classes"] = (not residual, len(FORBIDDEN), "; ".join(residual))
    # dashes
    d = prose_dashes(stripped)
    results["dashes"] = (len(d) <= PROSE_DASH_MAX, len(d),
                         "" if len(d) <= PROSE_DASH_MAX else f"{len(d)} > {PROSE_DASH_MAX} at lines {d[:10]}")
    # deposit
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


def first_prose(text, needle):
    fence, pos = False, 0
    for line in text.split("\n"):
        s = line.lstrip()
        if s.startswith("```"):
            fence = not fence
        elif not fence and not s.startswith(("|", "#")) and needle in line:
            return pos + line.find(needle)
        pos += len(line) + 1
    raise SystemExit(f"selftest: {needle!r} not on any prose line")


def sub_at(text, needle, repl):
    i = first_prose(text, needle)
    return text[:i] + repl + text[i + len(needle):]


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
    rc8_line = "proposed two §1 sentences, and both are taken verbatim."
    mutations = [
        ("declared number changed (F6 range)", "numbers", lambda t: sub_at(t, "94.3–97.9%", "94.4–97.9%")),
        ("undeclared number", "numbers", lambda t: sub_at(t, "fleet of 6 agents", "fleet of 7 agents")),
        ("Codex C2 unit mutation is NOT caught (documented limit) -> expect no failure", None,
         lambda t: sub_at(t, "232 characters", "232 words")),
        ("title reverted", "headings",
         lambda t: t.replace("the exposure record of a production agent-memory system",
                             "what a production agent-memory system actually surfaces", 1)),
        ("§ reference in prose", "refs", lambda t: sub_at(t, "§4.3.1", "§4.3.2")),
        ("code span (F9 reverted)", "code", lambda t: sub_at(t, "`brief.ts:470-474`", "`brief.ts:470-475`")),
        ("table row edited", "tables", lambda t: t.replace("| positive search counter (live) | 9,755 |",
                                                           "| positive search counter, live | 9,755 |", 1)),
        ("DOI", "links", lambda t: t.replace("`10.5281/zenodo.22110203`, v1.12",
                                             "`10.5281/zenodo.22110204`, v1.12", 1)),
        ("history: rc8 addendum edited", "history",
         lambda t: t.replace(rc8_line, rc8_line.replace("taken verbatim", "taken literally"), 1)),
        ("history: C2 rewrite reverted", "history", lambda t: t.replace(C2_NEW, C2_OLD, 1)),
        ("scope clause dropped from §3.1 definition", "qualifiers",
         lambda t: t.replace("together; non-delivery across all agent-facing search is not established, because untracked",
                             "together, because untracked", 1)),
        ("no-record definition removed", "qualifiers",
         lambda t: t.replace(NO_RECORD_DEF, "We name this quantity *no-record*", 1)),
        ("qualifier dropped: in that regime", "qualifiers",
         lambda t: sub_at(t, "describe the channel in that regime", "describe the channel")),
        ("rc8 class 'path-and-age' reintroduced", "classes",
         lambda t: sub_at(t, "There are two choices, one per", "There are two path-and-age choices, one per")),
        ("rc6 class 'immune' reintroduced", "classes",
         lambda t: sub_at(t, "The symmetry.** The two channels", "The symmetry.** The two immune channels")),
        ("em dash back in prose", "dashes",
         lambda t: sub_at(t, "- **redundancy:** under minute,", "- **redundancy** — under minute,")),
        ("rc10 addendum removed", "addendum", lambda t: t.replace(RC10_ADDENDUM, "**Note, rc10 (2026-10-05)", 1)),
    ]
    ok = True
    for name, expect, mut in mutations:
        m = mut(new)
        if m == new:
            print(f"SELFTEST mutation '{name}': did not apply -> MISSED")
            ok = False
            continue
        # the deposit follows NEW in every mutation except the deposit one, so only the target check moves
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
    bit = not res["deposit"][0] and all(g for k, (g, _, _) in res.items() if k != "deposit")
    print(f"SELFTEST mutation 'deposit copy diverges': fails on "
          f"{sorted(k for k, (g, _, _) in res.items() if not g)} (expect deposit) -> {'BITES' if bit else 'MISSED'}")
    ok &= bit
    print("SELFTEST OK" if ok else "SELFTEST FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
