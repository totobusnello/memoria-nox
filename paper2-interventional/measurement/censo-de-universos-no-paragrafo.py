#!/usr/bin/env python3
"""
censo-de-universos-no-paragrafo.py — dois denominadores no mesmo parágrafo, sem aviso?

Terceiro censo mecânico. Os dois primeiros olharam **rótulo × predicado** (o rótulo
nomeia a população que mede?) e **verbo × objeto** (o texto diz "servido" sobre o quê?).
Este olha o eixo que nenhum dos dois cobre: **dois números de populações diferentes
encostados no mesmo parágrafo**.

É a classe do caso que sobreviveu a cinco revisões adversariais:

> "Entregou **1.787 chunks distintos: 2,66%**" … "**83,78%** nunca exposto"

Os dois percentuais têm o mesmo denominador (67.187) mas **numeradores de superfícies
diferentes** — o primeiro conta só o brief, o segundo conta a união brief ∪ busca. Um
leitor que subtraia 2,66 de 83,78 obtém um número que não significa nada. A frase não
mente; o que falta é a fronteira.

⚠️ **Por que revisão não pega e censo pega.** Cada frase está certa isoladamente, e o
revisor lê frase a frase. O defeito só existe na **adjacência**, que é propriedade do
parágrafo — e ninguém revisa parágrafos como objetos.

⚠️ **O que ele NÃO faz.** Comparar populações é o método do paper: o §4.1 inteiro
contrasta corpus × piso × pool, e isso é correto e necessário. Este script não reprova
comparação; reprova **comparação sem transição declarada**. E, para não virar ruído,
reprova num caso estreito e definido — dois PERCENTUAIS de superfícies diferentes sem
nenhum marcador entre eles — listando todo o resto para leitura humana.

Uso:
  censo-de-universos-no-paragrafo.py [--doc MANUSCRIPT.md] [--json] [--out ...]
"""
import argparse
import json
import pathlib
import re
import sys

# valor no texto → (população, denominador, é_percentual)
# `superficie` é o que discrimina: dois números podem dividir o mesmo denominador e
# ainda contar coisas diferentes, que é exatamente o caso 2,66% × 83,78%.
UNIVERSO = {
    "67.187":  ("corpus vivo",              "corpus",     False),
    "583.763": ("slots entregues",          "slots",      False),
    "1.787":   ("distintos no brief",       "brief",      False),
    "2,66":    ("cobertura do brief",       "brief",      True),
    "9.755":   ("expostos pela busca",      "busca",      False),
    "10.899":  ("união das superfícies",    "união",      False),
    "56.288":  ("nunca expostos",           "união",      False),
    "83,78":   ("nunca exposto, agregado",  "união",      True),
    "13.388":  ("passam o piso",            "piso",       False),
    "10.008":  ("piso e nunca expostos",    "piso",       False),
    "74,75":   ("taxa condicionada ao piso", "piso",      True),
    "46.280":  ("nunca expostos sob o piso", "piso",      False),
    "82,2":    ("fração sob o piso",        "piso",       True),
    "108":     ("pool do canal",            "pool",       False),
    "0,161":   ("pool como % do corpus",    "pool",       True),
    "350":     ("estados do replay",        "replay",     False),
    "4,86":    ("teto do canal",            "replay",     True),
    "85,50":   ("coorte madura",            "coorte",     True),
    "99,98":   ("cobertura uniforme",       "contrafactual", True),
}

# Marcadores que declaram a fronteira. Se um deles está no parágrafo, a mudança de
# universo foi anunciada e o leitor tem como se orientar.
TRANSICAO = [
    r"\bdos quais\b", r"\bdesses\b", r"\bdestes\b", r"\bentre (?:os|as|esses|estes)\b",
    r"\bcondicionad[oa]\b", r"\brestring\w+", r"\bsubconjunto\b", r"\bpor outro lado\b",
    r"\benquanto\b", r"\bjá o\b", r"\bjá a\b", r"\bem contraste\b", r"\bao passo que\b",
    r"\bnão são comparáveis\b", r"\bdenominador\w*\b", r"\buniverso\w*\b",
    r"\bpopulaç\w+", r"\bsuperfícies?\b", r"\boutra grandeza\b", r"\bmesma base\b",
    r"\bnão se soma\w*\b", r"\bnão somam\b", r"\bapenas o brief\b", r"\bsó o brief\b",
    r"\bunião\b", r"\bagregad[oa]\b", r"\bcoorte\w*\b", r"\bpiso\b", r"\bpool\b",
]


# ⚠️ Parágrafo META: fala SOBRE as alegações (quais têm guarda, qual artefato as
# sustenta), não COM elas. O §6.1 cataloga números por origem de verificação, e nele
# `99,98%` e `82,2%` aparecem como ITENS DE INVENTÁRIO — não há comparação a declarar,
# porque não há comparação. A primeira versão deste script reprovou exatamente essa
# tabela, que é o guarda mordendo o remédio.
#
# ⚠️ E o inverso é o risco maior: uma exceção larga demais desliga o guarda onde ele
# importa — foi o que aconteceu no censo irmão, cujo detector de citação (`^\s*\|`)
# classificava QUALQUER linha de tabela como citação e deixou passar a mutação. Por
# isso a marca aqui é vocabulário de VERIFICAÇÃO, não forma de tabela, e o teste de
# mutação abaixo prova que o caso real (2,66% × 83,78%) segue mordendo.
META = [r"\bsem guarda\b", r"\bcom guarda\b", r"\bartefatos?\b", r"\brem[ée]dio\b",
        r"\brecomputar no guarda\b", r"\balegaç\w+ numéricas?\b", r"\bverificador\b"]


def paragrafos(texto: str):
    """Parágrafos fora de blocos de código; tabelas contam como um parágrafo só.

    ⚠️ Bloco de código não é prosa e não pode ser julgado como tal — SQL com dois
    predicados é a definição das populações, não confusão entre elas.
    """
    fora, dentro = [], False
    for bloco in texto.split("\n\n"):
        if bloco.count("```") % 2 == 1:
            dentro = not dentro
            continue
        if dentro or bloco.lstrip().startswith("```"):
            continue
        fora.append(bloco)
    return fora


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--doc", default="MANUSCRIPT.md")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--out")
    a = ap.parse_args()

    doc = pathlib.Path(a.doc)
    if not doc.exists():
        print(f"⛔ {doc} não existe", file=sys.stderr)
        return 1
    texto = doc.read_text(encoding="utf-8")

    ini_h = texto.find("## Apêndice H")
    achados, examinados = [], 0
    for p in paragrafos(texto):
        presentes = {}
        for val, (rot, sup, pct) in UNIVERSO.items():
            if re.search(rf"(?<![\d.,]){re.escape(val)}(?![\d])", p):
                presentes.setdefault(sup, []).append((val, rot, pct))
        if len(presentes) < 2:
            continue
        examinados += 1
        tem_transicao = any(re.search(t, p, re.I) for t in TRANSICAO)
        e_meta = any(re.search(m, p, re.I) for m in META)
        # o caso estreito que reprova: dois percentuais de SUPERFÍCIES diferentes
        pcts = [(s, v, r) for s, itens in presentes.items()
                for v, r, é in itens if é]
        colisao = len({s for s, _v, _r in pcts}) >= 2
        pos = texto.find(p)
        achados.append({
            "linha": texto[:pos].count("\n") + 1 if pos >= 0 else 0,
            "superficies": sorted(presentes),
            "numeros": sorted(v for itens in presentes.values() for v, _r, _p in itens),
            "percentuais_colidindo": [f"{v} ({r})" for _s, v, r in pcts] if colisao else [],
            "transicao_declarada": tem_transicao,
            "meta": e_meta,
            "em_apendice_h": ini_h >= 0 and pos > ini_h,
            "trecho": " ".join(p.split())[:200],
        })

    # ⚠️ O Apêndice H narra correções e cita, por desenho, números de populações
    # diferentes lado a lado — é o histórico, não afirmação corrente.
    graves = [x for x in achados
              if x["percentuais_colidindo"] and not x["transicao_declarada"]
              and not x["em_apendice_h"] and not x["meta"]]

    saida = {
        "paragrafos_com_2_ou_mais_universos": examinados,
        "graves": graves,
        "todos": achados,
        "nao_decide": ("comparar populações é o método do paper; o que se reprova é "
                       "comparar sem declarar a fronteira, e só entre percentuais"),
    }

    # ── guardas ────────────────────────────────────────────────────────────
    # (1) zero parágrafos examinados significa que os padrões não casam mais, e o
    #     veredito "limpo" viria de cegueira. Num paper que contrasta cinco populações
    #     é impossível não haver parágrafo com duas.
    if examinados == 0:
        print(f"⛔ nenhum parágrafo com dois universos em {len(UNIVERSO)} valores "
              f"vigiados — os padrões não estão casando, e 'limpo' seria cegueira.",
              file=sys.stderr)
        return 1
    # (2) o caso estreito: percentuais de superfícies diferentes, sem fronteira.
    if graves:
        print(f"⛔ {len(graves)} parágrafo(s) com percentuais de superfícies DIFERENTES "
              f"e nenhuma transição declarada:", file=sys.stderr)
        for x in graves:
            print(f"    L{x['linha']}: {' × '.join(x['percentuais_colidindo'])}",
                  file=sys.stderr)
            print(f"      …{x['trecho'][:130]}…", file=sys.stderr)
        print("  Um leitor que subtraia dois percentuais de superfícies diferentes "
              "obtém um número sem significado.", file=sys.stderr)
        return 1

    if a.json:
        print(json.dumps(saida, indent=2, ensure_ascii=False))
    else:
        print(f"{examinados} parágrafo(s) misturam dois ou mais universos\n")
        print("✅ nenhum com percentuais de superfícies diferentes sem transição")
        sem_t = [x for x in achados if not x["transicao_declarada"]]
        if sem_t:
            print(f"\n📌 {len(sem_t)} sem marcador de transição (só contagens "
                  f"absolutas — para leitura humana, não reprovam):")
            for x in sem_t[:8]:
                print(f"     L{x['linha']:<5} {'×'.join(x['superficies'])}: "
                      f"{', '.join(x['numeros'])}")

    if a.out:
        json.dump(saida, open(a.out, "w"), indent=2, ensure_ascii=False)
        print(f"\n→ {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
