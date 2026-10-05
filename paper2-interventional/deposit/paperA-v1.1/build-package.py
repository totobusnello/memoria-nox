#!/usr/bin/env python3
"""Monta o pacote da v1.1 do Paper A (Zenodo 22181415 -> nova versão).

NÃO toca em deposit/paperA/: aquele MANIFEST é a prova do que a v1.0 publicou.
Os 13 arquivos da v1.0 entram na v1.1 por `files-import` no servidor (cópia byte a
byte do publicado), não por reenvio do disco — o disco já divergiu do publicado.

Saída (nesta pasta):
  artefatos-v1.1.zip, scripts-v1.1.zip   zips determinísticos (ordem e data fixas)
  MANIFEST-v1.1.json                      sha256 de CADA arquivo do pacote novo

Regras:
  - caminhos dentro dos zips são relativos a paper2-interventional/, como na v1.0;
  - cópias empacotadas passam por REDACAO (caminho pessoal -> marcador); quando a
    cópia difere do repositório, o manifesto guarda os dois sha256 e as regras;
  - gate final: nenhum byte empacotado (zips, soltos, texto do PDF) contém host,
    IP não-loopback ou caminho pessoal. Sai 1 se contiver.
"""
import hashlib
import json
import pathlib
import re
import subprocess
import sys
import zipfile

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent.parent  # paper2-interventional/

ARTEFATOS = """
out/BONUS-VS-STEP-2026-10-05.json
out/SALIENCE-COUNTERFACTUAL-PROD-2026-10-05.json
out/TIEBREAK-EXPOSURE-PROD-2026-10-05.json
out/TIEBREAK-EXPOSURE-PROD-SHARED-2026-10-05.json
_sprint-2026-10-04/A-aging/WARNING-DENSITY-recomputed-2026-10-03.json
_sprint-2026-10-04/A-aging/p2_verdict_ids-280.txt
_sprint-2026-10-04/A-filters-disaggregation/observed-main-from-log.json
_sprint-2026-10-04/A-filters-disaggregation/out-ord0826.json
_sprint-2026-10-04/A-filters-disaggregation/diag-out.txt
_sprint-2026-10-04/A-rc2/COVERAGE-SET-FROM-LOG-2026-10-04.json
_sprint-2026-10-04/A-recon-evidence/COMPARABILITY-IDENTITY-5.7.2.json
_sprint-2026-10-04/A-recon/ORGANICO-e-hashes-2026-10-04.txt
_sprint-2026-10-04/A-recon/RECON-52-e-sondas-2026-10-04.json
_sprint-2026-10-04/POOL-ELEGIVEL-2026-08-26-to-29.json
CEILING-DESIGNATION-SENSITIVITY-2026-08-28.json
CEILING-GRANULARITY-2026-08-28.json
TIEBREAK-EXPOSURE-2026-08-29.json
POOL-ELEGIVEL-2026-08-28.json
BATCH-CYCLE-2026-08-28.json
BATCH-CYCLE-2026-08-29.json
measurement/CHANNEL-ATTRIBUTION-2026-08-29.json
PREDICTION-2026-08-29.md
DEVIATIONS-FOR-PAPER.md
SUPERFICIE-2026-08-27.md
REPLAY-OPORTUNIDADE-2026-08-27.md
REMEDIATION-2026-08-27.md
PROTOCOL-CALIBRATION-2026-08-27.md
CORPUS-FREEZE.md
RELATED-WORK.md
REVISAO-ADVERSARIAL-2026-09-21.md
_sprint-2026-10-04/A-recon-5.7.2-appD.md
_sprint-2026-10-04/A-filters-disaggregation.md
_sprint-2026-10-04/A-recon-52-and-slots.md
_sprint-2026-10-04/A-recon-pool-elegivel.md
_sprint-2026-10-04/REVIEW-A-2026-10-04.md
_sprint-2026-10-04/REVIEW-A-rc3-2026-10-04.md
_sprint-2026-10-04/APPLY-A-rc4.md
_sprint-2026-10-04/APPLY-A-rc5.md
_sprint-2026-10-04/APPLY-A-rc6.md
_sprint-2026-10-04/APPLY-A-rc7.md
_sprint-2026-10-04/CHECK-A-rc4-B-rc4.md
_sprint-2026-10-04/REVIEW-A-rc9-2026-10-05.md
_sprint-2026-10-04/APPLY-A-rc9.md
_sprint-2026-10-04/REVIEW-A-rc10-2026-10-05.md
_sprint-2026-10-04/APPLY-A-rc10.md
_sprint-2026-10-04/APPLY-A-rc11.md
_sprint-2026-10-04/REVIEW-A-rc11-2026-10-05.md
_sprint-2026-10-04/APPLY-A-rc12.md
_sprint-2026-10-04/REVIEW-A-rc12-2026-10-05.md
_sprint-2026-10-04/APPLY-A-rc13.md
_sprint-2026-10-04/REVIEW-A-rc13-2026-10-05.md
_sprint-2026-10-04/APPLY-A-rc14.md
_sprint-2026-10-04/REVIEW-A-rc14-2026-10-05.md
_sprint-2026-10-04/APPLY-A-rc15.md
_sprint-2026-10-04/REVIEW-A-rc15-2026-10-05.md
_sprint-2026-10-04/APPLY-A-rc16.md
_sprint-2026-10-04/REVIEW-A-rc16-2026-10-05.md
_sprint-2026-10-04/APPLY-A-rc17.md
_sprint-2026-10-04/REVIEW-A-rc17-2026-10-05.md
_sprint-2026-10-04/APPLY-A-rc18.md
""".split()

SCRIPTS = """
measurement/sprint-bonus-vs-passo.py
measurement/sprint-censo-artefatos-paperA.py
measurement/sprint-comparabilidade-identidade-572.py
measurement/sprint-contrafactual-salience-producao.mjs
measurement/sprint-desagrega-filtros-pool-principal.py
measurement/sprint-empates-salience-producao.mjs
measurement/sprint-pool-elegivel-multidia.py
measurement/sprint-recon-52-e-sondas.py
_sprint-2026-10-04/A-rc2/coverage-set-from-log.py
_sprint-2026-10-04/A-rc8/parity-rc8.py
_sprint-2026-10-04/A-rc9/parity-rc9.py
_sprint-2026-10-04/A-rc10/parity-rc10.py
_sprint-2026-10-04/A-rc11/parity-rc11.py
_sprint-2026-10-04/A-rc12/parity-rc12.py
_sprint-2026-10-04/A-rc13/parity-rc13.py
_sprint-2026-10-04/A-rc14/parity-rc14.py
_sprint-2026-10-04/A-rc15/parity-rc15.py
_sprint-2026-10-04/A-rc16/parity-rc16.py
_sprint-2026-10-04/A-rc17/parity-rc17.py
_sprint-2026-10-04/A-rc18/parity-rc18.py
_sprint-2026-10-04/A-filters-disaggregation/diag-residual-mismatch.py
serving-brief.ts
measurement/auditoria-da-cadeia.py
measurement/censo-de-universos-no-paragrafo.py
measurement/potencia-h1c.py
measurement/gatilho-composicao.mjs
measurement/gatilho-saturacao.sh
measurement/implantacao/PROCEDENCIA.md
measurement/implantacao/README.md
measurement/implantacao/desliga-dose-p2.sh
measurement/implantacao/restart-realinha-corpus.sh
measurement/implantacao/run-composicao.sh
measurement/implantacao/run-coorte.sh
measurement/implantacao/run-corpus-alinhado.sh
measurement/implantacao/run-designados.sh
measurement/implantacao/run-heartbeat.sh
measurement/implantacao/run-saturacao.sh
deposit/paperA-v1.1/build/build-pdf.sh
deposit/paperA-v1.1/build/preamble-paperA-v1.1.tex
""".split()

SOLTOS = ["deposit/paperA-v1.1/spare-capacity-narrow-surface-v1.1.md", "deposit/paperA-v1.1/spare-capacity-narrow-surface-v1.1.pdf"]
FONTE = "_sprint-2026-10-04/A-v1.1-rc18.md"

# Censo dos caminhos citados (rc11, mantido do rc12 ao rc18): todo caminho que o manuscrito cita e que resolve, no
# repositório, para `_sprint-2026-10-04/…` ou `out/…` (ou que é escrito assim) tem de estar no
# pacote v1.1 ou nos arquivos publicados da v1.0 (MANIFEST.json + zips do registro 22181415,
# baixados em A-recon-evidence/deposited-22181415/). Citação por nome nu (`out-ord0826.json`)
# basta que UMA das resoluções esteja coberta. Fora desse escopo, registra mas não barra.
V10_EVID = ROOT / "_sprint-2026-10-04/A-recon-evidence/deposited-22181415"
EXT_CIT = r"(?:json|md|py|mjs|js|ts|sh|txt|csv|svg|tex|html|zip|pdf|db|ndjson)"
ESCOPO = ("_sprint-2026-10-04/", "out/")


def _expande(tok):
    m = re.search(r"\{([^{}]*)\}", tok)
    if not m:
        return [tok]
    r = re.fullmatch(r"(\d+)\.\.(\d+)", m.group(1))
    opts = [str(i) for i in range(int(r.group(1)), int(r.group(2)) + 1)] if r else m.group(1).split(",")
    return [x for o in opts for x in _expande(tok[:m.start()] + o + tok[m.end():])]


def _citados(text):
    achados = {}
    for ln, line in enumerate(text.split("\n"), 1):
        spans = [(m.start(), m.end()) for m in re.finditer(r"`[^`\n]+`", line)]
        cands = [w for a, b in spans for w in re.split(r"[\s·]+", line[a + 1:b - 1])]
        resto = "".join(" " if any(a <= i < b for a, b in spans) else ch for i, ch in enumerate(line))
        cands += re.findall(r"[\w./{},*-]+\." + EXT_CIT + r"\b", resto)
        for w in cands:
            w = re.sub(r":\d[\d,-]*$", "", w.strip(".,;:()[]'\""))
            if w.startswith(("http", "10.5281")) or not re.search(r"\." + EXT_CIT + r"$", w):
                continue
            achados.setdefault(w, set()).add(ln)
    return achados


def _resolve(tok):
    hits = set()
    for base in ("", "_sprint-2026-10-04/", "measurement/", "out/"):
        for x in _expande(tok):
            hits |= {str(pathlib.Path(p).relative_to(ROOT)) for p in ROOT.glob(base + x) if p.is_file()}
    if not hits and "/" not in tok:
        for x in _expande(tok):
            hits |= {str(p.relative_to(ROOT)) for p in ROOT.rglob(x)
                     if p.is_file() and not ({".git", "node_modules", "__pycache__"} & set(p.parts))}
    return sorted(hits)


def censo_citados(text):
    v10 = {i["path"] for i in json.loads((V10_EVID / "MANIFEST.json").read_text())["itens"]}
    for z in ("artefatos.zip", "scripts.zip"):
        v10 |= set(zipfile.ZipFile(V10_EVID / z).namelist())
    pacote = set(ARTEFATOS) | set(SCRIPTS) | {s.rsplit("/", 1)[1] for s in SOLTOS}
    linhas, lacunas, fora = [], [], []
    for tok, lns in sorted(_citados(text).items()):
        hits = _resolve(tok)
        no_escopo = tok.startswith(ESCOPO) or any(h.startswith(ESCOPO) for h in hits)
        cob = {h: ("v1.1" if h in pacote else "v1.0" if h in v10 else None) for h in hits}
        if "/" in tok:
            ok = bool(hits) and all(cob.values())
        else:
            ok = any(cob.values())
        if no_escopo:
            linhas.append({"citado": tok, "onde": sorted({c for c in cob.values() if c})})
            if not ok:
                lacunas.append((tok, sorted(lns)[:5], [h for h, c in cob.items() if not c] or "não resolve"))
        elif hits and not ok:
            fora.append({"citado": tok, "fora_do_pacote": [h for h, c in cob.items() if not c]})
    return {"escopo": "caminhos _sprint-2026-10-04/… e out/… citados pelo manuscrito",
            "citados_no_escopo": len(linhas),
            "cobertos_v1_1": sum(1 for x in linhas if "v1.1" in x["onde"]),
            "cobertos_so_v1_0": sum(1 for x in linhas if x["onde"] == ["v1.0"]),
            "lacunas": len(lacunas),
            "fora_do_escopo_nao_empacotados": fora}, lacunas

EXCLUIDOS = [
    ("claims_check.py (versão atual)",
     "trabalho em andamento não commitado; seus guardas leem MANUSCRIPT.md (texto em português) e, "
     "com o texto v1.1 no lugar, falham 54 — não verifica a v1.1. A versão da v1.0 segue no registro "
     "(importada), e verifica o texto da v1.0"),
    ("bancos .db citados (epochs e20260826T060003Z / e20260830T060001Z, p2-ord-ro-2026-08-26, "
     "corpus-SERVING-REAL-e20260903-recuperado) (nomes de trabalho em diag-out.txt: ord-0826.db, "
     "preservado-0908.db)", "corpus de produção com conteúdo de trabalho real"),
    ("log de serving p2-serving.ndjson", "dado bruto de produção; os artefatos derivados entram"),
    ("_sprint-2026-10-04/A-filters-disaggregation/{out-pres0908,out-ord0826-tzm3-0828}.json, "
     "_sprint-2026-10-04/A-filters-disaggregation/copies-sha256.txt",
     "não citados pelo manuscrito (os dois JSON são citados só pela nota de sprint "
     "A-filters-disaggregation.md, que entra); diag-out.txt e diag-residual-mismatch.py, citados "
     "desde o rc10, entram desde o rc11"),
    ("out/C12-*-2026-10-05.json, sprint-c12-*", "pertencem ao Paper B"),
    # Declaração pedida pela revisão do rc11 (achado 3), aplicada no rc12.
    (".remember/adversary-receipt-codex-2026-10-05T100118-80790.txt (recibo da voz, citado pelo "
     "addendum rc8)",
     "recibo local fora do repositório; o addendum registra exit 0 e as duas frases adotadas"),
]

# Redação: ordem importa (a regra mais específica primeiro).
REDACAO = [
    ("R1", re.compile(r"/private/tmp/claude-\d+/-Users-[^/]+/[0-9a-f-]{36}/scratchpad/"), "<SCRATCH>/"),
    ("R2", re.compile(r"/Users/[^/\s\"'`]+/"), "<HOME>/"),
    ("R3", re.compile(r"~/"), "<HOME>/"),
    ("R4", re.compile(r"/private/tmp\b"), "<TMP>"),
]

# Arquivos que JÁ foram redigidos no repositório (scrub de 2026-10-05, ver SCRUBBED.txt): a cópia
# do repositório passou a ser a cópia empacotada, então rodar REDACAO sobre ela não acha nada e o
# manifesto perderia 'redacao' e 'sha256_no_repositorio'. O registro vem daqui: sha256 do original
# (o que está no git antes do scrub) e as regras aplicadas na época. Conferido em 2026-10-05 contra
# `git show HEAD:<path>` (os 7 batem) e contra o MANIFEST-v1.1.json depositado (md5 02b0325f…).
JA_REDIGIDOS = {
    "CEILING-GRANULARITY-2026-08-28.json":
        ("88358c34739e21b054e438a8e21efa4cfff884cdea01bf33759dfcaa4fe52376", ["R1 x4"], None),
    "_sprint-2026-10-04/A-filters-disaggregation.md":
        ("af61ca047560108496d0b5a75af086d1bfeae11c1654120e38c62d332319319a", ["R3 x4", "R4 x1"], None),
    "_sprint-2026-10-04/A-filters-disaggregation/observed-main-from-log.json":
        ("bebd8c972f1057c7b4a43ec8f33a424d2b806b79fb51dcd6298d7751de17097e", ["R2 x1"], None),
    "_sprint-2026-10-04/A-rc2/COVERAGE-SET-FROM-LOG-2026-10-04.json":
        ("ec729673a59b3e0ac90e8b83d9eac1ccd2a6f735d940e69ceb9159add212a7e5", ["R2 x1"], None),
    "_sprint-2026-10-04/A-recon-5.7.2-appD.md":
        ("c84158c6194938f47e1fc3af2794957bd58b317530365f4c184a648433314822", ["R3 x4"], None),
    "_sprint-2026-10-04/REVIEW-A-2026-10-04.md":
        ("6eca3e1ab74677a3fcf88a04c22721ee330b1fb8bed22dd0262ba472c261d223", ["R3 x1"], None),
    "measurement/sprint-censo-artefatos-paperA.py":
        ("602f25298f70703c34c3e9b1d76faccb68cfc38112fddc61b458d9138cf01e98", ["R3 x5"],
         "depois da redação, as 4 ocorrências no código (uma no docstring ficou <HOME>/) viraram "
         "os.path.join(os.path.expanduser('~'), ...), para o script rodar; saída idêntica à do original"),
    # Revisão do rc14 (FB3, Fable), aplicada no rc15: a cópia do repositório foi redigida ANTES do
    # primeiro commit (6fd76cb/36082af já têm a versão redigida), então o original não está no git.
    # O hash vem da cópia local guardada fora do repositório no scrub; conferido em 2026-10-05:
    # redige(original) == cópia do repositório, regras R2 x2.
    "_sprint-2026-10-04/REVIEW-A-rc12-2026-10-05.md":
        ("9d1abb0f536abc757aaf7ebe289b22856cc16b5ac712b9530b906e107ee6e6ce", ["R2 x2"], None,
         "2026-10-05, antes do primeiro commit; o original não está no histórico do git (hash "
         "registrado de uma cópia local mantida fora do repositório)"),
}

PRIVADO = re.compile(
    r"Users[-/]|/private/|claude-\d{3}|/home/\w+|~/|srv\d{5,}|MacBook|\.local\b|hostinger|"
    r"tailscale|\.ts\.net|hstgr|nuvini|lab@|"
    r"(?<![\d.])(?!127\.0\.0\.1)(?:\d{1,3}\.){3}\d{1,3}(?![\d.])")
# Número em formato pt-BR com 3 grupos de milhar (1.254.526.976) não é IP: octeto > 255.
def _falso_ip(m):
    s = m.group(0)
    return re.fullmatch(r"(?:\d{1,3}\.){3}\d{1,3}", s) and any(int(x) > 255 for x in s.split("."))

DATA_FIXA = (2026, 10, 5, 0, 0, 0)


def sha(b):
    return hashlib.sha256(b).hexdigest()


def redige(b, rel):
    if rel.endswith((".pdf",)):
        return b, []
    t = b.decode("utf-8")
    regras = []
    for nome, pat, rep in REDACAO:
        t2, n = pat.subn(rep, t)
        if n:
            regras.append(f"{nome} x{n}")
            t = t2
    return t.encode("utf-8"), regras


def privado(t):
    return [m.group(0) for m in PRIVADO.finditer(t) if not _falso_ip(m)]


def monta_zip(nome, lista, itens, achados):
    zpath = HERE / nome
    with zipfile.ZipFile(zpath, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as z:
        for rel in sorted(lista):
            orig = (ROOT / rel).read_bytes()
            emp, regras = redige(orig, rel)
            arc = rel
            if rel.startswith("deposit/paperA-v1.1/build/"):
                arc = "pdf-build/" + rel.rsplit("/", 1)[1]
            zi = zipfile.ZipInfo(arc, DATA_FIXA)
            zi.compress_type = zipfile.ZIP_DEFLATED
            zi.external_attr = (0o755 if rel.endswith(".sh") else 0o644) << 16
            z.writestr(zi, emp)
            it = {"path": arc, "no_deposito": nome, "bytes": len(emp), "sha256": sha(emp)}
            if regras:
                if rel in JA_REDIGIDOS and sha(orig) != JA_REDIGIDOS[rel][0]:
                    raise SystemExit(f"{rel}: já redigido no repositório, mas a cópia atual ainda "
                                     f"pede {regras}; o repositório deixaria de ser igual ao depósito")
                it["sha256_no_repositorio"] = sha(orig)
                it["redacao"] = regras
            elif rel in JA_REDIGIDOS:
                old, regras_antigas, depois, *nota = JA_REDIGIDOS[rel]
                it["sha256_no_repositorio"] = old
                it["redacao"] = regras_antigas
                it["redacao_no_repositorio"] = (nota[0] if nota else
                                                "2026-10-05 (SCRUBBED.txt); original no histórico do git")
                if depois:
                    it["alteracao_pos_redacao"] = depois
            itens.append(it)
            achados += [(arc, x) for x in privado(emp.decode("utf-8", "replace"))]
    return zpath


def main():
    itens, achados = [], []
    for rel in SOLTOS:
        b = (ROOT / rel).read_bytes()
        itens.append({"path": rel.rsplit("/", 1)[1], "no_deposito": "solto", "bytes": len(b), "sha256": sha(b)})
        if rel.endswith(".md"):
            achados += [(rel, x) for x in privado(b.decode("utf-8"))]
    # texto do PDF: o que um leitor extrai dele
    txt = subprocess.run(["pdftotext", "-enc", "UTF-8", str(ROOT / SOLTOS[1]), "-"],
                         capture_output=True, check=True).stdout.decode("utf-8")
    achados += [("spare-capacity-narrow-surface-v1.1.pdf (texto)", x) for x in privado(txt)]
    raw = (ROOT / SOLTOS[1]).read_bytes().decode("latin-1")
    achados += [("spare-capacity-narrow-surface-v1.1.pdf (bytes)", x) for x in re.findall(r"/Users/|Users-lab|claude-\d{3}", raw)]
    za = monta_zip("artefatos-v1.1.zip", ARTEFATOS, itens, achados)
    zs = monta_zip("scripts-v1.1.zip", SCRIPTS, itens, achados)

    fonte = (ROOT / FONTE).read_bytes()
    dep = (ROOT / SOLTOS[0]).read_bytes()
    if fonte != dep:
        print(f"ERRO: {SOLTOS[0]} difere de {FONTE}; o depósito deve ser a cópia byte a byte")
        return 1
    censo, lacunas = censo_citados(dep.decode("utf-8"))
    if lacunas:
        for tok, linhas, falta in lacunas:
            print(f"  LACUNA  `{tok}` (linhas {linhas}): {falta}")
        print(f"CENSO: {len(lacunas)} caminho(s) citado(s) fora do pacote e da v1.0 — NÃO depositar")
        return 1
    man = {
        "gerado_por": "deposit/paperA-v1.1/build-package.py",
        "registro": {
            "rascunho": 23163119,
            "doi": "10.5281/zenodo.23163119",
            "concept_doi": "10.5281/zenodo.22181414",
            "versao_anterior": "10.5281/zenodo.22181415 (v1.0, publicada 2026-08-30)",
        },
        "nota": ("Os 13 arquivos da v1.0 entram nesta versão por files-import no servidor, byte a byte "
                 "do publicado; não estão listados em 'itens' e seus md5 são conferidos contra o "
                 "registro 22181415 no readback. 'itens' cobre só o que a v1.1 acrescenta. Zips "
                 "determinísticos (ordem alfabética, data 2026-10-05 00:00). Onde a cópia empacotada "
                 "difere do repositório, 'redacao' diz quais regras e 'sha256_no_repositorio' guarda "
                 "o hash do original. Nos itens com 'redacao_no_repositorio', a cópia do repositório "
                 "já foi sobrescrita com a redigida (2026-10-05): 'sha256_no_repositorio' é então o "
                 "hash do original anterior ao scrub, que segue no histórico do git, salvo onde "
                 "'redacao_no_repositorio' diz que o original não chegou a ser commitado."),
        "regras_de_redacao": {
            "R1": "caminho absoluto do scratchpad temporário local -> <SCRATCH>/",
            "R2": "diretório home absoluto do autor -> <HOME>/",
            "R3": "prefixo de home '~' + barra -> <HOME>/",
            "R4": "diretório temporário do macOS -> <TMP>",
        },
        "manuscrito": {
            "fonte": FONTE,
            "sha256_fonte": sha(fonte),
            "sha256_depositado": sha(dep),
            "diferenca": "nenhuma: o depositado é a fonte byte a byte (gate de parity-rc18, check 'deposit')",
            "pdf": "pandoc 3.9 + xelatex x2 via pdf-build/build-pdf.sh (em scripts-v1.1.zip); 0 glifos ausentes",
        },
        "excluidos": [{"o_que": a, "motivo": b} for a, b in EXCLUIDOS],
        "censo_citados": censo,
        "envio": {
            "soltos": sum(1 for i in itens if i["no_deposito"] == "solto"),
            "artefatos-v1.1.zip": {"itens": len(ARTEFATOS), "bytes": za.stat().st_size},
            "scripts-v1.1.zip": {"itens": len(SCRIPTS), "bytes": zs.stat().st_size},
        },
        "itens": itens,
    }
    (HERE / "MANIFEST-v1.1.json").write_text(json.dumps(man, ensure_ascii=False, indent=1) + "\n",
                                              encoding="utf-8")
    achados += [("MANIFEST-v1.1.json", x) for x in privado((HERE / "MANIFEST-v1.1.json").read_text())]
    red = [i for i in itens if "redacao" in i]
    faltam = set(JA_REDIGIDOS) - {i["path"] for i in red}
    if faltam:
        print(f"ERRO: registro de redação perdido para {sorted(faltam)}")
        return 1
    print(f"itens novos: {len(itens)} ({len(ARTEFATOS)} artefatos, {len(SCRIPTS)} scripts, {len(SOLTOS)} soltos)")
    print(f"redigidos: {len(red)}: " + "; ".join(f"{i['path']} [{', '.join(i['redacao'])}]" for i in red))
    if achados:
        for a, x in achados:
            print(f"  PRIVADO  {a}: {x!r}")
        print(f"GATE: {len(achados)} ocorrência(s) privada(s) — NÃO depositar")
        return 1
    print("GATE: 0 ocorrências de host, IP não-loopback ou caminho pessoal em todo byte empacotado")
    return 0


if __name__ == "__main__":
    sys.exit(main())
