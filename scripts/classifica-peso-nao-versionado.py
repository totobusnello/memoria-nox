#!/usr/bin/env python3
"""Classifica o peso NAO versionado em tres classes de recuperabilidade.

"Apague os caches" e conselho barato e perigoso: neste projeto ja se perdeu o
corpus servido de um ensaio por parecer descartavel, e ele nao tinha copia
nenhuma. Entao antes de apagar, classificar -- e a classe nao e o nome do
diretorio, e o que custa refazer:

  gratis        -- um comando reconstroi, sem chamar API paga (venv, node_modules,
                   __pycache__, build de site estatico)
  pagando       -- reconstroi, mas passa pela fatura: cache de embedding e de LLM,
                   store vetorial que exige re-embedding
  irrecuperavel -- output de corrida, corpus servido, artefato que o manuscrito
                   cita. A corrida nao se repete igual: pod efemero, versao nao
                   registrada, non-determinismo do provider. Reproducibility nao
                   e replicability, e o paper cita numeros DESTA corrida

⚠️ A classe `irrecuperavel` nao se apaga com base neste script. Ele existe para
que a decisao seja tomada sabendo o que custa, nao para autorizar nada.
"""
import json
import os
import subprocess
import sys

RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MANIFESTO = "eval/q4-comparison/MANIFESTO-LASTRO.json"

# ordem importa: a primeira regra que casa decide
REGRAS = [
    ("gratis", ("/.venv", "/.venv-zep", "/node_modules", "/__pycache__",
                "/.pytest_cache", "/.mypy_cache", "/.astro", "/dist/",
                "/.svelte-kit", "/.next")),
    ("pagando", ("/cache/hipporag2", "/llm_cache", "/cache/raw",
                 "/.mem0-chroma", "/chroma", "/embeddings")),
    ("irrecuperavel", ("/output/", "/output-", "/results/", "/out/",
                       "/cache/rc4", "/cache/hybrid", "/cache/nox-mem")),
]


def classe_de(rel, declarados):
    if rel in declarados:
        return "irrecuperavel"
    alvo = "/" + rel
    for nome, marcas in REGRAS:
        if any(m in alvo for m in marcas):
            return nome
    return "nao classificado"


def main():
    vers = set(subprocess.run(["git", "-C", RAIZ, "ls-files"],
                              capture_output=True, check=True
                              ).stdout.decode().splitlines())
    decl = set()
    mp = os.path.join(RAIZ, MANIFESTO)
    if os.path.exists(mp):
        with open(mp, encoding="utf-8") as fh:
            decl = set(json.load(fh).get("artefatos", {}))

    tot = {}
    exemplos = {}
    for r, ds, fs in os.walk(RAIZ):
        ds[:] = [d for d in ds if d != ".git"]
        for f in fs:
            caminho = os.path.join(r, f)
            rel = os.path.relpath(caminho, RAIZ)
            if rel in vers:
                continue
            try:
                tam = os.path.getsize(caminho)
            except OSError:
                continue
            c = classe_de(rel, decl)
            tot[c] = tot.get(c, 0) + tam
            if tam > exemplos.get(c, (0, ""))[0]:
                exemplos[c] = (tam, rel)

    ordem = ["gratis", "pagando", "irrecuperavel", "nao classificado"]
    soma = sum(tot.values()) or 1
    print(f"{'classe':<18} {'MB':>9} {'%':>6}  maior exemplo")
    for c in ordem:
        if c not in tot:
            continue
        t, ex = exemplos[c]
        print(f"{c:<18} {tot[c]/1e6:9.1f} {100*tot[c]/soma:5.1f}%  {ex} ({t/1e6:.0f} MB)")
    print(f"{'TOTAL':<18} {soma/1e6:9.1f}")
    print("\n⚠️ `irrecuperavel` inclui o que o manifesto declara: a corrida nao se")
    print("   repete igual, e o manuscrito cita numeros dela. Nao apagar sem backup.")
    if "nao classificado" in tot:
        print("\n⚠️ ha peso NAO CLASSIFICADO: nenhuma regra casou, logo nenhuma decisao")
        print("   sobre ele esta apoiada neste script.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
