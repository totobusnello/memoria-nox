#!/usr/bin/env python3
"""Parity check B-v2-rc23.md -> B-v2-rc24.md (Paper B, sprint 2026-10-04; rc24 2026-10-07).

rc23 had two full final reads, both GO with no MEDIUM or HIGH: Fable (critic agent run, four LOW)
and Codex (receipt `adversary-receipt-codex-2026-10-07T093115-73165.txt`, exit 0; verdict
`REVIEW-B-rc23-codex-2026-10-07.md`, five LOW). rc24 applies only those LOW wording fixes, each
verified first (`APPLY-B-rc24.md`). No number of the analysis or of the sham results moves.

  F1  §4.0.1c: the 400/400 is the real run's records against the calibration sample
      (DETERMINISMO.json has REAL_vs_amostra200 only), not "as are the 200 states" of all runs
  F2  status header + working list 24: both GO reads of rc23 recorded
  F3  §4.0.1c first limit + working list 15: runner start 2026-10-05T09:40:32Z (RECIBO.txt) beside
      the launcher time 2026-10-05T09:39:53Z (JANELA-LANCAMENTO.md)
  F4  status header: 790 "of the 11,812 reconstructible brief states", not "of the trial window"
  X1  §4.0.1c limits: "not a calibrated randomization p-value"
  X2  §4.0.1c "What it adds": "the range produced by these 20 matched designations"
  X3  §8.3: the window run is a second run, 2026-10-05 to 2026-10-07 (job-v2b ran 2026-10-04)
  X4  Appendix B v3 row: RESULTADO-v3.md covered through the B-registered/ directory hash
      (recomputed with scripts/manifesto-lastro-p2.py's sha256_dir = the manifest entry)
  X5  Appendix B manifest row: the manifest itself (and the two rc23-read records, written after
      it) among the exceptions; a row for those two records
  CL  the rc24 changelog block (195-203)

Checks (exit 1 if any fails): rc23's whole set (hunks with IDs, numbers sourced, invariants,
tail with the declared edits reverted equal to rc23, no SHAM-JANELA marker, carried locks of every
earlier rc, qualifiers/hedges, integrity S..S23), except the three rc23 locks that rc24 makes false
on purpose and replaces: the status mark "rc23 has not been reviewed" (F2), the S23/X status
sentence "brief states of the trial window" (F4, re-derived in its new form from RESUMO.json) and
the manifest-row present-lock (X5). NEW: block S24 checks every fact a fix rests on.

Usage:  python3 parity-rc24.py | --report | --self-test     Reads; writes nothing.
Caveat: S24/M reads ~/Backups/paper2-ensaio-2026-09-21 (outside the repository, by design); on a
machine without it the manifest legs of X4/X5 are reported as NOT VERIFIED warnings, never passed.
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
OLD = SPRINT / "B-v2-rc23.md"
NEW = SPRINT / "B-v2-rc24.md"
RC23 = SPRINT / "B-rc23" / "parity-rc23.py"
RC23_SHA = "167263a2f6ace9c7a14da3c84e1ebd3762a08fcc95571deb1a45a4a6ac0ca24f"
OLD_SHA = "ff46bd65e5b6122a2d7d43fee00318e7ea2d42b6b18660157e82a8f5d0ad47f9"

assert hashlib.sha256(RC23.read_bytes()).hexdigest() == RC23_SHA, \
    "parity-rc23.py changed: the locks carried from it are no longer the ones rc23 ran"
_spec = importlib.util.spec_from_file_location("parity_rc23", RC23)
R23 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(R23)
R22, R21, R20, R19, R18, R17 = R23.R22, R23.R21, R23.R20, R23.R19, R23.R18, R23.R17
R16, R15, R14, R13, R12, R11 = R23.R16, R23.R15, R23.R14, R23.R13, R23.R12, R23.R11
flat, body, tail, sci, load = R23.flat, R23.body, R23.tail, R23.sci, R23.load
TITLE = R23.TITLE
S_OPEN, S_CLOSE = R23.S_OPEN, R23.S_CLOSE
nf, sha_b = R23.nf, R23.sha_b

RECEIPT24 = "adversary-receipt-codex-2026-10-07T093115-73165.txt"
REVIEW24 = "REVIEW-B-rc23-codex-2026-10-07.md"
BREG_SHA = "2555baf8f5d057c85496579724e7d2f0a362df678b8ef326c637d6d080ce9be3"
SOURCES24 = {
    "rcpt": SPRINT / "receipts" / RECEIPT24,
    "review": SPRINT / REVIEW24,
    "status_v2b": SPRINT / "B-sham-v2" / "job-v2b" / "STATUS",
    "recibo_v2b": SPRINT / "B-sham-v2" / "job-v2b" / "RECIBO.txt",
}


def _sha256_dir():
    spec = importlib.util.spec_from_file_location("manifesto_lastro_p2", REPO / "scripts" / "manifesto-lastro-p2.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m.sha256_dir


def load_src24():
    src = {k: p.read_text(encoding="utf-8") for k, p in SOURCES24.items()}
    sd = _sha256_dir()
    src["breg_dir"] = sd(SPRINT / "B-registered")
    src["breg_files"] = sorted(p.name for p in (SPRINT / "B-registered").iterdir() if p.is_file())
    src["receipts_live"] = sorted(p.name for p in (SPRINT / "receipts").iterdir() if p.is_file())
    src["receipts_copy"] = None
    return src


def status_sentence(f):
    m, n = f["mexeu"], f["fid"][0]
    return (f"changed {m['real']} of the {nf(n)} reconstructible brief states against {m['lo']}–{m['hi']} "
            f"for 20 matched shams, `p = 1/21`")


# ---------------------------------------------------------------- S24: the facts the fixes rest on
def source_facts_rc24(src, src23, new):
    fails, warns = [], []
    # F1: DETERMINISMO compares REAL (only) with the 200-state sample, 400/400
    d = json.loads(src23["det"])
    if (d["REAL_vs_amostra200"]["identicos"], d["REAL_vs_amostra200"]["compartilhados"],
            d["REAL_vs_amostra200"]["estados"]) != (400, 400, 200):
        fails.append("S24/F1: DETERMINISMO REAL_vs_amostra200 is not 400/400 on 200 states")
    if any("amostra" in k for k in d if k != "REAL_vs_amostra200") or \
            any("amostra" in k for v in d["SHAMS_vs_job_v2b"].values() for k in v):
        fails.append("S24/F1: DETERMINISMO has a sham-against-sample comparison; the rc24 wording narrows too far")
    # F3: launcher 09:39:53Z (JANELA-LANCAMENTO), runner start 09:40:32Z (RECIBO line 1)
    rec = src23["recibo"].splitlines()
    if not rec or not rec[0].startswith("inicio 2026-10-05T09:40:32Z ") or "(ate 2026-10-08T20:09:53Z)" not in rec[0]:
        fails.append("S24/F3: RECIBO.txt does not start at 2026-10-05T09:40:32Z with the 09:39:53Z-based deadline")
    if "## Relançamento 2026-10-05T09:39:53Z (`job-janela2`, 11.812 estados)" not in src23["janela"]:
        fails.append("S24/F3: JANELA-LANCAMENTO.md no longer records the 09:39:53Z relaunch")
    # F4: the status sentence in its rc24 form, from RESUMO.json
    _, f = R23.facts23(src23)
    fn = flat(R11.strip_struck(new.replace("\n> ", "\n")))
    if flat(status_sentence(f)) not in fn:
        fails.append(f"S24/F4: status sentence not in the form the files give: {status_sentence(f)!r}")
    # X3: the first replay ran and finished on 2026-10-04; the window run 2026-10-05..07
    if not src["status_v2b"].startswith("CONCLUIDO 2026-10-04T") or not src["recibo_v2b"].startswith("inicio 2026-10-04T"):
        fails.append("S24/X3: job-v2b did not start and finish on 2026-10-04")
    if not src23["status"].startswith("CONCLUIDO 2026-10-07T") or not rec[0].startswith("inicio 2026-10-05T"):
        fails.append("S24/X3: job-janela2 did not run 2026-10-05 to 2026-10-07")
    # X4: B-registered/ hashes, by the manifest's own function, to the manifest entry, with RESULTADO-v3.md
    if src["breg_dir"][0] != BREG_SHA or src["breg_dir"][2] != 19 or "RESULTADO-v3.md" not in src["breg_files"]:
        fails.append(f"S24/X4: B-registered/ hashes {src['breg_dir'][0][:12]}… ({src['breg_dir'][2]} files), "
                     f"not 2555baf8… (19) with RESULTADO-v3.md")
    # X5 + receipts: the manifest's receipts/ entry has 22 files; the rc23-read records are not in it
    if RECEIPT24 not in src["receipts_live"] or len(src["receipts_live"]) != 23:
        fails.append("S24/X5: receipts/ does not hold 23 receipts including the rc23 Codex read")
    if src23["manifest"] is None:
        warns.append("S24/M: ballast manifest not on this machine: B-registered/ entry and receipts/ count NOT VERIFIED")
    else:
        e = {x["nome"]: x for x in json.loads(src23["manifest"])["artefatos"]}
        br, rc = e.get("_sprint-2026-10-04/B-registered"), e.get("_sprint-2026-10-04/receipts")
        if not br or (br["sha256"], br["ficheiros"]) != (BREG_SHA, 19):
            fails.append("S24/M: the manifest's B-registered/ entry is not 2555baf8…, 19 files")
        if not rc or rc["ficheiros"] != 22:
            fails.append("S24/M: the manifest's receipts/ entry does not hash 22 receipts")
        else:
            cp = Path(rc["caminho"])
            if cp.exists() and (RECEIPT24 in {p.name for p in cp.iterdir()} or len(list(cp.iterdir())) != 22):
                fails.append("S24/M: the ballast copy of receipts/ is not the 22 receipts without the rc23 read")
        if any(REVIEW24 in n or RECEIPT24 in n for n in e):
            fails.append("S24/M: an rc23-read record is in the manifest; rc24 says it is not")
    # the two reads: Codex receipt exit 0; verdict GO, no MEDIUM/HIGH, five LOW at the cited lines
    r = src["rcpt"]
    if "voice: codex\n" not in r or "\nexit: 0\n" not in r or "timestamp: 2026-10-07T093115\n" not in r:
        fails.append("S24/ST: the Codex receipt is not voice codex, exit 0, 2026-10-07T093115")
    if re.search(r"\b\d{1,3}(?:\.\d{1,3}){3}\b", r):
        fails.append("S24/ST: the receipt carries an IP address")
    v = src["review"]
    lows = re.findall(r"^- \[L(\d+)\]", v, re.M)
    if "**No MEDIUM/HIGH findings.**" not in v or not v.rstrip().endswith("**GO**") \
            or lows != ["1243", "1276", "2285", "2658", "2676"]:
        fails.append("S24/ST: the Codex verdict is not GO, no MEDIUM/HIGH, five LOW at 1243/1276/2285/2658/2676")
    return fails, warns


# ---------------------------------------------------------------- 1: anchors
ANCHORS = [
    ("ST", "rc24 prepared\n> 2026-10-07 (the LOW wording fixes"),
    ("ST", "changed 790 of the 11,812 reconstructible brief states"),
    ("F3", "runner start\n  2026-10-05T09:40:32Z"),
    ("X1", "is not a calibrated randomization p-value."),
    ("F1", "and the real run's records for the 200 states"),
    ("X2", "the range produced by these 20 matched designations"),
    ("X3", "in a second run, 2026-10-05 to 2026-10-07"),
    ("X4", "the corrected file is covered by the rc23 ballast manifest through the `B-registered/` directory hash"),
    ("X5", "(excepted: the manifest itself,"),
    ("X5", "| the final Codex read of rc23 (`exit: 0`;"),
    ("WL", "(launcher 2026-10-05T09:39:53Z; runner start"),
    ("WL", "*(rc24: rc23 had two full reads"),
    ("CL", "**rc24: final reads of rc23 applied**"),
]
REMOVED_ANCHORS = []

# ---------------------------------------------------------------- 2: numbers
JUSTIFIED_REMOVED = {}


def derived_rc24(src23):
    out = {}
    for k in ("2026-10-05T09:40:32Z", "09:40:32Z", "2026-10-05T09:40:32"):
        out[k] = "runner start, RECIBO.txt line 1 (checked in S24/F3)"
    for k in ("2026-10-07T093115-73165", "093115", "73165", "2026-10-07T093115"):
        out[k] = "Codex receipt name (checked in S24/ST)"
    out["22"] = "receipts hashed by the manifest's receipts/ entry (checked in S24/M)"
    return out


# ---------------------------------------------------------------- 3/4: tail
TAIL_INSERTS = [
    """
    *(rc24: rc23 had two full reads, both GO with no MEDIUM or HIGH: Fable (an agent run, four
    LOW) and Codex (`adversary-receipt-codex-2026-10-07T093115-73165.txt`,
    `REVIEW-B-rc23-codex-2026-10-07.md`, five LOW); all verified and applied in rc24
    (`APPLY-B-rc24.md`). rc24 changes wording only; it has not been reviewed.)*""",
]
TAIL_EDITS = [  # (rc23 text, rc24 text) — working list 15, Fable LOW 3
    ("""→ **Done, rc23 (2026-10-07)**: `job-janela2`
    CONCLUIDO 2026-10-07T02:09:46Z,""",
     """→ **Done, rc23 (2026-10-07)**: `job-janela2`
    (launcher 2026-10-05T09:39:53Z; runner start 2026-10-05T09:40:32Z in `RECIBO.txt`, added
    in rc24) CONCLUIDO 2026-10-07T02:09:46Z,"""),
]
CL_ITEMS = [(195, "§4.0.1c (Fable LOW 1)"), (196, "Status header and working list 24 (Fable LOW 2)"),
            (197, "§4.0.1c first limit and working list 15 (Fable LOW 3)"), (198, "Status header (Fable LOW 4)"),
            (199, "§4.0.1c limits (Codex LOW 1)"), (200, "§4.0.1c \"What it adds\" (Codex LOW 2)"),
            (201, "§8.3 (Codex LOW 3)"), (202, "Appendix B, v3 row (Codex LOW 4)"),
            (203, "Appendix B, manifest row (Codex LOW 5)")]

# ---------------------------------------------------------------- 6: locks
SWEEP_LOCK_RC24 = [
    (r"(?i)a randomization p-value only to that extent", "X1: the rank p-value is not a calibrated one"),
    (r"(?i)the background that a matched designation produces", "X2: the range of these 20 designations"),
    (r"(?i)no recorded sha256 covers that file", "X4: B-registered/ is in the rc23 manifest"),
    (r"(?i)as are the 200 states of the calibration sample", "F1: only the real run is compared with the sample"),
    (r"(?i)brief states of the trial window against", "F4: the denominator is the 11,812 reconstructible states"),
    (r"(?i)on 2026-10-04: the real designation ranks above all 20 shams on the `w = 4` epochs, and again over "
     r"the whole hash-verified trial window \(", "X3: the window run is a second run, 2026-10-05 to 2026-10-07"),
    (r"(?i)every artifact in this table \(`B-censo/raw/` excepted, see its row\)", "X5: the manifest itself excepted"),
]
PRESENT_RC24 = [
    ("so the rank p-value is not a calibrated randomization p-value.", "X1"),
    ("and the real run's records for the 200 states of the calibration sample are identical to that sample "
     "(400/400): the replay is deterministic", "F1"),
    ("the shams' 449–583 is the range produced by these 20 matched designations at `w = 4` in these states.", "X2"),
    ("again over the whole hash-verified trial window in a second run, 2026-10-05 to 2026-10-07 (§4.0.1c).", "X3"),
    ("No number changed, and the corrected file is covered by the rc23 ballast manifest through the "
     "`B-registered/` directory hash.", "X4"),
    ("SHA-256 hashes of the 115 artifacts currently covered, for loss detection: from rc23, every artifact in this "
     "table (excepted: the manifest itself, `B-censo/raw/`, see its row, and the two records of the final Codex "
     "read of rc23, written after the manifest, see their row)", "X5 manifest row"),
    ("Both records were written after the rc23 ballast manifest and are not in it: the manifest's `receipts/` "
     "entry hashes the 22 receipts present when it was extended (added in rc24) |", "X5 new row"),
    ("relaunched 2026-10-05T09:39:53Z, runner start 2026-10-05T09:40:32Z, completed", "F3 §4.0.1c"),
]
PRESENT_REPLACED = {
    "SHA-256 hashes of the 115 artifacts currently covered, for loss detection: from rc23, every artifact in this "
    "table (`B-censo/raw/` excepted, see its row)": "X5: the manifest itself and the rc23-read records excepted",
}
STATUS_MARKS_RC24 = [m for m in R23.STATUS_MARKS_RC23 if m != "rc23 has not been reviewed"] + [
    "rc23 had two full reads, Fable and Codex, both GO with no MEDIUM or HIGH", RECEIPT24,
    "rc24 prepared 2026-10-07 (the LOW wording fixes of those two reads applied", "rc24 changes wording only",
    "rc24 has not been reviewed"]
STATUS_LOCK = R23.STATUS_LOCK + [(r"rc23 has not been reviewed", "F2: rc23 had two GO reads")]
STRUCK_DELTA = {}

# ---------------------------------------------------------------- 7: qualifier deltas (from --report)
JUSTIFIED_PHRASE = {
    ("not a calibrated", +2): "X1: §4.0.1c limit 'not a calibrated randomization p-value' and its changelog item 199",
}
JUSTIFIED_HEDGE = {
    "ST": ({"no": 2, "only": 1}, "status: 'both GO with no MEDIUM or HIGH', 'no number … moves', 'changes wording only'"),
    "X1": ({"not": 1, "only": -1}, "'a randomization p-value only to that extent' -> 'not a calibrated randomization p-value'"),
    "X4": ({"no": -1}, "'no recorded sha256 covers that file' -> 'covered … through the B-registered/ directory hash'"),
    "X5": ({"not": 1, "no": 3}, "new row: 'no MEDIUM or HIGH' (Codex, Fable), 'left no file', 'are not in it'"),
}


def carried_present():
    return [p for p in R23.carried_present() + R23.PRESENT_RC23 if p[0] not in PRESENT_REPLACED]


def check(old, new, verbose=True, report=False, cz=None, st=None, A=None, files=None, files15=None,
          src=None, src18=None, src19=None, src20=None, src21=None, src22=None, src23=None, src24=None):
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
    src24 = src24 or load_src24()
    if files is None:
        files = {k: p.read_bytes() for k, p in R15.ART.items()}
        files["res4_frozen"] = R17.RES4_FROZEN.read_bytes()
    files15 = files15 or {"py": R16.FROZEN_TEST_PY.read_bytes(), "json": R16.FROZEN_TEST_JSON.read_bytes()}
    fails, rep = [], []
    if hashlib.sha256(old.encode()).hexdigest() != OLD_SHA:
        fails.append("rc23 is not the ff46bd65… bytes rc23's parity passed on")
    ob, nb = body(old), body(new)
    # 2 numbers
    dn, do = R11.numbers(nb), R11.numbers(ob)
    delta = {k: dn[k] - do[k] for k in set(dn) | set(do) if dn[k] != do[k]}
    removed = {k: -d for k, d in delta.items() if d < 0}
    for k in sorted(set(removed) | set(JUSTIFIED_REMOVED)):
        if removed.get(k, 0) != JUSTIFIED_REMOVED.get(k, (0,))[0]:
            fails.append(f"numbers: token {k!r} removed {removed.get(k, 0)}x; JUSTIFIED_REMOVED declares "
                         f"{JUSTIFIED_REMOVED.get(k, (0,))[0]}x")
    der = derived_rc24(src23)
    old_nums = R11.numbers(old)
    added = {k: d for k, d in delta.items() if d > 0}
    src_add = {}
    for k in sorted(added):
        if old_nums[k]:
            src_add[k] = "in rc23"
        elif k in der:
            src_add[k] = "derived: " + der[k]
        else:
            fails.append(f"numbers: token {k!r} added {added[k]}x is neither in rc23 nor derived")
    # 1 hunks
    hs = R11.hunks(old, new)
    for h in hs:
        ids = [aid for aid, anc in ANCHORS if anc in h["new"]]
        ids += [aid for anc, aid in REMOVED_ANCHORS if not h["new"].strip() and anc in h["old"]]
        h["ids"] = list(dict.fromkeys(ids))
        if not h["ids"]:
            fails.append(f"hunk rc23 {h['rc10']} rc24 {h['rc11']} has no ID: {(h['new'] or h['old'])[:80]!r}")
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
                fails.append(f"invariant: struck spans moved by {d}; rc24 declares {STRUCK_DELTA}")
        elif name in R17.INV_FIXED and d:
            fails.append(f"invariant: {name} changed: {dict(list(d.items())[:4])}")
        rep.append(f"{name}: {sum(a.values())} -> {sum(b.values())}" + ("" if not d else f"  (delta {len(d)} items)"))
        if report and d and (name in R17.INV_FREE or name == "struck spans"):
            for k, v in sorted(d.items(), key=lambda kv: str(kv[0]))[:60]:
                rep.append(f"    {v:+d} {str(k)[:150]}")
    if R11.headings(old) != R11.headings(new):
        fails.append("invariant: heading list changed (rc24 changes no heading)")
    if new.count(R20.H301_NEW) != 1:
        fails.append("invariant: the rc20 §3.0.1 heading is not in rc24 exactly once")
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
    i24 = t.find("\n\n**rc24: final reads of rc23 applied**")
    blocks24 = t[i24:] if i24 >= 0 else ""
    t = t[:i24] + "\n" if i24 >= 0 else t
    if i24 < 0:
        fails.append("tail: the rc24 changelog block is missing")
    if t != to:
        fails.append("tail: working list / changelog, with the declared insertions and edits reverted and the rc24 "
                     "block removed, is not byte-identical to rc23")
    i = tn.find("\n**rc14: writing pass**")
    nums = [int(x) for x in re.findall(r"^(\d+)\. ", tn[i:] if i >= 0 else "", re.M)]
    if nums != list(range(149, 204)):
        fails.append(f"tail: rc14-rc24 changelog items are {nums[-8:]}…, expected 149..203")
    for n, needle in CL_ITEMS:
        if not re.search(rf"^{n}\. {re.escape(needle)}", blocks24, re.M):
            fails.append(f"tail: changelog item {n} missing")
    fb = flat(blocks24)
    if "_sprint-2026-10-04/APPLY-B-rc24.md`" not in fb or RECEIPT24 not in fb or "wording only" not in fb \
            or "both GO with no MEDIUM or HIGH" not in fb:
        fails.append("tail: the rc24 block does not name both GO reads, the receipt, the APPLY record and 'wording only'")
    # 5 SHAM: none in rc23 and none in rc24
    sn, en = R11.sham_spans(new)
    fails += en
    if sn or S_OPEN in new or S_CLOSE in new or "SHAM-JANELA: pending" in new:
        fails.append("sham: a SHAM-JANELA marker is in rc24")
    # 6 carried locks + rc24
    fails += R13.claims_rc13(new, cz)
    nb_unstruck = R11.strip_struck(nb)
    fn_unstruck = flat(nb_unstruck)
    for pat, why in (R15.SWEEP_LOCK + R16.SWEEP_LOCK_RC16 + R17.SWEEP_LOCK_RC17 + R18.SWEEP_LOCK_RC18
                     + R19.SWEEP_LOCK_RC19 + R20.SWEEP_LOCK_RC20 + R21.SWEEP_LOCK_RC21
                     + R22.SWEEP_LOCK_RC22 + R23.SWEEP_LOCK_RC23 + SWEEP_LOCK_RC24):
        for mo in re.finditer(pat, fn_unstruck):
            fails.append(f"sweep: {why}: {fn_unstruck[max(0, mo.start() - 60):mo.end() + 30]!r}")
    head = new[:new.find("\n---")]
    for mk in STATUS_MARKS_RC24:
        if mk not in head and flat(mk) not in flat(head.replace("> ", " ")):
            fails.append(f"status: header does not record {mk.splitlines()[0]!r}")
    for pat, why in STATUS_LOCK:
        if re.search(pat, flat(head.replace("> ", " "))):
            fails.append(f"status: {why}")
    for txt, why in carried_present() + PRESENT_RC24:
        if flat(txt) not in fn_unstruck:
            fails.append(f"present: {why} sentence missing: {txt[:70]!r}")
    for txt in PRESENT_REPLACED:
        if flat(txt) in fn_unstruck:
            fails.append(f"present: replaced rc23 text still present: {txt[:70]!r}")
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
                fails.append(f"qualifier: {ph[:70]!r} occurs {b}x in rc24 against {a}x in rc23, not justified")
    for (ph, d) in JUSTIFIED_PHRASE:
        if pdeltas.get(ph) != d:
            fails.append(f"qualifier: JUSTIFIED_PHRASE lists {ph[:50]!r} {d:+d}; measured {pdeltas.get(ph, 0):+d}")
    gone = {ph for (ph, d) in list(JUSTIFIED_PHRASE) + list(R23.JUSTIFIED_PHRASE) + list(R22.JUSTIFIED_PHRASE)
            + list(R21.JUSTIFIED_PHRASE) + list(R20.JUSTIFIED_PHRASE) + list(R19.JUSTIFIED_PHRASE)
            + list(R18.JUSTIFIED_PHRASE) + list(R17.JUSTIFIED_PHRASE) + list(R16.JUSTIFIED_PHRASE)
            + list(R15.JUSTIFIED_PHRASE) if d < 0 and fnn.count(ph) == 0}
    for k, v in h15.items():
        if flat(v) not in fnn and flat(v) not in gone:
            fails.append(f"headline: {k} — {v[:80]!r} not found in rc24")
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
    # 8 integrity: rc23's carried checks (S, S18..S23; S19/L6 replaced by S23/M as in rc23), then S24
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
    f23 = [x for x in f23 if not x.startswith("S23/X: ST status:")]   # replaced by S24/F4 (new form)
    f24, w24 = source_facts_rc24(src24, src23, new)
    fails += f19 + f20 + R21.source_facts_rc21(src21, new) + R22.source_facts_rc22(src22, new) + f23 + f24
    warns = list(warns) + w19 + w20 + w23 + w24
    # 9 REANALISE, bold
    if R11.R_ANY.search(new):
        fails.append("reanalise: a REANALISE marker is present in rc24")
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
        print(f"words: rc23 {len(old.split())} (body {len(body(old).split())}), "
              f"rc24 {len(new.split())} (body {len(body(new).split())})")
        for w in warns:
            print(w)
    if report:
        print("\nnumeric tokens added (and their source):")
        for k in sorted(added):
            print(f"  +{added[k]} {k}: {src_add.get(k, 'UNSOURCED')}")
        print("numeric tokens removed:", removed)
        print("phrase deltas:", pdeltas)
        for h in hs:
            print(f"\n[{'+'.join(h['ids']) or '?'}] rc23 l.{h['rc10'][0]}-{h['rc10'][1]} -> rc24 l.{h['rc11'][0]}-{h['rc11'][1]}")
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
    src21, src22, src23, src24 = R21.load_src21(), R22.load_src22(), R23.load_src23(), load_src24()
    rep1 = lambda a, b: (new.replace(a, b, 1), a in new)  # noqa: E731
    mutations = [
        ("X1: 'only to that extent' restored", rep1("is not a calibrated randomization p-value.",
                                                    "is a randomization p-value only to that extent.")),
        ("X2: 'background' restored", rep1("is the range produced by these 20 matched designations at",
                                           "is the background that a matched designation produces at")),
        ("X3: second-run dates dropped", rep1(" in a second run, 2026-10-05 to 2026-10-07\n(§4.0.1c).", " (§4.0.1c).")),
        ("X4: 'no recorded sha256' restored", rep1(
            "the corrected file is covered by the rc23 ballast manifest through the `B-registered/` directory hash.",
            "no recorded sha256 covers that file.")),
        ("X5: manifest-itself exception dropped", rep1("(excepted: the manifest itself, `B-censo/raw/`,", "(excepted: `B-censo/raw/`,")),
        ("X5: rc23-read row says 23 receipts", rep1("hashes the 22 receipts present", "hashes the 23 receipts present")),
        ("F1: 'as are the 200 states' restored", rep1(
            "and the real run's records for the 200 states\nof the calibration sample are identical to that sample (400/400)",
            "as are the 200 states of the calibration sample\n(400/400)")),
        ("F3: runner start re-timed", rep1("runner start\n  2026-10-05T09:40:32Z", "runner start\n  2026-10-05T09:41:32Z")),
        ("F4: 'of the trial window' restored", rep1("changed 790 of the 11,812 reconstructible brief states against",
                                                    "changed 790 brief states of the trial window against")),
        ("F4: status 790 -> 791", rep1("changed 790 of the 11,812", "changed 791 of the 11,812")),
        ("F2: 'rc23 has not been reviewed' restored in the status", rep1(
            "rc23 had two full reads, Fable and Codex, both GO with no MEDIUM or HIGH,", "rc23 has not been reviewed,")),
        ("ST: rc24 entry dropped", rep1("rc24 prepared\n> 2026-10-07 (the LOW", "rc24 drafted\n> 2026-10-07 (the LOW")),
        ("WL: rc24 note in item 24 dropped", rep1(TAIL_INSERTS[0], "")),
        ("WL: item 15 runner start dropped", rep1(TAIL_EDITS[0][1], TAIL_EDITS[0][0])),
        ("CL: changelog item 201 removed", rep1("\n201. §8.3", "\n§8.3")),
        ("old changelog line edited", rep1("**rc23: whole-window sham result integrated; ballast extended**",
                                           "**rc23: whole-window sham result integrated (edited)**")),
        ("carried rc23: sham table 790 -> 791", rep1("| states moved (`mexeu`) | **790** |", "| states moved (`mexeu`) | **791** |")),
        ("carried rc23: 'not independent' dropped", rep1("this run is not independent of the first, it\nextends it",
                                                          "this run extends")),
        ("carried rc22: 1.02% restored", rep1("unknown share of opportunities is 1.00%", "unknown share of opportunities is 1.02%")),
        ("carried title lock", rep1(TITLE, TITLE.replace("A registered horizon that", "A registration that"))),
        ("a heading changed", rep1("#### 4.0.1c The specificity control: invalid as first configured, then run",
                                   "#### 4.0.1c The specificity control")),
        ("unsourced number added", rep1("by 207 states over the largest", "by 207 states (5317 runs) over the largest")),
        ("H1 family untouched: H1c p moved", rep1("`p = 0.4006`", "`p = 0.4106`")),
    ]
    ok = True
    for name, (mutated, applied) in mutations:
        assert applied and mutated != new, f"mutation did not apply: {name}"
        f = [x for x in check(old, mutated, verbose=False, cz=cz, st=st, A=A, files=files, files15=files15,
                              src=src, src18=src18, src19=src19, src20=src20, src21=src21, src22=src22,
                              src23=src23, src24=src24)
             if "has no ID" not in x]
        print(f"mutation [{name}]: {'CAUGHT' if f else 'MISSED'}" + (f" -> {f[0][:140]}" if f else ""))
        ok &= bool(f)

    det_sham = json.loads(src23["det"])
    det_sham["SHAMS_vs_job_v2b"]["SHAM-003"]["vs_amostra200"] = {"identicos": 400}
    integ = [
        ("S24/F1: a sham-against-sample comparison appears", dict(src23=dict(src23, det=json.dumps(det_sham)))),
        ("S24/F3: RECIBO start re-timed", dict(src23=dict(src23, recibo=src23["recibo"].replace(
            "inicio 2026-10-05T09:40:32Z", "inicio 2026-10-05T09:41:32Z", 1)))),
        ("S24/X3: job-v2b finished 10-05", dict(src24=dict(src24, status_v2b=src24["status_v2b"].replace(
            "2026-10-04T", "2026-10-05T", 1)))),
        ("S24/X4: B-registered/ hash differs", dict(src24=dict(src24, breg_dir=("0" * 64, 605260, 19)))),
        ("S24/X4: RESULTADO-v3.md missing", dict(src24=dict(src24, breg_files=[x for x in src24["breg_files"]
                                                                              if x != "RESULTADO-v3.md"]))),
        ("S24/X5: the rc23 receipt absent from receipts/", dict(src24=dict(src24, receipts_live=[
            x for x in src24["receipts_live"] if x != RECEIPT24]))),
        ("S24/ST: receipt exit 1", dict(src24=dict(src24, rcpt=src24["rcpt"].replace("\nexit: 0\n", "\nexit: 1\n", 1)))),
        ("S24/ST: verdict NO-GO", dict(src24=dict(src24, review=src24["review"].replace("**GO**", "**NO-GO**")))),
        ("S24/ST: a sixth LOW", dict(src24=dict(src24, review=src24["review"] + "\n- [L9](x): extra\n"))),
        ("carried S23/R: REAL mexeu in RESUMO", dict(src23=dict(
            src23, resumo=src23["resumo"].replace('"mexeu": 790', '"mexeu": 560', 1)))),
        ("carried S22/ST: rc21 receipt exit 1", dict(src22=dict(src22, rcpt=src22["rcpt"].replace("\nexit: 0\n", "\nexit: 1\n", 1)))),
    ]
    if src23["manifest"] is not None:
        mj = json.loads(src23["manifest"])
        for e in mj["artefatos"]:
            if e["nome"] == "_sprint-2026-10-04/receipts":
                e["ficheiros"] = 23
        integ += [("S24/M: manifest receipts/ entry 23 files", dict(src23=dict(src23, manifest=json.dumps(mj))))]
    for name, kw in integ:
        args = dict(cz=cz, st=st, A=A, files=files, files15=files15, src=src, src18=src18, src19=src19,
                    src20=src20, src21=src21, src22=src22, src23=src23, src24=src24)
        args.update(kw)
        f = check(old, new, verbose=False, **args)
        if name.startswith("S24/"):   # an S24 mutation must be caught by its own S24 leg, not only by a pin
            tag = name.split(":")[0]
            f = [x for x in f if x.startswith(tag)]
        print(f"mutation [{name}] (integrity): {'CAUGHT' if f else 'MISSED'}" + (f" -> {f[0][:140]}" if f else ""))
        ok &= bool(f)
    base = check(old, new, verbose=False, cz=cz, st=st, A=A, files=files, files15=files15, src=src,
                 src18=src18, src19=src19, src20=src20, src21=src21, src22=src22, src23=src23, src24=src24)
    print(f"unmutated rc24: {'PASS' if not base else 'FAIL'}" + (f" -> {base}" if base else ""))
    print(f"mutations: {len(mutations) + len(integ)}")
    return 0 if ok and not base else 1


if __name__ == "__main__":
    sys.exit(main())
