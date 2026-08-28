#!/usr/bin/env python3
"""
regime-cobertura.py — explica a "quebra de regime" da diversidade de cobertura.

O §7 listava, como ameaça sem explicação, que `distinct/slots` por dia tem quebra de
regime em 21–22/08. Este script mostra que **não é quebra**: é a assinatura de um canal
alimentado **a lotes**, com janela de elegibilidade de 7 dias.

O que ele mede, e cada medida existe porque a anterior não bastava:

1. **série diária** de slots, distintos e distintos/agente. Sozinha ela só mostra o
   degrau, e degrau admite muitas explicações;
2. **interseção com o dia anterior**. É o teste que separa "carrossel girando" de
   "conjunto congelado": se a interseção é ~100% do dia anterior, nada saiu, e a
   variação é só o que ENTROU;
3. **idade do chunk no instante em que foi servido**. Se o mínimo sobe exatamente
   +1,0 dia por dia, o conjunto servido é literalmente o mesmo envelhecendo;
4. **atribuição das injeções**: para cada dia em que entram chunks novos, de que lote
   de ingestão eles vêm.

⚠️ Dois cuidados que mudam o número:

- **`JOIN chunks` descarta o que foi apagado.** Numa primeira passagem, 20/08 apareceu
  com 33 distintos onde a contagem sobre `brief_log` dava 85: os outros 52 já não
  existem em `chunks`. Contagens de exposição saem de `brief_log`; só as que precisam
  de metadado do chunk fazem JOIN, e essas declaram a perda.
- **`freshMaxAgeDays` é lido do ambiente**, não fixado aqui. Passar `--fresh-max-age`
  diferente do que a produção serve mede outra coisa.

Uso:
  regime-cobertura.py --db nox-mem.db --de 2026-08-10 --ate 2026-08-28 [--json]
"""
import argparse
import json
import sqlite3
import sys


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--de", required=True)
    ap.add_argument("--ate", required=True, help="EXCLUSIVO")
    ap.add_argument("--fresh-max-age", type=float, default=7.0)
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()

    c = sqlite3.connect(f"file:{a.db}?mode=ro", uri=True)

    serie = c.execute("""
        SELECT substr(served_at,1,10) dia, COUNT(*) slots,
               COUNT(DISTINCT chunk_id) distintos, COUNT(DISTINCT brief_id) briefs
          FROM brief_log WHERE served_at >= ? AND served_at < ?
         GROUP BY dia ORDER BY dia""", (a.de, a.ate)).fetchall()

    conj = {}
    for dia, _, _, _ in serie:
        conj[dia] = {r[0] for r in c.execute(
            "SELECT DISTINCT chunk_id FROM brief_log WHERE substr(served_at,1,10)=?", (dia,))}

    dias = [d for d, *_ in serie]
    linhas, injecoes = [], []
    vistos = set()
    for i, (dia, slots, dist, briefs) in enumerate(serie):
        hoje = conj[dia]
        ont = conj[dias[i - 1]] if i else set()
        novos = hoje - vistos
        # idade mínima entre os que ainda existem — o +1,0/dia é a assinatura do congelamento
        mi = c.execute("""SELECT MIN(julianday(b.served_at)-julianday(ch.created_at))
                            FROM brief_log b JOIN chunks ch ON ch.id=b.chunk_id
                           WHERE substr(b.served_at,1,10)=?""", (dia,)).fetchone()[0]
        frescos = c.execute("""SELECT COUNT(DISTINCT b.chunk_id)
                                 FROM brief_log b JOIN chunks ch ON ch.id=b.chunk_id
                                WHERE substr(b.served_at,1,10)=?
                                  AND julianday(b.served_at)-julianday(ch.created_at) <= ?""",
                            (dia, a.fresh_max_age)).fetchone()[0]
        linhas.append({
            "dia": dia, "slots": slots, "distintos": dist, "briefs": briefs,
            "intersecao_com_ontem": len(hoje & ont),
            "pct_de_ontem_retido": round(100 * len(hoje & ont) / len(ont), 1) if ont else None,
            "novos_absolutos": len(novos),
            "frescos_ate_%gd" % a.fresh_max_age: frescos,
            "idade_minima_servida": round(mi, 2) if mi is not None else None,
        })
        if len(novos) >= 10 and i:
            existem = c.execute(
                "SELECT COUNT(*), substr(MIN(created_at),1,16), substr(MAX(created_at),1,16),"
                " COUNT(DISTINCT source_file) FROM chunks WHERE id IN (%s)"
                % ",".join("?" * len(novos)), tuple(novos)).fetchone()
            injecoes.append({
                "dia": dia, "novos": len(novos), "ainda_existem": existem[0],
                "apagados_depois": len(novos) - existem[0],
                "lote_criado_de": existem[1], "lote_criado_ate": existem[2],
                "arquivos_de_origem": existem[3],
            })
        vistos |= hoje

    out = {"db": a.db, "janela": [a.de, a.ate], "fresh_max_age_dias": a.fresh_max_age,
           "serie": linhas, "injecoes": injecoes}

    if a.json:
        print(json.dumps(out, indent=2, ensure_ascii=False))
        return

    print(f"{'dia':<12}{'slots':>7}{'dist':>6}{'∩ontem':>8}{'ret%':>7}"
          f"{'novos':>7}{'frescos':>9}{'idade_min':>11}")
    for l in linhas:
        print(f"{l['dia']:<12}{l['slots']:>7}{l['distintos']:>6}{l['intersecao_com_ontem']:>8}"
              f"{(l['pct_de_ontem_retido'] if l['pct_de_ontem_retido'] is not None else 0):>7}"
              f"{l['novos_absolutos']:>7}{l['frescos_ate_%gd' % a.fresh_max_age]:>9}"
              f"{(l['idade_minima_servida'] or 0):>11}")
    print("\ninjeções (dias com ≥10 chunks nunca servidos antes):")
    for j in injecoes:
        print(f"  {j['dia']}: +{j['novos']} · ainda existem {j['ainda_existem']} "
              f"· apagados depois {j['apagados_depois']} "
              f"· lote {j['lote_criado_de']} → {j['lote_criado_ate']} "
              f"· {j['arquivos_de_origem']} arquivos")
    return 0


if __name__ == "__main__":
    sys.exit(main())
