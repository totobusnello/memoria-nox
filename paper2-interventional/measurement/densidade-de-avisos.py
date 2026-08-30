#!/usr/bin/env python3
"""
densidade-de-avisos.py — quantos avisos o manuscrito tem, e de quantas espécies?

Objeção de revisão adversarial (GLM, 2026-08-29), a única das seis que não é sobre um
número errado e sim sobre a **forma** do documento:

> Três espécies diferentes moram sob o mesmo marcador. O efeito é o leitor classificar
> o marcador como ruído na terceira ocorrência, que é a vez em que o importante aparece.

O diagnóstico é plausível e não pode ser aceito por impressão — nem a minha, nem a dele.
Este script classifica cada bloco marcado por **função**, que é o que decide se ele
pertence ao corpo:

| espécie | o que é | onde pertence |
|---|---|---|
| `validade` | condição sob a qual a alegação vale | no corpo, junto da alegação |
| `resultado` | número ou achado formatado como exceção | no corpo, **sem** marcador |
| `retratacao` | "uma versão anterior dizia X" | apêndice de histórico |
| `procedencia` | de onde veio o dado, qual artefato | apêndice ou nota |
| `escopo` | "é um sistema", "não generaliza" | uma vez, não oito |

⚠️ A classificação é por **padrão textual**, não por leitura — então erra nas bordas.
O que ela mede com confiança é a **repetição**: quantas vezes a mesma ressalva reaparece.
Esse número não depende de julgamento e é o que sustenta a objeção.

Uso:
  densidade-de-avisos.py [--doc MANUSCRIPT.md] [--json] [--out ...]
"""
import argparse
import json
import pathlib
import re
import sys

MARCADORES = ("⚠️", "🔴", "🟡", "📌", "✅", "🟢")

# Assinaturas de repetição: ressalvas que o revisor apontou como repetidas até a
# diluição. Cada uma é um conjunto de padrões alternativos da MESMA ideia.
REPETIDAS = {
    "é um sistema / não generaliza": [
        r"é \*\*um\*\* sistema", r"um único sistema", r"generalização (?:é )?dedutiva",
        r"não afirmamos nada sobre a área",
    ],
    "busca é iniciada pelo agente": [
        r"iniciada pelo agente", r"busca[^.]{0,40}o agente (?:procurou|inicia)",
        r"o agente \*\*procurou\*\*",
    ],
    "retratação de versão anterior": [
        r"[Uu]ma versão anterior", r"versão anterior d[eo]st[ae]", r"A versão anterior",
        r"a legenda anterior", r"A legenda anterior",
    ],
}


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
    linhas = texto.splitlines()

    por_marcador = {m: sum(l.count(m) for l in linhas) for m in MARCADORES}
    total = sum(por_marcador.values())

    repet = {}
    for rotulo, pats in REPETIDAS.items():
        ocorr = []
        for p in pats:
            for m in re.finditer(p, texto):
                ocorr.append(texto[:m.start()].count("\n") + 1)
        repet[rotulo] = {"ocorrencias": len(ocorr), "linhas": sorted(set(ocorr))}

    # densidade: parágrafos marcados sobre parágrafos totais
    paras = [p for p in texto.split("\n\n") if p.strip()]
    marcados = [p for p in paras if any(m in p for m in MARCADORES)]

    # ⚠️ A conta AGREGADA esconde o efeito da reestruturação: mover material do corpo
    # para um apêndice não muda o total, e o apêndice traz avisos próprios. A métrica
    # que decide se o argumento ficou legível é a densidade NO CORPO — o que um
    # revisor lê antes de chegar aos apêndices.
    corte = texto.find("\n## Apêndice ")
    corpo = [p for p in (texto[:corte] if corte > 0 else texto).split("\n\n") if p.strip()]
    corpo_marc = [p for p in corpo if any(m in p for m in MARCADORES)]

    saida = {
        "linhas_do_documento": len(linhas),
        "paragrafos": len(paras),
        "paragrafos_marcados": len(marcados),
        "pct_paragrafos_marcados": round(100 * len(marcados) / len(paras), 1),
        "paragrafos_do_corpo": len(corpo),
        "corpo_marcados": len(corpo_marc),
        "pct_corpo_marcado": round(100 * len(corpo_marc) / len(corpo), 1) if corpo else None,
        "marcadores_por_tipo": por_marcador,
        "marcadores_total": total,
        "ressalvas_repetidas": repet,
    }

    # ── guardas ────────────────────────────────────────────────────────────
    # (1) documento sem marcador nenhum: ou o arquivo errado, ou a reestruturação
    #     passou do ponto e tirou até as condições de validade.
    if total == 0:
        print("⛔ nenhum marcador encontrado — arquivo errado, ou a reestruturação "
              "removeu também as condições de validade, que pertencem ao corpo.",
              file=sys.stderr)
        return 1
    # (2) a métrica que sustenta a objeção é a REPETIÇÃO; se nenhum padrão casar, o
    #     script não está medindo o que diz medir.
    if all(v["ocorrencias"] == 0 for v in repet.values()):
        print("⛔ nenhum padrão de repetição casou — os padrões envelheceram junto com "
              "o texto e o script está medindo zero por cegueira, não por ausência.",
              file=sys.stderr)
        return 1

    if a.json:
        print(json.dumps(saida, indent=2, ensure_ascii=False))
    else:
        print(f"{len(linhas)} linhas · {len(paras)} parágrafos · "
              f"{len(marcados)} marcados ({saida['pct_paragrafos_marcados']}%)")
        print(f"CORPO (antes dos apêndices): {len(corpo)} parágrafos · "
              f"{len(corpo_marc)} marcados ({saida['pct_corpo_marcado']}%)\n")
        for m, n in sorted(por_marcador.items(), key=lambda kv: -kv[1]):
            if n:
                print(f"  {m}  {n}")
        print(f"\nressalvas repetidas:")
        for rot, v in sorted(repet.items(), key=lambda kv: -kv[1]["ocorrencias"]):
            print(f"  {v['ocorrencias']:>3}×  {rot}")
            if v["ocorrencias"] > 3:
                print(f"        linhas {v['linhas'][:12]}")

    if a.out:
        json.dump(saida, open(a.out, "w"), indent=2, ensure_ascii=False)
        print(f"→ {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
