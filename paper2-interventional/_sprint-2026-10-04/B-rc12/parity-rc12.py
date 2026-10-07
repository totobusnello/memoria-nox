#!/usr/bin/env python3
"""Parity check B-v2-rc11.md -> B-v2-rc12.md (Paper B, sprint 2026-10-04; rc12 2026-10-05).

rc12 adds one thing: the attempt, made after unblinding on 2026-10-05, to restore the census
that PREREG §3 locked (`B-censo/GATES.md`). Gate 1 passed, gate 2 failed, the census was not
run. No analysis changes; no estimate moves.

The diff is cut into hunks (difflib on lines). Every hunk must carry at least one ID, assigned
by an anchor substring of the rc12 hunk (ANCHORS):
    ST status header · CENSUS the attempt in §4 and Appendix A · DRIFT the §7 sentence on
    re-adjudication drift · APPB / B1 appendices · CL working list and changelog.

Checks (exit 1 if any fails):
  1. hunks: every hunk has an ID.
  2. numbers: every numeric token ADDED in a hunk is (a) already in rc11, or (b) a leaf of an
     artifact read at run time (rc11's artifacts plus `B-censo/gate2-compare.json`), in one of
     the paper's roundings, or (c) DERIVED at run time (the cost total and call count from
     the `usage` files, the first call's start time, the header time and the two criteria of
     the rules file, the 99/100 test-retest, the id counts), or (d) a LITERAL with its source
     (the rules file's file-system time, which nothing else holds; see check 14).
  3. headline values: rc11's headline strings (imported from `B-rc11/parity-rc11.py`, pinned
     by sha256) are still present; rc12's, formatted from `gate2-compare.json` and the `usage`
     files at run time, are present.
  4. claims: rc11's locks (a)–(f) carried, through rc11's own `claims()` (imported, pinned);
     NEW (g) no sentence says the census was run or restored (negations allowed); NEW (h) no
     credential-like string and no mention of the credential finding (decision in
     `APPLY-B-rc12.md`: omitted from the manuscript); the census attempt is reported in §4,
     §7 and Appendix A; rc11's census deviation still declared in §4 and Appendix A.
  5. headings identical (rc12 renames and adds none).
  6. citations unchanged and listed; footnotes defined; DOIs unchanged.
  7. no host, IP or personal path added.
  8. SHAM-JANELA: exactly 10 blocks, byte-identical to rc11's.
  9. no REANALISE marker.
 10. quotes: every *"..."* span added occurs verbatim in rc11 or a declared source (rc12 adds none).
 11. code spans: every added span that names a file resolves on disk; added snake_case
     identifiers occur in the artifacts or sources they name.
 12. bold balance: every paragraph has an even number of `**`.
 13. script integrity, carried from rc11 (its `script_integrity` and inputs, imported).
 14. census record: `B-censo/SHA256SUMS` verifies every file it lists, and lists the six files
     Appendix B registers plus the raw files the numbers come from; `GATES.md` says FAIL;
     `gate2-ids.txt` has 50 ids and `census-ids.txt` 4 756 = n_resto − n_amostrado, with the
     sha256 prefixes the manuscript prints; the rules file's file-system time precedes the
     first call (the manuscript prints both); the census output directory holds only its
     48 input batches (nothing was run). If the file-system time has changed since rc12 (a
     checkout rewrites it), that is a WARN, not a failure: the literal then rests on the
     record in `APPLY-B-rc12.md`.

Usage:  python3 parity-rc12.py              # check
        python3 parity-rc12.py --report     # per-ID numeric deltas with their justification
        python3 parity-rc12.py --self-test  # mutations in memory; each must fail a content check
Reads the two manuscripts and the artifacts named below. Writes nothing.
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
OLD = SPRINT / "B-v2-rc11.md"
NEW = SPRINT / "B-v2-rc12.md"
CENSO = SPRINT / "B-censo"
RAW = CENSO / "raw"
CENSO_OUT = Path.home() / ".paper2-verdicts" / "censo-B-20261005"
RC11 = SPRINT / "B-rc11" / "parity-rc11.py"
RC11_SHA = "c4daf8e466b70f318ae5d724c5fcee73a227444cc5bac7f7d5bf25daafd653f4"
RULES_FS_TIME = "23:13:58Z"  # literal: birth = mtime of GATE-RULES-PREDECLARED.md, read 2026-10-05

assert hashlib.sha256(RC11.read_bytes()).hexdigest() == RC11_SHA, \
    "parity-rc11.py changed: the locks carried from it are no longer the ones rc11 ran"
_spec = importlib.util.spec_from_file_location("parity_rc11", RC11)
R11 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(R11)

ART = dict(R11.ART, **{"gate2-compare": CENSO / "gate2-compare.json"})
REGISTERED = ["GATES.md", "GATE-RULES-PREDECLARED.md", "gate2-ids.txt", "census-ids.txt",
              "run_census.sh"]  # + SHA256SUMS itself
RAW_SOURCES = ["raw/gate1-calls.jsonl", "raw/cost-gate1.json", "raw/cost-gate2.json"]

ANCHORS = [
    ("ST", "rc12 prepared 2026-10-05"),
    ("CENSUS", "An attempt to restore the census, made after"),
    ("CENSUS", "**The census restoration we attempted, and why it was not run (rc12).**"),
    ("DRIFT", "**Reproducibility of the adjudication.**"),
    ("CENSUS", "Restoring the census was attempted on"),
    ("APPB", "`_sprint-2026-10-04/B-censo/GATES.md` · `_sprint-2026-10-04/B-censo/GATE-RULES-PREDECLARED.md`"),
    ("APPB", "The artifacts added in rc7, rc8, rc9, rc10, rc11 and rc12"),
    ("APPB", "files of rc12 in `B-censo/`"),
    ("B1", "| census restoration (rc12):"),
    ("CL", "*(rc12: nor has the census attempt"),
    ("CL", "**Closed, rc12 (2026-10-05): attempted, gates failed, not run.**"),
    ("CL", "**rc12: the census restoration attempted after unblinding**"),
]
LITERALS = {
    "CENSUS": {RULES_FS_TIME: "file-system birth and modification time of GATE-RULES-PREDECLARED.md (check 14)"},
    "B1": {RULES_FS_TIME: "same, in its B.1 row"},
}
# hunks whose numbers must come from the census record, not merely from rc11 or another artifact
STRICT_IDS = {"CENSUS", "DRIFT", "B1"}
CONTEXT = {
    "5556": "rc11's census declaration: stratum-B episodes outside the 395 is_error (ITT-2026-09-21 n_resto_no_corpus)",
    "800": "rc11's census declaration: the sample (ITT-2026-09-21 n_estrato_b_amostrado)",
    "1195": "rc11: episodes submitted to the panel (395 + 800)",
    "95": "the Wilson interval's level",
    "2026-10-04": "the sprint directory name in a path",
    "1": "gate number", "2": "gate number",
    "4": "section number in a B.1 cell", "7": "section number in a B.1 cell",
}
# 4(g): the census may not be said to have been run or restored
CENSUS_LOCK = [
    r"\b(?:the )?census (?:was|has been|is) (?:therefore |then |now |finally )?(?:run|restored|completed|adjudicated)\b",
    r"\brestored the census\b",
    r"\b(?:we|it) (?:ran|completed) the census\b",
]
CENSUS_NEG_OK = re.compile(r"\bcensus (?:was|has been|is) (?:therefore |then |now |finally )?not\b")
# 4(h): credential finding kept out of the manuscript (APPLY-B-rc12.md)
SECRET_LOCK = [r"xox[a-z]-", r"\bsk-[A-Za-z0-9]", r"\bcredential", r"\bSlack\b", r"\bunredacted\b",
               r"\bAKIA[0-9A-Z]{8}", r"\bgh[pousr]_[A-Za-z0-9]{8}", r"\bAIza[0-9A-Za-z_-]{8}"]


def load_census():
    c1 = json.loads((RAW / "cost-gate1.json").read_text())
    c2 = json.loads((RAW / "cost-gate2.json").read_text())
    calls = [json.loads(l) for l in (RAW / "gate1-calls.jsonl").read_text().splitlines() if l.strip()]
    rules = (CENSO / "GATE-RULES-PREDECLARED.md").read_text()
    st = (CENSO / "GATE-RULES-PREDECLARED.md").stat()
    fs = sorted({getattr(st, "st_birthtime", st.st_mtime), st.st_mtime})
    import time as _t
    return dict(
        cmp=json.loads(ART["gate2-compare"].read_text()),
        cost=round(c1["TOTAL_usd"] + c2["TOTAL_usd"], 4),
        n_calls=sum(v["calls"] for c in (c1, c2) for k, v in c.items() if isinstance(v, dict)),
        first_call=min(r["ts"] for r in calls)[11:],  # ts is taken before the request (gate_harness.py)
        rules=rules,
        rules_fs=[_t.strftime("%H:%M:%SZ", _t.gmtime(x)) for x in fs],
        gates=(CENSO / "GATES.md").read_text(),
        sums=(CENSO / "SHA256SUMS").read_text(),
        files={p: (CENSO / p).read_bytes() for p in REGISTERED + RAW_SOURCES + ["gate2-compare.json"]},
        gate2_ids=(CENSO / "gate2-ids.txt").read_text().split(),
        census_ids=(CENSO / "census-ids.txt").read_text().split(),
        out_files=sorted(str(p.relative_to(CENSO_OUT)) for p in CENSO_OUT.rglob("*") if p.is_file()),
        stab=(P2 / "STABILITY-TEST.md").read_text(),
    )


def derived_rc12(cz, itt):
    out = {}
    out[f"{cz['cost']:.2f}"] = "cost total = cost-gate1 + cost-gate2 TOTAL_usd (raw/, from the usage blocks)"
    out[str(cz["n_calls"])] = "calls = sum of `calls` in cost-gate1 and cost-gate2"
    out[cz["first_call"]] = "start of the first call = min ts of raw/gate1-calls.jsonl"
    m = re.search(r"Written (\d{4}-\d{2}-\d{2}T\d{2}:\d{2}Z)", cz["rules"])
    out[m.group(1)] = "time written in the header of GATE-RULES-PREDECLARED.md"
    out[re.search(r"agreement ≥ (0\.\d+)\*\*", cz["rules"]).group(1)] = "per-provider criterion (rules file)"
    out[re.search(r"Panel-outcome criterion: ≥ (0\.\d+)", cz["rules"]).group(1)] = "panel-outcome criterion (rules file)"
    m = re.search(r"(\d+)/(\d+) identical verdict categories", cz["rules"])
    assert "stability: 0.9900" in cz["stab"]
    out[m.group(1)] = "test-retest numerator (rules file; STABILITY-TEST.md §7 0.9900)"
    out[m.group(2)] = "test-retest denominator (rules file)"
    n_out = itt["n_resto_no_corpus"] - itt["n_estrato_b_amostrado"]
    assert len(cz["census_ids"]) == n_out
    out[str(len(cz["census_ids"]))] = "census ids = lines of census-ids.txt = n_resto − n_amostrado"
    out[str(len(cz["gate2_ids"]))] = "gate-2 ids = lines of gate2-ids.txt"
    out[re.search(r"step 1: gates \((\d{4}-\d{2}-\d{2})\)", cz["gates"]).group(1)] = "date of the attempt (GATES.md title)"
    return out


def headline_rc12(cz):
    pp = cz["cmp"]["per_provider"]
    po = cz["cmp"]["panel_outcome"]
    n = cz["cmp"]["n_episodes"]
    w = lambda x: f"[{x[0]:.2f}; {x[1]:.2f}]"  # noqa: E731
    prov = lambda p: f"{pp[p]['label_agree']}/{pp[p]['pairs_compared']} for `{p}` (Wilson 95% {w(pp[p]['label_wilson95'])})" \
        if p == "xai" else f"{pp[p]['label_agree']}/{pp[p]['pairs_compared']} for `{p}` ({w(pp[p]['label_wilson95'])})"  # noqa: E731
    flips = [c for c in po["changes"] if {c["sep"], c["new"]} == {"failure", "not_failure"}]
    assert len(flips) == 2 and flips[0]["sep"] != flips[1]["sep"], "the two F↔nf flips are no longer opposite"
    assert len(po["changes"]) - len(flips) == 2 and all("unknown" in (c["sep"], c["new"]) for c in po["changes"] if c not in flips)
    return {
        "xai": prov("xai"), "google": prov("google"), "zhipu": prov("zhipu"),
        "panel outcome": f"agreed on {po['agree']}/{n} (Wilson {w(po['wilson95'])}), which meets its own declared criterion",
        "flips": "two are `failure` ↔ `not_failure` flips in opposite directions and two involve `unknown`",
        "cost": f"US${cz['cost']:.2f} ({cz['n_calls']} calls",
        "not run": "The census was therefore not run, and the sampled design stays a declared deviation",
        "instrument change": "which adds an instrument change to the sampling deviation",
        "alias": "An id is an alias, however, and September recorded no fingerprint or snapshot",
        "order": f"created and last modified at {RULES_FS_TIME}, and the first call started at {cz['first_call']}",
        "drift §7": "the panel's verdicts drifted at the label level for two of the three families",
        "drift bound": "That bounds how reproducible the adjudication is",
        "gate2 sha": f"(sha256 `{hashlib.sha256(cz['files']['gate2-ids.txt']).hexdigest()[:8]}…`)",
        "census sha": f"(`{hashlib.sha256(cz['files']['census-ids.txt']).hexdigest()[:8]}…`)",
        "App A": f"label agreement {pp['google']['label_agree']}/{n} and {pp['zhipu']['label_agree']}/{n} for two of the three families",
        "WL25": "**Closed, rc12 (2026-10-05): attempted, gates failed, not run.**",
    }


def census_integrity(cz):
    fails = []
    listed = {}
    for line in cz["sums"].splitlines():
        h, p = line.split(None, 1)
        listed[p.strip().lstrip("./")] = h
    for p in REGISTERED + RAW_SOURCES + ["gate2-compare.json"]:
        if p not in listed:
            fails.append(f"census: {p} is not in SHA256SUMS")
        elif hashlib.sha256(cz["files"][p]).hexdigest() != listed[p]:
            fails.append(f"census: {p} does not match SHA256SUMS")
    for p, h in listed.items():
        if p not in cz["files"] and (CENSO / p).exists() and hashlib.sha256((CENSO / p).read_bytes()).hexdigest() != h:
            fails.append(f"census: {p} does not match SHA256SUMS")
        if not (CENSO / p).exists():
            fails.append(f"census: {p} listed in SHA256SUMS is missing")
    if "VERDICT: FAIL" not in cz["gates"]:
        fails.append("census: GATES.md no longer says FAIL")
    if len(cz["gate2_ids"]) != 50 or len(set(cz["gate2_ids"])) != 50:
        fails.append("census: gate2-ids.txt is not 50 distinct ids")
    if len(set(cz["census_ids"])) != len(cz["census_ids"]) or set(cz["census_ids"]) & set(cz["gate2_ids"]):
        fails.append("census: census ids have duplicates or overlap the gate-2 (sampled) ids")
    if not cz["rules_fs"][0] < cz["first_call"] or not cz["rules_fs"][-1] < cz["first_call"]:
        fails.append(f"census: rules file time {cz['rules_fs']} does not precede the first call {cz['first_call']}")
    extra = [f for f in cz["out_files"] if not re.fullmatch(r"lotes/censo-lote-\d{2}\.jsonl", f)]
    n_lotes = len(cz["out_files"]) - len(extra)
    if extra or n_lotes != 48:
        fails.append(f"census: output directory holds more than its 48 input batches ({n_lotes} batches, extra {extra[:3]})")
    return fails


def claims_rc12(new):
    fails = R11.claims(new)  # rc11 locks (a)-(f), carried unchanged
    corpo = R11.strip_struck(new[:new.find("\n## Working list")])
    flat = " ".join(corpo.split())
    for pat in CENSUS_LOCK:
        for m in re.finditer(pat, flat):
            ctx = flat[max(0, m.start() - 10):m.end() + 12]
            if CENSUS_NEG_OK.search(ctx):
                continue
            fails.append(f"claim: census presented as run or restored ({pat}): {flat[max(0, m.start() - 60):m.end() + 20]!r}")
    whole = " ".join(new.split())
    for pat in SECRET_LOCK:
        if re.search(pat, whole):
            fails.append(f"claim: credential-like string or credential finding in the manuscript ({pat})")
    return fails


def check(old, new, verbose=True, report=False, cz=None):
    cz = cz or load_census()
    fails = []
    itt = json.loads(ART["ITT-2026-09-21"].read_text())
    reg = json.loads(ART["ITT-REGISTRADO-v3"].read_text())
    chk = json.loads(ART["checks-rc10"].read_text())
    f4 = json.loads(ART["f4-w4"].read_text())
    f3 = json.loads(ART["f3-abort"].read_text())
    allowed_art = {}
    for name, p in ART.items():
        for v in R11.leaves(json.loads(p.read_text())):
            for f in R11.forms(v):
                allowed_art.setdefault(f, name)
    der = derived_rc12(cz, itt)
    census_art = {f for v in R11.leaves(cz["cmp"]) for f in R11.forms(v)}
    old_nums = R11.numbers(old)
    # 1 hunks (rc11's hunk splitter, rc12's anchors)
    R11.ANCHORS[:] = ANCHORS
    hs = R11.hunks(old, new)
    for h in hs:
        if not h["ids"]:
            fails.append(f"hunk rc11 {h['rc10']} rc12 {h['rc11']} has no ID: {h['new'][:70]!r}")
    # 2 numbers
    rep = collections.defaultdict(lambda: dict(added=[], removed=[]))
    for h in hs:
        add = R11.numbers(h["new"]) - R11.numbers(h["old"])
        rem = R11.numbers(h["old"]) - R11.numbers(h["new"])
        key = "+".join(h["ids"]) or "?"
        strict = bool(set(h["ids"]) & STRICT_IDS)
        for tok, n in sorted(add.items()):
            why = None
            lit = next((f"literal[{i}]: " + LITERALS[i][tok] for i in h["ids"] if tok in LITERALS.get(i, {})), None)
            if strict:  # census content: census sources only, then the declared context numbers
                if tok in der:
                    why = "derived: " + der[tok]
                elif tok in census_art:
                    why = "census artifact: gate2-compare.json"
                elif lit:
                    why = lit
                elif tok in CONTEXT:
                    why = "context: " + CONTEXT[tok]
            elif tok in old_nums:
                why = "rc11"
            elif tok in allowed_art:
                why = "artifact:" + allowed_art[tok]
            elif tok in der:
                why = "derived: " + der[tok]
            else:
                why = lit
            rep[key]["added"].append((tok, n, why))
            if why is None:
                fails.append(f"number '{tok}' (+{n}) added in hunk {key} (rc12 l.{h['rc11'][0]}) is not justified")
        for tok, n in sorted(rem.items()):
            rep[key]["removed"].append((tok, n))
    # 3 headlines: rc11's kept, rc12's added
    flat = " ".join(new.split())
    heads = dict(R11.headline(reg, chk, f4, f3, itt))
    heads.update({"rc12 " + k: v for k, v in headline_rc12(cz).items()})
    for k, v in heads.items():
        if " ".join(v.split()) not in flat:
            fails.append(f"headline: {k} — expected text {v!r} not found in rc12")
    # 4 claims, and where the census is reported
    fails += claims_rc12(new)
    sec4 = " ".join(new[new.find("\n## 4. Results"):new.find("\n### 4.0.1 ")].split())
    sec7 = " ".join(new[new.find("\n## 7. Threats"):new.find("\n## 8. Related")].split())
    appa = " ".join(new[new.find("\n## Appendix A"):new.find("\n## Appendix B")].split())
    dev = " ".join(heads["census deviation"].split())
    for nome, parte, marca in (("§4", sec4, dev), ("Appendix A", appa, dev),
                               ("§4", sec4, heads["rc12 not run"]), ("§7", sec7, heads["rc12 drift §7"]),
                               ("Appendix A", appa, heads["rc12 App A"])):
        if " ".join(marca.split()) not in parte:
            fails.append(f"census: {marca[:50]!r}… is not in {nome}")
    # 5 headings
    if R11.headings(old) != R11.headings(new):
        fails.append("heading: rc12 changes the heading list")
    # 6 citations, footnotes, DOIs
    for name, t in (("rc11", old), ("rc12", new)):
        body, refs = R11.body_and_refs(t)
        used = set(re.findall(r"@([A-Za-z0-9_]+)", " ".join(R11.CITE.findall(body))))
        listed = set(re.findall(r"`\[@([A-Za-z0-9_]+)\]`", refs))
        if used - listed:
            fails.append(f"citation ({name}): used but not listed: {sorted(used - listed)}")
        fm = set(re.findall(r"\[\^([^\]]+)\](?!:)", t))
        fd = set(re.findall(r"^\[\^([^\]]+)\]:", t, re.M))
        if fm - fd:
            fails.append(f"footnote ({name}): markers without definition {sorted(fm - fd)}")
    cc = lambda t: collections.Counter(re.findall(r"@([A-Za-z0-9_]+)", " ".join(R11.CITE.findall(R11.body_and_refs(t)[0]))))  # noqa: E731
    if cc(new) != cc(old):
        fails.append("citation: occurrences changed")
    if collections.Counter(R11.DOI.findall(old)) != collections.Counter(R11.DOI.findall(new)):
        fails.append("doi: DOI multiset changed")
    # 7 forbidden additions
    for pat in R11.FORBIDDEN:
        if len(re.findall(pat, new)) > len(re.findall(pat, old)):
            fails.append(f"forbidden: pattern {pat!r} added")
    # 8 SHAM-JANELA
    so, eo = R11.sham_spans(old)
    sn, en = R11.sham_spans(new)
    fails += eo + en
    if len(sn) != R11.EXPECTED_SHAM or len(so) != R11.EXPECTED_SHAM:
        fails.append(f"sham: {len(sn)} blocks in rc12 and {len(so)} in rc11, expected {R11.EXPECTED_SHAM}")
    for i, (x, y) in enumerate(zip(so, sn), 1):
        if x != y:
            fails.append(f"sham: block {i} ({y.strip()[:50]!r}…) is not byte-identical to rc11")
    # 9 REANALISE
    if R11.R_ANY.search(new):
        fails.append("reanalise: a REANALISE marker is present in rc12")
    # 10 quotes
    nq = lambda x: " ".join(x.replace("**", "").split())  # noqa: E731
    fontes = nq(old) + " " + " ".join(nq(p.read_text()) for p in R11.QUOTE_SOURCES)
    qo, qn = collections.Counter(R11.QUOTE.findall(old)), collections.Counter(R11.QUOTE.findall(new))
    for q in (qn - qo):
        if nq(q[2:-2]) not in fontes:
            fails.append(f"quote: {q[:70]!r} is not verbatim in rc11 or a declared source")
    for q in (qo - qn):
        fails.append(f"quote removed: {q[:70]!r}")
    # 11 code spans
    cos, cns = collections.Counter(R11.CODE.findall(old)), collections.Counter(R11.CODE.findall(new))
    roots = [P2, SPRINT, P2 / "out", P2.parent, R11.LASTRO, HERE, P2 / "measurement", SPRINT / "figures",
             R11.REG, CENSO, RAW]
    idsrc = "".join(p.read_text() for p in (ART["ITT-REGISTRADO-v3"], ART["checks-rc10"], ART["ITT-2026-09-21"],
                                            R11.SCRIPT, P2 / "pilot_replay.py", P2 / "PREREG-DRAFT.md",
                                            CENSO / "GATES.md", CENSO / "gate2-compare.json", CENSO / "gate_harness.py"))
    import glob
    for span in (cns - cos):
        s = span.strip()
        if re.search(r"\.(?:py|json|md|svg|png|ndjson|jsonl|sh|tgz|txt|ts)\b|/$|\.\*$|\{|SHA256SUMS$", s) and " " not in s:
            pats = [s]
            m = re.search(r"\{([^}]+)\}", s)
            if m:
                pats = [s[:m.start()] + x + s[m.end():] for x in m.group(1).split(",")]
            for pat in pats:
                pat = pat.replace("…", "*")
                if not any(glob.glob(str(r / pat)) for r in roots):
                    fails.append(f"code span: `{span}` names no file on disk")
        elif re.fullmatch(r"[a-z][a-z0-9]*(?:_[a-z0-9]+)+", s):
            if s not in idsrc:
                fails.append(f"code span: identifier `{span}` occurs in none of the named sources")
    # 12 bold balance
    noncode = re.sub(r"```.*?```", "", new, flags=re.S)
    for k, para in enumerate(re.split(r"\n\s*\n", noncode)):
        if para.count("**") % 2:
            fails.append(f"bold: odd number of ** in paragraph {k}: {para.strip()[:60]!r}")
    # 13 script integrity, carried
    fails += R11.script_integrity(**R11.load_integrity_inputs())
    # 14 census record
    fails += census_integrity(cz)
    warns = []
    if RULES_FS_TIME not in cz["rules_fs"]:
        warns.append(f"WARN rules file-system time is now {cz['rules_fs']}, not {RULES_FS_TIME} "
                     "(a checkout or copy rewrites it; the literal rests on APPLY-B-rc12.md)")
    if verbose:
        print(f"hunks: {len(hs)}, all with an ID: {all(h['ids'] for h in hs)}")
        cls = collections.Counter((t[2] or "UNJUSTIFIED").split(":")[0] for v in rep.values() for t in v["added"])
        print(f"numeric tokens added across hunks: {sum(cls.values())}; by class: {dict(cls)}")
        print(f"headings: {len(R11.headings(new))}, unchanged: {R11.headings(old) == R11.headings(new)}")
        print(f"SHAM-JANELA blocks: {len(sn)}, byte-identical to rc11: {sum(1 for x, y in zip(so, sn) if x == y)}")
        print(f"quotes added: {sum((qn - qo).values())}; code spans added: {sum((cns - cos).values())}")
        print(f"headlines checked: {len(heads)} ({len(heads) - len(headline_rc12(cz))} carried from rc11)")
        for w in warns:
            print(w)
    if report:
        for key, v in rep.items():
            print(f"\n[{key}]")
            for tok, n, why in v["added"]:
                print(f"  + {tok} x{n}  <- {why}")
            if v["removed"]:
                print("  - " + ", ".join(f"{t} x{n}" for t, n in v["removed"]))
    return fails


def main():
    old, new = OLD.read_text(encoding="utf-8"), NEW.read_text(encoding="utf-8")
    if "--report" in sys.argv:
        f = check(old, new, verbose=True, report=True)
        print("\n" + ("\n".join("FAIL " + x for x in f) or "no failures"))
        return 0
    if "--self-test" in sys.argv:
        cz = load_census()
        rep1 = lambda a, b: new.replace(a, b, 1)  # noqa: E731
        mutations = [
            ("word changed inside a SHAM-JANELA block", rep1("**Our error, stated.**", "**Our error.**")),
            ("google agreement changed", rep1("47/50 for `google`", "48/50 for `google`")),
            ("zhipu Wilson bound changed", rep1("46/50 for `zhipu` ([0.81; 0.97])", "46/50 for `zhipu` ([0.81; 0.99])")),
            ("panel outcome changed", rep1("agreed on 46/50 (Wilson", "agreed on 47/50 (Wilson")),
            ("cost changed", rep1("US$1.18 (154 calls", "US$1.81 (154 calls")),
            ("call count changed", rep1("US$1.18 (154 calls", "US$1.18 (150 calls")),
            ("first-call time changed", rep1("first call started at 23:14:49Z", "first call started at 23:14:59Z")),
            ("rules time changed", rep1("modified at 23:13:58Z", "modified at 23:13:59Z")),
            ("flip directions removed", rep1("flips in opposite directions", "flips")),
            ("alias caveat removed", rep1("An id is an alias, however, and September\nrecorded no fingerprint or snapshot, so a change of weights under the same name cannot be\nruled out. ", "")),
            ("§7 drift sentence removed", rep1("the panel's verdicts drifted at the label level for\ntwo of the three families", "the panel's verdicts were stable")),
            ("Appendix A attempt removed", rep1("(label agreement 47/50 and\n  46/50 for two of the three families, against a declared 0.99)", "")),
            ("census said to be run", rep1("The census\nwas therefore not run,", "The census\nwas therefore run,")),
            ("census said to be restored", rep1("so the census was not run\n  and the sample stays", "so we restored the census\n  and the sample stays")),
            ("credential finding mentioned", rep1("The gates cost about", "Six episodes held unredacted credential-like strings. The gates cost about")),
            ("credential-like string added", rep1("The gates cost about", "A token xoxp-abcdef was seen. The gates cost about")),
            ("gate-2 ids sha prefix changed", rep1("(sha256 `6377c80b…`)", "(sha256 `6377c80c…`)")),
            ("registered file name broken", rep1("`_sprint-2026-10-04/B-censo/run_census.sh`", "`_sprint-2026-10-04/B-censo/run-census.sh`")),
            ("working list 25 reopened", rep1("**Closed, rc12 (2026-10-05): attempted, gates failed, not run.**", "**Pending.**")),
            ("unmapped hunk with a new number", rep1("**Benchmarks compare systems on fixed tasks.**",
                                                     "We ran 4217 extra checks.\n\n**Benchmarks compare systems on fixed tasks.**")),
            ("carried: rc11 census deviation removed from §4", rep1(
                "This departs from the deposited sampling\nplan; the six-switch reanalysis does not restore the census.", "")),
            ("carried: dose lock", rep1("had no effect (§4.3).", "had no effect (§4.3). It was a property of how the denominator was computed and not of the dose.")),
            ("carried: H1a presented as rejected", rep1("and it is not rejected. Sources:", "and it is rejected. Sources:")),
            ("carried: stale 'report no cost, latency or energy'", rep1("*did*. We report action-level",
                                                                      "*did*, and report no cost, latency or energy. We report action-level")),
            ("carried: rc11 headline (stratum) changed", new.replace("+0.01867", "+0.01876")),
            ("heading renamed", rep1("## 7. Threats to validity", "## 7. Threats to validity (rc12)")),
            ("bold left unbalanced", rep1("**Reproducibility of the adjudication.** Re-run", "**Reproducibility of the adjudication. Re-run")),
        ]
        # lock mutations must be caught by the claim locks themselves, not by a headline or a number
        PELA_CLAIM = {"census said to be run", "census said to be restored", "credential finding mentioned",
                      "credential-like string added", "carried: dose lock", "carried: H1a presented as rejected",
                      "carried: stale 'report no cost, latency or energy'"}
        ok = True
        for name, mutated in mutations:
            assert mutated != new, f"mutation did not apply: {name}"
            if name in PELA_CLAIM:
                f, via = claims_rc12(mutated), "claim locks only"
            else:
                # a catch by "hunk has no ID" alone does not count: it fires for any edit
                f, via = [x for x in check(old, mutated, verbose=False, cz=cz) if "has no ID" not in x], "full check"
            print(f"mutation [{name}] ({via}): {'CAUGHT' if f else 'MISSED'}" + (f" -> {f[0][:140]}" if f else ""))
            ok &= bool(f)
        integ = [
            ("GATES.md says PASS", dict(cz, gates=cz["gates"].replace("VERDICT: FAIL", "VERDICT: PASS")), "no longer says FAIL"),
            ("registered file altered", dict(cz, files=dict(cz["files"], **{"run_census.sh": cz["files"]["run_census.sh"] + b"\n"})),
             "does not match SHA256SUMS"),
            ("census output written", dict(cz, out_files=cz["out_files"] + ["censo-B-PRIMARIO-3fam.jsonl"]), "more than its 48"),
            ("rules written after the first call", dict(cz, rules_fs=["23:15:30Z"]), "does not precede"),
            ("census ids overlap the sample", dict(cz, census_ids=cz["census_ids"] + cz["gate2_ids"][:1]), "overlap"),
        ]
        for name, kz, esperado in integ:
            f = [x for x in census_integrity(kz) if esperado in x]
            print(f"mutation [{name}] (census record): {'CAUGHT' if f else 'MISSED'}" + (f" -> {f[0][:140]}" if f else ""))
            ok &= bool(f)
        base = check(old, new, verbose=False, cz=cz)
        print(f"unmutated rc12: {'PASS' if not base else 'FAIL'}" + (f" -> {base}" if base else ""))
        print(f"mutations: {len(mutations) + len(integ)}")
        return 0 if ok and not base else 1
    fails = check(old, new)
    for f in fails:
        print("FAIL", f)
    print("PARITY: PASS" if not fails else f"PARITY: FAIL ({len(fails)})")
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
