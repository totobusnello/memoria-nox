#!/usr/bin/env python3
"""
exposicao-por-coorte.py — o 83,78% é artefato de chunks jovens demais para julgar?

Objeção de revisão adversarial (Kimi, 2026-08-29), e ela era a única das cinco cuja
**direção era desconhecida**:

> a taxa é incondicional: um chunk criado na semana 11 teve 7 dias de oportunidade de
> exposição; um da semana 1 teve 84. Os dois entram iguais no denominador de "nunca
> exposto". Se o corpus cresceu rápido dentro da janela, uma fatia desconhecida dos
> 56.288 é "jovem demais para julgar", não "recusado".

A objeção é correta em forma. Este script mede o tamanho dela, estratificando por idade
— e como toda medição de direção desconhecida, tinha de ser feita antes de qualquer
reescrita, não depois.

⚠️ **Uma segunda perna da mesma objeção NÃO se resolve aqui**, e fica declarada: dos
nunca-expostos, só uma fração passa o piso de relevância do próprio sistema. Isso não é
censura temporal, é composição do corpus, e a resposta é reportar o número
condicionado ao piso **ao lado** da manchete — não estratificar por idade.

⚠️ **E uma terceira perna é incontável por construção:** chunks criados e apagados dentro
da janela, sem nunca terem sido expostos, não aparecem em população nenhuma — o
complemento é sobre o corpus *vivo*. Que o inverso exista (152 servidos e depois
apagados) prova que há churn na janela. A direção desse viés é desconhecida e não
mensurável com os dados que temos.

Uso:
  exposicao-por-coorte.py --db nox-mem.db [--piso-imp 0.7 --piso-pain 0.7] [--json] [--out ...]
"""
import argparse
import json
import sqlite3
import sys

# ⚠️ "Exposto" TEM de ser a mesma definição da manchete do §4.1: a UNIÃO das duas
# superfícies — brief (`brief_log`) e busca (`access_count > 0`, incrementado só em
# `src/search.ts:396`). Uma primeira versão deste script contou só o brief e devolveu
# 97,57% onde a manchete diz 83,78%; os dois números são corretos e medem coisas
# diferentes, e compará-los seria o defeito de universos misturados que este paper
# já cometeu uma vez no §4.1.
EXPOSTO = ("(id IN (SELECT chunk_id FROM brief_log) OR COALESCE(access_count,0) > 0)")

CORTES = [(7, "a) < 1 semana"), (28, "b) 1-4 semanas"), (84, "c) 4-12 semanas")]
ULTIMO = "d) > 12 semanas"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--piso-imp", type=float, default=0.7)
    ap.add_argument("--piso-pain", type=float, default=0.7)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--out")
    a = ap.parse_args()

    c = sqlite3.connect(f"file:{a.db}?mode=ro", uri=True)
    idade = "julianday('now') - julianday(COALESCE(source_date, created_at))"
    caso = " ".join(f"WHEN {idade} < {d} THEN '{r}'" for d, r in CORTES)

    linhas = [
        {"coorte": r[0], "chunks": r[1], "nunca_expostos": r[2],
         "pct_nunca_exposto": round(100 * r[2] / r[1], 2) if r[1] else None}
        for r in c.execute(f"""
            SELECT CASE {caso} ELSE '{ULTIMO}' END coorte, COUNT(*),
                   SUM(CASE WHEN {EXPOSTO} THEN 0 ELSE 1 END)
              FROM chunks GROUP BY coorte ORDER BY coorte""").fetchall()]

    corpus = sum(l["chunks"] for l in linhas)
    nunca = sum(l["nunca_expostos"] for l in linhas)
    jovens = sum(l["chunks"] for l in linhas if l["coorte"] < "c)")
    maduro = next((l for l in linhas if l["coorte"].startswith("d")), None)

    piso_total, piso_nunca = c.execute(
        f"SELECT COUNT(*), SUM(CASE WHEN {EXPOSTO} THEN 0 ELSE 1 END) "
        f"FROM chunks WHERE COALESCE(importance,0) >= ? OR COALESCE(pain,0) >= ?",
        (a.piso_imp, a.piso_pain)).fetchone()

    saida = {
        "corpus": corpus,
        "nunca_expostos": nunca,
        "pct_agregado": round(100 * nunca / corpus, 2),
        "por_coorte": linhas,
        "chunks_com_menos_de_4_semanas": jovens,
        "pct_do_corpus_que_e_jovem": round(100 * jovens / corpus, 2),
        "coorte_madura_pct_nunca_exposto": maduro["pct_nunca_exposto"] if maduro else None,
        "condicionado_ao_piso": {
            "piso": f"importance >= {a.piso_imp} OR pain >= {a.piso_pain}",
            "chunks": piso_total, "nunca_expostos": piso_nunca,
            "pct": round(100 * piso_nunca / piso_total, 2) if piso_total else None,
        },
    }

    # ── guardas ────────────────────────────────────────────────────────────
    # (1) coorte vazia torna o percentual dela indefinido e a leitura, enganosa.
    vazias = [l["coorte"] for l in linhas if l["chunks"] == 0]
    if vazias:
        print(f"⛔ coorte(s) sem chunk: {vazias} — percentual indefinido, e reportar "
              f"'0% nunca exposto' ali seria ausência de dado lida como resultado.",
              file=sys.stderr)
        return 1
    # (2) o agregado tem de ser a média ponderada das coortes; se não for, o `CASE`
    #     não particiona (algum chunk caiu em duas ou em nenhuma).
    if abs(sum(l["nunca_expostos"] for l in linhas) - nunca) > 0:
        print("⛔ as coortes não particionam o corpus.", file=sys.stderr)
        return 1

    if a.json:
        print(json.dumps(saida, indent=2, ensure_ascii=False))
    else:
        print(f"corpus {corpus} · nunca expostos {nunca} ({saida['pct_agregado']}%)\n")
        print(f"{'coorte':<18}{'chunks':>8}{'nunca':>8}{'%':>9}")
        for l in linhas:
            print(f"{l['coorte']:<18}{l['chunks']:>8}{l['nunca_expostos']:>8}"
                  f"{l['pct_nunca_exposto']:>8.2f}%")
        print(f"\njovens (< 4 semanas): {jovens} = {saida['pct_do_corpus_que_e_jovem']}% "
              f"do corpus")
        if maduro and maduro["pct_nunca_exposto"] > saida["pct_agregado"]:
            print(f"⇒ a coorte com oportunidade MÁXIMA é a MAIS não-exposta "
                  f"({maduro['pct_nunca_exposto']}% contra {saida['pct_agregado']}% "
                  f"agregado): censura por idade não infla a manchete — desinfla.")
        p = saida["condicionado_ao_piso"]
        print(f"\ncondicionado ao piso de relevância do sistema: {p['nunca_expostos']} de "
              f"{p['chunks']} = {p['pct']}% nunca expostos")

    if a.out:
        json.dump(saida, open(a.out, "w"), indent=2, ensure_ascii=False)
        print(f"→ {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
