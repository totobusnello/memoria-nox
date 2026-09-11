#!/usr/bin/env python3
"""Reconta o NOSSO lado da regua de forma, com o metodo declarado.

Por que existe
--------------
O `regua-simetrica-2026-09-10.md` declarou o metodo dos quatro aceitos
(`ltx_bibitem` no HTML, tokens crus) e NAO declarou como o nosso `30` foi
obtido. O numero ficava entre duas contagens possiveis — obras (24 entao) e
footnotes (43 entao) — e a decisao em aberto estava calibrada contra ele.

Dois defeitos, em direcoes opostas:

  (a) o numerador contava auto-referencia (ponteiro para o nosso codigo), que
      nenhum dos aceitos tem na bibliografia;
  (b) o tokenizador do §5 remove tags HTML, correto para os aceitos (que sao
      HTML) e destrutivo em markdown: `<[^>]+>` casa de um '<' matematico ate
      o '>' seguinte e apaga o texto entre eles (-38%).

CONTROLE: o tokenizador tem de reproduzir as 24.126 palavras publicadas no
commit que as publicou. Se nao reproduzir, nada aqui e comparavel e o script
sai != 0 em vez de imprimir numero.

Uso
---
    python3 reconta-regua-nosso-lado.py [--repo <caminho>] [--regua <commit>]
"""
from __future__ import annotations
import argparse, json, re, subprocess, sys
from pathlib import Path

PISO, TETO_D, TETO_PAL = 2.06, 2.95, 17265
PUBLICADO = 24126          # regua-simetrica §2, linha `nosso`
TOLERANCIA = 60


def mdtok(t: str) -> int:
    """Metodo cru do §5 adaptado a markdown: token separado por espaco com
    >=1 alfanumerico, SEM remocao de tags."""
    return sum(1 for w in t.split() if any(c.isalnum() for c in w))


def _show(repo: Path, ref: str, caminho: str) -> str:
    return subprocess.run(["git", "-C", str(repo), "show", f"{ref}:{caminho}"],
                          capture_output=True, text=True, check=True).stdout


def _le(repo: Path, ref: str, caminho: str) -> str:
    """`ref=None` le o working tree; qualquer outro valor le aquele commit.

    Existe porque a primeira versao lia sempre `git show HEAD:` e portanto NAO
    via o censo ainda nao commitado: reportava 37 obras pela heuristica de
    fallback em vez das 39 do censo, dizendo "censo ainda nao existia neste
    commit" sobre um arquivo que estava no disco ao lado.
    """
    if ref is None:
        return (repo / caminho).read_text(encoding="utf-8")
    return _show(repo, ref, caminho)


def censo(repo: Path, ref: str | None) -> dict:
    md = _le(repo, ref, "paper/paper-tecnico-nox-mem.md")
    defs = set(re.findall(r"^\[\^([A-Za-z0-9_-]+)\]:", md, re.M))
    try:
        c = json.loads(_le(repo, ref, "paper/bibitem-census.json"))
        obra, evid = set(c["obra"]), set(c["evidencia"])
        if (obra | evid) != defs:
            sys.exit(f"{ref}: censo nao fecha com o manuscrito — "
                     f"fora do censo {sorted(defs-(obra|evid))}, "
                     f"no censo e nao no md {sorted((obra|evid)-defs)}")
        n_obra, fonte = len(obra), "bibitem-census.json"
    except (subprocess.CalledProcessError, FileNotFoundError):
        # antes do censo existir: obra = footnote com localizador de terceiro
        n_obra = sum(1 for k, c in re.findall(r"^\[\^([A-Za-z0-9_-]+)\]:(.*)$", md, re.M)
                     if re.search(r"arXiv:\d{4}\.\d{4,5}|doi|10\.\d{4,}/|"
                                  r"\b(ACL|EMNLP|NAACL|ICLR|ICML|NeurIPS|TACL|SIGIR|"
                                  r"TOIS|JMLR|Proceedings|Journal|Transactions)\b", c))
        fonte = "heuristica (censo ainda nao existia neste commit)"
    return {"pal": mdtok(md), "defs": len(defs), "obra": n_obra, "fonte": fonte}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=str(Path(__file__).resolve().parents[3]))
    ap.add_argument("--regua", default="fa3d28e")
    a = ap.parse_args()
    repo = Path(a.repo)

    antes = censo(repo, a.regua)
    d = abs(antes["pal"] - PUBLICADO)
    if d > TOLERANCIA:
        print(f"CONTROLE FALHOU: {a.regua} devolve {antes['pal']} palavras contra "
              f"{PUBLICADO} publicadas (delta {d} > {TOLERANCIA}) — o tokenizador nao "
              f"reproduz o numero, logo nada abaixo seria comparavel", file=sys.stderr)
        return 2
    print(f"controle: {a.regua} devolve {antes['pal']} palavras vs {PUBLICADO} "
          f"publicadas (delta {antes['pal']-PUBLICADO}) ⇒ metodo reproduz")

    b = censo(repo, None)   # working tree: e o que se quer medir
    dens = b["obra"] / (b["pal"] / 1000)
    print(f"\nworking tree: {b['pal']} palavras · {b['defs']} footnotes · {b['obra']} obras "
          f"({b['fonte']})")
    print(f"densidade {dens:.2f}/mil (faixa dos aceitos {PISO}–{TETO_D}) · "
          f"{b['pal']/TETO_PAL:.2f}× o maior aceito")
    if dens >= PISO:
        print("⇒ DENTRO da faixa")
        return 0
    print(f"\nponto fixo — cada obra nova custa W palavras de discussao:")
    for W in (0, 30, 45, 60, 90, 120):
        n = 0
        while (b["obra"] + n) / ((b["pal"] + n * W) / 1000) < PISO:
            n += 1
        print(f"  W={W:3}  ⇒ {n:2} obras novas · {b['pal']+n*W} palavras · "
              f"{(b['pal']+n*W)/TETO_PAL:.2f}× o teto")
    return 0


if __name__ == "__main__":
    sys.exit(main())
