#!/usr/bin/env python3
"""Teste de mutação para `claims_check.py` — cada guarda tem de MORDER.

POR QUE ISTO EXISTE
-------------------
Em 2026-09-03 eu rodei um censo de alegações de SOTA, ele classificou 26 linhas
como "SOTA de terceiros, legítimo", e eu **reportei isso sem ler nenhuma das
26**. Doze eram alegações próprias. O classificador usava "a frase menciona um
baseline" como prova de ser de terceiro — e toda alegação própria menciona o
baseline que alega bater. O filtro estava ANTICORRELACIONADO com o que devia
detectar, e nada revelou isso porque eu nunca o mutei.

Mutei ao final, depois de o escopo já ter sido reportado errado duas vezes. A
mutação achou o defeito em segundos.

⇒ **Um censo não é reportável antes de o próprio teste de mutação passar.**

E o teste tem de exigir a MENSAGEM, não só o `exit != 0`: um guarda que falha
pelo motivo errado passaria num teste que só olha o código de saída. Cada caso
aqui declara um marcador que a mensagem precisa conter.

Nada é escrito nos arquivos reais: cada mutação roda numa cópia em tempdir.

USO
---
    python3 claims_check_mutation_test.py
"""
from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

AQUI = Path(__file__).parent
PAPER = "paper-tecnico-nox-mem.md"
BIB = "refs.bib"
SCRIPT = "claims_check.py"

# (nome, arquivo, de, para, marcador esperado na mensagem)
# `de=None` => append ao fim do arquivo.
CASOS = [
    (
        "fence impar quebra toda varredura",
        PAPER, None, "\n```\n",
        "code fence",
    ),
    (
        "alegacao superlativa propria sem limitador",
        PAPER, None, "\nnox-mem achieves SOTA on both benchmarks.\n",
        "superlativa própria sem limitador",
    ),
    (
        "superlativo POR EXTENSO (a cegueira do censo original)",
        PAPER, None, "\nOur system is state-of-the-art on this task.\n",
        "superlativa própria sem limitador",
    ),
    (
        "entrada obsoleta na lista de permitidos = falso verde",
        PAPER, "reader SOTA numbers are published", "reader numbers exist",
        "SUPERLATIVO_PERMITIDO",
    ),
    (
        "sitio NOVO herdando a isencao por substring",
        # Alegação falsa que CONTÉM o trecho isento. Sem contagem esperada por
        # âncora, a isenção por substring a absolvia em silêncio — buraco real,
        # achado em 2026-09-04 ao generalizar a análise de um patch alheio.
        PAPER, None,
        "\nnox-mem is SOTA, and reader SOTA numbers are published elsewhere.\n",
        "herdando a isenção por substring",
    ),
    (
        "tabela de QA classico sem declarar split",
        PAPER, None, "\n| Beam Retrieval | 69.20% | +10.58 pp |\n",
        "não declara split",
    ),
    (
        "ID arXiv citado sem entrada bib",
        PAPER, None, "\nAs shown in (arxiv:9911.12345), this holds.\n",
        "não tem entrada",
    ),
    (
        "divida bib ja paga e nao removida da lista",
        BIB, None, "\n@misc{x, note = {arXiv:2104.08663.}}\n",
        "BIB_DIVIDA",
    ),
    (
        "evidencia nao-arquivavel AUMENTOU (ratchet)",
        PAPER, None, "\nEvidence in PR #999.\n",
        "AUMENTOU",
    ),
    (
        "PR # como fonte em tabela de comparacao externa",
        PAPER, None, "\n| MemOS | 42.55% | dev | fonte (PR #998) |\n",
        "usa `PR #NNN` como fonte",
    ),
    (
        "numero de serie viva sem data",
        PAPER, None, "\nThe store holds 94.9k chunks today.\n",
        "série viva sem data",
    ),
    (
        "alegacao retratada reaparece sem enquadramento",
        PAPER, None, "\nWe report 58.62% and 73.37% on these tasks.\n",
        "dual_sota_classico",
    ),
    (
        "cross-backbone reaparece sem declarar o backbone",
        PAPER, None, "\nWe reach 63.28% and 88.42% overall.\n",
        "memos_cross_backbone",
    ),
    (
        "cross-metric reaparece sem declarar metrica",
        PAPER, None, "\nWe get 74.52% versus 66.88% there.\n",
        "locomo_cross_metric",
    ),
    (
        "aritmetica em pp misturando F1 e strict EM",
        PAPER, None, "\nThat leaves a 55 pp gap between F1 and strict EM.\n",
        "mistura F1 e EM",
    ),
]

# Controle NEGATIVO: texto inócuo não pode disparar nada.
CONTROLE = (PAPER, "\nThe pipeline indexes files as they change.\n")


def _prepara(tmp: Path) -> None:
    for f in (PAPER, BIB, SCRIPT):
        shutil.copy2(AQUI / f, tmp / f)


def _roda(tmp: Path) -> tuple[int, str]:
    p = subprocess.run(
        [sys.executable, str(tmp / SCRIPT), "--root", str(tmp)],
        capture_output=True, text=True,
    )
    return p.returncode, p.stdout + p.stderr


def _classifica(rc: int, saida: str, marcador: str) -> str:
    """Veredicto de um caso de mutação: extraído para poder ser TESTADO.

    Existe por um furo que eu mesmo declarei e não havia fechado: os casos
    mutam o arquivo do paper, que é o input do PROCESSO FILHO, enquanto esta
    classificação roda no PAI. Envenenar o filho nunca exercita o pai — então
    se a checagem de marcador quebrasse, um guarda falhando pelo motivo errado
    passaria por 'mordeu' e a bateria diria 15/15.

    A forma que fecha isso é infrator sintético contra ESTA função, no próprio
    processo (ver `_meta_controle`). Diagnóstico e forma vindos da sessão do
    7_problems, onde a mesma classe apareceu como `${2@Q}` abortando o corpo da
    função antes do contador de falhas.
    """
    if rc == 0:
        return "nao_mordeu"
    if marcador not in saida:
        return "marcador_errado"
    return "ok"


def _meta_controle() -> list[str]:
    """Prova que `_classifica` distingue as três respostas, antes de qualquer caso.

    Sem isto, "15/15" é compatível com a classificação estar quebrada.
    """
    casos = [
        ((0, "ok — tudo verde", "qualquer"), "nao_mordeu",
         "exit 0 tem de ser 'não mordeu', mesmo com marcador ausente"),
        ((1, "FAIL — divergência: superlativa própria", "superlativa própria"),
         "ok", "exit 1 com o marcador presente tem de ser 'ok'"),
        ((1, "FAIL — divergência: outra coisa qualquer",
          "MARCADOR-QUE-NAO-PODE-APARECER"), "marcador_errado",
         "exit 1 SEM o marcador tem de ser 'marcador errado' — é esta perna "
         "que prova que a checagem de marcador está viva"),
    ]
    fails = []
    for (rc, saida, marcador), esperado, porque in casos:
        got = _classifica(rc, saida, marcador)
        if got != esperado:
            fails.append(f"_classifica({rc}, ...) deu {got!r}, esperado "
                         f"{esperado!r} — {porque}")
    return fails


def main() -> int:
    meta = _meta_controle()
    if meta:
        print("FAIL — o meta-controle reprovou; nenhum caso foi rodado, "
              "porque um resultado verde não significaria nada:", file=sys.stderr)
        for m in meta:
            print(f"  {m}", file=sys.stderr)
        return 1
    print("meta-controle ................. ✅ _classifica distingue as 3 respostas")

    with tempfile.TemporaryDirectory() as d:
        base = Path(d) / "base"
        base.mkdir()
        _prepara(base)
        rc, saida = _roda(base)
        if rc != 0:
            print("FAIL — baseline já está vermelho; mutação não diz nada:",
                  file=sys.stderr)
            print(saida, file=sys.stderr)
            return 1
        print("baseline ...................... ✅ verde")

    falhas = []
    for nome, arquivo, de, para, marcador in CASOS:
        with tempfile.TemporaryDirectory() as d:
            tmp = Path(d)
            _prepara(tmp)
            alvo = tmp / arquivo
            txt = alvo.read_text()
            if de is None:
                alvo.write_text(txt + para)
            else:
                if de not in txt:
                    falhas.append(f"{nome}: âncora `{de}` não existe — "
                                  f"o teste não testa nada")
                    print(f"{nome[:44]:<46} 🔴 âncora ausente")
                    continue
                alvo.write_text(txt.replace(de, para, 1))

            rc, saida = _roda(tmp)
            v = _classifica(rc, saida, marcador)
            if v == "nao_mordeu":
                falhas.append(f"{nome}: guarda NÃO mordeu")
                print(f"{nome[:44]:<46} 🔴 não mordeu")
            elif v == "marcador_errado":
                falhas.append(
                    f"{nome}: falhou, mas sem o marcador `{marcador}` — "
                    f"pode ter falhado pelo motivo errado")
                print(f"{nome[:44]:<46} 🟡 mordeu, marcador errado")
            else:
                print(f"{nome[:44]:<46} ✅ mordeu, marcador certo")

    with tempfile.TemporaryDirectory() as d:
        tmp = Path(d)
        _prepara(tmp)
        arquivo, texto = CONTROLE
        alvo = tmp / arquivo
        alvo.write_text(alvo.read_text() + texto)
        rc, saida = _roda(tmp)
        if rc != 0:
            falhas.append("controle negativo: texto inócuo disparou guarda")
            print(f"{'controle negativo (texto inocuo)':<46} 🔴 falso positivo")
            print(saida, file=sys.stderr)
        else:
            print(f"{'controle negativo (texto inocuo)':<46} ✅ silencioso")

    print()
    if falhas:
        print(f"FAIL — {len(falhas)} caso(s) de mutação sem valor:",
              file=sys.stderr)
        for f in falhas:
            print(f"  {f}", file=sys.stderr)
        return 1
    print(f"ok — {len(CASOS)} mutações mordidas com o marcador certo, "
          f"controle negativo silencioso")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
