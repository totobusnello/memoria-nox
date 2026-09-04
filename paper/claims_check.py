#!/usr/bin/env python3
"""claims_check.py — guardas mecânicas para o Paper 1 (nox-mem technical paper).

POR QUE ISTO EXISTE
-------------------
Em 2026-09-03 o arXiv recusou `submit/7771319`. Relendo o paper, a alegação
"**dual SOTA** em MuSiQue e HotPotQA" não se sustentava: 58,62 e 73,37 estão
**abaixo** do estado da arte publicado (Beam Retrieval, 69,2 e 85,04) — algo que
qualquer revisor de cs.IR falsifica em trinta segundos, e estava no abstract.

O honesty pass de 2026-07-01 — três revisores adversariais independentes — já
havia matado essa MESMA classe três vezes noutros lugares do paper. A quarta
ficou. Uma quinta havia RESSUSCITADO no bloco de highlights. Ou seja: revisão
humana e revisão por modelo leem se a frase é COERENTE, não se ainda é
VERDADEIRA, e a alegação era coerente e bem escrita.

E o conserto teve o próprio defeito: a v1 do patch de retratação colocou números
de **test** sob cabeçalhos de **dev**, reintroduzindo comparação cross-split
enquanto retratava uma cross-metric. Achado por revisão adversarial, não por mim.

⇒ O Paper A tem `claims_check.py` com 22 guardas. O Paper 1 tinha ZERO. Toda
prosa dele era inverificada por construção. Este arquivo fecha isso.

DECISÃO DE PROJETO: NADA É ANCORADO EM NÚMERO DE LINHA
------------------------------------------------------
A causa nº 1 dos erros desta sessão foi número derivado carregado através de uma
mutação — inclusive números de linha reusados depois de eu mesmo editar o
arquivo. Todo guarda aqui casa por CONTEÚDO. Linhas aparecem só em mensagem de
erro, recomputadas a cada execução.

Corolário: uma lista fechada de trechos permitidos também apodrece (entrada
obsoleta vira falso verde). Onde há lista, o guarda mede nas DUAS direções:
ocorrência sem entrada, e entrada sem ocorrência.

USO
---
    python3 claims_check.py [--root .]

Saída binária, no padrão do Paper A: 0 = limpo, 1 = divergência(s) em stderr.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

PAPER = "paper-tecnico-nox-mem.md"
BIB = "refs.bib"

# --- termos superlativos, sigla E por extenso -------------------------------
# ⚠️ O censo original desta sessão procurou APENAS a sigla `SOTA` e por isso
# deixou passar alegação escrita por extenso. Os dois entram.
SUPERLATIVO = re.compile(
    r"\bSOTA\b|state[-\s]of[-\s]the[-\s]art|best[-\s]in[-\s]class|unmatched|"
    r"outperforms all|world[-\s]class|unrival",
    re.I,
)

# Sujeito próprio: a alegação é sobre NÓS?
PROPRIO = re.compile(r"\bnox-mem\b|\bour\b|\bwe\b", re.I)

# Marcadores que tornam uma frase superlativa aceitável: ela LIMITA a alegação.
LIMITADOR = re.compile(
    r"\bbelow\b|\bshort of\b|not a state[-\s]of[-\s]the[-\s]art|not SOTA|"
    r"are not SOTA|rather than state[-\s]of[-\s]the[-\s]art|\bcompetent\b|"
    r"\bheadroom\b|backbones differ|pp vs SOTA|described as SOTA|"
    r"different metric|not comparable|\bbounding\b|\bbounds\b|below current",
    re.I,
)

# Séries vivas: números que envelhecem sozinhos. O grafo de KG deste projeto já
# drenou de ~21,5k para 554 por bug de decay — o número no paper não mudou.
SERIE_VIVA = re.compile(r"94\.9k|15\.6k|21\.5k|99\.99%|67[.,]187|69[.,]261")
DATADO = re.compile(r"as of|20\d\d-\d\d-\d\d")

# IDs arXiv citados inline que ainda não têm entrada bibliográfica.
# ⚠️ Isto é DÍVIDA DECLARADA, não isenção permanente: resolver antes de
# submissão a journal. O guarda falha para qualquer ID novo fora desta lista.
BIB_DIVIDA = {
    "2104.08663": "BEIR — citado inline no honesty pass de 2026-07-01",
    "2210.07316": "MTEB — idem",
    "2210.03629": "ReAct — citado em §5.5 (IterB)",
    "2402.17753": "citado inline; verificar título/venue antes de criar entrada",
    "2602.01313": "citado inline; verificar título/venue antes de criar entrada",
}

# Ratchet de evidência não-arquivável. `PR #NNN` não é resolvível por leitor
# externo. Há dívida herdada; o guarda impede que ela CRESÇA e proíbe o padrão
# nas tabelas de comparação externa, que são as que sustentam manchete.
#
# ⚠️ 67 é MEDIDO, não estimado. A primeira versão deste arquivo trouxe 24, que
# era o número de sítios que EU havia inspecionado — não o total. Baseline
# chutado é ratchet frouxo: aceitaria 43 inserções novas em silêncio.
PR_BASELINE = 67

# Tabelas de comparação externa que ainda usam `PR #NNN` como fonte. Dívida
# HERDADA e declarada, não isenção: qualquer sítio novo falha. Resolver com
# artefato citável antes de submissão a journal.
PR_EM_TABELA_DIVIDA = {
    "Above Zep 50.40% / LangMem 50.21%":
        "§5.3.2 LoCoMo F1 push — trocar (PR #404) por artefato de audit",
}

SISTEMAS_EXTERNOS = re.compile(
    r"Beam Retrieval|FE2H|EX\(SA\)|IRCoT|DPR|FiD|MemOS|Mem0|Zep|LangMem", re.I
)

# Só os sistemas de QA multi-hop clássico entram no guarda de split. É neles que
# a confusão dev/test é viva (leaderboard oficial reporta test; nossas rodadas
# são dev). Para EverMemBench e LoCoMo o eixo das tabelas é backbone ou sistema,
# não split, e exigir `dev|test` ali seria ruído.
SISTEMAS_QA_CLASSICO = re.compile(r"Beam Retrieval|FE2H|EX\(SA\)|IRCoT|DPR|FiD", re.I)

# Frases superlativas próprias permitidas, ancoradas por TRECHO (nunca por
# linha). Verificado nas DUAS direções: ocorrência sem entrada = alegação nova
# não auditada; entrada sem ocorrência = obsoleta, e lista obsoleta é falso
# verde. Manter curtíssima: se crescer, a regra está errada.
#
# 🔑 O valor é (razão, CONTAGEM ESPERADA), não só a razão. Isenção por substring
# sem contagem tem um buraco: uma alegação NOVA e falsa que contenha o trecho
# isento passa de graça. Declarar quantas ocorrências se espera fecha isso — uma
# segunda aparição da mesma frase é sítio novo e precisa de revisão.
#
# ⚠️ Contagem ESPERADA, e não unicidade universal. Um `assert count == 1`
# uniforme reprova âncora que casa legitimamente em dois sítios — foi o que
# aconteceu num patch analisado em 2026-09-04, cuja 12ª âncora casava duas vezes
# nos dois lugares certos. O guarda que exige unicidade em tudo bloqueia
# aplicação correta; o que declara a contagem por âncora não.
SUPERLATIVO_PERMITIDO = {
    "reader SOTA numbers are published": (
        "§5.2 metodologia — descreve que existe SOTA publicado de terceiros, "
        "não alega o nosso", 1),
    "Published SOTA (split noted)": (
        "§5.4 cabeçalho de tabela — nomeia a coluna, não afirma nada", 1),
}


def _linhas_de_prosa(texto: str) -> list[tuple[int, str]]:
    """Linhas FORA de code fence, com número de linha 1-based.

    ⚠️ Existe por defeito próprio: nesta sessão um parser meu contou `# Line
    3063` — comentário Python dentro de fence — como heading markdown, e eu
    reportei uma seção de 3.011 palavras que não existia.
    """
    fora, dentro = [], False
    for i, l in enumerate(texto.split("\n")):
        if re.match(r"^\s*```", l):
            dentro = not dentro
            continue
        if not dentro:
            fora.append((i + 1, l))
    return fora


def _frases(linha: str) -> list[str]:
    return [f for f in re.split(r"(?<=[.;])\s+", linha) if f.strip()]


def fence_check(root: Path) -> list[str]:
    """Cercas de código balanceadas.

    Cerca ímpar inverte o estado de todo parser a jusante — e faz um guarda
    varrer o conjunto errado sem reclamar. Precondição dos outros guardas.
    """
    md = (root / PAPER).read_text()
    n = len(re.findall(r"^\s*```", md, re.M))
    if n % 2:
        return [f"{PAPER}: {n} marcadores de code fence (ímpar) — "
                f"toda varredura por fence está lendo o conjunto errado"]
    return []


def superlativo_check(root: Path) -> list[str]:
    """Alegação superlativa PRÓPRIA precisa de limitador na mesma frase.

    Regra de conteúdo, não lista de linhas. Pega os cinco sítios de 2026-09-03
    (`dual SOTA`, `nox-mem is SOTA`, `both SOTA`, `prove ... is SOTA`,
    `12 SOTA-tier dimensions`), e deixa passar descrição de SOTA de terceiro
    ("below Mem0 SOTA"), que é legítima.
    """
    md = (root / PAPER).read_text()
    fails = []
    contagem: dict[str, int] = {k: 0 for k in SUPERLATIVO_PERMITIDO}
    for ln, linha in _linhas_de_prosa(md):
        for f in _frases(linha):
            if not SUPERLATIVO.search(f):
                continue
            if not PROPRIO.search(f):
                continue  # SOTA de terceiro, sem sujeito próprio
            if LIMITADOR.search(f):
                continue  # limitada — é o que a retratação exige
            permitido = next(
                (k for k in SUPERLATIVO_PERMITIDO if k in f), None
            )
            if permitido:
                contagem[permitido] += 1
                continue
            fails.append(
                f"{PAPER}:{ln}: alegação superlativa própria sem limitador na "
                f"frase — `{f.strip()[:88]}`"
            )

    # Direção inversa E contagem: entrada sem ocorrência é falso verde; entrada
    # com ocorrência A MAIS é sítio novo que herdou a isenção por substring.
    for k, (razao, esperado) in SUPERLATIVO_PERMITIDO.items():
        visto = contagem[k]
        if visto == esperado:
            continue
        if visto == 0:
            fails.append(
                f"claims_check.py: SUPERLATIVO_PERMITIDO tem `{k}`, que já não "
                f"aparece em {PAPER} — remover (entrada obsoleta = falso verde)"
            )
        else:
            fails.append(
                f"{PAPER}: `{k}` aparece {visto}x, isenção declarada para "
                f"{esperado}x ({razao}) — uma ocorrência a mais é sítio NOVO "
                f"herdando a isenção por substring, e precisa de revisão"
            )
    return fails


def split_metrica_check(root: Path) -> list[str]:
    """Linha de tabela que cita sistema externo tem de declarar o split.

    A v1 do patch de retratação pôs 69,2 (test) e 85,04 (blind test) sob
    cabeçalho `Dev F1`. O gap dev/test é ~1 pp e o gap real é 10-12 pp, então a
    conclusão não mudava — mas citar split trocado é o defeito que a retratação
    existe para corrigir.
    """
    fails = []
    for ln, linha in _linhas_de_prosa((root / PAPER).read_text()):
        if not linha.strip().startswith("|"):
            continue
        if not SISTEMAS_QA_CLASSICO.search(linha):
            continue
        if re.search(r"\d{2}\.\d{2}%|\d{2}\.\d%", linha) is None:
            continue  # linha sem número comparável
        if re.search(r"\bdev\b|\btest\b|blind test|Per Mem0|published|range",
                     linha, re.I):
            continue
        fails.append(
            f"{PAPER}:{ln}: linha de tabela compara sistema externo com número "
            f"e não declara split — `{linha.strip()[:88]}`"
        )
    return fails


def refs_check(root: Path) -> list[str]:
    """Todo ID arXiv citado inline precisa de entrada bib, ou dívida declarada.

    Nas duas direções: ID novo sem entrada FALHA; entrada de dívida que já foi
    resolvida também falha, para a lista não apodrecer em falso verde.
    """
    md = (root / PAPER).read_text()
    bib = (root / BIB).read_text()
    no_paper = set(re.findall(r"arxiv:\s*(\d{4}\.\d{4,5})", md, re.I))
    no_bib = set(re.findall(r"(\d{4}\.\d{4,5})", bib))

    fails = []
    for i in sorted(no_paper - no_bib - set(BIB_DIVIDA)):
        fails.append(
            f"{BIB}: arXiv:{i} é citado no paper e não tem entrada "
            f"bibliográfica nem consta de BIB_DIVIDA"
        )
    for i in sorted(set(BIB_DIVIDA) & no_bib):
        fails.append(
            f"claims_check.py: BIB_DIVIDA lista arXiv:{i}, que JÁ tem entrada "
            f"em {BIB} — remover da lista (entrada obsoleta = falso verde)"
        )
    return fails


def evidencia_check(root: Path) -> list[str]:
    """`PR #NNN` não é evidência arquivável — ratchet + proibição nas tabelas.

    Nenhum leitor externo resolve um número de pull request, e num repo privado
    ele nem existiria. Não é overclaim: é evidência inverificável, e o sintoma
    que um moderador vê é o mesmo de referência inventada.
    """
    md = (root / PAPER).read_text()
    fails = []

    n = len(re.findall(r"PR #\d+", md))
    if n > PR_BASELINE:
        fails.append(
            f"{PAPER}: {n} ocorrências de `PR #NNN` (baseline {PR_BASELINE}) — "
            f"evidência não-arquivável AUMENTOU; usar artefato ou commit pinado"
        )

    vistos: set[str] = set()
    for ln, linha in _linhas_de_prosa(md):
        if not (linha.strip().startswith("|")
                and re.search(r"PR #\d+", linha)
                and SISTEMAS_EXTERNOS.search(linha)):
            continue
        conhecido = next((k for k in PR_EM_TABELA_DIVIDA if k in linha), None)
        if conhecido:
            vistos.add(conhecido)
            continue
        fails.append(
            f"{PAPER}:{ln}: tabela de comparação externa usa `PR #NNN` como "
            f"fonte — `{linha.strip()[:88]}`"
        )

    for k in sorted(set(PR_EM_TABELA_DIVIDA) - vistos):
        fails.append(
            f"claims_check.py: PR_EM_TABELA_DIVIDA tem `{k}`, que já não "
            f"aparece em {PAPER} — dívida paga, remover da lista"
        )
    return fails


def serie_viva_check(root: Path) -> list[str]:
    """Número de série viva precisa de data na mesma frase.

    O grafo de KG deste sistema drenou de ~21,5k relações para 554 por bug de
    compounding no decay; o número no paper não mudou. Série viva citada como
    instante envelhece para falsidade em silêncio.
    """
    fails = []
    for ln, linha in _linhas_de_prosa((root / PAPER).read_text()):
        for f in _frases(linha):
            if SERIE_VIVA.search(f) and not DATADO.search(f):
                fails.append(
                    f"{PAPER}:{ln}: número de série viva sem data na frase — "
                    f"`{f.strip()[:88]}`"
                )
    return fails


# --- o guarda que nem o Paper A tem ----------------------------------------
# Uma alegação retratada tem DEPENDENTES. A de 2026-09-03 tinha CINCO sítios, e
# eu descobri isso em três rodadas (leitura -> censo -> revisão adversarial).
# Este mapa é a lista de invalidação, executável: se a alegação aparece, o
# enquadramento corrigido tem de aparecer com ela.
DEPENDENTES = [
    {
        "id": "dual_sota_classico",
        "porque": "58,62 e 73,37 estão ~10 e ~12 pp ABAIXO do SOTA publicado "
                  "(Beam Retrieval 69,2 test / 85,04 blind test)",
        "gatilho": [r"58\.62", r"73\.37"],   # os dois na mesma frase
        "exige": r"below|short of|competent|headroom|rather than|"
                 r"Beam Retrieval|bounding|bounds",
    },
    {
        "id": "memos_cross_backbone",
        "porque": "63,28/88,42 são Gemini-3-flash contra MemOS em "
                  "GPT-4.1-mini — comparação cross-backbone, não SOTA",
        "gatilho": [r"63\.28", r"88\.42"],
        "exige": r"GPT-4\.1-mini|backbones differ|not a state|obtained on",
    },
    {
        "id": "locomo_cross_metric",
        "porque": "74,52 é retrieval@10 e 66,88 é answer F1 end-to-end — "
                  "métricas diferentes, não comparáveis",
        "gatilho": [r"74\.52", r"66\.88"],
        "exige": r"different metric|not comparable|answer[-\s]F1|"
                 r"end-to-end|retrieval ceiling",
    },
]


def dependentes_check(root: Path) -> list[str]:
    """Alegação retratada não pode reaparecer sem o enquadramento corrigido."""
    fails = []
    for ln, linha in _linhas_de_prosa((root / PAPER).read_text()):
        for f in _frases(linha):
            for d in DEPENDENTES:
                if not all(re.search(g, f) for g in d["gatilho"]):
                    continue
                if re.search(d["exige"], f, re.I):
                    continue
                fails.append(
                    f"{PAPER}:{ln}: `{d['id']}` — os números aparecem juntos "
                    f"sem o enquadramento retratado ({d['porque']}) — "
                    f"`{f.strip()[:80]}`"
                )
    return fails


def aritmetica_check(root: Path) -> list[str]:
    """Subtração entre métricas diferentes.

    A v1 do patch defendeu a §5.4 com "~55 pp de distância", subtraindo F1
    (partial credit) de strict EM. Usei uma conta cross-metric para defender a
    retratação de um overclaim cross-metric — e o próprio paper lista
    "strict scoring" como mecanismo do gap, contradizendo a conta.
    """
    fails = []
    for ln, linha in _linhas_de_prosa((root / PAPER).read_text()):
        for f in _frases(linha):
            if not re.search(r"\d+(\.\d+)?\s*pp\b", f):
                continue
            tem_f1 = re.search(r"\bF1\b|ans_F1|answer F1", f, re.I)
            tem_em = re.search(r"strict EM|exact[-\s]match|\bEM\b", f, re.I)
            if tem_f1 and tem_em:
                fails.append(
                    f"{PAPER}:{ln}: aritmética em `pp` numa frase que mistura "
                    f"F1 e EM — métricas não subtraíveis — `{f.strip()[:80]}`"
                )
    return fails


GUARDAS = [
    fence_check,
    superlativo_check,
    split_metrica_check,
    refs_check,
    evidencia_check,
    serie_viva_check,
    dependentes_check,
    aritmetica_check,
]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(Path(__file__).parent))
    args = ap.parse_args()
    root = Path(args.root)

    for f in (PAPER, BIB):
        if not (root / f).exists():
            print(f"FAIL — {f} não encontrado em {root}", file=sys.stderr)
            return 1

    failures: list[str] = []
    for g in GUARDAS:
        failures.extend(g(root))

    if failures:
        print(f"FAIL — {len(failures)} divergência(s):", file=sys.stderr)
        for f in failures:
            print(f"  {f}", file=sys.stderr)
        return 1

    print(f"ok — {len(GUARDAS)} guardas passaram; "
          f"{len(DEPENDENTES)} alegações retratadas com lista de invalidação")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
