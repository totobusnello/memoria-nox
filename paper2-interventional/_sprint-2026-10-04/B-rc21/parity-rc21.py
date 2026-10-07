#!/usr/bin/env python3
"""Parity check B-v2-rc20.md -> B-v2-rc21.md (Paper B, sprint 2026-10-04; rc21 2026-10-06).

rc21 applies the Fable read of rc20 (NO-GO, two MEDIUM, six LOW, no HIGH), each finding verified
against the manuscript and DEVIATIONS-FOR-PAPER.md first (`APPLY-B-rc21.md`). No number of the
analysis moves and no artifact of the analysis changes.

  M1  §3.0.1: "in a session that recorded it and left the design decision open" -> "on the day the
      decision was taken not to widen the window and so to end the trial at the `09-20` epoch"
      (§10.13 morning decision to widen, §10.14 its reversal, §10.22 the instruction). Adapted:
      "on the day", not "in the session" (the log does not establish one session).
  M2  Abstract: "Three commitments made before the seed were not kept" -> "Three further
      commitments …, besides the primary outcome and the horizon above, were not kept".
  L1  §3.0: §10.14 and §10.22 named for what each holds; the instruction at 14:38 local time.
  L2  §3.0: "not a data-dependent stop" -> "not an outcome-dependent stop: it rested on
      measurements, not on outcomes, among them the expiry measurement and the instrument's
      positive-control reading of `09-08` (20 of 672 briefs changed)". Adapted: "among them".
  L3  §1.1: the closure-decision date added to "What requires trusting us".
  L4  §3.0.1: "could reach a designated item" -> "could have reached" (`09-20` is control).
  L5  rc20 changelog item 174: "which neither 234 epochs nor the calendar cap reached" -> "which
      was reached by neither 234 epochs nor the calendar cap" (declared tail edit).
  L6  §9: "while preparing this version" -> "while preparing rc8".

Checks (exit 1 if any fails): as rc20's (hunks, numbers, invariants, tail, SHAM-JANELA, carried
locks incl. title, "did not stop early" and the closure date CD, qualifiers/hedges, integrity
incl. S20), with the rc21 anchors, locks and the NEW source block S21.

Usage:  python3 parity-rc21.py | --report | --self-test     Reads; writes nothing.
"""
import collections
import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPRINT = HERE.parent
P2 = SPRINT.parent
OLD = SPRINT / "B-v2-rc20.md"
NEW = SPRINT / "B-v2-rc21.md"
RC20 = SPRINT / "B-rc20" / "parity-rc20.py"
RC20_SHA = "3210aa9577ae4694d9f19d1ba69b847af6398822e17a116193f0ec0e767f5006"
OLD_SHA = "617d90eaaaec303c081db8765a86c1f06932639b73cf836584cb409e3e806770"

assert hashlib.sha256(RC20.read_bytes()).hexdigest() == RC20_SHA, \
    "parity-rc20.py changed: the locks carried from it are no longer the ones rc20 ran"
_spec = importlib.util.spec_from_file_location("parity_rc20", RC20)
R20 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(R20)          # also installs appa_count_rc20 (count 12, horizon item)
R19, R18, R17 = R20.R19, R20.R18, R20.R17
R16, R15, R14, R13, R12, R11 = R17.R16, R17.R15, R17.R14, R17.R13, R17.R12, R17.R11
flat, body, tail, sci, load = R17.flat, R17.body, R17.tail, R17.sci, R17.load
TITLE, TITLE_OLD = R18.TITLE, R18.TITLE_OLD

SOURCES21 = {
    "dev": P2 / "DEVIATIONS-FOR-PAPER.md",
    "ctl": P2 / "out" / "CONTROLES-2026-09-10.json",
    "v4": P2 / "out" / "ITT-REGISTRADO-v4-2026-10-05.json",
    "exp": P2 / "out" / "expiracao-designados-2026-09-09.json",
}


def load_src21():
    return {k: p.read_text(encoding="utf-8") for k, p in SOURCES21.items()}


# ---------------------------------------------------------------- S21: the facts rc21 rests on
def source_facts_rc21(src, new):
    fails = []
    dv = src["dev"]
    # M1: §10.13 morning decision to widen, reverted the same day by §10.14
    if "Escolhido: **alargar a janela do pool global**" not in dv \
            or "A primeira metade desta decisão foi REVERTIDA no mesmo dia — ver §10.14." not in dv:
        fails.append("S21/M1: DEVIATIONS §10.13 no longer records the morning decision to widen and its reversal")
    if "#### 10.14 Decisão revisada (2026-09-09, tarde): **não alargar a janela**. O ensaio termina em 2026-09-20" not in dv:
        fails.append("S21/M1: DEVIATIONS §10.14 heading (2026-09-09, not widening, end 2026-09-20) changed")
    # the expiry measurement is dated 2026-09-09 (eleven days before 2026-09-20)
    if not json.loads(src["exp"]).get("ts", "").startswith("2026-09-09T"):
        fails.append("S21/M1: the expiry measurement is not dated 2026-09-09")
    # L1/L3: the instruction at 14:38 BRT (= local time, UTC-3) on 2026-09-09
    if "Toto, 2026-09-09 14:38 BRT:" not in dv or "> **\"encerra 20/09 mesmo, e desliga a dose depois\"**" not in dv:
        fails.append("S21/L1: DEVIATIONS §10.22 no longer dates the instruction 2026-09-09 14:38 BRT")
    # L2: §10.14 rests on the 09-08 positive control, 20/672; the artifact agrees; §10.15 correction
    if "(`churn>0` em 20/672 no epoch 09-08)" not in dv:
        fails.append("S21/L2: DEVIATIONS §10.14 no longer cites churn>0 in 20/672 at 09-08")
    if "O FUNDAMENTO desta seção foi corrigido pelo §10.15 (mesma tarde)." not in dv:
        fails.append("S21/L2: the §10.15 correction note on §10.14 is gone; 'among them' needs rereading")
    e08 = json.loads(src["ctl"])["por_epoch"]["2026-09-08"]
    if (e08["braco"], e08["mexeu"], e08["n"]) != ("treatment", 20, 672):
        fails.append(f"S21/L2: CONTROLES 09-08 is {e08}, not treatment 20/672")
    # L3: the dry-run receipt 2026-09-09 17:42:31Z, after 14:38 BRT = 17:38Z
    if "um teste manual de **2026-09-09 17:42:31Z** deixou lá\n  `YELLOW p2-desliga-dose motivo=janela-ainda-aberta-faltam-279h`" not in dv:
        fails.append("S21/L3: DEVIATIONS §10.28 no longer quotes the 2026-09-09 17:42:31Z dry-run receipt")
    # L4: 09-20 is a control epoch
    if json.loads(src["v4"])["pernas"]["registrado"]["por_epoch"]["2026-09-20"]["braco"] != "control":
        fails.append("S21/L4: 09-20 is not a control epoch")
    # L6: the stop was found in rc8 (changelog item 104 in the rc8 block)
    t = tail(new)
    i8, i9 = t.find("**rc8: the registered analysis reported"), t.find("**rc9: review of rc8 applied**")
    if not (0 <= i8 < i9) or "104. §3.0 (struck sentence and a new correction)" not in t[i8:i9] \
            or "§3-bis was met in Epoch 1" not in flat(t[i8:i9]):
        fails.append("S21/L6: the rc8 changelog block no longer records the stopping rule (item 104)")
    # M2: the Abstract names the primary switch and the horizon before the 'Three further' sentence
    ab = flat(R13.section(new, "\n## Abstract", "\n## 1. "))
    k = ab.find("Three further commitments made before the seed")
    if k < 0 or not (0 <= ab.find("It is therefore a deviation from the public registration") < k) \
            or not (0 <= ab.find("The trial ended before its registered 234-epoch horizon") < k):
        fails.append("S21/M2: the Abstract does not name the primary switch and the horizon before 'Three further'")
    return fails


# ---------------------------------------------------------------- 1: anchors
ANCHORS = [
    ("ST", "rc21 prepared 2026-10-06 (review"),
    ("M1", "on the day the decision was taken not to widen the window"),
    ("M2", "Three further commitments made before the seed, besides the primary outcome"),
    ("L1", "§10.14, the decision not to widen the window; §10.22, the author's"),
    ("L3", "The closure decision of §3.0 was taken on 2026-09-09, before any outcome was computed"),
    ("L4", "could have reached a\ndesignated item"),
    ("L6", "while preparing rc8 (met"),
    ("WL", "*(rc21: rc20 had one full read"),
    ("L5", "which was reached by neither"),
    ("CL", "**rc21: review of rc20 applied**"),
]
REMOVED_ANCHORS = []

# ---------------------------------------------------------------- 2: numbers
JUSTIFIED_REMOVED = {}


def derived_rc21(src):
    out = {str(n): "rc21 changelog item numbers" for n in range(178, 185)}
    out["104"] = "rc8 changelog item number (checked in S21)"
    for tok in ("10.13", "10.28", "10.15"):
        out[tok] = "DEVIATIONS section numbers (checked in S21)"
    for tok in ("14:38", "14", "38"):
        out[tok] = "§10.22 instruction time, 14:38 BRT (checked in S21)"
    for tok in ("17:42:31Z", "17:42:31", "17", "42", "31Z", "31"):
        out[tok] = "§10.28 dry-run receipt time (checked in S21)"
    out["2026-10-06"] = "rc21 date (status header)"
    return out


# ---------------------------------------------------------------- 3/4: tail
TAIL_INSERTS = [
    """
    *(rc21: rc20 had one full read, Fable NO-GO with two MEDIUM and six LOW and no HIGH; all
    verified, and applied or adapted in rc21 (`APPLY-B-rc21.md`). rc21 itself has not been
    reviewed.)*""",
]
TAIL_EDITS = [  # (rc20 text, rc21 text) inside the rc20 changelog block — Fable L5
    ("""data-collection horizon, which neither 234 epochs
    nor the calendar cap reached, and expiry""",
     """data-collection horizon, which was reached by neither
    234 epochs nor the calendar cap, and expiry"""),
]

# ---------------------------------------------------------------- 6: locks
SWEEP_LOCK_RC21 = [
    (r"(?i)data-dependent stop", "L2: not an outcome-dependent stop; it rested on measurements"),
    (r"(?i)left the design decision open", "M1: the decision was taken the same day"),
    (r"(?i)in a session that recorded it", "M1: on the day the decision was taken"),
    (r"(?i)could reach a designated", "L4: could have reached (09-20 is control)"),
    (r"(?i)while preparing this version", "L6: the stop was found while preparing rc8"),
    (r"Three commitments made before the seed were not kept", "M2: three further commitments"),
    (r"(?i)the author's explicit instruction\)", "L1: the instruction is dated"),
    (r"(?i)decision taken on 2026-09-21", "CD: the closure was decided on 2026-09-09"),
]
PRESENT_RC21 = [
    ("This was measurable on 2026-09-09 and was measured then, eleven days before the close, on the day "
     "the decision was taken not to widen the window and so to end the trial at the `09-20` epoch (§3.0; "
     "DEVIATIONS §10.13, §10.14, §10.22).", "M1 §3.0.1"),
    ("Three further commitments made before the seed, besides the primary outcome and the horizon above, "
     "were not kept. One, a stopping rule, we found only after the trial, from the artifacts.", "M2 Abstract"),
    ("The trial closed at the `2026-09-20` epoch by a decision taken on 2026-09-09 "
     "(`DEVIATIONS-FOR-PAPER.md` §10.14, the decision not to widen the window; §10.22, the author's "
     "explicit instruction of 14:38 local time, UTC−3), executed on 2026-09-21 by `desliga-dose-p2.sh` at "
     "09:43:05Z (§10.29).", "L1 + CD §3.0 (closure date carried)"),
    ("It was not an outcome-dependent stop: it rested on measurements, not on outcomes, among them the "
     "expiry measurement and the instrument's positive-control reading of `09-08` (20 of 672 briefs "
     "changed; §10.14). No outcome had been computed when it was taken, and the analysis specification "
     "that governs this report was written on 2026-09-10, the day after the decision", "L2 §3.0"),
    ("The closure decision of §3.0 was taken on 2026-09-09, before any outcome was computed; that date "
     "rests on the times written in our append-only deviation log (§10.14; §10.22, 14:38 local time) and "
     "on the switch-off script's dry-run receipt of 2026-09-09 17:42:31Z (§10.28).", "L3 §1.1"),
    ("It ran for the entire interval in which the dose could have reached a designated item", "L4 §3.0.1"),
    ("the feasibility stop we found from the artifacts while preparing rc8 (met in Epoch 1", "L6 §9"),
]
PRESENT_REPLACED = {}   # filled at import time below: carried presence locks rc21 rewrites
STATUS_MARKS_RC21 = R20.STATUS_MARKS_RC20 + ["rc21 prepared 2026-10-06 (review"]
STATUS_LOCK = R20.STATUS_LOCK
STRUCK_DELTA = {}

# ---------------------------------------------------------------- 7: qualifier deltas (from --report)
JUSTIFIED_PHRASE = {("Three commitments made before the seed were not kept.", -1):
                    "M2: the abstract sentence now reads 'Three further commitments …, besides the primary "
                    "outcome and the horizon above, were not kept.'"}
JUSTIFIED_HEDGE = {
    "L1": ({"not": 2}, "§3.0: 'the decision not to widen the window'; 'not an outcome-dependent stop' replaces 'not a "
                       "data-dependent stop'; 'measurements, not on outcomes'"),
    "M1": ({"not": 1}, "§3.0.1: 'the decision was taken not to widen the window'"),
    "L3": ({"any": 1}, "§1.1: 'before any outcome was computed'"),
    "ST": ({"any": 1}, "status header rc21: 'before any outcome'"),
}


def carried_present():
    carried = [p for p in R15.PRESENT if p[0] not in R16.PRESENT_REPLACED] + R16.PRESENT_RC16
    carried = [p for p in carried if p[0] not in R17.PRESENT_REPLACED] + R17.PRESENT_RC17
    carried = [p for p in carried if p[0] not in R18.PRESENT_REPLACED] + R18.PRESENT_RC18
    carried = [p for p in carried if p[0] not in R19.PRESENT_REPLACED] + R19.PRESENT_RC19
    carried = [p for p in carried if p[0] not in R20.PRESENT_REPLACED] + R20.PRESENT_RC20
    return [p for p in carried if p[0] not in PRESENT_REPLACED]


def check(old, new, verbose=True, report=False, cz=None, st=None, A=None, files=None, files15=None,
          src=None, src18=None, src19=None, src20=None, src21=None):
    cz = cz or R13.load_rc13()
    st = st or R13.load_paths()
    A = A or load()
    src = src or {k: p.read_text(encoding="utf-8") for k, p in R17.SOURCES.items()}
    src18 = src18 or R18.load_src18()
    src19 = src19 or R19.load_src19()
    src20 = src20 or R20.load_src20()
    src21 = src21 or load_src21()
    if files is None:
        files = {k: p.read_bytes() for k, p in R15.ART.items()}
        files["res4_frozen"] = R17.RES4_FROZEN.read_bytes()
    files15 = files15 or {"py": R16.FROZEN_TEST_PY.read_bytes(), "json": R16.FROZEN_TEST_JSON.read_bytes()}
    fails, rep = [], []
    if hashlib.sha256(old.encode()).hexdigest() != OLD_SHA:
        fails.append("rc20 is not the 617d90ea… bytes rc20's parity passed on")
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
    der = derived_rc21(src21)
    old_nums = R11.numbers(old)
    added = {k: d for k, d in delta.items() if d > 0}
    src_add = {}
    for k in sorted(added):
        if old_nums[k]:
            src_add[k] = "in rc20"
        elif k in der:
            src_add[k] = "derived: " + der[k]
        elif k in allowed:
            src_add[k] = "artifact: " + allowed[k]
        else:
            fails.append(f"numbers: token {k!r} added {added[k]}x is neither in rc20, nor an artifact leaf, nor derived")
    # 1 hunks
    hs = R11.hunks(old, new)
    for h in hs:
        ids = [aid for aid, anc in ANCHORS if anc in h["new"]]
        ids += [aid for anc, aid in REMOVED_ANCHORS if not h["new"].strip() and anc in h["old"]]
        h["ids"] = list(dict.fromkeys(ids))
        if not h["ids"]:
            fails.append(f"hunk rc20 {h['rc10']} rc21 {h['rc11']} has no ID: {(h['new'] or h['old'])[:80]!r}")
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
        if name == "struck spans":
            if d != STRUCK_DELTA:
                fails.append(f"invariant: struck spans moved by {d}; rc21 declares {STRUCK_DELTA}")
        elif name in R17.INV_FIXED and d:
            fails.append(f"invariant: {name} changed: {dict(list(d.items())[:4])}")
        rep.append(f"{name}: {sum(a.values())} -> {sum(b.values())}" + ("" if not d else f"  (delta {len(d)} items)"))
        if report and d and (name in R17.INV_FREE or name == "struck spans"):
            for k, v in sorted(d.items(), key=lambda kv: str(kv[0]))[:40]:
                rep.append(f"    {v:+d} {str(k)[:150]}")
    if R11.headings(old) != R11.headings(new):
        fails.append("invariant: heading list changed (rc21 changes no heading)")
    if new.count(R20.H301_NEW) != 1:
        fails.append("invariant: the rc20 §3.0.1 heading is not in rc21 exactly once")
    if new.splitlines()[0] != TITLE:
        fails.append("title: line 1 is not the author's title of 2026-10-05")
    if TITLE_OLD in body(new):
        fails.append("title: the old title appears in the body")
    # 4 tail
    to, tn = tail(old), tail(new)
    t = tn
    for ins in TAIL_INSERTS:
        if t.count(ins) != 1:
            fails.append(f"tail: declared insertion not found exactly once: {ins.strip()[:60]!r}")
        t = t.replace(ins, "")
    for a, b in TAIL_EDITS:
        if t.count(b) != 1:
            fails.append(f"tail: declared rc20-block edit not found exactly once: {b[:60]!r}")
        t = t.replace(b, a)
    i21 = t.find("\n\n**rc21: review of rc20 applied**")
    blocks21 = t[i21:] if i21 >= 0 else ""
    t = t[:i21] + "\n" if i21 >= 0 else t
    if i21 < 0:
        fails.append("tail: the rc21 changelog block is missing")
    if t != to:
        fails.append("tail: working list / changelog, with the declared insertion and edit reverted and the rc21 "
                     "block removed, is not byte-identical to rc20")
    i = tn.find("\n**rc14: writing pass**")
    nums = [int(x) for x in re.findall(r"^(\d+)\. ", tn[i:] if i >= 0 else "", re.M)]
    if nums != list(range(149, 185)):
        fails.append(f"tail: rc14-rc21 changelog items are {nums}, expected 149..184")
    for n, needle in ((178, "§3.0.1 (Fable M-1)"), (179, "Abstract (Fable M-2)"), (180, "§3.0 (Fable L1, L2)"),
                      (181, "§1.1 (Fable L3)"), (182, "§3.0.1 (Fable L4)"),
                      (183, "rc20 changelog item 174 (Fable L5)"), (184, "§9 (Fable L6)")):
        if not re.search(rf"^{n}\. {re.escape(needle)}", blocks21, re.M):
            fails.append(f"tail: changelog item {n} missing")
    if "NO-GO with two MEDIUM and six" not in flat(blocks21) or "_sprint-2026-10-04/APPLY-B-rc21.md`" not in flat(blocks21):
        fails.append("tail: the rc21 block does not name the Fable verdict and the APPLY record")
    # 5 SHAM
    so, eo = R11.sham_spans(old)
    sn, en = R11.sham_spans(new)
    fails += eo + en
    if len(sn) != R11.EXPECTED_SHAM or len(so) != R11.EXPECTED_SHAM:
        fails.append(f"sham: {len(sn)} blocks in rc21 and {len(so)} in rc20, expected {R11.EXPECTED_SHAM}")
    for k, (x, y) in enumerate(zip(so, sn), 1):
        if x != y:
            fails.append(f"sham: block {k} ({y.strip()[:50]!r}…) is not byte-identical to rc20")
    # 6 carried locks + rc21
    fails += R13.claims_rc13(new, cz)
    nb_unstruck = R11.strip_struck(nb)
    fn_unstruck = flat(nb_unstruck)
    for pat, why in (R15.SWEEP_LOCK + R16.SWEEP_LOCK_RC16 + R17.SWEEP_LOCK_RC17 + R18.SWEEP_LOCK_RC18
                     + R19.SWEEP_LOCK_RC19 + R20.SWEEP_LOCK_RC20 + SWEEP_LOCK_RC21):
        for mo in re.finditer(pat, fn_unstruck):
            fails.append(f"sweep: {why}: {fn_unstruck[max(0, mo.start() - 60):mo.end() + 30]!r}")
    head = new[:new.find("\n---")]
    for mk in STATUS_MARKS_RC21:
        if mk not in head and flat(mk) not in flat(head.replace("> ", " ")):
            fails.append(f"status: header does not record {mk.splitlines()[0]!r}")
    for pat, why in STATUS_LOCK:
        if re.search(pat, flat(head.replace("> ", " "))):
            fails.append(f"status: {why}")
    for txt, why in carried_present() + PRESENT_RC21:
        if flat(txt) not in fn_unstruck:
            fails.append(f"present: {why} sentence missing: {txt[:70]!r}")
    for txt in PRESENT_REPLACED:
        if flat(txt) in fn_unstruck:
            fails.append(f"present: replaced rc20 text still present: {txt[:70]!r}")
    # 7 qualifier set
    h15 = R15.headlines(A, cz, "rc15")
    fo, fnn = flat(old), flat(new)
    locked = list(dict.fromkeys(R14.QUALIFIERS + R14.CENSUS_MARKS + [flat(v) for v in h15.values()]))
    pdeltas = {}
    for ph in locked:
        a, b = fo.count(ph), fnn.count(ph)
        if a != b:
            pdeltas[ph] = b - a
            if (ph, b - a) not in JUSTIFIED_PHRASE:
                fails.append(f"qualifier: {ph[:70]!r} occurs {b}x in rc21 against {a}x in rc20, not justified")
    for (ph, d) in JUSTIFIED_PHRASE:
        if pdeltas.get(ph) != d:
            fails.append(f"qualifier: JUSTIFIED_PHRASE lists {ph[:50]!r} {d:+d}; measured {pdeltas.get(ph, 0):+d}")
    gone = {ph for (ph, d) in list(JUSTIFIED_PHRASE) + list(R20.JUSTIFIED_PHRASE) + list(R19.JUSTIFIED_PHRASE)
            + list(R18.JUSTIFIED_PHRASE) + list(R17.JUSTIFIED_PHRASE) + list(R16.JUSTIFIED_PHRASE)
            + list(R15.JUSTIFIED_PHRASE) if d < 0 and fnn.count(ph) == 0}
    for k, v in h15.items():
        if flat(v) not in fnn and flat(v) not in gone:
            fails.append(f"headline: {k} — {v[:80]!r} not found in rc21")
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
    rep.append(f"locked phrases: {len(locked)} (rc20's); justified deltas: {pdeltas}; hedge deltas: {hd}")
    if report:
        for k, v in sorted(per.items()):
            rep.append(f"  hedge [{k}]: {v}")
    # 8 integrity: rc20's carried checks (incl. S, S18, S19, S20), then S21
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
    fails += R17.res4_integrity(files, new)
    if sci(A["teste"]["max_dif_cru"]) not in R17.RES_NOTE:
        fails.append("res4: the note does not cite the largest unrounded difference")
    fails += R17.source_facts(src)
    fails += R18.source_facts_rc18(src18)
    f19, w19 = R19.source_facts_rc19(src19)
    f20, w20 = R20.source_facts_rc20(src20)
    fails += f19 + f20 + source_facts_rc21(src21, new)
    warns = list(warns) + w19 + w20
    # 9 REANALISE, bold
    if R11.R_ANY.search(new):
        fails.append("reanalise: a REANALISE marker is present in rc21")
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
        print(f"SHAM-JANELA blocks: {len(sn)}, byte-identical to rc20: {sum(1 for x, y in zip(so, sn) if x == y)}")
        print(f"words: rc20 {len(old.split())} (body {len(body(old).split())}), "
              f"rc21 {len(new.split())} (body {len(body(new).split())})")
        for w in warns:
            print(w)
    if report:
        print("\nnumeric tokens added (and their source):")
        for k in sorted(added):
            print(f"  +{added[k]} {k}: {src_add.get(k, 'UNSOURCED')}")
        print("numeric tokens removed:", removed)
        print("phrase deltas:", pdeltas)
        for h in hs:
            print(f"\n[{'+'.join(h['ids']) or '?'}] rc20 l.{h['rc10'][0]}-{h['rc10'][1]} -> rc21 l.{h['rc11'][0]}-{h['rc11'][1]}")
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
    files["res4_frozen"] = R17.RES4_FROZEN.read_bytes()
    files15 = {"py": R16.FROZEN_TEST_PY.read_bytes(), "json": R16.FROZEN_TEST_JSON.read_bytes()}
    src = {k: p.read_text(encoding="utf-8") for k, p in R17.SOURCES.items()}
    src18, src19, src20, src21 = R18.load_src18(), R19.load_src19(), R20.load_src20(), load_src21()
    rep1 = lambda a, b: (new.replace(a, b, 1), a in new)  # noqa: E731
    mutations = [
        ("M1: 'left the design decision open' restored", rep1(
            "on the day the decision was taken not to widen the window and so to end the trial\nat the `09-20` "
            "epoch (§3.0; DEVIATIONS §10.13, §10.14, §10.22).", "in a session that recorded it and left the "
            "design decision open.")),
        ("M1: sources dropped", rep1(" (§3.0; DEVIATIONS §10.13, §10.14, §10.22).", ".")),
        ("M2: abstract back to 'Three commitments'", rep1(
            "Three further commitments made before the seed, besides the primary outcome and the horizon\nabove, "
            "were not kept.", "Three commitments made before the seed were not kept.")),
        ("M2: 'besides … the horizon above' dropped", rep1(
            "Three further commitments made before the seed, besides the primary outcome and the horizon\nabove, "
            "were not kept.", "Three further commitments made before the seed were not kept.")),
        ("L1: undated instruction restored", rep1(
            "§10.14, the decision not to widen the window; §10.22, the author's\nexplicit instruction of 14:38 "
            "local time, UTC−3)", "§10.14 and §10.22, the author's explicit instruction)")),
        ("L1: wrong instruction time", rep1("instruction of 14:38 local time", "instruction of 16:38 local time")),
        ("L2: 'data-dependent stop' restored", rep1("It was not an outcome-dependent stop",
                                                    "It was not a data-dependent stop")),
        ("L2: positive-control reading dropped", rep1(
            " among them the expiry measurement and the instrument's\npositive-control reading of `09-08` (20 of "
            "672 briefs changed; §10.14).", " the expiry measurement.")),
        ("CD: closure decision dated 2026-09-21 again", rep1("by a decision taken on 2026-09-09",
                                                             "by a decision taken on 2026-09-21")),
        ("L3: trust clause dropped", rep1(
            "The closure decision of §3.0 was taken on 2026-09-09, before any outcome was computed; that\n", "")),
        ("L3: wrong receipt time", rep1("dry-run receipt of 2026-09-09 17:42:31Z", "dry-run receipt of 2026-09-09 17:24:31Z")),
        ("L4: 'could reach' restored", rep1("could have reached a\ndesignated item", "could reach a designated\nitem")),
        ("L6: 'this version' restored", rep1("while preparing rc8 (met", "while preparing this version (met")),
        ("carried rc20: 'did not stop early' slipped back", rep1(
            "a limitation fixed before Epoch 1. All 19", "a limitation fixed before Epoch 1. It did not stop early. All 19")),
        ("carried rc20: horizon item dropped from Appendix A", rep1(
            "- the horizon: data collection ended after 20 randomized epochs, before either deposited\n", "- ")),
        ("carried title lock", rep1(TITLE, TITLE.replace("A registered horizon that", "A registration that"))),
        ("L5: changelog item 174 edit reverted", rep1(
            "which was reached by neither\n    234 epochs nor the calendar cap,", "which neither 234 epochs\n    nor "
            "the calendar cap reached,")),
        ("WL: working list 24 rc21 note dropped", rep1(TAIL_INSERTS[0], "")),
        ("CL: changelog item 181 removed", rep1("\n181. §1.1 (Fable L3)", "\n§1.1 (Fable L3)")),
        ("old changelog line edited", rep1("**rc20: review of rc19 applied**", "**rc20: review of rc19 applied (edited)**")),
        ("status header without rc21", rep1("rc21 prepared 2026-10-06 (review", "rc21 drafted 2026-10-06 (review")),
        ("a heading changed", rep1("### 3.0 The stopping rule, and the feasibility question it raises",
                                   "### 3.0 The stopping rule")),
        ("SHAM-JANELA block changed", rep1("**Our error, stated.**", "**Our error.**")),
        ("struck span added", rep1("~~Eleven~~ Twelve", "~~Eleven~~ ~~Twelve~~ Twelve")),
        ("italic quotation removed", rep1("reading\n*\"what does not move, and could not\"* (PREREG", "reading\nthe phrase (PREREG")),
        ("unsourced number added", rep1("It ran for the entire interval in which", "It ran for the entire interval (8317 h) in which")),
        ("unmapped hunk with no anchor", rep1("**Benchmarks compare systems on fixed tasks.**",
                                               "Benchmarks are compared.\n\n**Benchmarks compare systems on fixed tasks.**")),
    ]
    ok = True
    for name, (mutated, applied) in mutations:
        assert applied and mutated != new, f"mutation did not apply: {name}"
        f = [x for x in check(old, mutated, verbose=False, cz=cz, st=st, A=A, files=files, files15=files15,
                              src=src, src18=src18, src19=src19, src20=src20, src21=src21)
             if name.startswith("unmapped") or "has no ID" not in x]
        print(f"mutation [{name}]: {'CAUGHT' if f else 'MISSED'}" + (f" -> {f[0][:140]}" if f else ""))
        ok &= bool(f)
    dv = src21["dev"]
    ctl = json.loads(src21["ctl"])
    ctl["por_epoch"]["2026-09-08"]["mexeu"] = 19
    v4 = json.loads(src21["v4"])
    v4["pernas"]["registrado"]["por_epoch"]["2026-09-20"]["braco"] = "treatment"
    integ = [
        ("S21/M1: §10.13 no longer reverted", dict(src21=dict(src21, dev=dv.replace(
            "A primeira metade desta decisão foi REVERTIDA no mesmo dia", "A primeira metade desta decisão foi mantida", 1)))),
        ("S21/L1: instruction re-timed", dict(src21=dict(src21, dev=dv.replace(
            "Toto, 2026-09-09 14:38 BRT:", "Toto, 2026-09-09 16:38 BRT:", 1)))),
        ("S21/L2: §10.14 positive control changed", dict(src21=dict(src21, dev=dv.replace(
            "(`churn>0` em 20/672 no epoch 09-08)", "(`churn>0` em 19/672 no epoch 09-08)", 1)))),
        ("S21/L2: CONTROLES 09-08 differs", dict(src21=dict(src21, ctl=json.dumps(ctl)))),
        ("S21/L3: dry-run receipt re-dated", dict(src21=dict(src21, dev=dv.replace(
            "um teste manual de **2026-09-09 17:42:31Z**", "um teste manual de **2026-09-10 17:42:31Z**", 1)))),
        ("S21/L4: 09-20 a treatment epoch", dict(src21=dict(src21, v4=json.dumps(v4)))),
        ("carried S20: switch-off time moved", dict(src20=dict(src20, dev=src20["dev"].replace(
            "| drop-in arquivado | `2026-09-21 09:43:05Z` |", "| drop-in arquivado | `2026-09-20 21:00:00Z` |")))),
        ("carried S18: Zenodo v1.12 created at 14:01Z", dict(src18=dict(src18, zrec=src18["zrec"].replace(
            "2026-08-26T12:01:06", "2026-08-26T14:01:06")))),
    ]
    for name, kw in integ:
        args = dict(cz=cz, st=st, A=A, files=files, files15=files15, src=src, src18=src18, src19=src19,
                    src20=src20, src21=src21)
        args.update(kw)
        f = check(old, new, verbose=False, **args)
        print(f"mutation [{name}] (integrity): {'CAUGHT' if f else 'MISSED'}" + (f" -> {f[0][:140]}" if f else ""))
        ok &= bool(f)
    base = check(old, new, verbose=False, cz=cz, st=st, A=A, files=files, files15=files15, src=src,
                 src18=src18, src19=src19, src20=src20, src21=src21)
    print(f"unmutated rc21: {'PASS' if not base else 'FAIL'}" + (f" -> {base}" if base else ""))
    print(f"mutations: {len(mutations) + len(integ)}")
    return 0 if ok and not base else 1


if __name__ == "__main__":
    sys.exit(main())
