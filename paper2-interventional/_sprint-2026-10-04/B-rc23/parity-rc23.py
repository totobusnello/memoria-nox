#!/usr/bin/env python3
"""Parity check B-v2-rc22.md -> B-v2-rc23.md (Paper B, sprint 2026-10-04; rc23 2026-10-07).

rc23 integrates the result of the whole-window sham (`job-janela2`, CONCLUIDO
2026-10-07T02:09:46Z, 21/21 validated) and closes working list 15 and 17 (ballast extended to
115 artifacts). rc22 was the text frozen until that result was integrated. The ten
`SHAM-JANELA` blocks of rc22 are replaced by result text and the markers are removed. No number
of the H1 family moves and no artifact of the analysis changes (`APPLY-B-rc23.md`).

  SH  the ten blocks: status header, Abstract, §4.0.1c, §7, §8.3, §8.5, B.1, working list 8, 9, 15
  C   §4.0.1c inside the old block: the whole-window table and reading, the first limit, two rows
      of "What was measured", the `dist/` row, "What this does to the claims", the artifacts
  B01 §4.0.1b table, specificity row
  P11 §1.1: ITT-PRELIMINAR.json entered the manifest in rc23
  AB  Appendix B: two new rows, nineteen ballast-status cells, the manifest row, the ballast
      paragraph
  WL  working list 8, 10, 17 (done), 24; CL the rc23 changelog block; ST the status header

Checks (exit 1 if any fails): rc22's (hunks with IDs, numbers sourced, invariants, tail with the
declared edits reverted equal to rc22, carried locks of every earlier rc, qualifiers/hedges,
integrity S..S22), except that the sham check is inverted: rc22 must hold exactly the ten blocks
and rc23 none, and that S19/L6 (the manifest had 50 entries and no rc15-rc19 path), which rc23
deliberately makes false, is replaced by S23/M. NEW: block S23 re-derives every number rc23
adds from the job's own files (RESUMO.json recomputed from its per-run counts with the
pre-committed p rule, DETERMINISMO.json, RUNS.sha256 against the 21 runs inside the .tgz,
RECIBO.txt, STATUS, the instrument and database pins against job-v2b's, the 53 exclusions, the
235 states without a bonus against the expiry) and from the ballast manifest and receipt; and
the result sentences are locked in the exact form those files give.

Usage:  python3 parity-rc23.py | --report | --self-test     Reads; writes nothing.
Caveat: the manifest and the receipt live in ~/Backups (outside the repository, by design);
on a machine without them S23/M and S23/R are reported as NOT VERIFIED warnings, never passed.
"""
import collections
import functools
import hashlib
import importlib.util
import json
import re
import sys
import tarfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
SPRINT = HERE.parent
P2 = SPRINT.parent
REPO = P2.parent
OLD = SPRINT / "B-v2-rc22.md"
NEW = SPRINT / "B-v2-rc23.md"
RC22 = SPRINT / "B-rc22" / "parity-rc22.py"
RC22_SHA = "143101dd5426c8708445056db7496ae54164e312b6af15e5486f503bae436d93"
OLD_SHA = "168ddd5da88701c60df94619ebc24dc17f053f1ab02bb007f64f807a8d36fa89"

assert hashlib.sha256(RC22.read_bytes()).hexdigest() == RC22_SHA, \
    "parity-rc22.py changed: the locks carried from it are no longer the ones rc22 ran"
_spec = importlib.util.spec_from_file_location("parity_rc22", RC22)
R22 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(R22)
R21, R20, R19, R18, R17 = R22.R21, R22.R20, R22.R19, R22.R18, R22.R17
R16, R15, R14, R13, R12, R11 = R22.R16, R22.R15, R22.R14, R22.R13, R22.R12, R22.R11
flat, body, tail, sci, load = R22.flat, R22.body, R22.tail, R22.sci, R22.load
TITLE = R22.TITLE
S_OPEN, S_CLOSE = R11.S_OPEN, R11.S_CLOSE

SHAM = SPRINT / "B-sham-v2"
J2 = SHAM / "job-janela2"
V2B = SHAM / "job-v2b"
LASTRO = Path.home() / "Backups" / "paper2-ensaio-2026-09-21"
RECEIPT23 = "RECIBO-ITEM15-20261007T120404Z.txt"
PINS = {  # sha256 of the job files rc23 cites, as recorded in JANELA-LANCAMENTO.md and the manifest
    "resumo": "ec10bd52cdebf43f35ee748e82787cb6b342be0e1b8637e8d750ad24cb304219",
    "det": "f36f1325a6b7da34d3a11b96d9c7b632d0e8b4494b67c1ec155244a168c44c58",
    "runs": "02c570de5c5f32c520621636273dd3c4594a68fd3dc342a630cd8417ec9523e0",
    "tgz": "aa4fe1e0e30fc3f1152dd381cffa598fec46ba6e164b058ff079b4ab06a5d871",
    "janela": "6cff1885c17eff237e3a0b912cff0f91c7e0be8902830890394872cebcf14df3",
    "reader": "22abd1b4a5ffde3206ae75dae8986571c7d16901068411d04ab8a6bdb99e9cb1",
    "detpy": "317a844bead72e8c7dd2a0989b9d19ed69047f993d1512d1703da54697cd3717",
    "manifest": "d310e4e9354206a55434dea2662ec154ec9ea7d352bf1bc9dce9057e1ce973b6",
    "manifest_prev": "172c5382bcc79d23b06ff050c8a2dd8bfcf9458fbbce8aa2b4e0a14b724c00ee",
}
SOURCES23 = {
    "resumo": J2 / "RESUMO.json", "det": J2 / "DETERMINISMO.json", "runs": J2 / "RUNS.sha256",
    "concl": J2 / "CONCLUIDO", "recibo": J2 / "RECIBO.txt", "status": J2 / "STATUS",
    "instr": J2 / "INSTRUMENTO.sha256", "bancos": J2 / "BANCOS.sha256",
    "instr_v2b": V2B / "INSTRUMENTO.sha256", "bancos_v2b": V2B / "BANCOS.sha256",
    "janela": SHAM / "JANELA-LANCAMENTO.md", "excl": SHAM / "janela-lancamento" / "ts-janela-excluidos-53.txt",
    "tsall": SHAM / "calibration" / "ts-janela.txt", "exp": P2 / "out" / "expiracao-designados-2026-09-09.json",
}
OPTIONAL23 = {
    "manifest": LASTRO / "MANIFESTO-LASTRO-P2.json",
    "manifest_prev": LASTRO / "manifestos-anteriores" / "MANIFESTO-LASTRO-P2.172c5382bcc7.json",
    "receipt": LASTRO / RECEIPT23,
}


def sha_b(b):
    return hashlib.sha256(b).hexdigest()


@functools.lru_cache(maxsize=1)
def _tgz_facts():
    """Hash the 21 runs inside the .tgz and read REAL.json's zero-bonus states (done once)."""
    tgz = SHAM / "job-janela2-runs.tgz"
    out = dict(tgz_sha=sha_b(tgz.read_bytes()), members={}, zero_boost=None)
    with tarfile.open(tgz) as tf:
        for m in tf.getmembers():
            if m.isfile() and m.name.endswith(".json"):
                b = tf.extractfile(m).read()
                out["members"][m.name.split("/")[-1]] = sha_b(b)
                if m.name.endswith("/REAL.json"):
                    det = json.loads(b)["dose"]["detalhe"]
                    z = sorted(x["ts"] for x in det if float(x["w"]) == 4 and x["boosts_emitidos"] == 0)
                    out["zero_boost"] = (len(z), z[0] if z else None)
    return out


def load_src23():
    src = {k: p.read_text(encoding="utf-8") for k, p in SOURCES23.items()}
    src["_sha"] = {k: sha_b(SOURCES23[k].read_bytes()) for k in ("resumo", "det", "runs", "janela")}
    src["_sha"]["reader"] = sha_b((P2 / "measurement" / "sprint-resume-sham-v2.py").read_bytes())
    src["_sha"]["detpy"] = sha_b((P2 / "measurement" / "sprint-determinismo-janela2.py").read_bytes())
    for k, p in OPTIONAL23.items():
        src[k] = p.read_text(encoding="utf-8") if p.exists() else None
    src["_tgz"] = dict(_tgz_facts())
    return src


def nf(n):
    return f"{n:,}"


def facts23(src):
    """The numbers rc23 states, computed from the job's files with the pre-committed rule."""
    r = json.loads(src["resumo"])
    pr = r["por_run"]
    shams = sorted(k for k in pr if k.startswith("SHAM-"))
    K = len(shams)
    f = dict(K=K)
    for m in ("mexeu", "churn_total"):
        real = pr["REAL"]["4.0"][m]
        xs = [pr[s]["4.0"][m] for s in shams]
        ge = sum(1 for x in xs if x >= real)
        f[m] = dict(real=real, lo=min(xs), hi=max(xs), ge=ge, ties=sum(1 for x in xs if x == real),
                    p=round((1 + ge) / (K + 1), 4))
    pc = [pr[s]["100000.0"]["mexeu"] for s in shams]
    f["pc"] = dict(real=pr["REAL"]["100000.0"]["mexeu"], lo=min(pc), hi=max(pc))
    f["estados"] = {pr[k]["4.0"]["estados"] for k in pr} | {pr[k]["100000.0"]["estados"] for k in pr}
    f["erros"] = sum(pr[k]["erros"] for k in pr)
    f["boosts"] = {json.dumps(pr[k]["4.0"]["boosts"], sort_keys=True) for k in pr}
    fr = r["fidelidade_real"]
    f["fid"] = (fr["estados"], fr["controle_igual"], fr["estados_com_w_de_producao"], fr["churn_e_entra_iguais"])
    f["gap"] = f["mexeu"]["real"] - f["mexeu"]["hi"]
    return r, f


def expected_sentences(f):
    m, c, pc = f["mexeu"], f["churn_total"], f["pc"]
    n, _, nw, _ = f["fid"]
    return [
        (f"| states moved (`mexeu`) | **{m['real']}** | {m['lo']}–{m['hi']} | {m['ge']} | **{m['p']:.4f}** |", "C table, mexeu"),
        (f"| total churn | **{c['real']}** | {c['lo']}–{c['hi']} | {c['ge']} | **{c['p']:.4f}** |", "C table, churn"),
        (f"`w = 100 000`, the positive control, the real designation moves {pc['real']} states and the shams "
         f"{pc['lo']}–{pc['hi']}.", "C positive control"),
        (f"The real run reproduces production's control set in {nf(n)}/{nf(n)} states", "C fidelity, control"),
        (f"its churn and entering id in {nf(nw)}/{nf(nw)}.", "C fidelity, w = 4"),
        (f"by {f['gap']} states over the largest ({m['real']} against {m['hi']})", "C what it adds"),
        (f"({m['real']} against {m['lo']}–{m['hi']}), with `p = 1/21`, the floor for 20 shams, in both.", "SH abstract"),
        (f"rank 1 of 21 again, {m['real']} against {m['lo']}–{m['hi']} (§4.0.1c)", "B01 §4.0.1b row"),
        (f"whole-window sham: {m['real']} / {c['real']} against {m['lo']}–{m['hi']} / {c['lo']}–{c['hi']}, "
         f"{m['ge']} shams ≥ real, `p = {m['p']:.4f}`; {pc['real']} against {pc['lo']}–{pc['hi']} at `w = 100 000`; "
         f"{nf(n)}/{nf(n)} and {nf(nw)}/{nf(nw)}", "SH B.1 row"),
        (f"changed {m['real']} brief states of the trial window against {m['lo']}–{m['hi']} for 20 matched shams, "
         f"`p = 1/21`", "ST status"),
        (f"real {m['real']} changed states against {m['lo']}–{m['hi']} (churn {c['real']} against {c['lo']}–{c['hi']}), "
         f"{m['ge']} shams at or above the real designation, `p = 1/21`; positive control {pc['real']} against "
         f"{pc['lo']}–{pc['hi']}", "SH working list 15"),
        (f"was run as item 15 (rc23): real {m['real']} against {m['lo']}–{m['hi']}, `p = 1/21`.", "SH working list 9"),
    ]


# ---------------------------------------------------------------- S23: the facts rc23 rests on
def source_facts_rc23(src, new):
    fails, warns = [], []
    for k in ("resumo", "det", "runs", "janela", "reader", "detpy"):
        if src["_sha"][k] != PINS[k]:
            fails.append(f"S23/H: {k} sha256 {src['_sha'][k][:12]}… is not the pinned {PINS[k][:12]}…")
    # completion: STATUS, CONCLUIDO = RUNS.sha256, RECIBO
    if not src["status"].startswith("CONCLUIDO 2026-10-07T02:09:46Z 21/21 validadas"):
        fails.append("S23/J: STATUS is not CONCLUIDO 2026-10-07T02:09:46Z 21/21")
    if src["runs"] != src["concl"]:
        fails.append("S23/J: RUNS.sha256 is not a copy of CONCLUIDO")
    rec = src["recibo"].splitlines()
    if not rec or rec[-1] != "fim 2026-10-07T02:09:46Z -- 21/21 corridas validadas em 145793s":
        fails.append("S23/J: RECIBO does not end with the 21/21 completion line")
    if sum(1 for l in rec if re.search(r" VALIDADA \(\d+/21\)$", l)) != 21 or any("exit=" in l and "exit=0 " not in l for l in rec):
        fails.append("S23/J: RECIBO does not show 21 validations with every exit 0")
    for s in ("SHAM-017", "SHAM-018", "SHAM-019"):
        if not any(l.split()[1:3] == [s, "exit=0"] for l in rec if len(l.split()) > 2):
            fails.append(f"S23/J: RECIBO has no exit 0 line for {s}")
    # the 21 runs: RUNS.sha256 against the .tgz members
    exp = {}
    for line in src["runs"].splitlines():
        h, nome = line.split(maxsplit=1)
        exp[nome.strip().lstrip("*")] = h
    tg = src["_tgz"]
    want = {"REAL.json"} | {f"SHAM-{i:03d}.json" for i in range(20)}
    if set(exp) != want:
        fails.append(f"S23/T: RUNS.sha256 lists {len(exp)} runs, not REAL + SHAM-000..019")
    if tg["tgz_sha"] != PINS["tgz"]:
        fails.append("S23/T: job-janela2-runs.tgz is not the pinned bytes")
    if tg["members"] != exp:
        fails.append("S23/T: the runs inside the .tgz do not match RUNS.sha256")
    # instrument and databases: 28 of 29 equal to job-v2b, line 6 the state list; banks equal
    a = [l.split()[0] for l in src["instr"].splitlines() if l.strip()]
    b = [l.split()[0] for l in src["instr_v2b"].splitlines() if l.strip()]
    if len(a) != 29 or len(b) != 29 or [i for i in range(29) if a[i] != b[i]] != [5]:
        fails.append("S23/I: the instrument pins are not 29, equal to job-v2b's except line 6")
    if not src["instr"].splitlines()[5].endswith("cal/ts-janela-reconstruivel.txt") or not a[5].startswith("956e712e"):
        fails.append("S23/I: line 6 of the pins is not the 11,812-state list 956e712e…")
    if [l.split()[0] for l in src["bancos"].splitlines()] != [l.split()[0] for l in src["bancos_v2b"].splitlines()]:
        fails.append("S23/I: the database pins differ from job-v2b's")
    # the state set: 11,865 − 53, 52 of them on 2026-09-21 and 1 on 2026-09-06
    tsall = [l.strip() for l in src["tsall"].splitlines() if l.strip()]
    excl = [l.strip() for l in src["excl"].splitlines() if l.strip()]
    if (len(tsall), len(excl), len(set(tsall) - set(excl))) != (11865, 53, 11812):
        fails.append("S23/W: the window is not 11,865 − 53 = 11,812 states")
    if collections.Counter(x[:10] for x in excl) != {"2026-09-21": 52, "2026-09-06": 1}:
        fails.append("S23/W: the 53 exclusions are not 52 on 2026-09-21 and 1 on 2026-09-06")
    if tsall[0][:19] != "2026-09-03T17:23:39":
        fails.append("S23/W: the window does not start at 2026-09-03T17:23:39Z")
    # the result, recomputed from the per-run counts with the pre-committed rule
    r, f = facts23(src)
    if r["status"] != "CONCLUIDO 2026-10-07T02:09:46Z 21/21 validadas" or f["K"] != 20 or r["w"] != 4.0:
        fails.append("S23/R: RESUMO is not the K = 20, w = 4 summary of the CONCLUIDO job")
    for m in ("mexeu", "churn_total"):
        t = r["teste"][m]
        if (t["real"], min(t["shams"]), max(t["shams"]), t["shams_ge_real"], t["p"]) != \
                (f[m]["real"], f[m]["lo"], f[m]["hi"], f[m]["ge"], f[m]["p"]):
            fails.append(f"S23/R: RESUMO's test block for {m} disagrees with its own per-run counts")
        if f[m]["ge"] != 0 or f[m]["ties"] != 0 or f[m]["p"] != 0.0476:
            fails.append(f"S23/R: {m}: shams ≥ real {f[m]['ge']}, ties {f[m]['ties']}, p {f[m]['p']} (text says 0, 0, 0.0476)")
    if f["estados"] != {11812} or f["erros"] != 0:
        fails.append("S23/R: not every run has 11,812 states at both doses with 0 errors")
    if f["boosts"] != {json.dumps({"0": 235, "19": 11577}, sort_keys=True)}:
        fails.append("S23/R: not every run has 235 states without a bonus and 11,577 with 19")
    if f["fid"] != (11812, 11812, 2016, 2016):
        fails.append("S23/R: the real run's fidelity is not 11,812/11,812 and 2,016/2,016")
    zb = src["_tgz"]["zero_boost"]
    expiry = "2026-09-20T22:51:23"
    if not zb or zb[0] != 235 or zb[1] < expiry:
        fails.append("S23/R: the 235 states without a bonus are not all after the expiry")
    if expiry.replace("T", " ") not in src["exp"].replace("T", " "):
        fails.append("S23/R: the expiry artifact no longer gives 2026-09-20 22:51:23")
    # determinism
    d = json.loads(src["det"])
    if not d["ok"] or (d["REAL_vs_job_v2b"]["compartilhados"], d["REAL_vs_job_v2b"]["identicos"],
                       d["REAL_vs_job_v2b"]["estados"]) != (4032, 4032, 2016) \
            or (d["REAL_vs_amostra200"]["identicos"], d["REAL_vs_amostra200"]["estados"]) != (400, 200) \
            or d["shams_todos_identicos"] != "20/20" \
            or any((v["compartilhados"], v["identicos"], v["mesma_designacao"]) != (4032, 4032, True)
                   for v in d["SHAMS_vs_job_v2b"].values()):
        fails.append("S23/D: DETERMINISMO is not 4,032/4,032 per run, 400/400 on the sample, 20/20 shams")
    # the launch record carries the result and the reader's bytes
    jl = src["janela"]
    if "## Result (`job-janela2`, CONCLUIDO 2026-10-07T02:09:46Z, 21/21 validated)" not in jl \
            or "reader `22abd1b4…`" not in jl or "ts-janela-excluidos-53" not in jl:
        fails.append("S23/L: JANELA-LANCAMENTO.md does not record the result, the reader 22abd1b4… and the exclusions")
    # ballast manifest and receipt (outside the repository)
    if src["manifest"] is None or src["manifest_prev"] is None:
        warns.append("S23/M: ballast manifest not on this machine: 115 artifacts, 79/36 and the rc23 entries NOT VERIFIED")
    else:
        mj, mp = json.loads(src["manifest"]), json.loads(src["manifest_prev"])
        if sha_b(src["manifest"].encode()) != PINS["manifest"] or sha_b(src["manifest_prev"].encode()) != PINS["manifest_prev"]:
            fails.append("S23/M: the manifest or its kept predecessor is not the pinned bytes")
        if (mj["n_artefatos"], mj["bytes_totais"]) != (115, 184509309) or round(mj["bytes_totais"] / 2 ** 20) != 176:
            fails.append("S23/M: the manifest does not hash 115 artifacts, 184 509 309 bytes (176 MiB)")
        if mj["artefatos"][:50] != mp["artefatos"] or mp["n_artefatos"] != 50:
            fails.append("S23/M: the 50 earlier entries are not identical to the kept 172c5382… manifest")
        ext = mj["extensoes"][-1]
        if (ext["rotulo"], ext["adicionados"], ext["manifesto_anterior_sha256"]) != ("item15-janela2", 65, PINS["manifest_prev"]):
            fails.append("S23/M: the last extension is not item15-janela2, 65 entries, after 172c5382…")
        dentro = [e for e in mj["artefatos"] if "/Claude/Projetos/memoria-nox/" in e.get("caminho", "")]
        if (len(mj["artefatos"]) - len(dentro), len(dentro)) != (79, 36):
            fails.append("S23/M: outside / inside the repository is not 79 / 36")
        names = {e["nome"] for e in mj["artefatos"]}
        for nm in ("ITT-PRELIMINAR.json", "STABILITY-TEST.md", "_sprint-2026-10-04/receipts", "_sprint-2026-10-04/B-registered",
                   "_sprint-2026-10-04/B-sham-v2/JANELA-LANCAMENTO.md", "_sprint-2026-10-04/B-sham-v2/job-janela2/RESUMO.json",
                   "_sprint-2026-10-04/B-sham-v2/job-janela2-runs.tgz", "_sprint-2026-10-04/B-sham-v2/job-janela2/DETERMINISMO.json",
                   "_sprint-2026-10-04/B-rc18/zenodo-22110203-record.json", "_sprint-2026-10-04/B-rc19/zenodo-21978476-files.json",
                   "_sprint-2026-10-04/B-rc15/checks-rc15.json", "out/ITT-REGISTRADO-v4-2026-10-05.json",
                   "_sprint-2026-10-04/figures/figB1-h1a-inversao-registrado-v4.svg", "_sprint-2026-10-04/B-censo/GATES.md"):
            if nm not in names:
                fails.append(f"S23/M: {nm} is not in the manifest")
        if any("B-censo/raw" in n for n in names):
            fails.append("S23/M: B-censo/raw/ (episode text) is in the manifest")
        e = {x["nome"]: x for x in mj["artefatos"]}
        for k, nm in (("resumo", "_sprint-2026-10-04/B-sham-v2/job-janela2/RESUMO.json"),
                      ("janela", "_sprint-2026-10-04/B-sham-v2/JANELA-LANCAMENTO.md"),
                      ("tgz", "_sprint-2026-10-04/B-sham-v2/job-janela2-runs.tgz")):
            if nm in e and e[nm]["sha256"] != PINS[k]:
                fails.append(f"S23/M: the manifest hashes {nm} as other bytes")
    if src["receipt"] is None:
        warns.append(f"S23/RC: {RECEIPT23} not on this machine: the 79/79 legs NOT VERIFIED")
    else:
        rc = src["receipt"]
        for needle in ("local 79/79, 0 divergem", "remoto 79/79 (79 examinados = 79 locais), exit 0",
                       "local 16/16, remoto 16/16", "= 36/36", "entradas antigas byte-idênticas: 50/50",
                       PINS["manifest"]):
            if needle not in rc:
                fails.append(f"S23/RC: the receipt does not record {needle[:40]!r}")
        if re.search(r"\b\d{1,3}(?:\.\d{1,3}){3}\b", rc):
            fails.append("S23/RC: the receipt carries an IP address")
    # the result sentences, in the exact form the files give
    fn = flat(R11.strip_struck(new.replace("\n> ", "\n")))
    for txt, why in expected_sentences(f):
        if flat(txt) not in fn:
            fails.append(f"S23/X: {why}: expected {txt[:90]!r}")
    return fails, warns


# ---------------------------------------------------------------- 1: anchors
ANCHORS = [
    ("ST", "rc23 prepared 2026-10-07 (the whole-window sham result integrated"),
    ("SH", "reported in §4.0.1c (rc23)"),
    ("SH", "including two sham replays"),
    ("P11", "entered the ballast manifest only in rc23"),
    ("B01", "rank 1 of 21 again"),
    ("C", "**measured (rc23)**: control set equal to production in 11,812/11,812"),
    ("C", "and again for the whole-window run"),
    ("C", "Its result follows these limits."),
    ("C", "was then run (`job-janela2`"),
    ("C", "**The whole-window sham, run (2026-10-05 to 2026-10-07).**"),
    ("C", "and again over the whole hash-verified trial window, that"),
    ("C", "For the whole-window sham:"),
    ("SH", "propensity for a fixed population."),
    ("SH", "was run twice with the same"),
    ("SH", "§4.0.1b. The sham replay, the placebo-like"),
    ("SH", "again over the whole hash-verified trial window (§4.0.1c)."),
    ("SH", "served over the hash-verified trial window (without epoch `09-01`)"),
    ("AB", "In the ballast manifest from rc23 (working list 17)"),
    ("AB", "in the ballast manifest from rc23"),
    ("AB", "SHA-256 hashes of the 115 artifacts currently covered"),
    ("AB", "the whole-window sham of §4.0.1c (21 runs, 11,812 states each)"),
    ("AB", "65 more on 2026-10-07"),
    ("AB", "**79/79**"),
    ("SH", "whole-window sham: 790 / 868"),
    ("WL", "*(rc23: 15 and 17 are done"),
    ("SH", "(whole-window sham)~~."),
    ("SH", "was run as item 15"),
    ("SH", "real 132 against 81–122, `p = 1/21`. The larger set"),
    ("SH", "15. ~~**Whole-window sham**"),
    ("WL", "*(rc23: both entered on 2026-10-07"),
    ("SH", "→ **Done, rc23 (2026-10-07)**: `job-janela2`"),
    ("WL", "~~**Ballast for the rc7 and rc8 evidence**~~"),
    ("WL", "→ **Done, rc23 (2026-10-07)**: 65 entries"),
    ("WL", "*(rc23: rc23 integrates"),
    ("CL", "**rc23: whole-window sham result integrated; ballast extended**"),
]
REMOVED_ANCHORS = [(S_OPEN, "SH")]  # the lone opening marker before the §4.0.1c heading

# ---------------------------------------------------------------- 2: numbers
JUSTIFIED_REMOVED = {
    "2026-10-07T03:00Z": (3, "SH: the job's ETA (status header, §4.0.1c first limit, B.1); it finished 02:09:46Z"),
    "2026-10-05T09:39:53Z": (2, "SH: the relaunch time in the status header and B.1; §4.0.1c keeps it"),
    "50": (2, "AB: 'for 50 artifacts' and 'the 50 artifacts currently covered'; the manifest now has 115"),
    "158": (1, "AB: the 158 MiB of the 50-artifact manifest; now 176 MiB"),
    "34": (1, "AB: 'the other 34 are versioned'; now 36"),
    "16": (1, "AB: 'copies the 16 that live outside'; now 79 (16/16 kept as the earlier check)"),
    "17": (3, "AB: two 'not in the ballast manifest, working list 17' cells and the paragraph's "
              "'(working list 17)'; item 17 is done"),
    "2026-10-05": (3, "AB: the rc7-rc19 file list of the ballast paragraph condensed (three file names dated "
                      "2026-10-05 no longer spelled out there; each keeps its own row)"),
}


def derived_rc23(src):
    out = {}
    r, f = facts23(src)
    out[str(f["gap"])] = "790 − 583: the real designation over the largest sham (RESUMO)"
    for k in ("2026-10-07", "2026-10-07T02:09:46Z", "02:09:46Z"):
        out[k] = "completion time (STATUS, RECIBO)"
    out["12:02Z"] = "time of the post-check receipt recibos/backup-20261007T120248Z.txt"
    out["2026-09-03T17:23:39Z"] = "first state of the window (calibration/ts-janela.txt)"
    out["2026-09-06"] = out["2026-09-21"] = out["52"] = "the 53 exclusions by date (ts-janela-excluidos-53.txt)"
    out["15"] = "18 − 3: the epochs the window adds to the three w = 4 epochs it shares"
    out["28"] = out["29"] = "instrument pins: 29, 28 equal to job-v2b (INSTRUMENTO.sha256)"
    out["176"] = "184 509 309 bytes / 2^20, rounded (manifest)"
    for n, why in ((79, "artifacts outside the repository"), (36, "artifacts versioned in the repository"),
                   (65, "entries appended by item15-janela2"), (115, "manifest entries"),
                   (184509309, "manifest bytes")):
        out[str(n)] = f"manifest: {why} (checked in S23/M)"
    out["11577"] = "states with 19 bonuses (RESUMO boosts)"
    d = json.loads(src["det"])
    out[nf(d["REAL_vs_job_v2b"]["estados"])] = "states shared with job-v2b (DETERMINISMO, checked in S23/D)"
    out[nf(d["REAL_vs_job_v2b"]["compartilhados"])] = "records shared per run, both doses (DETERMINISMO)"
    return out


def artifact_numbers_rc23(src):
    allowed = {}
    for name in ("resumo", "det"):
        for v in R11.leaves(json.loads(src[name])):
            for fm in R11.forms(v):
                allowed.setdefault(fm, name)
    return allowed


# ---------------------------------------------------------------- 3/4: tail
TAIL_INSERTS = [
    """
   *(rc23: 15 and 17 are done, so none of the items named here blocks the deposit any longer;
   the deposit itself is not done.)*""",
    """
    *(rc23: rc23 integrates the whole-window sham result and closes items 15 and 17
    (`APPLY-B-rc23.md`); it has not been reviewed.)*""",
]
TAIL_EDITS = [  # (rc22 text, rc23 text)
    ("and~~ " + S_OPEN + "15\n   (whole-window sham)." + S_CLOSE + " Also blocked by 17",
     "and~~ ~~15\n   (whole-window sham)~~. Also blocked by 17"),
    (S_OPEN + """The larger set
   (~~the 11,865 states of the trial window, about 36 h~~ 11,812 reconstructible states of
   the trial window) ~~is configured and not run~~ is running as item 15.""" + S_CLOSE,
     """The larger set
   (~~the 11,865 states of the trial window, about 36 h~~ 11,812 reconstructible states of
   the trial window) ~~is configured and not run~~ ~~is running as item 15~~ was run as item 15
   (rc23): real 790 against 449–583, `p = 1/21`."""),
    ("""they enter together when the job completes.
""", """they enter together when the job completes. *(rc23: both entered on 2026-10-07,
    with the rc7–rc23 artifacts; item 17.)*
"""),
    ("""rc3 itself has not been reviewed.""" + S_OPEN + """
15. **Whole-window sham**: the replay over the trial window, 11,812 reconstructible states of
    18 epochs (without epoch `09-01`, whose corpus has no hash proof, and without 53 states
    whose serve-state cut cannot be reconstructed), job `job-janela2`, relaunched
    2026-10-05T09:39:53Z, expected to finish about 2026-10-07T03:00Z. Add its result to
    §4.0.1c, §7 and B.1 before deposit.""" + S_CLOSE,
     """rc3 itself has not been reviewed.
15. ~~**Whole-window sham**: the replay over the trial window, 11,812 reconstructible states of
    18 epochs (without epoch `09-01`, whose corpus has no hash proof, and without 53 states
    whose serve-state cut cannot be reconstructed), job `job-janela2`, relaunched
    2026-10-05T09:39:53Z, expected to finish about 2026-10-07T03:00Z. Add its result to
    §4.0.1c, §7 and B.1 before deposit.~~ → **Done, rc23 (2026-10-07)**: `job-janela2`
    CONCLUIDO 2026-10-07T02:09:46Z, 21/21 runs validated, instrument and databases re-hashed
    on the host after completion; real 790 changed states against 449–583 (churn 868 against
    484–612), 0 shams at or above the real designation, `p = 1/21`; positive control 894
    against 462–591; the 2,016 states shared with the first run identical in all 21 runs.
    Reported in §4.0.1b, §4.0.1c, §7, §8.3, §8.5, the Abstract and B.1
    (`_sprint-2026-10-04/APPLY-B-rc23.md`)."""),
    ("17. **Ballast for the rc7 and rc8 evidence**: add", "17. ~~**Ballast for the rc7 and rc8 evidence**~~: add"),
    ("""    they are, this item blocks the deposit (item 8).
""", """    they are, this item blocks the deposit (item 8). → **Done, rc23 (2026-10-07)**: 65 entries
    appended under the label `item15-janela2` without regenerating the manifest, the 50
    existing ones byte-identical: every artifact listed here, the whole-window sham of item 15
    with `JANELA-LANCAMENTO.md`, `STABILITY-TEST.md` and `receipts/` (`B-censo/raw/` left out:
    it holds episode text). The manifest now hashes **115** artifacts (184 509 309 bytes =
    176 MiB; sha256 `d310e4e9…`, previous versions kept). The 79 that live outside the
    repository are in both copies, **79/79 recomputed at the destination on each leg**, after a
    pre-check with nothing copied (16/16 on each leg); the 36 versioned ones, **36/36**
    recomputed from `origin/main` (receipt `RECIBO-ITEM15-20261007T120404Z.txt`, with
    `recibos/backup-20261007T120120Z.txt` and `…T120248Z.txt`).
"""),
]
CL_ITEMS = [(188, "§4.0.1c:"), (189, "§4.0.1b table, specificity row"), (190, "Abstract: two sham replays"),
            (191, "§7 \"Scope of the specificity control\", §8.3 and §8.5"), (192, "§1.1: `ITT-PRELIMINAR.json`"),
            (193, "Appendix B: rows for the whole-window sham"), (194, "Working list 8, 9, 10, 15 (done), 17 (done), 24")]

# ---------------------------------------------------------------- 6: locks
SWEEP_LOCK_RC23 = [
    (r"(?i)\bis (?:now )?running\b[^.]{0,80}(?:job-janela|whole[- ]window|trial window)", "SH: the window sham is no longer running"),
    (r"(?i)whole[- ]window sham, running", "SH: B.1 says running"),
    (r"(?i)result will be added before deposit", "SH: the result is integrated"),
    (r"(?i)expected to finish about 2026-10-07", "SH: the job finished"),
    (r"(?i)launch record; no result yet", "SH: JANELA-LANCAMENTO.md holds the result"),
    (r"(?i)not yet in the ballast manifest", "AB: working list 17 is done"),
    (r"(?i)not in the ballast manifest, working list 17", "AB: working list 17 is done"),
    (r"(?i)the 50 artifacts currently covered", "AB: the manifest covers 115"),
    (r"(?i)are \*\*not yet in\s+the ballast manifest\*\*", "AB: the rc7-rc19 artifacts are in it"),
    (r"(?i)specificity control covers what was served on the `w = 4` epochs only", "SH §8.5: the window"),
    (r"(?i)covers the 2,646 brief states of the four `w = 4` epochs, not the whole window", "SH §7: the window"),
    (r"(?i)a calibrated randomization p-value(?:[^.]{0,20})\bfor the window\b", "do not upgrade the rank"),
    (r"(?i)independent replication", "the window run contains the w = 4 states; it is not independent"),
]
PRESENT_RC23 = [
    ("No sham equals the real designation on either statistic; the only ties are between shams.", "C ties"),
    ("the replay is deterministic, and this run is not independent of the first, it extends it to the other 15 "
     "epochs and leaves out `09-01`.", "C not independent"),
    ("The other three limits are unchanged (shams from the 36 boostable items; a match on severity and bonus "
     "mass, not on signature group; `p` at its floor), and it says nothing about outcomes.", "C limits"),
    ("the exclusion is a property of the data, fixed when the first attempt stopped on them, and does not depend "
     "on the outcome.", "C exclusion"),
    ("The statistic, the p rule and the positive control are those above, fixed before the job ran.", "C pre-committed"),
    ("the second replay contains the states of the first (without `09-01`) rather than replicating it, and it says "
     "nothing about outcomes (§4.0.1c).", "SH abstract caveat"),
    ("it does not establish specificity against every matched designation, nor an effect on outcomes.", "SH §7"),
    ("SHA-256 hashes of the 115 artifacts currently covered, for loss detection: from rc23, every artifact in this "
     "table (`B-censo/raw/` excepted, see its row)", "AB manifest row"),
    ("`B-censo/raw/`, which holds episode excerpts and panelist reasons, is not in the manifest.", "AB raw excluded"),
    ("so the manifest does not date it either.", "P11"),
    ("(added in rc19; in the ballast manifest from rc23) |\n| `_sprint-2026-10-04/B-rc19/zenodo-21978476-record.json`",
     "L2/L4 replaced: the rc18 snapshot row says in the manifest"),
    ("the Zenodo snapshots in `B-rc18/` and `B-rc19/`, and `receipts/`)", "L6 replaced: the paragraph lists the snapshots"),
]
PRESENT_REPLACED = {  # rc19's L2/L4 and L6 locks pinned "not in the manifest", which rc23 makes false
    "(added in rc19; not in the ballast manifest, working list 17) |\n| `_sprint-2026-10-04/B-rc19/zenodo-21978476-record.json`":
        "L2/L4: the snapshots are in the manifest from rc23",
    "the rc15 Figure B1, and the Zenodo snapshots of rc18 and rc19 in `B-rc18/` and `B-rc19/`) are **not yet in the "
    "ballast manifest** (working list 17)": "L6: the rc7-rc19 artifacts are in the manifest from rc23",
}
STATUS_MARKS_RC23 = R22.STATUS_MARKS_RC22 + ["rc23 prepared 2026-10-07 (the whole-window sham result integrated",
                                             "rc23 has not been reviewed"]
STATUS_LOCK = R22.STATUS_LOCK
STRUCK_DELTA = {}   # filled from --report

# ---------------------------------------------------------------- 7: qualifier deltas
JUSTIFIED_PHRASE = {
    ("SHA-256 hashes of the 115 artifacts currently covered", +1):
        "AB: the live manifest-coverage headline (rc11) now reads 115; rc22's row did not carry the phrase",
}
JUSTIFIED_HEDGE = {
    "AB": ({"not": -20, "every": 2, "registered": 2, "without": 1},
           "nineteen 'not yet in the ballast manifest' cells and the paragraph's 'not yet' become 'in the ballast "
           "manifest from rc23'; 'every artifact' (manifest row, paragraph), 'registered analyses/analysis' and "
           "'without raw/' in the condensed ballast paragraph"),
    "C": ({"every": 6, "not": 3, "no": 4, "cannot": 1, "only": 1, "all": 3, "any": 1, "either": 1, "still": 1},
          "the whole-window paragraphs: 'every reconstructible state', 'no rowid cut … under any designation', "
          "'not independent', 'no sham equals … either statistic', 'cannot be located', 'still out', 'not on "
          "signature group'; the limit's 'expected to finish about' replaced by 'completed'"),
    "P11": ({"only": 1, "either": 1}, "§1.1: 'entered the manifest only in rc23 … does not date it either'"),
    "SH": ({"about": -2, "without": 3, "rather": 2, "not": -1, "cannot": 1, "still": 1, "only": -1, "all": 1},
           "status and B.1 lose the ETA ('expected … about'); §7 and §8.5 lose 'w = 4 epochs only' and 'not the "
           "whole window' and gain 'without 09-01', 'rather than replicating', 'still leaves out', 'cannot be "
           "reconstructed'; the Abstract gains 'rather than replicating it' and 'without 09-01'"),
    "ST": ({"not": 1}, "status: 'rc23 has not been reviewed'"),
}


def carried_present():
    return [p for p in R22.carried_present() + R22.PRESENT_RC22 if p[0] not in PRESENT_REPLACED]


def check(old, new, verbose=True, report=False, cz=None, st=None, A=None, files=None, files15=None,
          src=None, src18=None, src19=None, src20=None, src21=None, src22=None, src23=None):
    cz = cz or R13.load_rc13()
    st = st or R13.load_paths()
    A = A or load()
    src = src or {k: p.read_text(encoding="utf-8") for k, p in R17.SOURCES.items()}
    src18 = src18 or R18.load_src18()
    src19 = src19 or R19.load_src19()
    src20 = src20 or R20.load_src20()
    src21 = src21 or R21.load_src21()
    src22 = src22 or R22.load_src22()
    src23 = src23 or load_src23()
    if files is None:
        files = {k: p.read_bytes() for k, p in R15.ART.items()}
        files["res4_frozen"] = R17.RES4_FROZEN.read_bytes()
    files15 = files15 or {"py": R16.FROZEN_TEST_PY.read_bytes(), "json": R16.FROZEN_TEST_JSON.read_bytes()}
    fails, rep = [], []
    if hashlib.sha256(old.encode()).hexdigest() != OLD_SHA:
        fails.append("rc22 is not the 168ddd5d… bytes rc22's parity passed on")
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
    allowed23 = artifact_numbers_rc23(src23)
    der = derived_rc23(src23)
    old_nums = R11.numbers(old)
    added = {k: d for k, d in delta.items() if d > 0}
    src_add = {}
    for k in sorted(added):
        if old_nums[k]:
            src_add[k] = "in rc22"
        elif k in der:
            src_add[k] = "derived: " + der[k]
        elif k in allowed23:
            src_add[k] = "job-janela2 artifact: " + allowed23[k]
        elif k in allowed:
            src_add[k] = "artifact: " + allowed[k]
        else:
            fails.append(f"numbers: token {k!r} added {added[k]}x is neither in rc22, nor an artifact leaf, nor derived")
    # 1 hunks
    hs = R11.hunks(old, new)
    for h in hs:
        ids = [aid for aid, anc in ANCHORS if anc in h["new"]]
        ids += [aid for anc, aid in REMOVED_ANCHORS if not h["new"].strip() and anc in h["old"]]
        h["ids"] = list(dict.fromkeys(ids))
        if not h["ids"]:
            fails.append(f"hunk rc22 {h['rc10']} rc23 {h['rc11']} has no ID: {(h['new'] or h['old'])[:80]!r}")
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
                fails.append(f"invariant: struck spans moved by {d}; rc23 declares {STRUCK_DELTA}")
        elif name in R17.INV_FIXED and d:
            fails.append(f"invariant: {name} changed: {dict(list(d.items())[:4])}")
        rep.append(f"{name}: {sum(a.values())} -> {sum(b.values())}" + ("" if not d else f"  (delta {len(d)} items)"))
        if report and d and (name in R17.INV_FREE or name == "struck spans"):
            for k, v in sorted(d.items(), key=lambda kv: str(kv[0]))[:60]:
                rep.append(f"    {v:+d} {str(k)[:150]}")
    if R11.headings(old) != R11.headings(new):
        fails.append("invariant: heading list changed (rc23 changes no heading)")
    if new.count(R20.H301_NEW) != 1:
        fails.append("invariant: the rc20 §3.0.1 heading is not in rc23 exactly once")
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
    i23 = t.find("\n\n**rc23: whole-window sham result integrated; ballast extended**")
    blocks23 = t[i23:] if i23 >= 0 else ""
    t = t[:i23] + "\n" if i23 >= 0 else t
    if i23 < 0:
        fails.append("tail: the rc23 changelog block is missing")
    if t != to:
        fails.append("tail: working list / changelog, with the declared insertions and edits reverted and the rc23 "
                     "block removed, is not byte-identical to rc22")
    i = tn.find("\n**rc14: writing pass**")
    nums = [int(x) for x in re.findall(r"^(\d+)\. ", tn[i:] if i >= 0 else "", re.M)]
    if nums != list(range(149, 195)):
        fails.append(f"tail: rc14-rc23 changelog items are {nums[-8:]}…, expected 149..194")
    for n, needle in CL_ITEMS:
        if not re.search(rf"^{n}\. {re.escape(needle)}", blocks23, re.M):
            fails.append(f"tail: changelog item {n} missing")
    if "_sprint-2026-10-04/APPLY-B-rc23.md`" not in flat(blocks23) or "CONCLUIDO 2026-10-07T02:09:46Z" not in flat(blocks23) \
            or "markers removed" not in flat(blocks23):
        fails.append("tail: the rc23 block does not name the job, the APPLY record and the marker removal")
    # 5 SHAM: rc22 had exactly the ten blocks; rc23 has none
    so, eo = R11.sham_spans(old)
    sn, en = R11.sham_spans(new)
    fails += eo + en
    if len(so) != R11.EXPECTED_SHAM:
        fails.append(f"sham: rc22 holds {len(so)} blocks, expected {R11.EXPECTED_SHAM}")
    if sn or S_OPEN in new or S_CLOSE in new or "SHAM-JANELA: pending" in new:
        fails.append("sham: a SHAM-JANELA marker is left in rc23")
    # 6 carried locks + rc23
    fails += R13.claims_rc13(new, cz)
    nb_unstruck = R11.strip_struck(nb)
    fn_unstruck = flat(nb_unstruck)
    for pat, why in (R15.SWEEP_LOCK + R16.SWEEP_LOCK_RC16 + R17.SWEEP_LOCK_RC17 + R18.SWEEP_LOCK_RC18
                     + R19.SWEEP_LOCK_RC19 + R20.SWEEP_LOCK_RC20 + R21.SWEEP_LOCK_RC21
                     + R22.SWEEP_LOCK_RC22 + SWEEP_LOCK_RC23):
        for mo in re.finditer(pat, fn_unstruck):
            fails.append(f"sweep: {why}: {fn_unstruck[max(0, mo.start() - 60):mo.end() + 30]!r}")
    head = new[:new.find("\n---")]
    for mk in STATUS_MARKS_RC23:
        if mk not in head and flat(mk) not in flat(head.replace("> ", " ")):
            fails.append(f"status: header does not record {mk.splitlines()[0]!r}")
    for pat, why in STATUS_LOCK:
        if re.search(pat, flat(head.replace("> ", " "))):
            fails.append(f"status: {why}")
    for txt, why in carried_present() + PRESENT_RC23:
        if flat(txt) not in fn_unstruck:
            fails.append(f"present: {why} sentence missing: {txt[:70]!r}")
    for txt in PRESENT_REPLACED:
        if flat(txt) in fn_unstruck:
            fails.append(f"present: replaced rc22 text still present: {txt[:70]!r}")
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
                fails.append(f"qualifier: {ph[:70]!r} occurs {b}x in rc23 against {a}x in rc22, not justified")
    for (ph, d) in JUSTIFIED_PHRASE:
        if pdeltas.get(ph) != d:
            fails.append(f"qualifier: JUSTIFIED_PHRASE lists {ph[:50]!r} {d:+d}; measured {pdeltas.get(ph, 0):+d}")
    gone = {ph for (ph, d) in list(JUSTIFIED_PHRASE) + list(R22.JUSTIFIED_PHRASE) + list(R21.JUSTIFIED_PHRASE)
            + list(R20.JUSTIFIED_PHRASE) + list(R19.JUSTIFIED_PHRASE) + list(R18.JUSTIFIED_PHRASE)
            + list(R17.JUSTIFIED_PHRASE) + list(R16.JUSTIFIED_PHRASE) + list(R15.JUSTIFIED_PHRASE)
            if d < 0 and fnn.count(ph) == 0}
    for k, v in h15.items():
        if flat(v) not in fnn and flat(v) not in gone:
            fails.append(f"headline: {k} — {v[:80]!r} not found in rc23")
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
    # 8 integrity: rc22's carried checks (S, S18..S22), S19/L6 replaced by S23/M, then S23
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
    f19 = [x for x in f19 if not x.startswith("S19/L6")]   # replaced by S23/M (rc23 extends the manifest)
    f20, w20 = R20.source_facts_rc20(src20)
    f23, w23 = source_facts_rc23(src23, new)
    fails += f19 + f20 + R21.source_facts_rc21(src21, new) + R22.source_facts_rc22(src22, new) + f23
    warns = list(warns) + w19 + w20 + w23
    # 9 REANALISE, bold
    if R11.R_ANY.search(new):
        fails.append("reanalise: a REANALISE marker is present in rc23")
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
        print(f"SHAM-JANELA blocks: rc22 {len(so)}, rc23 {len(sn)}")
        print(f"words: rc22 {len(old.split())} (body {len(body(old).split())}), "
              f"rc23 {len(new.split())} (body {len(body(new).split())})")
        for w in warns:
            print(w)
    if report:
        print("\nnumeric tokens added (and their source):")
        for k in sorted(added):
            print(f"  +{added[k]} {k}: {src_add.get(k, 'UNSOURCED')}")
        print("numeric tokens removed:", removed)
        print("phrase deltas:", pdeltas)
        for h in hs:
            print(f"\n[{'+'.join(h['ids']) or '?'}] rc22 l.{h['rc10'][0]}-{h['rc10'][1]} -> rc23 l.{h['rc11'][0]}-{h['rc11'][1]}")
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
    src21, src22, src23 = R21.load_src21(), R22.load_src22(), load_src23()
    rep1 = lambda a, b: (new.replace(a, b, 1), a in new)  # noqa: E731
    mutations = [
        ("SH: a marker left behind", rep1("**Scope of the specificity control.**",
                                           S_OPEN + "**Scope of the specificity control.**")),
        ("C: real mexeu 790 -> 791 in the table", rep1("| states moved (`mexeu`) | **790** |", "| states moved (`mexeu`) | **791** |")),
        ("C: largest sham 583 -> 590", rep1("| **790** | 449–583 |", "| **790** | 449–590 |")),
        ("C: p 0.0476 -> 0.0952 (churn)", rep1("| total churn | **868** | 484–612 | 0 | **0.0476** |",
                                               "| total churn | **868** | 484–612 | 0 | **0.0952** |")),
        ("C: positive control 894 -> 899", rep1("the real designation moves 894 states", "the real designation moves 899 states")),
        ("C: fidelity 2,016 -> 2,015", rep1("its churn and entering id in\n2,016/2,016.", "its churn and entering id in\n2,015/2,016.")),
        ("C: 'not independent' dropped", rep1("this run is not independent of the first, it\nextends it",
                                              "this run extends")),
        ("C: ties sentence dropped", rep1("No sham equals the real designation on either statistic; the only ties are between shams. ", "")),
        ("C: limits sentence dropped", rep1("The other three limits are unchanged", "The other limits are unchanged")),
        ("SH abstract: window numbers wrong", rep1("(790 against 449–583), with `p = 1/21`", "(790 against 449–580), with `p = 1/21`")),
        ("SH abstract: independence caveat dropped", rep1(
            " the second replay contains the states of the first\n(without `09-01`) rather than replicating it,", "")),
        ("SH: 'is running' restored in the status", rep1("21/21 runs validated), is run and\n> reported in §4.0.1c (rc23).",
                                                         "21/21 runs validated), is running, and its result will be added before deposit (§4.0.1c).")),
        ("SH §8.5: 'w = 4 epochs only' restored", rep1("served over the hash-verified trial window (without epoch `09-01`), not outcomes",
                                                        "served on the `w = 4` epochs only, not outcomes")),
        ("SH B.1: row numbers changed", rep1("whole-window sham: 790 / 868", "whole-window sham: 790 / 866")),
        ("B01: §4.0.1b row dropped", rep1("; over the 11,812 reconstructible states of the hash-verified trial window, rank 1 of 21 again, 790 against 449–583", "")),
        ("AB: 'not yet in the ballast manifest' restored", rep1("(added in rc10; in the ballast manifest from rc23)",
                                                                "(added in rc10; not yet in the ballast manifest)")),
        ("AB: manifest row 115 -> 114", rep1("SHA-256 hashes of the 115 artifacts currently covered", "SHA-256 hashes of the 114 artifacts currently covered")),
        ("AB: raw/ exclusion dropped", rep1(" `B-censo/raw/`, which holds episode excerpts and panelist reasons, is not in the\nmanifest.", "")),
        ("P11: dating caveat dropped", rep1(", so the manifest does not date it either.", ".")),
        ("WL: item 15 Done removed", rep1("~~ → **Done, rc23 (2026-10-07)**: `job-janela2`", "~~ `job-janela2`")),
        ("WL: item 17 Done altered", rep1("**79/79 recomputed at the destination on each leg**", "**78/79 recomputed at the destination on each leg**")),
        ("WL: rc23 note in item 24 dropped", rep1(TAIL_INSERTS[1], "")),
        ("CL: changelog item 191 removed", rep1("\n191. §7", "\n§7")),
        ("old changelog line edited", rep1("**rc22: final read of rc21 applied**", "**rc22: final read of rc21 applied (edited)**")),
        ("status header without rc23", rep1("rc23 prepared 2026-10-07 (the whole-window sham result integrated",
                                            "rc23 drafted 2026-10-07 (the whole-window sham result integrated")),
        ("status: 'not reviewed' dropped", rep1("; rc23 has not been reviewed).**", ").**")),
        ("carried rc22: 1.02% restored", rep1("unknown share of opportunities is 1.00%", "unknown share of opportunities is 1.02%")),
        ("carried rc21 CD: closure decision re-dated", rep1("by a decision taken on 2026-09-09", "by a decision taken on 2026-09-21")),
        ("carried title lock", rep1(TITLE, TITLE.replace("A registered horizon that", "A registration that"))),
        ("a heading changed", rep1("#### 4.0.1c The specificity control: invalid as first configured, then run",
                                   "#### 4.0.1c The specificity control")),
        ("unsourced number added", rep1("by 207 states over the largest", "by 207 states (5317 runs) over the largest")),
        ("host address added", rep1("**What it adds.**", "**What it adds (10.0.0.1).**")),
        ("H1 family untouched: H1c p moved", rep1("`p = 0.4006`", "`p = 0.4106`")),
    ]
    ok = True
    for name, (mutated, applied) in mutations:
        assert applied and mutated != new, f"mutation did not apply: {name}"
        f = [x for x in check(old, mutated, verbose=False, cz=cz, st=st, A=A, files=files, files15=files15,
                              src=src, src18=src18, src19=src19, src20=src20, src21=src21, src22=src22, src23=src23)
             if "has no ID" not in x]
        print(f"mutation [{name}]: {'CAUGHT' if f else 'MISSED'}" + (f" -> {f[0][:140]}" if f else ""))
        ok &= bool(f)

    def jmut(key, fn):
        d = json.loads(src23[key]); fn(d); return dict(src23, **{key: json.dumps(d), "_sha": dict(src23["_sha"])})

    def resumo_real(d):
        d["por_run"]["REAL"]["4.0"]["mexeu"] = 560
    def resumo_tie(d):
        d["por_run"]["SHAM-007"]["4.0"]["churn_total"] = 868
    def det_bad(d):
        d["SHAMS_vs_job_v2b"]["SHAM-011"]["identicos"] = 4031
    def resumo_fid(d):
        d["fidelidade_real"]["controle_igual"] = 11811
    s_r = jmut("resumo", resumo_real)
    s_r["_sha"]["resumo"] = PINS["resumo"]           # isolate the recomputation from the hash pin
    s_t = jmut("resumo", resumo_tie); s_t["_sha"]["resumo"] = PINS["resumo"]
    s_d = jmut("det", det_bad); s_d["_sha"]["det"] = PINS["det"]
    s_f = jmut("resumo", resumo_fid); s_f["_sha"]["resumo"] = PINS["resumo"]
    tg_bad = dict(src23["_tgz"], members=dict(src23["_tgz"]["members"], **{"SHAM-005.json": "0" * 64}))
    integ = [
        ("S23/R: REAL mexeu below a sham in RESUMO", dict(src23=s_r)),
        ("S23/R: a sham ties the real churn", dict(src23=s_t)),
        ("S23/R: fidelity 11,811", dict(src23=s_f)),
        ("S23/D: one sham not deterministic", dict(src23=s_d)),
        ("S23/H: RESUMO bytes not the pinned ones", dict(src23=dict(src23, _sha=dict(src23["_sha"], resumo="0" * 64)))),
        ("S23/H: reader script changed", dict(src23=dict(src23, _sha=dict(src23["_sha"], reader="1" * 64)))),
        ("S23/T: a run inside the .tgz differs", dict(src23=dict(src23, _tgz=tg_bad))),
        ("S23/J: SHAM-019 exit 1", dict(src23=dict(src23, recibo=src23["recibo"].replace("SHAM-019 exit=0", "SHAM-019 exit=1")))),
        ("S23/J: STATUS ABORTADO", dict(src23=dict(src23, status="ABORTADO 2026-10-07T02:09:46Z 20/21"))),
        ("S23/I: instrument line 3 differs from job-v2b", dict(src23=dict(src23, instr_v2b=src23["instr_v2b"].replace(
            src23["instr_v2b"].splitlines()[2][:8], "deadbeef", 1)))),
        ("S23/W: an exclusion moved to 09-07", dict(src23=dict(src23, excl=src23["excl"].replace("2026-09-06T", "2026-09-07T", 1)))),
        ("carried S22/ST: receipt exit 1", dict(src22=dict(src22, rcpt=src22["rcpt"].replace("\nexit: 0\n", "\nexit: 1\n", 1)))),
        ("carried S21: instruction re-timed", dict(src21=dict(src21, dev=src21["dev"].replace(
            "Toto, 2026-09-09 14:38 BRT:", "Toto, 2026-09-09 16:38 BRT:", 1)))),
    ]
    if src23["manifest"] is not None:
        integ += [
            ("S23/M: manifest re-counted 114", dict(src23=dict(src23, manifest=src23["manifest"].replace(
                '"n_artefatos": 115', '"n_artefatos": 114', 1)))),
            ("S23/RC: receipt says 78/79", dict(src23=dict(src23, receipt=src23["receipt"].replace("local 79/79", "local 78/79", 1)))),
        ]
    for name, kw in integ:
        args = dict(cz=cz, st=st, A=A, files=files, files15=files15, src=src, src18=src18, src19=src19,
                    src20=src20, src21=src21, src22=src22, src23=src23)
        args.update(kw)
        f = check(old, new, verbose=False, **args)
        print(f"mutation [{name}] (integrity): {'CAUGHT' if f else 'MISSED'}" + (f" -> {f[0][:140]}" if f else ""))
        ok &= bool(f)
    base = check(old, new, verbose=False, cz=cz, st=st, A=A, files=files, files15=files15, src=src,
                 src18=src18, src19=src19, src20=src20, src21=src21, src22=src22, src23=src23)
    print(f"unmutated rc23: {'PASS' if not base else 'FAIL'}" + (f" -> {base}" if base else ""))
    print(f"mutations: {len(mutations) + len(integ)}")
    return 0 if ok and not base else 1


if __name__ == "__main__":
    sys.exit(main())
