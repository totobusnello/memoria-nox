#!/usr/bin/env python3
"""Produz a variante ANONIMA do manuscrito para a submissao ao TMLR.

Por que existe um filtro em vez de uma edicao na fonte: sao necessarias DUAS
saidas do mesmo texto -- a identificada (Zenodo hoje, arXiv depois) e a anonima
do TMLR, cuja politica exige *"double blind of the TMLR submission itself must
be maintained by not linking to another version that includes the authors'
names"* (author-guide, lido 2026-09-11). Editar a fonte perde a identificada e
faz as duas divergirem em silencio.

O nome do sistema (`nox-mem`) FICA -- decisao do dono do projeto, 2026-09-11. A
politica proibe LINKAR versao identificada, nao proibe nomear, e instrui
reviewers a nao buscarem. E' desanonimizador conhecido e aceito.

Modos:
  --check <arquivo>...   audita vazamento de identidade e sai != 0 se achar
  --write <saida>        escreve a variante anonima do manuscrito
  --autoteste            roda o controle positivo e sai

⚠️ O modo --check tem CONTROLE POSITIVO obrigatorio a cada execucao: antes de
auditar os arquivos reais, ele varre uma sentinela sintetica que contem um
exemplo de cada padrao. Se a sentinela nao acusar os N padroes, o auditor esta
quebrado e o script aborta -- em vez de reportar "nenhum vazamento", que e' a
saida identica de quem nao conseguiu procurar.
"""
from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[3]
FONTE = RAIZ / "paper" / "paper-tecnico-nox-mem.md"

# (rotulo, regex). Cada um tem de aparecer na SENTINELA abaixo.
PADROES: list[tuple[str, str]] = [
    ("nome do autor",        r"Busnello|Luiz\s+Antonio"),
    ("email",                r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}"),
    ("usuario do github",    r"totobusnello"),
    ("apelido do operador",  r"\bToto\b"),
    ("DOI/URL do Zenodo",    r"10\.5281/zenodo\.\d+|zenodo\.org/records?/\d+"),
    ("afiliacao",            r"\bNuvini\b|\bGenerantis\b"),
    ("caminho local",        r"/Users/[a-z]+\b"),
    ("host de producao",     r"srv\d{6,}|\broot@[\w.-]+|(?<![§.\d])\b(?:\d{1,3}\.){3}\d{1,3}\b(?![.\d])"),
]

SENTINELA = (
    "Luiz Antonio Busnello <lab@example.com> github.com/totobusnello/x "
    "Toto 10.5281/zenodo.22649269 Nuvini /Users/lab root@host srv1826603 "
    "100.87.8.44\n"
)

# Sentinela NEGATIVA: cada item TEM de passar ilesa. Sem esta perna, apertar um
# padrao para tirar um falso positivo poderia tirar tambem o verdadeiro, e o
# "0 vazamentos" seguinte continuaria a parecer boa noticia.
SENTINELA_LIMPA = (
    "sections 5.1.8.1 5.1.8.2 5.1.8.3 and 5.1.8.4 report the knob series; "
    "version 1.2.3.4 of the schema; nDCG 0.6455 on n=2,482\n"
)

_IPV4 = re.compile(r"^(?:\d{1,3}\.){3}\d{1,3}$")


def _e_numeracao(s: str) -> bool:
    """`5.1.8.3` e' numero de secao; `100.87.8.44` e' endereco.

    Um endereco real quase sempre tem um octeto de 3 digitos (100.x, 127.x,
    192.x) ou pelo menos dois de 2 digitos. A numeracao deste manuscrito chega a
    quatro niveis e nunca passa de um digito por nivel.

    A regra e' INCOMPLETA de proposito: um host `4.5.6.7` passaria. As outras
    duas pernas do padrao (srv+digitos e root@...) cobrem os hosts que este
    projeto de facto nomeia, e declarar o buraco aqui e' melhor do que finge-lo
    fechado. Instalada em 2026-09-11 depois de o auditor acusar `5.1.8.1`–`.4`
    como host ao varrer o suplemento.
    """
    octetos = s.split(".")
    return not (any(len(o) == 3 for o in octetos)
                or sum(1 for o in octetos if len(o) >= 2) >= 2)


# Substituicoes aplicadas para gerar a variante anonima.
SUBSTITUICOES: list[tuple[str, str]] = [
    # linha de autoria
    (r"^\*\*Luiz Antonio Busnello\*\*.*$", "**Anonymous authors**  \nPaper under double-blind review"),
    # ponteiro do repositorio: o usuario do github E' o nome do autor
    (r"^\*\*Repository:\*\* github\.com/totobusnello/[A-Za-z0-9_.-]+$",
     "**Supplementary material (anonymized):** the sections this manuscript cites as "
     "§S\\*, the aggregate result artifacts behind the §6 tables, and the claim-guard "
     "apparatus described in §6.9. The source tree and evaluation harness are withheld "
     "for double-blind review — anonymizing them would require rewriting host addresses "
     "and identifiers inside code offered as reproducible — and the identified "
     "repository will be cited in the camera-ready version."),
]


def audita(texto: str) -> list[tuple[str, str]]:
    """Devolve [(rotulo, casamento)] para cada vazamento encontrado."""
    achados: list[tuple[str, str]] = []
    for rotulo, rx in PADROES:
        for m in re.finditer(rx, texto, re.M):
            achado = m.group(0)
            if rotulo == "host de producao" and _IPV4.match(achado) and _e_numeracao(achado):
                continue
            achados.append((rotulo, achado))
    return achados


def controle_positivo() -> None:
    """Duas pernas: acusa tudo o que deve, e nada do que nao deve.

    A perna negativa existe porque apertar um padrao para matar um falso
    positivo pode matar o verdadeiro junto — e o "0 vazamentos" seguinte
    continuaria a ler-se como boa noticia.
    """
    limpos = audita(SENTINELA_LIMPA)
    if limpos:
        sys.exit(
            "controle NEGATIVO falhou: o auditor acusou "
            f"{[a for _, a in limpos]} numa sentinela sem vazamento nenhum — "
            "o padrao esta a acusar numeracao de secao como endereco")
    vistos = {r for r, _ in audita(SENTINELA)}
    faltando = [r for r, _ in PADROES if r not in vistos]
    if faltando:
        sys.exit(
            "CONTROLE POSITIVO FALHOU — o auditor nao viu estes padroes na "
            f"sentinela: {faltando}. O auditor esta quebrado; 'nenhum vazamento' "
            "seria indistinguivel de 'nao consegui procurar'."
        )
    print(f"controle positivo: {len(PADROES)}/{len(PADROES)} padroes acusados na sentinela")


def anonimiza(texto: str) -> str:
    for rx, novo in SUBSTITUICOES:
        texto, n = re.subn(rx, novo, texto, flags=re.M)
        if n == 0:
            sys.exit(f"ancora ausente, nada escrito: {rx!r}")
    return texto


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", nargs="*", metavar="ARQUIVO")
    ap.add_argument("--write", metavar="SAIDA")
    ap.add_argument("--autoteste", action="store_true")
    a = ap.parse_args()

    if a.autoteste:
        controle_positivo()
        # o filtro remove o que a sentinela injeta nos dois sitios que ele cobre?
        amostra = "**Luiz Antonio Busnello**  \nx\n**Repository:** github.com/totobusnello/memoria-nox"
        saida = anonimiza(amostra)
        resta = audita(saida)
        print(f"filtro sobre amostra sintetica: {len(resta)} vazamento(s) restante(s) {resta}")
        return 0 if not resta else 1

    if a.write:
        controle_positivo()
        saida = anonimiza(FONTE.read_text(encoding="utf-8"))
        resta = audita(saida)
        if resta:
            for r, m in resta:
                print(f"  VAZAMENTO {r}: {m!r}", file=sys.stderr)
            sys.exit(f"variante anonima ainda tem {len(resta)} vazamento(s) — nao escrita")
        Path(a.write).write_text(saida, encoding="utf-8")
        print(f"escrito {a.write}: 0 vazamentos em {len(PADROES)} padroes")
        return 0

    if a.check is not None:
        controle_positivo()
        alvos = [Path(x) for x in a.check] or [FONTE]
        ruim = 0
        for f in alvos:
            achados = audita(f.read_text(encoding="utf-8"))
            print(f"  {'🔴' if achados else 'ok'} {f}: {len(achados)} vazamento(s)")
            for r, m in achados[:12]:
                print(f"       {r}: {m!r}")
            ruim += len(achados)
        return 1 if ruim else 0

    ap.print_help()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
