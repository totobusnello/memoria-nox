#!/usr/bin/env python3
"""Confere que a tradução em inglês não mudou nenhum número.

O risco de traduzir prosa numérica não é o idioma: é a NOTAÇÃO. `2,66%` vira `2.66%`
e `583.763` vira `583,763` — trocando o papel do ponto e da vírgula. Uma troca feita
pela metade produz `583.763` lido como quinhentos e oitenta e três *inteiros*, ou
`2,66%` lido como dois mil e sessenta e seis. Ambos passam despercebidos em revisão
humana e nenhum guarda existente pega, porque os guardas leem só o arquivo PT.

Este script normaliza os dois lados para um número puro e compara os MULTICONJUNTOS.
Comparar conjuntos esconderia uma repetição perdida; comparar contagens não.

Só varre as seções já traduzidas — o EN é parcial por construção, e cobrar dele os
números das seções ausentes daria falso positivo em massa.

Uso:
  paridade-de-traducao.py                 # confere e sai 0/1
  paridade-de-traducao.py --json out.json # grava o artefato
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
from collections import Counter

RAIZ = pathlib.Path(__file__).resolve().parent.parent
PT = RAIZ / "MANUSCRIPT.md"
EN = RAIZ / "MANUSCRIPT-en.md"

# seções presentes no EN hoje. Crescer esta lista é o que "avançar a tradução" significa.
SECOES = ("## Abstract", "## 1.")


def fatiar(texto: str, inicios: tuple[str, ...], fim_marcadores: tuple[str, ...]) -> str:
    """Concatena as seções nomeadas, da abertura até o próximo cabeçalho de topo."""
    linhas = texto.splitlines(keepends=True)
    saida: list[str] = []
    dentro = False
    for l in linhas:
        if any(l.startswith(p) for p in inicios):
            dentro = True
            saida.append(l)
            continue
        if dentro and any(l.startswith(f) for f in fim_marcadores) and not any(
                l.startswith(p) for p in inicios):
            dentro = False
        if dentro:
            saida.append(l)
    return "".join(saida)


def numeros(texto: str, ingles: bool) -> Counter:
    """Extrai números como Decimal-string canônica, independente de notação.

    Ignora referências de seção (§4.1.1), versões (v1.12), datas ISO e identificadores
    tipo TMLR 2602.06052v4 — não são grandezas e a tradução não os converte.
    """
    t = texto
    t = re.sub(r"§[\d.]+", " ", t)                       # §4.1.1
    t = re.sub(r"\bv\d+(?:\.\d+)*\b", " ", t)            # v1.12, v4
    t = re.sub(r"\b\d{4}-\d{2}-\d{2}\b", " ", t)         # 2026-08-29
    t = re.sub(r"\b\d{2}/\d{2}\b", " ", t)               # 30/08
    t = re.sub(r"`[^`]*`", " ", t)                       # código: nomes, sha, comandos
    # ⚠️ `TMLR 2602.06052v4` tem ESPAÇO antes do número. A primeira versão usava
    # `TMLR[^\s)]*`, que parava no espaço e deixava o identificador entrar como
    # grandeza — lido `260206052` pela convenção PT e `2602.06` pela EN, produzindo
    # uma divergência que não era erro de tradução, e sim do próprio verificador.
    t = re.sub(r"\bTMLR\s*[\d.]+v?\d*", " ", t)
    t = re.sub(r"\bH-\d[\d.]*", " ", t)

    achados: Counter = Counter()
    # milhar + decimal, nas duas convenções
    for m in re.finditer(r"\d[\d.,]*\d|\d", t):
        cru = m.group(0)
        if ingles:
            limpo = cru.replace(",", "")                 # 583,763 -> 583763
        else:
            limpo = cru.replace(".", "").replace(",", ".")  # 583.763 -> 583763; 2,66 -> 2.66
        try:
            v = float(limpo)
        except ValueError:
            continue
        # canônico: sem zeros à direita
        achados[f"{v:g}"] += 1
    return achados


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json")
    a = ap.parse_args()

    if not EN.exists():
        print("MANUSCRIPT-en.md não existe — nada a conferir")
        return 0

    topo = ("## ", "# ")
    pt = numeros(fatiar(PT.read_text(encoding="utf-8"), SECOES, topo), ingles=False)
    en = numeros(fatiar(EN.read_text(encoding="utf-8"), SECOES, topo), ingles=True)

    so_pt = pt - en
    so_en = en - pt
    ok = not so_pt and not so_en

    print(f"  seções conferidas: {', '.join(SECOES)}")
    print(f"  números no PT: {sum(pt.values())}  ·  no EN: {sum(en.values())}")
    if so_pt:
        print("  🔴 no PT e não no EN (ou com contagem menor):")
        for v, n in sorted(so_pt.items(), key=lambda x: -x[1])[:15]:
            print(f"       {v}  ×{n}")
    if so_en:
        print("  🔴 no EN e não no PT (ou com contagem maior):")
        for v, n in sorted(so_en.items(), key=lambda x: -x[1])[:15]:
            print(f"       {v}  ×{n}")
    if ok:
        print("  ✅ paridade exata — todo número do PT aparece no EN, com a mesma contagem")

    if a.json:
        pathlib.Path(a.json).write_text(json.dumps({
            "secoes": list(SECOES),
            "total_pt": sum(pt.values()),
            "total_en": sum(en.values()),
            "so_pt": dict(so_pt),
            "so_en": dict(so_en),
            "paridade": ok,
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"  artefato: {a.json}")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
