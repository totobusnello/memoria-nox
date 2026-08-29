#!/usr/bin/env python3
"""
lacuna-no-eixo-de-tamanho.py — "×0,38 por década" descreve uma inclinação que existe?

Objeção de revisão adversarial (Kimi, 2026-08-29), item 4:

> `β = −0,961 ⇒ ×0,38 por década de tamanho` é uma parametrização forte para n=15
> unidades independentes, e o eixo tem um buraco: nenhum tipo entre n=53 e n=1.046.
> "Por década" convida o leitor a interpolar numa faixa onde não existe observação.

Este script mede o buraco. Ele não decide se o achado é verdadeiro — o §4.2 já reporta
o jackknife que mostra que ele sobrevive por pouco — decide se a **forma** de reportar
é honesta.

⚠️ O que ele NÃO faz: separar tamanho de **curadoria**. Nenhuma medição aqui distingue
"coleções pequenas cabem na superfície" de "coleções pequenas são mais curadas". As
parciais do §4.2 controlam idade, importância média e tamanho do texto; nenhuma delas
é curadoria, e não há no corpus uma variável que a meça. Fica declarado como não
separado — que é diferente de separado e nulo.

Uso:
  lacuna-no-eixo-de-tamanho.py [--json] [--out ...]
"""
import argparse
import json
import math
import sys

# Verbatim da tabela do §4.2 (os 15 tipos, sem o filtro `HAVING total >= 10`).
TIPOS = {
    "lesson": 53, "test": 14, "project": 43, "feedback": 17, "digest": 25,
    "person": 14, "decision": 11, "shared": 40, "graph_node": 1046, "daily": 3231,
    "team": 15308, "distilled": 14456, "other": 32920, "pending": 6, "procedure": 3,
}
PEQUENO, GRANDE = 100, 1000


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--out")
    a = ap.parse_args()

    xs = sorted((math.log10(n), k, n) for k, n in TIPOS.items())
    lacunas = sorted(
        ({"decadas": round(xs[i + 1][0] - xs[i][0], 3),
          "de": {"tipo": xs[i][1], "n": xs[i][2]},
          "para": {"tipo": xs[i + 1][1], "n": xs[i + 1][2]}}
         for i in range(len(xs) - 1)),
        key=lambda d: -d["decadas"])
    amplitude = round(xs[-1][0] - xs[0][0], 3)
    maior = lacunas[0]

    pequenos = [x for x in xs if x[2] < PEQUENO]
    grandes = [x for x in xs if x[2] >= GRANDE]
    meio = [x for x in xs if PEQUENO <= x[2] < GRANDE]

    # ⚠️ Este guarda vem ANTES de `saida`, e a ordem é o ponto: o dict indexa
    # `pequenos[0]`, então uma nuvem vazia levantava IndexError antes de qualquer
    # guarda rodar. Um teste de mutação de 29/08 leu esse traceback como "o guarda
    # mordeu" — abortar não é diagnosticar, e guarda colocado depois do uso não é
    # guarda.
    if not pequenos or not grandes:
        print(f"⛔ nuvem vazia (pequenos={len(pequenos)}, grandes={len(grandes)}) — "
              f"os limiares {PEQUENO}/{GRANDE} não descrevem mais este corpus.",
              file=sys.stderr)
        return 1

    saida = {
        "tipos": len(TIPOS),
        "amplitude_do_eixo_decadas": amplitude,
        "maior_lacuna": maior,
        "pct_da_amplitude_sem_ponto": round(100 * maior["decadas"] / amplitude, 1),
        "tres_maiores_lacunas": lacunas[:3],
        "nuvem_pequenos": {"tipos": len(pequenos), "n_min": pequenos[0][2],
                           "n_max": pequenos[-1][2]},
        "nuvem_grandes": {"tipos": len(grandes), "n_min": grandes[0][2],
                          "n_max": grandes[-1][2]},
        "tipos_na_faixa_intermediaria": len(meio),
        "nao_separado": "tamanho vs curadoria — nenhuma variável do corpus mede curadoria",
    }

    # ── guardas ────────────────────────────────────────────────────────────
    # (1) a conclusão inteira é "há um vazio no meio". Se algum tipo cair nele, ela
    #     deixa de valer e o script tem de acusar, não reportar o vazio antigo.
    if meio:
        print(f"⛔ a faixa {PEQUENO}–{GRANDE} deixou de ser vazia: "
              f"{[m[1] for m in meio]} — a leitura de 'duas nuvens' não vale mais.",
              file=sys.stderr)
        return 1
    # (2) as duas nuvens têm de particionar os tipos; se não, os limiares se
    #     sobrepõem e as contagens reportadas somam errado.
    if len(pequenos) + len(grandes) != len(TIPOS):
        print("⛔ as nuvens não particionam os tipos.", file=sys.stderr)
        return 1

    if a.json:
        print(json.dumps(saida, indent=2, ensure_ascii=False))
    else:
        print(f"{len(TIPOS)} tipos · amplitude {amplitude} décadas de log₁₀(n)\n")
        for l in lacunas[:3]:
            print(f"  {l['decadas']:>6.3f} décadas entre {l['de']['tipo']}"
                  f"(n={l['de']['n']}) e {l['para']['tipo']}(n={l['para']['n']})")
        print(f"\n⇒ a maior lacuna é {saida['pct_da_amplitude_sem_ponto']}% da amplitude "
              f"SEM um único ponto, e a faixa {PEQUENO}–{GRANDE} tem "
              f"{len(meio)} tipos.")
        print(f"⇒ o dado são DUAS NUVENS: {len(pequenos)} tipos de "
              f"{pequenos[0][2]} a {pequenos[-1][2]} e {len(grandes)} de "
              f"{grandes[0][2]} a {grandes[-1][2]}. 'Por década' interpola no vazio.")

    if a.out:
        json.dump(saida, open(a.out, "w"), indent=2, ensure_ascii=False)
        print(f"→ {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
