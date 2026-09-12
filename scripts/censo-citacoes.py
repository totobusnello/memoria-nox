#!/usr/bin/env python3
"""Conta quem cita cada arquivo, para decidir o que pode ir para `_archive/`.

Por que existe: mover um arquivo com `git mv` quebra em silencio toda citacao
feita a ele -- e o caminho por que um artefato e citado vive FORA do artefato.
Este censo mede a citacao ANTES do movimento.

Duas pernas, reportadas SEPARADAMENTE porque respondem perguntas diferentes:

  por_caminho  -- alguem escreveu o caminho relativo (ex. `docs/FOO-2026-05-18.md`).
                  Precisa e o que quebra literalmente no `git mv`.
  por_basename -- alguem escreveu so o nome do arquivo (ex. `FOO-2026-05-18.md`).
                  Pega citacao em prosa, mas admite homonimo.

Um arquivo so e seguro para arquivar se as DUAS pernas derem zero. Assertar pelo
composto esconderia a perna errada atras da certa.

Controle positivo obrigatorio: um par conhecido (arquivo, citadores esperados) tem
de ser encontrado. Se o controle falhar, o instrumento nao esta medindo e sai != 0
-- "medi zero" e "nao consegui medir" teriam a mesma saida sem isso.
"""
import argparse
import os
import subprocess
import sys
from collections import defaultdict

# Um controle POR PERNA. Uma perna quebrada fica invisivel atras da outra se o
# controle for do composto -- e as duas pernas leem o repo com semanticas
# diferentes, logo uma pode estar morta enquanto a outra responde.
#
# por_caminho : o `docs/...RUNBOOK.md` e citado pelo caminho relativo inteiro.
# por_basename: `output-2026-09-10/zep.json` NUNCA aparece por caminho completo em
#               doc nenhum -- o manuscrito cita `output/zep.json`, seu homonimo.
#               E exatamente o caso que a perna de basename existe para pegar.
CONTROLES = {
    "por_caminho": ("docs/A2-TIER3-MIGRATION-RUNBOOK.md", 1),
    "por_basename": ("eval/q4-comparison/output-2026-09-10/zep.json", 1),
}

BIN = {".pdf", ".png", ".jpg", ".jpeg", ".gif", ".zip", ".pickle", ".sqlite",
       ".docx", ".ico", ".woff", ".woff2", ".db", ".tar", ".gz"}


def versionados(repo):
    out = subprocess.run(["git", "-C", repo, "ls-files", "-z"],
                         capture_output=True, check=True).stdout
    return [p for p in out.decode().split("\0") if p]


def texto_de(repo, paths):
    """Le uma vez cada arquivo de texto; devolve {path: conteudo}."""
    corpo = {}
    for p in paths:
        if os.path.splitext(p)[1].lower() in BIN:
            continue
        try:
            with open(os.path.join(repo, p), "r", encoding="utf-8", errors="ignore") as fh:
                corpo[p] = fh.read()
        except (OSError, IsADirectoryError):
            continue
    return corpo


def censo(repo, candidatos, corpo):
    por_caminho = defaultdict(list)
    por_basename = defaultdict(list)
    bases = {}
    for c in candidatos:
        bases[c] = os.path.basename(c)
    for citador, txt in corpo.items():
        for c in candidatos:
            if citador == c:                      # auto-referencia nao conta
                continue
            if c in txt:
                por_caminho[c].append(citador)
            b = bases[c]
            # basename sozinho: so conta se o caminho completo nao apareceu nesse citador
            if b in txt and c not in txt:
                por_basename[c].append(citador)
    return por_caminho, por_basename


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=str(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    ap.add_argument("--dir", action="append", required=True,
                    help="diretorio cujos arquivos SOLTOS na raiz sao candidatos")
    ap.add_argument("--padrao", default="",
                    help="so candidatos cujo nome contem esta substring (ex. 2026-05)")
    args = ap.parse_args()
    repo = args.repo

    todos = versionados(repo)
    candidatos = []
    for d in args.dir:
        pref = d.rstrip("/") + "/"
        for p in todos:
            if not p.startswith(pref):
                continue
            if p[len(pref):].count("/"):          # so o nivel raiz do diretorio
                continue
            if args.padrao and args.padrao not in os.path.basename(p):
                continue
            candidatos.append(p)

    corpo = texto_de(repo, todos)
    for perna, (alvo, minimo) in CONTROLES.items():
        if alvo not in todos:
            print(f"CONTROLE[{perna}] FALHOU: {alvo} nao esta versionado", file=sys.stderr)
            return 2
        pc, pb = censo(repo, [alvo], corpo)
        achou = len(pc.get(alvo, [])) if perna == "por_caminho" else len(pb.get(alvo, []))
        if achou < minimo:
            print(f"CONTROLE[{perna}] FALHOU: {alvo} tinha de ser achado por >= "
                  f"{minimo}, o instrumento achou {achou} ⇒ esta perna nao mede",
                  file=sys.stderr)
            return 2
        print(f"controle[{perna}]: {alvo} → {achou} citador(es) ⇒ perna mede")
    print()

    if not candidatos:
        print("nenhum candidato -- confira --dir/--padrao", file=sys.stderr)
        return 2

    por_caminho, por_basename = censo(repo, candidatos, corpo)
    livres, presos = [], []
    for c in sorted(candidatos):
        nc, nb = len(por_caminho.get(c, [])), len(por_basename.get(c, []))
        (livres if nc == 0 and nb == 0 else presos).append((c, nc, nb))

    print(f"candidatos: {len(candidatos)}  ·  livres: {len(livres)}  ·  citados: {len(presos)}\n")
    if livres:
        print("== LIVRES (as duas pernas em zero) — arquivar nao quebra citacao")
        for c, _, _ in livres:
            print(f"   {c}")
    if presos:
        print("\n== CITADOS — mover exige atualizar quem cita")
        for c, nc, nb in presos:
            quem = (por_caminho.get(c, []) + por_basename.get(c, []))[:3]
            print(f"   {c}\n      por_caminho={nc} por_basename={nb}  ex: {', '.join(quem)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
