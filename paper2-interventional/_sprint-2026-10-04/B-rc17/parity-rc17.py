#!/usr/bin/env python3
"""Parity check B-v2-rc16.md -> B-v2-rc17.md (Paper B, sprint 2026-10-04; rc17 2026-10-05).

rc17 applies the review of rc16 (Codex: one MEDIUM, M1, and two LOW; Fable: three LOW), each
finding verified against its primary source before it was applied (`APPLY-B-rc17.md`). No number
of the analysis moves: v4, checks-rc15 and the acceleration test are untouched. One artifact
changes: `B-registered/RESULTADO-v4.md` gains a dated note at its end (Fable LOW); the bytes before
the note are kept as `RESULTADO-v4-rc16-d5b3b8b6.md`, and the note is the only difference.

M1, verified: the deposited v1.12 (published 2026-08-26T14:01Z) designates at brief composition
and recomputes the designation at every brief (PREREG §2 l.535; AMENDMENT-v1.12 §0 and §5.2-bis),
and records that rule as an open defect (§5). The fixed 19-item designation was decided at
14:47Z (DESIGNATION-SEED) and completed at 20:28Z the same day, after v1.12, and was not
deposited (PROSPECTIVE-ESTIMAND §3 item 1: the resolution lives outside the registration). So
the horizon/expiry mismatch is between the registered horizon and the subsequently frozen
intervention, not inside the registration. The source facts are checked here (block S).

Checks (exit 1 if any fails):
  1. hunks: every hunk rc16 -> rc17 carries an ID from ANCHORS.
  2. numbers: every numeric token REMOVED from the body is in JUSTIFIED_REMOVED with its exact count;
     every token ADDED is in rc16, a leaf of an artifact read here (v4, checks-rc15, the test
     output), or derived (derived_rc17, each read from its source file here).
  3. invariants rc16 -> rc17: italic quotations, citations, footnotes, DOIs, image links and struck
     spans unchanged; headings identical.
  4. working list and changelog: rc17's, with the declared insertion and the rc17 block removed, is
     byte-identical to rc16's; the changelog items after rc14's are 149-163.
  5. SHAM-JANELA: 10 blocks byte-identical to rc16.
  6. carried locks: rc16's (rc13 claims with rc16's deviation-count lock, rc15 and rc16 sweeps,
     status marks and presence locks), with declared replacements (PRESENT_REPLACED); NEW sweep
     (SWEEP_LOCK_RC17: the mismatch placed inside the registration, "every earlier version", the
     B.1 row without accelerations), presence of each reviewer text, status names rc17.
  7. qualifier set: rc16's locked phrases (= rc15's) occur as often as in rc16, except
     JUSTIFIED_PHRASE; hedge words per hunk-ID group (JUSTIFIED_HEDGE), summed to the body delta.
  8. integrity: rc16's carried checks, with RESULTADO-v4.md read as its frozen rc16 bytes; NEW: the
     frozen copy is exactly d5b3b8b6…, the live file is the frozen bytes plus RES_NOTE and nothing
     else, the note names the live test sha8s and its largest difference; source facts (block S).
  9. no REANALISE marker; bold balanced per paragraph.

Usage:  python3 parity-rc17.py | --report | --self-test     Reads; writes nothing.
"""
import collections
import copy
import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPRINT = HERE.parent
P2 = SPRINT.parent
OLD = SPRINT / "B-v2-rc16.md"
NEW = SPRINT / "B-v2-rc17.md"
RC16 = SPRINT / "B-rc16" / "parity-rc16.py"
RC16_SHA = "527f9484b80c184b0cc767cd16aee779e5ace74785e7dcd30052be00ab4281e2"
OLD_SHA = "d6a9259ecae5d6d8c7d358ff4014443d90bd18287ccbaba7e6652555ce705823"

assert hashlib.sha256(RC16.read_bytes()).hexdigest() == RC16_SHA, \
    "parity-rc16.py changed: the locks carried from it are no longer the ones rc16 ran"
_spec = importlib.util.spec_from_file_location("parity_rc16", RC16)
R16 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(R16)  # also installs rc16's deviation-count lock into R13
R15, R14, R13, R12, R11 = R16.R15, R16.R14, R16.R13, R16.R12, R16.R11

REG = SPRINT / "B-registered"
RES4 = REG / "RESULTADO-v4.md"
RES4_FROZEN = REG / "RESULTADO-v4-rc16-d5b3b8b6.md"
RES4_SHA = "d5b3b8b62fea4ba5b64ac6f0f45fdcac8424773f37375f9367143e6911ff9413"
RES_NOTE = """
## Note added 2026-10-05 (rc17): the acceleration test was revised in rc16

The artifact table above records the test as rc15 left it (`bb9c3197…` · `ae9e8fe9…`); those
bytes are kept unchanged as `B-registered/teste_aceleracao_v4-rc15-bb9c3197.py` and
`teste-aceleracao-v4-rc15-ae9e8fe9.json`. rc16 revised the test so that it also compares the
unrounded accelerations, to 1e-12 (largest difference 1.4×10⁻¹⁶); the current files,
`teste_aceleracao_v4.py` · `teste-aceleracao-v4.json`, have sha256 `d4d960db…` · `041bd4a9…`
(`APPLY-B-rc16.md`). Nothing above this note was edited, so every hash it records still
resolves; the bytes before this note are kept as `RESULTADO-v4-rc16-d5b3b8b6.md`.
"""
SOURCES = {
    "plan13": P2 / "deposit" / "PLAN-v1.13.md",
    "dseed": P2 / "DESIGNATION-SEED-2026-08-26.md",
    "amend": P2 / "AMENDMENT-v1.12.md",
    "prosp": P2 / "PROSPECTIVE-ESTIMAND-2026-08-30.md",
    "prereg": P2 / "PREREG-DRAFT.md",
    "dev": P2 / "DEVIATIONS-FOR-PAPER.md",
    "meta12": P2 / "deposit" / "zenodo-v1.12-metadata.json",
}

flat, body, tail, sha, sci = R16.flat, R16.body, R16.tail, R16.sha, R16.sci
load = R16.load


# ---------------------------------------------------------------- S: the source facts M1 rests on
def source_facts(src=None):
    src = src or {k: p.read_text(encoding="utf-8") for k, p in SOURCES.items()}
    fails = []
    need = [
        ("plan13", "`10.5281/zenodo.22110203`, 2026-08-26T14:01Z", "v1.12 published 2026-08-26T14:01Z"),
        ("dseed", "A substituição foi decidida em **2026-08-26T14:47Z**", "replacement rule decided 14:47Z"),
        ("amend", "e a designação é recomputada a cada\nbrief", "AMENDMENT-v1.12 §0: designation recomputed at every brief"),
        ("amend", "hoje a designação **é recomputada a cada brief**", "AMENDMENT-v1.12 §5.2-bis: recomputed at every brief"),
        ("amend", "## §5. Defeito aberto: a designação não está validamente congelada", "AMENDMENT-v1.12 §5: open defect"),
        ("prosp", "A resolução vive **fora** do registro", "PROSPECTIVE-ESTIMAND §3: resolution outside the registration"),
        ("prosp", "resolvido em 2026-08-26 (`DESIGNATION-SEED-2026-08-26.md`); a v1.12 foi depositada **antes**",
         "PROSPECTIVE-ESTIMAND §3 item 1: v1.12 deposited before, not amended"),
    ]
    for k, needle, why in need:
        if needle not in src[k]:
            fails.append(f"source: {why} — not found in {SOURCES[k].name}")
    meta = json.loads(src["meta12"])["metadata"]
    if meta.get("version") != "1.12" or meta.get("publication_date") != "2026-08-26":
        fails.append("source: zenodo-v1.12-metadata.json is not version 1.12 of 2026-08-26")
    pl = src["prereg"].splitlines()
    if not pl[534].lstrip("> ").startswith("**Registered:** at brief composition, partition eligible failure chunks"):
        fails.append("source: PREREG l.535 is not the registered at-brief-composition designation rule")
    if "the nesting that makes the joint reporting work" not in pl[307] or "H1b defined — LOCKED 2026-08-16" not in pl[307]:
        fails.append("source: PREREG l.308 is not the 2026-08-16 H1b lock carrying the nesting sentence")
    heads = [(i + 1, x) for i, x in enumerate(pl[:308]) if x.startswith("## ")]
    if not heads or not heads[-1][1].startswith("## 1. "):
        fails.append(f"source: PREREG l.308 is not inside §1 (last heading {heads[-1] if heads else None})")
    # the only "expir…" in PREREG is about snapshot-relative corpus counts (l.861), not about a designation
    exp = [ln for ln in pl if re.search(r"(?i)expir", ln)]
    if len(exp) != 1 or "These counts are snapshot-relative" not in exp[0]:
        fails.append("source: PREREG mentions an expiry beyond the snapshot-count sentence; §3.0.1's "
                     "'not as the life of a fixed set' needs rereading")
    band = [x for x in src["dev"].splitlines() if x.startswith("| a banda `{2,0 · 4,0 · 7,5}`")]
    if len(band) != 1 or not band[0].rstrip().endswith("| ⬇ |") or "what does not move, and could not" not in band[0]:
        fails.append("source: DEVIATIONS-FOR-PAPER.md front table does not carry the band row marked ⬇")
    return fails


# ---------------------------------------------------------------- 1: anchors
ANCHORS = [
    ("TT", "# A registered horizon that outlived its intervention:"),
    ("ST", "rc17 prepared 2026-10-05 (review of rc16 applied:"),
    ("M1", "The trial retained the registered 234-epoch horizon"),
    ("M1", "whose registered\nhorizon outlived the intervention it ran"),
    ("M1", "Its designation rule selects, at brief composition, one"),
    ("M1", "the registered horizon outlived the intervention the trial ran, and the trial"),
    ("M1", "it is not a\ncontradiction inside the registration either"),
    ("M1", "the registered horizon outlived the\nintervention the trial ran (§3.0.1)"),
    ("M1", "collisions between its own locks."),
    ("M1", "two collisions whose parts each looked complete alone"),
    ("M1", "In short, the registered horizon outlived the intervention the trial ran"),
    ("M1", "One contradiction was internal to the registration"),
    ("M1", "after v1.12 was published, by the fixed 19-item designation, which was not deposited"),
    ("LV", "a rejection in versions up to rc9, and returns neither"),
    ("LV", "in versions\nup to rc9, whose analyses"),
    ("LV", "H1 did reject in versions\nup to rc9 of this analysis"),
    ("LB1", "the BCa intervals, accelerations and adjusted quantiles equal to"),
    ("FD", "`DEVIATIONS-FOR-PAPER.md` still carries\nthe withdrawn reading"),
    ("FN", "the H1b lock of\n2026-08-16 in §1 of the pre-registration (PREREG l.308)"),
    ("FR", "*(rc17: `RESULTADO-v4.md` now ends with a dated note"),
    ("WL", "*(rc17: rc16 had two full reads"),
    ("CL", "**rc17: review of rc16 applied**"),
]
REMOVED_ANCHORS = []

# ---------------------------------------------------------------- 2: numbers
JUSTIFIED_REMOVED = {}


def derived_rc17(A, src=None):
    src = src or {k: p.read_text(encoding="utf-8") for k, p in SOURCES.items()}
    out = {}
    for tok, k, needle in (("14:01Z", "plan13", "2026-08-26T14:01Z"),
                           ("14:47Z", "dseed", "2026-08-26T14:47Z")):
        if needle in src[k]:
            out[tok] = f"{SOURCES[k].name}: {needle}"
    return out


# ---------------------------------------------------------------- 3: invariants
DECL_INV = {}
INV_FREE = R16.INV_FREE
INV_FIXED = {"italic quotations", "citations", "footnote markers", "DOIs", "image links", "struck spans"}

# ---------------------------------------------------------------- 4: tail insertions
TAIL_INSERTS = [
    """ *(rc17: rc16 had two full reads: Codex NO-GO with one
    MEDIUM and two LOW, Fable with three LOW; all verified and applied in rc17. rc17 itself
    has not been reviewed.)*""",
]

# ---------------------------------------------------------------- 6: locks
SWEEP_LOCK_RC17 = [  # searched in the unstruck, flattened body (status header included)
    (r"property of the registration", "M1: the mismatch is not a property of the registration"),
    (r"[Tt]he registration outlived its intervention", "M1 (the title, 'A registration that …', is flagged, not swept)"),
    (r"each contradicted another lock of the same registration", "M1 (§8.5)"),
    (r"inconsistencies in its own registration", "M1 (§8.5)"),
    (r"It happened twice here, at two scales", "M1 (§9)"),
    (r"the same shape as the H1b collision of §4\.4, on a larger object", "M1 (§3.0.1)"),
    (r"a fixed set of designated items \(memory chunks\)", "M1 (§1): the deposited rule is not a fixed set"),
    (r"in every earlier version", "Codex LOW: 'versions up to rc9'"),
    (r"every number but the BCa intervals and adjusted quantiles", "Codex LOW (B.1): accelerations"),
]
PRESENT_RC17 = [
    ("The trial retained the registered 234-epoch horizon while adopting a fixed designation that was eligible for "
     "only 20 epochs; the designation was chosen on 2026-08-26, after v1.12 was deposited, and was not deposited "
     "itself.", "M1 Abstract"),
    ("This incompatibility was present before the trial began", "M1 Abstract"),
    ("Its designation rule selects, at brief composition, one eligible chunk per signature group (PREREG §2), so the "
     "designation is recomputed at every brief (`AMENDMENT-v1.12.md` §5.2-bis)", "M1 §1"),
    ("The fixed 19-item designation used in this trial was adopted on 2026-08-26, after v1.12, and was not deposited "
     "as an amendment", "M1 §1 (reviewer's text, adapted)"),
    ("v1.12 was published at 14:01Z, the replacement rule was decided at 14:47Z", "M1 §1 (times)"),
    ("this is a mismatch between the registered horizon and the intervention frozen after it", "M1 §3.0.1"),
    ("an internal contradiction in the registered estimand (§4.4), and a mismatch between the registered horizon and "
     "the subsequently frozen intervention (§3.0.1)", "M1 §8.5 (reviewer's text)"),
    ("One contradiction was internal to the registration", "M1 §9 (reviewer's text)"),
    ("A second incompatibility arose between its horizon and the subsequently frozen intervention",
     "M1 §9 (reviewer's text)"),
    ("a rejection in versions up to rc9", "Codex LOW (Abstract)"),
    ("It rejected under the deposited reading in versions up to rc9", "Codex LOW (§9)"),
    ("every number but the BCa intervals, accelerations and adjusted quantiles equal to", "Codex LOW (B.1)"),
    ("`DEVIATIONS-FOR-PAPER.md` still carries the withdrawn reading in its front table (the band row, marked ⬇): it "
     "is a dated, append-only log, and it is not edited.", "Fable LOW (App. A)"),
    ("the H1b lock of 2026-08-16 in §1 of the pre-registration (PREREG l.308) calls that nesting", "Fable LOW (§1)"),
    ("*(rc17: `RESULTADO-v4.md` now ends with a dated note naming the rc16 test bytes", "Fable LOW (App. B)"),
]
PRESENT_REPLACED = {}  # rc15/rc16 presence locks that rc17 rewrites -> finding
STATUS_MARKS_RC17 = R16.STATUS_MARKS_RC16 + ["rc17 prepared 2026-10-05 (review of rc16 applied:"]
STATUS_LOCK = R16.STATUS_LOCK

# ---------------------------------------------------------------- 7: qualifier deltas
JUSTIFIED_PHRASE = {
    ("not deposited", +6): ("M1", "the reviewer's 'was not deposited', said of the fixed designation where the "
                                   "mismatch is now placed: Abstract, §1, §3.0.1, Appendix A and the status header "
                                   "(twice: 'not deposited itself', 'and was not deposited')"),
}
JUSTIFIED_HEDGE = {
    "TT": ({"registered": 1}, "title (author decision 2026-10-05): 'A registration' → 'A registered horizon' (M1)"),
    "ST": ({"not": 2, "registered": 1, "deposited": 2},
           "status header, rc17 clause: 'the deposited v1.12 and was not deposited', 'the registered horizon', "
           "'not a contradiction inside the registration'"),
    "M1": ({"not": 7, "only": 2, "registered": 10, "deposited": 6, "every": 2, "would": -2, "either": 1},
           "the mismatch moved out of the registration: 'not deposited' (Abstract, §1, §3.0.1, App. A), 'not a "
           "contradiction inside the registration either' and 'not as the life of a fixed set' (§3.0.1), 'only 20 "
           "epochs' (Abstract) and 'only the horizon is in the registration' (§3.0.1), 'registered horizon' "
           "throughout, 'recomputed at every brief' (§1, §3.0.1); 'the designation it would act on' (§3.0.1) and "
           "'the intervention it would act on' (§9) removed, since sizing.py acted under the deposited rule"),
    "LV": ({"every": -3}, "'every earlier version' → 'versions up to rc9' (Abstract twice, §9)"),
    "FD": ({"not": 1, "still": 1}, "App. A (Fable): 'still carries the withdrawn reading … it is not edited'"),
    "FR": ({"every": 1, "still": 1}, "App. B (Fable): 'so every hash it records still resolves'"),
}


def res4_integrity(files, new):
    """RESULTADO-v4.md = its rc16 bytes + RES_NOTE, and nothing else (Fable LOW)."""
    fails = []
    h = lambda b: hashlib.sha256(b).hexdigest()  # noqa: E731
    fr, live = files["res4_frozen"], files["res4"]
    if h(fr) != RES4_SHA:
        fails.append("res4: the frozen rc16 copy is not d5b3b8b6…")
    if live != fr + RES_NOTE.encode():
        fails.append("res4: RESULTADO-v4.md is not its rc16 bytes plus the rc17 note, exactly")
    note = RES_NOTE
    for s8 in (h(files["testepy"])[:8], h(files["teste"])[:8]):
        if f"`{s8}…`" not in note:
            fails.append(f"res4: the note does not name the live test sha8 {s8}")
    return fails


def check(old, new, verbose=True, report=False, cz=None, st=None, A=None, files=None, files15=None, src=None):
    cz = cz or R13.load_rc13()
    st = st or R13.load_paths()
    A = A or load()
    src = src or {k: p.read_text(encoding="utf-8") for k, p in SOURCES.items()}
    if files is None:
        files = {k: p.read_bytes() for k, p in R15.ART.items()}
        files["res4_frozen"] = RES4_FROZEN.read_bytes()
    files15 = files15 or {"py": R16.FROZEN_TEST_PY.read_bytes(), "json": R16.FROZEN_TEST_JSON.read_bytes()}
    fails, rep = [], []
    if hashlib.sha256(old.encode()).hexdigest() != OLD_SHA:
        fails.append("rc16 is not the d6a9259e… bytes rc16's parity passed on")
    ob, nb = body(old), body(new)
    # 2 numbers
    dn, do = R11.numbers(nb), R11.numbers(ob)
    delta = {k: dn[k] - do[k] for k in set(dn) | set(do) if dn[k] != do[k]}
    removed = {k: -d for k, d in delta.items() if d < 0}
    for k in sorted(set(removed) | set(JUSTIFIED_REMOVED)):
        if removed.get(k, 0) != JUSTIFIED_REMOVED.get(k, (0,))[0]:
            fails.append(f"numbers: token {k!r} removed {removed.get(k, 0)}x; JUSTIFIED_REMOVED declares "
                         f"{JUSTIFIED_REMOVED.get(k, (0,))[0]}x")
    allowed = dict(R11.artifact_numbers())
    for name in ("v4", "c15", "teste"):
        for v in R11.leaves(A[name]):
            for fm in R11.forms(v):
                allowed.setdefault(fm, name)
    der = derived_rc17(A, src)
    old_nums = R11.numbers(old)
    added = {k: d for k, d in delta.items() if d > 0}
    src_add = {}
    for k in sorted(added):
        if old_nums[k]:
            src_add[k] = "in rc16"
        elif k in der:
            src_add[k] = "derived: " + der[k]
        elif k in allowed:
            src_add[k] = "artifact: " + allowed[k]
        else:
            fails.append(f"numbers: token {k!r} added {added[k]}x is neither in rc16, nor an artifact leaf, nor derived")
    # 1 hunks
    hs = R11.hunks(old, new)
    for h in hs:
        ids = [aid for aid, anc in ANCHORS if anc in h["new"]]
        ids += [aid for anc, aid in REMOVED_ANCHORS if not h["new"].strip() and anc in h["old"]]
        h["ids"] = list(dict.fromkeys(ids))
        if not h["ids"]:
            fails.append(f"hunk rc16 {h['rc10']} rc17 {h['rc11']} has no ID: {(h['new'] or h['old'])[:80]!r}")
    # 3 invariants
    inv = {
        "§ cross-references": (collections.Counter(mo.group(0) for mo in R11.SECREF.finditer(ob)),
                               collections.Counter(mo.group(0) for mo in R11.SECREF.finditer(nb))),
        "code spans": (collections.Counter(R11.CODE.findall(ob)), collections.Counter(R11.CODE.findall(nb))),
        "italic quotations": (collections.Counter(R11.QUOTE.findall(ob)), collections.Counter(R11.QUOTE.findall(nb))),
        "straight-quoted strings": (collections.Counter(R14.STRAIGHT.findall(ob)), collections.Counter(R14.STRAIGHT.findall(nb))),
        "path-like tokens": (collections.Counter(R14.PATHLIKE.findall(ob)), collections.Counter(R14.PATHLIKE.findall(nb))),
        "citations": (collections.Counter(R11.CITE.findall(ob)), collections.Counter(R11.CITE.findall(nb))),
        "footnote markers": (collections.Counter(R14.FOOT.findall(ob)), collections.Counter(R14.FOOT.findall(nb))),
        "DOIs": (collections.Counter(R11.DOI.findall(ob)), collections.Counter(R11.DOI.findall(nb))),
        "struck spans": (collections.Counter(R14.STRUCK.findall(ob)), collections.Counter(R14.STRUCK.findall(nb))),
        "table lines": (collections.Counter(R14.TABLE.findall(ob)), collections.Counter(R14.TABLE.findall(nb))),
        "image links": (collections.Counter(R14.IMG.findall(ob)), collections.Counter(R14.IMG.findall(nb))),
    }
    for name, (a, b) in inv.items():
        d = {k: b[k] - a[k] for k in set(a) | set(b) if a[k] != b[k]}
        if name in DECL_INV:
            if d != DECL_INV[name]:
                fails.append(f"invariant: {name} delta {d} is not the declared {DECL_INV[name]}")
        elif name in INV_FIXED:
            if d:
                fails.append(f"invariant: {name} changed: {dict(list(d.items())[:4])}")
        rep.append(f"{name}: {sum(a.values())} -> {sum(b.values())}" + ("" if not d else f"  (delta {len(d)} items)"))
        if report and d and name in INV_FREE:
            for k, v in sorted(d.items(), key=lambda kv: str(kv[0]))[:40]:
                rep.append(f"    {v:+d} {str(k)[:150]}")
    TITLE_OLD = "# A registration that outlived its intervention:"
    TITLE_NEW = "# A registered horizon that outlived its intervention:"
    if R11.headings(old.replace(TITLE_OLD, TITLE_NEW, 1)) != R11.headings(new):
        fails.append("invariant: heading list changed (beyond the declared title change)")
    if not new.startswith(TITLE_NEW):
        fails.append("title: declared author title not on line 1")
    # 4 tail
    to, tn = tail(old), tail(new)
    t = tn
    for ins in TAIL_INSERTS:
        if t.count(ins) != 1:
            fails.append(f"tail: declared insertion not found exactly once: {ins.strip()[:60]!r}")
        t = t.replace(ins, "")
    i17 = t.find("\n\n**rc17: review of rc16 applied**")
    blocks17 = t[i17:] if i17 >= 0 else ""
    t = t[:i17] + "\n" if i17 >= 0 else t
    if i17 < 0:
        fails.append("tail: the rc17 changelog block is missing")
    if t != to:
        fails.append("tail: working list / changelog, with the declared insertion and the rc17 block removed, "
                     "is not byte-identical to rc16")
    i = tn.find("\n**rc14: writing pass**")
    nums = [int(x) for x in re.findall(r"^(\d+)\. ", tn[i:] if i >= 0 else "", re.M)]
    if nums != list(range(149, 164)):
        fails.append(f"tail: rc14-rc17 changelog items are {nums}, expected 149..163")
    if not re.search(r"^161\. Abstract, §1, §1\.1, §3\.0\.1, §7, §8\.5 and §9 \(Codex M1\)", blocks17, re.M):
        fails.append("tail: changelog item 161 (M1) missing")
    if "The title is\nnot changed; `APPLY-B-rc17.md` flags it for the author." not in blocks17:
        fails.append("tail: the rc17 block does not record that the title is flagged, not changed")
    # 5 SHAM
    so, eo = R11.sham_spans(old)
    sn, en = R11.sham_spans(new)
    fails += eo + en
    if len(sn) != R11.EXPECTED_SHAM or len(so) != R11.EXPECTED_SHAM:
        fails.append(f"sham: {len(sn)} blocks in rc17 and {len(so)} in rc16, expected {R11.EXPECTED_SHAM}")
    for k, (x, y) in enumerate(zip(so, sn), 1):
        if x != y:
            fails.append(f"sham: block {k} ({y.strip()[:50]!r}…) is not byte-identical to rc16")
    # 6 carried locks + rc17
    fails += R13.claims_rc13(new, cz)
    nb_unstruck = R11.strip_struck(nb)
    fn_unstruck = flat(nb_unstruck)
    for pat, why in R15.SWEEP_LOCK + R16.SWEEP_LOCK_RC16 + SWEEP_LOCK_RC17:
        for mo in re.finditer(pat, fn_unstruck):
            fails.append(f"sweep: {why}: {fn_unstruck[max(0, mo.start() - 60):mo.end() + 30]!r}")
    head = new[:new.find("\n---")]
    for mk in STATUS_MARKS_RC17:
        if mk not in head:
            fails.append(f"status: header does not record {mk.splitlines()[0]!r}")
    for pat, why in STATUS_LOCK:
        if re.search(pat, flat(head.replace("> ", " "))):
            fails.append(f"status: {why}")
    carried = [p for p in R15.PRESENT if p[0] not in R16.PRESENT_REPLACED] + R16.PRESENT_RC16
    for txt, why in [p for p in carried if p[0] not in PRESENT_REPLACED] + PRESENT_RC17:
        if flat(txt) not in fn_unstruck:
            fails.append(f"present: {why} sentence missing: {txt[:70]!r}")
    # 7 qualifier set (rc16's = rc15's locked phrases; the same artifacts on both sides)
    h15 = R15.headlines(A, cz, "rc15")
    fo, fnn = flat(old), flat(new)
    locked = list(dict.fromkeys(R14.QUALIFIERS + R14.CENSUS_MARKS + [flat(v) for v in h15.values()]))
    pdeltas = {}
    for ph in locked:
        a, b = fo.count(ph), fnn.count(ph)
        if a != b:
            pdeltas[ph] = b - a
            if (ph, b - a) not in JUSTIFIED_PHRASE:
                fails.append(f"qualifier: {ph[:70]!r} occurs {b}x in rc17 against {a}x in rc16, not justified")
    for (ph, d) in JUSTIFIED_PHRASE:
        if pdeltas.get(ph) != d:
            fails.append(f"qualifier: JUSTIFIED_PHRASE lists {ph[:50]!r} {d:+d}; measured {pdeltas.get(ph, 0):+d}")
    gone = {ph for (ph, d) in list(JUSTIFIED_PHRASE) + list(R16.JUSTIFIED_PHRASE) + list(R15.JUSTIFIED_PHRASE)
            if d < 0 and fnn.count(ph) == 0}
    for k, v in h15.items():
        if flat(v) not in fnn and flat(v) not in gone:
            fails.append(f"headline: {k} — {v[:80]!r} not found in rc17")
    ho, hn = R14.hedge_counts(old), R14.hedge_counts(new)
    hd = {w: hn[w] - ho[w] for w in R14.HEDGE if hn[w] != ho[w]}

    def hc(t_):
        w = collections.Counter(re.findall(r"[a-z][a-z\-]*", R11.strip_struck(t_).lower()))
        return {x: w.get(x, 0) for x in R14.HEDGE}
    per = collections.defaultdict(collections.Counter)
    cut = len(body(new).splitlines())
    for h in hs:
        if h["rc11"][0] > cut:
            continue
        a_, b_ = hc(h["old"]), hc(h["new"])
        key = "+".join(h["ids"]) or "?"
        for w in R14.HEDGE:
            if b_[w] != a_[w]:
                per[key][w] += b_[w] - a_[w]
    per = {k: {w: d for w, d in v.items() if d} for k, v in per.items()}
    per = {k: v for k, v in per.items() if v}
    for k in sorted(set(per) | set(JUSTIFIED_HEDGE)):
        if per.get(k, {}) != JUSTIFIED_HEDGE.get(k, ({}, ""))[0]:
            fails.append(f"hedge: hunks [{k}] move hedge words by {per.get(k, {})}; JUSTIFIED_HEDGE declares "
                         f"{JUSTIFIED_HEDGE.get(k, ({}, ''))[0]}")
    tot = collections.Counter()
    for v in per.values():
        tot.update(v)
    if {w: d for w, d in tot.items() if d} != hd:
        fails.append(f"hedge: per-hunk deltas {dict(tot)} do not add up to the body delta {hd}")
    rep.append(f"locked phrases: {len(locked)} (rc16's); justified deltas: {pdeltas}; hedge deltas: {hd}")
    if report:
        for k, v in sorted(per.items()):
            rep.append(f"  hedge [{k}]: {v}")
    # 8 integrity: rc16's carried checks, RESULTADO-v4.md read as its frozen rc16 bytes
    fails += R11.script_integrity(**R11.load_integrity_inputs())
    fails += R12.census_integrity(cz)
    st2, f_res = R15.resultado_reverted(st)
    fails += f_res
    f15, warns = R13.paths_integrity(st2)
    fails += f15
    files_rc16 = dict(files, res4=files["res4_frozen"])
    A15 = dict(A, teste=json.loads(files15["json"]))
    fails += R15.v4_integrity(A15, new, dict(files_rc16, testepy=files15["py"], teste=files15["json"]))
    fails += R16.test_integrity(A, new, files_rc16, files15)
    fails += res4_integrity(files, new)
    if sci(A["teste"]["max_dif_cru"]) not in RES_NOTE:
        fails.append("res4: the note does not cite the largest unrounded difference")
    fails += source_facts(src)
    # 9 REANALISE, bold
    if R11.R_ANY.search(new):
        fails.append("reanalise: a REANALISE marker is present in rc17")
    noncode = re.sub(r"```.*?```", "", new, flags=re.S)
    for k, para in enumerate(re.split(r"\n\s*\n", noncode)):
        if para.count("**") % 2:
            fails.append(f"bold: odd number of ** in paragraph {k}: {para.strip()[:60]!r}")
    if verbose:
        print(f"hunks: {len(hs)}, all with an ID: {all(h['ids'] for h in hs)} "
              f"({sorted({i for h in hs for i in h['ids']})})")
        for r in rep:
            print(r)
        print(f"headings: {len(R11.headings(new))}, unchanged: {R11.headings(old) == R11.headings(new)}")
        print(f"SHAM-JANELA blocks: {len(sn)}, byte-identical to rc16: {sum(1 for x, y in zip(so, sn) if x == y)}")
        print(f"words: rc16 {len(old.split())} (body {len(body(old).split())}), "
              f"rc17 {len(new.split())} (body {len(body(new).split())})")
        for w in warns:
            print(w)
    if report:
        print("\nnumeric tokens added (and their source):")
        for k in sorted(added):
            print(f"  +{added[k]} {k}: {src_add.get(k, 'UNSOURCED')}")
        print("numeric tokens removed:", removed)
        print("phrase deltas:", pdeltas)
        for h in hs:
            print(f"\n[{'+'.join(h['ids']) or '?'}] rc16 l.{h['rc10'][0]}-{h['rc10'][1]} -> rc17 l.{h['rc11'][0]}-{h['rc11'][1]}")
            print("  - " + "\n  - ".join(h["old"].splitlines()[:6]))
            print("  + " + "\n  + ".join(h["new"].splitlines()[:6]))
    return fails


def main():
    old, new = OLD.read_text(encoding="utf-8"), NEW.read_text(encoding="utf-8")
    if "--report" in sys.argv:
        f = check(old, new, verbose=True, report=True)
        print("\n" + ("\n".join("FAIL " + x for x in f) or "no failures"))
        return 0
    if "--self-test" in sys.argv:
        return self_test(old, new)
    fails = check(old, new)
    for f in fails:
        print("FAIL", f)
    print("PARITY: PASS" if not fails else f"PARITY: FAIL ({len(fails)})")
    return 0 if not fails else 1


def self_test(old, new):
    cz, st, A = R13.load_rc13(), R13.load_paths(), load()
    files = {k: p.read_bytes() for k, p in R15.ART.items()}
    files["res4_frozen"] = RES4_FROZEN.read_bytes()
    files15 = {"py": R16.FROZEN_TEST_PY.read_bytes(), "json": R16.FROZEN_TEST_JSON.read_bytes()}
    src = {k: p.read_text(encoding="utf-8") for k, p in SOURCES.items()}
    rep1 = lambda a, b: (new.replace(a, b, 1), a in new)  # noqa: E731
    mutations = [
        ("M1: Abstract 'property of the registration' restored", rep1(
            "This incompatibility was present before the trial\nbegan, and the under-powering of this study follows "
            "from it, not from the realized window.",
            "The under-powering of this\nstudy follows from that, and it is a property of the registration, not of "
            "the realized\nwindow.")),
        ("M1: Abstract 'The registration outlived its intervention' restored", rep1(
            "The trial retained the registered 234-epoch horizon\nwhile adopting",
            "The registration outlived its intervention. The trial retained the registered 234-epoch horizon\nwhile adopting")),
        ("M1: §1 'a fixed set of designated items' restored", rep1(
            "designated memory chunks (items). Its designation rule",
            "a fixed set of designated items (memory chunks). Its designation rule")),
        ("M1: §1 times dropped", rep1("v1.12 was\npublished at 14:01Z, the replacement rule was decided at 14:47Z\n",
                                      "v1.12 was\npublished earlier, the replacement rule was decided later\n")),
        ("M1: §3.0.1 'same shape … larger object' restored", rep1(
            "this is\na mismatch between the registered horizon and the intervention frozen after it.",
            "the same shape as the H1b collision of\n§4.4, on a larger object.")),
        ("M1: §8.5 'each contradicted another lock' restored", rep1(
            "an\ninternal contradiction in the registered estimand (§4.4), and a mismatch between the\nregistered horizon "
            "and the subsequently frozen intervention (§3.0.1).",
            "each\nlooked complete alone and each contradicted another lock of the same registration.")),
        ("M1: §8.5 'inconsistencies in its own registration' restored", rep1(
            "collisions between its own locks.", "inconsistencies in its own registration.")),
        ("M1: §9 'twice here, at two scales' restored", rep1(
            "One contradiction was internal to the registration: two",
            "It happened twice here, at two scales. Two")),
        ("M1: §7 back to 'the registration outlived'", rep1(
            "the registered horizon outlived the\nintervention the trial ran (§3.0.1),",
            "the registration outlived its\nintervention (§3.0.1),")),
        ("LV: Abstract 'every earlier version' restored", rep1("a rejection in versions up to rc9, and returns",
                                                               "a rejection in every earlier version, and returns")),
        ("LV: §9 'every earlier version' restored", rep1("in versions\nup to rc9, whose analyses",
                                                         "in every\nearlier version, whose analyses")),
        ("LV: Abstract 'every earlier version of this analysis' restored", rep1(
            "H1 did reject in versions\nup to rc9 of this analysis", "H1 did reject in every\nearlier version of this analysis")),
        ("LB1: accelerations dropped from B.1", rep1("the BCa intervals, accelerations and adjusted quantiles equal",
                                                     "the BCa intervals and adjusted quantiles equal")),
        ("FD: DEVIATIONS clause dropped", rep1(
            " `DEVIATIONS-FOR-PAPER.md` still carries\nthe withdrawn reading in its front table (the band row, marked ⬇): it "
            "is a dated,\nappend-only log, and it is not edited.", "")),
        ("FN: nesting attribution reverted", rep1(
            "the H1b lock of\n2026-08-16 in §1 of the pre-registration (PREREG l.308) calls",
            "§1 of the\npre-registration calls")),
        ("FR: App. B rc17 note dropped", rep1(
            " *(rc17: `RESULTADO-v4.md` now ends with a dated note naming the rc16 test bytes; nothing above the note "
            "was edited, so every hash it records still resolves.)*", "")),
        ("status header without rc17", rep1("rc17 prepared 2026-10-05 (review of rc16 applied:",
                                            "rc17 drafted 2026-10-05 (review of rc16 applied:")),
        ("changelog: title flag dropped", rep1("The title is\nnot changed; `APPLY-B-rc17.md` flags it for the author.",
                                               "The title is\nnot changed.")),
        ("changelog item 163 removed", rep1("\n163. Appendix A (Fable LOW)", "\nAppendix A (Fable LOW)")),
        ("old changelog line edited", rep1("**rc16: review of rc15 applied**", "**rc16: review of rc15 applied (edited)**")),
        ("SHAM-JANELA block changed", rep1("**Our error, stated.**", "**Our error.**")),
        ("hedge 'not' removed (M1 §3.0.1)", rep1("it is not a\ncontradiction inside the registration either",
                                                 "it is a\ncontradiction inside the registration either")),
        ("carried rc16: 'heavy in the tail' restored", rep1(
            "its contribution to estimator variance has not been quantified.",
            "which is unbiased in expectation and heavy in the tail.")),
        ("carried rc13: abstract back to two commitments", rep1("Three commitments made before the seed",
                                                               "Two commitments made before the seed")),
        ("carried rc11: H1a presented as rejected", rep1("and it is not rejected. Sources:", "and it is rejected. Sources:")),
        ("italic quotation removed", rep1("reading\n*\"what does not move, and could not\"* (PREREG", "reading\nthe phrase (PREREG")),
        ("citation removed", rep1(" [@kaplan2015nullnhlbi]", "")),
        ("unsourced number added", rep1("decided at 14:47Z", "decided at 14:48Z")),
        ("unmapped hunk with no anchor", rep1("**Benchmarks compare systems on fixed tasks.**",
                                               "Benchmarks are compared.\n\n**Benchmarks compare systems on fixed tasks.**")),
    ]
    ok = True
    for name, (mutated, applied) in mutations:
        assert applied and mutated != new, f"mutation did not apply: {name}"
        f = [x for x in check(old, mutated, verbose=False, cz=cz, st=st, A=A, files=files, files15=files15, src=src)
             if name.startswith("unmapped") or "has no ID" not in x]
        print(f"mutation [{name}]: {'CAUGHT' if f else 'MISSED'}" + (f" -> {f[0][:140]}" if f else ""))
        ok &= bool(f)
    # integrity and source mutations (in memory)
    note_b = RES_NOTE.encode()
    integ = [
        ("RESULTADO-v4 edited above the note", dict(files=dict(files, res4=files["res4"].replace(b"bb9c3197", b"deadbeef", 1)))),
        ("RESULTADO-v4 note missing", dict(files=dict(files, res4=files["res4_frozen"]))),
        ("RESULTADO-v4 note altered", dict(files=dict(files, res4=files["res4_frozen"] + note_b.replace(b"d4d960db", b"d4d960dc")))),
        ("frozen RESULTADO-v4 copy altered", dict(files=dict(files, res4_frozen=files["res4_frozen"] + b"\n",
                                                             res4=files["res4_frozen"] + b"\n" + note_b))),
        ("carried rc16: frozen rc15 test copy altered", dict(files15=dict(files15, py=files15["py"] + b"\n"))),
        ("source: v1.12 publication time changed", dict(src=dict(src, plan13=src["plan13"].replace("T14:01Z", "T21:01Z")))),
        ("source: amendment no longer says recomputed at every brief", dict(src=dict(src, amend=src["amend"].replace(
            "**é recomputada a cada brief**", "**é fixa**")))),
        ("source: prospective estimand places the resolution inside", dict(src=dict(src, prosp=src["prosp"].replace(
            "A resolução vive **fora** do registro", "A resolução vive dentro do registro")))),
        ("source: PREREG nesting sentence moved out of §1", dict(src=dict(src, prereg=src["prereg"].replace(
            "## 1. Study Information", "## 0b. Study Information")))),
        ("source: DEVIATIONS band row no longer ⬇", dict(src=dict(src, dev=src["dev"].replace(
            "a saturação, que fica em `(4,0 ; 4,4]` | ⬇ |", "a saturação, que fica em `(4,0 ; 4,4]` | ⬆ |")))),
    ]
    for name, kw in integ:
        args = dict(cz=cz, st=st, A=A, files=files, files15=files15, src=src)
        args.update(kw)
        f = check(old, new, verbose=False, **args)
        print(f"mutation [{name}] (integrity): {'CAUGHT' if f else 'MISSED'}" + (f" -> {f[0][:140]}" if f else ""))
        ok &= bool(f)
    base = check(old, new, verbose=False, cz=cz, st=st, A=A, files=files, files15=files15, src=src)
    print(f"unmutated rc17: {'PASS' if not base else 'FAIL'}" + (f" -> {base}" if base else ""))
    print(f"mutations: {len(mutations) + len(integ)}")
    return 0 if ok and not base else 1


if __name__ == "__main__":
    sys.exit(main())
