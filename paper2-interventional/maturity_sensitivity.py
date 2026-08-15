#!/usr/bin/env python3
"""Sensibilidade dos parâmetros de sizing à MATURIDADE do corpus.

⚠️ EXPLORATORIA, NAO PRE-ESPECIFICADA. Não altera nenhum número travado. Existe
porque o cálculo de δ (Apêndice B) expôs algo que nenhuma das análises
anteriores tinha olhado.

O QUE FOI ENCONTRADO
A densidade de repeated failure por epoch não é estacionária. Nos primeiros
epochs do corpus ela é praticamente zero e depois sobe uma ordem de grandeza.
A causa não é ruído: a condição (i) de oportunidade exige um *failure episode*
com a mesma assinatura escrito ≥1 epoch antes, e esse estoque **cresce de 0 a
64 assinaturas ao longo do corpus, sem saturar**. Em 2026-08-14, o último
epoch disponível, ele ainda estava subindo.

POR QUE ISSO IMPORTA PARA O SIZING
`r̂`, `p̂0` e ICC foram estimados sobre o corpus inteiro, isto é, sobre uma
mistura de regimes. Três consequências, em direções que **não** se cancelam:

1. `p̂0` é puxado para baixo pelos epochs iniciais (taxa ~0,005 contra ~0,12
   depois). `p̂0` menor ⇒ `N` maior.
2. O ICC é inflado, porque a transição regime-inicial→regime-maduro é variância
   *entre* clusters que não é estrutura de cluster — é tendência.
   ICC maior ⇒ design effect maior ⇒ `N` maior.
3. δ (§B.5) herda a mesma transição e fica inflado.

Ou seja: os três parâmetros erram no mesmo sentido, e `N = 154` é
provavelmente **conservador** — mas por um motivo que não era conhecido quando
foi travado, e isso precisa ser dito.

O QUE ESTE SCRIPT NAO RESOLVE
Não sabe se a não-estacionariedade é artefato de janela ou propriedade do
sistema. Se o estoque de assinaturas cresce indefinidamente com o uso, então
o estudo real **também** rodará sob tendência, e residualizar no sizing seria
otimista. O §5 do pré-registro já residualiza tendência **no teste** (outcome
regredido em study-day, resíduos permutados); o sizing não. Essa assimetria é
o achado, e resolvê-la é decisão do titular, não deste script.

O corte por maturidade é feito por **estoque de assinaturas elegíveis**, que
depende só da condição (i) e nunca do desfecho do epoch corrente — não é um
corte escolhido olhando o resultado.

    python3 maturity_sensitivity.py --episodes ... --verdicts ... --estrato-b-ids ...
"""
from __future__ import annotations

import argparse
import collections
import json
import sys
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pilot_replay as pr


def p95(xs: list[float]) -> float:
    if not xs:
        return float("nan")
    s = sorted(xs)
    if len(s) == 1:
        return s[0]
    pos = 0.95 * (len(s) - 1)
    lo = int(pos)
    return s[lo] + (pos - lo) * (s[min(lo + 1, len(s) - 1)] - s[lo])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--episodes", required=True)
    ap.add_argument("--verdicts", required=True)
    ap.add_argument("--estrato-b-ids", required=True)
    ap.add_argument("--replicas", nargs="*", default=[])
    a = ap.parse_args()

    instaveis = frozenset(pr.episodios_instaveis(a.replicas)) if a.replicas else frozenset()
    verdicts = pr.carregar_verdicts(Path(a.verdicts), instaveis)
    eps = pr.carregar_episodios(Path(a.episodes), verdicts)

    primeiro_failure: dict[str, object] = {}
    for e in sorted(eps, key=lambda x: x.ts):
        if e.estado == "failure" and (e.sig not in primeiro_failure
                                      or e.ts < primeiro_failure[e.sig]):
            primeiro_failure[e.sig] = e.ts
    limiar = timedelta(hours=pr.EPOCH_H)

    spans = pr.span_por_sessao(eps)
    horas: dict[object, float] = collections.defaultdict(float)
    sessoes: dict[object, set] = collections.defaultdict(set)
    for (ep, s), h in spans.items():
        horas[ep] += h
        sessoes[ep].add(s)

    analisaveis = [e for e in eps if e.offset_h >= pr.WASHOUT_H]
    ids = {l.strip() for l in Path(a.estrato_b_ids).read_text().splitlines() if l.strip()}
    estrato_a = [e for e in analisaveis if e.err]
    resto = [e for e in analisaveis if not e.err]
    estrato_b = [e for e in resto if e.id in ids]
    peso = {e.id: 1.0 for e in estrato_a}
    peso.update({e.id: len(resto) / len(estrato_b) for e in estrato_b})

    op: dict[object, float] = collections.defaultdict(float)
    rp: dict[object, float] = collections.defaultdict(float)
    rp_sessao: dict[tuple, float] = collections.defaultdict(float)
    for e in estrato_a + estrato_b:
        t0 = primeiro_failure.get(e.sig)
        if t0 is None or t0 > e.epoch - limiar or e.estado == "unknown":
            continue
        op[e.epoch] += peso[e.id]
        if e.estado == "failure":
            rp[e.epoch] += peso[e.id]
            rp_sessao[(e.epoch, e.sessao)] += peso[e.id]

    todos_epochs = sorted(ep for ep in horas if horas[ep] > 0)
    estoque = {ep: sum(1 for t0 in primeiro_failure.values() if t0 <= ep - limiar)
               for ep in todos_epochs}

    def bloco(epochs_sel: list) -> dict:
        tot_op = sum(op.get(ep, 0.0) for ep in epochs_sel)
        tot_rp = sum(rp.get(ep, 0.0) for ep in epochs_sel)
        tot_h = sum(horas[ep] for ep in epochs_sel)
        dens = {ep: rp.get(ep, 0.0) / horas[ep] for ep in epochs_sel}
        difs = []
        for k in range(len(epochs_sel) - 1):
            gap = (epochs_sel[k + 1] - epochs_sel[k]).total_seconds() / 3600
            if abs(gap - pr.EPOCH_H) < 1e-6:
                difs.append(abs(dens[epochs_sel[k + 1]] - dens[epochs_sel[k]]))
        d: dict[object, list[float]] = collections.defaultdict(list)
        for (ep, s), h in spans.items():
            if ep in set(epochs_sel) and len(sessoes[ep]) >= 2:
                d[ep].append(rp_sessao.get((ep, s), 0) / h)
        icc = pr.icc_anova(dict(d))
        return {
            "epochs": len(epochs_sel),
            "estoque_min": min(estoque[e] for e in epochs_sel) if epochs_sel else None,
            "estoque_max": max(estoque[e] for e in epochs_sel) if epochs_sel else None,
            "r_hat": round(tot_op / tot_h, 6) if tot_h else None,
            "p0_hat": round(tot_rp / tot_op, 6) if tot_op else None,
            "icc": icc["icc"],
            "icc_ic": [icc["ic_low"], icc["ic_high"]],
            "delta_p95": round(p95(difs), 6) if difs else None,
            "n_transicoes": len(difs),
        }

    # Corte por estoque, NAO por desfecho. A mediana do estoque parte o corpus
    # em duas metades de maturidade, sem olhar repeats.
    mediana_estoque = sorted(estoque.values())[len(estoque) // 2]
    maduros = [ep for ep in todos_epochs if estoque[ep] >= mediana_estoque]
    jovens = [ep for ep in todos_epochs if estoque[ep] < mediana_estoque]

    print(json.dumps({
        "corte": f"estoque de assinaturas elegiveis >= mediana ({mediana_estoque})",
        "corpus_inteiro": bloco(todos_epochs),
        "metade_madura": bloco(maduros),
        "metade_jovem": bloco(jovens),
        "estoque_por_epoch": {ep.date().isoformat(): estoque[ep] for ep in todos_epochs},
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
