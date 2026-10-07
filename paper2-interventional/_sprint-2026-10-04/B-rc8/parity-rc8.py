#!/usr/bin/env python3
"""Parity check B-v2-rc7.md -> B-v2-rc8.md (Paper B, sprint 2026-10-04; rc8 2026-10-05).

rc8 replaces every `REANALISE` block of rc7 (R01..R108, `B-rc7/reanalise-list.txt`) with the
analysis as registered (`out/ITT-REGISTRADO-2026-10-05.json`), keeps the rc7 analysis as a
sensitivity, and adds what `B-rc8/checks-rc8.py` established (sensitivity legs, C12 under
the registered window, the stopping rule, the assignment rule) and the regenerated Figure B1.

The diff is cut into hunks (difflib on lines). Every hunk must carry at least one ID:
  R01..R108  the rc7 REANALISE blocks whose lines the hunk replaces (found automatically);
  new-check / sweep IDs, assigned by an anchor substring of the rc8 hunk (ANCHORS):
    ST status header · AB abstract sweep · HOLM multiplicity · REG the registered analysis
    described (estimator, switches, panel, window, BCa, set) · STOP stopping rule (block D)
    · ASSIGN assignment rule (block E) · LEGS sensitivity legs (block A) · C12 ties (block C)
    · H2H3 §5 · FIG Figure B1 · POW power sweep · BCA §4.2/§4.1 interval sweep · IDENT H1
    identity (block A) · APPA / APPB appendices · CL working list and changelog.

Checks (exit 1 if any fails):
  1. hunks: every hunk has an ID; every rc7 REANALISE block R01..R108 is inside a hunk.
  2. numbers: every numeric token ADDED in a hunk is (a) already in rc7, or (b) derived from
     an artifact read at run time (ITT-REGISTRADO, checks-rc8.json, C12-EMPATES-REGISTRADO,
     the registered figure's run.json, CONCENTRATION), in one of the paper's roundings, or
     (c) listed in LITERALS for one of the hunk's IDs with its source. --report prints, per
     ID, every added and removed number and the class that justifies it.
  3. headline values: the strings the paper states for the registered result are formatted
     from the artifacts at run time and must be present (HEADLINE).
  4. claims: outside struck text and before the working list, no sentence presents H1a as
     rejected, and `1 195` is never called adjudicated.
  5. headings identical except the two renames in HEADINGS.
  6. citations unchanged and listed; footnotes defined.
  7. no host, IP or personal path added.
  8. SHAM-JANELA: exactly 10 blocks, byte-identical to rc7's.
  9. REANALISE: no marker left in rc8 (comment form).
 10. quotes: every *"..."* span added in rc8 occurs verbatim (bold and whitespace
     normalized) in rc7 or in a declared source document.
 11. code spans: every added span that names a file resolves on disk (repo, sprint dir,
     out/, or the trial ballast directory); added snake_case identifiers occur in the
     artifacts or scripts they name.
 12. bold balance: every paragraph has an even number of `**`.

Usage:  python3 parity-rc8.py              # check
        python3 parity-rc8.py --report     # per-ID numeric deltas with their justification
        python3 parity-rc8.py --self-test  # mutations of rc8 in memory; each must fail
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
OLD = SPRINT / "B-v2-rc7.md"
NEW = SPRINT / "B-v2-rc8.md"
ART = {
    "ITT-REGISTRADO": P2 / "out" / "ITT-REGISTRADO-2026-10-05.json",
    "checks-rc8": HERE / "checks-rc8.json",
    "C12-REGISTRADO": P2 / "out" / "C12-EMPATES-REGISTRADO-2026-10-05.json",
    "figB1-registrado": SPRINT / "figures" / "figB1-h1a-inversao-registrado.run.json",
    "CONCENTRATION": P2 / "out" / "CONCENTRATION-2026-08-30.json",
}
QUOTE_SOURCES = [P2 / "PROSPECTIVE-ESTIMAND-2026-08-30.md"]

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
    ("ST", "rc8 prepared 2026-10-05 (the analysis as"),
    ("AB", "served data and form the analysis set."),
    ("AB", "quantities *do* return intervals excluding zero: `H1a` on the locked and pre-committed"),
    ("STOP", "Two commitments made before the seed were not kept"),
    ("AB", "session with three episodes~~ ~~excludes zero only on the locked leg"),
    ("BCA", "excludes zero on the locked and the\npre-committed legs under the registered BCa interval"),
    ("ASSIGN", "**The assignment rule, declared and replaced (rc8).**"),
    ("HOLM", "| `H1a` | rate of eligible opportunities per session-hour | **computable**; unadjusted"),
    ("H2H3", "This paper reports the intention-to-treat analysis of that family and, in §5"),
    ("ASSIGN", "- the assignment, from drand round 31774052 through `assign_arms.py` to the served arms,"),
    ("STOP", "- the Epoch-1 coverage of §3.0 against the 36.7% stopping threshold"),
    ("ASSIGN", "The replacement of the declared assignment rule (§1) is dated by our commit log too"),
    ("REG", "**Deviation, declared in rc7; resolved in rc8.**"),
    ("REG", "The registered analysis counts it from its first `active` record"),
    ("STOP", "**Correction (rc8): a declared stopping rule was met in Epoch 1 and not executed.**"),
    ("REG", "The registered analysis is `measurement/estimador_itt_registrado.py`"),
    ("REG", "The registered analysis applies the substitution rule of §6 item 7"),
    ("C12", "Nor can it bind in the\nregistered substitution panel"),
    ("C12", "Under the registered window and epoch\nset (`out/C12-EMPATES-REGISTRADO-2026-10-05.json`, rc8)"),
    ("REG", "over the 20 epochs of the sensitivity analysis and 9 903 over the 19 of the registered"),
    ("HOLM", "### 4.0.2 The registered test against the bootstrap, and the Holm rule on H1a"),
    ("HOLM", "| outcome | re-randomization *p*, unadjusted (registered analysis; sensitivity)"),
    ("HOLM", "The registered decision rule\nreaches the same verdict by a route that does not need that argument"),
    ("HOLM", "Artifacts: `out/ITT-REGISTRADO-2026-10-05.json` (field `multiplicidade` holds both Holm"),
    ("BCA", "*(rc8: the direction held for the percentile intervals of the analysis now"),
    ("POW", "(96.4) and set it aside because `09-02` served no brief, which is also why the registered"),
    ("BCA", "### 4.2 H1a: excludes zero on a denominator dominated by one epoch, is not rejected, and bears no weight"),
    ("BCA", "and it made the inversion look specific to one epoch when it is not. ~~Under the"),
    ("BCA", "`09-14` is the magnitude; the exclusion of zero is a property of the locked leg alone.~~"),
    ("BCA", "sparse session is not a conclusion~~ ~~that both sensitivity legs contain zero (the"),
    ("BCA", "on the locked leg only, on a denominator dominated by one sparse session.~~ that the"),
    ("FIG", "![Figure B1](figures/figB1-h1a-inversao-registrado.svg)"),
    ("FIG", "**Figure B1. H1a's intervals exclude zero on a denominator dominated by one epoch of idle"),
    ("IDENT", "On the six cells\nof the registered analysis the relative error is at most"),
    ("BCA", "excludes zero only while `09-14` is in, on a denominator dominated by one sparse session,"),
    ("H2H3", "The secondary model and co-estimates were not listed"),
    ("H2H3", "**H2, computed (rc8).**"),
    ("C12", "It cannot bind in the three-family panel, where three substantive verdicts are required"),
    ("C12", "window (10, 10, 7, and one control tie before `09-03`'s exposure window under the"),
    ("STOP", "**A stopping rule that was met and not executed.**"),
    ("APPA", "| **This trial** | promotion dose *w* on 19 designated items |"),
    ("BCA", "directly calibrate this BCa (or percentile) ratio estimator"),
    ("STOP", "Two further commitments made before the seed\nwere not kept"),
    ("HOLM", "only rejection under the registered decision rules is on the hypothesis demoted"),
    ("APPA", "the unexecuted stopping rule and the replaced assignment\nrule below are not in it"),
    ("APPA", "~~Three~~ ~~Seven~~ Nine that a reader cannot reconstruct"),
    ("APPB", "| `out/ITT-REGISTRADO-2026-10-05.json` · `measurement/estimador_itt_registrado.py`"),
    ("APPB", "| `_sprint-2026-10-04/B-rc7/checks-rc7.py` · `checks-rc7.json` |"),
    ("APPB", "| registered analysis: H1, H1a, H1c, every BCa interval and re-randomization p-value"),
    ("APPB", "The artifacts added in rc7 and rc8 (`ITT-PRELIMINAR.json`, `checks-rc7.*`,"),
    ("CL", "*(rc8: 18 is done; 17 now also covers the rc8 artifacts."),
    ("CL", "*(rc8: Figure B1 is now"),
    ("CL", "17. **Ballast for the rc7 and rc8 evidence**"),
    ("CL", "*(rc8)* also\n    `out/ITT-REGISTRADO-2026-10-05.json`"),
    ("CL", "→ **Done,\n    rc8 (2026-10-05)**"),
    ("CL", "20. **Review of rc8**"),
    ("CL", "**rc8: the registered analysis reported, and two findings of ours**"),
]

# (c) literals: numbers added that are neither in rc7 nor in an artifact, with their source
LITERALS = {
    "ST": {"2026-10-05": "date of rc8"},
    "STOP": {"36.7": "PROSPECTIVE-ESTIMAND-2026-08-30.md §3-bis l.268/277 (the threshold)",
             "2026-08-30": "date of PROSPECTIVE-ESTIMAND",
             "1526": "out/CONCENTRATION-2026-08-30.json `oportunidades` (artifact, integer)",
             "40.0": "CONCENTRATION `cobertura` 0.4004 as written in PROSPECTIVE §2-bis",
             "33.7": "checks-rc8.json block D epoch_1_fase_active 0.3366",
             "4": "the four H1-family hypotheses / §4"},
    "ASSIGN": {"2026-08-16": "assign_arms.py first commit (87ac89a, commit log)",
               "2026-08-17": "assign_arms.py last change before the round (3199ec1, commit log)",
               "21:33:46Z": "commit 686bea6, the declared assignment (commit log)",
               "21:56:42Z": "commit 3e1c259, the retraction (commit log)",
               "24": "21:56:42Z − 21:32:04Z = 24 min 38 s",
               "38": "21:56:42Z − 21:32:04Z = 24 min 38 s",
               "234": "registered N", "117": "ASSIGN-SEED allocation", "39": "ASSIGN-SEED allocation",
               "09-05": "epoch label, block E", "09-06": "epoch label, block E", "09-07": "epoch label, block E",
               "09-08": "epoch label, block E", "09-09": "epoch label, block E", "09-11": "epoch label, block E",
               "09-13": "epoch label, block E", "09-17": "epoch label, block E", "09-19": "epoch label, block E",
               "2426": "sha256_da_atribuicao prefix 2426d13d…"},
    "REG": {"10:37:01.943Z": "first active record of 09-01 (ITT-REGISTRADO janelas_de_exposicao)",
            "17:23:39.777Z": "first served record of 09-03 (ITT-REGISTRADO janelas_de_exposicao)",
            "0.190": "RESULTADO.md §1: 09-02's own H1c (94.3 weighted opportunities, 17.95 repeats)",
            "0.5": "upper bound on the expiry cut's relative effect (so_janela_expiracao deltas < 0.33%)",
            "0.160": "0.1603 to three decimals (rc7 value)", "0.439": "so_conjunto H1c p 0.4393",
            "0.152": "registrado_sem_conjunto H1c p 0.1524",
            "9903": "ITT-REGISTRADO pernas.registrado rerand_padroes_distintos",
            "1179": "ITT-REGISTRADO painel resolvidos_substituicao", "16": "painel unknown_substituicao",
            "13": "painel resgatados_failure", "20": "painel resgatados",
            "441": "SPEC §2 09-03 volume 441/672", "672": "SPEC §2 09-03 volume 441/672",
            "1.02": "ITT-REGISTRADO unknown share 0.010193", "1.34": "pernas.atual unknown share 0.013412",
            "10": "the registered 10% missing-data rule",
            "0.0017": "BCa alfa_ajustado H1 0.001745", "0.0009": "BCa alfa_ajustado H1a 0.000867",
            "10000": "bootstrap replicates"},
    "HOLM": {"0.43": "sensitivity Holm adjusted H1a m=5 0.4275", "0.34": "sensitivity Holm adjusted H1a m=4 0.342",
             "0.01": "first Holm threshold 0.05/5", "0.0125": "first Holm threshold 0.05/4",
             "0.05": "α", "1.0": "Holm-adjusted H1c / H2", "5": "m", "4": "m",
             "0.831": "H2 tempo p_bilateral 0.8305", "0.684": "H2 tokens p_bilateral 0.6844",
             "0.1603": "rc7 value (sensitivity)", "0.0855": "rc7 value", "0.0127": "rc7 value"},
    "H2H3": {"7.45": "WINSOR tempo_s (PREREG §4.2)", "65206": "WINSOR tokens (PREREG §4.2)",
             "2026-08-15": "lock date of the p95", "5951": "H2 instrumento pares",
             "37": "H2 instrumento assinaturas_com_piso", "5875": "H2 instrumento episodios_com_regret",
             "2026-08-23": "first day of the locked corpus", "2026-09-21": "last day of the locked corpus",
             "0.892": "multiplicidade.atual H2_tempo", "0.950": "multiplicidade.atual H2_tokens 0.95",
             "1172": "H2 treatment n_episodios", "1115": "H2 control n_episodios",
             "1.770": "H2 treatment media_winsorizada 1.770111", "1.486": "H2 control media_winsorizada 1.485745",
             "12861": "H2 treatment tokens media_winsorizada", "10721": "H2 control tokens media_winsorizada",
             "0.28": "H2 tempo dif winsorizada 0.284366", "1.13": "H2 tempo dif bruta", "1.0": "Holm adjusted",
             "19": "epochs"},
    "C12": {"0.0211": "C12-REGISTRADO empate_como_failure diferenca −0.021067"},
    "FIG": {},
    "POW": {"96.4": "SPEC §3 (already cited in rc7 B.1)"},
    "BCA": {},
    "LEGS": {},
    "IDENT": {"6.0": "checks-rc8 block A identity error 6.04e-06"},
    "APPA": {"36.7": "PROSPECTIVE §3-bis threshold", "24": "24 min 38 s", "38": "24 min 38 s",
             "2026-08-30": "date"},
    "APPB": {"0.6235": "corte_pos_expiracao horas_sessao_antes", "0.5154": "horas_sessao_depois",
             "22.835": "corte_pos_expiracao oportunidades_removidas", "33": "episodios_pos_expiracao",
             "21:33:46Z": "commit log", "21:56:42Z": "commit log", "2426": "sha prefix",
             "6.0": "identity error"},
    "AB": {},
    "HOLM_SENS": {},
    "CL": {},
}
R_EXTRA = {  # literals allowed in hunks that replace REANALISE blocks (the sentence's own sources)
    "10.9375": "SPEC fractional count (rc7 R51)", "8.23375": "rc7 R51",
    "90.2": "out/H1C-POWER-REALIZADO-2026-09-10.json (rc7)", "0.0796": "registered control H1c",
    "0.0351": "checks-rc8 block A distance", "0.6235": "corte_pos_expiracao", "0.5154": "idem",
    "0.543": "RESULTADO §1: 09-01 hours before offset (current)", "0.406": "09-01 after offset (checks A 0.4056)",
    "0.457": "RESULTADO §1: 09-03 before", "0.246": "09-03 after (checks A 0.2455)",
    "22.835": "corte_pos_expiracao", "33": "episodios_pos_expiracao", "441": "SPEC §2", "672": "SPEC §2",
    "10:37:01.943Z": "janelas_de_exposicao", "17:23:39.777Z": "janelas_de_exposicao",
    "0.0017": "BCa alfa", "0.0009": "BCa alfa", "0.0162": "rerand observado H1c −0.016237",
    "1179": "painel", "16": "painel", "13": "painel", "20": "painel", "0.43": "rc7 Holm", "0.34": "rc7 Holm",
    "6.117": "registered H1 treatment 6.116682", "20.236": "registered H1 control 20.23648",
    "0.0211": "C12-REGISTRADO", "0.1205": "Holm", "0.0964": "Holm", "0.831": "H2", "0.684": "H2",
    "0.01": "Holm threshold", "0.0125": "Holm threshold", "1.0": "Holm adjusted", "36.7": "PROSPECTIVE",
    "32.4": "checks D", "24": "24 min 38 s", "38": "24 min 38 s",
    "2026-09-02": "INCIDENT-2026-09-02-epoch-perdido.md (file name cited for the outage)",
}

HEADINGS = {
    "### 4.0.2 The registered test disagrees with the bootstrap on H1a":
        ("### 4.0.2 The registered test against the bootstrap, and the Holm rule on H1a", "HOLM"),
    "### 4.2 H1a: excludes zero only on the locked leg, and therefore bears no weight":
        ("### 4.2 H1a: excludes zero on a denominator dominated by one epoch, is not rejected, and bears no weight", "BCA"),
}
FORBIDDEN = [r"\b\d{1,3}(?:\.\d{1,3}){3}\b", r"/Users/", r"~/", r"/var/", r"/root/", r"/tmp/",
             r"\$NOX_", r"srv\d+", r"\.hostinger", r"@[a-z0-9-]+\.(?:com|br|ai)\b"]


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


def headline(reg, chk):
    r = reg["pernas"]["registrado"]["hipoteses"]
    m = reg["multiplicidade"]["registrado"]
    holm = m["holm_H1a_H1b_H1c_H2x2"]
    lo, hi = r["H1c"]["ic95"]
    D, E = chk["D_regra_de_parada"], chk["E_regra_de_atribuicao"]
    a = D["a_regra_do_artefato_de_planejamento"]["epoch_1_inteiro"]
    return {
        "H1 p": f"`p = {r['H1']['p_rerand']}`",
        "H1c p": f"`p = {r['H1c']['p_rerand']}`",
        "H1a raw p": f"{r['H1a']['p_rerand']}",
        "H1a Holm m=5": f"{holm['A_familia_registada_inavaliaveis_como_p1']['p_ajustado']['H1a']}",
        "H1a Holm m=4": f"{holm['B_so_membros_avaliaveis']['p_ajustado']['H1a']}",
        "H1c point": f"{fmt4(r['H1c']['dif_pontual'])}".replace("+", ""),
        "H1c CI": f"[{fmt4(lo)}; {fmt4(hi)}]",
        "panel 1 179": f"{reg['painel']['resolvidos_substituicao']:,}".replace(",", " "),
        "stop coverage": f"{100 * a['cobertura']:.1f}%",
        "stop counts": f"{a['cobertas']} of {a['oportunidades']}",
        "assignment epochs": f"{len(E['janela_realizada']['braco_binario_diferente'])} of the 20",
        "H2 time p": f"{round(reg['H2']['registrado']['tempo_s']['rerand_bruto']['p_bilateral'], 3)}",
        "H2 tokens p": f"{round(reg['H2']['registrado']['tokens']['rerand_bruto']['p_bilateral'], 3)}",
    }


def check(old, new, verbose=True, report=False):
    fails = []
    reg = json.loads(ART["ITT-REGISTRADO"].read_text())
    chk = json.loads(ART["checks-rc8"].read_text())
    allowed_art = artifact_numbers()
    rc7_nums = numbers(old)
    hs, rb = hunks(old, new)
    # 1 hunks
    covered = set()
    for h in hs:
        if not h["ids"]:
            fails.append(f"hunk rc7 {h['rc7']} rc8 {h['rc8']} has no ID: {h['new'][:70]!r}")
        covered |= {i for i in h["ids"] if re.fullmatch(r"R\d{2,3}", i)}
    if len(rb) != EXPECTED_R:
        fails.append(f"rc7 has {len(rb)} REANALISE blocks, expected {EXPECTED_R}")
    for r, _, _ in rb:
        if r not in covered:
            fails.append(f"REANALISE block {r} is not inside any hunk")
    # 2 numbers per hunk
    rep = collections.defaultdict(lambda: dict(added=[], removed=[]))
    for h in hs:
        add = numbers(h["new"]) - numbers(h["old"])
        rem = numbers(h["old"]) - numbers(h["new"])
        key = "+".join(h["ids"]) or "?"
        for tok, n in sorted(add.items()):
            why = None
            if tok in rc7_nums:
                why = "rc7"
            elif tok in allowed_art:
                why = "artifact:" + allowed_art[tok]
            else:
                for i in h["ids"]:
                    if tok in LITERALS.get(i, {}):
                        why = f"literal[{i}]: " + LITERALS[i][tok]
                        break
                if why is None and any(re.fullmatch(r"R\d{2,3}", i) for i in h["ids"]) and tok in R_EXTRA:
                    why = "literal[R]: " + R_EXTRA[tok]
            rep[key]["added"].append((tok, n, why))
            if why is None:
                fails.append(f"number '{tok}' (+{n}) added in hunk {key} (rc8 l.{h['rc8'][0]}) is not justified")
        for tok, n in sorted(rem.items()):
            rep[key]["removed"].append((tok, n))
    # 3 headline values
    for k, v in headline(reg, chk).items():
        if v not in new:
            fails.append(f"headline: {k} — expected text {v!r} (from the artifact) not found in rc8")
    # 4 claims
    corpo = strip_struck(new[:new.find("\n## Working list")])
    NEG = re.compile(r"\b(?:not|no|nor|never|neither|without|cannot|stops)\b")
    HYP = re.compile(r"\bH1[abc]?\b|\bH2\b")
    for sent in re.split(r"(?<=[.])\s+|\s*\|\s*", corpo):
        if "H1a" not in sent:
            continue
        for m in re.finditer(r"\b(?:rejects?|rejected|rejection)\b", sent):
            antes = list(HYP.finditer(sent[:m.start()]))
            if not antes or antes[-1].group(0) != "H1a":
                continue                      # the verb's subject is another hypothesis
            ini = max(sent.rfind(c, 0, m.start()) for c in ",;:()")
            clause = sent[ini + 1:m.end() + 12]
            if not NEG.search(clause):
                fails.append(f"claim: H1a presented as rejected: {clause.strip()[:90]!r}")
    if re.search(r"\b1 195 (?:episodes )?(?:were |are )?adjudicated", corpo):
        fails.append("claim: 1 195 called adjudicated (it is the number submitted)")
    # 5 headings
    h7, h8 = headings(old), headings(new)
    expected = [HEADINGS.get(h, (h, None))[0] for h in h7]
    if expected != h8:
        for x, y in zip(expected + [None] * 9, h8 + [None] * 9):
            if x != y:
                fails.append(f"heading: expected {x!r}, found {y!r}")
                break
    # 6 citations and footnotes
    for name, t in (("rc7", old), ("rc8", new)):
        body, refs = body_and_refs(t)
        used = set(re.findall(r"@([A-Za-z0-9_]+)", " ".join(CITE.findall(body))))
        listed = set(re.findall(r"`\[@([A-Za-z0-9_]+)\]`", refs))
        if used - listed:
            fails.append(f"citation ({name}): used but not listed: {sorted(used - listed)}")
        if name == "rc8":
            c8 = collections.Counter(re.findall(r"@([A-Za-z0-9_]+)", " ".join(CITE.findall(body))))
            c7 = collections.Counter(re.findall(r"@([A-Za-z0-9_]+)", " ".join(CITE.findall(body_and_refs(old)[0]))))
            if c8 != c7:
                fails.append(f"citation: occurrences changed: +{dict(c8 - c7)} -{dict(c7 - c8)}")
        fm = set(re.findall(r"\[\^([^\]]+)\](?!:)", t))
        fd = set(re.findall(r"^\[\^([^\]]+)\]:", t, re.M))
        if fm - fd:
            fails.append(f"footnote ({name}): markers without definition {sorted(fm - fd)}")
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
    if len(sn) != EXPECTED_SHAM:
        fails.append(f"sham: {len(sn)} blocks, expected {EXPECTED_SHAM}")
    for i, (x, y) in enumerate(zip(so, sn), 1):
        if x != y:
            fails.append(f"sham: block {i} ({y.strip()[:50]!r}…) is not byte-identical to rc7")
    # 9 no REANALISE comment marker
    if R_ANY.search(new):
        fails.append("reanalise: a REANALISE marker is left in rc8")
    # 10 quotes
    def nq(x):
        return " ".join(x.replace("**", "").split())
    fontes = nq(old) + " " + " ".join(nq(p.read_text()) for p in QUOTE_SOURCES)
    q7, q8 = collections.Counter(QUOTE.findall(old)), collections.Counter(QUOTE.findall(new))
    for q in (q8 - q7):
        inner = nq(q[2:-2])
        if inner not in fontes:
            fails.append(f"quote: {q[:70]!r} is not verbatim in rc7 or a declared source")
    for q in (q7 - q8):
        fails.append(f"quote removed: {q[:70]!r}")
    # 11 code spans
    c7, c8 = collections.Counter(CODE.findall(old)), collections.Counter(CODE.findall(new))
    roots = [P2, SPRINT, P2 / "out", REPO, LASTRO, SPRINT / "B-rc7", HERE, P2 / "measurement", SPRINT / "figures"]
    idsrc = "".join(p.read_text() for p in (ART["ITT-REGISTRADO"], ART["checks-rc8"],
                                            P2 / "measurement" / "estimador_itt_registrado.py",
                                            P2 / "ASSIGN-SEED-2026-08-30.md"))
    for span in (c8 - c7):
        s = span.strip()
        if re.search(r"\.(?:py|json|md|svg|png|ndjson|jsonl|sh|tgz|txt)\b|/$|\.\*$|\{", s) and " " not in s:
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
                fails.append(f"code span: identifier `{span}` occurs in none of the named artifacts")
    # 12 bold balance
    noncode = re.sub(r"```.*?```", "", new, flags=re.S)
    for k, para in enumerate(re.split(r"\n\s*\n", noncode)):
        if para.count("**") % 2:
            fails.append(f"bold: odd number of ** in paragraph {k}: {para.strip()[:60]!r}")
    if verbose:
        print(f"hunks: {len(hs)}, all with an ID: {all(h['ids'] for h in hs)}; "
              f"REANALISE blocks covered: {len(covered)}/{len(rb)}")
        na = sum(len(v['added']) for v in rep.values())
        print(f"numeric tokens added across hunks: {na}; justified by rc7 / artifact / literal: "
              f"{sum(1 for v in rep.values() for t in v['added'] if t[2] == 'rc7')} / "
              f"{sum(1 for v in rep.values() for t in v['added'] if t[2] and t[2].startswith('artifact'))} / "
              f"{sum(1 for v in rep.values() for t in v['added'] if t[2] and t[2].startswith('literal'))}")
        print(f"headings: {len(h8)}; renamed: {sum(1 for x, y in zip(h7, h8) if x != y)} (allowed {len(HEADINGS)})")
        print(f"SHAM-JANELA blocks: {len(sn)}, byte-identical to rc7: {sum(1 for x, y in zip(so, sn) if x == y)}")
        print(f"REANALISE markers left: {len(R_ANY.findall(new))}")
        print(f"quotes added: {sum((q8 - q7).values())}; code spans added: {sum((c8 - c7).values())}")
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
        S = new.find(S_OPEN)
        mutations = [
            ("word changed inside a SHAM-JANELA block", new.replace("**Our error, stated.**", "**Our error.**", 1)),
            ("REANALISE marker reinserted", new.replace("`p = 0.434`", "<!-- REANALISE -->`p = 0.434`<!-- /REANALISE -->", 1)),
            ("H1c p changed (0.434 -> 0.443)", new.replace("`p = 0.434`", "`p = 0.443`")),
            ("H1a Holm-adjusted changed (0.1205 -> 0.1250)", new.replace("0.1205", "0.1250")),
            ("H1a presented as rejected", new.replace("and not rejected under the registered Holm rule;",
                                                      "and rejected under the registered Holm rule;", 1)),
            ("1 195 called adjudicated", new.replace("All 1 195 were submitted to the", "All 1 195 were adjudicated by the", 1)),
            ("heading renamed without justification", new.replace("### 4.3 H1: an interval", "### 4.3 H1 (rc8): an interval", 1)),
            ("quote fabricated", new.replace('*"a decisão de parar"*', '*"a decisão de seguir"*', 1)),
            ("code span names a missing file", new.replace("`out/C12-EMPATES-REGISTRADO-2026-10-05.json`, rc8)",
                                                           "`out/C12-EMPATES-REGISTRADO-2026-10-06.json`, rc8)", 1)),
            ("IP address added", new.replace("Every\n> number below is measured", "Every\n> number below (10.1.2.3) is measured", 1)),
            ("stopping-rule coverage changed (32.4% -> 38.4%)", new.replace("32.4%", "38.4%")),
            ("assignment count changed (11 of the 20 -> 9 of the 20)", new.replace("11 of the 20", "9 of the 20")),
            ("citation removed", new.replace("[@cameron2008bootstrap; @webb2014reworking] motivates", "motivates", 1)),
            ("bold left unbalanced", new.replace("**Correction (rc8): a declared stopping rule", "**Correction (rc8): a declared stopping rule*", 1)),
            ("unmapped hunk with a new number", new.replace("**Benchmarks compare systems on fixed tasks.**",
                                                            "We ran 4217 extra checks.\n\n**Benchmarks compare systems on fixed tasks.**", 1)),
            ("headline interval changed", new.replace("[−0.0445; +0.0125]", "[−0.0445; +0.0152]")),
        ]
        ok = True
        for name, mutated in mutations:
            assert mutated != new, f"mutation did not apply: {name}"
            f = check(old, mutated, verbose=False)
            print(f"mutation [{name}]: {'CAUGHT' if f else 'MISSED'}" + (f" -> {f[0]}" if f else ""))
            ok &= bool(f)
        base = check(old, new, verbose=False)
        print(f"unmutated rc8: {'PASS' if not base else 'FAIL'}")
        return 0 if ok and not base else 1
    fails = check(old, new)
    for f in fails:
        print("FAIL", f)
    print("PARITY: PASS" if not fails else f"PARITY: FAIL ({len(fails)})")
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
