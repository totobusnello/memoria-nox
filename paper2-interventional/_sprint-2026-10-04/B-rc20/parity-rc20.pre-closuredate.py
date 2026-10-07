#!/usr/bin/env python3
"""Parity check B-v2-rc19.md -> B-v2-rc20.md (Paper B, sprint 2026-10-04; rc20 2026-10-06).

rc20 applies the Codex read of rc19 (NO-GO, one MEDIUM, two LOW; receipt
`adversary-receipt-codex-2026-10-06T095645-63516.txt`, exit 0), each finding verified against its
primary source first (`APPLY-B-rc20.md`). No number of the analysis moves and no artifact of the
analysis changes.

  M1  Abstract, §3.0.1, §3.0.1 heading, Appendix A: "The trial did not stop early" / "234 was
      infeasible from the start" / "ran exactly as long as it could" -> the trial ended before the
      deposited horizon (PREREG l.795: 234 randomized epochs or the calendar cap, whichever first;
      neither reached), and expiry of the fixed designation is not a deposited stopping condition.
      Appendix A gains a twelfth item. §3.0.1 "the expiry stops the trial" -> "ends the
      intervention" (sweep).
  L1  §3.0.1 and B.1: `09-20` session-hours under the expiry cut quoted on the registered leg,
      0.5902 -> 0.4820 (v4 legs `registrado_sem_janela`, `registrado`); 0.6235 -> 0.5154 named in
      B.1 as the washout-retaining diagnostic of `corte_pos_expiracao`.
  L2  §9: "a 30-day life, 8.5% of the registered design" -> "a 30-day age limit, leaving 20
      eligible trial epochs, 8.5% of the registered 234".
  P   §1: "(option B) (the deposited bytes …)" merged into one parenthetical.

Checks (exit 1 if any fails):
  1. hunks: every hunk rc19 -> rc20 carries an ID from ANCHORS.
  2. numbers: every numeric token REMOVED from the body is in JUSTIFIED_REMOVED with its exact
     count; every token ADDED is in rc19, an artifact leaf, or derived (derived_rc20).
  3. invariants rc19 -> rc20: italic quotations, citations, footnotes, DOIs, image links unchanged;
     struck spans changed only by the declared "~~Eleven~~"; headings identical except the declared
     §3.0.1 heading; title lock.
  4. working list and changelog: rc20's, with the declared insertion reverted and the rc20 block
     removed, is byte-identical to rc19's; items 149-177.
  5. SHAM-JANELA: 10 blocks byte-identical to rc19.
  6. carried locks: rc19's (with everything it carries), with declared replacements; NEW sweep
     (SWEEP_LOCK_RC20, incl. no "did not stop early") and presence locks (PRESENT_RC20).
  7. qualifier set and hedge words, per hunk-ID group, summed to the body delta.
  8. integrity: rc19's carried checks (incl. S, S18, S19); NEW source block S20.
  9. no REANALISE marker; bold balanced per paragraph.

Usage:  python3 parity-rc20.py | --report | --self-test     Reads; writes nothing.
"""
import collections
import datetime as dt
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
OLD = SPRINT / "B-v2-rc19.md"
NEW = SPRINT / "B-v2-rc20.md"
RC19 = SPRINT / "B-rc19" / "parity-rc19.py"
RC19_SHA = "13ad30fe07d89511e84b6162f17b7d34271af139936cf726fc82d3b36adecce3"
OLD_SHA = "fe1be66798090e9138274ef3c8127c9472616d9194231716adbe336018645b52"

assert hashlib.sha256(RC19.read_bytes()).hexdigest() == RC19_SHA, \
    "parity-rc19.py changed: the locks carried from it are no longer the ones rc19 ran"
_spec = importlib.util.spec_from_file_location("parity_rc19", RC19)
R19 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(R19)
R18 = R19.R18
R17 = R18.R17
R16, R15, R14, R13, R12, R11 = R17.R16, R17.R15, R17.R14, R17.R13, R17.R12, R17.R11
flat, body, tail, sha, sci, load = R17.flat, R17.body, R17.tail, R17.sha, R17.sci, R17.load
TITLE, TITLE_OLD = R18.TITLE, R18.TITLE_OLD
H301_OLD = R18.H301_NEW
H301_NEW = "### 3.0.1 The fixed designation could support dose exposure in only 20 of 234 registered epochs"

SOURCES20 = {
    "prereg": P2 / "PREREG-DRAFT.md",
    "dev": P2 / "DEVIATIONS-FOR-PAPER.md",
    "v4": P2 / "out" / "ITT-REGISTRADO-v4-2026-10-05.json",
    "exp": P2 / "out" / "expiracao-designados-2026-09-09.json",
}
RECEIPT = REPO / ".remember" / "adversary-receipt-codex-2026-10-06T095645-63516.txt"


def load_src20():
    src = {k: p.read_text(encoding="utf-8") for k, p in SOURCES20.items()}
    src["receipt"] = RECEIPT.read_text(encoding="utf-8") if RECEIPT.exists() else None
    return src


# ---------------------------------------------------------------- S20: the facts M1, L1, L2 rest on
def source_facts_rc20(src):
    fails, warns = [], []
    pl = src["prereg"].splitlines()
    # M1: the deposited stopping rule (l.795) and its calendar cap (l.799, l.801)
    l795 = pl[794] if len(pl) > 794 else ""
    if not (l795.startswith("**Stopping rule (F3 fix).**")
            and "data collection ends at **234 randomized epochs" in l795
            and "or the pre-committed calendar end date, whichever comes first" in l795
            and "No interim analyses; no optional stopping." in l795):
        fails.append("S20/M1: PREREG l.795 is not the 234-epochs-or-calendar stopping rule")
    if "`calendar_end = date(first randomized epoch) + 240 days.`" not in pl[798] \
            or "AMENDED 2026-08-17 to 323 days" not in pl[800]:
        fails.append("S20/M1: PREREG l.799/l.801 no longer give the calendar cap (240 d, amended to 323 d)")
    if re.search(r"(?i)\bexpir", "\n".join(ln for ln in pl if not ln.startswith("⚠️ **These counts are snapshot-relative"))):
        fails.append("S20/M1: PREREG now mentions expiry outside the l.861 snapshot note; 'not a deposited "
                     "stopping condition' needs rereading")
    # neither horizon condition reached: 20 epochs 2026-09-01..2026-09-20, cap >= 240 d after 09-01
    exp = json.loads(src["exp"])
    ca = {e.get("created_at") for e in exp.get("por_id", [])}
    if len(exp.get("por_id", [])) != 19 or len(ca) != 1 or exp.get("janela_global_d") != 30.0:
        fails.append("S20/M1: the expiry measurement no longer has 19 items, one created_at, a 30-day window")
    else:
        end = dt.datetime.fromisoformat(ca.pop()) + dt.timedelta(days=exp["janela_global_d"])
        if end.strftime("%Y-%m-%d %H:%M:%S") != "2026-09-20 22:51:23":
            fails.append(f"S20/M1: the designation expires {end}, not 2026-09-20 22:51:23")
        # neither horizon condition reached: epochs 2026-09-01..2026-09-20 are 20, far below 234
        # and far inside the calendar cap (first epoch + 323 d)
        if (dt.date(2026, 9, 20) - dt.date(2026, 9, 1)).days + 1 != 20 or 20 >= 234 \
                or dt.date(2026, 9, 1) + dt.timedelta(days=323) <= dt.date(2026, 9, 21):
            fails.append("S20/M1: the realized window reaches a deposited horizon condition")
    dv = src["dev"]
    if "#### 10.14 Decisão revisada (2026-09-09, tarde): **não alargar a janela**. O ensaio termina em 2026-09-20" not in dv:
        fails.append("S20/M1: DEVIATIONS §10.14 heading (decision 2026-09-09, end 2026-09-20) changed")
    if "> **\"encerra 20/09 mesmo, e desliga a dose depois\"**" not in dv:
        fails.append("S20/M1: DEVIATIONS §10.22 no longer quotes the closure instruction")
    if "| drop-in arquivado | `2026-09-21 09:43:05Z` |" not in dv:
        fails.append("S20/M1: DEVIATIONS §10.29 no longer dates the switch-off 2026-09-21 09:43:05Z")
    # L1: the registered leg and the diagnostic block
    v4 = json.loads(src["v4"])
    reg = v4["pernas"]["registrado"]["por_epoch"]["2026-09-20"]
    sj = v4["pernas"]["registrado_sem_janela"]["por_epoch"]["2026-09-20"]
    if f"{sj['horas']:.4f}" != "0.5902" or f"{reg['horas']:.4f}" != "0.4820":
        fails.append(f"S20/L1: registered-leg 09-20 hours are {sj['horas']} -> {reg['horas']}, not 0.5902 -> 0.4820")
    if round(sj["oport"] - reg["oport"], 3) != 22.835 or round(sj["repet"] - reg["repet"], 3) != 2.0:
        fails.append("S20/L1: the cut on the registered leg no longer removes 22.835 opportunities and 2 repeats")
    c = v4["corte_pos_expiracao"]["substituicao"]
    if (c["horas_sessao_antes"], c["horas_sessao_depois"], c["episodios_pos_expiracao"]) != (0.6235, 0.5154, 33):
        fails.append("S20/L1: corte_pos_expiracao is no longer 33 episodes, 0.6235 -> 0.5154")
    wd = v4["pernas"]["so_washout_in_denominator"]["por_epoch"]["2026-09-20"]["horas"]
    if f"{wd:.4f}" != "0.5902" or f"{v4['pernas']['atual']['por_epoch']['2026-09-20']['horas']:.4f}" != "0.6235":
        fails.append("S20/L1: 0.6235 is no longer the washout-retaining value (atual) and 0.5902 its washout-free one")
    # L2: 20 of 234 is 8.5%
    if f"{100 * 20 / 234:.1f}" != "8.5":
        fails.append("S20/L2: 20/234 is not 8.5%")
    # the receipt the review rests on
    if src["receipt"] is None:
        warns.append("S20: Codex receipt not found on this machine; 'exit: 0' not re-verified")
    elif not re.search(r"^exit: 0$", src["receipt"], re.M) or "voice: codex" not in src["receipt"]:
        fails.append("S20: the Codex receipt is not a codex voice with exit: 0")
    return fails, warns


# ---------------------------------------------------------------- 1: anchors
ANCHORS = [
    ("ST", "rc20 prepared 2026-10-06 (review of rc19 applied:"),
    ("M1", "The trial ended before its registered 234-epoch horizon"),
    ("M1", H301_NEW),
    ("M1", "The trial ended before the\ndeposited data-collection horizon"),
    ("M1", "so the expiry ends the intervention"),
    ("M1", "~~Eleven~~ Twelve"),
    ("M1", "- the horizon: data collection ended after 20 randomized epochs"),
    ("L1", "session-hours fall from 0.5902 to 0.4820"),
    ("L1", "0.5902 → 0.4820 h on the registered leg"),
    ("L2", "30-day age limit, leaving 20 eligible trial epochs"),
    ("P", "(option B; the\ndeposited bytes are md5"),
    ("WL", "*(rc20: rc19 had one full read"),
    ("CL", "**rc20: review of rc19 applied**"),
]
REMOVED_ANCHORS = []

# ---------------------------------------------------------------- 2: numbers
JUSTIFIED_REMOVED = {   # token -> (count, finding, reason)
    "0.6235": (1, "L1", "§3.0.1 now quotes the registered leg; B.1 keeps 0.6235 as the named diagnostic"),
    "0.5154": (1, "L1", "§3.0.1 now quotes the registered leg; B.1 keeps 0.5154 as the named diagnostic"),
}


def derived_rc20(src):
    out = {}
    for tok in ("174", "175", "176", "177"):
        out[tok] = "rc20 changelog item numbers"
    out["2026-10-06"] = "rc20 date (status header)"
    for tok in ("795", "797", "801", "l.795", "l.797–801"):
        out[tok] = "PREREG line numbers (checked in S20)"
    out["09"] = "the field path `por_epoch.2026-09-20.horas` (B.1), cut by the tokenizer"
    out["2026-10-06T095645-63516"] = "Codex receipt name"
    out["095645"] = out["2026-10-06T095645-63516"]
    out["63516"] = out["2026-10-06T095645-63516"]
    for tok in ("10.14", "10.22", "10.29"):
        out[tok] = "DEVIATIONS section numbers (checked in S20)"
    return out


# ---------------------------------------------------------------- 3/4: tail
TAIL_INSERTS = [
    """
    *(rc20: rc19 had one full read, Codex NO-GO with one MEDIUM and two LOW; all verified and
    applied in rc20 (`APPLY-B-rc20.md`). rc20 itself has not been reviewed.)*""",
]
TAIL_EDITS = []

# ---------------------------------------------------------------- 6: locks
SWEEP_LOCK_RC20 = [
    (r"(?i)did not stop early", "M1: the trial ended before its deposited horizon"),
    (r"(?i)\binfeasib", "M1: no 'infeasible' claim about N = 234 left in the body"),
    (r"(?i)ran exactly as long as it could", "M1: heading and text no longer say the trial ran as long as it could"),
    (r"(?i)expiry stops the trial", "M1: expiry ends the intervention; it is not a deposited stopping condition"),
    (r"(?i)stop(ped)? early", "M1: no 'stop early' framing"),
    (r"30-day life", "L2: a 30-day age limit, not a life"),
    (r"8\.5% of the registered design", "L2: 8.5% of the registered 234"),
    (r"session-hours fall from 0\.6235", "L1: §3.0.1 quotes the registered leg"),
    (r"\(option B\) \(", "P: one parenthetical"),
]
PRESENT_RC20 = [
    ("The trial ended before its registered 234-epoch horizon, after the fixed designation exhausted its "
     "eligibility. The designation could support dose exposure in only 20 trial epochs, a limitation fixed "
     "before Epoch 1.", "M1 Abstract"),
    ("The trial ended before the deposited data-collection horizon: neither 234 randomized epochs nor the "
     "calendar cap was reached, and expiry of the fixed designation is not a deposited stopping condition "
     "(Appendix A).", "M1 §3.0.1"),
    ("and the dose was switched off only after the fixed designation had expired (09:43:05Z on 2026-09-21)",
     "M1 §3.0.1 switch-off"),
    ("- the horizon: data collection ended after 20 randomized epochs, before either deposited horizon "
     "condition (234 randomized epochs, or the calendar cap) was reached. Expiry of the fixed designation was "
     "not a deposited stopping condition.", "M1 Appendix A item"),
    ("Twelve (the struck item below is no longer a deviation) that a reader cannot reconstruct",
     "M1 Appendix A count (struck spans removed before matching)"),
    ("session-hours fall from 0.5902 to 0.4820 (`out/ITT-REGISTRADO-v4-2026-10-05.json`, legs "
     "`registrado_sem_janela` and `registrado`).", "L1 §3.0.1"),
    ("2 repeats, 0.5902 → 0.4820 h on the registered leg, fields `pernas.registrado_sem_janela` and "
     "`pernas.registrado`, `por_epoch.2026-09-20.horas`; the 0.6235 → 0.5154 h of the block "
     "`corte_pos_expiracao` keeps the washout in the denominator and is a diagnostic);", "L1 B.1"),
    ("had a 30-day age limit, leaving 20 eligible trial epochs, 8.5% of the registered 234 (§3.0.1).", "L2 §9"),
    ("signature group (option B; the deposited bytes are md5 `35abeb68…`, 7 036 bytes, the blob of commit "
     "`d42f950`, and the repository file was extended after publication to record the decision);", "P §1"),
]
PRESENT_REPLACED = {  # rc19 presence locks that rc20 rewrites -> finding
    R19.PRESENT_RC19[0][0]: "P: the double parenthesis merged",
}
STATUS_MARKS_RC20 = R19.STATUS_MARKS_RC19 + ["rc20 prepared 2026-10-06 (review of rc19 applied:"]
STATUS_LOCK = R19.STATUS_LOCK
STRUCK_DELTA = {"~~Eleven~~": 1}

# ---------------------------------------------------------------- 7: qualifier deltas (from --report)
JUSTIFIED_PHRASE = {}   # no locked qualifier phrase moves (measured: {})
JUSTIFIED_HEDGE = {
    "ST": ({"not": 1, "registered": 2}, "status header, rc20 clause: 'ended before its registered horizon, which "
                                        "expiry … does not satisfy'; 'quoted on the registered leg'"),
    "M1": ({"only": 3, "could": 1, "registered": 2, "neither": 1, "nor": 1, "deposited": 4, "either": 1},
           "Codex M1's text: abstract 'registered 234-epoch horizon', 'could support … in only 20'; heading "
           "'only 20 of 234 registered'; §3.0.1 'deposited data-collection horizon', 'neither … nor', 'not a "
           "deposited stopping condition', 'only after'; Appendix A 'either deposited horizon condition', "
           "'not a deposited stopping condition'"),
    "L1": ({"registered": 1}, "B.1: '0.5902 → 0.4820 h on the registered leg'"),
}

# ---------------------------------------------------------------- deviation-count lock (rc16's), replaced:
# M1 adds the horizon item, so the count word is Twelve after a struck Eleven
DEV_COUNT = 12
DEV_COUNT_JUSTIFIED = ("M1: data collection ended after 20 randomized epochs, before either deposited horizon "
                       "condition; expiry of the fixed designation was not a deposited stopping condition")


def appa_count_rc20(new):
    appa = R13.section(new, "\n## Appendix A", "\n## Appendix B")
    m = re.search(r"~~Twelve~~ ~~Thirteen~~ ~~Twelve~~ ~~Eleven~~ (\w+) \(the struck item below is no longer a "
                  r"deviation\) that a reader", appa)
    if not m:
        return ["App A: count sentence (~~Twelve~~ ~~Eleven~~ <word>) not found"]
    end = appa.find("\n\nThe dose band `{2.0, 4.0, 7.5}` was retained", m.end())
    if end < 0:
        return ["App A: the list's closing note (K1) not found"]
    lst = appa[m.end():end]
    items = re.split(r"\n- ", "\n" + lst.strip())[1:]
    live = [x for x in items if not x.lstrip().startswith("~~")]
    want = R13.WORDS.get(m.group(1).lower())
    fails = []
    if want != len(live):
        fails.append(f"App A: the count word says {m.group(1)}, the list has {len(live)} unstruck items of {len(items)}")
    if want != DEV_COUNT:
        fails.append(f"App A: the count is {m.group(1)}, the locked count is {DEV_COUNT} ({DEV_COUNT_JUSTIFIED[:40]}…)")
    if R16.DOSE_ITEM.search("\n" + lst.strip()):
        fails.append("App A: the dose band is listed as a deviation again (K1)")
    if not any(x.startswith("the horizon: data collection ended after 20 randomized epochs") for x in live):
        fails.append("App A: the horizon item (M1) is not among the unstruck items")
    return fails


R13.appa_count = appa_count_rc20  # claims_rc13 looks it up in its module at call time


def check(old, new, verbose=True, report=False, cz=None, st=None, A=None, files=None, files15=None,
          src=None, src18=None, src19=None, src20=None):
    cz = cz or R13.load_rc13()
    st = st or R13.load_paths()
    A = A or load()
    src = src or {k: p.read_text(encoding="utf-8") for k, p in R17.SOURCES.items()}
    src18 = src18 or R18.load_src18()
    src19 = src19 or R19.load_src19()
    src20 = src20 or load_src20()
    if files is None:
        files = {k: p.read_bytes() for k, p in R15.ART.items()}
        files["res4_frozen"] = R17.RES4_FROZEN.read_bytes()
    files15 = files15 or {"py": R16.FROZEN_TEST_PY.read_bytes(), "json": R16.FROZEN_TEST_JSON.read_bytes()}
    fails, rep = [], []
    if hashlib.sha256(old.encode()).hexdigest() != OLD_SHA:
        fails.append("rc19 is not the fe1be667… bytes rc19's parity passed on")
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
    der = derived_rc20(src20)
    old_nums = R11.numbers(old)
    added = {k: d for k, d in delta.items() if d > 0}
    src_add = {}
    for k in sorted(added):
        if old_nums[k]:
            src_add[k] = "in rc19"
        elif k in der:
            src_add[k] = "derived: " + der[k]
        elif k in allowed:
            src_add[k] = "artifact: " + allowed[k]
        else:
            fails.append(f"numbers: token {k!r} added {added[k]}x is neither in rc19, nor an artifact leaf, nor derived")
    # 1 hunks
    hs = R11.hunks(old, new)
    for h in hs:
        ids = [aid for aid, anc in ANCHORS if anc in h["new"]]
        ids += [aid for anc, aid in REMOVED_ANCHORS if not h["new"].strip() and anc in h["old"]]
        h["ids"] = list(dict.fromkeys(ids))
        if not h["ids"]:
            fails.append(f"hunk rc19 {h['rc10']} rc20 {h['rc11']} has no ID: {(h['new'] or h['old'])[:80]!r}")
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
                fails.append(f"invariant: struck spans moved by {d}; rc20 declares {STRUCK_DELTA}")
        elif name in R17.INV_FIXED and d:
            fails.append(f"invariant: {name} changed: {dict(list(d.items())[:4])}")
        rep.append(f"{name}: {sum(a.values())} -> {sum(b.values())}" + ("" if not d else f"  (delta {len(d)} items)"))
        if report and d and (name in R17.INV_FREE or name == "struck spans"):
            for k, v in sorted(d.items(), key=lambda kv: str(kv[0]))[:40]:
                rep.append(f"    {v:+d} {str(k)[:150]}")
    if old.count(H301_OLD) != 1 or new.count(H301_NEW) != 1 or H301_OLD in new:
        fails.append("invariant: the §3.0.1 heading is not rc19's in rc19 and the M1 heading in rc20")
    if R11.headings(old.replace(H301_OLD, H301_NEW, 1)) != R11.headings(new):
        fails.append("invariant: heading list changed beyond the declared §3.0.1 heading")
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
            fails.append(f"tail: declared rc19-block edit not found exactly once: {b[:60]!r}")
        t = t.replace(b, a)
    i20 = t.find("\n\n**rc20: review of rc19 applied**")
    blocks20 = t[i20:] if i20 >= 0 else ""
    t = t[:i20] + "\n" if i20 >= 0 else t
    if i20 < 0:
        fails.append("tail: the rc20 changelog block is missing")
    if t != to:
        fails.append("tail: working list / changelog, with the declared insertion reverted and the rc20 "
                     "block removed, is not byte-identical to rc19")
    i = tn.find("\n**rc14: writing pass**")
    nums = [int(x) for x in re.findall(r"^(\d+)\. ", tn[i:] if i >= 0 else "", re.M)]
    if nums != list(range(149, 178)):
        fails.append(f"tail: rc14-rc20 changelog items are {nums}, expected 149..177")
    for n, needle in ((174, "Abstract, §3.0.1 and Appendix A (Codex M1)"), (175, "§3.0.1 and B.1 (Codex L1)"),
                      (176, "§9 (Codex L2)"), (177, "§1: the double parenthesis")):
        if not re.search(rf"^{n}\. {re.escape(needle)}", blocks20, re.M):
            fails.append(f"tail: changelog item {n} missing")
    fb = flat(blocks20)
    if "adversary-receipt-codex-2026-10-06T095645-63516.txt" not in fb or "`exit: 0`" not in fb:
        fails.append("tail: the rc20 block does not name the Codex receipt and its exit")
    # 5 SHAM
    so, eo = R11.sham_spans(old)
    sn, en = R11.sham_spans(new)
    fails += eo + en
    if len(sn) != R11.EXPECTED_SHAM or len(so) != R11.EXPECTED_SHAM:
        fails.append(f"sham: {len(sn)} blocks in rc20 and {len(so)} in rc19, expected {R11.EXPECTED_SHAM}")
    for k, (x, y) in enumerate(zip(so, sn), 1):
        if x != y:
            fails.append(f"sham: block {k} ({y.strip()[:50]!r}…) is not byte-identical to rc19")
    # 6 carried locks + rc20
    fails += R13.claims_rc13(new, cz)
    nb_unstruck = R11.strip_struck(nb)
    fn_unstruck = flat(nb_unstruck)
    for pat, why in (R15.SWEEP_LOCK + R16.SWEEP_LOCK_RC16 + R17.SWEEP_LOCK_RC17 + R18.SWEEP_LOCK_RC18
                     + R19.SWEEP_LOCK_RC19 + SWEEP_LOCK_RC20):
        for mo in re.finditer(pat, fn_unstruck):
            fails.append(f"sweep: {why}: {fn_unstruck[max(0, mo.start() - 60):mo.end() + 30]!r}")
    head = new[:new.find("\n---")]
    for mk in STATUS_MARKS_RC20:
        if mk not in head and flat(mk) not in flat(head.replace("> ", " ")):
            fails.append(f"status: header does not record {mk.splitlines()[0]!r}")
    for pat, why in STATUS_LOCK:
        if re.search(pat, flat(head.replace("> ", " "))):
            fails.append(f"status: {why}")
    carried = [p for p in R15.PRESENT if p[0] not in R16.PRESENT_REPLACED] + R16.PRESENT_RC16
    carried = [p for p in carried if p[0] not in R17.PRESENT_REPLACED] + R17.PRESENT_RC17
    carried = [p for p in carried if p[0] not in R18.PRESENT_REPLACED] + R18.PRESENT_RC18
    carried = [p for p in carried if p[0] not in R19.PRESENT_REPLACED] + R19.PRESENT_RC19
    for txt, why in [p for p in carried if p[0] not in PRESENT_REPLACED] + PRESENT_RC20:
        if flat(txt) not in fn_unstruck:
            fails.append(f"present: {why} sentence missing: {txt[:70]!r}")
    for txt in PRESENT_REPLACED:
        if flat(txt) in fn_unstruck:
            fails.append(f"present: replaced rc19 text still present: {txt[:70]!r}")
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
                fails.append(f"qualifier: {ph[:70]!r} occurs {b}x in rc20 against {a}x in rc19, not justified")
    for (ph, d) in JUSTIFIED_PHRASE:
        if pdeltas.get(ph) != d:
            fails.append(f"qualifier: JUSTIFIED_PHRASE lists {ph[:50]!r} {d:+d}; measured {pdeltas.get(ph, 0):+d}")
    gone = {ph for (ph, d) in list(JUSTIFIED_PHRASE) + list(R19.JUSTIFIED_PHRASE) + list(R18.JUSTIFIED_PHRASE)
            + list(R17.JUSTIFIED_PHRASE) + list(R16.JUSTIFIED_PHRASE) + list(R15.JUSTIFIED_PHRASE)
            if d < 0 and fnn.count(ph) == 0}
    for k, v in h15.items():
        if flat(v) not in fnn and flat(v) not in gone:
            fails.append(f"headline: {k} — {v[:80]!r} not found in rc20")
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
    rep.append(f"locked phrases: {len(locked)} (rc19's); justified deltas: {pdeltas}; hedge deltas: {hd}")
    if report:
        for k, v in sorted(per.items()):
            rep.append(f"  hedge [{k}]: {v}")
    # 8 integrity: rc19's carried checks (incl. S, S18, S19), then S20
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
    f20, w20 = source_facts_rc20(src20)
    fails += f19 + f20
    warns = list(warns) + w19 + w20
    # 9 REANALISE, bold
    if R11.R_ANY.search(new):
        fails.append("reanalise: a REANALISE marker is present in rc20")
    noncode = re.sub(r"```.*?```", "", new, flags=re.S)
    for k, para in enumerate(re.split(r"\n\s*\n", noncode)):
        if para.count("**") % 2:
            fails.append(f"bold: odd number of ** in paragraph {k}: {para.strip()[:60]!r}")
    if verbose:
        print(f"hunks: {len(hs)}, all with an ID: {all(h['ids'] for h in hs)} "
              f"({sorted({i for h in hs for i in h['ids']})})")
        for r in rep:
            print(r)
        print(f"headings: {len(R11.headings(new))}, only §3.0.1 changed: "
              f"{R11.headings(old.replace(H301_OLD, H301_NEW, 1)) == R11.headings(new)}")
        print(f"SHAM-JANELA blocks: {len(sn)}, byte-identical to rc19: {sum(1 for x, y in zip(so, sn) if x == y)}")
        print(f"words: rc19 {len(old.split())} (body {len(body(old).split())}), "
              f"rc20 {len(new.split())} (body {len(body(new).split())})")
        for w in warns:
            print(w)
    if report:
        print("\nnumeric tokens added (and their source):")
        for k in sorted(added):
            print(f"  +{added[k]} {k}: {src_add.get(k, 'UNSOURCED')}")
        print("numeric tokens removed:", removed)
        print("phrase deltas:", pdeltas)
        for h in hs:
            print(f"\n[{'+'.join(h['ids']) or '?'}] rc19 l.{h['rc10'][0]}-{h['rc10'][1]} -> rc20 l.{h['rc11'][0]}-{h['rc11'][1]}")
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
    src18, src19, src20 = R18.load_src18(), R19.load_src19(), load_src20()
    rep1 = lambda a, b: (new.replace(a, b, 1), a in new)  # noqa: E731
    mutations = [
        ("M1: abstract 'did not stop early' restored", rep1(
            "The trial ended before its registered 234-epoch horizon, after the fixed designation\nexhausted its "
            "eligibility. The designation could support dose exposure in only 20 trial\nepochs, a limitation fixed "
            "before Epoch 1.", "The trial did not stop early: 234 was infeasible from the start.")),
        ("M1: 'did not stop early' added beside the new abstract text", rep1(
            "a limitation fixed before Epoch 1. All 19", "a limitation fixed before Epoch 1. It did not stop early. All 19")),
        ("M1: §3.0.1 'The trial did not stop early' restored", rep1(
            "The trial ended before the\ndeposited data-collection horizon: neither 234 randomized epochs nor the "
            "calendar cap was\nreached, and expiry of the fixed designation is not a deposited stopping condition\n"
            "(Appendix A).", "The trial did not stop early.")),
        ("M1: §3.0.1 'switched off later' restored", rep1(
            "the dose was switched off only\nafter the fixed designation had expired (09:43:05Z",
            "the dose was switched off later\n(09:43:05Z")),
        ("M1: rc19 heading restored", rep1(H301_NEW, H301_OLD)),
        ("M1: 'infeasible from the start' slipped into §9", rep1(
            "had a\n30-day age limit,", "had a\n30-day age limit (234 was infeasible from the start),")),
        ("M1: 'the expiry stops the trial' restored", rep1("so the expiry ends the intervention",
                                                           "so the expiry stops the trial")),
        ("M1: Appendix A item dropped", rep1(
            "- the horizon: data collection ended after 20 randomized epochs, before either deposited\n", "- ")),
        ("M1: Appendix A count left at Eleven", rep1("~~Eleven~~ Twelve (the struck", "Eleven (the struck")),
        ("M1: Appendix A expiry sentence dropped", rep1(
            " Expiry of the\n  fixed designation was not a deposited stopping condition.", "")),
        ("L1: §3.0.1 back to the diagnostic 0.6235 → 0.5154", rep1(
            "session-hours fall from 0.5902 to 0.4820", "session-hours fall from 0.6235 to 0.5154")),
        ("L1: wrong registered-leg value", rep1("session-hours fall from 0.5902 to 0.4820",
                                                "session-hours fall from 0.5902 to 0.4802")),
        ("L1: B.1 loses the diagnostic label", rep1(
            "keeps the washout in the denominator and is a diagnostic);", ");")),
        ("L2: '30-day life' restored", rep1(
            "30-day age limit, leaving 20 eligible trial epochs, 8.5% of the registered 234 (§3.0.1).",
            "30-day life, 8.5% of the registered design (§3.0.1).")),
        ("P: double parenthesis restored", rep1("(option B; the\ndeposited bytes are md5",
                                                "(option B) (the\ndeposited bytes, md5")),
        ("WL: working list 24 note dropped", rep1(TAIL_INSERTS[0], "")),
        ("CL: changelog item 176 removed", rep1("\n176. §9 (Codex L2)", "\n§9 (Codex L2)")),
        ("CL: receipt name dropped", rep1("receipt `adversary-receipt-codex-2026-10-06T095645-63516.txt`, ", "")),
        ("status header without rc20", rep1("rc20 prepared 2026-10-06 (review of rc19 applied:",
                                            "rc20 drafted 2026-10-06 (review of rc19 applied:")),
        ("title lock: old title on line 1", rep1(TITLE, TITLE.replace("A registered horizon that", "A registration that"))),
        ("another heading changed", rep1("### 3.0 The stopping rule, and the feasibility question it raises",
                                         "### 3.0 The stopping rule")),
        ("old changelog line edited", rep1("**rc19: review of rc18 applied**", "**rc19: review of rc18 applied (edited)**")),
        ("SHAM-JANELA block changed", rep1("**Our error, stated.**", "**Our error.**")),
        ("extra struck span", rep1("~~Eleven~~ Twelve", "~~Eleven~~ ~~Twelve~~ Twelve")),
        ("carried rc19: 'two weeks before the round' restored", rep1(
            "thirteen days before the\nround was emitted,", "two weeks before the round,")),
        ("carried rc19: 'retracted as an open defect' restored", rep1(
            "per-brief rule declared an open defect (`AMENDMENT-v1.12.md` §5) and, in `DECISION",
            "per-brief rule retracted as an open defect (`AMENDMENT-v1.12.md` §5) and, in `DECISION")),
        ("carried rc18: 12:01Z back to 14:01Z", rep1("was published at 12:01Z (the creation time of Zenodo record 22110203)",
                                                    "was published at 14:01Z (the creation time of Zenodo record 22110203)")),
        ("carried rc13: abstract back to two commitments", rep1("Three commitments made before the seed",
                                                               "Two commitments made before the seed")),
        ("italic quotation removed", rep1("reading\n*\"what does not move, and could not\"* (PREREG", "reading\nthe phrase (PREREG")),
        ("citation removed", rep1(" [@kaplan2015nullnhlbi]", "")),
        ("unsourced number added", rep1("It ran for the entire interval in which", "It ran for the entire interval (8317 h) in which")),
        ("unmapped hunk with no anchor", rep1("**Benchmarks compare systems on fixed tasks.**",
                                               "Benchmarks are compared.\n\n**Benchmarks compare systems on fixed tasks.**")),
    ]
    ok = True
    for name, (mutated, applied) in mutations:
        assert applied and mutated != new, f"mutation did not apply: {name}"
        f = [x for x in check(old, mutated, verbose=False, cz=cz, st=st, A=A, files=files, files15=files15,
                              src=src, src18=src18, src19=src19, src20=src20)
             if name.startswith("unmapped") or "has no ID" not in x]
        print(f"mutation [{name}]: {'CAUGHT' if f else 'MISSED'}" + (f" -> {f[0][:140]}" if f else ""))
        ok &= bool(f)

    def v4_mut(path, val):
        j = json.loads(src20["v4"])
        o = j
        for k in path[:-1]:
            o = o[k]
        o[path[-1]] = val
        return dict(src20=dict(src20, v4=json.dumps(j)))
    pr = src20["prereg"]
    integ = [
        ("S20/M1: PREREG stopping rule no longer 'whichever comes first'", dict(src20=dict(src20, prereg=pr.replace(
            "or the pre-committed calendar end date, whichever comes first", "or the designation's expiry", 1)))),
        ("S20/M1: PREREG gains an expiry stop", dict(src20=dict(src20, prereg=pr.replace(
            "No interim analyses; no optional stopping.", "Data collection also ends if the designation expires.", 1)))),
        ("S20/M1: PREREG line shift", dict(src20=dict(src20, prereg="\n" + pr))),
        ("S20/M1: PREREG mentions expiry elsewhere", dict(src20=dict(src20, prereg=pr + "\nData collection ends when the designation expires.\n"))),
        ("S20/M1: calendar cap amended away", dict(src20=dict(src20, prereg=pr.replace(
            "AMENDED 2026-08-17 to 323 days", "AMENDED 2026-08-17 to 20 days", 1)))),
        ("S20/M1: switch-off time moved", dict(src20=dict(src20, dev=src20["dev"].replace(
            "| drop-in arquivado | `2026-09-21 09:43:05Z` |", "| drop-in arquivado | `2026-09-20 21:00:00Z` |")))),
        ("S20/L1: registered-leg 09-20 hours differ", v4_mut(["pernas", "registrado", "por_epoch", "2026-09-20", "horas"], 0.5)),
        ("S20/L1: diagnostic block differs", v4_mut(["corte_pos_expiracao", "substituicao", "horas_sessao_depois"], 0.5)),
        ("S20: receipt exit 1", dict(src20=dict(src20, receipt=(src20["receipt"] or "voice: codex\nexit: 0\n").replace(
            "exit: 0", "exit: 1")))),
        ("carried S19: v1.11 created a day later", dict(src19=dict(src19, zrec11=src19["zrec11"].replace(
            "2026-08-17T18:32:45", "2026-08-18T18:32:45")))),
        ("carried S18: Zenodo v1.12 created at 14:01Z", dict(src18=dict(src18, zrec=src18["zrec"].replace(
            "2026-08-26T12:01:06", "2026-08-26T14:01:06")))),
        ("carried rc17 S: amendment wording", dict(src=dict(src, amend=src["amend"].replace(
            "**é recomputada a cada brief**", "**é fixa**")))),
        ("carried rc17: RESULTADO-v4 note missing", dict(files=dict(files, res4=files["res4_frozen"]))),
    ]
    for name, kw in integ:
        args = dict(cz=cz, st=st, A=A, files=files, files15=files15, src=src, src18=src18, src19=src19,
                    src20=src20)
        args.update(kw)
        f = check(old, new, verbose=False, **args)
        print(f"mutation [{name}] (integrity): {'CAUGHT' if f else 'MISSED'}" + (f" -> {f[0][:140]}" if f else ""))
        ok &= bool(f)
    base = check(old, new, verbose=False, cz=cz, st=st, A=A, files=files, files15=files15, src=src,
                 src18=src18, src19=src19, src20=src20)
    print(f"unmutated rc20: {'PASS' if not base else 'FAIL'}" + (f" -> {base}" if base else ""))
    print(f"mutations: {len(mutations) + len(integ)}")
    return 0 if ok and not base else 1


if __name__ == "__main__":
    sys.exit(main())
