#!/usr/bin/env python3
"""Parity check B-v2-rc24.md -> B-v2-rc25.md (Paper B, sprint 2026-10-04; rc25 2026-10-07).

Fable's diff check of rc23 -> rc24 (an agent run, no file) gave GO with three LOW, all in
Appendix B / B.1. rc25 applies only those, each verified first (`APPLY-B-rc25.md`). No number of
the analysis or of the sham results moves.

  R1  Appendix B, row of the rc23 Codex read: "(the receipt's stamp is local time, UTC−3: 12:31Z,
      after the 12:02Z extension)" after "written after the rc23 ballast manifest"
      (scripts/adversary-run.sh stamps with `date +%Y-%m-%dT%H%M%S`, no -u; 093115 local = 12:31:15Z;
      the manifest's last extension `item15-janela2` is 2026-10-07T12:02:12Z)
  R2  B.1 ballast paragraph: "…is not in the manifest, nor are the two records of the final Codex
      read of rc23 (Appendix B)."
  R3  Appendix B manifest row: "`B-censo/raw/` (see its row)" in parentheses
  ST  status header: rc24's diff check recorded, rc25 entry ("rc24 has not been reviewed" replaced)
  WL  working list 24: rc25 note
  CL  the rc25 changelog block (204-206)

Checks (exit 1 if any fails): rc24's whole set (hunks with IDs, numbers sourced, invariants, tail
with the declared edits reverted equal to rc24, no SHAM-JANELA marker, carried locks of every
earlier rc, qualifiers/hedges, integrity S..S24), except the rc24 locks that rc25 makes false on
purpose and replaces: the status mark "rc24 has not been reviewed" and the two present-locks of
the Appendix B rows R1 and R3 touch. NEW: block S25 checks every fact a fix rests on.

Usage:  python3 parity-rc25.py | --report | --self-test     Reads; writes nothing.
Caveat: S24/M and S25/M read ~/Backups/paper2-ensaio-2026-09-21 (outside the repository, by
design); on a machine without it those legs are NOT VERIFIED warnings, never passed.
"""
import collections
import datetime
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
OLD = SPRINT / "B-v2-rc24.md"
NEW = SPRINT / "B-v2-rc25.md"
RC24 = SPRINT / "B-rc24" / "parity-rc24.py"
RC24_SHA = "5340173f6a1f36d33223914e00c6d715872c3e2a371607e9a26a5b06dffbc73d"
OLD_SHA = "f66bf8c63f5beb21020833193a05d5d3c9c20ce919c7e822977a98fe024ba344"
ADV_RUN = Path.home() / "Claude" / "scripts" / "adversary-run.sh"

assert hashlib.sha256(RC24.read_bytes()).hexdigest() == RC24_SHA, \
    "parity-rc24.py changed: the locks carried from it are no longer the ones rc24 ran"
_spec = importlib.util.spec_from_file_location("parity_rc24", RC24)
R24 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(R24)
R23 = R24.R23
R22, R21, R20, R19, R18, R17 = R23.R22, R23.R21, R23.R20, R23.R19, R23.R18, R23.R17
R16, R15, R14, R13, R12, R11 = R23.R16, R23.R15, R23.R14, R23.R13, R23.R12, R23.R11
flat, body, tail, sci, load = R23.flat, R23.body, R23.tail, R23.sci, R23.load
TITLE = R23.TITLE
S_OPEN, S_CLOSE = R23.S_OPEN, R23.S_CLOSE

STAMP_LOCAL = "2026-10-07T093115"
EXT_LABEL, EXT_AT = "item15-janela2", "2026-10-07T12:02"


def load_src25():
    try:
        adv = ADV_RUN.read_text(encoding="utf-8")
    except OSError:
        adv = None
    return {"adv": adv}


# ---------------------------------------------------------------- S25: the facts the fixes rest on
def source_facts_rc25(src25, src24, src23):
    fails, warns = [], []
    # R1a: the runner stamps receipts in local time (date without -u)
    adv = src25["adv"]
    if adv is None:
        warns.append("S25/R1: scripts/adversary-run.sh not on this machine: local-time stamp NOT VERIFIED")
    else:
        stamps = re.findall(r"date[^\n\"]*\+%Y-%m-%dT%H%M%S", adv)
        if not re.search(r'STAMP="\$\(date \+%Y-%m-%dT%H%M%S\)"', adv) or any("-u" in s for s in stamps):
            fails.append("S25/R1: adversary-run.sh does not stamp with `date +%Y-%m-%dT%H%M%S` without -u")
    # R1b: the receipt's stamp, read as UTC−3 (America/Sao_Paulo, no DST in 2026), is 12:31Z
    r = src24["rcpt"]
    if f"timestamp: {STAMP_LOCAL}\n" not in r:
        fails.append("S25/R1: the rc23 Codex receipt stamp is not 2026-10-07T093115")
    try:
        from zoneinfo import ZoneInfo
        loc = datetime.datetime.strptime(STAMP_LOCAL, "%Y-%m-%dT%H%M%S").replace(tzinfo=ZoneInfo("America/Sao_Paulo"))
        if loc.utcoffset() != datetime.timedelta(hours=-3) or \
                loc.astimezone(datetime.timezone.utc).strftime("%H:%M") != "12:31":
            fails.append("S25/R1: 093115 at UTC−3 is not 12:31Z")
    except Exception as exc:  # noqa: BLE001
        warns.append(f"S25/R1: zoneinfo unavailable ({exc}): UTC−3 offset NOT VERIFIED")
    # R1c: the manifest's last extension (item15-janela2) is 12:02Z, before the read
    if src23["manifest"] is None:
        warns.append("S25/M: ballast manifest not on this machine: 12:02Z extension NOT VERIFIED")
    else:
        ext = json.loads(src23["manifest"])["extensoes"][-1]
        if ext["rotulo"] != EXT_LABEL or not ext["em"].startswith(EXT_AT):
            fails.append("S25/M: the manifest's last extension is not item15-janela2 at 2026-10-07T12:02Z")
    return fails, warns


# ---------------------------------------------------------------- 1: anchors
ANCHORS = [
    ("ST", "had a diff check by Fable, rc23 → rc24, GO with three LOW"),
    ("ST", "rc25 has not been\n> reviewed"),
    ("R1", "(the receipt's stamp is local time, UTC−3: 12:31Z, after the 12:02Z extension)"),
    ("R2", "nor are the two records of the final Codex read of rc23 (Appendix B)."),
    ("R3", "`B-censo/raw/` (see its row), and the two records"),
    ("WL", "*(rc25: Fable's diff check of rc23 → rc24"),
    ("CL", "**rc25: diff check of rc24 applied**"),
]
REMOVED_ANCHORS = []

# ---------------------------------------------------------------- 2: numbers
JUSTIFIED_REMOVED = {}


def derived_rc25():
    return {"12:31Z": "receipt stamp 2026-10-07T093115 at UTC−3 (checked in S25/R1)"}


# ---------------------------------------------------------------- 3/4: tail
TAIL_INSERTS = [
    """
    *(rc25: Fable's diff check of rc23 → rc24 (an agent run, no file) gave GO with three LOW in
    Appendix B and B.1; all verified and applied in rc25 (`APPLY-B-rc25.md`). rc25 changes
    wording only; it has not been reviewed.)*""",
]
TAIL_EDITS = []
CL_ITEMS = [(204, "Appendix B, row of the rc23 Codex read (Fable LOW 1)"),
            (205, "B.1, ballast paragraph (Fable LOW 2)"),
            (206, "Appendix B, manifest row (Fable LOW 3)")]

# ---------------------------------------------------------------- 6: locks
SWEEP_LOCK_RC25 = [
    (r"`B-censo/raw/`, see its row, and the two records", "R3: '(see its row)' in parentheses"),
    (r"panelist reasons, is not in the manifest\.", "R2: the rc23-read records are named beside B-censo/raw/"),
    (r"written after the rc23 ballast manifest and are not in it", "R1: the receipt's stamp is local time"),
]
PRESENT_RC25 = [
    ("SHA-256 hashes of the 115 artifacts currently covered, for loss detection: from rc23, every artifact in this "
     "table (excepted: the manifest itself, `B-censo/raw/` (see its row), and the two records of the final Codex "
     "read of rc23, written after the manifest, see their row)", "R3 manifest row"),
    ("Both records were written after the rc23 ballast manifest (the receipt's stamp is local time, UTC−3: 12:31Z, "
     "after the 12:02Z extension) and are not in it: the manifest's `receipts/` entry hashes the 22 receipts "
     "present when it was extended (added in rc24) |", "R1 row"),
    ("`B-censo/raw/`, which holds episode excerpts and panelist reasons, is not in the manifest, nor are the two "
     "records of the final Codex read of rc23 (Appendix B).", "R2 B.1"),
]
PRESENT_REPLACED = {
    "SHA-256 hashes of the 115 artifacts currently covered, for loss detection: from rc23, every artifact in this "
    "table (excepted: the manifest itself, `B-censo/raw/`, see its row, and the two records of the final Codex "
    "read of rc23, written after the manifest, see their row)": "R3: '(see its row)' in parentheses",
    "Both records were written after the rc23 ballast manifest and are not in it: the manifest's `receipts/` "
    "entry hashes the 22 receipts present when it was extended (added in rc24) |": "R1: stamp note inserted",
    "`B-censo/raw/`, which holds episode excerpts and panelist reasons, is not in the manifest.":
        "R2: the sentence now continues 'nor are the two records…' (carried rc23 lock 'AB raw excluded')",
}
STATUS_MARKS_RC25 = [m for m in R24.STATUS_MARKS_RC24 if m != "rc24 has not been reviewed"] + [
    "rc24 had a diff check by Fable, rc23 → rc24, GO with three LOW in Appendix B and B.1",
    "rc25 prepared 2026-10-07 (those three LOW applied; rc25 changes wording only",
    "rc25 has not been reviewed"]
STATUS_LOCK = R24.STATUS_LOCK + [(r"rc24 has not been reviewed", "ST: rc24 had a diff check")]
STRUCK_DELTA = {}

# ---------------------------------------------------------------- 7: qualifier deltas (from --report)
JUSTIFIED_PHRASE = {}
JUSTIFIED_HEDGE = {
    "ST": ({"only": 1}, "status: 'rc25 changes wording only' (the 'not been reviewed' moves from rc24 to rc25)"),
    "R2": ({"nor": 1}, "B.1: '…is not in the manifest, nor are the two records…'"),
}


def carried_present():
    return [p for p in R24.carried_present() + R24.PRESENT_RC24 if p[0] not in PRESENT_REPLACED]


def check(old, new, verbose=True, report=False, cz=None, st=None, A=None, files=None, files15=None,
          src=None, src18=None, src19=None, src20=None, src21=None, src22=None, src23=None, src24=None,
          src25=None):
    cz = cz or R13.load_rc13()
    st = st or R13.load_paths()
    A = A or load()
    src = src or {k: p.read_text(encoding="utf-8") for k, p in R17.SOURCES.items()}
    src18 = src18 or R18.load_src18()
    src19 = src19 or R19.load_src19()
    src20 = src20 or R20.load_src20()
    src21 = src21 or R21.load_src21()
    src22 = src22 or R22.load_src22()
    src23 = src23 or R23.load_src23()
    src24 = src24 or R24.load_src24()
    src25 = src25 or load_src25()
    if files is None:
        files = {k: p.read_bytes() for k, p in R15.ART.items()}
        files["res4_frozen"] = R17.RES4_FROZEN.read_bytes()
    files15 = files15 or {"py": R16.FROZEN_TEST_PY.read_bytes(), "json": R16.FROZEN_TEST_JSON.read_bytes()}
    fails, rep = [], []
    if hashlib.sha256(old.encode()).hexdigest() != OLD_SHA:
        fails.append("rc24 is not the f66bf8c6… bytes rc24's parity passed on")
    ob, nb = body(old), body(new)
    # 2 numbers
    dn, do = R11.numbers(nb), R11.numbers(ob)
    delta = {k: dn[k] - do[k] for k in set(dn) | set(do) if dn[k] != do[k]}
    removed = {k: -d for k, d in delta.items() if d < 0}
    for k in sorted(set(removed) | set(JUSTIFIED_REMOVED)):
        if removed.get(k, 0) != JUSTIFIED_REMOVED.get(k, (0,))[0]:
            fails.append(f"numbers: token {k!r} removed {removed.get(k, 0)}x; JUSTIFIED_REMOVED declares "
                         f"{JUSTIFIED_REMOVED.get(k, (0,))[0]}x")
    der = derived_rc25()
    old_nums = R11.numbers(old)
    added = {k: d for k, d in delta.items() if d > 0}
    src_add = {}
    for k in sorted(added):
        if old_nums[k]:
            src_add[k] = "in rc24"
        elif k in der:
            src_add[k] = "derived: " + der[k]
        else:
            fails.append(f"numbers: token {k!r} added {added[k]}x is neither in rc24 nor derived")
    # 1 hunks
    hs = R11.hunks(old, new)
    for h in hs:
        ids = [aid for aid, anc in ANCHORS if anc in h["new"]]
        ids += [aid for anc, aid in REMOVED_ANCHORS if not h["new"].strip() and anc in h["old"]]
        h["ids"] = list(dict.fromkeys(ids))
        if not h["ids"]:
            fails.append(f"hunk rc24 {h['rc10']} rc25 {h['rc11']} has no ID: {(h['new'] or h['old'])[:80]!r}")
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
                fails.append(f"invariant: struck spans moved by {d}; rc25 declares {STRUCK_DELTA}")
        elif name in R17.INV_FIXED and d:
            fails.append(f"invariant: {name} changed: {dict(list(d.items())[:4])}")
        rep.append(f"{name}: {sum(a.values())} -> {sum(b.values())}" + ("" if not d else f"  (delta {len(d)} items)"))
        if report and d and (name in R17.INV_FREE or name == "struck spans"):
            for k, v in sorted(d.items(), key=lambda kv: str(kv[0]))[:60]:
                rep.append(f"    {v:+d} {str(k)[:150]}")
    if R11.headings(old) != R11.headings(new):
        fails.append("invariant: heading list changed (rc25 changes no heading)")
    if new.count(R20.H301_NEW) != 1:
        fails.append("invariant: the rc20 §3.0.1 heading is not in rc25 exactly once")
    if new.splitlines()[0] != TITLE:
        fails.append("title: line 1 is not the author's title of 2026-10-05")
    if R22.TITLE_OLD in body(new):
        fails.append("title: the old title appears in the body")
    for pat in R11.FORBIDDEN:
        if len(re.findall(pat, new)) > len(re.findall(pat, old)):
            fails.append(f"forbidden: pattern {pat!r} added")
    # 4 tail
    to, tn = tail(old), tail(new)
    t = tn
    for ins in TAIL_INSERTS:
        if t.count(ins) != 1:
            fails.append(f"tail: declared insertion not found exactly once: {ins.strip()[:60]!r}")
        t = t.replace(ins, "")
    for a_, b_ in TAIL_EDITS:
        if t.count(b_) != 1:
            fails.append(f"tail: declared tail edit not found exactly once: {b_[:60]!r}")
        t = t.replace(b_, a_)
    i25 = t.find("\n\n**rc25: diff check of rc24 applied**")
    blocks25 = t[i25:] if i25 >= 0 else ""
    t = t[:i25] + "\n" if i25 >= 0 else t
    if i25 < 0:
        fails.append("tail: the rc25 changelog block is missing")
    if t != to:
        fails.append("tail: working list / changelog, with the declared insertions reverted and the rc25 "
                     "block removed, is not byte-identical to rc24")
    i = tn.find("\n**rc14: writing pass**")
    nums = [int(x) for x in re.findall(r"^(\d+)\. ", tn[i:] if i >= 0 else "", re.M)]
    if nums != list(range(149, 207)):
        fails.append(f"tail: rc14-rc25 changelog items are {nums[-8:]}…, expected 149..206")
    for n, needle in CL_ITEMS:
        if not re.search(rf"^{n}\. {re.escape(needle)}", blocks25, re.M):
            fails.append(f"tail: changelog item {n} missing")
    fb = flat(blocks25)
    if "_sprint-2026-10-04/APPLY-B-rc25.md`" not in fb or "wording only" not in fb or "GO with three LOW" not in fb:
        fails.append("tail: the rc25 block does not name the GO diff check, the APPLY record and 'wording only'")
    # 5 SHAM: none
    sn, en = R11.sham_spans(new)
    fails += en
    if sn or S_OPEN in new or S_CLOSE in new or "SHAM-JANELA: pending" in new:
        fails.append("sham: a SHAM-JANELA marker is in rc25")
    # 6 carried locks + rc25
    fails += R13.claims_rc13(new, cz)
    nb_unstruck = R11.strip_struck(nb)
    fn_unstruck = flat(nb_unstruck)
    for pat, why in (R15.SWEEP_LOCK + R16.SWEEP_LOCK_RC16 + R17.SWEEP_LOCK_RC17 + R18.SWEEP_LOCK_RC18
                     + R19.SWEEP_LOCK_RC19 + R20.SWEEP_LOCK_RC20 + R21.SWEEP_LOCK_RC21
                     + R22.SWEEP_LOCK_RC22 + R23.SWEEP_LOCK_RC23 + R24.SWEEP_LOCK_RC24 + SWEEP_LOCK_RC25):
        for mo in re.finditer(pat, fn_unstruck):
            fails.append(f"sweep: {why}: {fn_unstruck[max(0, mo.start() - 60):mo.end() + 30]!r}")
    head = new[:new.find("\n---")]
    for mk in STATUS_MARKS_RC25:
        if mk not in head and flat(mk) not in flat(head.replace("> ", " ")):
            fails.append(f"status: header does not record {mk.splitlines()[0]!r}")
    for pat, why in STATUS_LOCK:
        if re.search(pat, flat(head.replace("> ", " "))):
            fails.append(f"status: {why}")
    for txt, why in carried_present() + PRESENT_RC25:
        if flat(txt) not in fn_unstruck:
            fails.append(f"present: {why} sentence missing: {txt[:70]!r}")
    for txt in PRESENT_REPLACED:
        if flat(txt) in fn_unstruck:
            fails.append(f"present: replaced rc24 text still present: {txt[:70]!r}")
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
                fails.append(f"qualifier: {ph[:70]!r} occurs {b}x in rc25 against {a}x in rc24, not justified")
    for (ph, d) in JUSTIFIED_PHRASE:
        if pdeltas.get(ph) != d:
            fails.append(f"qualifier: JUSTIFIED_PHRASE lists {ph[:50]!r} {d:+d}; measured {pdeltas.get(ph, 0):+d}")
    gone = {ph for (ph, d) in list(JUSTIFIED_PHRASE) + list(R24.JUSTIFIED_PHRASE) + list(R23.JUSTIFIED_PHRASE)
            + list(R22.JUSTIFIED_PHRASE) + list(R21.JUSTIFIED_PHRASE) + list(R20.JUSTIFIED_PHRASE)
            + list(R19.JUSTIFIED_PHRASE) + list(R18.JUSTIFIED_PHRASE) + list(R17.JUSTIFIED_PHRASE)
            + list(R16.JUSTIFIED_PHRASE) + list(R15.JUSTIFIED_PHRASE) if d < 0 and fnn.count(ph) == 0}
    for k, v in h15.items():
        if flat(v) not in fnn and flat(v) not in gone:
            fails.append(f"headline: {k} — {v[:80]!r} not found in rc25")
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
    rep.append(f"locked phrases: {len(locked)}; justified deltas: {pdeltas}; hedge deltas: {hd}")
    if report:
        for k, v in sorted(per.items()):
            rep.append(f"  hedge [{k}]: {v}")
    # 8 integrity: rc24's carried checks (S, S18..S24; S19/L6 replaced by S23/M), then S25
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
    f19 = [x for x in f19 if not x.startswith("S19/L6")]   # replaced by S23/M, as in rc23
    f20, w20 = R20.source_facts_rc20(src20)
    f23, w23 = R23.source_facts_rc23(src23, new)
    f23 = [x for x in f23 if not x.startswith("S23/X: ST status:")]   # replaced by S24/F4, as in rc24
    f24, w24 = R24.source_facts_rc24(src24, src23, new)
    f25, w25 = source_facts_rc25(src25, src24, src23)
    fails += f19 + f20 + R21.source_facts_rc21(src21, new) + R22.source_facts_rc22(src22, new) + f23 + f24 + f25
    warns = list(warns) + w19 + w20 + w23 + w24 + w25
    # 9 REANALISE, bold
    if R11.R_ANY.search(new):
        fails.append("reanalise: a REANALISE marker is present in rc25")
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
        print(f"words: rc24 {len(old.split())} (body {len(body(old).split())}), "
              f"rc25 {len(new.split())} (body {len(body(new).split())})")
        for w in warns:
            print(w)
    if report:
        print("\nnumeric tokens added (and their source):")
        for k in sorted(added):
            print(f"  +{added[k]} {k}: {src_add.get(k, 'UNSOURCED')}")
        print("numeric tokens removed:", removed)
        print("phrase deltas:", pdeltas)
        for h in hs:
            print(f"\n[{'+'.join(h['ids']) or '?'}] rc24 l.{h['rc10'][0]}-{h['rc10'][1]} -> rc25 l.{h['rc11'][0]}-{h['rc11'][1]}")
            print("  - " + "\n  - ".join(h["old"].splitlines()[:4]))
            print("  + " + "\n  + ".join(h["new"].splitlines()[:4]))
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
    src21, src22, src23 = R21.load_src21(), R22.load_src22(), R23.load_src23()
    src24, src25 = R24.load_src24(), load_src25()
    kw0 = dict(cz=cz, st=st, A=A, files=files, files15=files15, src=src, src18=src18, src19=src19, src20=src20,
               src21=src21, src22=src22, src23=src23, src24=src24, src25=src25)
    rep1 = lambda a, b: (new.replace(a, b, 1), a in new)  # noqa: E731
    mutations = [
        ("R1: stamp note dropped", rep1(" (the receipt's stamp is local time, UTC−3: 12:31Z, after the 12:02Z extension)", "")),
        ("R1: 12:31Z -> 12:13Z", rep1("UTC−3: 12:31Z,", "UTC−3: 12:13Z,")),
        ("R2: 'nor are the two records' dropped", rep1(
            "is not in the\nmanifest, nor are the two records of the final Codex read of rc23 (Appendix B).",
            "is not in the\nmanifest.")),
        ("R3: parentheses removed", rep1("`B-censo/raw/` (see its row), and", "`B-censo/raw/`, see its row, and")),
        ("ST: 'rc24 has not been reviewed' restored", rep1(
            "rc24\n> had a diff check by Fable, rc23 → rc24, GO with three LOW in Appendix B and B.1);",
            "rc24\n> has not been reviewed);")),
        ("ST: rc25 entry dropped", rep1("rc25\n> prepared 2026-10-07 (those three LOW", "rc25\n> drafted 2026-10-07 (those three LOW")),
        ("WL: rc25 note dropped", rep1(TAIL_INSERTS[0], "")),
        ("CL: changelog item 205 removed", rep1("\n205. B.1", "\nB.1")),
        ("old changelog line edited", rep1("**rc24: final reads of rc23 applied**", "**rc24: final reads of rc23 (edited)**")),
        ("carried rc24: X1 'only to that extent' restored", rep1("is not a calibrated randomization p-value.",
                                                                 "is a randomization p-value only to that extent.")),
        ("carried rc24: status 790 -> 791", rep1("changed 790 of the 11,812", "changed 791 of the 11,812")),
        ("carried rc23: sham table 790 -> 791", rep1("| states moved (`mexeu`) | **790** |", "| states moved (`mexeu`) | **791** |")),
        ("carried title lock", rep1(TITLE, TITLE.replace("A registered horizon that", "A registration that"))),
        ("a heading changed", rep1("#### 4.0.1c The specificity control: invalid as first configured, then run",
                                   "#### 4.0.1c The specificity control")),
        ("unsourced number added", rep1("by 207 states over the largest", "by 207 states (5317 runs) over the largest")),
        ("H1 family untouched: H1c p moved", rep1("`p = 0.4006`", "`p = 0.4106`")),
    ]
    ok = True
    for name, (mutated, applied) in mutations:
        assert applied and mutated != new, f"mutation did not apply: {name}"
        f = [x for x in check(old, mutated, verbose=False, **kw0) if "has no ID" not in x]
        print(f"mutation [{name}]: {'CAUGHT' if f else 'MISSED'}" + (f" -> {f[0][:140]}" if f else ""))
        ok &= bool(f)

    integ = [
        ("S25/R1: receipt stamp re-timed", dict(src24=dict(src24, rcpt=src24["rcpt"].replace(
            "timestamp: 2026-10-07T093115", "timestamp: 2026-10-07T103115", 1)))),
        ("S25/R1: adversary-run.sh stamps in UTC", dict(src25=dict(src25, adv=(src25["adv"] or "").replace(
            'STAMP="$(date +%Y-%m-%dT%H%M%S)"', 'STAMP="$(date -u +%Y-%m-%dT%H%M%S)"')))),
        ("carried S24/ST: rc23 receipt exit 1", dict(src24=dict(src24, rcpt=src24["rcpt"].replace("\nexit: 0\n", "\nexit: 1\n", 1)))),
    ]
    if src23["manifest"] is not None:
        mj = json.loads(src23["manifest"])
        mj["extensoes"][-1]["em"] = "2026-10-07T12:42:12.963305+00:00"
        integ += [("S25/M: extension moved after the read", dict(src23=dict(src23, manifest=json.dumps(mj))))]
    for name, kw in integ:
        args = dict(kw0)
        args.update(kw)
        f = check(old, new, verbose=False, **args)
        if name.startswith("S25/"):   # an S25 mutation must be caught by its own S25 leg, not only by a pin
            tag = name.split(":")[0]
            f = [x for x in f if x.startswith(tag)]
        print(f"mutation [{name}] (integrity): {'CAUGHT' if f else 'MISSED'}" + (f" -> {f[0][:140]}" if f else ""))
        ok &= bool(f)
    base = check(old, new, verbose=False, **kw0)
    print(f"unmutated rc25: {'PASS' if not base else 'FAIL'}" + (f" -> {base}" if base else ""))
    print(f"mutations: {len(mutations) + len(integ)}")
    return 0 if ok and not base else 1


if __name__ == "__main__":
    sys.exit(main())
