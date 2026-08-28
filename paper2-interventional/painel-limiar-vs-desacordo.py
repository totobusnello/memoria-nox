#!/usr/bin/env python3
"""
painel-limiar-vs-desacordo.py — o desacordo do painel é de LIMIAR ou de FATO?

O estrato S2 consolidado repousa numa família (`xai`): 22 de 22 têm `xai = S2`, e sem
ela sobreviveriam 5. A pergunta que decide o conserto — e que precede escolher conserto —
é **de que espécie** é o desacordo:

  (a) **deslocamento de limiar** — as famílias ordenam os episódios igual e cortam a
      fronteira S1/S2 em lugares diferentes. Os conjuntos S2 seriam então **aninhados**.
      Conserto: normalizar por família. **Não exige readjudicar nada.**

  (b) **desacordo genuíno** — as famílias discordam sobre QUAIS episódios são graves,
      não sobre onde cortar. Os conjuntos se **cruzam**. Nenhuma normalização salva; o
      conserto é rubrica ancorada, e custa readjudicação.

⚠️ As duas hipóteses produzem a MESMA estatística agregada (shares de S2 diferentes) e
a mesma concordância par a par alta. Distinguir exige olhar par a par, episódio a
episódio — e é o que este script faz.

⚠️ E não usa leave-one-family-out: com 3 painelistas a mediana inferior é o valor do
meio, com 2 vira o mínimo, então o LOO mistura mudança de estimador com mudança de
painel. Aqui tudo é contagem direta sobre os votos.

Uso:
  painel-limiar-vs-desacordo.py --verdicts ~/.paper2-verdicts/verdicts-lambda-2026-08-21.jsonl
"""
import argparse
import json
import sys
from collections import defaultdict
from itertools import combinations

ORD = {"S0": 0, "S1": 1, "S2": 2, "S3": 3, "S4": 4}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--verdicts", required=True)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    votos = defaultdict(dict)          # episode_id -> panelist -> nivel
    for linha in open(a.verdicts):
        d = json.loads(linha)
        if d.get("status") != "ok" or d.get("level") not in ORD:
            continue
        votos[d["episode_id"]][d["panelist"]] = ORD[d["level"]]

    panels = sorted({p for v in votos.values() for p in v})
    completos = {e: v for e, v in votos.items() if len(v) == len(panels)}

    out = {"verdicts": a.verdicts, "painelistas": panels,
           "episodios": len(votos), "com_voto_de_todos": len(completos), "pares": []}

    for p, q in combinations(panels, 2):
        # Conjuntos "grave" (>= S2) de cada um, sobre os episódios completos
        Sp = {e for e, v in completos.items() if v[p] >= 2}
        Sq = {e for e, v in completos.items() if v[q] >= 2}
        # Cruzamento em nível: um chama S2+ o que o outro chama S0. Se (a) valesse,
        # isso seria ~0 — deslocar um limiar não move episódio de S0 para S2.
        cruz_pq = sum(1 for e, v in completos.items() if v[p] >= 2 and v[q] == 0)
        cruz_qp = sum(1 for e, v in completos.items() if v[q] >= 2 and v[p] == 0)
        # Discordância assinada: quantas vezes p é mais severo, quantas menos.
        mais_p = sum(1 for v in completos.values() if v[p] > v[q])
        mais_q = sum(1 for v in completos.values() if v[q] > v[p])
        igual = len(completos) - mais_p - mais_q
        # Monotonicidade: existe episódio em que p < q E outro em que p > q com a
        # mesma dupla de níveis trocada? Inversões são a marca de (b).
        inversoes = sum(1 for v in completos.values()
                        if (v[p], v[q]) in {(2, 0), (0, 2), (3, 0), (0, 3)})
        # Jaccard e κ sobre o BINÁRIO ≥S2. O κ publicado (0,874) é do veredito
        # falha/sucesso; este é o do NÍVEL, que é o eixo que carrega o estrato — e a
        # concordância "alta" do primeiro não diz nada sobre o segundo.
        n = len(completos)
        a11 = len(Sp & Sq)
        a10, a01 = len(Sp - Sq), len(Sq - Sp)
        a00 = n - a11 - a10 - a01
        po = (a11 + a00) / n
        pe = ((a11 + a10) * (a11 + a01) + (a01 + a00) * (a10 + a00)) / (n * n)
        kappa = (po - pe) / (1 - pe) if pe < 1 else None
        jac = a11 / (a11 + a10 + a01) if (a11 + a10 + a01) else None

        out["pares"].append({
            "par": f"{p}×{q}",
            "jaccard_do_conjunto_grave": round(jac, 3) if jac is not None else None,
            "kappa_binario_S2mais": round(kappa, 3) if kappa is not None else None,
            f"graves_{p}": len(Sp), f"graves_{q}": len(Sq),
            "intersecao": len(Sp & Sq),
            "aninhado": "sim" if (Sp <= Sq or Sq <= Sp) else "NAO",
            "so_de_" + p: len(Sp - Sq), "so_de_" + q: len(Sq - Sp),
            "cruzamento_S2mais_vs_S0": {f"{p}>=S2 & {q}=S0": cruz_pq,
                                        f"{q}>=S2 & {p}=S0": cruz_qp},
            "mais_severo_" + p: mais_p, "mais_severo_" + q: mais_q, "igual": igual,
            "inversoes_extremas": inversoes,
        })

    # Teste global de aninhamento: ordenando as famílias por severidade, os conjuntos
    # graves formam uma cadeia?
    graves = {p: {e for e, v in completos.items() if v[p] >= 2} for p in panels}
    ordem = sorted(panels, key=lambda p: len(graves[p]))
    cadeia = all(graves[ordem[i]] <= graves[ordem[i + 1]] for i in range(len(ordem) - 1))
    fora = []
    for i in range(len(ordem) - 1):
        fora += [(ordem[i], e) for e in graves[ordem[i]] - graves[ordem[i + 1]]]
    # Controle positivo do instrumento: a nota publicada diz que "sem xai
    # sobreviveriam 5", e 5 é exatamente |moonshot ∩ zhipu| sob a regra de mínimo com
    # 2 painelistas. Se este script não reproduzir esse 5, ele está lendo outra coisa.
    outros = [p for p in panels if p != "xai"]
    sem_xai = len(graves[outros[0]] & graves[outros[1]]) if len(outros) == 2 else None
    out["controle_positivo"] = {
        "|{}∩{}|".format(*outros): sem_xai,
        "ancora_publicada": 5,
        "reproduz": sem_xai == 5,
    }

    out["cadeia_de_aninhamento"] = {
        "ordem_por_severidade": [f"{p}={len(graves[p])}" for p in ordem],
        "e_cadeia_perfeita": cadeia,
        "violacoes": len(fora),
        "veredito": ("DESLOCAMENTO DE LIMIAR: conjuntos aninhados, normalizar por "
                     "família resolve sem readjudicar")
                    if cadeia else
                    ("MISTO — ver os pares: o aninhamento pode valer para uma família "
                     "e falhar entre as outras, e nesse caso o rótulo agregado engana"),
    }

    if a.json:
        print(json.dumps(out, indent=2, ensure_ascii=False))
        return 0

    print(f"painelistas: {panels} · episódios com voto de todos: {len(completos)}\n")
    for r in out["pares"]:
        p, q = r["par"].split("×")
        print(f"— {r['par']}")
        print(f"    graves(≥S2): {p}={r['graves_'+p]} · {q}={r['graves_'+q]} · "
              f"∩={r['intersecao']} · só {p}={r['so_de_'+p]} · só {q}={r['so_de_'+q]}"
              f" · aninhado: {r['aninhado']}")
        print(f"    Jaccard do conjunto grave = {r['jaccard_do_conjunto_grave']} · "
              f"κ binário(≥S2) = {r['kappa_binario_S2mais']}")
        print(f"    cruzamento com S0: {r['cruzamento_S2mais_vs_S0']}")
        print(f"    mais severo: {p}={r['mais_severo_'+p]} · {q}={r['mais_severo_'+q]} "
              f"· empate={r['igual']} · inversões extremas={r['inversoes_extremas']}")
    c = out["cadeia_de_aninhamento"]
    print(f"\ncadeia por severidade: {' ⊆ '.join(c['ordem_por_severidade'])}")
    print(f"cadeia perfeita: {c['e_cadeia_perfeita']} · violações: {c['violacoes']}")
    print(f"\n⇒ {c['veredito']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
