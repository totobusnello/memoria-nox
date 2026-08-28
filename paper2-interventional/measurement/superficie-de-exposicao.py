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
import re
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
    ap.add_argument("--fonte-search", required=True,
                    help="caminho de src/search.ts. Obrigatório: a lista de colunas "
                         "da INSERT é o segundo critério do censo de colunas sem "
                         "escritor, e digitá-la aqui foi o defeito que este argumento "
                         "existe para impedir.")
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
    #
    # Censo das colunas SEM escritor, computado. Dois critérios, e o segundo existe
    # porque o primeiro sozinho classificaria como morta uma coluna viva de valor
    # constante na janela.
    CORTE_ESCRITOR = "2026-05-20"      # dia seguinte à morte suspeita
    try:
        FONTE_SEARCH = open(a.fonte_search, encoding="utf-8", errors="replace").read()
    except OSError as e:
        print("⛔ não consegui ler --fonte-search: %s" % e, file=sys.stderr)
        sys.exit(2)
    m_ins = re.search(r"INSERT INTO search_telemetry \(([^)]*)\)", FONTE_SEARCH)
    if not m_ins:
        print("⛔ não achei a INSERT de search_telemetry no fonte — sem ela o censo "
              "de colunas sem escritor não tem o segundo critério", file=sys.stderr)
        sys.exit(2)
    escritas = [x.strip() for x in m_ins.group(1).split(",")]
    sem_escritor, mortas_por_data = [], {}
    for _i, nome, _t, _nn, _d, _pk in c.execute("PRAGMA table_info(search_telemetry)"):
        if nome in escritas or nome in ("id", "ts"):
            continue
        dist = um(c, 'SELECT COUNT(DISTINCT "%s") FROM search_telemetry WHERE ts >= ?'
                  % nome, CORTE_ESCRITOR)
        if dist <= 1:
            sem_escritor.append(nome)
            # ⚠️ "última escrita real" tem de EXCLUIR o default, senão para coluna com
            # DEFAULT a resposta é sempre "a última linha antes do corte" — foi o que
            # agrupou 11 colunas num instante falso (2026-05-19 23:47:02) na primeira
            # versão deste cômputo.
            if _d is None:
                cond = '"%s" IS NOT NULL' % nome
                par = ()
            else:
                cond = '"%s" IS NOT NULL AND "%s" <> %s' % (nome, nome, _d)
                par = ()
            ult = um(c, 'SELECT MAX(ts) FROM search_telemetry WHERE %s AND ts < ?'
                     % cond, CORTE_ESCRITOR, *par)
            # agrupa por instante da última escrita real: instantes DIFERENTES ⇒
            # commits diferentes, e a narrativa de "um commit apagou tudo" cai.
            mortas_por_data.setdefault(ult or "nunca escrita", []).append(nome)
    st_tot = um(c, "SELECT COUNT(*) FROM search_telemetry")
    st_ids = um(c, "SELECT COUNT(*) FROM search_telemetry WHERE top_chunk_ids IS NOT NULL AND top_chunk_ids <> ''")
    st_ultimo = um(c, "SELECT MAX(ts) FROM search_telemetry WHERE top_chunk_ids IS NOT NULL AND top_chunk_ids <> ''")
    st_na_janela = um(c, """SELECT COUNT(*) FROM search_telemetry
        WHERE ts >= ? AND top_chunk_ids IS NOT NULL AND top_chunk_ids <> ''""", ini)

    # ─── a telemetria de busca mede o CANÁRIO, e o teste é o minuto do cron ────
    #
    # O cron roda `22,52 * * * *`. Se as linhas se agrupam nesses minutos, a tabela
    # mede a sonda de saúde, não o agente.
    #
    # ⚠️ O teste ANTERIOR estava errado no motivo: eu havia usado "`requesting_agent`
    # não populado" como evidência de que era o canário. Mas essa coluna é nula para
    # TODOS — o `INSERT` que a preenchia foi apagado em 2026-05-19 (ver
    # `instrumento_apagado`). Coluna vazia por remoção de escritor não distingue
    # canário de agente. O minuto distingue.
    MIN_CANARIO = (21, 22, 23, 51, 52, 53)
    st_jan = c.execute("""SELECT CAST(substr(ts,15,2) AS INTEGER) m, COUNT(*)
                            FROM search_telemetry WHERE ts >= ? AND ts < ?
                           GROUP BY m""", (d7ini, fim)).fetchall()
    st_n = sum(n for _, n in st_jan)
    st_can = sum(n for m, n in st_jan if m in MIN_CANARIO)

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
            # Curva completa rank × slots, para a Figura 2. `pct_top10`/`pct_top20` são
            # dois pontos DESTA série: emiti-la em vez de só os dois resumos é o que
            # impede a figura de ser desenho — ela passa a derivar do mesmo artefato que
            # o texto cita, e muda junto se o dado mudar. Só as contagens: `chunk_id`
            # ficaria de fora por privacidade se fosse conteúdo, mas aqui nem é preciso,
            # porque a figura é sobre a FORMA da distribuição, não sobre quais itens.
            "curva_slots_por_rank": [n for _, n in d7],
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
        "canario_vs_agente": {
            "janela_7d": [d7ini, fim],
            "cron": "22,52 * * * *",
            "linhas": st_n,
            "nos_minutos_do_canario": st_can,
            "pct_canario": round(100 * st_can / st_n, 1) if st_n else None,
            "restante_por_dia": round((st_n - st_can) / 7, 1) if st_n else None,
            "conclusao": ("a tabela mede a sonda de saúde do cron, não o agente; "
                          "o que sobra é ~2-3 linhas/dia"),
        },
        "instrumento_apagado": {
            "tabela": "search_telemetry.top_chunk_ids",
            "diagnostico": (
                "NÃO é retirada deliberada: o commit 7fdaab4f ('eod: 2026-05-19 — "
                "nox-mem repair (import mismatch)') APAGOU o INSERT de 23 colunas "
                "(top_chunk_ids, top_scores, requesting_agent, reason_boost_*, "
                "reranker_*) num commit de fim de dia que também mexeu em CONTEXT.md "
                "e memória de agentes. Sobrou o INSERT de 7 colunas em search.ts:608. "
                "Este projeto REGISTRA retirada deliberada com 'CUT' no título do "
                "commit (ex.: 'CUT E05b reason-boost — bias arquitetural confirmado'); "
                "não existe CUT para esta telemetria. Ausência de CUT ⇒ regressão, "
                "não decisão — e ninguém notou por 3,3 meses."),
            # ⚠️ COMPUTADO, e a lista digitada que estava aqui dava 13 — errado.
            # Três métodos falharam antes deste, cada um por um motivo diferente:
            #   grep por INSERT       -> perde UPDATE e SQL dinâmico (perdeu 3 colunas)
            #   "não-nulo"            -> DEFAULT preenche toda linha (11 falsos vivos)
            #   "distintos > 1"       -> o histórico pré-morte infla (394 distintos!)
            # O teste que vale é DISTINTOS DENTRO DE UMA JANELA depois da morte
            # suspeita, cruzado com a lista literal de colunas da INSERT do fonte.
            "colunas_sem_escritor": sem_escritor,
            "colunas_escritas_pela_insert": escritas,
            "criterio_sem_escritor": (
                f"distintos == {'<=1'} em ts >= {CORTE_ESCRITOR} E fora da lista de "
                "colunas da INSERT de src/search.ts. ⚠️ Limite: coluna VIVA cujo valor "
                "seja constante na janela seria classificada como morta — por isso o "
                "segundo critério, e por isso a lista da INSERT é extraída do fonte."),
            "mortas_por_data": mortas_por_data,
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
