#!/usr/bin/env python3
"""
empates-por-granularidade.py — quanto da ordem o comparador NÃO decide?

O §5.7 mede o teto do canal sob quatro resoluções de `served_at` e conclui que ele vai de
4,86% a 99,43%. Revisão adversarial (GLM, 2026-08-29) levantou a objeção certa:

> truncar CRIA empates, e empates são resolvidos por um desempate **não declarado**
> (ordem de linha do SQLite, estabilidade do `sort` em JS). Sob granularidade grossa,
> fração crescente do resultado passa a ser decidida por essa ordem arbitrária.

E derrubou o contra-argumento óbvio — "os dois braços compartilham a mesma ordem, logo
ela se cancela". Não cancela: `churn` é **diferença simétrica** de dois conjuntos, e
permutar a ordem arbitrária move os dois de forma não correlacionada exatamente na
fronteira do corte, onde o churn nasce e morre.

Este script mede a **exposição** a esse problema, que é o que decide se a objeção morde:
quantos pares de candidatos o comparador `(last_served ASC, salience DESC)` deixa
**indistinguíveis** em cada resolução. Se fosse zero em todas, o comparador seria ordem
total e a objeção morreria.

Não é zero. E o motivo é a própria expressão de salience do canal de cobertura
(`brief.ts:700-703`), que é grossa por construção:

    0,55·importance + 0,10·pain + (0,1 se access_count > 0)

⚠️ **O que este script NÃO faz.** Ele não quantifica quanto dos números 127/281/348 vem
da ordem arbitrária — isso exigiria rerodar as 4×350 com uma terceira coordenada de
desempate explícita e comparar. Fica declarado como não feito. O que ele estabelece é o
tamanho da exposição, e que ela é **mínima justamente na resolução que o paper reporta**.

Uso:
  empates-por-granularidade.py --db nox-mem.db [--json] [--out ...]
"""
import argparse
import json
import sqlite3
import sys

GLOBAL_FRESH_PATTERNS = ["memory/entities/%", "memory/lessons.md"]
FRESH_GLOBAL_MAX_AGE_DAYS = 30
FRESH_MIN_IMP = 0.7
FRESH_MIN_PAIN = 0.7
# Verbatim de `src/api/brief.ts` — a expressão que o ordenador de cobertura usa.
SALIENCE = ("0.55*COALESCE(importance,0.5) + 0.10*COALESCE(pain,0.2) "
            "+ CASE WHEN COALESCE(access_count,0)>0 THEN 0.1 ELSE 0 END")
GRAN = {"seg": 19, "min": 16, "hora": 13, "dia": 10}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--out")
    a = ap.parse_args()

    c = sqlite3.connect(f"file:{a.db}?mode=ro", uri=True)
    pat = " OR ".join(["source_file LIKE ?"] * len(GLOBAL_FRESH_PATTERNS))
    base = f"""
        SELECT id, {SALIENCE} AS sal,
               (SELECT MAX(served_at) FROM brief_log b WHERE b.chunk_id = chunks.id) ls
          FROM chunks
         WHERE julianday('now') - julianday(COALESCE(source_date, created_at)) <= ?
           AND (COALESCE(importance,0) >= ? OR COALESCE(pain,0) >= ?)
           AND ({pat})"""
    args = [FRESH_GLOBAL_MAX_AGE_DAYS, FRESH_MIN_IMP, FRESH_MIN_PAIN,
            *GLOBAL_FRESH_PATTERNS]

    n, nsal = c.execute(
        f"SELECT COUNT(*), COUNT(DISTINCT sal) FROM ({base})", args).fetchone()

    linhas = []
    for rot, k in GRAN.items():
        pares, maior = c.execute(
            f"SELECT COALESCE(SUM(n*(n-1)/2),0), COALESCE(MAX(n),0) FROM "
            f"(SELECT COUNT(*) n FROM ({base}) GROUP BY substr(ls,1,{k}), sal)",
            args).fetchone()
        linhas.append({"granularidade": rot, "pares_indistinguiveis": pares,
                       "maior_bloco_indistinguivel": maior})

    total_pares = n * (n - 1) // 2
    for l in linhas:
        l["pct_dos_pares"] = round(100 * l["pares_indistinguiveis"] / total_pares, 2)

    # ── guardas ────────────────────────────────────────────────────────────
    # (1) coarsening só funde: os pares indistinguíveis não podem DIMINUIR ao
    #     engrossar. Se diminuírem, a chave truncada não é prefixo da original.
    seq = [l["pares_indistinguiveis"] for l in linhas]
    if any(seq[i] > seq[i + 1] for i in range(len(seq) - 1)):
        print(f"⛔ pares indistinguíveis DIMINUEM ao engrossar: {seq}. Truncar deveria "
              f"só fundir — a chave não está sendo truncada como prefixo.", file=sys.stderr)
        return 1
    # (2) pool vazio não é "nenhum empate", é "nada medido".
    if n == 0:
        print("⛔ pool elegível vazio — 'zero empates' aqui seria ausência de medição.",
              file=sys.stderr)
        return 1

    saida = {
        "pool_elegivel": n, "valores_distintos_de_salience": nsal,
        "pares_possiveis": total_pares,
        "expressao_de_salience": SALIENCE,
        "por_granularidade": linhas,
        "nao_medido": "quanto dos tetos 127/281/348 vem da ordem arbitrária — exigiria "
                      "rerodar 4×350 com terceira coordenada de desempate explícita",
    }

    if a.json:
        print(json.dumps(saida, indent=2, ensure_ascii=False))
    else:
        print(f"pool elegível: {n} · valores distintos de salience: {nsal} "
              f"· pares possíveis: {total_pares}")
        print(f"{'gran':6}{'pares indist.':>15}{'% dos pares':>13}{'maior bloco':>13}")
        for l in linhas:
            print(f"{l['granularidade']:6}{l['pares_indistinguiveis']:>15}"
                  f"{l['pct_dos_pares']:>12.2f}%{l['maior_bloco_indistinguivel']:>13}")
        print(f"\n⇒ a exposição a desempate arbitrário é MÍNIMA na resolução de produção "
              f"({linhas[0]['pct_dos_pares']}% dos pares) e cresce {seq[-1]//max(seq[0],1)}× "
              f"até o dia.")

    if a.out:
        json.dump(saida, open(a.out, "w"), indent=2, ensure_ascii=False)
        print(f"→ {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
