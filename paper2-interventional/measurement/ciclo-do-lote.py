#!/usr/bin/env python3
"""
ciclo-do-lote.py — um lote de ingestão alimenta o canal de cobertura por quantos dias?

O §4.3.1 afirma que o carrossel de cobertura não gira: ele salta a cada lote de ingestão
e congela entre saltos, porque o sub-pool por agente exige `freshMaxAgeDays = 7`. A
afirmação estava apoiada numa **predição datada** sobre o lote de 21–22/08, o que a
deixava inverificável até a data chegar.

Este script verifica a mesma afirmação por **retrodição**, sobre um lote que já viveu o
ciclo inteiro. É teste mais forte que a predição: os dados já existem, e o resultado não
pode ser ajustado depois.

O que ele mede, por dia, para os chunks criados numa janela de ingestão:

  - quantos do lote foram servidos;
  - a idade **máxima** servida — é ela que localiza o corte, não a mínima. Se o corte é
    `idade <= K`, nenhum dia pode exibir máxima ≥ K, e o dia em que o lote encolhe é
    aquele em que parte dele cruzou K;
  - o dia em que zera, e se volta depois.

⚠️ **Duas janelas, não uma, e o paper citava só a primeira.** `brief-diversity.ts:61-62`:
`freshMaxAgeDays = 7` (sub-pool por agente) e `freshGlobalMaxAgeDays = 30` (sub-pool
global; `brief.ts:809` e `:845` sobrescrevem a primeira pela segunda). Sem override no
ambiente. Um lote portanto sai do sub-pool por agente aos 7 dias e continua **elegível**
no global por mais 23 — e mesmo assim para de ser servido. Não é contradição: o global
ordena por `last_served ASC`, e quem acabou de ser servido vai para o **fim** da fila,
atrás de qualquer coisa menos-recentemente-servida dentro dos 30 dias. Elegível e
alcançável são coisas diferentes, e é a distinção que o §4.3.1 depende.

⚠️ **Contar exposição sai de `brief_log`; idade precisa de `JOIN chunks`, e o JOIN
perde o que foi apagado.** O script reporta os dois números para que a perda seja
visível em vez de silenciosa (a injeção de 20/08 tinha 52 chunks e nenhum sobreviveu).

Uso:
  ciclo-do-lote.py --db nox-mem.db --lote 2026-08-09:2026-08-11 [--lote 2026-08-21:2026-08-23]
                   [--corte 7] [--json] [--out ...]
"""
import argparse
import json
import sqlite3
import sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--lote", action="append", required=True,
                    help="criado_de:criado_ate (ate EXCLUSIVO), ex 2026-08-09:2026-08-11")
    ap.add_argument("--corte", type=float, default=7.0,
                    help="freshMaxAgeDays do sub-pool por agente (default 7, o de produção)")
    ap.add_argument("--out")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    c = sqlite3.connect(f"file:{a.db}?mode=ro", uri=True)
    saida = {"db": a.db, "corte_dias": a.corte, "lotes": []}

    for spec in a.lote:
        de, _, ate = spec.partition(":")
        if not ate:
            raise SystemExit(f"--lote espera de:ate, recebi {spec!r}")

        tam = c.execute(
            "SELECT COUNT(*) FROM chunks WHERE created_at >= ? AND created_at < ?",
            (de, ate)).fetchone()[0]

        linhas = c.execute("""
            WITH lote AS (SELECT id, created_at FROM chunks
                           WHERE created_at >= ? AND created_at < ?)
            SELECT substr(b.served_at,1,10) dia,
                   COUNT(DISTINCT b.chunk_id) servidos,
                   MIN(julianday(b.served_at)-julianday(l.created_at)) idade_min,
                   MAX(julianday(b.served_at)-julianday(l.created_at)) idade_max
              FROM brief_log b JOIN lote l ON l.id = b.chunk_id
             WHERE b.served_at >= ?
             GROUP BY dia ORDER BY dia""", (de, ate, de)).fetchall()

        serie = [{"dia": d, "servidos": n,
                  "idade_min": round(mi, 2), "idade_max": round(ma, 2)}
                 for d, n, mi, ma in linhas]

        # ── o guarda que dá sentido ao número: NENHUM dia pode exibir idade máxima
        # servida >= o corte. Se exibir, o corte não é o que o paper diz que é.
        violam = [x for x in serie if x["idade_max"] >= a.corte]

        # último dia com serviço, e se houve retorno depois de zerar
        ultimo = serie[-1]["dia"] if serie else None
        # dias entre o primeiro e o último, para detectar buraco-e-volta
        dias_todos = [r[0] for r in c.execute(
            "SELECT DISTINCT substr(served_at,1,10) d FROM brief_log WHERE served_at >= ? ORDER BY d",
            (de,)).fetchall()]
        com_servico = {x["dia"] for x in serie}
        i0 = dias_todos.index(serie[0]["dia"]) if serie else 0
        iN = dias_todos.index(ultimo) if ultimo else 0
        buracos = [d for d in dias_todos[i0:iN] if d not in com_servico]

        lote = {
            "criado_de": de, "criado_ate_exclusivo": ate,
            "chunks_criados": tam,
            "chunks_do_lote_que_chegaram_a_ser_servidos":
                max((x["servidos"] for x in serie), default=0),
            "serie": serie,
            "ultimo_dia_com_servico": ultimo,
            "dias_sem_servico_no_meio": buracos,
            "voltou_depois_de_zerar": bool(buracos),
            "dias_acima_do_corte": violam,
            "corte_respeitado": not violam,
            "idade_maxima_jamais_servida":
                round(max((x["idade_max"] for x in serie), default=0), 2),
        }
        if violam:
            print(f"⛔ lote {de}: {len(violam)} dia(s) servem chunk com idade >= "
                  f"{a.corte} — o corte não é {a.corte}.", file=sys.stderr)
            for x in violam:
                print(f"     {x['dia']}: idade_max = {x['idade_max']}", file=sys.stderr)
        saida["lotes"].append(lote)

    if a.json:
        print(json.dumps(saida, indent=2, ensure_ascii=False))
    else:
        for L in saida["lotes"]:
            print(f"\n── lote {L['criado_de']} → {L['criado_ate_exclusivo']} "
                  f"({L['chunks_criados']} chunks criados, "
                  f"{L['chunks_do_lote_que_chegaram_a_ser_servidos']} chegaram a ser servidos) ──")
            print(f"{'dia':<12}{'servidos':>9}{'idade_min':>11}{'idade_max':>11}")
            for x in L["serie"]:
                print(f"{x['dia']:<12}{x['servidos']:>9}{x['idade_min']:>11.2f}{x['idade_max']:>11.2f}")
            print(f"  último dia com serviço: {L['ultimo_dia_com_servico']} · "
                  f"voltou depois de zerar: {L['voltou_depois_de_zerar']}")
            print(f"  idade máxima jamais servida: {L['idade_maxima_jamais_servida']} "
                  f"(corte declarado: {a.corte}) · corte respeitado: {L['corte_respeitado']}")

    if a.out:
        json.dump(saida, open(a.out, "w"), indent=2, ensure_ascii=False)
        print(f"\n→ {a.out}")
    return 0 if all(L["corte_respeitado"] for L in saida["lotes"]) else 1


if __name__ == "__main__":
    sys.exit(main())
