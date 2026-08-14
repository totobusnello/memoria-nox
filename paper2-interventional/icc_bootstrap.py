#!/usr/bin/env python3
"""IC do ICC por bootstrap de cluster — checa se o IC de Searle está estreito.

⚠️ EXPLORATORIA, NAO PRE-ESPECIFICADA. Não substitui o IC publicado pelo
`pilot_replay`; serve para saber se aquele intervalo pode ser confiado.

POR QUE
O IC de Searle implementado no `pilot_replay.icc_anova` assume clusters
BALANCEADOS. Os nossos não são: 30 epochs com tamanhos de 1 a ~100, dois deles
parciais por censura à direita, m̄ = 55,96. Para desbalanceamento moderado o
intervalo de Searle é conhecido por ser levemente ANTICONSERVADOR — estreito
demais. `SIZING-2026-08-14-v2.md` §5 declara isso e diz que bootstrap resolve.

Este script resolve. Reamostra EPOCHS INTEIROS com reposição (o cluster é a
unidade de reamostragem — reamostrar sessões destruiria justamente a estrutura
que o ICC mede) e recalcula o ICC em cada réplica, com a mesma `icc_anova` do
canônico. O intervalo sai dos percentis.

DETERMINISMO
Sem `random` sem seed. A seed vem de `--seed`, e o default é derivado do
mesmo beacon da extensão 2 — se um terceiro rodar com a mesma seed, obtém os
mesmos números.

    python3 icc_bootstrap.py --episodes ... --verdicts ... --estrato-b-ids ... [-B 5000]
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import random
import sys
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import pilot_replay as pr

# Seed da extensão 2 (round drand 31309420), declarada antes do round existir.
# Usar uma seed JA PUBLICA em vez de inventar uma nova: nada aqui depende de
# aleatoriedade não auditável.
SEED_PADRAO = "fd9b4027dbdf223d689e02a2b33f6bca09b92ced41acebc332b0c8d4efc1aa85"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--episodes", required=True)
    ap.add_argument("--verdicts", required=True)
    ap.add_argument("--estrato-b-ids", required=True)
    ap.add_argument("--replicas", nargs="*", default=[])
    ap.add_argument("-B", "--reamostras", type=int, default=5000)
    ap.add_argument("--seed", default=SEED_PADRAO)
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

    analisaveis = [e for e in eps if e.offset_h >= pr.WASHOUT_H]
    ids = {l.strip() for l in Path(a.estrato_b_ids).read_text().splitlines() if l.strip()}
    estrato_a = [e for e in analisaveis if e.err]
    resto = [e for e in analisaveis if not e.err]
    estrato_b = [e for e in resto if e.id in ids]
    peso = {e.id: 1.0 for e in estrato_a}
    peso.update({e.id: len(resto) / len(estrato_b) for e in estrato_b})
    selecionados = estrato_a + estrato_b

    # ⚠️ `eps`, nao `selecionados`. A duracao de uma sessao e um fato dela, nao
    # da amostra: calcular o span so sobre os episodios sorteados encolhe o
    # denominador da densidade e infla o ICC. Medido: 0,1204 contra os 0,0985
    # do canonico — um IC construido sobre esse ponto nao seria o IC do
    # estimador publicado.
    spans = pr.span_por_sessao(eps)
    repeat_por_sessao: dict[tuple, float] = collections.defaultdict(float)
    sessoes_por_epoch: dict[object, set] = collections.defaultdict(set)
    horas: dict[object, float] = collections.defaultdict(float)
    for (ep, s), h in spans.items():
        sessoes_por_epoch[ep].add(s)
        horas[ep] += h
    for e in selecionados:
        t0 = primeiro_failure.get(e.sig)
        if t0 is None or t0 > e.epoch - limiar or e.estado == "unknown":
            continue
        if e.estado == "failure":
            repeat_por_sessao[(e.epoch, e.sessao)] += peso[e.id]

    # Densidade por sessão, agrupada por epoch — exatamente o insumo do ANOVA
    # no canônico, inclusive a exclusão de epochs com < 2 sessões.
    epochs = sorted(ep for ep in horas if horas[ep] > 0)
    dens: dict[object, list[float]] = collections.defaultdict(list)
    for (ep, s), h in spans.items():
        if ep in epochs and len(sessoes_por_epoch[ep]) >= 2:
            dens[ep].append(repeat_por_sessao.get((ep, s), 0) / h)

    ponto = pr.icc_anova(dict(dens))
    chaves = sorted(dens)
    k = len(chaves)

    # Reamostragem de CLUSTERS INTEIROS. Se um epoch é sorteado duas vezes, ele
    # entra como dois clusters distintos — é isso que preserva a estrutura de
    # variância entre-cluster que o ICC estima.
    rng = random.Random(int(hashlib.sha256(a.seed.encode()).hexdigest()[:16], 16))
    amostras: list[float] = []
    degenerados = 0
    for _ in range(a.reamostras):
        rep: dict[int, list[float]] = {}
        for i in range(k):
            escolhido = chaves[rng.randrange(k)]
            rep[i] = dens[escolhido]
        out = pr.icc_anova(rep)
        if out["ms_within"] is None:
            degenerados += 1
            continue
        amostras.append(out["icc"])

    amostras.sort()
    def pct(p: float) -> float:
        if not amostras:
            return float("nan")
        i = min(len(amostras) - 1, max(0, int(round(p * (len(amostras) - 1)))))
        return round(amostras[i], 6)

    searle = (ponto["ic_low"], ponto["ic_high"])
    boot = (pct(0.025), pct(0.975))
    print(json.dumps({
        "metodo": "bootstrap de cluster (epochs inteiros, com reposicao)",
        "reamostras": a.reamostras,
        "reamostras_degeneradas": degenerados,
        "seed": a.seed,
        "clusters": k,
        "icc_ponto": ponto["icc"],
        "ic_searle": list(searle),
        "ic_bootstrap_percentil": list(boot),
        "largura_searle": round(searle[1] - searle[0], 6) if None not in searle else None,
        "largura_bootstrap": round(boot[1] - boot[0], 6),
        "razao_larguras_boot_sobre_searle": (
            round((boot[1] - boot[0]) / (searle[1] - searle[0]), 3)
            if None not in searle and searle[1] > searle[0] else None),
        "fracao_reamostras_com_icc_zero": round(
            sum(1 for x in amostras if x == 0.0) / len(amostras), 4) if amostras else None,
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
