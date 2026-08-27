#!/usr/bin/env python3
"""
superficie-de-exposicao.py — o que uma memória de agente em produção REALMENTE entrega.

Mede as duas superfícies pelas quais um chunk pode chegar ao agente, e quanto do
corpus nunca chegou por nenhuma. É a medição da manchete do reframe de 27/08: o
paper deixa de perguntar "a memória interventiva funciona?" e passa a responder
"o que o sistema entrega, e por que uma intervenção plausível não muda isso".

─── As duas superfícies, e por que a contabilidade é exata ──────────────────

1. **Brief proativo** — `brief_log`. Cobre a vida INTEIRA do `/api/brief` (F1 subiu
   em 2026-06-04) e **não tem poda** no fonte: a única `DELETE FROM brief_log` do
   repo está num teste. Logo "nunca apareceu no `brief_log`" == "nunca foi servido
   no brief", sem qualificação.

2. **Busca** — `chunks.access_count`, incrementado em `src/search.ts:396`
   (`access_count = access_count + 1` nos resultados). O brief **nunca** escreve
   nessa coluna: `src/api/brief.ts` só a lê. Logo `access_count > 0` == "retornado
   por busca ao menos uma vez, desde sempre".

Como as duas cobrem desde o início, a UNIÃO é uma contagem exata de
"já-exposto-alguma-vez", e o complemento é exato. Nenhum dos dois números é bound.

─── O que este script NÃO pode responder, e a razão é instrumental ──────────

⚠️ Uma comparação brief-vs-busca **dentro de uma janela** não é possível hoje.
`search_telemetry.top_chunk_ids` — o único instrumento com timestamp por chunk —
foi populado 6.150 vezes em maio/2026 e **zero** de 2026-06-04 em diante; parou em
2026-05-19 14:47:04. Instrumentação que existe e está desligada.

O que resta para janela é `last_accessed_at`, que guarda só o ÚLTIMO acesso: um
chunk buscado em maio e nunca mais fica de fora. Isso é **limite inferior** da
exposição por busca, e o script o rotula como tal.

⚠️ E o limite protege a direção CHATA. Exposição ≥ X ⇒ invisibilidade ≤ Y: o bound
sustenta "no máximo tanto é invisível", não "no mínimo tanto é invisível". Para a
alegação de invisibilidade ALTA a contagem válida é a **cumulativa**, que é exata.
Escrever a janelada como se sustentasse a mesma coisa foi um erro que eu quase
cometi em 27/08 — e a comparação de entities curadas INVERTE quando escopada:
cumulativa dá busca 617 × brief 245; na janela comum dá brief 245 × busca ≥ 151.

Uso:
  ./superficie-de-exposicao.py --db <nox-mem.db> [--janela-inicio 2026-06-04]
                               [--out saida.json] [--assert-json esperado.json]
"""
import argparse
import json
import sqlite3
import subprocess
import sys


def um(c, q, *a):
    return c.execute(q, a).fetchone()[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--janela-inicio", default="2026-06-04",
                    help="início da janela comum; default = subida do /api/brief (F1)")
    ap.add_argument("--fim", default=None,
                    help="fim EXCLUSIVO da janela de 7 dias; default = hoje 00:00Z. "
                         "Sem isto a janela é viva e os números envelhecem para falsos.")
    ap.add_argument("--piso-imp", type=float, default=0.7)
    ap.add_argument("--piso-pain", type=float, default=0.7)
    ap.add_argument("--out")
    ap.add_argument("--assert-json")
    a = ap.parse_args()

    c = sqlite3.connect(f"file:{a.db}?mode=ro", uri=True)
    ini = a.janela_inicio

    # ⚠️ Janela FECHADA nos dois extremos. Com `date('now','-7 day')` os números são
    # série viva: numa conferência de 27/08 `briefs_7d` passou de 5.199 para 5.206 e
    # `search_telemetry` de 13.009 para 13.010 em minutos — e a nota que os citasse
    # envelheceria para falsa em horas. Já aconteceu nesta linha de trabalho.
    fim = a.fim or subprocess.run(["date", "-u", "+%Y-%m-%d"],
                                  capture_output=True, text=True).stdout.strip()
    d7ini = subprocess.run(["date", "-u", "-d", f"{fim} -7 day", "+%Y-%m-%d"],
                           capture_output=True, text=True).stdout.strip()

    corpus = um(c, "SELECT COUNT(*) FROM chunks")

    # ─── cumulativo: exato nas duas pontas ─────────────────────────────────
    brief_ids = um(c, "SELECT COUNT(DISTINCT chunk_id) FROM brief_log")
    busca = um(c, "SELECT COUNT(*) FROM chunks WHERE COALESCE(access_count,0) > 0")
    uniao = um(c, """SELECT COUNT(*) FROM (
                       SELECT DISTINCT chunk_id id FROM brief_log
                       UNION SELECT id FROM chunks WHERE COALESCE(access_count,0) > 0)""")
    nenhuma = um(c, """SELECT COUNT(*) FROM chunks
                        WHERE id NOT IN (SELECT DISTINCT chunk_id FROM brief_log)
                          AND COALESCE(access_count,0) = 0""")
    # `brief_ids` conta ids que podem já ter sido APAGADOS do corpus. Sem esta
    # linha, `corpus - uniao != nenhuma` e a diferença parece erro de query.
    servidos_e_apagados = um(c, """SELECT COUNT(*) FROM (
        SELECT DISTINCT chunk_id id FROM brief_log
         WHERE chunk_id NOT IN (SELECT id FROM chunks))""")

    invisiveis_elegiveis = um(c, """SELECT COUNT(*) FROM chunks
        WHERE id NOT IN (SELECT DISTINCT chunk_id FROM brief_log)
          AND COALESCE(access_count,0) = 0
          AND (COALESCE(importance,0) >= ? OR COALESCE(pain,0) >= ?)""",
                              a.piso_imp, a.piso_pain)
    por_tipo_invisivel = c.execute("""SELECT COALESCE(chunk_type,'(null)'), COUNT(*)
        FROM chunks
       WHERE id NOT IN (SELECT DISTINCT chunk_id FROM brief_log)
         AND COALESCE(access_count,0) = 0
         AND (COALESCE(importance,0) >= ? OR COALESCE(pain,0) >= ?)
       GROUP BY 1 ORDER BY 2 DESC""", (a.piso_imp, a.piso_pain)).fetchall()

    # exposição por tipo: o gradiente de curadoria é o achado, não o número bruto
    tipos = c.execute("""
        SELECT COALESCE(chunk_type,'(null)') tipo, COUNT(*) total,
               SUM(CASE WHEN id IN (SELECT DISTINCT chunk_id FROM brief_log)
                          OR COALESCE(access_count,0) > 0 THEN 1 ELSE 0 END) exposto
          FROM chunks GROUP BY tipo HAVING total >= 10 ORDER BY total DESC""").fetchall()

    # ─── concentração da superfície do brief (exata) ───────────────────────
    slots = um(c, "SELECT COUNT(*) FROM brief_log")
    span = c.execute("SELECT MIN(served_at), MAX(served_at) FROM brief_log").fetchone()
    d7 = c.execute("""SELECT chunk_id, COUNT(*) n FROM brief_log
                       WHERE served_at >= ? AND served_at < ?
                       GROUP BY chunk_id ORDER BY n DESC""", (d7ini, fim)).fetchall()
    tot7 = sum(n for _, n in d7)
    nb7 = um(c, """SELECT COUNT(DISTINCT brief_id) FROM brief_log
                    WHERE served_at >= ? AND served_at < ? AND brief_id IS NOT NULL""",
             d7ini, fim)
    em_todos = c.execute("""SELECT COUNT(*) FROM (
        SELECT chunk_id FROM brief_log
         WHERE served_at >= ? AND served_at < ? AND brief_id IS NOT NULL
         GROUP BY chunk_id HAVING COUNT(DISTINCT brief_id) = ?)""",
                         (d7ini, fim, nb7)).fetchone()[0]

    # ─── janela comum: brief exato x busca LIMITE INFERIOR ────────────────
    b_jan = um(c, "SELECT COUNT(DISTINCT chunk_id) FROM brief_log WHERE served_at >= ?", ini)
    s_jan_lb = um(c, "SELECT COUNT(*) FROM chunks WHERE last_accessed_at >= ?", ini)
    ent_tot = um(c, "SELECT COUNT(*) FROM chunks WHERE source_file LIKE 'memory/entities/%'")
    ent_b_jan = um(c, """SELECT COUNT(*) FROM chunks
        WHERE source_file LIKE 'memory/entities/%'
          AND id IN (SELECT DISTINCT chunk_id FROM brief_log WHERE served_at >= ?)""", ini)
    ent_s_jan_lb = um(c, """SELECT COUNT(*) FROM chunks
        WHERE source_file LIKE 'memory/entities/%' AND last_accessed_at >= ?""", ini)

    # ─── o instrumento que está desligado ─────────────────────────────────
    st_tot = um(c, "SELECT COUNT(*) FROM search_telemetry")
    st_ids = um(c, "SELECT COUNT(*) FROM search_telemetry WHERE top_chunk_ids IS NOT NULL AND top_chunk_ids <> ''")
    st_ultimo = um(c, "SELECT MAX(ts) FROM search_telemetry WHERE top_chunk_ids IS NOT NULL AND top_chunk_ids <> ''")
    st_na_janela = um(c, """SELECT COUNT(*) FROM search_telemetry
        WHERE ts >= ? AND top_chunk_ids IS NOT NULL AND top_chunk_ids <> ''""", ini)

    out = {
        "gerado_em": subprocess.run(["date", "-u", "+%Y-%m-%dT%H:%M:%SZ"],
                                    capture_output=True, text=True).stdout.strip(),
        "db": a.db,
        "corpus": corpus,
        "cumulativo_exato": {
            "brief": brief_ids,
            "busca": busca,
            "uniao": uniao,
            "nenhuma_superficie": nenhuma,
            "pct_nenhuma": round(100 * nenhuma / corpus, 2),
            "servidos_no_brief_e_depois_apagados": servidos_e_apagados,
            "invisiveis_que_passam_o_piso": invisiveis_elegiveis,
            "invisiveis_elegiveis_por_tipo": dict(por_tipo_invisivel),
        },
        "gradiente_de_curadoria": [
            {"tipo": t, "total": tot, "exposto": exp, "pct": round(100 * exp / tot, 1)}
            for t, tot, exp in tipos
        ],
        "concentracao_do_brief": {
            "janela_7d": [d7ini, fim],
            "slots_historicos_ATE_AGORA_serie_viva": slots,
            "desde": span[0], "ate": span[1],
            "distintos_7d": len(d7),
            "slots_7d": tot7,
            "briefs_7d": nb7,
            "chunks_em_100pct_dos_briefs_7d": em_todos,
            "pct_top10": round(100 * sum(n for _, n in d7[:10]) / tot7, 2) if tot7 else None,
            "pct_top20": round(100 * sum(n for _, n in d7[:20]) / tot7, 2) if tot7 else None,
        },
        "janela_comum": {
            "inicio": ini,
            "brief_exato": b_jan,
            "busca_limite_inferior": s_jan_lb,
            "entities_total": ent_tot,
            "entities_brief_exato": ent_b_jan,
            "entities_busca_limite_inferior": ent_s_jan_lb,
            "aviso": ("busca é LIMITE INFERIOR (last_accessed_at guarda só o último "
                      "acesso). O bound sustenta 'invisibilidade no MÁXIMO tanto', "
                      "não o contrário — para invisibilidade alta use o cumulativo."),
        },
        "instrumento_desligado": {
            "tabela": "search_telemetry.top_chunk_ids",
            "linhas_totais_serie_viva": st_tot,
            "linhas_com_ids_serie_viva": st_ids,
            "ultimo_com_ids": st_ultimo,
            "com_ids_na_janela_comum": st_na_janela,
            "consequencia": ("sem isto não existe comparação brief-vs-busca DENTRO de "
                             "janela; religá-lo é pré-requisito para essa comparação"),
        },
    }
    print(json.dumps(out, indent=2, ensure_ascii=False))
    if a.out:
        with open(a.out, "w") as f:
            f.write(json.dumps(out, indent=2, ensure_ascii=False) + "\n")

    if a.assert_json:
        with open(a.assert_json) as f:
            esp = json.load(f)
        falhas = []

        def desce(cam, e, o):
            if isinstance(e, dict):
                for k, v in e.items():
                    desce(f"{cam}.{k}", v, (o or {}).get(k))
            elif e != o:
                falhas.append(f"{cam}: obtido {o!r} != declarado {e!r}")

        for k, v in esp.items():
            if k.startswith("_"):
                continue
            desce(k, v, out.get(k))
        if falhas:
            print("\n⛔ ASSERÇÃO FALHOU:", file=sys.stderr)
            for x in falhas:
                print("   " + x, file=sys.stderr)
            sys.exit(1)
        print("\n✅ números declarados batem", file=sys.stderr)


if __name__ == "__main__":
    main()
