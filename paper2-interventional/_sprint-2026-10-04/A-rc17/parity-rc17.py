#!/usr/bin/env python3
"""Parity check rc16 -> rc17 of Paper A after the Codex review of rc16.

Usage:
    python3 parity-rc17.py [OLD] [NEW] [--deposit PATH]
    python3 parity-rc17.py --selftest [OLD] [NEW] [--deposit PATH]

Exit 0 = parity holds; 1 = at least one check fails; 2 = usage/IO error.

rc17 applies the findings of `_sprint-2026-10-04/REVIEW-A-rc16-2026-10-05.md`: Codex C17-1..C17-6,
IDs as in `APPLY-A-rc17.md`. C17-1 (a `brief_log` row called a delivery) and C17-2 (the vocabulary
of one survey read as the methods or conventions of the field) are classes, so the whole
manuscript was swept for both and the sweep edits are declared under the same IDs ("C17-1 sweep",
"C17-2 sweep"). rc17 may change numbers, references, code spans and one qualifier count, but only
the ones a finding declares; no heading and no table row changes. The F-5 "Addendum, rc17" is cut
out of NEW (between its header and "## Open items") before the delta checks; the "addendum" check
requires that it exists exactly once, right after the rc16 addendum and right before
"## Open items".

As in rc16, rc17 does not touch any earlier addendum: the F-5 addenda rc5..rc16 must be
byte-identical.

Checks, OLD vs NEW-without-the-rc17-addendum (the extractors come from A-rc16/parity-rc16.py,
which takes them from A-rc15 back to A-rc9, so the tokenisation cannot drift):

  numbers     net multiset delta of numeric tokens + cardinal number words == DECLARED["numbers"]
  footnotes   net delta of [^x] markers and (↩ F-x) back-references == DECLARED (empty)
  refs        net delta of §n, Appendix X, F-n, Table/Figure/... references == DECLARED["refs"]
  code        net delta of inline backtick spans and fenced blocks == DECLARED["code"]
  links       net delta of link targets, bare URLs and DOIs == DECLARED (empty)
  headings    OLD headings == NEW headings, in order (no declared replacement)
  tables      OLD table rows == NEW table rows, in order (no declared replacement)
  history     F-5 addenda rc5..rc16 byte-identical
  qualifiers  carried: every rc6-rc16 scope qualifier keeps its rc16 count (outside the addenda),
              except the one DECLARED delta ('phase 0' +1, C17-3), and is >= 1; full scope clause
              in the Abstract and in §3.1; *no-record* defined exactly once, in §3.1
  classes     carried: none of the 35 forbidden phrasings of A-rc8/parity-rc8.py occurs in NEW
              outside the F-5 addenda
  withdrawn   carried and extended: none of the 72 phrasings withdrawn in rc11..rc16, nor the 25
              rc16 phrasings withdrawn here, occurs in NEW outside the F-5 addenda
  dashes      em dashes in running prose outside the carve-outs <= 0 (as in rc16)
  addendum    the rc17 addendum exists exactly once, in place
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
DEFAULT_OLD = SPRINT / "A-v1.1-rc16.md"
DEFAULT_NEW = SPRINT / "A-v1.1-rc17.md"
DEFAULT_DEPOSIT = SPRINT.parent / "deposit" / "paperA-v1.1" / "spare-capacity-narrow-surface-v1.1.md"

_spec = importlib.util.spec_from_file_location("parity_rc16", SPRINT / "A-rc16" / "parity-rc16.py")
_rc16 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_rc16)
FORBIDDEN = list(_rc16.FORBIDDEN)
assert len(FORBIDDEN) == 35, f"expected 35 forbidden phrasings, got {len(FORBIDDEN)}"
extract, norm, outside_addenda, prose_dashes = _rc16.extract, _rc16.norm, _rc16.outside_addenda, _rc16.prose_dashes
QUALIFIERS = list(_rc16.QUALIFIERS)
SCOPE_FULL, NO_RECORD_DEF = _rc16.SCOPE_FULL, _rc16.NO_RECORD_DEF
section, declared_counter, delta = _rc16.section, _rc16.declared_counter, _rc16.delta
first_prose, sub_at, qualifier_counts = _rc16.first_prose, _rc16.sub_at, _rc16.qualifier_counts

ADDENDA_START = "**Addendum, rc5 (2026-10-05)"
RC15_ADDENDUM = "**Addendum, rc15 (2026-10-05)"
RC16_ADDENDUM = "**Addendum, rc16 (2026-10-05)"
RC17_ADDENDUM = "**Addendum, rc17 (2026-10-05)"
OPEN_ITEMS = "\n## Open items"
PROSE_DASH_MAX = 0

# ---------------------------------------------------------------------------------------------
# Declared deltas: (finding, token, net change NEW - OLD).
# C17-1 = §3.1: `brief_log` records the selected items, written before rendering
#         (`brief.ts:1081-1104`); the text renderer can drop trailing items (`brief.ts:867-881`);
#         render check 2026-08-22..2026-09-07 (`out-ord0826.json`, `render_cut_lines_dropped_hist`);
#         counts of logged selections. Abstract/§1: "logged ... selected slots", pointer §3.1.
#         Sweep: §1 bullet, §4.1.1, §4.2, §4.3.1, §9 ("delivered/delivers" said of the brief).
# C17-2 = §1 and §8.3: "These terms are absent from this survey's extracted text. This does not
#         establish field methods or conventions." Sweep: Abstract first sentence, §1 first
#         sentence (pointer §8.1), "goes unasked", "the benchmarks do not measure", §8.3 opening
#         ("in systems CS"), "that precedent", §9 third conclusion (pointer §8.1).
# C17-3 = §4.3.2 note: main-pool membership from the reconstruction of §4.3.1 (phase 0), not
#         from frequency.
# C17-4 = §4.3.2: "would respond to a score adjustment, and nobody adjusts it" (no tokens).
# C17-5 = §4.3.2: scores do not decline; tracked accesses can still raise the access component
#         up to its cap (no tokens).
# C17-6 = §4.3.1: "the unit used in this main-pool comparison" (pointer §4.1 removed).
# ---------------------------------------------------------------------------------------------
D_NUMBERS = [
    # C17-1 §3.1: line cites and the render-check window 2026-08-22 .. 2026-09-07
    ("C17-1 §3.1 '`brief.ts:1081-1104`'", "1081", +1),
    ("C17-1 §3.1 '`brief.ts:1081-1104`'", "1104", +1),
    ("C17-1 §3.1 '`brief.ts:867-881`'", "867", +1),
    ("C17-1 §3.1 '`brief.ts:867-881`'", "881", +1),
    ("C17-1 §3.1 'from 2026-08-22 to 2026-09-07'", "2026", +2),
    ("C17-1 §3.1 'from 2026-08-22'", "08", +1),
    ("C17-1 §3.1 'from 2026-08-22'", "22", +1),
    ("C17-1 §3.1 'to 2026-09-07'", "09", +1),
    ("C17-1 §3.1 'to 2026-09-07'", "07", +1),
    ("C17-1 Abstract pointer '(§3.1)'", "3.1", +1),
    # C17-2 sweep: '(§8.1)' in the first sentence of §1 and in the third conclusion of §9
    ("C17-2 sweep §1 and §9 pointer '§8.1'", "8.1", +2),
    # C17-3 §4.3.2 note: 'present in 4,632 of 4,632 briefs' removed; '§4.3.1' and 'phase 0' added;
    # 'between the two channels' removed
    ("C17-3 §4.3.2 '4,632 of 4,632' removed", "4,632", -2),
    ("C17-3 §4.3.2 'reconstruction of §4.3.1'", "4.3.1", +1),
    ("C17-3 §4.3.2 'phase 0 selects them'", "0", +1),
    ("C17-3 §4.3.2 'between the two channels' removed", "two", -1),
    # C17-6 §4.3.1: 'the unit at which §4.1 measures exposure' removed
    ("C17-6 §4.3.1 pointer '§4.1' removed", "4.1", -1),
]
D_FOOTNOTES = []
D_REFS = [
    ("C17-1 Abstract '(§3.1)'", "§3.1", +1),
    ("C17-2 sweep §1 and §9 '(§8.1)'", "§8.1", +2),
    ("C17-3 §4.3.2 'reconstruction of §4.3.1'", "§4.3.1", +1),
    ("C17-6 §4.3.1 '§4.1' removed", "§4.1", -1),
]
D_CODE = [
    ("C17-1 §3.1 log write", "`brief.ts:1081-1104`", +1),
    ("C17-1 §3.1 renderer", "`brief.ts:867-881`", +1),
    ("C17-1 §3.1 render check artifact", "`A-filters-disaggregation/out-ord0826.json`", +1),
    ("C17-1 §3.1 render check field", "`render_cut_lines_dropped_hist`", +1),
    ("C17-3 §4.3.2 note: comparator removed", "`last_served ASC`", -1),
    ("C17-3 §4.3.2 note: comparator removed", "`last_served`", -1),
]
D_LINKS = []
D_HEADINGS = []
D_TABLES = []

# Declared qualifier deltas (rc17 - rc16), counted outside the addenda.
D_QUALIFIERS = {"phase 0": (+1, "C17-3 §4.3.2 'where phase 0 selects them as pinned items'")}

# Withdrawn phrasings: the 72 of rc11..rc16 (carried), plus the ones this review withdrew. None
# may come back outside the F-5 addenda (matching is whitespace-normalised and case-insensitive).
WITHDRAWN = list(_rc16.WITHDRAWN) + [
    ("C17-1", "`brief_log` records what the brief returned"),
    ("C17-1", "The brief delivered 583,763 slots"),
    ("C17-1", "It delivered 1,635 distinct live chunks"),
    ("C17-1", "It served 1,635 distinct live chunks"),
    ("C17-1", "a surface with slack delivers"),
    ("C17-1", "The surface delivers 10 items per session"),
    ("C17-1", "the surface delivers 10 per session"),
    ("C17-1", "what the channel delivered"),
    ("C17-1", "what the brief delivered"),
    ("C17-2", "describes a field whose"),
    ("C17-2", "instrument is the offline benchmark"),
    ("C17-2", "no established convention"),
    ("C17-2", "in systems CS, it is not"),
    ("C17-2", "goes unasked"),
    ("C17-2", "the metrics the field uses"),
    ("C17-2", "a coordinate the benchmarks do not measure"),
    ("C17-2", "is judged today on fixed inputs"),
    ("C17-2", "Memory systems for agents are evaluated on fixed sets"),
    ("C17-2", "does not claim to be that precedent"),
    ("C17-3", "by deduction. The coverage channel orders"),
    ("C17-3", "cannot have been chosen by a comparator"),
    ("C17-4", "*could* be corrected by score"),
    ("C17-4", "nobody corrects it"),
    ("C17-5", "stays at its ceiling"),
    ("C17-6", "the unit at which §4.1 measures"),
]
assert len(WITHDRAWN) == 97, f"expected 97 withdrawn phrasings, got {len(WITHDRAWN)}"


def cut_addendum(new):
    n = new.count(RC17_ADDENDUM)
    if n != 1:
        return new, f"rc17 addendum header occurs {n} times (expected 1)"
    a = new.find(RC17_ADDENDUM)
    b = new.find(OPEN_ITEMS, a)
    r16 = new.find(RC16_ADDENDUM)
    if b < 0:
        return new, "no '## Open items' after the rc17 addendum"
    if r16 < 0 or r16 > a:
        return new, "rc17 addendum is not after the rc16 addendum"
    if new[a:b].count("\n## ") or new[a:b].count("\n### "):
        return new, "a heading sits between the rc17 addendum and '## Open items'"
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

    # history: the addenda rc5..rc16 are byte-identical (rc17 corrects none of them)
    def region(t, a_mark, b_mark):
        a = t.find(a_mark)
        b = t.find(b_mark, a) if a >= 0 else -1
        return t[a:b] if a >= 0 and b >= 0 else None
    ho, hn = region(old, ADDENDA_START, OPEN_ITEMS), region(stripped, ADDENDA_START, OPEN_ITEMS)
    bad = []
    if ho is None or hn is None or ho != hn:
        bad.append("F-5 addenda rc5..rc16 differ or not found")
    for hdr in (RC15_ADDENDUM, RC16_ADDENDUM):
        if stripped.count(hdr) != 1:
            bad.append(f"{hdr!r} occurs {stripped.count(hdr)} times (expected 1)")
    results["history"] = (not bad, len(ho or ""), "; ".join(bad))

    # qualifiers (carried): rc16 counts + declared delta must hold in rc17, and each >= 1
    co, cn = qualifier_counts(old), qualifier_counts(stripped)
    bad = []
    for q, want, why in QUALIFIERS:
        if cn[q] < 1:
            bad.append(f"{q!r}: absent (meaning lost)")
        elif cn[q] != co[q] + D_QUALIFIERS.get(q, (0, ""))[0]:
            bad.append(f"{q!r}: {cn[q]} (rc16 has {co[q]}, declared delta "
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
CXA_S1 = "All 20 entries observed at saturation had an exit in the same stratum. That matching check is an"
C1_S31 = "`brief_log` records the items the brief selected, and it is written before the response is rendered"
C1_ABS = "The brief logged 583,763 selected slots, 8.7 times the size of the corpus, enough to"
C2_S1 = "`randomized` never. These terms are absent from this survey's extracted text. This does not"
C2_S83 = "What the absence of experimental vocabulary in the survey supports is more modest. These terms are"
C3_NOTE = "**Note:** the three constant items belong to the main pool in the reconstruction of §4.3.1,"
C4_S432 = "The main pool would respond to a score adjustment, and nobody adjusts it. The coverage channel,"
C5_S432 = "once-popular chunk does not decline with elapsed time, and further tracked accesses can still"
C6_S431 = "So the main pool is not capacity-bound at the day, the unit used in this main-pool"


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
        ("declared number changed (C17-1: render window 2026-09-07 -> 2026-09-08)", "numbers",
         lambda t: sub_at(t, "reconstructed from 2026-08-22 to 2026-09-07", "reconstructed from 2026-08-22 to 2026-09-08")),
        ("undeclared number", "numbers", lambda t: sub_at(t, "fleet of 6 agents", "fleet of 7 agents")),
        ("unit mutation is NOT caught (documented limit, as in rc16) -> expect no failure", None,
         lambda t: sub_at(t, "232 characters", "232 words")),
        ("heading edited", "headings",
         lambda t: t.replace("the exposure record of a production agent-memory system",
                             "the exposure record of an agent-memory system", 1)),
        ("§ reference (C17-2 sweep pointer §8.1 dropped in §9)", "refs",
         lambda t: sub_at(t, "the metrics of the survey's taxonomy (§8.1). This", "the metrics of the survey's taxonomy. This")),
        ("§ reference (C17-3 pointer §4.3.1 -> §4.3.2)", "refs",
         lambda t: sub_at(t, C3_NOTE, C3_NOTE.replace("reconstruction of §4.3.1,", "reconstruction of §4.3.2,"))),
        ("code span (C17-1 render-check field dropped)", "code",
         lambda t: sub_at(t, "`A-filters-disaggregation/out-ord0826.json`, `render_cut_lines_dropped_hist`); delivery",
                          "`A-filters-disaggregation/out-ord0826.json`); delivery")),
        ("table row edited (no table change declared in rc17)", "tables",
         lambda t: t.replace("The check that replaced it uses only **recorded** quantities and is not a falsifier (§5.6) |",
                             "The check that replaced it uses **recorded** quantities and is not a falsifier (§5.6) |", 1)),
        ("DOI", "links", lambda t: t.replace("`10.5281/zenodo.22110203`, v1.12",
                                             "`10.5281/zenodo.22110204`, v1.12", 1)),
        ("history: rc12 addendum edited", "history",
         lambda t: t.replace(rc12_line, rc12_line.replace("no wrong number", "no incorrect number"), 1)),
        ("history: rc16 addendum edited (now frozen)", "history",
         lambda t: t.replace("so the term is non-decreasing and capped at 0.20.", "so the term is non-decreasing and bounded by 0.20.", 1)),
        ("history: rc16 addendum header duplicated", "history",
         lambda t: t.replace(RC17_ADDENDUM, RC16_ADDENDUM + " " + RC17_ADDENDUM, 1)),
        ("scope clause dropped from §3.1 definition", "qualifiers",
         lambda t: t.replace("together; non-delivery across all agent-facing search is not established, because untracked",
                             "together, because untracked", 1)),
        ("qualifier dropped: in that regime", "qualifiers",
         lambda t: sub_at(t, "describe the channel in that regime", "describe the channel")),
        ("declared qualifier delta not seen (C17-3 'phase 0' reworded)", "qualifiers",
         lambda t: sub_at(t, "where phase 0 selects them as pinned items. Their", "where the first phase selects them as pinned items. Their")),
        ("rc8 class 'path-and-age' reintroduced", "classes",
         lambda t: sub_at(t, "There are two choices, one per", "There are two path-and-age choices, one per")),
        ("R11-2 withdrawn wording back (carried, no token changes)", "withdrawn",
         lambda t: sub_at(t, R2_SLOTS, R2_SLOTS.replace("are what", "are taken by the high-pain floor, what"))),
        ("CX-A (rc16) withdrawn wording back in §1 (carried, no token changes)", "withdrawn",
         lambda t: sub_at(t, CXA_S1, CXA_S1.replace("All 20 entries", "The prediction survived the test that could have killed it. All 20 entries"))),
        ("C17-1 withdrawn wording back in §3.1 (no token changes)", "withdrawn",
         lambda t: sub_at(t, C1_S31, C1_S31.replace("`brief_log` records the items the brief selected, and it is",
                                                    "`brief_log` records what the brief returned. It is"))),
        ("C17-1 withdrawn wording back in the Abstract", "withdrawn",
         lambda t: sub_at(t, C1_ABS, C1_ABS.replace("The brief logged 583,763 selected slots", "The brief delivered 583,763 slots"))),
        ("C17-2 withdrawn wording back in §1 (no token changes)", "withdrawn",
         lambda t: sub_at(t, C2_S1, C2_S1.replace("These terms are absent", "That describes a field whose instrument is the offline benchmark. These terms are absent"))),
        ("C17-2 withdrawn wording back in §8.3 (no token changes)", "withdrawn",
         lambda t: sub_at(t, C2_S83, C2_S83.replace("is more modest.", "is more modest: there is no established convention."))),
        ("C17-3 withdrawn wording back (no token changes)", "withdrawn",
         lambda t: sub_at(t, C3_NOTE, C3_NOTE + " A constant chunk cannot have been chosen by a comparator that prioritizes the least-recently-served.")),
        ("C17-4 withdrawn wording back (no token changes)", "withdrawn",
         lambda t: sub_at(t, C4_S432, C4_S432.replace("would respond to a score adjustment, and nobody adjusts it.",
                                                      "*could* be corrected by score, and nobody corrects it."))),
        ("C17-5 withdrawn wording back (no token changes)", "withdrawn",
         lambda t: sub_at(t, C5_S432, C5_S432.replace("does not decline with elapsed time,", "stays at its ceiling,"))),
        ("C17-6 withdrawn wording back (declared pointer restored, so refs/numbers also move)", "withdrawn",
         lambda t: sub_at(t, C6_S431, "So the main pool is not capacity-bound at the day, the unit at which §4.1 measures")),
        ("em dash back in prose", "dashes",
         lambda t: sub_at(t, "- **redundancy:** under minute,", "- **redundancy** — under minute,")),
        ("rc17 addendum removed", "addendum", lambda t: t.replace(RC17_ADDENDUM, "**Note, rc17 (2026-10-05)", 1)),
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
