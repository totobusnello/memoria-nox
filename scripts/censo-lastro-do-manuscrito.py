#!/usr/bin/env python3
"""Enumera todo caminho que o manuscrito cita, e diz o que existe e o que nao.

## Por que este script substitui uma lista de mao

O `MANIFESTO-LASTRO.json` nasceu de uma lista que eu escrevi olhando o §6.3.2 --
e lista de mao e amostra vendida como censo. O espaco correto do censo nao e a
minha lembranca do que o paper cita: e o **proprio manuscrito**. Este script le o
manuscrito, extrai os caminhos, e classifica cada um:

  AUSENTE          -- o paper cita e o arquivo nao existe ⇒ o script sai != 0
  so-no-disco      -- existe, mas fora do versionamento ⇒ lastro sem copia
  versionado       -- existe e esta no git

O que ele NAO faz: dizer se o arquivo tem o conteudo que o paper afirma. Ele
mede existencia e alcance, nao correspondencia -- presenca de localizador nao e
correspondencia, e essa confusao ja produziu tres footnotes com autoria
inventada sob guarda verde.

## Dois controles

positivo -- um caminho que o manuscrito cita e que existe tem de ser achado.
negativo -- uma SENTINELA: um caminho inventado, injetado no texto lido, que tem
            de ser classificado AUSENTE. Sem ela, um censo que extrai zero
            caminhos passaria como "nada ausente".
"""
import argparse
import json
import os
import re
import subprocess
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Caminho citado em markdown vive quase sempre entre backticks. Exigimos uma
# barra e um segmento inicial que seja diretorio de topo real do repo -- sem
# isso, `a/b` de prosa matematica entra como caminho.
RE_BACKTICK = re.compile(r"`([^`\n]{3,200})`")
RE_CAMINHO = re.compile(r"^[\w./\-]+$")

SENTINELA = "eval/q4-comparison/output/SENTINELA-que-nao-existe.json"

# DOIS controles positivos, porque o manuscrito cita de duas formas e a primeira
# versao deste script viu so uma. O filtro "o primeiro segmento tem de ser um
# diretorio de topo do repo" -- posto para cortar ruido -- descartava justamente
# `output/rc4/mem0.json` e `cache/rc4-nox-hybrid.db`, que sao os artefatos que
# motivaram o censo. O controle de forma absoluta passava e escondia isso.
CONTROLES_POSITIVOS = {
    "absoluta": "eval/q4-comparison/output/zep.json",
    "relativa": "output/rc4/mem0.json",
}

# ruido que casa o formato de caminho mas nao e caminho deste repo
IGNORAR_PREFIXO = ("http", "www.", "10.5281/", "arxiv", "10.1038/")


def topos(repo):
    saida = {p.split("/")[0] for p in subprocess.run(
        ["git", "-C", repo, "ls-files"], capture_output=True, check=True
    ).stdout.decode().splitlines() if "/" in p}
    return saida


def resolve(cand, validos, universo):
    """Devolve (caminho_resolvido, como) ou (None, motivo).

    O manuscrito cita de duas formas: a partir da raiz do repo
    (`eval/q4-comparison/output/zep.json`) e relativa a um diretorio de trabalho
    (`output/rc4/mem0.json`, relativo a `eval/q4-comparison/`). A segunda forma
    nao tem diretorio de topo do repo no inicio -- e um filtro por topo a
    descarta em silencio.

    Para a forma relativa, procuramos no universo (versionados + existentes no
    disco) quem TERMINA com `/<cand>`. Um unico casamento resolve; varios sao
    reportados como ambiguos em vez de escolhidos, porque escolher seria inventar.
    """
    if cand.split("/")[0] in validos:
        return cand, "absoluta"
    sufixo = "/" + cand
    casam = sorted(u for u in universo if u.endswith(sufixo))
    if len(casam) == 1:
        return casam[0], "relativa"
    if len(casam) > 1:
        return None, f"ambiguo ({len(casam)} candidatos)"
    return None, "nao resolve"


def extrai(texto):
    """So a forma lexica; a resolucao contra o disco vem depois, em `resolve`."""
    achados = set()
    for bruto in RE_BACKTICK.findall(texto):
        cand = bruto.strip().rstrip(".,;:)")
        if "/" not in cand or not RE_CAMINHO.match(cand):
            continue
        if cand.lower().startswith(IGNORAR_PREFIXO):
            continue
        achados.add(cand)
    return achados


MANIFESTO = "eval/q4-comparison/MANIFESTO-LASTRO.json"


def declarados(repo):
    """Caminhos que o MANIFESTO declara como lastro fora do versionamento.

    Por que isto e indispensavel: num checkout limpo -- que e o que a CI tem -- os
    artefatos ignorados nao existem, e um censo que exige presenca no disco fica
    vermelho para sempre e por motivo falso. Ja aconteceu duas vezes neste
    trabalho: arvore fresca nao tem o estado gitignored, e a guarda leu isso como
    "desapareceu do disco".

    O manifesto ESTA versionado, logo viaja com o checkout. Ele e a declaracao de
    "este arquivo existe, fora do git, e eis o sha256 dele" -- e por isso a CI
    consegue distinguir as duas coisas que importam:

      citado e declarado  -> lastro conhecido, ausente DESTE checkout: ok
      citado e nem declarado nem versionado -> citacao para o vazio: falha

    Efeito colateral util: se alguem tirar um artefato do manifesto e o manuscrito
    continuar a cita-lo, a CI grita.
    """
    caminho = os.path.join(repo, MANIFESTO)
    if not os.path.exists(caminho):
        return set()
    try:
        with open(caminho, encoding="utf-8") as fh:
            return set(json.load(fh).get("artefatos", {}))
    except (OSError, ValueError):
        return set()


def universo_de(repo, vers):
    """Versionados + declarados no manifesto + o que existe no disco."""
    u = set(vers) | declarados(repo)
    for base in ("eval", "paper", "docs", "experiments"):
        raiz = os.path.join(repo, base)
        if not os.path.isdir(raiz):
            continue
        for r, ds, fs in os.walk(raiz):
            ds[:] = [d for d in ds if d not in
                     (".venv", ".venv-zep", "node_modules", "__pycache__")]
            rel = os.path.relpath(r, repo)
            for f in fs:
                u.add(os.path.join(rel, f))
            for d in ds:
                u.add(os.path.join(rel, d))
    return u


def versionados(repo):
    return set(subprocess.run(["git", "-C", repo, "ls-files"],
                              capture_output=True, check=True
                              ).stdout.decode().splitlines())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", default=RAIZ)
    ap.add_argument("--doc", action="append",
                    default=["paper/paper-tecnico-nox-mem.md"],
                    help="manuscrito(s) a varrer")
    a = ap.parse_args()
    repo = a.repo

    validos = topos(repo)
    vers = versionados(repo)

    texto = ""
    for d in a.doc:
        caminho = os.path.join(repo, d)
        if not os.path.exists(caminho):
            print(f"documento ausente: {d}", file=sys.stderr)
            return 2
        with open(caminho, encoding="utf-8", errors="ignore") as fh:
            texto += fh.read() + "\n"

    universo = universo_de(repo, vers)

    # sentinela injetada no texto lido: o censo tem de acusa-la como AUSENTE
    brutos = extrai(texto + f"\nver `{SENTINELA}` para o controle negativo\n")

    if SENTINELA not in brutos:
        print("SENTINELA FALHOU: o extrator nao achou o caminho injetado ⇒ nao mede",
              file=sys.stderr)
        return 2
    for forma, alvo in CONTROLES_POSITIVOS.items():
        if alvo not in brutos:
            print(f"CONTROLE[{forma}] FALHOU: o manuscrito cita {alvo} e o extrator "
                  f"nao o achou ⇒ cego para esta forma", file=sys.stderr)
            return 2
        r, como = resolve(alvo, validos, universo)
        if r is None:
            print(f"CONTROLE[{forma}] FALHOU: {alvo} extraido mas nao resolvido "
                  f"({como})", file=sys.stderr)
            return 2
        print(f"controle[{forma}]: {alvo} → {r} ({como})")
    print("sentinela: caminho inventado foi acusado ⇒ o censo ve ausencia")

    decl = declarados(repo)
    ausentes, so_disco, ok, nao_resolvidos, fora_do_checkout = [], [], [], [], []
    for bruto in sorted(brutos):
        if bruto == SENTINELA:
            continue
        c, como = resolve(bruto, validos, universo)
        if c is None:
            if os.path.exists(os.path.join(repo, bruto)):
                c, como = bruto, "absoluta"
            else:
                nao_resolvidos.append((bruto, como))
                continue
        abs_ = os.path.join(repo, c)
        if not os.path.exists(abs_):
            # declarado no manifesto ⇒ e lastro conhecido que nao viaja no git,
            # nao citacao para o vazio
            (fora_do_checkout if c in decl else ausentes).append(c)
            continue
        if c in vers:
            ok.append(c)
        else:
            tam = 0
            if os.path.isfile(abs_):
                tam = os.path.getsize(abs_)
            elif os.path.isdir(abs_):
                for r, _, fs in os.walk(abs_):
                    tam += sum(os.path.getsize(os.path.join(r, f))
                               for f in fs if os.path.exists(os.path.join(r, f)))
            so_disco.append((c, tam))

    print(f"\ncaminhos citados pelo manuscrito: {len(brutos) - 1}")
    print(f"  versionados            : {len(ok)}")
    print(f"  so no disco (sem copia): {len(so_disco)}")
    print(f"  declarados no manifesto, ausentes deste checkout: "
          f"{len(fora_do_checkout)}")
    print(f"  AUSENTES               : {len(ausentes)}")
    print(f"  nao resolvidos         : {len(nao_resolvidos)}")
    if fora_do_checkout:
        print("\n  (lastro declarado no manifesto — esperado faltar num clone:)")
        for c in fora_do_checkout:
            print(f"     {c}")
    if nao_resolvidos:
        print("\n  (nao resolvidos — nem caminho do repo nem sufixo unico:)")
        for b, motivo in nao_resolvidos:
            print(f"     {b}  [{motivo}]")

    if so_disco:
        print("\n⚠️ CITADO E FORA DO GIT — existe so nesta maquina")
        for c, t in sorted(so_disco, key=lambda x: -x[1]):
            print(f"   {t/1e6:9.1f} MB  {c}")
    if ausentes:
        print("\n🔴 CITADO E AUSENTE — o manuscrito aponta para o vazio", file=sys.stderr)
        for c in ausentes:
            print(f"   {c}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
