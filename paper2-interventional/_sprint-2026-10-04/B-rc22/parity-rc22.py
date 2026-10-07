#!/usr/bin/env python3
"""Parity check B-v2-rc21.md -> B-v2-rc22.md (Paper B, sprint 2026-10-04; rc22 2026-10-06).

rc22 applies Codex's final read of rc21 (GO with three LOW; receipt
`adversary-receipt-codex-2026-10-06T133927-60502.txt`, exit 0), each finding verified against the
artifacts and DEVIATIONS-FOR-PAPER.md first (`APPLY-B-rc22.md`). rc22 is the text frozen until the
whole-window sham result is integrated. No number of the analysis moves and no artifact of the
analysis changes.

  U1  §4 Adjudication: "The unknown share of opportunities is 1.02%" -> "1.00%" (v4
      `pernas.registrado.unknown_ponderado_sobre_oportunidades` = 0.009998; 1.02% was v2's
      0.010193). The 1.34% of the sensitivity analysis (leg `atual`, 0.013412, panel `3fam`) holds.
  W4  Working list 4: "Measured 2026-09-09; incorporated into the manuscript 2026-09-21", and only
      dose eligibility, not continued data collection, was limited to 20 epochs ("a dosed
      `N = 234`"). Declared tail edit.
  A3  Appendix A: "the substantive ones … are §10.29 through §10.34" -> "§10.14 and §10.22 (the
      closure decision of §3.0) and §10.29 through §10.34".

Checks (exit 1 if any fails): as rc21's (hunks, numbers, invariants, tail, SHAM-JANELA, carried
locks incl. title, "did not stop early", the closure date CD and every rc21 lock, qualifiers/hedges,
integrity incl. S21), with the rc22 anchors, locks and the NEW source block S22.

Usage:  python3 parity-rc22.py | --report | --self-test     Reads; writes nothing.
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
REPO = P2.parent
OLD = SPRINT / "B-v2-rc21.md"
NEW = SPRINT / "B-v2-rc22.md"
RC21 = SPRINT / "B-rc21" / "parity-rc21.py"
RC21_SHA = "47ddf0f6ccd1d48de9de55dc5488d861c16c0a4979f11bfe15193c58f386350d"
OLD_SHA = "c0589f85d2eba06b29b67b94ae4cd5f7420b62c5bcc1911398389dd51f128cd9"

assert hashlib.sha256(RC21.read_bytes()).hexdigest() == RC21_SHA, \
    "parity-rc21.py changed: the locks carried from it are no longer the ones rc21 ran"
_spec = importlib.util.spec_from_file_location("parity_rc21", RC21)
R21 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(R21)          # also installs appa_count_rc20 (count 12, horizon item)
R20 = R21.R20
R19, R18, R17 = R20.R19, R20.R18, R20.R17
R16, R15, R14, R13, R12, R11 = R17.R16, R17.R15, R17.R14, R17.R13, R17.R12, R17.R11
flat, body, tail, sci, load = R17.flat, R17.body, R17.tail, R17.sci, R17.load
TITLE, TITLE_OLD = R18.TITLE, R18.TITLE_OLD

RECEIPT_NAME = "adversary-receipt-codex-2026-10-06T133927-60502.txt"
FROZEN_MARK = "rc22 is the text frozen until the whole-window sham result is integrated"
SOURCES22 = {
    "dev": P2 / "DEVIATIONS-FOR-PAPER.md",
    "v4": P2 / "out" / "ITT-REGISTRADO-v4-2026-10-05.json",
    "v2": P2 / "out" / "ITT-REGISTRADO-v2-2026-10-05.json",
    "exp": P2 / "out" / "expiracao-designados-2026-09-09.json",
    "rcpt": (REPO / ".remember" / RECEIPT_NAME) if (REPO / ".remember" / RECEIPT_NAME).exists()
            else (HERE.parent / "receipts" / RECEIPT_NAME),  # versioned, scrubbed copy (host/home redacted)
}


def load_src22():
    return {k: p.read_text(encoding="utf-8") for k, p in SOURCES22.items()}


def pct(x):
    return f"{100 * x:.2f}%"


# ---------------------------------------------------------------- S22: the facts rc22 rests on
def source_facts_rc22(src, new):
    fails = []
    v4 = json.loads(src["v4"])["pernas"]
    reg, atu = v4["registrado"], v4["atual"]
    # U1: the registered leg's unknown share is 1.00%; the sensitivity (atual, three families) 1.34%
    if pct(reg["unknown_ponderado_sobre_oportunidades"]) != "1.00%":
        fails.append(f"S22/U1: v4 registered unknown share is {reg['unknown_ponderado_sobre_oportunidades']}, not 1.00%")
    if pct(atu["unknown_ponderado_sobre_oportunidades"]) != "1.34%":
        fails.append(f"S22/U1: v4 sensitivity (atual) unknown share is {atu['unknown_ponderado_sobre_oportunidades']}, not 1.34%")
    if (reg["config"]["painel"], atu["config"]["painel"]) != ("substituicao", "3fam"):
        fails.append("S22/U1: the registered leg no longer uses substitution, or the sensitivity leg no longer three families")
    if reg["regra_10pct_dados_ausentes_dispara"] is not False or atu["regra_10pct_dados_ausentes_dispara"] is not False:
        fails.append("S22/U1: the 10% missing-data rule fires on a leg")
    # the stale 1.02% was v2's registered value
    if pct(json.loads(src["v2"])["pernas"]["registrado"]["unknown_ponderado_sobre_oportunidades"]) != "1.02%":
        fails.append("S22/U1: v2's registered unknown share is not 1.02%; the provenance note needs rereading")
    # W4: measured 2026-09-09; the draft (and §3.0.1) opened 2026-09-21; data collection was not the limit
    if not json.loads(src["exp"]).get("ts", "").startswith("2026-09-09T"):
        fails.append("S22/W4: the expiry measurement is not dated 2026-09-09")
    if "> **STATUS: DRAFT opened 2026-09-21;" not in new:
        fails.append("S22/W4: the status header no longer dates the draft 2026-09-21")
    if "neither 234 randomized epochs nor the calendar cap was\nreached" not in new \
            and "neither 234 randomized epochs nor the calendar cap was reached" not in flat(body(new)):
        fails.append("S22/W4: §3.0.1 no longer says the data-collection horizon was not reached")
    # A3: §10.14 and §10.22 hold the closure decision; §10.29 .. §10.34 exist
    dv = src["dev"]
    for needle, why in (
            ("#### 10.14 Decisão revisada (2026-09-09, tarde): **não alargar a janela**. O ensaio termina em 2026-09-20",
             "§10.14 heading (closure decision)"),
            ("## §10.22 — Desfecho: decisão explícita, janela elegível e o desligamento armado",
             "§10.22 heading (closure instruction)"),
            ("## §10.29 — Desfecho EXECUTADO (2026-09-21)", "§10.29 heading"),
            ("## 10.34 — Itens 5 e 7 do §6", "§10.34 heading")):
        if needle not in dv:
            fails.append(f"S22/A3: DEVIATIONS {why} changed")
    # the receipt: Codex, exit 0, the timestamp named
    r = src["rcpt"]
    if "voice: codex\n" not in r or "\nexit: 0\n" not in r or "timestamp: 2026-10-06T133927\n" not in r:
        fails.append("S22/ST: the Codex receipt is not voice codex, exit 0, 2026-10-06T133927")
    return fails


# ---------------------------------------------------------------- 1: anchors
ANCHORS = [
    ("ST", "rc22 prepared 2026-10-06 (Codex's final read"),
    ("U1", "The unknown share of opportunities is 1.00%"),
    ("A3", "§10.14 and §10.22 (the closure decision of §3.0)"),
    ("W4", "a dosed `N = 234`"),
    ("WL", "*(rc22: rc21 had one full read"),
    ("CL", "**rc22: final read of rc21 applied**"),
]
REMOVED_ANCHORS = []

# ---------------------------------------------------------------- 2: numbers
JUSTIFIED_REMOVED = {"1.02": (1, "U1: the registered unknown share 1.02% (v2, 0.010193) -> 1.00% (v4, 0.009998)")}


def derived_rc22(src):
    out = {}
    reg = json.loads(src["v4"])["pernas"]["registrado"]["unknown_ponderado_sobre_oportunidades"]
    for tok in (pct(reg), pct(reg)[:-1]):
        out[tok] = "v4 pernas.registrado.unknown_ponderado_sobre_oportunidades, as a percentage (checked in S22)"
    out["10.14"] = out["10.22"] = "DEVIATIONS section numbers (checked in S22)"
    out["2026-10-06"] = "rc22 date (status header)"
    out["2026-10-06T133927-60502"] = out["133927"] = out["60502"] = "Codex receipt name (checked in S22)"
    return out


# ---------------------------------------------------------------- 3/4: tail
TAIL_INSERTS = [
    """
    *(rc22: rc21 had one full read, Codex GO with three LOW
    (`adversary-receipt-codex-2026-10-06T133927-60502.txt`); all verified and applied in rc22
    (`APPLY-B-rc22.md`). rc22 is the text frozen until the whole-window sham result is
    integrated.)*""",
]
TAIL_EDITS = [  # (rc21 text, rc22 text) — working list item 4, Codex LOW 2
    ("""   `N = 234` **was** infeasible: the designation expires 2026-09-20 22:51:23, giving 20
   eligible epochs of 234. §9 *(numbered §8 before v2)* rewritten around it.
""",
     """   a dosed `N = 234` **was** infeasible: the designation expires 2026-09-20 22:51:23, giving 20
   eligible epochs of 234. §9 *(numbered §8 before v2)* rewritten around it. Measured
   2026-09-09; incorporated into the manuscript 2026-09-21. Only dose eligibility, not
   continued data collection, was limited to 20 epochs.
"""),
]

# ---------------------------------------------------------------- 6: locks
SWEEP_LOCK_RC22 = [
    (r"(?i)unknown share of opportunities is 1\.02%", "U1: the registered leg's unknown share is 1.00% (v4)"),
    (r"(?i)substantive ones for this paper are §10\.29", "A3: §10.14 and §10.22 are named beside §10.29–§10.34"),
]
PRESENT_RC22 = [
    ("The unknown share of opportunities is 1.00% (1.34% in the sensitivity analysis), so the registered 10% "
     "missing-data rule does not fire.", "U1 §4 Adjudication"),
    ("the substantive ones for this paper are §10.14 and §10.22 (the closure decision of §3.0) and §10.29 "
     "through §10.34;", "A3 Appendix A"),
]
PRESENT_REPLACED = {}
STATUS_MARKS_RC22 = R21.STATUS_MARKS_RC21 + ["rc22 prepared 2026-10-06 (Codex's final read", RECEIPT_NAME,
                                             FROZEN_MARK]
STATUS_LOCK = R21.STATUS_LOCK
STRUCK_DELTA = {}

# ---------------------------------------------------------------- 7: qualifier deltas (from --report)
JUSTIFIED_PHRASE = {}
JUSTIFIED_HEDGE = {}


def carried_present():
    return [p for p in R21.carried_present() + R21.PRESENT_RC21 if p[0] not in PRESENT_REPLACED]


def check(old, new, verbose=True, report=False, cz=None, st=None, A=None, files=None, files15=None,
          src=None, src18=None, src19=None, src20=None, src21=None, src22=None):
    cz = cz or R13.load_rc13()
    st = st or R13.load_paths()
    A = A or load()
    src = src or {k: p.read_text(encoding="utf-8") for k, p in R17.SOURCES.items()}
    src18 = src18 or R18.load_src18()
    src19 = src19 or R19.load_src19()
    src20 = src20 or R20.load_src20()
    src21 = src21 or R21.load_src21()
    src22 = src22 or load_src22()
    if files is None:
        files = {k: p.read_bytes() for k, p in R15.ART.items()}
        files["res4_frozen"] = R17.RES4_FROZEN.read_bytes()
    files15 = files15 or {"py": R16.FROZEN_TEST_PY.read_bytes(), "json": R16.FROZEN_TEST_JSON.read_bytes()}
    fails, rep = [], []
    if hashlib.sha256(old.encode()).hexdigest() != OLD_SHA:
        fails.append("rc21 is not the c0589f85… bytes rc21's parity passed on")
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
    der = derived_rc22(src22)
    old_nums = R11.numbers(old)
    added = {k: d for k, d in delta.items() if d > 0}
    src_add = {}
    for k in sorted(added):
        if old_nums[k]:
            src_add[k] = "in rc21"
        elif k in der:
            src_add[k] = "derived: " + der[k]
        elif k in allowed:
            src_add[k] = "artifact: " + allowed[k]
        else:
            fails.append(f"numbers: token {k!r} added {added[k]}x is neither in rc21, nor an artifact leaf, nor derived")
    # 1 hunks
    hs = R11.hunks(old, new)
    for h in hs:
        ids = [aid for aid, anc in ANCHORS if anc in h["new"]]
        ids += [aid for anc, aid in REMOVED_ANCHORS if not h["new"].strip() and anc in h["old"]]
        h["ids"] = list(dict.fromkeys(ids))
        if not h["ids"]:
            fails.append(f"hunk rc21 {h['rc10']} rc22 {h['rc11']} has no ID: {(h['new'] or h['old'])[:80]!r}")
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
                fails.append(f"invariant: struck spans moved by {d}; rc22 declares {STRUCK_DELTA}")
        elif name in R17.INV_FIXED and d:
            fails.append(f"invariant: {name} changed: {dict(list(d.items())[:4])}")
        rep.append(f"{name}: {sum(a.values())} -> {sum(b.values())}" + ("" if not d else f"  (delta {len(d)} items)"))
        if report and d and (name in R17.INV_FREE or name == "struck spans"):
            for k, v in sorted(d.items(), key=lambda kv: str(kv[0]))[:40]:
                rep.append(f"    {v:+d} {str(k)[:150]}")
    if R11.headings(old) != R11.headings(new):
        fails.append("invariant: heading list changed (rc22 changes no heading)")
    if new.count(R20.H301_NEW) != 1:
        fails.append("invariant: the rc20 §3.0.1 heading is not in rc22 exactly once")
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
            fails.append(f"tail: declared tail edit not found exactly once: {b[:60]!r}")
        t = t.replace(b, a)
    i21 = t.find("\n\n**rc22: final read of rc21 applied**")
    blocks21 = t[i21:] if i21 >= 0 else ""
    t = t[:i21] + "\n" if i21 >= 0 else t
    if i21 < 0:
        fails.append("tail: the rc22 changelog block is missing")
    if t != to:
        fails.append("tail: working list / changelog, with the declared insertion and edit reverted and the rc22 "
                     "block removed, is not byte-identical to rc21")
    i = tn.find("\n**rc14: writing pass**")
    nums = [int(x) for x in re.findall(r"^(\d+)\. ", tn[i:] if i >= 0 else "", re.M)]
    if nums != list(range(149, 188)):
        fails.append(f"tail: rc14-rc22 changelog items are {nums}, expected 149..187")
    for n, needle in ((185, "§4 Adjudication (Codex LOW 1)"), (186, "Working list 4 (Codex LOW 2)"),
                      (187, "Appendix A (Codex LOW 3)")):
        if not re.search(rf"^{n}\. {re.escape(needle)}", blocks21, re.M):
            fails.append(f"tail: changelog item {n} missing")
    if "GO with three LOW" not in flat(blocks21) or "_sprint-2026-10-04/APPLY-B-rc22.md`" not in flat(blocks21) \
            or RECEIPT_NAME not in flat(blocks21) or FROZEN_MARK not in flat(blocks21):
        fails.append("tail: the rc22 block does not name the Codex verdict, its receipt, the freeze and the APPLY record")
    # 5 SHAM
    so, eo = R11.sham_spans(old)
    sn, en = R11.sham_spans(new)
    fails += eo + en
    if len(sn) != R11.EXPECTED_SHAM or len(so) != R11.EXPECTED_SHAM:
        fails.append(f"sham: {len(sn)} blocks in rc22 and {len(so)} in rc21, expected {R11.EXPECTED_SHAM}")
    for k, (x, y) in enumerate(zip(so, sn), 1):
        if x != y:
            fails.append(f"sham: block {k} ({y.strip()[:50]!r}…) is not byte-identical to rc21")
    # 6 carried locks + rc22
    fails += R13.claims_rc13(new, cz)
    nb_unstruck = R11.strip_struck(nb)
    fn_unstruck = flat(nb_unstruck)
    for pat, why in (R15.SWEEP_LOCK + R16.SWEEP_LOCK_RC16 + R17.SWEEP_LOCK_RC17 + R18.SWEEP_LOCK_RC18
                     + R19.SWEEP_LOCK_RC19 + R20.SWEEP_LOCK_RC20 + R21.SWEEP_LOCK_RC21
                     + SWEEP_LOCK_RC22):
        for mo in re.finditer(pat, fn_unstruck):
            fails.append(f"sweep: {why}: {fn_unstruck[max(0, mo.start() - 60):mo.end() + 30]!r}")
    head = new[:new.find("\n---")]
    for mk in STATUS_MARKS_RC22:
        if mk not in head and flat(mk) not in flat(head.replace("> ", " ")):
            fails.append(f"status: header does not record {mk.splitlines()[0]!r}")
    for pat, why in STATUS_LOCK:
        if re.search(pat, flat(head.replace("> ", " "))):
            fails.append(f"status: {why}")
    for txt, why in carried_present() + PRESENT_RC22:
        if flat(txt) not in fn_unstruck:
            fails.append(f"present: {why} sentence missing: {txt[:70]!r}")
    for txt in PRESENT_REPLACED:
        if flat(txt) in fn_unstruck:
            fails.append(f"present: replaced rc21 text still present: {txt[:70]!r}")
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
                fails.append(f"qualifier: {ph[:70]!r} occurs {b}x in rc22 against {a}x in rc21, not justified")
    for (ph, d) in JUSTIFIED_PHRASE:
        if pdeltas.get(ph) != d:
            fails.append(f"qualifier: JUSTIFIED_PHRASE lists {ph[:50]!r} {d:+d}; measured {pdeltas.get(ph, 0):+d}")
    gone = {ph for (ph, d) in list(JUSTIFIED_PHRASE) + list(R21.JUSTIFIED_PHRASE) + list(R20.JUSTIFIED_PHRASE) + list(R19.JUSTIFIED_PHRASE)
            + list(R18.JUSTIFIED_PHRASE) + list(R17.JUSTIFIED_PHRASE) + list(R16.JUSTIFIED_PHRASE)
            + list(R15.JUSTIFIED_PHRASE) if d < 0 and fnn.count(ph) == 0}
    for k, v in h15.items():
        if flat(v) not in fnn and flat(v) not in gone:
            fails.append(f"headline: {k} — {v[:80]!r} not found in rc22")
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
    rep.append(f"locked phrases: {len(locked)} (rc21's); justified deltas: {pdeltas}; hedge deltas: {hd}")
    if report:
        for k, v in sorted(per.items()):
            rep.append(f"  hedge [{k}]: {v}")
    # 8 integrity: rc21's carried checks (incl. S, S18, S19, S20, S21), then S22
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
    fails += f19 + f20 + R21.source_facts_rc21(src21, new) + source_facts_rc22(src22, new)
    warns = list(warns) + w19 + w20
    # 9 REANALISE, bold
    if R11.R_ANY.search(new):
        fails.append("reanalise: a REANALISE marker is present in rc22")
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
        print(f"SHAM-JANELA blocks: {len(sn)}, byte-identical to rc21: {sum(1 for x, y in zip(so, sn) if x == y)}")
        print(f"words: rc21 {len(old.split())} (body {len(body(old).split())}), "
              f"rc22 {len(new.split())} (body {len(body(new).split())})")
        for w in warns:
            print(w)
    if report:
        print("\nnumeric tokens added (and their source):")
        for k in sorted(added):
            print(f"  +{added[k]} {k}: {src_add.get(k, 'UNSOURCED')}")
        print("numeric tokens removed:", removed)
        print("phrase deltas:", pdeltas)
        for h in hs:
            print(f"\n[{'+'.join(h['ids']) or '?'}] rc21 l.{h['rc10'][0]}-{h['rc10'][1]} -> rc22 l.{h['rc11'][0]}-{h['rc11'][1]}")
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
    src18, src19, src20 = R18.load_src18(), R19.load_src19(), R20.load_src20()
    src21, src22 = R21.load_src21(), load_src22()
    rep1 = lambda a, b: (new.replace(a, b, 1), a in new)  # noqa: E731
    mutations = [
        ("U1: 1.02% restored", rep1("unknown share of opportunities is 1.00%", "unknown share of opportunities is 1.02%")),
        ("U1: sensitivity 1.34% changed", rep1("(1.34% in the sensitivity analysis)", "(1.39% in the sensitivity analysis)")),
        ("A3: §10.14 and §10.22 dropped", rep1(
            "§10.14 and §10.22 (the closure decision of §3.0) and\n§10.29 through §10.34", "§10.29 through §10.34")),
        ("A3: wrong section named", rep1("§10.14 and §10.22 (the closure", "§10.15 and §10.22 (the closure")),
        ("W4: item 4 note dropped", rep1(
            " Measured\n   2026-09-09; incorporated into the manuscript 2026-09-21. Only dose eligibility, not\n"
            "   continued data collection, was limited to 20 epochs.", "")),
        ("W4: measurement date wrong", rep1("Measured\n   2026-09-09; incorporated", "Measured\n   2026-09-21; incorporated")),
        ("W4: data-collection clause dropped", rep1(
            " Only dose eligibility, not\n   continued data collection, was limited to 20 epochs.", "")),
        ("WL: working list 24 rc22 note dropped", rep1(TAIL_INSERTS[0], "")),
        ("CL: changelog item 186 removed", rep1("\n186. Working list 4 (Codex LOW 2)", "\nWorking list 4 (Codex LOW 2)")),
        ("CL: receipt dropped from the rc22 block", rep1(
            "receipt `adversary-receipt-codex-2026-10-06T133927-60502.txt`, `exit: 0`;", "`exit: 0`;")),
        ("old changelog line edited", rep1("**rc21: review of rc20 applied**", "**rc21: review of rc20 applied (edited)**")),
        ("status header without rc22", rep1("rc22 prepared 2026-10-06 (Codex's final read",
                                            "rc22 drafted 2026-10-06 (Codex's final read")),
        ("status header without the freeze", rep1(
            "> three applied; rc22 is the text frozen until the whole-window sham result is integrated).**",
            "> three applied).**")),
        ("carried rc21: 'data-dependent stop' restored", rep1("It was not an outcome-dependent stop",
                                                              "It was not a data-dependent stop")),
        ("carried rc21 CD: closure decision dated 2026-09-21 again", rep1(
            "by a decision taken on 2026-09-09", "by a decision taken on 2026-09-21")),
        ("carried rc20: 'did not stop early' slipped back", rep1(
            "a limitation fixed before Epoch 1. All 19", "a limitation fixed before Epoch 1. It did not stop early. All 19")),
        ("carried title lock", rep1(TITLE, TITLE.replace("A registered horizon that", "A registration that"))),
        ("a heading changed", rep1("### 3.0 The stopping rule, and the feasibility question it raises",
                                   "### 3.0 The stopping rule")),
        ("SHAM-JANELA block changed", rep1("**Our error, stated.**", "**Our error.**")),
        ("unsourced number added", rep1("It ran for the entire interval in which", "It ran for the entire interval (8317 h) in which")),
        ("unmapped hunk with no anchor", rep1("**Benchmarks compare systems on fixed tasks.**",
                                               "Benchmarks are compared.\n\n**Benchmarks compare systems on fixed tasks.**")),
    ]
    ok = True
    for name, (mutated, applied) in mutations:
        assert applied and mutated != new, f"mutation did not apply: {name}"
        f = [x for x in check(old, mutated, verbose=False, cz=cz, st=st, A=A, files=files, files15=files15,
                              src=src, src18=src18, src19=src19, src20=src20, src21=src21, src22=src22)
             if name.startswith("unmapped") or "has no ID" not in x]
        print(f"mutation [{name}]: {'CAUGHT' if f else 'MISSED'}" + (f" -> {f[0][:140]}" if f else ""))
        ok &= bool(f)
    v4 = json.loads(src22["v4"])
    v4["pernas"]["registrado"]["unknown_ponderado_sobre_oportunidades"] = 0.010193
    v4b = json.loads(src22["v4"])
    v4b["pernas"]["atual"]["unknown_ponderado_sobre_oportunidades"] = 0.013856
    v4c = json.loads(src22["v4"])
    v4c["pernas"]["atual"]["config"]["painel"] = "substituicao"
    exp = json.loads(src22["exp"])
    exp["ts"] = "2026-09-21T09:00:00Z"
    dv = src22["dev"]
    integ = [
        ("S22/U1: registered unknown share 1.02%", dict(src22=dict(src22, v4=json.dumps(v4)))),
        ("S22/U1: sensitivity unknown share 1.39%", dict(src22=dict(src22, v4=json.dumps(v4b)))),
        ("S22/U1: sensitivity leg no longer three families", dict(src22=dict(src22, v4=json.dumps(v4c)))),
        ("S22/W4: expiry measurement re-dated", dict(src22=dict(src22, exp=json.dumps(exp)))),
        ("S22/A3: §10.22 heading changed", dict(src22=dict(src22, dev=dv.replace(
            "## §10.22 — Desfecho: decisão explícita", "## §10.22 — Desfecho: decisão implícita", 1)))),
        ("S22/ST: receipt exit 1", dict(src22=dict(src22, rcpt=src22["rcpt"].replace("\nexit: 0\n", "\nexit: 1\n", 1)))),
        ("carried S21: instruction re-timed", dict(src21=dict(src21, dev=src21["dev"].replace(
            "Toto, 2026-09-09 14:38 BRT:", "Toto, 2026-09-09 16:38 BRT:", 1)))),
        ("carried S20: switch-off time moved", dict(src20=dict(src20, dev=src20["dev"].replace(
            "| drop-in arquivado | `2026-09-21 09:43:05Z` |", "| drop-in arquivado | `2026-09-20 21:00:00Z` |")))),
    ]
    for name, kw in integ:
        args = dict(cz=cz, st=st, A=A, files=files, files15=files15, src=src, src18=src18, src19=src19,
                    src20=src20, src21=src21, src22=src22)
        args.update(kw)
        f = check(old, new, verbose=False, **args)
        print(f"mutation [{name}] (integrity): {'CAUGHT' if f else 'MISSED'}" + (f" -> {f[0][:140]}" if f else ""))
        ok &= bool(f)
    base = check(old, new, verbose=False, cz=cz, st=st, A=A, files=files, files15=files15, src=src,
                 src18=src18, src19=src19, src20=src20, src21=src21, src22=src22)
    print(f"unmutated rc22: {'PASS' if not base else 'FAIL'}" + (f" -> {base}" if base else ""))
    print(f"mutations: {len(mutations) + len(integ)}")
    return 0 if ok and not base else 1


if __name__ == "__main__":
    sys.exit(main())
