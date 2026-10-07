#!/usr/bin/env python3
"""Parity check B-v2-rc12.md -> B-v2-rc13.md (Paper B, sprint 2026-10-04; rc13 2026-10-05).

rc13 applies the Fable review of rc12 (`REVIEW-B-rc12-2026-10-05.md`, MEDIUM-1/2, LOW-1..5),
each finding verified before it was applied (`APPLY-B-rc13.md`), and removes the personal
absolute paths from the four scripts in `B-censo/`. No analysis changes; no estimate moves.

Hunks (difflib on lines) must each carry an ID, assigned by an anchor substring of the rc13 hunk:
    ST status header · COMMIT the three commitments not kept (abstract, §9) · UNC the abstract's
    uncertainty sentence · CENSUS §4 (header time, noise property) · LAYERS §4.1.2 · REPRO §7 ·
    APPA Appendix A count · APPB / B1 appendices · CL working list and changelog.

Checks (exit 1 if any fails):
  1. hunks: every hunk has an ID.
  2. numbers: every numeric token ADDED is (a) in rc12, or (b) a leaf of an artifact read at run
     time (rc11's artifacts, `gate2-compare.json`), or (c) DERIVED at run time (rc12's census
     derivations; rc13's: the second call's start, the rules' Wilson bounds and pair count,
     1 − 0.99^150 and 0.99^150, the number of panel-outcome changes, the HT weight 5 556 / 800).
     Hunks with census content (CENSUS, LAYERS, B1) take their numbers from the census record,
     the HT weight or declared context only, never merely from rc12.
  3. headlines: rc12's (minus the §7 sentence rc13 rewrites, a justified delta) and rc11's
     carried; rc13's, formatted from the census record at run time, present.
  4. claims: rc12's locks carried through rc12's own `claims_rc12` (rc11's (a)-(f), 4(g) census
     not run or restored, 4(h) no credential or credential finding); NEW (i) no "drift" in the
     body (the §7 finding is non-reproduction, cause unknown); NEW (j) the abstract and §9 say
     three commitments, never two, and §4.1.2 says three layers, never two; NEW (k) the census
     and its attempt are reported in the abstract and §9 as well as §4, §7 and Appendix A;
     NEW (l) the Appendix A count word equals the number of unstruck items of its list.
  5. headings identical. 6. citations, footnotes, DOIs unchanged. 7. no host, IP or personal
     path added. 8. SHAM-JANELA: 10 blocks byte-identical to rc12. 9. no REANALISE marker.
 10. quotes added are verbatim in rc12 or a declared source (rc13 adds none). 11. code spans
     resolve. 12. bold balance. 13. script integrity, carried from rc11 (through rc12).
 14. census record, carried from rc12 (`census_integrity`): SHA256SUMS verifies, GATES.md FAIL,
     ids, rules before the first call, census output directory holds only its 48 batches.
 15. NEW, B-censo paths: (a) no `/Users/` or home path in any B-censo file outside `raw/`;
     (b) `census-pins.sha256` verifies; (c) bridge: each of the four scripts, with its derived
     path line put back to the absolute literal of this checkout, has the sha256 it had when the
     gates ran (`GATES.md` for the harness and the tools, rc12's `SHA256SUMS` for the other two),
     so the edit touched those lines only. The bridge needs this checkout's path to be the one
     the gates ran from (its sha256 is pinned, the path itself is not written here); elsewhere
     it is a WARN. (d) `B-registered/RESULTADO-v3.md`: with rc13's correction reverted it has
     the bytes it had before rc13 (sha256 pinned), so only that sentence changed and no number.

Usage:  python3 parity-rc13.py | --report | --self-test     Reads; writes nothing.
"""
import collections
import glob
import hashlib
import importlib.util
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPRINT = HERE.parent
P2 = SPRINT.parent
OLD = SPRINT / "B-v2-rc12.md"
NEW = SPRINT / "B-v2-rc13.md"
CENSO = SPRINT / "B-censo"
RAW = CENSO / "raw"
RESULTADO = SPRINT / "B-registered" / "RESULTADO-v3.md"
RC12 = SPRINT / "B-rc12" / "parity-rc12.py"
RC12_SHA = "94c03a163a32f8046e14278253560c41b771113efb8bb65758fdec3a1a3702ee"

assert hashlib.sha256(RC12.read_bytes()).hexdigest() == RC12_SHA, \
    "parity-rc12.py changed: the locks carried from it are no longer the ones rc12 ran"
_spec = importlib.util.spec_from_file_location("parity_rc12", RC12)
R12 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(R12)
R11 = R12.R11

# ---- 15: the gate-time bytes of the four scripts and of RESULTADO-v3.md
GATE_SHA = {  # GATES.md "Census" table (harness, tools); rc12 SHA256SUMS (the other two)
    "gate_harness.py": "3b0a1d4b9e2c992c52b1259034958e172973a557c995aeda56970cc3b1254bf6",
    "census_tools.py": "6f6f9a6d4d9358f67ebac068362f24c87a33bdc8518b954304cb8889556a1fa6",
    "compare_gate2.py": "ba8527c88da8d5ccd903c8d9fbc1cc08d733005e9afb6fa6d4ba8cda29da3851",
    "run_census.sh": "97bcaa8a563eba21d54b8acd7db9dc00e952e364949f1d56da8b8d43bfc979ab",
}
# sha256 of the absolute path of paper2-interventional/ the gates ran from (the path is not written here)
GATE_P2_SHA = "be2db7553dafecbec4f73cb3d91c1bf7552fdad1604124492302949ba240a672"
DERIVED_LINES = {  # current line -> template of the gate-time line ({P2} = absolute path)
    "gate_harness.py": [('P2 = Path(__file__).resolve().parents[2]  # paper2-interventional/, two levels above B-censo/',
                         'P2 = Path("{P2}")')],
    "census_tools.py": [('P2 = Path(__file__).resolve().parents[2]  # paper2-interventional/, two levels above B-censo/',
                         'P2 = Path("{P2}")')],
    "compare_gate2.py": [('sys.path.insert(0, str(Path(__file__).resolve().parents[2]))  # paper2-interventional/',
                          'sys.path.insert(0, "{P2}")')],
    "run_census.sh": [('B=$(cd "$(dirname "$0")" && pwd)   # this directory, B-censo/', 'B={P2}/_sprint-2026-10-04/B-censo'),
                      ('R=$(cd "$B/../.." && pwd)          # paper2-interventional/', 'R={P2}')],
}
RESULTADO_PRE_SHA = "f3c73483732e901132ccd02bfd3486b25dc158724ad29b75d741e3aaacb35db4"
RESULTADO_OLD = ("control session: no within-stratum contrast is estimable; they are listed, and the with/without\n"
                 "sensitivity is the registered way to see their weight.")
RESULTADO_NEW = ("control session: no within-stratum inferential contrast (interval or test) is estimable, and H1c\n"
                 "cannot be contrasted because control has no opportunity; the descriptive per-hour differences\n"
                 "(6.00 / 321.43 and 139.96 / 321.43 in treatment against 0 / 54.00 in control) are given in the\n"
                 "manuscript (§4). They are listed, and the with/without sensitivity is the registered way to see\n"
                 "their weight. *(Corrected 2026-10-05, rc13: this sentence read \"no within-stratum contrast is\n"
                 "estimable\", which the descriptive differences reported since rc11 contradict. No number\n"
                 "changed.)*")

ANCHORS = [
    ("ST", "rc13\n> prepared 2026-10-05 (review of rc12 applied"),
    ("ST", "not kept, in the abstract and §9, and the panel's run-to-run variation is a third layer of"),
    ("UNC", "nor re-adjudicates the episodes, whose labels did not all reproduce when"),
    ("COMMIT", "Three commitments made before the seed were not kept."),
    ("COMMIT", "(§3.0). The second, the replacement of the declared assignment rule"),
    ("COMMIT", "third is in the deposit: PREREG §3 locked census adjudication of the live study"),
    ("COMMIT", "Three further commitments made"),
    ("COMMIT", "the deposited census of the live study (PREREG"),
    ("CENSUS", "rounded and, read literally, falls after the first call"),
    ("CENSUS", "The rules declared in advance that"),
    ("LAYERS", "There are three layers of randomness the estimate inherits"),
    ("LAYERS", "The third was measured in rc12"),
    ("REPRO", "did not reproduce at the label"),
    ("APPA", "~~Thirteen~~ Twelve"),
    ("APPB", "rc13 corrected one sentence of `RESULTADO-v3.md`"),
    ("APPB", "rc13 replaced the absolute personal paths"),
    ("B1", "| gate-2 rules, declared noise property (rc13)"),
    ("CL", "(rc13: rc12, which contains all of the above"),
    ("CL", "**rc13: review of rc12 applied**"),
]
STRICT_IDS = {"CENSUS", "LAYERS", "B1"}
CONTEXT = {
    "4": "section number (§4)", "7": "section number (§7)", "12": "rc12, the version that measured it",
    "2026-10-04": "the sprint directory name in a path",
    "800": "stratum-B sample (ITT-2026-09-21 n_estrato_b_amostrado)",
    "5556": "stratum-B episodes outside is_error (ITT-2026-09-21 n_resto_no_corpus)",
}
# 4(i): the §7 finding is non-reproduction of unknown cause, not drift
DRIFT_LOCK = re.compile(r"\bdrift(?:ed|s|ing)?\b", re.I)
# 4(j): counts that rc13 corrected
COUNT_LOCK = [("Abstract", r"\bTwo commitments made before the seed\b"),
              ("§9", r"\bTwo further commitments made\b"), ("§9", r"\bwe report both here for the first time\b"),
              ("§4.1.2", r"\btwo layers of randomness\b"), ("§4.1.2", r"\bwith the second frozen\b")]
WORDS = {w: i for i, w in enumerate("zero one two three four five six seven eight nine ten eleven twelve "
                                     "thirteen fourteen fifteen".split())}


def section(text, start, end):
    i = text.find(start)
    j = text.find(end, i + 1)
    return text[i:j] if i >= 0 and j > i else ""


def load_rc13():
    cz = R12.load_census()
    calls = sorted(json.loads(l)["ts"][11:] for l in (RAW / "gate1-calls.jsonl").read_text().splitlines() if l.strip())
    cz["second_call"] = calls[1]
    rules = cz["rules"]
    m = re.search(r"99/100 identical verdict categories \(Wilson 95% \[(0\.\d+); (0\.\d+)\]\)", rules)
    cz["stab_wilson"] = (m.group(1), m.group(2))
    cz["n_pairs"] = int(re.search(r"chance that (\d+)\s+pairs show zero changes", rules).group(1))
    cz["p0"] = float(re.search(r"agreement ≥ (0\.\d+)\*\*", rules).group(1))
    assert re.search(r"0\.99\^150 ≈ 22%", rules), "rules no longer declare 0.99^150 ≈ 22%"
    assert re.search(r"## Gate 1: model identity \(2026-10-05 " + re.escape(calls[1][:-1]) + r"–", cz["gates"]), \
        "GATES.md no longer dates gate 1 from the second call"
    itt = json.loads(R12.ART["ITT-2026-09-21"].read_text())
    cz["n_resto"], cz["n_s"] = itt["n_resto_no_corpus"], itt["n_estrato_b_amostrado"]
    cz["w_ht"] = cz["n_resto"] / cz["n_s"]
    return cz


def derived_rc13(cz):
    out = {}
    out[cz["second_call"]] = "start of the second call (raw/gate1-calls.jsonl), where GATES.md dates gate 1"
    out[cz["stab_wilson"][0]] = "Wilson lower bound of the 99/100 test-retest (rules file)"
    out[cz["stab_wilson"][1]] = "Wilson upper bound of the 99/100 test-retest (rules file)"
    out[str(cz["n_pairs"])] = "pairs over which the 0.99 point criterion must show zero changes (rules file)"
    q = cz["p0"] ** cz["n_pairs"]
    out[f"{q:.2f}"] = f"0.99^{cz['n_pairs']} = {q:.4f}, the chance of zero changes (rules file: ≈ 22%)"
    out[f"{round(100 * (1 - q))}"] = f"1 − 0.99^{cz['n_pairs']} = {1 - q:.4f}, failure on noise alone"
    out[str(len(cz["cmp"]["panel_outcome"]["changes"]))] = "panel-outcome changes (gate2-compare.json)"
    out[f"{cz['w_ht']:.3f}"] = "Horvitz-Thompson weight n_resto / n_amostrado (ITT-2026-09-21)"
    out[f"{cz['p0']:.2f}"] = "per-provider criterion (rules file)"
    return out


def headline_rc13(cz):
    pp, po, n = cz["cmp"]["per_provider"], cz["cmp"]["panel_outcome"], cz["cmp"]["n_episodes"]
    q = cz["p0"] ** cz["n_pairs"]
    flips = [c for c in po["changes"] if {c["sep"], c["new"]} == {"failure", "not_failure"}]
    assert len(flips) == 2 and flips[0]["sep"] != flips[1]["sep"]
    return {
        "abstract three": "Three commitments made before the seed were not kept.",
        "abstract second": "The second, the replacement of the declared assignment rule",
        "abstract third": "The third is in the deposit: PREREG §3 locked census adjudication of the live study",
        "abstract alike": f"a hash-ordered sample of {cz['n_s']} of the {cz['n_resto'] // 1000} {cz['n_resto'] % 1000:03d} "
                          f"other episodes, weighted by {cz['w_ht']:.3f}, in the registered and the sensitivity analysis "
                          "alike (§4)",
        "abstract gate": f"two of the three panel families returned {pp['google']['label_agree']}/{n} and "
                         f"{pp['zhipu']['label_agree']}/{n} identical labels against a declared {cz['p0']:.2f}, so the "
                         "sample stays a declared deviation (§4, §7)",
        "abstract unc": "it neither re-draws the stratum-B sample nor re-adjudicates the episodes",
        "§9 three": "Three further commitments made before the seed were not kept, and we report all three here "
                    "for the first time",
        "§9 census": f"which a post-unblinding attempt could not restore because the panel's labels did not reproduce "
                     f"at the declared {cz['p0']:.2f} (§4, §7)",
        "§4 header time": "is rounded and, read literally, falls after the first call; it is not evidence of the "
                          "order, which rests on the file-system creation time alone, and a checkout rewrites that time",
        "§4 second call": f"(`GATES.md` also dates gate 1 from {cz['second_call']}, the start of the second call.)",
        "§4 noise": f"would fail on noise alone about {round(100 * (1 - q))}% of the time if each pair truly agreed with "
                    f"probability {cz['p0']:.2f} ({cz['p0']:.2f}^{cz['n_pairs']} ≈ {q:.2f} is the chance of zero changes)",
        "§4 stab wilson": f"(99/100, Wilson [{cz['stab_wilson'][0]}; {cz['stab_wilson'][1]}], with a",
        "§4 not that case": "both point estimates lie below the lower bound of the 99/100 measurement, so this "
                            "failure is not that case",
        "§4.1.2 three": "There are three layers of randomness the estimate inherits",
        "§4.1.2 frozen": "The cluster bootstrap resamples the first with the other two frozen.",
        "§4.1.2 changes": f"changed {len(po['changes'])} panel outcomes, two of them `failure` ↔ `not_failure` in "
                          "opposite directions",
        "§4.1.2 weight": f"enters (failures, and repeats where the episode is one) by {cz['w_ht']:.3f}",
        "§4.1.2 none": "The September labels are held fixed in every interval, so this variation is in none of them",
        "§7 not reproduce": "the panel's verdicts did not reproduce at the label level for two of the three families",
        "§7 cause": "whether that is non-determinism under the same model id or a changed model, the record cannot say",
        "§7 interval": "no interval includes that variation (§4.1.2)",
        "App A count": "~~Thirteen~~ Twelve (the struck item below is no longer a deviation)",
    }


def appa_count(new):
    appa = section(new, "\n## Appendix A", "\n## Appendix B")
    m = re.search(r"~~Twelve~~ ~~Thirteen~~ (\w+) \(the struck item below is no longer a deviation\) that a reader", appa)
    if not m:
        return ["App A: count sentence not found"]
    lst = appa[m.end():appa.find("\n\nThe two items where", m.end())]
    items = re.split(r"\n- ", "\n" + lst.strip())[1:]
    live = [x for x in items if not x.lstrip().startswith("~~")]
    want = WORDS.get(m.group(1).lower())
    return [] if want == len(live) else [f"App A: the count word says {m.group(1)}, the list has {len(live)} unstruck items "
                                         f"of {len(items)}"]


def claims_rc13(new, cz):
    fails = R12.claims_rc12(new)  # rc11 (a)-(f), 4(g), 4(h), carried
    body = R11.strip_struck(new[:new.find("\n## Working list")])
    flat = " ".join(body.split())
    for m in DRIFT_LOCK.finditer(flat):
        ctx = flat[max(0, m.start() - 60):m.end() + 40]
        fails.append(f"claim: 'drift' in the body (the §7 finding is non-reproduction, cause unknown): {ctx!r}")
    parts = {"Abstract": section(new, "\n## Abstract", "\n## 1. "), "§9": section(new, "\n## 9. ", "\n## References"),
             "§4.1.2": section(new, "\n### 4.1.2 ", "\n### 4.2 ")}
    for nome, pat in COUNT_LOCK:
        if re.search(pat, " ".join(R11.strip_struck(parts[nome]).split())):
            fails.append(f"claim: {nome} still says {pat!r}")
    # (k) census and its attempt in the abstract and §9 (as well as §4, §7, App. A, checked in check())
    ab = " ".join(parts["Abstract"].split())
    s9 = " ".join(parts["§9"].split())
    for nome, txt, marks in (("Abstract", ab, ["census adjudication of the live study", "An attempt to restore the census"]),
                             ("§9", s9, ["the deposited census of the live study", "post-unblinding attempt"])):
        for mk in marks:
            if mk not in txt:
                fails.append(f"census: {mk!r} is not in the {nome}")
    fails += appa_count(new)
    return fails


# ---------------------------------------------------------------- 15: B-censo paths and bridges
def load_paths():
    files = {}
    for p in sorted(CENSO.rglob("*")):
        rel = p.relative_to(CENSO)
        if p.is_file() and rel.parts[0] != "raw" and "__pycache__" not in rel.parts:  # bytecode: gitignored
            files[str(rel)] = p.read_bytes()
    return dict(files=files, p2=str(P2), resultado=RESULTADO.read_bytes())


def paths_integrity(st):
    fails, warns = [], []
    home = str(Path.home())
    for rel, b in st["files"].items():
        t = b.decode("utf-8", "replace")
        if "/Users/" in t or home in t:
            fails.append(f"paths: {rel} holds an absolute personal path")
    # (b) census-pins.sha256 verifies (paths relative to B-censo/)
    for line in st["files"]["census-pins.sha256"].decode().splitlines():
        h, p = line.split(None, 1)
        q = (CENSO / p.strip()).resolve()
        got = st["files"].get(p.strip()) if p.strip() in st["files"] else (q.read_bytes() if q.exists() else None)
        if got is None or hashlib.sha256(got).hexdigest() != h:
            fails.append(f"paths: census-pins.sha256 does not verify {p.strip()}")
    # (c) bridge to the gate-time bytes
    same_path = hashlib.sha256(st["p2"].encode()).hexdigest() == GATE_P2_SHA
    for name, lines in DERIVED_LINES.items():
        t = st["files"][name].decode()
        for cur, tpl in lines:
            if t.count(cur) != 1:
                fails.append(f"paths: {name} no longer has its derived-path line {cur[:40]!r}")
            t = t.replace(cur, tpl.format(P2=st["p2"]))
        if hashlib.sha256(t.encode()).hexdigest() != GATE_SHA[name]:
            msg = f"paths: {name} with its path line reverted is not the gate-time file ({GATE_SHA[name][:8]}…)"
            (fails if same_path else warns).append(msg if same_path else "WARN " + msg +
                                                  " — this checkout is not the path the gates ran from")
    # (d) RESULTADO-v3.md: only the corrected sentence changed
    r = st["resultado"].decode()
    if r.count(RESULTADO_NEW) != 1 or RESULTADO_OLD in r:
        fails.append("paths: RESULTADO-v3.md does not carry the rc13 correction exactly once")
    elif hashlib.sha256(r.replace(RESULTADO_NEW, RESULTADO_OLD).encode()).hexdigest() != RESULTADO_PRE_SHA:
        fails.append("paths: RESULTADO-v3.md with the correction reverted is not its pre-rc13 file")
    return fails, warns


# ---------------------------------------------------------------- the check
def check(old, new, verbose=True, report=False, cz=None, st=None):
    cz = cz or load_rc13()
    st = st or load_paths()
    fails = []
    itt = json.loads(R12.ART["ITT-2026-09-21"].read_text())
    reg = json.loads(R12.ART["ITT-REGISTRADO-v3"].read_text())
    chk = json.loads(R12.ART["checks-rc10"].read_text())
    f4 = json.loads(R12.ART["f4-w4"].read_text())
    f3 = json.loads(R12.ART["f3-abort"].read_text())
    allowed_art = {}
    for name, p in R12.ART.items():
        for v in R11.leaves(json.loads(p.read_text())):
            for f in R11.forms(v):
                allowed_art.setdefault(f, name)
    der = dict(R12.derived_rc12(cz, itt))
    der.update(derived_rc13(cz))
    census_art = {f for v in R11.leaves(cz["cmp"]) for f in R11.forms(v)}
    old_nums = R11.numbers(old)
    # 1 hunks
    R11.ANCHORS[:] = ANCHORS
    hs = R11.hunks(old, new)
    for h in hs:
        if not h["ids"]:
            fails.append(f"hunk rc12 {h['rc10']} rc13 {h['rc11']} has no ID: {h['new'][:70]!r}")
    # 2 numbers
    rep = collections.defaultdict(lambda: dict(added=[], removed=[]))
    for h in hs:
        add = R11.numbers(h["new"]) - R11.numbers(h["old"])
        rem = R11.numbers(h["old"]) - R11.numbers(h["new"])
        key = "+".join(h["ids"]) or "?"
        strict = bool(set(h["ids"]) & STRICT_IDS)
        for tok, n in sorted(add.items()):
            if strict:
                why = ("derived: " + der[tok]) if tok in der else ("census artifact: gate2-compare.json" if tok in census_art
                                                                  else ("context: " + CONTEXT[tok] if tok in CONTEXT else None))
            elif tok in old_nums:
                why = "rc12"
            elif tok in der:
                why = "derived: " + der[tok]
            elif tok in allowed_art:
                why = "artifact:" + allowed_art[tok]
            else:
                why = ("context: " + CONTEXT[tok]) if tok in CONTEXT else None
            rep[key]["added"].append((tok, n, why))
            if why is None:
                fails.append(f"number '{tok}' (+{n}) added in hunk {key} (rc13 l.{h['rc11'][0]}) is not justified")
        for tok, n in sorted(rem.items()):
            rep[key]["removed"].append((tok, n))
    # 3 headlines: rc11's and rc12's carried (minus the rewritten §7 sentence), rc13's present
    flat = " ".join(new.split())
    heads = dict(R11.headline(reg, chk, f4, f3, itt))
    heads.update({"rc12 " + k: v for k, v in R12.headline_rc12(cz).items() if k != "drift §7"})
    heads.update({"rc13 " + k: v for k, v in headline_rc13(cz).items()})
    for k, v in heads.items():
        if " ".join(v.split()) not in flat:
            fails.append(f"headline: {k} — expected text {v!r} not found in rc13")
    # 4 claims, and where the census is reported
    fails += claims_rc13(new, cz)
    sec4 = " ".join(section(new, "\n## 4. Results", "\n### 4.0.1 ").split())
    sec7 = " ".join(section(new, "\n## 7. Threats", "\n## 8. Related").split())
    appa = " ".join(section(new, "\n## Appendix A", "\n## Appendix B").split())
    dev = " ".join(heads["census deviation"].split())
    for nome, parte, marca in (("§4", sec4, dev), ("Appendix A", appa, dev), ("§4", sec4, heads["rc12 not run"]),
                               ("§7", sec7, heads["rc13 §7 not reproduce"]), ("Appendix A", appa, heads["rc12 App A"])):
        if " ".join(marca.split()) not in parte:
            fails.append(f"census: {marca[:50]!r}… is not in {nome}")
    # 5 headings
    if R11.headings(old) != R11.headings(new):
        fails.append("heading: rc13 changes the heading list")
    # 6 citations, footnotes, DOIs
    for name, t in (("rc12", old), ("rc13", new)):
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
        fails.append(f"sham: {len(sn)} blocks in rc13 and {len(so)} in rc12, expected {R11.EXPECTED_SHAM}")
    for i, (x, y) in enumerate(zip(so, sn), 1):
        if x != y:
            fails.append(f"sham: block {i} ({y.strip()[:50]!r}…) is not byte-identical to rc12")
    # 9 REANALISE
    if R11.R_ANY.search(new):
        fails.append("reanalise: a REANALISE marker is present in rc13")
    # 10 quotes
    nq = lambda x: " ".join(x.replace("**", "").split())  # noqa: E731
    fontes = nq(old) + " " + " ".join(nq(p.read_text()) for p in R11.QUOTE_SOURCES)
    qo, qn = collections.Counter(R11.QUOTE.findall(old)), collections.Counter(R11.QUOTE.findall(new))
    for q in (qn - qo):
        if nq(q[2:-2]) not in fontes:
            fails.append(f"quote: {q[:70]!r} is not verbatim in rc12 or a declared source")
    for q in (qo - qn):
        fails.append(f"quote removed: {q[:70]!r}")
    # 11 code spans
    cos, cns = collections.Counter(R11.CODE.findall(old)), collections.Counter(R11.CODE.findall(new))
    roots = [P2, SPRINT, P2 / "out", P2.parent, R11.LASTRO, HERE, P2 / "measurement", SPRINT / "figures",
             R11.REG, CENSO, RAW]
    idsrc = "".join(p.read_text() for p in (R12.ART["ITT-REGISTRADO-v3"], R12.ART["checks-rc10"], R12.ART["ITT-2026-09-21"],
                                            R11.SCRIPT, P2 / "pilot_replay.py", P2 / "PREREG-DRAFT.md",
                                            CENSO / "GATES.md", CENSO / "gate2-compare.json", CENSO / "gate_harness.py"))
    for span in (cns - cos):
        s = span.strip()
        if re.search(r"\.(?:py|json|md|svg|png|ndjson|jsonl|sh|tgz|txt|ts|sha256)\b|/$|\.\*$|\{|SHA256SUMS$", s) and " " not in s:
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
    # 13 script integrity (rc11), 14 census record (rc12), 15 paths (rc13)
    fails += R11.script_integrity(**R11.load_integrity_inputs())
    fails += R12.census_integrity(cz)
    f15, warns = paths_integrity(st)
    fails += f15
    if R12.RULES_FS_TIME not in cz["rules_fs"]:
        warns.append(f"WARN rules file-system time is now {cz['rules_fs']}, not {R12.RULES_FS_TIME} "
                     "(a checkout rewrites it; the literal rests on APPLY-B-rc12.md)")
    if verbose:
        print(f"hunks: {len(hs)}, all with an ID: {all(h['ids'] for h in hs)}")
        cls = collections.Counter((t[2] or "UNJUSTIFIED").split(":")[0] for v in rep.values() for t in v["added"])
        print(f"numeric tokens added across hunks: {sum(cls.values())}; by class: {dict(cls)}")
        print(f"headings: {len(R11.headings(new))}, unchanged: {R11.headings(old) == R11.headings(new)}")
        print(f"SHAM-JANELA blocks: {len(sn)}, byte-identical to rc12: {sum(1 for x, y in zip(so, sn) if x == y)}")
        print(f"quotes added: {sum((qn - qo).values())}; code spans added: {sum((cns - cos).values())}")
        print(f"headlines checked: {len(heads)} ({len(headline_rc13(cz))} new in rc13)")
        print(f"B-censo files outside raw/ scanned for personal paths: {len(st['files'])}")
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
        cz, st = load_rc13(), load_paths()
        rep1 = lambda a, b: new.replace(a, b, 1)  # noqa: E731
        mutations = [
            # rc13 content
            ("abstract back to two commitments", rep1("Three commitments made before the seed", "Two commitments made before the seed")),
            ("§9 back to two commitments", rep1("Three further commitments made", "Two further commitments made")),
            ("§4.1.2 back to two layers", rep1("There are three layers of randomness the estimate inherits", "There are two layers of randomness")),
            ("§7 says drifted", rep1("verdicts did not reproduce at the label\nlevel", "verdicts drifted at the label\nlevel")),
            ("abstract census sentence removed", rep1("The\nthird is in the deposit: PREREG §3 locked census adjudication of the live study, and the\n", "The\n")),
            ("abstract gate numbers changed", rep1("returned 47/50 and 46/50 identical labels", "returned 48/50 and 46/50 identical labels")),
            ("§9 census item removed", rep1("; and the deposited census of the live study (PREREG\n§3)", "; and (PREREG\n§3)")),
            ("bootstrap frozen sentence reverted", rep1("with the other two frozen.", "with the second frozen.")),
            ("panel-outcome changes miscounted", rep1("changed 4 panel outcomes", "changed 3 panel outcomes")),
            ("HT weight changed", rep1("(failures, and repeats where the episode is one) by 6.945", "(failures, and repeats where the episode is one) by 6.94")),
            ("§7 cause clause removed", rep1(" whether that is non-determinism under the same model id or a changed model, the\nrecord cannot say.", "")),
            ("noise share changed", rep1("about 78% of the time", "about 87% of the time")),
            ("0.99^150 changed", rep1("0.99^150 ≈ 0.22", "0.99^150 ≈ 0.32")),
            ("second-call time changed", rep1("gate 1 from 23:14:52Z", "gate 1 from 23:14:55Z")),
            ("99/100 Wilson bound changed", rep1("Wilson [0.9455; 0.9982], with a", "Wilson [0.9455; 0.9928], with a")),
            ("header time said to be the order", rep1("it is not evidence of the order,", "it confirms the order,")),
            ("Appendix A count back to Thirteen", rep1("~~Thirteen~~ Twelve (the struck item below is no longer a deviation)",
                                                      "~~Thirteen~~ Thirteen (the struck item below is no longer a deviation)")),
            ("abstract uncertainty sentence reverted", rep1("it neither re-draws the\nstratum-B sample nor re-adjudicates the episodes, whose labels did not all reproduce when\nre-run; §4.1.2)",
                                                            "it does not re-draw the\nstratum-B sample)")),
            # carried from rc12 and rc11
            ("carried rc12: census said to be run", rep1("The census\nwas therefore not run,", "The census\nwas therefore run,")),
            ("carried rc12: credential finding mentioned", rep1("The gates cost about", "Six episodes held unredacted credential-like strings. The gates cost about")),
            ("carried rc12: google agreement changed", rep1("47/50 for `google`", "48/50 for `google`")),
            ("carried rc11: H1a presented as rejected", rep1("and it is not rejected. Sources:", "and it is rejected. Sources:")),
            ("carried rc11: rc11 headline (stratum) changed", new.replace("+0.01867", "+0.01876")),
            ("SHAM-JANELA block changed", rep1("**Our error, stated.**", "**Our error.**")),
            ("personal path added", rep1("The gates cost about", "See /Users/someone/x. The gates cost about")),
            ("unmapped hunk with a new number", rep1("**Benchmarks compare systems on fixed tasks.**",
                                                     "We ran 4217 extra checks.\n\n**Benchmarks compare systems on fixed tasks.**")),
            ("heading renamed", rep1("## 7. Threats to validity", "## 7. Threats to validity (rc13)")),
        ]
        PELA_CLAIM = {"abstract back to two commitments", "§9 back to two commitments", "§4.1.2 back to two layers",
                      "§7 says drifted", "abstract census sentence removed", "§9 census item removed",
                      "Appendix A count back to Thirteen", "carried rc12: census said to be run",
                      "carried rc12: credential finding mentioned", "carried rc11: H1a presented as rejected"}
        ok = True
        for name, mutated in mutations:
            assert mutated != new, f"mutation did not apply: {name}"
            if name in PELA_CLAIM:
                f, via = claims_rc13(mutated, cz), "claim locks only"
            else:
                f, via = [x for x in check(old, mutated, verbose=False, cz=cz, st=st) if "has no ID" not in x], "full check"
            print(f"mutation [{name}] ({via}): {'CAUGHT' if f else 'MISSED'}" + (f" -> {f[0][:140]}" if f else ""))
            ok &= bool(f)
        F = st["files"]
        integ = [
            ("absolute path put back in run_census.sh", dict(st, files=dict(F, **{"run_census.sh": F["run_census.sh"].replace(
                b'B=$(cd "$(dirname "$0")" && pwd)', ("B=" + str(Path.home()) + "/x").encode())})), "personal path"),
            ("home path in a new B-censo note", dict(st, files=dict(F, **{"NOTE.md": ("see " + str(Path.home()) + "/y\n").encode()})), "personal path"),
            ("script changed beyond its path line", dict(st, files=dict(F, **{"census_tools.py": F["census_tools.py"].replace(
                b'"zhipu": (1.40, 0.26, 4.40)', b'"zhipu": (1.40, 0.26, 4.41)')})), "not the gate-time file"),
            ("census-pins.sha256 stale", dict(st, files=dict(F, **{"gate_harness.py": F["gate_harness.py"] + b"\n"})), "census-pins.sha256 does not verify"),
            ("RESULTADO-v3 number changed", dict(st, resultado=st["resultado"].replace(b"139.96 weighted opportunities", b"139.69 weighted opportunities")),
             "pre-rc13 file"),
            ("RESULTADO-v3 correction reverted", dict(st, resultado=st["resultado"].decode().replace(RESULTADO_NEW, RESULTADO_OLD).encode()),
             "carry the rc13 correction"),
        ]
        for name, kst, esperado in integ:
            f = [x for x in paths_integrity(kst)[0] if esperado in x]
            print(f"mutation [{name}] (paths): {'CAUGHT' if f else 'MISSED'}" + (f" -> {f[0][:140]}" if f else ""))
            ok &= bool(f)
        r12 = [("GATES.md says PASS", dict(cz, gates=cz["gates"].replace("VERDICT: FAIL", "VERDICT: PASS")), "no longer says FAIL"),
               ("census output written", dict(cz, out_files=cz["out_files"] + ["censo-B-PRIMARIO-3fam.jsonl"]), "more than its 48")]
        for name, kz, esperado in r12:
            f = [x for x in R12.census_integrity(kz) if esperado in x]
            print(f"mutation [carried rc12: {name}] (census record): {'CAUGHT' if f else 'MISSED'}" + (f" -> {f[0][:140]}" if f else ""))
            ok &= bool(f)
        base = check(old, new, verbose=False, cz=cz, st=st)
        print(f"unmutated rc13: {'PASS' if not base else 'FAIL'}" + (f" -> {base}" if base else ""))
        print(f"mutations: {len(mutations) + len(integ) + len(r12)}")
        return 0 if ok and not base else 1
    fails = check(old, new)
    for f in fails:
        print("FAIL", f)
    print("PARITY: PASS" if not fails else f"PARITY: FAIL ({len(fails)})")
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
