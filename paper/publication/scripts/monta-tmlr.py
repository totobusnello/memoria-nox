#!/usr/bin/env python3
r"""Reparte o manuscrito nas tres pecas que o template do TMLR pede.

O `tmlr.sty` quer titulo, `\author{}` e `\begin{abstract}` no preambulo do
documento, e o corpo depois. O manuscrito e um markdown unico em que titulo,
bloco de autoria e abstract sao *texto*. Este script faz o corte, e sobretudo
**verifica** o corte: um corte silenciosamente errado produz um PDF que parece
certo e perdeu uma peca.

Tres regras do template que ficam aqui como pos-condicao executavel:

1. "The abstract must be limited to one paragraph" (main.tex do upstream) —
   abortamos se o abstract tiver linha em branco no meio.
2. Autoria nao pode vazar para o corpo: o `tmlr.sty` sem `[accepted]`
   suprime o `\author{}`, mas nao suprime o nome escrito no meio do texto.
3. A nota de hardware vive *antes* do abstract no markdown e tem de continuar
   antes da §1 no PDF — se ela simplesmente desaparecer, o PDF deixa de
   declarar o que foi omitido, o que e uma perda de honestidade e nao de forma.

Saida: um unico `tmlr-full.md` com bloco YAML (title/author/abstract) mais o
corpo. O template default do pandoc ja emite \title, \author, \maketitle e
\begin{abstract} na ordem que o `tmlr.sty` espera, entao nao existe wrapper
.tex com marcadores para manter em paralelo.

O `author` sai como LaTeX cru (`{=latex}`) de proposito: o campo leva `\name`,
`\email`, `\\` e `\addr`, macros do `tmlr.sty`, e o pandoc escaparia a barra
dupla para `\textbackslash{}` se o campo fosse texto normal.

Modos:
  --write <dir>   grava <dir>/tmlr-full.md (+ titulo e abstract soltos, p/ inspecao)
  --autoteste     controle positivo: entradas defeituosas TEM de abortar
"""
from __future__ import annotations

import pathlib
import re
import sys

PAPER = pathlib.Path(__file__).resolve().parents[2] / "paper-tecnico-nox-mem.md"

# Vai dentro do \author{}, que o `tmlr.sty` sem [accepted] suprime. Fica
# declarado para que o camera-ready seja `\usepackage[accepted]{tmlr}` e nao
# uma reescrita. Verificado no PDF: o nome nao aparece no texto extraido.
AUTOR_LATEX = (
    r"\name Luiz Antonio Busnello \email lab@nuvini.com.br \\ "
    r"\addr Independent Researcher"
)


class CorteInvalido(Exception):
    pass


def reparte(md: str) -> tuple[str, str, str]:
    """Devolve (titulo, abstract, corpo). Levanta CorteInvalido em tudo o resto."""
    m = re.match(r"^# (.+)\n", md)
    if not m:
        raise CorteInvalido("primeira linha nao e um '# titulo'")
    titulo = m.group(1).strip()

    m = re.search(r"(?m)^## Abstract\n\n(.*?)\n\n---\n\n(## 1\..*)\Z", md, re.S)
    if not m:
        raise CorteInvalido(
            "nao achei '## Abstract' seguido de '---' e '## 1.' — "
            "a estrutura do manuscrito mudou e o corte nao pode ser adivinhado"
        )
    abstract, corpo = m.group(1).strip(), m.group(2)

    if "\n\n" in abstract:
        n = len(abstract.split("\n\n"))
        raise CorteInvalido(
            f"o abstract tem {n} paragrafos; o template do TMLR limita a um "
            "('The abstract must be limited to one paragraph')"
        )
    if re.search(r"\[\^[a-z0-9-]+\](?!:)", abstract):
        raise CorteInvalido(
            "o abstract referencia uma footnote; dentro de \\begin{abstract} "
            "a nota nao e composta no lugar certo — mover a marca para o corpo"
        )

    # o miolo entre o titulo e o abstract: autoria, versao, nota de hardware
    cabeca = md[: md.index("\n## Abstract")].split("\n", 1)[1]
    nota = [
        p.strip()
        for p in cabeca.split("\n\n")
        if p.strip() and not p.strip().startswith(("**Luiz", "**Anonymous", "*Independent", "**Version", "---"))
    ]
    if len(nota) != 1:
        raise CorteInvalido(
            f"esperava exatamente 1 paragrafo de nota entre o titulo e o abstract, "
            f"achei {len(nota)}: {[n[:40] for n in nota]}"
        )
    corpo = nota[0] + "\n\n" + corpo
    return titulo, abstract, corpo


def monta_md(titulo: str, abstract: str, corpo: str) -> str:
    """Cola o bloco YAML no corpo. Aborta se o titulo nao couber entre aspas."""
    if '"' in titulo:
        raise CorteInvalido(
            f"o titulo tem aspas duplas e o YAML o envolve em aspas duplas: {titulo!r}"
        )
    if "\n" in abstract:
        raise CorteInvalido("abstract com quebra de linha nao cabe numa linha de YAML")
    return (
        "---\n"
        f'title: "{titulo}"\n'
        "author:\n"
        f"  - '`{AUTOR_LATEX}`{{=latex}}'\n"
        "abstract: |\n"
        f"  {abstract}\n"
        "---\n\n"
        f"{corpo}"
    )


def autoteste() -> None:
    bom = (
        "# T\n\n**Anonymous authors**  \nPaper under double-blind review\n\n"
        "**Version** v1\n\nnota de hardware.\n\n---\n\n"
        "## Abstract\n\numa frase so.\n\n---\n\n## 1. Intro\n\ncorpo.\n"
    )
    t, a, c = reparte(bom)
    assert (t, a) == ("T", "uma frase so."), (t, a)
    assert c.startswith("nota de hardware.") and "## 1. Intro" in c, c
    assert "Anonymous" not in c and "**Version**" not in c, c

    defeitos = {
        "abstract com dois paragrafos": bom.replace("uma frase so.", "um.\n\ndois."),
        "abstract com footnote": bom.replace("uma frase so.", "uma frase[^x]."),
        "sem titulo": bom[2:],
        "sem o separador antes da §1": bom.replace("\n\n---\n\n## 1.", "\n\n## 1."),
        "nota de hardware apagada": bom.replace("nota de hardware.\n\n", ""),
        "duas notas onde devia haver uma": bom.replace(
            "nota de hardware.", "nota de hardware.\n\nnota a mais."
        ),
    }
    for nome, texto in defeitos.items():
        try:
            reparte(texto)
        except CorteInvalido:
            print(f"  ✅ {nome:38s} abortou")
        else:
            sys.exit(f"  ❌ {nome}: o corte ACEITOU entrada defeituosa")
    full = monta_md(t, a, c)
    assert full.startswith('---\ntitle: "T"\n'), full[:60]
    assert "`{=latex}'" in full and r"\\ \addr" in full, "autoria nao saiu como latex cru"
    assert full.rstrip().endswith("corpo."), full[-40:]
    try:
        monta_md('tem "aspas"', a, c)
    except CorteInvalido:
        print('  ✅ titulo com aspas duplas               abortou')
    else:
        sys.exit("  ❌ titulo com aspas duplas: monta_md ACEITOU")

    print("autoteste ok — 1 caso bom reparte, 7 defeitos abortam")


def main() -> int:
    if "--autoteste" in sys.argv:
        autoteste()
        return 0
    if "--write" not in sys.argv:
        print(__doc__)
        return 2
    destino = pathlib.Path(sys.argv[sys.argv.index("--write") + 1])
    fonte = pathlib.Path(sys.argv[sys.argv.index("--fonte") + 1]) if "--fonte" in sys.argv else PAPER
    autoteste()
    try:
        titulo, abstract, corpo = reparte(fonte.read_text(encoding="utf-8"))
    except CorteInvalido as e:
        print(f"corte invalido em {fonte}: {e}", file=sys.stderr)
        return 3
    try:
        full = monta_md(titulo, abstract, corpo)
    except CorteInvalido as e:
        print(f"montagem invalida: {e}", file=sys.stderr)
        return 3
    destino.mkdir(parents=True, exist_ok=True)
    (destino / "tmlr-full.md").write_text(full, encoding="utf-8")
    (destino / "tmlr-abstract.md").write_text(abstract + "\n", encoding="utf-8")
    (destino / "tmlr-title.txt").write_text(titulo + "\n", encoding="utf-8")
    pal = lambda t: sum(1 for w in t.split() if any(c.isalnum() for c in w))
    print(f"titulo   : {titulo}")
    print(f"abstract : 1 paragrafo, {pal(abstract)} palavras")
    print(f"corpo    : {pal(corpo)} palavras")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
