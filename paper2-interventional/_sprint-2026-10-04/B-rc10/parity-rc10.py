#!/usr/bin/env python3
"""Parity check B-v2-rc9.md -> B-v2-rc10.md (Paper B, sprint 2026-10-04; rc10 2026-10-05).

rc10 makes the registered attribution of boundary-straddling sessions (PREREG §2 item 3: a
session belongs to the epoch of its start) the sixth switch of the registered analysis
(`out/ITT-REGISTRADO-v3-2026-10-05.json`), reports the registered with/without sensitivity and
the own stratum, and closes working list 22 (`APPLY-B-rc10.md`).

The diff is cut into hunks (difflib on lines). Every hunk must carry at least one ID, assigned
by an anchor substring of the rc10 hunk (ANCHORS):
    ST status header · S6 the sixth switch and the v3 numbers of H1/H1a/H1c · HOLM the two
    multiplicity readings under v3 · STRAD boundary-straddling sessions, with/without and the
    own stratum · H2 the H2 table under v3 · TIES four-vote ties under v3 · FIG Figure B1 ·
    APPA / APPB appendices · CL working list and changelog.

Checks (exit 1 if any fails):
  1. hunks: every hunk has an ID.
  2. numbers: every numeric token ADDED in a hunk is (a) already in rc9, or (b) derived from an
     artifact read at run time (ITT-REGISTRADO-v3, checks-rc10, the rc10 figure's run.json, and,
     for values kept from earlier versions, ITT-REGISTRADO v2 and v1, checks-rc9, checks-rc8,
     f4, f3, the rc9 figure's run.json), in one of the paper's roundings, or (c) listed in
     LITERALS for one of the hunk's IDs with its source.
     --report prints, per ID, every added and removed number and the class that justifies it.
  3. headline values: strings formatted from the v3 artifacts at run time must be present.
  4. claims, outside struck text and before the working list:
     (a) no sentence presents H1a as rejected;
     (b) LOCK kept from rc9: no sentence presents H1 as rejecting (or as a rejection) without the
         word "deposited" in the same sentence;
     (c) NEW in rc10: no sentence presents H1 as rejecting in "the registered analysis" unless
         the same sentence places that rejection in the sensitivity analysis or an earlier
         version (rc8, rc9, earlier, sensitivity): in v3 H1 rejects under neither reading;
     (d) stopping condition "was met" only with "planning"; §4.6 never calls its correlation
         "M10" without "registered"/"called"/"label"; `1 195` never called adjudicated.
  5. headings identical except the two renames in HEADINGS (§4.2, §4.3).
  6. citations unchanged and listed; footnotes defined; DOIs unchanged.
  7. no host, IP or personal path added.
  8. SHAM-JANELA: exactly 10 blocks, byte-identical to rc9's.
  9. no REANALISE marker.
 10. quotes: every *"..."* span added occurs verbatim (bold and whitespace normalized) in rc9 or
     in a declared source document.
 11. code spans: every added span that names a file resolves on disk; added snake_case
     identifiers occur in the artifacts or sources they name.
 12. bold balance: every paragraph has an even number of `**`.

Usage:  python3 parity-rc10.py              # check
        python3 parity-rc10.py --report     # per-ID numeric deltas with their justification
        python3 parity-rc10.py --self-test  # mutations of rc10 in memory; each must fail
Reads the two manuscripts and the artifacts named above. Writes nothing.
"""
import collections
import difflib
import glob
import json
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPRINT = HERE.parent
P2 = SPRINT.parent
REPO = P2.parent
LASTRO = Path.home() / "Backups" / "paper2-ensaio-2026-09-21"
OLD = SPRINT / "B-v2-rc9.md"
NEW = SPRINT / "B-v2-rc10.md"
ART = {
    "ITT-REGISTRADO-v3": P2 / "out" / "ITT-REGISTRADO-v3-2026-10-05.json",
    "checks-rc10": HERE / "checks-rc10.json",
    "figB1-v3": SPRINT / "figures" / "figB1-h1a-inversao-registrado-v3.run.json",
    "ITT-REGISTRADO-v2": P2 / "out" / "ITT-REGISTRADO-v2-2026-10-05.json",
    "checks-rc9": SPRINT / "B-rc9" / "checks-rc9.json",
    "f4-w4": SPRINT / "B-registered" / "f4-promoviveis-w4.json",
    "f3-abort": SPRINT / "B-registered" / "f3-abort-ex-post.json",
    "figB1-v2": SPRINT / "figures" / "figB1-h1a-inversao-registrado-v2.run.json",
    "ITT-REGISTRADO-v1": P2 / "out" / "ITT-REGISTRADO-2026-10-05.json",
    "checks-rc8": SPRINT / "B-rc8" / "checks-rc8.json",
    "CONCENTRATION": P2 / "out" / "CONCENTRATION-2026-08-30.json",
}
QUOTE_SOURCES = [P2 / "PROSPECTIVE-ESTIMAND-2026-08-30.md", P2 / "PREREG-DRAFT.md",
                 P2 / "ASSIGN-SEED-2026-08-30.md"]

# ---------------------------------------------------------------- tokenization (as rc7)
SECREF = re.compile(r"§§?\s?(\d+(?:\.\d+)*[a-z]?)(?:\(\d+\))?(?:[–-]§?\d+(?:\.\d+)*[a-z]?)?")
CITE = re.compile(r"\[@[^\]]+\]")
LISTNUM = re.compile(r"^(\s*)\d+\.\s", re.M)
DATE = (r"\d{4}-\d{2}-\d{2}(?:T\d{2}:\d{2}(?::\d{2})?Z?)?"
        r"|\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?Z?"
        r"|(?<![\d-])\d{2}-\d{2}(?![\d-])")
TOK = re.compile(r"(?<![A-Za-z_\d.,])(" + DATE + r"|\d+(?:[.,]\d+)*)(?![A-Za-z_\d]|\.\d)")
HEADNUM = re.compile(r"^(#{1,6} )(?:Appendix )?[A-Z]?\.?\d+(?:\.\d+)*[a-z]?", re.M)
SECCELL = re.compile(r"\|\s*(?:Abstract, )?\d+(?:\.\d+)*[a-z]?(?:\s*[,–]\s*\d+(?:\.\d+)*[a-z]?)*\s*(?=\|)")
CODE = re.compile(r"`([^`\n]+)`")
QUOTE = re.compile(r"(?<!\*)\*\".*?\"\*(?!\*)", re.S)
DOI = re.compile(r"10\.\d{4,9}/[^\s`)]+")
S_OPEN, S_CLOSE = "<!-- SHAM-JANELA: pending -->", "<!-- /SHAM-JANELA -->"
R_ANY = re.compile(r"<!-- (?:REANALISE(?:: rewrite)?|/REANALISE) -->")
EXPECTED_SHAM = 10
EXPECTED_R = 108


def normalize(text):
    text = CITE.sub(" ", text)
    text = HEADNUM.sub(r"\1", text)
    text = SECCELL.sub("| ", text)
    text = SECREF.sub(" ", text)
    text = LISTNUM.sub(r"\1", text)
    prev = None
    while prev != text:
        prev = text
        text = re.sub(r"(?<![\d.,])(\d{1,3}) (\d{3})(?![\d,])", r"\1\2", text)
    return text


def numbers(text):
    return collections.Counter(TOK.findall(normalize(text)))


# ---------------------------------------------------------------- hunk IDs
ANCHORS = [
    ("ST", "rc10 prepared 2026-10-05 (every"),
    ("HOLM", "analysis H1 does not reject under either reading: tested alone"),
    ("HOLM", "H1a's unadjusted p-value is 0.2599, and every Holm-adjusted"),
    ("S6", "every session counted in the epoch of its start, the analysis"),
    ("S6", "null for H1c (`p = 0.4006`, §4.0.2)"),
    ("S6", "H1 family excludes zero on any leg: `H1` −1.27"),
    ("H2", "Two intervals of H2, the secondary"),
    ("STRAD", "registered sensitivity without the sessions that cross an epoch boundary (§5)"),
    ("S6", "The realized estimate is −0.0140"),
    ("S6", "re-randomization test, `p = 0.4006`) does not rest on the"),
    ("S6", "~~nonetheless returns an interval excluding zero on all"),
    ("S6", "returns neither once every"),
    ("S6", "~~excludes zero on all three legs once the washout leaves the denominator"),
    ("S6", "shares that history"),
    ("HOLM", "the registered test does not reject under either reading (`p = 0.3294` alone"),
    ("HOLM", "reject either (`p = 0.3294`). Under the deposited Holm"),
    ("HOLM", "smallest p-value is H1a's 0.2599, so the step-down"),
    ("HOLM", "under that deposited reading it does not reject in the registered analysis"),
    ("STRAD", "**Sessions that cross an epoch boundary.**"),
    ("S6", "adds six switches"),
    ("S6", "from rc10 the attribution of"),
    ("S6", "puts H1c back at −0.0228"),
    ("S6", "**Sessions in the epoch of their start (rc10).**"),
    ("STRAD", "As a stratum, the three hold"),
    ("TIES", "In the registered analysis of rc10,"),
    ("S6", "Its acceleration for H1 and H1a is now positive"),
    ("HOLM", "| **H1a** | **0.2599**; 0.0855"),
    ("HOLM", "~~H1a's unadjusted p-value falls below 0.05 in the registered analysis"),
    ("HOLM", "*(rc10: the struck paragraph described rc9's analysis"),
    ("S6", "(−0.0174 for H1c"),
    ("HOLM", "In the sensitivity analysis the disagreement between test and"),
    ("HOLM", "`H1` does not reject in the registered analysis under either reading"),
    ("HOLM", "Artifacts: `out/ITT-REGISTRADO-v3-2026-10-05.json` (field `multiplicidade`"),
    ("S6", "| **locked (the 19 epochs of the analysis set)** | 0.0663"),
    ("S6", "The first four rows are the registered analysis"),
    ("S6", "*(rc10: with sessions counted at their start, H1a"),
    ("S6", "so does the registered sensitivity without boundary-crossing sessions, and all"),
    ("S6", "Control sits at `H1c = 0.0803`"),
    ("S6", "| **95% CI of [−0.0464; +0.0110]**"),
    ("S6", "as in the sensitivity analysis and in earlier versions, is a claim made"),
    ("S6", "non-rejection (`p = 0.4006`, §4.0.2) that wider"),
    ("S6", "### 4.2 H1a: contains zero once sessions"),
    ("S6", "**Correction (rc9).** ~~The rc8 correction"),
    ("S6", "**Correction (rc10).** The rc9 correction"),
    ("S6", "| session-hours, treatment / control | 324.95 / 57.06"),
    ("S6", "Sources: the registered locked leg and the sensitivity without"),
    ("STRAD", "Counted at their start, three sessions carry almost all the exposure"),
    ("S6", "interval it does not.)*~~ ~~that the registered decision rule does not reject H1a. Its"),
    ("S6", "registered decision rule does not reject H1a, and that its interval contains zero on every"),
    ("FIG", "![Figure B1](figures/figB1-h1a-inversao-registrado-v3.svg)"),
    ("FIG", "**Figure B1. H1a: the intervals that excluded zero"),
    ("S6", "### 4.3 H1: the interval that excluded zero came from"),
    ("S6", "`H1` returns −1.27, BCa CI"),
    ("S6", "The struck sentence is rc9's analysis"),
    ("S6", "The rest of this section was written about"),
    ("S6", "relative error ≤ 5.8×10⁻⁶ in all six arm-by-leg cells of the"),
    ("S6", "In the analyses that excluded"),
    ("S6", "**What the argument did NOT do in rc9, and what replaced it.**"),
    ("S6", "The magnitude argument of earlier versions belongs to the same history."),
    ("HOLM", "and `H1` is discarded on the same ground"),
    ("STRAD", "| **boundary-straddling sessions**"),
    ("H2", "| time (s) | 1.795 / 1.478"),
    ("H2", "Two intervals exclude zero, both in the"),
    ("TIES", "difference from −0.0140 to −0.0249 in the registered analysis"),
    ("S6", "(opportunities per epoch 109.5"),
    ("HOLM", "as on H1a in the sensitivity analysis."),
    ("HOLM", "registered test does not reject in the registered analysis (`p = 0.3294`), and under the"),
    ("S6", "**An interval that excludes zero can be the artifact, and the non-rejection the sound result.** ~~The"),
    ("S6", "the only rejection under the deposited decision rules was on the hypothesis demoted"),
    ("APPA", "does not reject under either reading (`p = 0.3294` tested alone; Holm-adjusted 1.0 under"),
    ("APPA", "Up to rc9 the analysis also counted every episode"),
    ("APPA", "- ~~boundary-straddling sessions are not assigned"),
    ("APPA", "*(rc10: implemented; see the item on the registered"),
    ("APPB", "| `out/ITT-REGISTRADO-v3-2026-10-05.json` · `measurement/estimador_itt_registrado.py` (six switches)"),
    ("APPB", "| `out/ITT-REGISTRADO-v2-2026-10-05.json` · `_sprint-2026-10-04/B-registered/estimador_itt_registrado-v2-ac9d2f05.py`"),
    ("APPB", "| `_sprint-2026-10-04/B-rc10/checks-rc10.py` · `checks-rc10.json` |"),
    ("APPB", "| `measurement/sprint-figB-h1a-inversao-registrado-v3.py`"),
    ("APPB", "| registered analysis: H1, H1a, H1c, every BCa interval and re-randomization p-value of the locked leg; session-hours 324.95"),
    ("APPB", "| registered analysis (rc10) on the pre-committed"),
    ("APPB", "| opportunities per epoch 109.5 / 135.0"),
    ("APPB", "| Figure B1 (rc10):"),
    ("APPB", "The artifacts added in rc7, rc8, rc9 and rc10"),
    ("APPB", "`checks-rc10.*` and the rc10"),
    ("CL", "*(rc10)* also `out/ITT-REGISTRADO-v3-2026-10-05.json`"),
    ("CL", "22. ~~**Boundary-straddling sessions**"),
    ("CL", "→ **Done, rc10 (2026-10-05)**"),
    ("CL", "**rc10: sessions in the epoch of their start**"),
]

# (c) literals: numbers added that are neither in rc9 nor in an artifact, with their source
LITERALS = {
    "ST": {"2026-10-05": "date of rc10"},
    "S6": {},
    "HOLM": {},
    "STRAD": {"321.43": "240.42 + 81.01 h (checks-rc10 S spans of d37a5964 and 74de1e72) = 324.95 − 3.52 (v3 with − without)"},
    "H2": {},
    "TIES": {},
    "FIG": {},
    "APPA": {},
    "APPB": {},
    "CL": {},
}

HEADINGS = {
    "### 4.2 H1a: excludes zero on every registered leg, is not rejected under the registered rule, and bears no weight":
        ("### 4.2 H1a: contains zero once sessions are counted at their start, is not rejected, and bears no weight", "S6"),
    "### 4.3 H1: an interval excluding zero that is not a finding":
        ("### 4.3 H1: the interval that excluded zero came from sessions split across epochs", "S6"),
}
FORBIDDEN = [r"\b\d{1,3}(?:\.\d{1,3}){3}\b", r"/Users/", r"~/", r"/var/", r"/root/", r"/tmp/",
             r"\$NOX_", r"srv\d+", r"\.hostinger", r"@[a-z0-9-]+\.(?:com|br|ai)\b"]
EXPECTED_SHAM = 10

# ---------------------------------------------------------------- artifact-derived numbers
def leaves(o):
    if isinstance(o, dict):
        for v in o.values():
            yield from leaves(v)
    elif isinstance(o, list):
        for v in o:
            yield from leaves(v)
    elif isinstance(o, (int, float)) and not isinstance(o, bool):
        yield float(o)


def forms(v):
    out = set()
    for x in (abs(v), abs(v) * 100):
        for d in range(0, 5):
            t = f"{x:.{d}f}"
            out.add(t)
            if "." in t:
                out.add(t.rstrip("0").rstrip(".") if d else t)
        if float(x).is_integer():
            out.add(str(int(x)))
    return out


def artifact_numbers():
    allowed = {}
    for name, p in ART.items():
        d = json.loads(p.read_text())
        for v in leaves(d):
            for f in forms(v):
                allowed.setdefault(f, name)
    return allowed


# ---------------------------------------------------------------- helpers
def headings(text):
    return [l.rstrip() for l in text.splitlines() if re.match(r"^#{1,6} ", l)]


def body_and_refs(text):
    i = text.find("\n## References")
    j = text.find("\n## Appendix A")
    return text[:i] + text[j:], text[i:j]


def sham_spans(text):
    spans, errs, pos = [], [], 0
    while True:
        i = text.find(S_OPEN, pos)
        j = text.find(S_CLOSE, pos)
        if i < 0 and j < 0:
            break
        if i < 0 or (0 <= j < i):
            errs.append(f"sham: closing marker without opening at offset {j}")
            break
        k = text.find(S_CLOSE, i)
        n2 = text.find(S_OPEN, i + len(S_OPEN))
        if k < 0:
            errs.append(f"sham: opening marker at offset {i} never closed")
            break
        if 0 <= n2 < k:
            errs.append(f"sham: nested opening marker at offset {n2}")
            break
        spans.append(text[i + len(S_OPEN):k])
        pos = k + len(S_CLOSE)
    return spans, errs


def reanalise_lines(text):
    """rc7 REANALISE blocks as (id, first line, last line), 1-based, in order."""
    out, stack, i = [], None, 0
    for m in R_ANY.finditer(text):
        ln = text.count("\n", 0, m.start()) + 1
        if m.group(0) != "<!-- /REANALISE -->":
            stack = ln
        else:
            i += 1
            out.append((f"R{i:02d}", stack, ln))
            stack = None
    return out


def hunks(old, new):
    a, b = old.splitlines(), new.splitlines()
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    rb = reanalise_lines(old)
    out = []
    for t, i1, i2, j1, j2 in sm.get_opcodes():
        if t == "equal":
            continue
        ids = [r for r, s, e in rb if s <= i2 and e >= i1 + 1]
        texto8 = "\n".join(b[j1:j2])
        for aid, anc in ANCHORS:
            if anc in texto8 and aid not in ids:
                ids.append(aid)
        out.append(dict(rc7=(i1 + 1, i2), rc8=(j1 + 1, j2), ids=ids,
                        old="\n".join(a[i1:i2]), new=texto8))
    return out, rb


def strip_struck(text):
    return re.sub(r"~~.*?~~", " ", text, flags=re.S)


def fmt4(x):
    return f"{x:+.4f}".replace("-", "−") if x else "0"


def hunks(old, new):
    a, b = old.splitlines(), new.splitlines()
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    out = []
    for t, i1, i2, j1, j2 in sm.get_opcodes():
        if t == "equal":
            continue
        texto = "\n".join(b[j1:j2])
        ids = []
        for aid, anc in ANCHORS:
            if anc in texto and aid not in ids:
                ids.append(aid)
        out.append(dict(rc9=(i1 + 1, i2), rc10=(j1 + 1, j2), ids=ids, old="\n".join(a[i1:i2]), new=texto))
    return out


def strip_struck(text):
    return re.sub(r"~~.*?~~", " ", text, flags=re.S)


def fmt2(x, sinal=False):
    t = f"{x:+.2f}" if sinal else f"{x:.2f}"
    return t.replace("-", "−")


def fmt4(x):
    return f"{x:+.4f}".replace("-", "−") if x else "0"


def headline(reg, chk, f4, f3):
    r = reg["pernas"]["registrado"]["hipoteses"]
    m = reg["multiplicidade"]["registrado"]
    dep = m["leitura_depositada"]["holm_H1a_H1b_H1c_H2x2"]
    tro = m["leitura_da_troca"]["holm_H1_H1a_H1b_H1c_H2x2_m6_m5"]
    lo, hi = r["H1c"]["ic95"]
    d = reg["pernas"]["sens_registrado_sem_sessoes_atravessadas"]["hipoteses"]
    v2 = reg["pernas"]["registrado_v2_equivalente"]["hipoteses"]
    e4 = f4["epoch_1"]["4"]["epoch_1_inteiro"]
    ss = chk["S_sessoes_atravessadas"]["sessoes"]
    ci = lambda x, n=2: f"[{fmt2(x[0], True)}; {fmt2(x[1], True)}]"  # noqa: E731
    adj = {dep["A_familia_registada_inavaliaveis_como_p1"]["p_ajustado"]["H1a"],
           dep["B_so_membros_avaliaveis"]["p_ajustado"]["H1a"],
           tro["A_familia_registada_inavaliaveis_como_p1"]["p_ajustado"]["H1"],
           tro["B_so_membros_avaliaveis"]["p_ajustado"]["H1"]}
    assert adj == {1.0}, f"v3 Holm-adjusted values are not all 1.0: {adj}"
    return {
        "H1 p (registered)": f"`p = {r['H1']['p_rerand']}`",
        "H1 point and BCa CI": f"`H1` returns {fmt2(r['H1']['dif_pontual'])}, BCa CI {ci(r['H1']['ic95'])}",
        "H1a point and BCa CI": f"{fmt2(r['H1a']['dif_pontual'])} · CI {ci(r['H1a']['ic95'])} · **contains zero**",
        "H1c p": f"`p = {r['H1c']['p_rerand']}`",
        "H1a raw p": f"`p = {r['H1a']['p_rerand']}`",
        "Holm all 1.0": "every Holm-adjusted p-value in the family is 1.0",
        "H1c CI": f"[{fmt4(lo)}; {fmt4(hi)}]",
        "hours v3": f"{reg['pernas']['registrado']['por_braco']['treatment']['horas_sessao']} / "
                    f"{reg['pernas']['registrado']['por_braco']['control']['horas_sessao']}",
        "washout episodes v3": f"removes {chk['W_washout']['episodios_removidos_pelo_washout']} episodes",
        "without H1 CI": f"H1 {fmt2(d['H1']['dif_pontual'])} {ci(d['H1']['ic95'])}".replace(" [", " [", 1),
        "without p": f"{d['H1']['p_rerand']}, {d['H1a']['p_rerand']} and {d['H1c']['p_rerand']}",
        "rc9-equivalent H1": f"−19.85 (`p = {v2['H1']['p_rerand']}`) to **{fmt2(r['H1']['dif_pontual'])}**",
        "longest session": f"spans {ss['d37a5964']['span_h']:.2f} h with {ss['d37a5964']['episodios']} episodes",
        "w=4 coverage": f"{100 * e4['cobertura']:.1f}% ({e4['cobertas']} of {e4['oportunidades']}",
        "abort adjudicated": f"{f3['substituicao']['total']['adjudicados']} episodes",
    }


HYP = re.compile(r"\bH1[abc]?\b|\bH2\b")
NEG = re.compile(r"\b(?:not|no|nor|never|neither|without|cannot|stops|only)\b")
REJ = re.compile(r"\b(?:rejects?|rejected|rejection)\b")


def sentences(corpo):
    return re.split(r"(?<=[.])\s+|\s*\|\s*", corpo)


def claims(new):
    fails = []
    corpo = strip_struck(new[:new.find("\n## Working list")])
    for sent in sentences(corpo):
        for m in REJ.finditer(sent):
            antes = list(HYP.finditer(sent[:m.start()]))
            if not antes:
                continue
            sujeito = antes[-1].group(0)
            ini = max(sent.rfind(c, 0, m.start()) for c in ",;:()")
            clause = sent[ini + 1:m.end() + 12]
            negado = bool(re.search(r"\b(?:not|no|nor|never|neither|without|cannot|stops)\b", clause))
            if sujeito == "H1a" and not negado:
                fails.append(f"claim: H1a presented as rejected: {clause.strip()[:90]!r}")
            if sujeito == "H1" and not negado and "deposited" not in sent:
                fails.append(f"claim: H1 presented as rejecting without 'deposited': {sent.strip()[:110]!r}")
            if sujeito == "H1" and not negado and re.search(r"registered\s+analysis", sent) \
                    and not re.search(r"sensitivity|rc8|rc9|earlier", sent):
                fails.append(f"claim: H1 presented as rejecting in the registered analysis: {sent.strip()[:110]!r}")
    for sent in sentences(corpo):
        if re.search(r"\b(?:condition|rule)\b[^.]*\bwas met\b", sent) and "planning" not in sent \
                and "not met" not in sent and "Whether" not in sent:
            fails.append(f"claim: stopping condition 'was met' without the planning qualifier: {sent.strip()[:110]!r}")
    sec46 = corpo[corpo.find("### 4.6"):corpo.find("### 4.7")]
    for sent in sentences(sec46):
        if "M10" in sent and not re.search(r"registered|called|label", sent):
            fails.append(f"claim: §4.6 calls the correlation M10: {sent.strip()[:110]!r}")
    if re.search(r"\b1 195 (?:episodes )?(?:were |are )?adjudicated", corpo):
        fails.append("claim: 1 195 called adjudicated (it is the number submitted)")
    return fails


def check(old, new, verbose=True, report=False):
    fails = []
    reg = json.loads(ART["ITT-REGISTRADO-v3"].read_text())
    chk = json.loads(ART["checks-rc10"].read_text())
    f4 = json.loads(ART["f4-w4"].read_text())
    f3 = json.loads(ART["f3-abort"].read_text())
    allowed_art = artifact_numbers()
    rc9_nums = numbers(old)
    hs = hunks(old, new)
    # 1 hunks
    for h in hs:
        if not h["ids"]:
            fails.append(f"hunk rc9 {h['rc9']} rc10 {h['rc10']} has no ID: {h['new'][:70]!r}")
    # 2 numbers per hunk
    rep = collections.defaultdict(lambda: dict(added=[], removed=[]))
    for h in hs:
        add = numbers(h["new"]) - numbers(h["old"])
        rem = numbers(h["old"]) - numbers(h["new"])
        key = "+".join(h["ids"]) or "?"
        for tok, n in sorted(add.items()):
            why = None
            if tok in rc9_nums:
                why = "rc9"
            elif tok in allowed_art:
                why = "artifact:" + allowed_art[tok]
            else:
                for i in h["ids"]:
                    if tok in LITERALS.get(i, {}):
                        why = f"literal[{i}]: " + LITERALS[i][tok]
                        break
            rep[key]["added"].append((tok, n, why))
            if why is None:
                fails.append(f"number '{tok}' (+{n}) added in hunk {key} (rc10 l.{h['rc10'][0]}) is not justified")
        for tok, n in sorted(rem.items()):
            rep[key]["removed"].append((tok, n))
    # 3 headline values
    flat = " ".join(new.split())
    for k, v in headline(reg, chk, f4, f3).items():
        if " ".join(v.split()) not in flat:
            fails.append(f"headline: {k} — expected text {v!r} (from the artifact) not found in rc10")
    # 4 claims
    fails += claims(new)
    # 5 headings
    h8, h9 = headings(old), headings(new)
    expected = [HEADINGS.get(h, (h, None))[0] for h in h8]
    if expected != h9:
        for x, y in zip(expected + [None] * 9, h9 + [None] * 9):
            if x != y:
                fails.append(f"heading: expected {x!r}, found {y!r}")
                break
    # 6 citations and footnotes
    for name, t in (("rc9", old), ("rc10", new)):
        body, refs = body_and_refs(t)
        used = set(re.findall(r"@([A-Za-z0-9_]+)", " ".join(CITE.findall(body))))
        listed = set(re.findall(r"`\[@([A-Za-z0-9_]+)\]`", refs))
        if used - listed:
            fails.append(f"citation ({name}): used but not listed: {sorted(used - listed)}")
        fm = set(re.findall(r"\[\^([^\]]+)\](?!:)", t))
        fd = set(re.findall(r"^\[\^([^\]]+)\]:", t, re.M))
        if fm - fd:
            fails.append(f"footnote ({name}): markers without definition {sorted(fm - fd)}")
    c9 = collections.Counter(re.findall(r"@([A-Za-z0-9_]+)", " ".join(CITE.findall(body_and_refs(new)[0]))))
    c8 = collections.Counter(re.findall(r"@([A-Za-z0-9_]+)", " ".join(CITE.findall(body_and_refs(old)[0]))))
    if c9 != c8:
        fails.append(f"citation: occurrences changed: +{dict(c9 - c8)} -{dict(c8 - c9)}")
    if collections.Counter(DOI.findall(old)) != collections.Counter(DOI.findall(new)):
        fails.append("doi: DOI multiset changed")
    # 7 forbidden additions
    for pat in FORBIDDEN:
        if len(re.findall(pat, new)) > len(re.findall(pat, old)):
            fails.append(f"forbidden: pattern {pat!r} added")
    # 8 SHAM-JANELA
    so, eo = sham_spans(old)
    sn, en = sham_spans(new)
    fails += eo + en
    if len(sn) != EXPECTED_SHAM or len(so) != EXPECTED_SHAM:
        fails.append(f"sham: {len(sn)} blocks in rc10 and {len(so)} in rc9, expected {EXPECTED_SHAM}")
    for i, (x, y) in enumerate(zip(so, sn), 1):
        if x != y:
            fails.append(f"sham: block {i} ({y.strip()[:50]!r}…) is not byte-identical to rc9")
    # 9 no REANALISE comment marker
    if R_ANY.search(new):
        fails.append("reanalise: a REANALISE marker is present in rc10")
    # 10 quotes
    def nq(x):
        return " ".join(x.replace("**", "").split())
    fontes = nq(old) + " " + " ".join(nq(p.read_text()) for p in QUOTE_SOURCES)
    q8, q9 = collections.Counter(QUOTE.findall(old)), collections.Counter(QUOTE.findall(new))
    for q in (q9 - q8):
        if nq(q[2:-2]) not in fontes:
            fails.append(f"quote: {q[:70]!r} is not verbatim in rc9 or a declared source")
    for q in (q8 - q9):
        fails.append(f"quote removed: {q[:70]!r}")
    # 11 code spans
    c8s, c9s = collections.Counter(CODE.findall(old)), collections.Counter(CODE.findall(new))
    roots = [P2, SPRINT, P2 / "out", REPO, LASTRO, SPRINT / "B-rc8", SPRINT / "B-rc9", HERE, P2 / "measurement",
             SPRINT / "figures", SPRINT / "B-registered"]
    idsrc = "".join(p.read_text() for p in (ART["ITT-REGISTRADO-v3"], ART["checks-rc10"],
                                            P2 / "measurement" / "estimador_itt_registrado.py",
                                            P2 / "ASSIGN-SEED-2026-08-30.md", P2 / "serving-brief.ts",
                                            P2 / "PREREG-DRAFT.md"))
    for span in (c9s - c8s):
        s = span.strip()
        if re.search(r"\.(?:py|json|md|svg|png|ndjson|jsonl|sh|tgz|txt|ts)\b|/$|\.\*$|\{", s) and " " not in s:
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
    if verbose:
        print(f"hunks: {len(hs)}, all with an ID: {all(h['ids'] for h in hs)}")
        na = sum(len(v['added']) for v in rep.values())
        print(f"numeric tokens added across hunks: {na}; justified by rc9 / artifact / literal: "
              f"{sum(1 for v in rep.values() for t in v['added'] if t[2] == 'rc9')} / "
              f"{sum(1 for v in rep.values() for t in v['added'] if t[2] and t[2].startswith('artifact'))} / "
              f"{sum(1 for v in rep.values() for t in v['added'] if t[2] and t[2].startswith('literal'))}")
        print(f"headings: {len(h9)}; renamed: {sum(1 for x, y in zip(h8, h9) if x != y)} (allowed {len(HEADINGS)})")
        print(f"SHAM-JANELA blocks: {len(sn)}, byte-identical to rc9: {sum(1 for x, y in zip(so, sn) if x == y)}")
        print(f"quotes added: {sum((q9 - q8).values())}; code spans added: {sum((c9s - c8s).values())}")
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
        mutations = [
            ("word changed inside a SHAM-JANELA block", new.replace("**Our error, stated.**", "**Our error.**", 1)),
            ("REANALISE marker inserted", new.replace("`p = 0.4006`", "<!-- REANALISE -->`p = 0.4006`<!-- /REANALISE -->", 1)),
            ("H1 p changed (0.3294 -> 0.3249)", new.replace("0.3294", "0.3249")),
            ("H1a p changed (0.2599 -> 0.2959)", new.replace("0.2599", "0.2959")),
            ("v3 session-hours changed (324.95 -> 329.45)", new.replace("324.95", "329.45")),
            ("'without' p changed (0.1957 -> 0.1975)", new.replace("0.1957", "0.1975")),
            ("own-stratum span changed (240.42 -> 204.42)", new.replace("240.42", "204.42")),
            ("H1 rejects without 'deposited'", new.replace(
                "`H1` does not reject in the registered analysis under either reading",
                "`H1` rejects in the registered analysis under either reading", 1)),
            ("H1 rejects in the registered analysis under the deposited reading", new.replace(
                "In the registered\nanalysis H1 does not reject under either reading:",
                "In the registered\nanalysis H1 rejects under the deposited reading:", 1)),
            ("H1a presented as rejected", new.replace("and it is not rejected. Sources:", "and it is rejected. Sources:", 1)),
            ("stopping condition 'was met' unqualified", new.replace(
                "names was met under the planning definition, and the arm was not closed.",
                "names was met, and the arm was not closed.", 1)),
            ("§4.6 calls the correlation M10", new.replace("**The sign flips.**", "**The M10 sign flips.**", 1)),
            ("w = 4 coverage changed (37.4% -> 34.7%)", new.replace("37.4%", "34.7%")),
            ("1 195 called adjudicated", new.replace("All 1 195 were submitted to the", "All 1 195 were adjudicated by the", 1)),
            ("heading renamed without justification", new.replace("### 4.3 H1: the interval", "### 4.3 H1 (rc10): the interval", 1)),
            ("quote fabricated", new.replace('*"esta declaração falhou', '*"esta declaração vale', 1)),
            ("code span names a missing file", new.replace("`out/ITT-REGISTRADO-v3-2026-10-05.json`",
                                                           "`out/ITT-REGISTRADO-v4-2026-10-05.json`", 1)),
            ("IP address added", new.replace("Every\n> number below is measured", "Every\n> number below (10.1.2.3) is measured", 1)),
            ("citation removed", new.replace("[@cameron2008bootstrap; @webb2014reworking] motivates", "motivates", 1)),
            ("bold left unbalanced", new.replace("**Sessions in the epoch of their start (rc10).**",
                                                 "**Sessions in the epoch of their start (rc10).*", 1)),
            ("unmapped hunk with a new number", new.replace("**Benchmarks compare systems on fixed tasks.**",
                                                            "We ran 4217 extra checks.\n\n**Benchmarks compare systems on fixed tasks.**", 1)),
            ("headline interval changed", new.replace("[−0.0464; +0.0110]", "[−0.0464; +0.0101]")),
        ]
        PELA_CLAIM = {"H1 rejects without 'deposited'", "H1 rejects in the registered analysis under the deposited reading",
                      "H1a presented as rejected", "stopping condition 'was met' unqualified",
                      "§4.6 calls the correlation M10", "1 195 called adjudicated"}
        ok = True
        for name, mutated in mutations:
            assert mutated != new, f"mutation did not apply: {name}"
            f = claims(mutated) if name in PELA_CLAIM else check(old, mutated, verbose=False)
            # a mutation counts as caught only by a check other than "hunk has no ID", which
            # fires for any edit to an unchanged line and so proves nothing about the content
            f = [x for x in f if "has no ID" not in x]
            via = "claim check" if name in PELA_CLAIM else "full check, content checks only"
            print(f"mutation [{name}] ({via}): {'CAUGHT' if f else 'MISSED'}" + (f" -> {f[0]}" if f else ""))
            ok &= bool(f)
        base = check(old, new, verbose=False)
        print(f"unmutated rc10: {'PASS' if not base else 'FAIL'}" + (f" -> {base}" if base else ""))
        return 0 if ok and not base else 1
    fails = check(old, new)
    for f in fails:
        print("FAIL", f)
    print("PARITY: PASS" if not fails else f"PARITY: FAIL ({len(fails)})")
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
