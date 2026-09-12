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

Cinco pernas, porque tres formas de citar escapavam das duas primeiras -- e a
primeira delas foi achada por uma voz adversarial no proprio `CLAUDE.md`:

  por_chaves   -- expansao de chaves: `audits/2026-04-26-{A1v2-...,W2-cleanup}.md`
                  cita tres arquivos e NENHUM aparece por caminho nem por basename,
                  porque depois de `cleanup` vem `,` e nao `.md`.
  por_glob     -- `audits/*.md`, `audits/2026-05-*`: citacao por CONJUNTO nao tem
                  caminho nem basename. Quem cita o conjunto cita cada membro.
  por_semext   -- `[[2026-05-01-review]]` ou o nome sem `.md`.

Um arquivo so e seguro para arquivar se TODAS as pernas derem zero. Assertar pelo
composto esconderia a perna errada atras da certa.

⚠️ Cegueira DECLARADA e testada: arquivos binarios de texto (`.docx`) sao lidos
descomprimindo o XML interno -- grep cru neles le 0 bytes e reporta como quem
nada achou. E citadores FORA do versionamento (memoria do agente, outros repos,
depositos imutaveis, issues) nao entram: passe `--extra <dir>` para incluir.

DOIS controles, porque provam coisas diferentes:

  positivo -- um por perna, sobre citacao real do repo: prova que a perna acha
              *alguma* citacao.
  negativo (sentinela) -- um texto sintetico com UMA citacao de cada forma cega
              conhecida. Prova que o instrumento SABE VER cada forma. Sem ele, um
              controle positivo escolhido depois de o primeiro falhar so mostra
              que o script foi ajustado ate o controle passar.

Qualquer controle que falhe faz o script sair != 0: "nao ha citacao" e "nao
consegui medir citacao" nao podem ter a mesma saida.
"""
import io
import re
import zipfile
import argparse
import fnmatch
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
CONTROLES_POSITIVOS = {
    "por_caminho": ("docs/A2-TIER3-MIGRATION-RUNBOOK.md", 1),
    "por_basename": ("eval/q4-comparison/output-2026-09-10/zep.json", 1),
}

# Controle NEGATIVO. Cada linha cita `audits/SENTINELA-<perna>.md` de UMA forma, e
# nenhuma delas escreve o caminho de um jeito que outra perna pegue. Se qualquer
# perna nao acusar a sua, ela esta cega e o script para.
SENTINELA_ALVOS = {
    "por_caminho": "audits/SENTINELA-caminho.md",
    "por_basename": "audits/SENTINELA-basename.md",
    "por_chaves": "audits/SENTINELA-chaves.md",
    "por_glob": "audits/SENTINELA-glob.md",
    "por_semext": "audits/SENTINELA-semext.md",
}
SENTINELA_TEXTO = (
    "ver audits/SENTINELA-caminho.md para o caminho inteiro\n"
    "ver SENTINELA-basename.md, so o nome do arquivo\n"
    "ver audits/SENTINELA-{chaves,ignore-me}.md via expansao de chaves\n"
    "ver audits/SENTINELA-glob*.md via conjunto\n"
    "ver [[SENTINELA-semext]] sem extensao nenhuma\n"
)

BIN = {".pdf", ".png", ".jpg", ".jpeg", ".gif", ".zip", ".pickle", ".sqlite",
       ".ico", ".woff", ".woff2", ".db", ".tar", ".gz"}
# .docx NAO entra em BIN: e zip, e grep cru nele le 0 bytes e reporta "nao cita",
# que e indistinguivel de "nao consegui ler". Lemos o XML interno.
ZIPADO = {".docx", ".xlsx", ".pptx"}


def versionados(repo):
    out = subprocess.run(["git", "-C", repo, "ls-files", "-z"],
                         capture_output=True, check=True).stdout
    return [p for p in out.decode().split("\0") if p]


def texto_de(repo, paths):
    """Le uma vez cada arquivo de texto; devolve {path: conteudo}."""
    corpo = {}
    for p in paths:
        ext = os.path.splitext(p)[1].lower()
        if ext in BIN:
            continue
        alvo = os.path.join(repo, p)
        if ext in ZIPADO:
            try:
                with zipfile.ZipFile(alvo) as z:
                    partes = [z.read(n).decode("utf-8", "ignore")
                              for n in z.namelist() if n.endswith(".xml")]
                corpo[p] = " ".join(partes)
            except (OSError, zipfile.BadZipFile, KeyError):
                pass
            continue
        try:
            with open(alvo, "r", encoding="utf-8", errors="ignore") as fh:
                corpo[p] = fh.read()
        except (OSError, IsADirectoryError):
            continue
    return corpo


PERNAS = ("por_caminho", "por_basename", "por_chaves", "por_glob", "por_semext")

RE_CHAVES = re.compile(r"([\w./\-]*?)\{([^{}]+)\}([\w./\-]*)")


def expande_chaves(txt):
    """Devolve os caminhos que uma expansao de chaves cita.

    `audits/2026-04-26-{A,B}.md` -> {audits/2026-04-26-A.md, audits/2026-04-26-B.md}
    Nenhum deles aparece literalmente no texto, e e por isso que esta perna existe.
    """
    saida = set()
    for pre, meio, pos in RE_CHAVES.findall(txt):
        if "," not in meio:
            continue
        for item in meio.split(","):
            saida.add(pre + item.strip() + pos)
    return saida


RE_GLOB = re.compile(r"[\w./\-]*\*[\w./\-]*")


def censo(repo, candidatos, corpo):
    achados = {perna: defaultdict(list) for perna in PERNAS}
    bases = {c: os.path.basename(c) for c in candidatos}
    semext = {c: os.path.splitext(os.path.basename(c))[0] for c in candidatos}

    for citador, txt in corpo.items():
        chaves = expande_chaves(txt) if "{" in txt else set()
        globs = [g for g in RE_GLOB.findall(txt) if "/" in g] if "*" in txt else []
        for c in candidatos:
            if citador == c:                      # auto-referencia nao conta
                continue
            tem_caminho = c in txt
            if tem_caminho:
                achados["por_caminho"][c].append(citador)
            if bases[c] in txt and not tem_caminho:
                achados["por_basename"][c].append(citador)
            if c in chaves:
                achados["por_chaves"][c].append(citador)
            if semext[c] in txt and bases[c] not in txt and not tem_caminho:
                achados["por_semext"][c].append(citador)
            for g in globs:
                # o glob cita o conjunto; se o candidato cai nele, esta citado
                if fnmatch.fnmatch(c, g):
                    achados["por_glob"][c].append(f"{citador} (via {g})")
                    break
    return achados


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=str(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
    ap.add_argument("--dir", action="append", required=True,
                    help="diretorio cujos arquivos SOLTOS na raiz sao candidatos")
    ap.add_argument("--extra", action="append",
                    help="diretorio FORA do repo a incluir como citador "
                         "(memoria do agente, outro repo) -- a cegueira que sobra")
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
    for d in (args.extra or []):
        for raiz, _, arqs in os.walk(d):
            for a in arqs:
                if os.path.splitext(a)[1].lower() in (".md", ".txt", ".json", ".py"):
                    caminho = os.path.join(raiz, a)
                    try:
                        with open(caminho, encoding="utf-8", errors="ignore") as fh:
                            corpo["[externo] " + caminho] = fh.read()
                    except OSError:
                        pass

    # controle NEGATIVO primeiro: prova que cada perna SABE VER a sua forma
    sent = censo(repo, list(SENTINELA_ALVOS.values()),
                 {"[sentinela]": SENTINELA_TEXTO})
    for perna, alvo in SENTINELA_ALVOS.items():
        if not sent[perna].get(alvo):
            print(f"SENTINELA[{perna}] FALHOU: a perna nao acusou {alvo} "
                  f"⇒ esta cega para a sua forma de citacao", file=sys.stderr)
            return 2
    print(f"sentinela: {len(SENTINELA_ALVOS)}/{len(SENTINELA_ALVOS)} pernas "
          f"acusaram a sua forma ⇒ nenhuma esta cega")

    for perna, (alvo, minimo) in CONTROLES_POSITIVOS.items():
        if alvo not in todos:
            print(f"CONTROLE[{perna}] FALHOU: {alvo} nao esta versionado", file=sys.stderr)
            return 2
        achou = len(censo(repo, [alvo], corpo)[perna].get(alvo, []))
        if achou < minimo:
            print(f"CONTROLE[{perna}] FALHOU: {alvo} tinha de ser achado por >= "
                  f"{minimo}, o instrumento achou {achou} ⇒ esta perna nao mede",
                  file=sys.stderr)
            return 2
        print(f"controle[{perna}]: {alvo} → {achou} citador(es) ⇒ perna mede")
    print(f"citadores lidos: {len(corpo)}")
    print()

    if not candidatos:
        print("nenhum candidato -- confira --dir/--padrao", file=sys.stderr)
        return 2

    achados = censo(repo, candidatos, corpo)
    livres, presos = [], []
    for c in sorted(candidatos):
        cont = {p: len(achados[p].get(c, [])) for p in PERNAS}
        (livres if sum(cont.values()) == 0 else presos).append((c, cont))

    print(f"candidatos: {len(candidatos)}  ·  livres: {len(livres)}  ·  citados: {len(presos)}\n")
    if livres:
        print("== LIVRES (as CINCO pernas em zero) — arquivar nao quebra citacao")
        for c, _ in livres:
            print(f"   {c}")
    if presos:
        print("\n== CITADOS — mover exige atualizar quem cita")
        for c, cont in presos:
            vivas = " ".join(f"{p}={n}" for p, n in cont.items() if n)
            quem = [q for p in PERNAS for q in achados[p].get(c, [])][:2]
            print(f"   {c}\n      {vivas}  ex: {', '.join(quem)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
