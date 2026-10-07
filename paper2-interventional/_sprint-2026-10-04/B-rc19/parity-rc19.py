#!/usr/bin/env python3
"""Parity check B-v2-rc18.md -> B-v2-rc19.md (Paper B, sprint 2026-10-04; rc19 2026-10-05).

rc19 applies the Fable read of rc18 (GO, six LOW), each finding verified against its primary
source first (`APPLY-B-rc19.md`). No number of the analysis moves and no artifact of the analysis
changes.

  L1  §1 and §3.0.1: "the per-brief rule retracted as an open defect" -> "declared an open defect"
      (AMENDMENT-v1.12.md §5 declares the designation not validly frozen; §5.1 retracts the
      threshold model behind CUT_FRESH, not the per-brief rule).
  L2  §1: the deposited DECISION bytes named (md5 35abeb68…, 7 036 bytes, blob of d42f950; the repo
      file extended after publication). B.1 row (12:01Z / md5 / 19:40Z / 2 h 46 min) and an
      Appendix B row for the B-rc18/ snapshot, declared as not in the ballast manifest.
  L3  §3.0.1: "both numbers" named (the horizon and the 20-epoch life of the fixed set).
  L4  §1: "fixed and deposited two weeks before the round" -> fixed 2026-08-17 (last commit
      3199ec1), deposited in Zenodo v1.11 (record 21978476, 2026-08-17T18:32Z, the day before the
      OSF registration), same bytes in v1.12 (md5 3fa3f710…), thirteen days before round 31774052
      was emitted; "deposited with v1.12" -> "with v1.11 and v1.12". Snapshot of v1.11 in B-rc19/
      (public GET), B.1 and Appendix B rows.
  L5  rc18 changelog item 165: AMENDMENT-DRAFT-band-collapse l.5 named beside PLAN-v1.13 (both
      carry 14:01Z as UTC+2 labelled Z; neither edited).
  L6  working list 8, 17, 24: rc15-rc18 artifacts and both Zenodo snapshots not in the ballast
      manifest; item 17 blocks the deposit.

Checks (exit 1 if any fails):
  1. hunks: every hunk rc18 -> rc19 carries an ID from ANCHORS.
  2. numbers: every numeric token REMOVED from the body is in JUSTIFIED_REMOVED with its exact
     count; every token ADDED is in rc18, an artifact leaf, or derived (derived_rc19).
  3. invariants rc18 -> rc19: italic quotations, citations, footnotes, DOIs, image links, struck
     spans unchanged; headings identical (incl. rc18's §3.0.1 heading); title lock.
  4. working list and changelog: rc19's, with the declared insertions, the declared rc18-block
     edit reverted and the rc19 block removed, is byte-identical to rc18's; items 149-173.
  5. SHAM-JANELA: 10 blocks byte-identical to rc18.
  6. carried locks: rc18's (with everything it carries), with declared replacements; NEW sweep
     (SWEEP_LOCK_RC19) and presence locks (PRESENT_RC19).
  7. qualifier set and hedge words, per hunk-ID group, summed to the body delta.
  8. integrity: rc18's carried checks (incl. S and S18); NEW source block S19.
  9. no REANALISE marker; bold balanced per paragraph.

Usage:  python3 parity-rc19.py | --report | --self-test     Reads; writes nothing.
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
OLD = SPRINT / "B-v2-rc18.md"
NEW = SPRINT / "B-v2-rc19.md"
RC18 = SPRINT / "B-rc18" / "parity-rc18.py"
RC18_SHA = "dee8a51a074405673243979ccf4dff1af4d222cd4b327862ff1ee1ec194c8348"
OLD_SHA = "b07f19c2aedcfff26f9f5a3761ab79a9dec4a5bbe92c41c9674cf683de38f166"

assert hashlib.sha256(RC18.read_bytes()).hexdigest() == RC18_SHA, \
    "parity-rc18.py changed: the locks carried from it are no longer the ones rc18 ran"
_spec = importlib.util.spec_from_file_location("parity_rc18", RC18)
R18 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(R18)
R17 = R18.R17
R16, R15, R14, R13, R12, R11 = R17.R16, R17.R15, R17.R14, R17.R13, R17.R12, R17.R11
flat, body, tail, sha, sci, load = R17.flat, R17.body, R17.tail, R17.sha, R17.sci, R17.load
TITLE, TITLE_OLD, H301 = R18.TITLE, R18.TITLE_OLD, R18.H301_NEW

ASSIGN_PATH = "paper2-interventional/assign_arms.py"
ASSIGN_LAST = "3199ec1"
MANIFEST = Path.home() / "Backups" / "paper2-ensaio-2026-09-21" / "MANIFESTO-LASTRO-P2.json"
SOURCES19 = {
    "zrec11": HERE / "zenodo-21978476-record.json",
    "zfiles11": HERE / "zenodo-21978476-files.json",
    "zfiles12": SPRINT / "B-rc18" / "zenodo-22110203-files.json",
    "zrec12": SPRINT / "B-rc18" / "zenodo-22110203-record.json",
    "amend": P2 / "AMENDMENT-v1.12.md",
    "band": P2 / "AMENDMENT-DRAFT-band-collapse-2026-08-26.md",
    "dseed": P2 / "DESIGNATION-SEED-2026-08-26.md",
    "aseed": P2 / "ASSIGN-SEED-2026-08-30.md",
    "prereg": P2 / "PREREG-DRAFT.md",
    "plan13": P2 / "deposit" / "PLAN-v1.13.md",
}


def git(*args):
    return subprocess.run(["git", "-C", str(REPO), *args], check=True, capture_output=True).stdout


def load_src19():
    src = {k: p.read_text(encoding="utf-8") for k, p in SOURCES19.items()}
    src["assign_blob"] = git("show", f"{ASSIGN_LAST}:{ASSIGN_PATH}")
    src["assign_log"] = git("log", "--format=%h %cI", "--", ASSIGN_PATH).decode()
    src["decision_dep"] = git("show", f"{R18.DEPOSITED_DECISION_COMMIT}:{R18.DECISION_PATH}")
    src["decision_log"] = git("log", "--format=%h %cI", "--", R18.DECISION_PATH).decode()
    src["decision_head"] = (P2 / "DECISION-designacao-2026-08-25.md").read_bytes()
    src["manifest"] = MANIFEST.read_text(encoding="utf-8") if MANIFEST.exists() else None
    return src


def _t(s):
    return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))


def _entry(files_json, key):
    return {e["key"]: e for e in json.loads(files_json).get("entries", [])}.get(key)


# ---------------------------------------------------------------- S19: the facts the six LOWs rest on
def source_facts_rc19(src):
    fails, warns = [], []
    # L1: what AMENDMENT-v1.12 §5 declares and what §5.1 retracts
    am = src["amend"]
    s5 = am[am.find("## §5. "):am.find("## §6. ")]
    if not s5.startswith("## §5. Defeito aberto: a designação não está validamente congelada"):
        fails.append("S19/L1: AMENDMENT-v1.12 §5 is not 'Defeito aberto: … não está validamente congelada'")
    if "Retratado o modelo de limiar (§1.1)" not in s5 or "### 5.1 A regra consome uma constante cujo referente esta emenda retrata" not in s5:
        fails.append("S19/L1: AMENDMENT-v1.12 §5.1 no longer retracts the threshold model (not the rule)")
    if re.search(r"(?i)retrat\w* a regra|regra\s+\w*\s*retratad", s5):
        fails.append("S19/L1: AMENDMENT-v1.12 §5 now retracts the rule itself; 'declared an open defect' needs rereading")
    # L2: the deposited DECISION bytes, their size, and the later extension
    dec = _entry(src["zfiles12"], "DECISION-designacao-2026-08-25.md")
    d = src["decision_dep"]
    if not dec or dec.get("checksum") != "md5:" + hashlib.md5(d).hexdigest() or dec.get("size") != len(d) or len(d) != 7036:
        fails.append("S19/L2: the deposited DECISION is not md5 35abeb68…, 7 036 bytes, the blob of d42f950")
    if not dec or not dec["checksum"].startswith("md5:35abeb68") or len(d) != 7036:
        fails.append("S19/L2: the md5 prefix or the size cited in §1 no longer matches")
    pub = _t(json.loads(src["zrec12"])["created"])
    later = [(h, _t(t)) for h, t in (ln.split() for ln in src["decision_log"].splitlines())
             if h != R18.DEPOSITED_DECISION_COMMIT]
    if not later or min(t for _, t in later) <= pub or len(src["decision_head"]) <= len(d) \
            or "DECIDID" not in src["decision_head"].decode("utf-8"):
        fails.append("S19/L2: the repository DECISION was not extended after publication to record the decision")
    ds = src["dseed"].splitlines()
    if "2026-08-26T14:47Z" not in ds[30] or "14:47Z" not in ds[95] or "19:40Z" not in ds[96]:
        fails.append("S19/L2: DESIGNATION-SEED l.31 (14:47Z) / l.96–97 (19:40Z) are not the cited lines")
    # L4: assign_arms.py, the v1.11 deposit, the OSF registration and the round
    log = [ln.split() for ln in src["assign_log"].splitlines()]
    if not log or log[0][0] != ASSIGN_LAST or _t(log[0][1]).astimezone(dt.timezone.utc).date() != dt.date(2026, 8, 17):
        fails.append("S19/L4: assign_arms.py's last commit is not 3199ec1 of 2026-08-17")
    r11 = json.loads(src["zrec11"])
    if r11.get("doi") != "10.5281/zenodo.21978476" or r11.get("metadata", {}).get("version") != "1.11":
        fails.append("S19/L4: the v1.11 snapshot is not record 21978476, version 1.11")
    c11 = _t(r11.get("created", "1970-01-01T00:00:00Z"))
    if c11.strftime("%Y-%m-%dT%H:%MZ") != "2026-08-17T18:32Z":
        fails.append(f"S19/L4: v1.11 created {c11.isoformat()}, not 2026-08-17T18:32Z")
    md5_blob = "md5:" + hashlib.md5(src["assign_blob"]).hexdigest()
    a11, a12 = _entry(src["zfiles11"], "assign_arms.py"), _entry(src["zfiles12"], "assign_arms.py")
    if not a11 or not a12 or a11["checksum"] != md5_blob or a12["checksum"] != md5_blob \
            or not md5_blob.startswith("md5:3fa3f710"):
        fails.append("S19/L4: assign_arms.py in v1.11 and v1.12 is not md5 3fa3f710…, the blob of 3199ec1")
    m = re.search(r"REGISTERED — OSF `yf7d2`, (\S+Z)", src["prereg"].splitlines()[2])
    if not m or (_t(m.group(1)).date() - c11.date()).days != 1 or _t(m.group(1)) <= c11:
        fails.append("S19/L4: v1.11 was not published the day before the OSF registration")
    if "A rodada emitiu em **2026-08-30T21:32:04Z**" not in src["aseed"]:
        fails.append("S19/L4: ASSIGN-SEED no longer gives the emission 2026-08-30T21:32:04Z")
    if (_t("2026-08-30T21:32:04Z") - c11).days != 13:
        fails.append("S19/L4: v1.11 publication to the round's emission is not thirteen days")
    # L5: both notes carry the mislabelled 14:01Z
    if "(`10.5281/zenodo.22110203`, 2026-08-26T14:01Z)" not in src["band"].splitlines()[4]:
        fails.append("S19/L5: AMENDMENT-DRAFT-band-collapse l.5 no longer carries 14:01Z")
    if "2026-08-26T14:01Z" not in src["plan13"].splitlines()[12]:
        fails.append("S19/L5: PLAN-v1.13 l.13 no longer carries 14:01Z")
    # L6: the manifest has none of the rc15-rc18 artifacts nor the snapshots
    if src["manifest"] is None:
        warns.append("S19/L6: ballast manifest not found on this machine; 'not in the manifest' not re-verified")
    else:
        mj = json.loads(src["manifest"])
        if mj.get("n_artefatos") != 50 or re.search(r"B-rc1[5-9]/|zenodo-22110203|zenodo-21978476", src["manifest"]):
            fails.append("S19/L6: the ballast manifest changed (count or rc15–rc19 paths); working list 17 needs rereading")
    return fails, warns


# ---------------------------------------------------------------- 1: anchors
ANCHORS = [
    ("ST", "rc19 prepared 2026-10-05 (review of rc18 applied:"),
    ("L1", "carries the per-brief rule declared an open defect (`AMENDMENT-v1.12.md` §5) and, in"),
    ("L1", "per-brief rule declared an open defect (`AMENDMENT-v1.12.md` §5)"),
    ("L2", "deposited bytes, md5 `35abeb68…`, 7 036 bytes"),
    ("L2", "| v1.12 published 12:01Z; md5 `35abeb68…`"),
    ("L2", "| `_sprint-2026-10-04/B-rc18/zenodo-22110203-record.json`"),
    ("L3", "Both numbers, the\nhorizon and the 20-epoch life of the fixed set"),
    ("L4", "deposited with v1.11 and\nv1.12"),
    ("L4", "deposited in Zenodo v1.11 (record 21978476"),
    ("L4", "| `assign_arms.py` last changed 2026-08-17;"),
    ("L4", "| `_sprint-2026-10-04/B-rc19/zenodo-21978476-record.json`"),
    ("L6", "the Zenodo snapshots of rc18 and rc19 in `B-rc18/` and `B-rc19/`"),
    ("WL", "*(rc19: 17 is still open"),
    ("WL", "*(rc19)* None of the"),
    ("WL", "*(rc19: rc18 had one full read"),
    ("L5", "`AMENDMENT-DRAFT-band-collapse-2026-08-26.md` (l.5) give the time"),
    ("CL", "**rc19: review of rc18 applied**"),
]
REMOVED_ANCHORS = []

# ---------------------------------------------------------------- 2: numbers
JUSTIFIED_REMOVED = {}   # token -> (count, finding, reason)


def derived_rc19(src):
    out = {}
    r11 = json.loads(src["zrec11"])
    if r11.get("created", "").startswith("2026-08-17T18:32"):
        out["21978476"] = "zenodo-21978476-record.json: record id"
        out["18:32Z"] = "zenodo-21978476-record.json: created 2026-08-17T18:32:45Z"
        out["18:32:45Z"] = out["18:32Z"]
        out["2026-08-17T18:32Z"] = out["18:32Z"]
        out["2026-08-17T18:32:45Z"] = out["18:32Z"]
    if json.loads(src["zrec12"]).get("created", "").startswith("2026-08-26T12:01:06"):
        out["12:01:06Z"] = "zenodo-22110203-record.json: created 2026-08-26T12:01:06Z"
        out["2026-08-26T12:01:06Z"] = out["12:01:06Z"]
    dec = _entry(src["zfiles12"], "DECISION-designacao-2026-08-25.md")
    if dec and dec.get("size") == 7036:
        out["7 036"] = "zenodo-22110203-files.json: DECISION size"
        out["7036"] = out["7 036"]
    out["3199"] = "commit 3199ec1 (the token the tokenizer cuts from the hash)"
    out["d42"] = "commit d42f950"
    out["35"] = "md5 prefix 35abeb68…"
    out["3"] = "md5 prefix 3fa3f710…"
    for tok in ("31", "96", "97", "96–97", "13", "5", "l.5", "l.13"):
        out[tok] = "line numbers of DESIGNATION-SEED / band draft / PLAN-v1.13 (checked in S19)"
    out["2026-08-30T21:32:04Z"] = "ASSIGN-SEED-2026-08-30.md l.130"
    for tok in ("168", "169", "170", "171", "172", "173"):
        out[tok] = "rc19 changelog item numbers"
    return out


# ---------------------------------------------------------------- 3/4: tail
TAIL_INSERTS = [
    """
   *(rc19: 17 is still open and still blocks this deposit; it now also covers the rc15–rc18
   artifacts and the Zenodo snapshots in `B-rc18/` and `B-rc19/`.)*""",
    """ *(rc19)* None of the
    rc15–rc18 artifacts listed here is in the manifest yet (checked 2026-10-05: no `B-rc15/`
    to `B-rc18/` path among the 50 artifacts of `MANIFESTO-LASTRO-P2.json`), and neither are
    the Zenodo snapshots `B-rc18/zenodo-22110203-{record,files}.json` and
    `B-rc19/zenodo-21978476-{record,files}.json`, which §1, §3.0.1 and B.1 now cite; until
    they are, this item blocks the deposit (item 8).""",
    """ *(rc19: rc18 had one full read, Fable GO with six LOW; all
    verified and applied in rc19 (`APPLY-B-rc19.md`). rc19 itself has not been reviewed.)*""",
]
TAIL_EDITS = [  # (rc18 text, rc19 text) inside the rc18 changelog block — Fable L5
    ("""`deposit/PLAN-v1.13.md`
    gives the time in UTC+2 labelled Z, and is not edited.""",
     """`deposit/PLAN-v1.13.md`
    (l.13) and `AMENDMENT-DRAFT-band-collapse-2026-08-26.md` (l.5) give the time in UTC+2
    labelled Z, and neither is edited."""),
]

# ---------------------------------------------------------------- 6: locks
SWEEP_LOCK_RC19 = [
    (r"retracted as an open defect", "L1: AMENDMENT-v1.12 §5 declares the rule an open defect"),
    (r"two weeks before the round", "L4: thirteen days, from the v1.11 deposit of 2026-08-17"),
    (r"(?i)\btwo weeks\b", "L4: no 'two weeks' left in the body"),
    (r"deposited with v1\.12\)", "L4: deposited with v1.11 and v1.12"),
    (r"Both numbers are ours", "L3: name the two numbers"),
    (r"twelve days before the round", "L4: the proposed 'twelve days' (from OSF) was not used"),
]
PRESENT_RC19 = [
    ("the deposit carries the per-brief rule declared an open defect (`AMENDMENT-v1.12.md` §5) and, in "
     "`DECISION-designacao-2026-08-25.md`, a recommendation, marked as awaiting the author's decision, of a seeded "
     "pseudorandom draw of one chunk per signature group (option B) (the deposited bytes, md5 `35abeb68…`, 7 036 "
     "bytes, the blob of commit `d42f950`; the repository file was extended after publication to record the "
     "decision); the decision, the seed, the key layout that was used and the 19 items were not deposited.",
     "L1+L2 §1"),
    ("Both numbers, the horizon and the 20-epoch life of the fixed set, are ours, both were locked, and they are "
     "incompatible, but only the horizon is locked in the registration: the deposit carries the per-brief rule "
     "declared an open defect (`AMENDMENT-v1.12.md` §5) and, in `DECISION-designacao-2026-08-25.md`, a "
     "recommendation, marked as awaiting the author's decision, of a seeded pseudorandom draw of one chunk per "
     "signature group (option B), which was decided 2 h 46 min after publication;", "L1+L3 §3.0.1"),
    ("(stratified block randomization, committed 2026-08-16, last changed 2026-08-17, deposited with v1.11 and "
     "v1.12)", "L4 §1 parenthetical"),
    ("so the only protection is that the rule it adopted was fixed on 2026-08-17 (its last commit) and deposited "
     "in Zenodo v1.11 (record 21978476, published 2026-08-17T18:32Z, the day before the OSF registration; v1.12 "
     "carries the same bytes, md5 `3fa3f710…`), thirteen days before the round was emitted, which the deposit, "
     "not our log, dates.", "L4 §1"),
    ("| v1.12 published 12:01Z; md5 `35abeb68…` and 7 036 bytes of the deposited "
     "`DECISION-designacao-2026-08-25.md`, the blob of commit `d42f950`; `sig_primary` dropped from the key at "
     "19:40Z; decision 2 h 46 min after publication | 1, 3.0.1 | "
     "`_sprint-2026-10-04/B-rc18/zenodo-22110203-record.json` (`created`) and "
     "`_sprint-2026-10-04/B-rc18/zenodo-22110203-files.json` (the file's `checksum` and `size`); "
     "`DESIGNATION-SEED-2026-08-26.md` l.31 (14:47Z) and l.96–97 (19:40Z) (added in rc19) |", "L2 B.1 row"),
    ("| `assign_arms.py` last changed 2026-08-17; Zenodo v1.11 (record 21978476) published 2026-08-17T18:32Z with "
     "that file at md5 `3fa3f710…`, the bytes v1.12 carries; thirteen days before round 31774052 was emitted | 1 |",
     "L4 B.1 row"),
    ("(added in rc19; not in the ballast manifest, working list 17) |\n| "
     "`_sprint-2026-10-04/B-rc19/zenodo-21978476-record.json`", "L2/L4 Appendix B rows, declared unmanifested"),
    ("the rc15 Figure B1, and the Zenodo snapshots of rc18 and rc19 in `B-rc18/` and `B-rc19/`) are **not yet in "
     "the ballast manifest** (working list 17)", "L6 Appendix B paragraph"),
]
PRESENT_REPLACED = {  # rc18 presence locks that rc19 rewrites -> finding
    R18.PRESENT_RC18[0][0]: "L1+L2: 'declared an open defect' and the deposited-bytes parenthetical",
    R18.PRESENT_RC18[4][0]: "L1+L3: 'declared an open defect', both numbers named",
}
STATUS_MARKS_RC19 = R18.STATUS_MARKS_RC18 + ["rc19 prepared 2026-10-05 (review of rc18 applied:"]
STATUS_LOCK = R18.STATUS_LOCK

# ---------------------------------------------------------------- 7: qualifier deltas (from --report)
JUSTIFIED_PHRASE = {}   # no locked qualifier phrase moves (measured: {})
JUSTIFIED_HEDGE = {
    "ST": ({"registered": 1, "deposited": 1}, "status header, rc19 clause: 'the registered assignment rule was "
                                              "deposited on 2026-08-17'"),
    "L2": ({"deposited": 1}, "§1 (Fable L2's text): '(the deposited bytes, md5 `35abeb68…`, …)'"),
    "L2+L4": ({"not": 2, "deposited": 2, "every": 1},
              "B.1 row 'of the deposited `DECISION-…`'; Appendix B rows 'every deposited file' and, twice, "
              "'not in the ballast manifest' (Fable L2, L6)"),
}


def check(old, new, verbose=True, report=False, cz=None, st=None, A=None, files=None, files15=None,
          src=None, src18=None, src19=None):
    cz = cz or R13.load_rc13()
    st = st or R13.load_paths()
    A = A or load()
    src = src or {k: p.read_text(encoding="utf-8") for k, p in R17.SOURCES.items()}
    src18 = src18 or R18.load_src18()
    src19 = src19 or load_src19()
    if files is None:
        files = {k: p.read_bytes() for k, p in R15.ART.items()}
        files["res4_frozen"] = R17.RES4_FROZEN.read_bytes()
    files15 = files15 or {"py": R16.FROZEN_TEST_PY.read_bytes(), "json": R16.FROZEN_TEST_JSON.read_bytes()}
    fails, rep = [], []
    if hashlib.sha256(old.encode()).hexdigest() != OLD_SHA:
        fails.append("rc18 is not the b07f19c2… bytes rc18's parity passed on")
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
    der = derived_rc19(src19)
    old_nums = R11.numbers(old)
    added = {k: d for k, d in delta.items() if d > 0}
    src_add = {}
    for k in sorted(added):
        if old_nums[k]:
            src_add[k] = "in rc18"
        elif k in der:
            src_add[k] = "derived: " + der[k]
        elif k in allowed:
            src_add[k] = "artifact: " + allowed[k]
        else:
            fails.append(f"numbers: token {k!r} added {added[k]}x is neither in rc18, nor an artifact leaf, nor derived")
    # 1 hunks
    hs = R11.hunks(old, new)
    for h in hs:
        ids = [aid for aid, anc in ANCHORS if anc in h["new"]]
        ids += [aid for anc, aid in REMOVED_ANCHORS if not h["new"].strip() and anc in h["old"]]
        h["ids"] = list(dict.fromkeys(ids))
        if not h["ids"]:
            fails.append(f"hunk rc18 {h['rc10']} rc19 {h['rc11']} has no ID: {(h['new'] or h['old'])[:80]!r}")
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
    if new.count(H301) != 1:
        fails.append("invariant: rc18's §3.0.1 heading is not present exactly once")
    if R11.headings(old) != R11.headings(new):
        fails.append("invariant: heading list changed (rc19 declares no heading change)")
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
            fails.append(f"tail: declared rc18-block edit not found exactly once: {b[:60]!r}")
        t = t.replace(b, a)
    i19 = t.find("\n\n**rc19: review of rc18 applied**")
    blocks19 = t[i19:] if i19 >= 0 else ""
    t = t[:i19] + "\n" if i19 >= 0 else t
    if i19 < 0:
        fails.append("tail: the rc19 changelog block is missing")
    if t != to:
        fails.append("tail: working list / changelog, with the declared insertions and edit reverted and the rc19 "
                     "block removed, is not byte-identical to rc18")
    i = tn.find("\n**rc14: writing pass**")
    nums = [int(x) for x in re.findall(r"^(\d+)\. ", tn[i:] if i >= 0 else "", re.M)]
    if nums != list(range(149, 174)):
        fails.append(f"tail: rc14-rc19 changelog items are {nums}, expected 149..173")
    for n, needle in ((168, "§1 and §3.0.1 (Fable L1)"), (169, "§1 (Fable L2)"), (170, "§3.0.1 (Fable L3)"),
                      (171, "§1 (Fable L4, verified)"), (172, "rc18 changelog item 165 (Fable L5)"),
                      (173, "Working list 8, 17 and 24 (Fable L6)")):
        if not re.search(rf"^{n}\. {re.escape(needle)}", blocks19, re.M):
            fails.append(f"tail: changelog item {n} missing")
    fb = flat(blocks19)
    if "twelve days before the round\" was not used" not in fb or "neither file is edited" not in fb:
        fails.append("tail: the rc19 block does not record the L4 adaptation or the L5 non-edit")
    # 5 SHAM
    so, eo = R11.sham_spans(old)
    sn, en = R11.sham_spans(new)
    fails += eo + en
    if len(sn) != R11.EXPECTED_SHAM or len(so) != R11.EXPECTED_SHAM:
        fails.append(f"sham: {len(sn)} blocks in rc19 and {len(so)} in rc18, expected {R11.EXPECTED_SHAM}")
    for k, (x, y) in enumerate(zip(so, sn), 1):
        if x != y:
            fails.append(f"sham: block {k} ({y.strip()[:50]!r}…) is not byte-identical to rc18")
    # 6 carried locks + rc19
    fails += R13.claims_rc13(new, cz)
    nb_unstruck = R11.strip_struck(nb)
    fn_unstruck = flat(nb_unstruck)
    for pat, why in (R15.SWEEP_LOCK + R16.SWEEP_LOCK_RC16 + R17.SWEEP_LOCK_RC17 + R18.SWEEP_LOCK_RC18
                     + SWEEP_LOCK_RC19):
        for mo in re.finditer(pat, fn_unstruck):
            fails.append(f"sweep: {why}: {fn_unstruck[max(0, mo.start() - 60):mo.end() + 30]!r}")
    head = new[:new.find("\n---")]
    for mk in STATUS_MARKS_RC19:
        if mk not in head and flat(mk) not in flat(head.replace("> ", " ")):
            fails.append(f"status: header does not record {mk.splitlines()[0]!r}")
    for pat, why in STATUS_LOCK:
        if re.search(pat, flat(head.replace("> ", " "))):
            fails.append(f"status: {why}")
    carried = [p for p in R15.PRESENT if p[0] not in R16.PRESENT_REPLACED] + R16.PRESENT_RC16
    carried = [p for p in carried if p[0] not in R17.PRESENT_REPLACED] + R17.PRESENT_RC17
    carried = [p for p in carried if p[0] not in R18.PRESENT_REPLACED] + R18.PRESENT_RC18
    for txt, why in [p for p in carried if p[0] not in PRESENT_REPLACED] + PRESENT_RC19:
        if flat(txt) not in fn_unstruck:
            fails.append(f"present: {why} sentence missing: {txt[:70]!r}")
    for txt in PRESENT_REPLACED:
        if flat(txt) in fn_unstruck:
            fails.append(f"present: replaced rc18 text still present: {txt[:70]!r}")
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
                fails.append(f"qualifier: {ph[:70]!r} occurs {b}x in rc19 against {a}x in rc18, not justified")
    for (ph, d) in JUSTIFIED_PHRASE:
        if pdeltas.get(ph) != d:
            fails.append(f"qualifier: JUSTIFIED_PHRASE lists {ph[:50]!r} {d:+d}; measured {pdeltas.get(ph, 0):+d}")
    gone = {ph for (ph, d) in list(JUSTIFIED_PHRASE) + list(R18.JUSTIFIED_PHRASE) + list(R17.JUSTIFIED_PHRASE)
            + list(R16.JUSTIFIED_PHRASE) + list(R15.JUSTIFIED_PHRASE) if d < 0 and fnn.count(ph) == 0}
    for k, v in h15.items():
        if flat(v) not in fnn and flat(v) not in gone:
            fails.append(f"headline: {k} — {v[:80]!r} not found in rc19")
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
    rep.append(f"locked phrases: {len(locked)} (rc18's); justified deltas: {pdeltas}; hedge deltas: {hd}")
    if report:
        for k, v in sorted(per.items()):
            rep.append(f"  hedge [{k}]: {v}")
    # 8 integrity: rc18's carried checks (incl. S and S18), then S19
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
    f19, w19 = source_facts_rc19(src19)
    fails += f19
    warns = list(warns) + w19
    # 9 REANALISE, bold
    if R11.R_ANY.search(new):
        fails.append("reanalise: a REANALISE marker is present in rc19")
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
        print(f"SHAM-JANELA blocks: {len(sn)}, byte-identical to rc18: {sum(1 for x, y in zip(so, sn) if x == y)}")
        print(f"words: rc18 {len(old.split())} (body {len(body(old).split())}), "
              f"rc19 {len(new.split())} (body {len(body(new).split())})")
        for w in warns:
            print(w)
    if report:
        print("\nnumeric tokens added (and their source):")
        for k in sorted(added):
            print(f"  +{added[k]} {k}: {src_add.get(k, 'UNSOURCED')}")
        print("numeric tokens removed:", removed)
        print("phrase deltas:", pdeltas)
        for h in hs:
            print(f"\n[{'+'.join(h['ids']) or '?'}] rc18 l.{h['rc10'][0]}-{h['rc10'][1]} -> rc19 l.{h['rc11'][0]}-{h['rc11'][1]}")
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
    src18, src19 = R18.load_src18(), load_src19()
    rep1 = lambda a, b: (new.replace(a, b, 1), a in new)  # noqa: E731
    mutations = [
        ("L1: §1 'retracted as an open defect' restored", rep1(
            "carries the per-brief rule declared an open defect (`AMENDMENT-v1.12.md` §5) and, in\n`DECISION",
            "carries the per-brief rule retracted as an open defect (`AMENDMENT-v1.12.md` §5) and, in\n`DECISION")),
        ("L1: §3.0.1 'retracted as an open defect' restored", rep1(
            "per-brief rule declared an open defect (`AMENDMENT-v1.12.md` §5) and, in `DECISION",
            "per-brief rule retracted as an open defect (`AMENDMENT-v1.12.md` §5) and, in `DECISION")),
        ("L2: deposited-bytes parenthetical dropped", rep1(
            " (the\ndeposited bytes, md5 `35abeb68…`, 7 036 bytes, the blob of commit `d42f950`; the repository\n"
            "file was extended after publication to record the decision)", "")),
        ("L2: wrong size in the parenthetical", rep1("md5 `35abeb68…`, 7 036 bytes, the blob",
                                                     "md5 `35abeb68…`, 7 063 bytes, the blob")),
        ("L2: B.1 row removed", rep1(next(t for t, w in PRESENT_RC19 if w == "L2 B.1 row") + "\n", "")),
        ("L2: Appendix B row loses 'not in the ballast manifest'", rep1(
            "`DECISION-designacao-2026-08-25.md` among them (§1, §3.0.1) (added in rc19; not in the ballast manifest, "
            "working list 17) |", "`DECISION-designacao-2026-08-25.md` among them (§1, §3.0.1) (added in rc19) |")),
        ("L3: 'Both numbers are ours' restored", rep1(
            "Both numbers, the\nhorizon and the 20-epoch life of the fixed set, are ours,", "Both numbers are\nours,")),
        ("L4: 'two weeks before the round' restored", rep1(
            "was fixed on 2026-08-17 (its last commit) and\ndeposited in Zenodo v1.11 (record 21978476, published "
            "2026-08-17T18:32Z, the day before the\nOSF registration; v1.12 carries the same bytes, md5 `3fa3f710…`), "
            "thirteen days before the\nround was emitted,", "was fixed and deposited two weeks before the round,")),
        ("L4: 'twelve days' (the proposal) instead of thirteen", rep1(
            "thirteen days before the\nround was emitted,", "twelve days before the round,")),
        ("L4: 'deposited with v1.12' restored", rep1("deposited with v1.11 and\nv1.12). The", "deposited with v1.12). The")),
        ("L4: wrong v1.11 time", rep1("published 2026-08-17T18:32Z, the day before the\nOSF", "published 2026-08-17T19:32Z, the day before the\nOSF")),
        ("L6: Appendix B paragraph loses the snapshots", rep1(
            "the rc15 Figure B1, and\nthe Zenodo snapshots of rc18 and rc19 in `B-rc18/` and `B-rc19/`) are",
            "the rc15 Figure B1) are")),
        ("L6: working list 17 note dropped", rep1(TAIL_INSERTS[1], "")),
        ("L6: working list 8 note dropped", rep1(TAIL_INSERTS[0], "")),
        ("WL: working list 24 note dropped", rep1(TAIL_INSERTS[2], "")),
        ("L5: item 165 edit reverted", rep1(TAIL_EDITS[0][1], TAIL_EDITS[0][0])),
        ("CL: changelog item 172 removed", rep1("\n172. rc18 changelog item 165 (Fable L5)",
                                                "\nrc18 changelog item 165 (Fable L5)")),
        ("CL: L4 adaptation note dropped", rep1("The\n    proposed \"registered on OSF on 2026-08-18, twelve days "
                                                "before the round\" was not used:", "Also:")),
        ("status header without rc19", rep1("rc19 prepared 2026-10-05 (review of rc18 applied:",
                                            "rc19 drafted 2026-10-05 (review of rc18 applied:")),
        ("title lock: old title on line 1", rep1(TITLE, TITLE.replace("A registered horizon that", "A registration that"))),
        ("heading changed", rep1(H301, H301.replace("once the designation was frozen", "by construction"))),
        ("old changelog line edited", rep1("**rc18: review of rc17 applied**", "**rc18: review of rc17 applied (edited)**")),
        ("SHAM-JANELA block changed", rep1("**Our error, stated.**", "**Our error.**")),
        ("carried rc18: 12:01Z back to 14:01Z", rep1("was published at 12:01Z (the creation time of Zenodo record 22110203)",
                                                    "was published at 14:01Z (the creation time of Zenodo record 22110203)")),
        ("carried rc18: L1 'went live' reverted", rep1(
            "designation went live at 20:28Z (`AMENDMENT-DRAFT-band-collapse-2026-08-26.md` §1)",
            "designation was completed at 20:28Z")),
        ("carried rc17: 'every earlier version' restored", rep1("a rejection in versions up to rc9, and returns",
                                                                "a rejection in every earlier version, and returns")),
        ("carried rc13: abstract back to two commitments", rep1("Three commitments made before the seed",
                                                               "Two commitments made before the seed")),
        ("italic quotation removed", rep1("reading\n*\"what does not move, and could not\"* (PREREG", "reading\nthe phrase (PREREG")),
        ("citation removed", rep1(" [@kaplan2015nullnhlbi]", "")),
        ("unsourced number added", rep1("thirteen days before the\nround was emitted,",
                                        "thirteen days (313 h) before the\nround was emitted,")),
        ("unmapped hunk with no anchor", rep1("**Benchmarks compare systems on fixed tasks.**",
                                               "Benchmarks are compared.\n\n**Benchmarks compare systems on fixed tasks.**")),
    ]
    ok = True
    for name, (mutated, applied) in mutations:
        assert applied and mutated != new, f"mutation did not apply: {name}"
        f = [x for x in check(old, mutated, verbose=False, cz=cz, st=st, A=A, files=files, files15=files15,
                              src=src, src18=src18, src19=src19)
             if name.startswith("unmapped") or "has no ID" not in x]
        print(f"mutation [{name}]: {'CAUGHT' if f else 'MISSED'}" + (f" -> {f[0][:140]}" if f else ""))
        ok &= bool(f)

    def zf_mut(key, field, val, which="zfiles11"):
        j = json.loads(src19[which])
        for e in j["entries"]:
            if e["key"] == key:
                e[field] = val
        return dict(src19=dict(src19, **{which: json.dumps(j)}))
    s5 = src19["amend"]
    integ = [
        ("S19/L1: amendment §5 heading no longer 'validamente congelada'", dict(src19=dict(src19, amend=s5.replace(
            "## §5. Defeito aberto: a designação não está validamente congelada", "## §5. Retratação: a regra por brief")))),
        ("S19/L1: amendment §5.1 retracts the rule itself", dict(src19=dict(src19, amend=s5.replace(
            "Retratado o modelo de limiar (§1.1)", "Fica retratada a regra por brief (§1.1)")))),
        ("S19/L2: deposited DECISION size differs", zf_mut("DECISION-designacao-2026-08-25.md", "size", 7063, "zfiles12")),
        ("S19/L2: repository DECISION never extended", dict(src19=dict(src19, decision_head=src19["decision_dep"]))),
        ("S19/L2: DESIGNATION-SEED line shift", dict(src19=dict(src19, dseed="\n" + src19["dseed"]))),
        ("S19/L4: assign_arms.py changed after 2026-08-17", dict(src19=dict(
            src19, assign_log="abc1234 2026-08-29T10:00:00+00:00\n" + src19["assign_log"]))),
        ("S19/L4: v1.11 assign_arms.py md5 differs", zf_mut("assign_arms.py", "checksum", "md5:" + "0" * 32)),
        ("S19/L4: v1.12 assign_arms.py md5 differs", zf_mut("assign_arms.py", "checksum", "md5:" + "1" * 32, "zfiles12")),
        ("S19/L4: v1.11 created a day later", dict(src19=dict(src19, zrec11=src19["zrec11"].replace(
            "2026-08-17T18:32:45", "2026-08-18T18:32:45")))),
        ("S19/L4: OSF registration date moved", dict(src19=dict(src19, prereg=src19["prereg"].replace(
            "REGISTERED — OSF `yf7d2`, 2026-08-18T07:56:44Z", "REGISTERED — OSF `yf7d2`, 2026-08-20T07:56:44Z", 1)))),
        ("S19/L4: emission time moved", dict(src19=dict(src19, aseed=src19["aseed"].replace(
            "A rodada emitiu em **2026-08-30T21:32:04Z**", "A rodada emitiu em **2026-08-31T21:32:04Z**")))),
        ("S19/L5: band draft l.5 corrected", dict(src19=dict(src19, band=src19["band"].replace(
            "2026-08-26T14:01Z)", "2026-08-26T12:01Z)", 1)))),
        ("S19/L6: manifest now lists B-rc18/", dict(src19=dict(src19, manifest=(src19["manifest"] or "{}").replace(
            '"artefatos"', '"B-rc18/zenodo-22110203-files.json": 1, "artefatos"', 1)))),
        ("carried S18: Zenodo v1.12 created at 14:01Z", dict(src18=dict(src18, zrec=src18["zrec"].replace(
            "2026-08-26T12:01:06", "2026-08-26T14:01:06")))),
        ("carried rc17 S: amendment wording", dict(src=dict(src, amend=src["amend"].replace(
            "**é recomputada a cada brief**", "**é fixa**")))),
        ("carried rc17: RESULTADO-v4 note missing", dict(files=dict(files, res4=files["res4_frozen"]))),
    ]
    for name, kw in integ:
        args = dict(cz=cz, st=st, A=A, files=files, files15=files15, src=src, src18=src18, src19=src19)
        args.update(kw)
        f = check(old, new, verbose=False, **args)
        print(f"mutation [{name}] (integrity): {'CAUGHT' if f else 'MISSED'}" + (f" -> {f[0][:140]}" if f else ""))
        ok &= bool(f)
    base = check(old, new, verbose=False, cz=cz, st=st, A=A, files=files, files15=files15, src=src,
                 src18=src18, src19=src19)
    print(f"unmutated rc19: {'PASS' if not base else 'FAIL'}" + (f" -> {base}" if base else ""))
    print(f"mutations: {len(mutations) + len(integ)}")
    return 0 if ok and not base else 1


if __name__ == "__main__":
    sys.exit(main())
