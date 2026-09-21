#!/usr/bin/env python3
"""Controles de instrumento pré-comprometidos — SPEC-ANALISE §5, janela COMPLETA.

A spec mediu estes em 2026-09-10, com o ensaio **ainda a correr**: o controlo
positivo passava 6/6 e o dual negativo 3/3 sobre uma janela parcial. Este
ficheiro re-mede sobre os 20 epochs realizados, porque um controlo medido a meio
não cobre o que veio depois.

Os três, como pré-comprometidos:

  (1) POSITIVO — epoch de tratamento servido tem `mexeu > 0`. Se algum desse 0,
      o nulo seria do INSTRUMENTO e não do efeito.

  (2) DUAL NEGATIVO — epoch de controlo tem `sem_ids == n`. ⚠️ O enunciado
      óbvio (`mexeu == 0` no controlo) é INVÁLIDO: em `w=0` os campos `ids_*`
      nem existem, logo `mexeu == 0` é indistinguível de «o campo nunca foi
      escrito» — regra 9 do CLAUDE.md, predicado que exige o dado que falta.

  (3) ESPECIFICIDADE por designação-sham — 19 chunks NÃO designados, mesmo `w`.

⚠️ SEMÂNTICA DECLARADA: `mexeu` compara `ids_tratado` com `ids_controle` por
**PERTENCIMENTO** (`set`), nunca por lista. A comparação de lista mistura
reordenação com entrada/saída e no epoch `09-08` dá 48 contra 20.
"""
from __future__ import annotations
import argparse, collections, datetime as dt, hashlib, json, random
from pathlib import Path

JANELA = ("2026-09-01", "2026-09-20")
OFFSET_H = 9


def epoch_de(ts: str) -> str:
    d = dt.datetime.fromisoformat(ts.replace("Z", "+00:00"))
    return (d - dt.timedelta(hours=OFFSET_H)).strftime("%Y-%m-%d")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--serving", required=True)
    ap.add_argument("--designation", required=True)
    ap.add_argument("--assignment", default=str(Path(__file__).parent / "ASSIGNMENT-SERVING.json"))
    ap.add_argument("--seed-prefix", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()

    des = json.loads(Path(a.designation).read_text())
    designados = set(des["designados"].values())
    arm = {e["epoch_inicio"]: (e["arm"], float(e["w"]))
           for e in json.loads(Path(a.assignment).read_text())["epochs"]}

    n = collections.Counter(); mexeu = collections.Counter()
    sem_ids = collections.Counter(); universo: set[str] = set()
    # para o sham: por brief, o conjunto de controlo e o de tratamento
    pares: list[tuple[str, frozenset, frozenset]] = []

    for linha in Path(a.serving).open():
        o = json.loads(linha)
        ep = epoch_de(o["ts"])
        if not (JANELA[0] <= ep <= JANELA[1]) or ep not in arm:
            continue
        n[ep] += 1
        ic, it = o.get("ids_controle"), o.get("ids_tratado")
        if ic is None or it is None:
            sem_ids[ep] += 1
            continue
        universo |= set(ic) | set(it)
        sc, st = frozenset(ic), frozenset(it)
        if sc != st:                       # PERTENCIMENTO, nunca lista
            mexeu[ep] += 1
        pares.append((ep, sc, st))

    eps = sorted(n)
    # ── (1) POSITIVO ────────────────────────────────────────────────────────
    trat = sorted({e for e in eps if arm[e][0] == "treatment" and n[e]})
    pos = {e: dict(n=n[e], mexeu=mexeu[e], taxa=round(mexeu[e] / n[e], 4), w=arm[e][1])
           for e in trat}
    pos_passa = all(v["mexeu"] > 0 for v in pos.values())

    # ── (2) DUAL NEGATIVO ───────────────────────────────────────────────────
    ctrl = sorted({e for e in eps if arm[e][0] == "control" and n[e]})
    neg = {e: dict(n=n[e], sem_ids=sem_ids[e], igual=sem_ids[e] == n[e]) for e in ctrl}
    neg_passa = all(v["igual"] for v in neg.values())

    nao_designados = sorted(universo - designados)
    # ── (3) ESPECIFICIDADE: NÃO EXECUTÁVEL sobre este log ───────────────────
    # 🔴 A primeira versão deste ficheiro contou quantos briefs têm um chunk
    # SHAM presente em `ids_tratado`, e comparou com os designados. Deu
    # "FALHA" (real 2.069 contra mediana sham 5.832) e a FALHA era do teste,
    # não do estudo.
    #
    # A própria SPEC §5 avisa, na 2.ª linha da tabela de candidatos:
    #     «condicionar em "designado presente no conjunto SERVIDO" é
    #      TAUTOLÓGICO: servido é `ids_tratado`, que é PÓS-DOSE»
    # Contar presença num conjunto produzido pela dose real não mede
    # especificidade — mede quão COMUNS são os chunks. O universo tem 141 ids e
    # os não-designados incluem os que entram em quase todo brief, enquanto os
    # designados são um por grupo de assinatura, logo mais raros. O sinal é de
    # frequência, e teria ido ao paper como alarme sobre o instrumento.
    #
    # O sham pré-comprometido é um **REPLAY**: re-executar o mecanismo de dose
    # com 19 chunks não designados e o mesmo `w`, e comparar o CHURN que ele
    # produz. Isso exige correr o código de serving, não ler o log dele — e
    # nenhuma contagem sobre `p2-serving.ndjson` o substitui, porque o log só
    # contém o resultado da designação que de facto correu.
    especificidade = dict(
        enunciado="replay com designacao-sham: 19 chunks NAO designados, mesmo w",
        executado=False,
        porque="exige RE-EXECUTAR o mecanismo de dose, nao ler o log dele. O log "
               "so' contem o resultado da designacao que correu.",
        tentativa_invalida="contar presenca de chunks sham em ids_tratado deu real=2069 "
                           "contra mediana sham=5832 e lia-se como FALHA do instrumento; "
                           "e' o candidato que a SPEC §5 ja' declara TAUTOLOGICO (servido "
                           "e' pos-dose). Mede frequencia de chunk, nao especificidade.",
        universo_de_ids=len(universo), nao_designados=len(nao_designados),
        briefs_com_ids=len(pares),
    )

    out = dict(
        gerado_em=dt.datetime.now(dt.timezone.utc).isoformat(),
        fonte="SPEC-ANALISE-2026-09-10 §5, re-medido sobre a janela COMPLETA",
        nota_medicao_anterior="a spec mediu 6/6 e 3/3 em 10/09 com o ensaio ainda a correr; "
                              "um controlo medido a meio nao cobre o que veio depois",
        semantica_mexeu="pertencimento (set), NUNCA lista — lista mistura reordenacao com "
                        "entrada/saida e em 09-08 da 48 contra 20",
        controle_positivo=dict(
            enunciado="epoch de tratamento servido tem mexeu > 0",
            passa=pos_passa, epochs=len(pos), por_epoch=pos,
            interpretacao="se algum desse 0, o nulo seria do INSTRUMENTO, nao do efeito"),
        controle_negativo_dual=dict(
            enunciado="epoch de controlo tem sem_ids == n (o dual-compute nao corre em w=0)",
            porque_nao_o_obvio="'mexeu == 0' e' indistinguivel de 'o campo nunca foi "
                               "escrito' — regra 9: predicado que exige o dado que falta",
            passa=neg_passa, epochs=len(neg), por_epoch=neg),
        especificidade_sham=especificidade,
        seed_prefix=a.seed_prefix,
    )
    Path(a.out).write_text(json.dumps(out, indent=2, ensure_ascii=False))

    print(f"(1) POSITIVO  {'✅ PASSA' if pos_passa else '🔴 FALHA'}  {len(pos)} epochs de tratamento")
    for e, v in pos.items():
        print(f"      {e}  w={v['w']:4}  mexeu {v['mexeu']:4}/{v['n']:<4} = {100*v['taxa']:5.2f}%")
    print(f"(2) DUAL NEG  {'✅ PASSA' if neg_passa else '🔴 FALHA'}  {len(neg)} epochs de controlo")
    for e, v in neg.items():
        print(f"      {e}  sem_ids {v['sem_ids']}/{v['n']}  {'ok' if v['igual'] else '🔴'}")
    print("(3) SHAM      ⏭  NAO EXECUTADO — exige replay do mecanismo, nao leitura do log")
    print("      (a tentativa por contagem e' o candidato que a SPEC §5 declara TAUTOLOGICO)")
    print(f"→ {a.out}")
    return 0 if (pos_passa and neg_passa) else 1


if __name__ == "__main__":
    raise SystemExit(main())
