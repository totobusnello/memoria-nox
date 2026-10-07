#!/usr/bin/env python3
"""Parity check B-v2-rc17.md -> B-v2-rc18.md (Paper B, sprint 2026-10-04; rc18 2026-10-05).

rc18 applies the Fable read of rc17 (NO-GO, three MEDIUM, four LOW, no HIGH), each finding verified
against its primary source first (`APPLY-B-rc18.md`). No number of the analysis moves and no artifact
of the analysis changes.

M-3, verified, and adapted where the source did not hold:
  * the DEPOSITED bytes of `DECISION-designacao-2026-08-25.md` are the blob of commit d42f950
    (2026-08-25T16:16:58Z): md5 35abeb68… in the Zenodo v1.12 file list (snapshot in this
    directory) equals the md5 of that blob, and of no later commit. That version is OPEN ("aberta,
    aguardando o Toto"), lays out options A-D and recommends B (a seeded SHA256 draw, one chunk per
    signature group, keyed on sig_primary and chunk_id). No "DECIDIDO" in it.
  * v1.12 was published at 2026-08-26T12:01Z (Zenodo record `created` 12:01:06Z), NOT 14:01Z as
    rc17 said from `deposit/PLAN-v1.13.md` (that file gives UTC+2 labelled Z). The decision
    (14:47Z, UTC: commit c46d7e3 at 14:48:45Z) is therefore 2 h 46 min after publication, not the
    46 min the review proposed. rc17's source check (plan13 needle) is carried as a check that
    PLAN-v1.13 still carries that mislabelled time, which rc18 declares and does not edit.

Checks (exit 1 if any fails):
  1. hunks: every hunk rc17 -> rc18 carries an ID from ANCHORS.
  2. numbers: every numeric token REMOVED from the body is in JUSTIFIED_REMOVED with its exact count;
     every token ADDED is in rc17, an artifact leaf, or derived (derived_rc18, each read from its
     source file here).
  3. invariants rc17 -> rc18: italic quotations, citations, footnotes, DOIs, image links, struck
     spans unchanged; headings identical except the declared §3.0.1 heading (L3); title lock.
  4. working list and changelog: rc18's, with the declared insertion, the declared rc17-block edit
     reverted and the rc18 block removed, is byte-identical to rc17's; changelog items 149-167.
  5. SHAM-JANELA: 10 blocks byte-identical to rc17.
  6. carried locks: rc17's (incl. rc16/rc15/rc13 carried, and the title lock), with declared
     replacements; NEW sweep (SWEEP_LOCK_RC18) and presence locks (PRESENT_RC18).
  7. qualifier set and hedge words, per hunk-ID group, summed to the body delta.
  8. integrity: rc17's carried checks (incl. its source block S and RESULTADO-v4 = frozen + note);
     NEW source block S18 (Zenodo snapshot, deposited DECISION bytes via `git show`, the seed file,
     the designation record, the band-collapse draft, the PREREG lines cited).
  9. no REANALISE marker; bold balanced per paragraph.

Usage:  python3 parity-rc18.py | --report | --self-test     Reads; writes nothing.
"""
import collections
import datetime as dt
import hashlib
import importlib.util
import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPRINT = HERE.parent
P2 = SPRINT.parent
REPO = P2.parent
OLD = SPRINT / "B-v2-rc17.md"
NEW = SPRINT / "B-v2-rc18.md"
RC17 = SPRINT / "B-rc17" / "parity-rc17.py"
RC17_SHA = "dc25fa228e7a82e8a14c6f50e2f68257e555b15026903a8cac5f240c3264eb63"
OLD_SHA = "2af6226676e79d04cfd611b2d663eea3f5c808ae7ff2b16d0f4171509c5996c6"

assert hashlib.sha256(RC17.read_bytes()).hexdigest() == RC17_SHA, \
    "parity-rc17.py changed: the locks carried from it are no longer the ones rc17 ran"
_spec = importlib.util.spec_from_file_location("parity_rc17", RC17)
R17 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(R17)
R16, R15, R14, R13, R12, R11 = R17.R16, R17.R15, R17.R14, R17.R13, R17.R12, R17.R11
flat, body, tail, sha, sci, load = R17.flat, R17.body, R17.tail, R17.sha, R17.sci, R17.load

TITLE = ("# A registered horizon that outlived its intervention: a pre-registered randomized trial of "
         "memory dosing in a production agent fleet")
TITLE_OLD = "A registration that outlived its intervention"
H301_OLD = "### 3.0.1 `N = 234` was infeasible by construction, and the trial ran exactly as long as it could"
H301_NEW = "### 3.0.1 `N = 234` was infeasible once the designation was frozen, and the trial ran exactly as long as it could"

DEPOSITED_DECISION_COMMIT = "d42f950"
DECISION_PATH = "paper2-interventional/DECISION-designacao-2026-08-25.md"
SOURCES18 = {
    "zrec": HERE / "zenodo-22110203-record.json",
    "zfiles": HERE / "zenodo-22110203-files.json",
    "dseed": P2 / "DESIGNATION-SEED-2026-08-26.md",
    "desig": P2 / "DESIGNATION-2026-08-26.json",
    "band": P2 / "AMENDMENT-DRAFT-band-collapse-2026-08-26.md",
    "prereg": P2 / "PREREG-DRAFT.md",
    "dep12": P2 / "deposit" / "deposit-v1.12.sh",
    "plan13": P2 / "deposit" / "PLAN-v1.13.md",
    "decision_head": P2 / "DECISION-designacao-2026-08-25.md",
}


def git_blob(commit, path):
    return subprocess.run(["git", "-C", str(REPO), "show", f"{commit}:{path}"], check=True,
                          capture_output=True).stdout


def load_src18():
    src = {k: p.read_text(encoding="utf-8") for k, p in SOURCES18.items()}
    src["decision_dep"] = git_blob(DEPOSITED_DECISION_COMMIT, DECISION_PATH).decode("utf-8")
    return src


def _t(s):
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))


# ---------------------------------------------------------------- S18: the facts M-3 and the LOWs rest on
def source_facts_rc18(src):
    fails = []
    rec, files = json.loads(src["zrec"]), json.loads(src["zfiles"])
    if rec.get("metadata", {}).get("version") != "1.12" or rec.get("doi") != "10.5281/zenodo.22110203":
        fails.append("S18: the Zenodo snapshot is not record 22110203, version 1.12")
    created = _t(rec.get("created", "1970-01-01T00:00:00+00:00"))
    if created.strftime("%Y-%m-%dT%H:%M") != "2026-08-26T12:01":
        fails.append(f"S18: v1.12 record created {created.isoformat()}, not 2026-08-26T12:01Z")
    ent = {e["key"]: e for e in files.get("entries", [])}
    dec = ent.get("DECISION-designacao-2026-08-25.md")
    dep_md5 = hashlib.md5(src["decision_dep"].encode("utf-8")).hexdigest()
    head_md5 = hashlib.md5(src["decision_head"].encode("utf-8")).hexdigest()
    if not dec or dec.get("checksum") != f"md5:{dep_md5}":
        fails.append(f"S18: the deposited DECISION md5 is not that of commit {DEPOSITED_DECISION_COMMIT}'s blob")
    if dec and dec.get("checksum") == f"md5:{head_md5}":
        fails.append("S18: the deposited DECISION equals the current file; 'not deposited' needs rereading")
    if "DECISION-designacao-2026-08-25.md" not in src["dep12"].split("NOVOS=(")[1].split(")")[0]:
        fails.append("S18: deposit-v1.12.sh NOVOS does not list DECISION-designacao-2026-08-25.md")
    d = src["decision_dep"]
    for needle, why in (
        ("> **Status:** aberta, aguardando o Toto.", "deposited DECISION is marked open, awaiting the author"),
        ("### B — Sorteio pseudoaleatório com seed declarada", "deposited DECISION carries option B"),
        ("## Recomendação\n\n**B**", "deposited DECISION recommends B"),
        ('SHA256( seed ‖ "|" ‖ sig_primary ‖ "|" ‖ chunk_id )', "deposited option B keys on sig_primary"),
        ("### D — `chunk_id` mais baixo", "deposited DECISION lays out options A–D"),
    ):
        if needle not in d:
            fails.append(f"S18: {why} — not found in the deposited bytes")
    if re.search(r"DECIDID|seed = |e5d134ee", d):
        fails.append("S18: the deposited DECISION carries the decision or the seed")
    ds = src["dseed"]
    for needle, why in (("A substituição foi decidida em **2026-08-26T14:47Z**", "decided 14:47Z"),
                        ("Foi corrigido às 19:40Z", "sig_primary dropped from the key at 19:40Z"),
                        ("**2026-08-26T20:07:27Z** (commit `40d2462`)", "declaration file time 20:07:27Z"),
                        ("**1.053 s", "declaration file gives 1.053 s")):
        if needle not in ds:
            fails.append(f"S18: {why} — not in DESIGNATION-SEED")
    js = json.loads(src["desig"])
    m = re.search(r"(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ)", js.get("declaracao", ""))
    if not m or not js.get("declaracao", "").startswith("DESIGNATION-SEED-2026-08-26.md, commit 40d2462"):
        fails.append("S18: DESIGNATION json does not record the declaration commit time")
    else:
        e = _t(js["emissao_de_R"])
        if (e - _t(m.group(1))).total_seconds() != 1056 or m.group(1) != "2026-08-26T20:07:24Z":
            fails.append("S18: commit time to emission is not 1 056 s from 20:07:24Z")
        if (e - _t("2026-08-26T20:07:27Z")).total_seconds() != 1053:
            fails.append("S18: 20:07:27Z to emission is not 1 053 s")
    if (_t("2026-08-26T14:47:00Z") - created.replace(second=0, microsecond=0)) != dt.timedelta(hours=2, minutes=46):
        fails.append("S18: publication to decision is not 2 h 46 min")
    b = src["band"]
    s1 = b[b.find("## §1. Fechado: a designação"):b.find("## §2.")]
    if "| vigente desde | **20:28Z** |" not in s1:
        fails.append("S18: the band-collapse draft §1 does not give 'vigente desde 20:28Z'")
    pl = src["prereg"].splitlines()
    if ("Measured cost of the age window" not in pl[512] or "30-day window" not in pl[514]
            or "`w = 7.5`" not in pl[518] or "The consequence, computed and registered" not in pl[549]
            or not pl[557].lstrip("> ").startswith("| 90 d |")):
        fails.append("S18: PREREG l.513–519 / l.550–558 are not the reach table and the age table")
    if "`10.5281/zenodo.22110203`, 2026-08-26T14:01Z" not in src["plan13"]:
        fails.append("S18: PLAN-v1.13 no longer carries the mislabelled 14:01Z rc18 declares")
    return fails


# ---------------------------------------------------------------- 1: anchors
ANCHORS = [
    ("ST", "rc18 prepared 2026-10-05\n> (review of rc17 applied:"),
    ("M3", "the deposit\ncarries the per-brief rule retracted as an open defect"),
    ("M3", "but only the horizon is locked in the\nregistration"),
    ("L1", "designation went live at 20:28Z"),
    ("L2", "counted from the commit time of the declaration"),
    ("L3", "was infeasible once the designation was frozen"),
    ("L4", "the reach table at l.513–519 is computed under it"),
    ("M2", "we by a registered horizon of 234 epochs"),
    ("WL", "*(rc18: rc17 had one full read"),
    ("M1", "The title was\nchanged by the author after the review was applied"),
    ("CL", "**rc18: review of rc17 applied**"),
]
REMOVED_ANCHORS = []

# ---------------------------------------------------------------- 2: numbers
JUSTIFIED_REMOVED = {}   # filled from the --report run; each entry: token -> (count, finding, reason)


def derived_rc18(src):
    out = {}
    rec = json.loads(src["zrec"])
    if rec.get("created", "").startswith("2026-08-26T12:01"):
        out["12:01Z"] = "zenodo-22110203-record.json: created 2026-08-26T12:01:06Z"
        out["22110203"] = "zenodo-22110203-record.json: record id"
    if "Foi corrigido às 19:40Z" in src["dseed"]:
        out["19:40Z"] = "DESIGNATION-SEED-2026-08-26.md: 'Foi corrigido às 19:40Z'"
    if "**2026-08-26T20:07:27Z**" in src["dseed"]:
        out["20:07:27Z"] = "DESIGNATION-SEED-2026-08-26.md: T_declare"
    if "20:07:24Z" in json.loads(src["desig"]).get("declaracao", ""):
        out["20:07:24Z"] = "DESIGNATION-2026-08-26.json: declaracao"
    out["1 053"] = "derived: 20:25:00Z − 20:07:27Z (checked in S18)"
    out["1053"] = out["1 053"]
    if "DECISION-designacao-2026-08-25.md" in json.dumps(json.loads(src["zfiles"])):
        out["2026-08-25"] = "the deposited file name DECISION-designacao-2026-08-25.md (Zenodo v1.12 file list)"
    out["46"] = "derived: 14:47Z − 12:01Z = 2 h 46 min (checked in S18)"
    for tok in ("513", "519", "550", "558", "513–519", "550–558"):
        out[tok] = "PREREG-DRAFT.md line numbers (checked in S18)"
    return out


# ---------------------------------------------------------------- 3/4: tail
TAIL_INSERTS = [
    """ *(rc18: rc17 had one full read, Fable NO-GO with three MEDIUM and
    four LOW and no HIGH; all verified, and applied or adapted in rc18 (`APPLY-B-rc18.md`). rc18
    itself has not been reviewed.)*""",
]
TAIL_EDITS = [  # (rc17 text, rc18 text) inside the rc17 changelog block — Fable M-1
    ("""The title is
not changed; `APPLY-B-rc17.md` flags it for the author.""",
     """The title was
changed by the author after the review was applied (`APPLY-B-rc17.md`, author decision of
2026-10-05): "A registration that outlived its intervention" → "A registered horizon that
outlived its intervention", line 1 only, because the intervention that expired was not the
registration's own (item 161); no deposit metadata for this paper exists yet, and the one
written at deposit must carry this title (item 164)."""),
]

# ---------------------------------------------------------------- 6: locks
SWEEP_LOCK_RC18 = [
    (r"sample size ignored a 30-day", "M-2: the registration did not ignore the window (§8.3)"),
    (r"whose sample size ignored", "M-2 (§8.3)"),
    (r"only the horizon is in the registration", "M-3: 'locked in the registration'"),
    (r"published at 14:01Z", "M-3 (verified): v1.12 was published at 12:01Z"),
    (r"(?<!2 h )46 min(?:utes)? after publication", "M-3 (verified): 2 h 46 min, not 46 min"),
    (r"(?<!2 h )46 minutes", "M-3 (verified): 2 h 46 min"),
    (r"designation was completed at 20:28Z", "L1: 'went live at 20:28Z', sourced"),
    (r"1 056 s according to the recorded timestamps", "L2: name the timestamp"),
    (r"infeasible by construction", "L3"),
    (r"A registration that outlived its intervention", "title lock (body)"),
]
PRESENT_RC18 = [
    ("the deposit carries the per-brief rule retracted as an open defect (`AMENDMENT-v1.12.md` §5) and, in "
     "`DECISION-designacao-2026-08-25.md`, a recommendation, marked as awaiting the author's decision, of a seeded "
     "pseudorandom draw of one chunk per signature group (option B); the decision, the seed, the key layout that "
     "was used and the 19 items were not deposited.", "M-3 §1"),
    ("v1.12 was published at 12:01Z (the creation time of Zenodo record 22110203), the replacement rule was "
     "decided at 14:47Z, 2 h 46 min later", "M-3 §1 (times, corrected)"),
    ("the designation went live at 20:28Z (`AMENDMENT-DRAFT-band-collapse-2026-08-26.md` §1)", "L1"),
    ("by 1 056 s, counted from the commit time of the declaration that `DESIGNATION-2026-08-26.json` records "
     "(20:07:24Z); the declaration file itself records 20:07:27Z, which gives 1 053 s.", "L2"),
    ("but only the horizon is locked in the registration: the deposit carries the per-brief rule retracted as an "
     "open defect (`AMENDMENT-v1.12.md` §5) and, in `DECISION-designacao-2026-08-25.md`, a recommendation, marked "
     "as awaiting the author's decision, of a seeded pseudorandom draw of one chunk per signature group (option "
     "B), which was decided 2 h 46 min after publication; the decision, the seed, the key layout that was used "
     "(the deposited option B keys on `sig_primary`, which was dropped from the key at 19:40Z) and the 19 items "
     "were not deposited.", "M-3 §3.0.1"),
    ("This is therefore a mismatch between the registered horizon and the intervention frozen after it, unlike the "
     "H1b collision of §4.4, whose two locks are both registered.", "M-3 §3.0.1 (reviewer's sentence)"),
    ("(PREREG §2: the reach table at l.513–519 is computed under it, and l.550–558 give the minimum dose at chunk "
     "ages up to 90 days)", "L4"),
    ("we by a registered horizon of 234 epochs that was never re-read against the intervention frozen after "
     "registration, whose 19 items left a 30-day eligibility window together after 20 epochs (§3.0.1).", "M-2"),
]
PRESENT_REPLACED = {  # rc17 presence locks that rc18 rewrites -> finding
    "v1.12 was published at 14:01Z, the replacement rule was decided at 14:47Z": "M-3: 14:01Z was UTC+2",
    "this is a mismatch between the registered horizon and the intervention frozen after it":
        "M-3: 'This is therefore a mismatch …' (PRESENT_RC18)",
}
STATUS_MARKS_RC18 = R17.STATUS_MARKS_RC17 + ["rc18 prepared 2026-10-05\n> (review of rc17 applied:"]
STATUS_LOCK = R17.STATUS_LOCK

# ---------------------------------------------------------------- 7: qualifier deltas (from --report)
JUSTIFIED_PHRASE = {
    ("not deposited", +3): ("M3", "'… and the 19 items were not deposited' in §1 and §3.0.1 (the reviewer's clause), "
                                  "and the same words in changelog item 165"),
}
JUSTIFIED_HEDGE = {
    "ST": ({"not": 2}, "status header, rc18 clause: 'not 14:01Z', 'not the decision, the seed …'"),
    "M3+L1": ({"not": 1, "deposited": 1}, "§1 (one hunk with L1's 'went live'): 'were not deposited'; 'the deposit "
                                         "carries' is 'deposit', not 'deposited'"),
    "M3": ({"not": 1, "deposited": 2, "therefore": 1},
           "§3.0.1: 'were not deposited', 'the deposited option B', and the reviewer's 'This is therefore a mismatch'"),
    "M2": ({"never": 1, "registered": 1}, "§8.3 (reviewer's text): 'a registered horizon … never re-read'"),
}


def check(old, new, verbose=True, report=False, cz=None, st=None, A=None, files=None, files15=None,
          src=None, src18=None):
    cz = cz or R13.load_rc13()
    st = st or R13.load_paths()
    A = A or load()
    src = src or {k: p.read_text(encoding="utf-8") for k, p in R17.SOURCES.items()}
    src18 = src18 or load_src18()
    if files is None:
        files = {k: p.read_bytes() for k, p in R15.ART.items()}
        files["res4_frozen"] = R17.RES4_FROZEN.read_bytes()
    files15 = files15 or {"py": R16.FROZEN_TEST_PY.read_bytes(), "json": R16.FROZEN_TEST_JSON.read_bytes()}
    fails, rep = [], []
    if hashlib.sha256(old.encode()).hexdigest() != OLD_SHA:
        fails.append("rc17 is not the 2af62266… bytes rc17's parity passed on (title included)")
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
    der = derived_rc18(src18)
    old_nums = R11.numbers(old)
    added = {k: d for k, d in delta.items() if d > 0}
    src_add = {}
    for k in sorted(added):
        if old_nums[k]:
            src_add[k] = "in rc17"
        elif k in der:
            src_add[k] = "derived: " + der[k]
        elif k in allowed:
            src_add[k] = "artifact: " + allowed[k]
        else:
            fails.append(f"numbers: token {k!r} added {added[k]}x is neither in rc17, nor an artifact leaf, nor derived")
    # 1 hunks
    hs = R11.hunks(old, new)
    for h in hs:
        ids = [aid for aid, anc in ANCHORS if anc in h["new"]]
        ids += [aid for anc, aid in REMOVED_ANCHORS if not h["new"].strip() and anc in h["old"]]
        h["ids"] = list(dict.fromkeys(ids))
        if not h["ids"]:
            fails.append(f"hunk rc17 {h['rc10']} rc18 {h['rc11']} has no ID: {(h['new'] or h['old'])[:80]!r}")
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
        if name in R17.INV_FIXED and d:
            fails.append(f"invariant: {name} changed: {dict(list(d.items())[:4])}")
        rep.append(f"{name}: {sum(a.values())} -> {sum(b.values())}" + ("" if not d else f"  (delta {len(d)} items)"))
        if report and d and name in R17.INV_FREE:
            for k, v in sorted(d.items(), key=lambda kv: str(kv[0]))[:40]:
                rep.append(f"    {v:+d} {str(k)[:150]}")
    if old.count(H301_OLD) != 1 or new.count(H301_NEW) != 1:
        fails.append("invariant: the §3.0.1 heading is not the declared L3 change")
    if R11.headings(old.replace(H301_OLD, H301_NEW, 1)) != R11.headings(new):
        fails.append("invariant: heading list changed (beyond the declared §3.0.1 heading)")
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
            fails.append(f"tail: declared rc17-block edit not found exactly once: {b[:60]!r}")
        t = t.replace(b, a)
    i18 = t.find("\n\n**rc18: review of rc17 applied**")
    blocks18 = t[i18:] if i18 >= 0 else ""
    t = t[:i18] + "\n" if i18 >= 0 else t
    if i18 < 0:
        fails.append("tail: the rc18 changelog block is missing")
    if t != to:
        fails.append("tail: working list / changelog, with the declared insertion and edit reverted and the rc18 "
                     "block removed, is not byte-identical to rc17")
    i = tn.find("\n**rc14: writing pass**")
    nums = [int(x) for x in re.findall(r"^(\d+)\. ", tn[i:] if i >= 0 else "", re.M)]
    if nums != list(range(149, 168)):
        fails.append(f"tail: rc14-rc18 changelog items are {nums}, expected 149..167")
    for n, needle in ((164, "rc17 changelog block (Fable M-1)"), (165, "§1 and §3.0.1 (Fable M-3)"),
                      (166, "§8.3 (Fable M-2)"), (167, "§1 (Fable L1, L2)")):
        if not re.search(rf"^{n}\. {re.escape(needle)}", blocks18, re.M):
            fails.append(f"tail: changelog item {n} missing")
    if "not 14:01Z" not in flat(blocks18) or "2 h 46 min after publication, not 46 min" not in flat(blocks18):
        fails.append("tail: the rc18 block does not record the 12:01Z correction and the 46-min rejection")
    # 5 SHAM
    so, eo = R11.sham_spans(old)
    sn, en = R11.sham_spans(new)
    fails += eo + en
    if len(sn) != R11.EXPECTED_SHAM or len(so) != R11.EXPECTED_SHAM:
        fails.append(f"sham: {len(sn)} blocks in rc18 and {len(so)} in rc17, expected {R11.EXPECTED_SHAM}")
    for k, (x, y) in enumerate(zip(so, sn), 1):
        if x != y:
            fails.append(f"sham: block {k} ({y.strip()[:50]!r}…) is not byte-identical to rc17")
    # 6 carried locks + rc18
    fails += R13.claims_rc13(new, cz)
    nb_unstruck = R11.strip_struck(nb)
    fn_unstruck = flat(nb_unstruck)
    for pat, why in R15.SWEEP_LOCK + R16.SWEEP_LOCK_RC16 + R17.SWEEP_LOCK_RC17 + SWEEP_LOCK_RC18:
        for mo in re.finditer(pat, fn_unstruck):
            fails.append(f"sweep: {why}: {fn_unstruck[max(0, mo.start() - 60):mo.end() + 30]!r}")
    head = new[:new.find("\n---")]
    for mk in STATUS_MARKS_RC18:
        if mk not in head:
            fails.append(f"status: header does not record {mk.splitlines()[0]!r}")
    for pat, why in STATUS_LOCK:
        if re.search(pat, flat(head.replace("> ", " "))):
            fails.append(f"status: {why}")
    carried = [p for p in R15.PRESENT if p[0] not in R16.PRESENT_REPLACED] + R16.PRESENT_RC16
    carried = [p for p in carried if p[0] not in R17.PRESENT_REPLACED] + R17.PRESENT_RC17
    for txt, why in [p for p in carried if p[0] not in PRESENT_REPLACED] + PRESENT_RC18:
        if flat(txt) not in fn_unstruck:
            fails.append(f"present: {why} sentence missing: {txt[:70]!r}")
    for txt in PRESENT_REPLACED:
        if flat(txt) in fn_unstruck:
            fails.append(f"present: replaced rc17 text still present: {txt[:70]!r}")
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
                fails.append(f"qualifier: {ph[:70]!r} occurs {b}x in rc18 against {a}x in rc17, not justified")
    for (ph, d) in JUSTIFIED_PHRASE:
        if pdeltas.get(ph) != d:
            fails.append(f"qualifier: JUSTIFIED_PHRASE lists {ph[:50]!r} {d:+d}; measured {pdeltas.get(ph, 0):+d}")
    gone = {ph for (ph, d) in list(JUSTIFIED_PHRASE) + list(R17.JUSTIFIED_PHRASE) + list(R16.JUSTIFIED_PHRASE)
            + list(R15.JUSTIFIED_PHRASE) if d < 0 and fnn.count(ph) == 0}
    for k, v in h15.items():
        if flat(v) not in fnn and flat(v) not in gone:
            fails.append(f"headline: {k} — {v[:80]!r} not found in rc18")
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
    rep.append(f"locked phrases: {len(locked)} (rc17's); justified deltas: {pdeltas}; hedge deltas: {hd}")
    if report:
        for k, v in sorted(per.items()):
            rep.append(f"  hedge [{k}]: {v}")
    # 8 integrity: rc17's carried checks, then S18
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
    fails += source_facts_rc18(src18)
    # 9 REANALISE, bold
    if R11.R_ANY.search(new):
        fails.append("reanalise: a REANALISE marker is present in rc18")
    noncode = re.sub(r"```.*?```", "", new, flags=re.S)
    for k, para in enumerate(re.split(r"\n\s*\n", noncode)):
        if para.count("**") % 2:
            fails.append(f"bold: odd number of ** in paragraph {k}: {para.strip()[:60]!r}")
    if verbose:
        print(f"hunks: {len(hs)}, all with an ID: {all(h['ids'] for h in hs)} "
              f"({sorted({i for h in hs for i in h['ids']})})")
        for r in rep:
            print(r)
        print(f"headings: {len(R11.headings(new))}, unchanged but the declared §3.0.1: "
              f"{R11.headings(old.replace(H301_OLD, H301_NEW, 1)) == R11.headings(new)}")
        print(f"SHAM-JANELA blocks: {len(sn)}, byte-identical to rc17: {sum(1 for x, y in zip(so, sn) if x == y)}")
        print(f"words: rc17 {len(old.split())} (body {len(body(old).split())}), "
              f"rc18 {len(new.split())} (body {len(body(new).split())})")
        for w in warns:
            print(w)
    if report:
        print("\nnumeric tokens added (and their source):")
        for k in sorted(added):
            print(f"  +{added[k]} {k}: {src_add.get(k, 'UNSOURCED')}")
        print("numeric tokens removed:", removed)
        print("phrase deltas:", pdeltas)
        for h in hs:
            print(f"\n[{'+'.join(h['ids']) or '?'}] rc17 l.{h['rc10'][0]}-{h['rc10'][1]} -> rc18 l.{h['rc11'][0]}-{h['rc11'][1]}")
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
    src18 = load_src18()
    rep1 = lambda a, b: (new.replace(a, b, 1), a in new)  # noqa: E731
    mutations = [
        ("M-3: §1 deposit clause dropped", rep1(
            "an amendment: the deposit\ncarries the per-brief rule retracted as an open defect (`AMENDMENT-v1.12.md` §5) and, in\n"
            "`DECISION-designacao-2026-08-25.md`, a recommendation, marked as awaiting the author's\n"
            "decision, of a seeded pseudorandom draw of one chunk per signature group (option B); the\n"
            "decision, the seed, the key layout that was used and the 19 items were not deposited. v1.12\n"
            "was published", "an amendment: v1.12\nwas published")),
        ("M-3: 14:01Z restored", rep1("was published at 12:01Z (the creation time of Zenodo record 22110203)",
                                      "was published at 14:01Z (the creation time of Zenodo record 22110203)")),
        ("M-3: reviewer's '46 minutes' inserted", rep1("which was decided 2 h 46 min after publication",
                                                       "which was decided 46 minutes after publication")),
        ("M-3: §3.0.1 'only the horizon is in the registration' restored", rep1(
            "but only the horizon is locked in the\nregistration:", "but only the horizon is in the\nregistration:")),
        ("M-3: §3.0.1 sig_primary parenthetical dropped", rep1(
            " (the deposited option B keys on `sig_primary`, which\nwas dropped from the key at 19:40Z)", "")),
        ("M-3: §3.0.1 reviewer's closing sentence reverted", rep1(
            "This is therefore a\nmismatch between the registered horizon",
            "this is a\nmismatch between the registered horizon")),
        ("M-2: §8.3 'ignored a 30-day window' restored", rep1(
            "we by a registered horizon of 234 epochs that was never re-read\nagainst the intervention frozen after "
            "registration, whose 19 items left a 30-day\neligibility window together after 20 epochs (§3.0.1).",
            "we by a registration whose sample size ignored a 30-day\neligibility window (§3.0.1).")),
        ("L1: 'completed at 20:28Z' restored", rep1(
            "designation went live at 20:28Z (`AMENDMENT-DRAFT-band-collapse-2026-08-26.md` §1)",
            "designation was completed at 20:28Z")),
        ("L2: unnamed timestamp restored", rep1(
            "by 1 056 s, counted from the commit time of the declaration that `DESIGNATION-2026-08-26.json`\n"
            "records (20:07:24Z); the declaration file itself records 20:07:27Z, which gives 1 053 s.",
            "by 1 056 s according to the recorded timestamps.")),
        ("L3: heading 'by construction' restored", rep1(H301_NEW, H301_OLD)),
        ("L4: PREREG line citation dropped", rep1(
            "(PREREG §2: the reach table at l.513–519 is computed under it, and l.550–558 give the\n"
            "minimum dose at chunk ages up to 90 days)", "(PREREG §2)")),
        ("M-1: rc17 block 'title is not changed' restored", rep1(TAIL_EDITS[0][1], TAIL_EDITS[0][0])),
        ("M-1: changelog item 164 removed", rep1("\n164. rc17 changelog block (Fable M-1)", "\nrc17 changelog block (Fable M-1)")),
        ("title lock: old title on line 1", rep1(TITLE, TITLE.replace("A registered horizon that", "A registration that"))),
        ("title lock: old title in body", rep1("## 1. What was registered, and what this paper reports",
                                               "## 1. What was registered, and what this paper reports\n\n"
                                               "A registration that outlived its intervention.")),
        ("status header without rc18", rep1("rc18 prepared 2026-10-05\n> (review of rc17 applied:",
                                            "rc18 drafted 2026-10-05\n> (review of rc17 applied:")),
        ("working list rc18 note dropped", rep1(TAIL_INSERTS[0], "")),
        ("rc18 block: 12:01Z correction dropped", rep1("not 14:01Z; `deposit/PLAN-v1.13.md`", "; `deposit/PLAN-v1.13.md`")),
        ("old changelog line edited", rep1("**rc17: review of rc16 applied**", "**rc17: review of rc16 applied (edited)**")),
        ("SHAM-JANELA block changed", rep1("**Our error, stated.**", "**Our error.**")),
        ("carried rc17: 'same shape … larger object' restored", rep1(
            "unlike the\nH1b collision of §4.4, whose two locks are both registered.",
            "the same shape as the H1b collision of\n§4.4, on a larger object.")),
        ("carried rc17: 'every earlier version' restored", rep1("a rejection in versions up to rc9, and returns",
                                                                "a rejection in every earlier version, and returns")),
        ("carried rc16: 'heavy in the tail' restored", rep1(
            "its contribution to estimator variance has not been quantified.",
            "which is unbiased in expectation and heavy in the tail.")),
        ("carried rc13: abstract back to two commitments", rep1("Three commitments made before the seed",
                                                               "Two commitments made before the seed")),
        ("italic quotation removed", rep1("reading\n*\"what does not move, and could not\"* (PREREG", "reading\nthe phrase (PREREG")),
        ("citation removed", rep1(" [@kaplan2015nullnhlbi]", "")),
        ("unsourced number added", rep1("decided at 14:47Z, 2 h 46 min later", "decided at 14:47Z, 2 h 49 min later")),
        ("unmapped hunk with no anchor", rep1("**Benchmarks compare systems on fixed tasks.**",
                                               "Benchmarks are compared.\n\n**Benchmarks compare systems on fixed tasks.**")),
    ]
    ok = True
    for name, (mutated, applied) in mutations:
        assert applied and mutated != new, f"mutation did not apply: {name}"
        f = [x for x in check(old, mutated, verbose=False, cz=cz, st=st, A=A, files=files, files15=files15,
                              src=src, src18=src18)
             if name.startswith("unmapped") or "has no ID" not in x]
        print(f"mutation [{name}]: {'CAUGHT' if f else 'MISSED'}" + (f" -> {f[0][:140]}" if f else ""))
        ok &= bool(f)
    zr = json.loads(src18["zrec"])
    zf = json.loads(src18["zfiles"])
    zr_late = json.dumps(dict(zr, created="2026-08-26T14:01:06.500672+00:00"))
    zf_other = json.loads(json.dumps(zf))
    for e in zf_other["entries"]:
        if e["key"].startswith("DECISION"):
            e["checksum"] = "md5:" + hashlib.md5(src18["decision_head"].encode()).hexdigest()
    def dep_mut(old_, new_):  # mutate the deposited bytes AND the listed md5, so the content needle must bite
        d_ = src18["decision_dep"].replace(old_, new_)
        zf_ = json.loads(json.dumps(zf))
        for e_ in zf_["entries"]:
            if e_["key"].startswith("DECISION"):
                e_["checksum"] = "md5:" + hashlib.md5(d_.encode()).hexdigest()
        return dict(src18=dict(src18, decision_dep=d_, zfiles=json.dumps(zf_)))
    integ = [
        ("S18: Zenodo record created at 14:01Z", dict(src18=dict(src18, zrec=zr_late))),
        ("S18: deposited DECISION md5 = current file", dict(src18=dict(src18, zfiles=json.dumps(zf_other)))),
        ("S18: deposited bytes carry the decision (md5 kept consistent)", dep_mut(
            "> **Status:** aberta, aguardando o Toto.", "> **Status:** DECIDIDO, opção B.")),
        ("S18: deposited option B without sig_primary (md5 kept consistent)", dep_mut(
            'SHA256( seed ‖ "|" ‖ sig_primary ‖ "|" ‖ chunk_id )', 'SHA256( seed ‖ "|" ‖ chunk_id )')),
        ("S18: deposited bytes without option D (md5 kept consistent)", dep_mut(
            "### D — `chunk_id` mais baixo", "### D")),
        ("S18: 19:40Z correction absent from the seed file", dict(src18=dict(src18, dseed=src18["dseed"].replace(
            "Foi corrigido às 19:40Z", "Foi corrigido")))),
        ("S18: band draft no longer 'vigente desde 20:28Z'", dict(src18=dict(src18, band=src18["band"].replace(
            "| vigente desde | **20:28Z** |", "| vigente desde | **20:29Z** |")))),
        ("S18: PREREG line shift", dict(src18=dict(src18, prereg="\n" + src18["prereg"]))),
        ("S18: DESIGNATION json commit time moved", dict(src18=dict(src18, desig=src18["desig"].replace(
            "pushado 2026-08-26T20:07:24Z", "pushado 2026-08-26T20:07:21Z")))),
        ("carried rc17 S: amendment wording", dict(src=dict(src, amend=src["amend"].replace(
            "**é recomputada a cada brief**", "**é fixa**")))),
        ("carried rc17: RESULTADO-v4 note missing", dict(files=dict(files, res4=files["res4_frozen"]))),
    ]
    for name, kw in integ:
        args = dict(cz=cz, st=st, A=A, files=files, files15=files15, src=src, src18=src18)
        args.update(kw)
        f = check(old, new, verbose=False, **args)
        print(f"mutation [{name}] (integrity): {'CAUGHT' if f else 'MISSED'}" + (f" -> {f[0][:140]}" if f else ""))
        ok &= bool(f)
    base = check(old, new, verbose=False, cz=cz, st=st, A=A, files=files, files15=files15, src=src, src18=src18)
    print(f"unmutated rc18: {'PASS' if not base else 'FAIL'}" + (f" -> {base}" if base else ""))
    print(f"mutations: {len(mutations) + len(integ)}")
    return 0 if ok and not base else 1


if __name__ == "__main__":
    sys.exit(main())
