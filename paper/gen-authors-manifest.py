#!/usr/bin/env python3
"""Gera paper/authors-manifest.json a partir dos arXiv IDs do manuscrito.

Vai a rede (arxiv.org/abs) e escreve o manifesto que a perna (3) do
`footnotes_check` consome OFFLINE. A separacao e deliberada: guarda de CI que
depende de rede falha por rede, e guarda que falha por rede ensina a ignorar
guarda.

⚠️ Um ID que a rede nao resolver NAO entra no manifesto — e a perna (3) reporta
IDs ausentes como NAO-VERIFICADOS, nao como aprovados. Resposta vazia mais
parser que reporta ausencia e indistinguivel de ausencia real; foi assim que o
`export.arxiv.org` (inalcancavel daqui) me fez declarar tres IDs validos como
inexistentes em 2026-09-10. Por isso: `arxiv.org/abs` sobre HTTPS, e controle
positivo obrigatorio antes de escrever.

Uso:  python3 paper/gen-authors-manifest.py [--check]
      --check: nao escreve; sai !=0 se o manifesto no disco estiver desatualizado.
"""
from __future__ import annotations
import html
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PAPER = RAIZ / "paper" / "paper-tecnico-nox-mem.md"
MANIFESTO = RAIZ / "paper" / "authors-manifest.json"
# um ID antigo e estavel, citado no proprio manuscrito, para o controle positivo
CONTROLE = "1809.09600"


def busca(aid: str) -> dict | None:
    with urllib.request.urlopen(f"https://arxiv.org/abs/{aid}", timeout=30) as r:
        h = r.read().decode("utf8", "replace")
    aut = [html.unescape(x).split(",")[0].strip()
           for x in re.findall(r'citation_author" content="([^"]*)"', h)]
    t = re.search(r'citation_title" content="([^"]*)"', h)
    if not aut or not t:
        return None
    return {"surnames": aut, "title": html.unescape(t.group(1))}


def main() -> int:
    checar = "--check" in sys.argv
    ids = sorted(set(re.findall(r"arxiv:\s*(\d{4}\.\d{4,5})",
                            PAPER.read_text(), re.I)))
    print(f"IDs no manuscrito: {len(ids)}")

    ctl = busca(CONTROLE)
    if not ctl or "Yang" not in ctl["surnames"]:
        print(f"CONTROLE POSITIVO FALHOU em {CONTROLE} — a sonda nao alcanca o arXiv "
              f"ou o parser mudou. Nada escrito.", file=sys.stderr)
        return 2
    print(f"controle OK ({CONTROLE} -> {ctl['surnames'][0]} et al.)")

    novo, falhos = {}, []
    for i in ids:
        try:
            d = busca(i)
        except Exception as e:
            d = None
            print(f"  ?? {i}: {type(e).__name__}", file=sys.stderr)
        if d is None:
            falhos.append(i)
        else:
            novo[i] = d
        time.sleep(0.35)

    print(f"resolvidos {len(novo)}/{len(ids)}"
          + (f" | NAO resolvidos (ficam NAO-VERIFICADOS): {falhos}" if falhos else ""))

    saida = json.dumps(novo, ensure_ascii=False, indent=1, sort_keys=True)
    if checar:
        atual = MANIFESTO.read_text() if MANIFESTO.exists() else ""
        if atual.strip() != saida.strip():
            print("manifesto DESATUALIZADO — rode sem --check", file=sys.stderr)
            return 1
        print("manifesto em dia")
        return 0
    MANIFESTO.write_text(saida + "\n")
    print(f"escrito {MANIFESTO.relative_to(RAIZ)} ({len(saida)} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
