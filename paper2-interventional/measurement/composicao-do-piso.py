#!/usr/bin/env python3
"""
composicao-do-piso.py — o que são, de fato, os 10.008 elegíveis e nunca expostos?

O §4.1 promoveu a co-manchete "dos 13.388 que passam o piso de relevância do próprio
sistema, 10.008 = 74,75% nunca foram expostos". Um número dessa força circula sozinho,
e a leitura tentadora — "dez mil lições preciosas invisíveis" — é falsa. Este script
mede a composição, para que a qualificação viaje colada à manchete.

⚠️ **Ele existe porque a versão anterior da qualificação estava em prosa, sem artefato,
e atribuía à população errada.** O texto dizia "8.928 são fragmentos de sessão de **205**
caracteres em média". Os 8.928 estão certos; os 205 são a média de **todos os 14.456
`distilled` do corpus**, não a dos 8.928, que é **231,9**. A query de 27/08 foi ad-hoc,
não deixou artefato, e a frase nomeou um subconjunto enquanto o número media o conjunto.
Diferença de 13% que não move a conclusão — fragmento de 232 caracteres continua sendo
fragmento — mas a atribuição estava errada e só apareceu porque o número foi recomputado.

⚠️ **`chunk_type`, não `memory_type`.** A coluna `memory_type` é NULL em todo o corpus;
o tipo vive em `chunk_type`. Filtrar pela primeira devolve zero linhas sem erro.

Uso:
  composicao-do-piso.py --db nox-mem.db [--piso-imp 0.7 --piso-pain 0.7] [--json] [--out ...]
"""
import argparse
import json
import sqlite3
import sys

EXPOSTO = "(id IN (SELECT chunk_id FROM brief_log) OR COALESCE(access_count,0) > 0)"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--piso-imp", type=float, default=0.7)
    ap.add_argument("--piso-pain", type=float, default=0.7)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--out")
    a = ap.parse_args()

    c = sqlite3.connect(f"file:{a.db}?mode=ro", uri=True)
    onde = (f"(COALESCE(importance,0) >= {a.piso_imp} OR COALESCE(pain,0) >= {a.piso_pain}) "
            f"AND NOT {EXPOSTO}")

    total = c.execute(f"SELECT COUNT(*) FROM chunks WHERE {onde}").fetchone()[0]
    tipos = [
        {"tipo": t, "chunks": n, "pct_do_piso": round(100 * n / total, 1),
         "comprimento_medio": round(m, 1)}
        for t, n, m in c.execute(
            f"SELECT COALESCE(chunk_type,'(nulo)'), COUNT(*), AVG(LENGTH(chunk_text)) "
            f"FROM chunks WHERE {onde} GROUP BY 1 ORDER BY 2 DESC")]

    dom = tipos[0]
    # o contraste que revelou o erro de atribuição: a média do TIPO INTEIRO no corpus
    # contra a média do subconjunto que a manchete nomeia.
    n_corpus, m_corpus = c.execute(
        "SELECT COUNT(*), AVG(LENGTH(chunk_text)) FROM chunks WHERE chunk_type = ?",
        (dom["tipo"],)).fetchone()

    saida = {
        "elegiveis_nunca_expostos": total,
        "por_tipo": tipos,
        "tipo_dominante": dom,
        "contraste_de_populacao": {
            "nota": "a média do tipo inteiro NÃO é a média do subconjunto da manchete",
            "tipo": dom["tipo"],
            "no_corpus_inteiro": {"chunks": n_corpus, "comprimento_medio": round(m_corpus, 1)},
            "no_subconjunto_da_manchete": {"chunks": dom["chunks"],
                                           "comprimento_medio": dom["comprimento_medio"]},
        },
    }

    # ── guardas ────────────────────────────────────────────────────────────
    # (1) `memory_type` é NULL em todo o corpus e filtrar por ela devolve zero sem
    #     erro. Se este script um dia devolver zero, é isso — não "não há elegíveis".
    if total == 0:
        print("⛔ zero elegíveis nunca expostos — antes de reportar isso como achado, "
              "conferir se o filtro de tipo está na coluna certa (`chunk_type`).",
              file=sys.stderr)
        return 1
    # (2) a qualificação só funciona se UM tipo dominar. Se o dominante cair abaixo
    #     de metade, "o achado não é dez mil lições" deixa de estar demonstrado.
    if dom["pct_do_piso"] < 50:
        print(f"⛔ o tipo dominante é só {dom['pct_do_piso']}% do piso — a qualificação "
              f"do §4.1 não se sustenta mais sobre um único tipo.", file=sys.stderr)
        return 1

    if a.json:
        print(json.dumps(saida, indent=2, ensure_ascii=False))
    else:
        print(f"elegíveis e nunca expostos: {total}\n")
        print(f"{'tipo':<14}{'chunks':>8}{'% do piso':>11}{'compr. médio':>14}")
        for t in tipos[:6]:
            print(f"{t['tipo']:<14}{t['chunks']:>8}{t['pct_do_piso']:>10.1f}%"
                  f"{t['comprimento_medio']:>14.1f}")
        cc = saida["contraste_de_populacao"]
        print(f"\n⚠️ `{dom['tipo']}` no corpus inteiro: {cc['no_corpus_inteiro']['chunks']} "
              f"chunks, {cc['no_corpus_inteiro']['comprimento_medio']} caracteres — "
              f"contra {dom['comprimento_medio']} no subconjunto da manchete. Citar a "
              f"primeira como se fosse a segunda foi o erro de 27/08.")

    if a.out:
        json.dump(saida, open(a.out, "w"), indent=2, ensure_ascii=False)
        print(f"→ {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
