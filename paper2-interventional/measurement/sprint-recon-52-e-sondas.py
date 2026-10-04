#!/usr/bin/env python3
"""
sprint-recon-52-e-sondas.py — closes two reconciliations left open in MANUSCRIPT.md
(list "O que falta", item 5): the "52 = 52" between §4.3.1 and §4.3.2, and the
"25 missing slots" of §4.3.

Read-only on every DB it opens (mode=ro). Run it on COPIES, never on the originals
(a WAL-mode DB grows -wal/-shm even when opened read-only).

Inputs
  --serving-db  a DB whose brief_log covers [2026-08-20, 2026-08-27) and whose `chunks`
                is the state the §4.3 numbers were measured against (the 2026-09-07
                epoch e20260907T060001Z.db has corpus = 67.187, the same as §4.1, and the
                access_count of the three constants equals TOP-COUNTERFACTUAL).
  --pre-db      a DB taken while the deleted chunks still existed (daily-main of
                2026-08-21 06:00 UTC), to recover their identity and metadata.
  --post-db     a DB taken after their deletion (pre-op kg-confirm 2026-08-22 02:02 UTC).
  --sondas      out/ancora-sondas.json (lists the 5 probe brief_ids).
  --now         pinned "now" for the salience recency term (the original counterfactual
                used julianday('now') on 2026-08-29 and did not record the instant).

What it measures
  1. window totals, and per-UTC-day distinct served vs distinct that still exist;
  2. the deleted set of the week and of each day, compared as SETS (not counts);
  3. identity of the deleted chunks (source_file, type, created_at) and when they
     disappeared, plus how many slots were served after the disappearance;
  4. briefs with != 10 rows in the window, compared by brief_id to the probe list,
     and the §4.3 table recomputed with those briefs excluded;
  5. the counterfactual of §4.3.2 reproduced on the 149 survivors, then re-run with
     the 52 deleted chunks restored from --pre-db, so the "lower bound" becomes a
     measured position.
"""
import argparse
import collections
import datetime as dt
import json
import math
import sqlite3
import sys

W0, W1 = "2026-08-20", "2026-08-27"
W_IMP, W_REC, W_PAIN, W_ACC = 0.55, 0.15, 0.10, 0.20   # serving-salience.ts:220-223
LOG1000 = math.log(1000)
ONIPRESENTES = (116467, 112241, 116107)


def ro(path):
    return sqlite3.connect(f"file:{path}?mode=ro", uri=True)


def acesso(n):
    return 0.0 if not n or n <= 0 else min(1.0, math.log1p(n) / LOG1000)


def ids_served(c, a, b, excl=()):
    q = "SELECT DISTINCT chunk_id FROM brief_log WHERE served_at>=? AND served_at<?"
    args = [a, b]
    if excl:
        q += " AND brief_id NOT IN (%s)" % ",".join("?" * len(excl))
        args += list(excl)
    return {r[0] for r in c.execute(q, args)}


def concentracao(c, excl=()):
    where = "served_at>=? AND served_at<?"
    args = [W0, W1]
    if excl:
        where += " AND brief_id NOT IN (%s)" % ",".join("?" * len(excl))
        args += list(excl)
    slots, briefs, dist = c.execute(
        f"SELECT COUNT(*), COUNT(DISTINCT brief_id), COUNT(DISTINCT chunk_id) FROM brief_log WHERE {where}",
        args).fetchone()
    curva = [r[0] for r in c.execute(
        f"SELECT COUNT(*) n FROM brief_log WHERE {where} GROUP BY chunk_id ORDER BY n DESC", args)]
    em_todos = c.execute(
        f"SELECT COUNT(*) FROM (SELECT chunk_id, COUNT(DISTINCT brief_id) nb FROM brief_log WHERE {where} "
        f"GROUP BY chunk_id) WHERE nb=?", args + [briefs]).fetchone()[0]
    return {
        "slots": slots, "briefs": briefs, "distintos": dist,
        "deficit_contra_10_por_brief": briefs * 10 - slots,
        "presentes_em_100pct": em_todos,
        "pct_top10": round(100 * sum(curva[:10]) / slots, 2),
        "pct_top20": round(100 * sum(curva[:20]) / slots, 2),
        "pct_3_constantes": round(100 * sum(curva[:3]) / slots, 2),
        "soma_curva_confere": sum(curva) == slots,
    }


def score(imp, pain, acc, idade, com_acesso):
    rec = max(0.0, min(1.0, 1.0 - (idade or 0) / 365.0))
    return W_IMP * imp + W_REC * rec + W_PAIN * pain + (W_ACC * acesso(acc) if com_acesso else 0.0)


def ranking(cands):
    """cands: list of (id, imp, pain, acc, idade). Same tie-break as contrafactual-do-topo.py
    (sorted on (score, id) descending)."""
    out = {}
    for com in (True, False):
        s = sorted(((score(i, p, a, d, com), cid) for cid, i, p, a, d in cands), reverse=True)
        out[com] = {cid: k for k, (_, cid) in enumerate(s, 1)}
    return out


def cands_from(c, ids, now):
    q = ("SELECT id, COALESCE(importance,0.5), COALESCE(pain,0.2), COALESCE(access_count,0), "
         "julianday(?) - julianday(COALESCE(source_date, created_at)) FROM chunks WHERE id IN (%s)"
         % ",".join(map(str, ids)))
    return c.execute(q, (now,)).fetchall()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--serving-db", required=True)
    ap.add_argument("--pre-db", required=True)
    ap.add_argument("--post-db", required=True)
    ap.add_argument("--sondas", required=True)
    ap.add_argument("--now", action="append", default=None,
                    help="pinned now(s) for the recency term; repeatable")
    ap.add_argument("--out")
    a = ap.parse_args()
    nows = a.now or ["2026-08-29 00:00:00", "2026-08-29 12:00:00", "2026-08-29 23:59:59"]

    s = ro(a.serving_db)
    pre = ro(a.pre_db)
    post = ro(a.post_db)
    existe = {r[0] for r in s.execute("SELECT id FROM chunks")}
    res = {"inputs": {"serving_db": a.serving_db, "pre_db": a.pre_db, "post_db": a.post_db,
                      "sondas": a.sondas, "janela": [W0, W1]},
           "serving_db_state": {
               "chunks": len(existe),
               "brief_log_max_served_at": s.execute("SELECT MAX(served_at) FROM brief_log").fetchone()[0],
               "access_count_dos_3": dict(s.execute(
                   "SELECT id, access_count FROM chunks WHERE id IN (116467,112241,116107)").fetchall()),
           }}

    # ── 1-2. week vs day, as sets ────────────────────────────────────────────
    W = ids_served(s, W0, W1)
    DW = W - existe
    dias = []
    d = dt.date(2026, 8, 18)
    while d < dt.date(2026, 8, 30):
        n = d + dt.timedelta(days=1)
        S = ids_served(s, d.isoformat(), n.isoformat())
        D = S - existe
        dias.append({"dia_utc": d.isoformat(), "distintos_brief_log": len(S),
                     "distintos_que_existem": len(S & existe), "ausentes": len(D),
                     "ausentes_igual_ao_conjunto_da_semana": D == DW and bool(D)})
        d = n
    q = ",".join(map(str, sorted(DW)))
    first, last, nslots, nbriefs = s.execute(
        f"SELECT MIN(served_at), MAX(served_at), COUNT(*), COUNT(DISTINCT brief_id) FROM brief_log WHERE chunk_id IN ({q})"
    ).fetchone()
    por_agente = dict(s.execute(
        f"SELECT COALESCE(agent,'(null)'), COUNT(*) FROM brief_log WHERE chunk_id IN ({q}) GROUP BY 1").fetchall())
    por_brief = collections.Counter(r[0] for r in s.execute(
        f"SELECT COUNT(*) FROM brief_log WHERE chunk_id IN ({q}) GROUP BY brief_id"))

    # ── 3. identity and disappearance ───────────────────────────────────────
    meta = pre.execute(
        f"SELECT id, source_file, chunk_type, created_at, importance, pain FROM chunks WHERE id IN ({q})"
    ).fetchall()
    ainda_no_post = post.execute(f"SELECT COUNT(*) FROM chunks WHERE id IN ({q})").fetchone()[0]
    arquivos = sorted({m[1] for m in meta})
    subst = {}
    for f in arquivos:
        subst[f] = {
            "pre": pre.execute("SELECT created_at, COUNT(*), MIN(id), MAX(id) FROM chunks WHERE source_file=? GROUP BY created_at", (f,)).fetchall(),
            "post": post.execute("SELECT created_at, COUNT(*), MIN(id), MAX(id) FROM chunks WHERE source_file=? GROUP BY created_at", (f,)).fetchall(),
            "serving": s.execute("SELECT created_at, COUNT(*), MIN(id), MAX(id) FROM chunks WHERE source_file=? GROUP BY created_at", (f,)).fetchall(),
        }
    pre_bl = pre.execute("SELECT MAX(served_at) FROM brief_log").fetchone()[0]
    post_bl = post.execute("SELECT MAX(served_at) FROM brief_log").fetchone()[0]
    # earliest creation instant of the replacement set, as a bound on the deletion instant
    repl_created = [r for f in arquivos for r in subst[f]["post"]]
    repl_t = min(r[0] for r in repl_created) if repl_created else None
    servidos_apos_substituicao = s.execute(
        f"SELECT COUNT(*), COUNT(DISTINCT brief_id) FROM brief_log WHERE chunk_id IN ({q}) AND served_at > ?",
        (repl_t,)).fetchone() if repl_t else None
    res["c52"] = {
        "semana_distintos": len(W), "semana_existem": len(W & existe), "semana_ausentes": len(DW),
        "ausentes_ids_min_max": [min(DW), max(DW)] if DW else None,
        "ausentes_contiguos": (max(DW) - min(DW) + 1 == len(DW)) if DW else None,
        "por_dia_utc": dias,
        "ausentes_servidos": {"primeiro": first, "ultimo": last, "slots": nslots, "briefs": nbriefs,
                              "linhas_por_brief": dict(por_brief), "slots_por_agente": por_agente},
        "identidade_no_pre_db": {
            "encontrados": len(meta),
            "source_file": dict(collections.Counter(m[1] for m in meta)),
            "chunk_type": dict(collections.Counter(m[2] for m in meta)),
            "created_at": dict(collections.Counter(m[3] for m in meta)),
            "importance_pain": dict(collections.Counter(f"{m[4]}/{m[5]}" for m in meta)),
        },
        "pre_db_brief_log_max": pre_bl, "post_db_brief_log_max": post_bl,
        "presentes_no_post_db": ainda_no_post,
        "linhagem_do_arquivo": subst,
        "substituicao_criada_em": repl_t,
        "servidos_depois_da_substituicao": servidos_apos_substituicao,
    }
    if repl_t:
        novos = [r for r in s.execute(
            "SELECT id FROM chunks WHERE source_file IN (%s) AND created_at=?" % ",".join("?" * len(arquivos)),
            arquivos + [repl_t])]
        novos = {r[0] for r in novos}
        res["c52"]["substitutos_servidos_na_janela"] = [len(novos & W), len(novos)]

    # ── 4. the 25 slots ──────────────────────────────────────────────────────
    sondas = json.load(open(a.sondas))["procedencia"]["sondas_excluidas"]
    curtos = s.execute(
        "SELECT brief_id, COUNT(*) n, MIN(served_at), MAX(served_at), COALESCE(agent,'(null)'), scope "
        "FROM brief_log WHERE served_at>=? AND served_at<? GROUP BY brief_id HAVING n<>10 ORDER BY 3",
        (W0, W1)).fetchall()
    hist = dict(s.execute(
        "SELECT n, COUNT(*) FROM (SELECT COUNT(*) n FROM brief_log WHERE served_at>=? AND served_at<? "
        "GROUP BY brief_id) GROUP BY n", (W0, W1)).fetchall())
    nulos = s.execute("SELECT COUNT(*) FROM brief_log WHERE served_at>=? AND served_at<? AND brief_id IS NULL",
                      (W0, W1)).fetchone()[0]
    res["c25"] = {
        "histograma_linhas_por_brief": hist,
        "linhas_sem_brief_id": nulos,
        "briefs_com_n_diferente_de_10": [
            {"brief_id": b, "linhas": n, "de": t0, "ate": t1, "agent": ag, "scope": sc} for b, n, t0, t1, ag, sc in curtos],
        "conjunto_igual_a_ancora_sondas": {b for b, *_ in curtos} == set(sondas),
        "sondas_na_ancora": len(sondas),
        "tabela_4_3_como_publicada": concentracao(s),
        "tabela_4_3_sem_sondas": concentracao(s, sondas),
    }

    # ── 5. counterfactual: reproduce, then restore the 52 ──────────────────
    vivos = sorted(W & existe)
    cf = []
    meta_pre = {m[0]: m for m in meta}
    for now in nows:
        c149 = cands_from(s, vivos, now)
        r149 = ranking(c149)
        c52 = cands_from(pre, sorted(DW), now) if DW else []
        r201 = ranking(c149 + c52)
        cf.append({
            "now": now,
            "n_149": len(c149), "n_201": len(c149) + len(c52),
            "posicoes_149": {cid: [r149[True][cid], r149[False][cid]] for cid in ONIPRESENTES},
            "posicoes_201": {cid: [r201[True][cid], r201[False][cid]] for cid in ONIPRESENTES},
            "melhor_posicao_dos_52_sem_acesso": min(r201[False][x] for x in DW) if DW else None,
            "melhor_posicao_dos_52_com_acesso": min(r201[True][x] for x in DW) if DW else None,
        })
    res["contrafactual"] = {"formula": "serving-salience.ts:220-233 via contrafactual-do-topo.py",
                            "artefato_publicado": {"116467": [2, 131], "112241": [3, 129], "116107": [5, 128]},
                            "rodadas": cf}

    txt = json.dumps(res, indent=2, ensure_ascii=False, default=list)
    if a.out:
        open(a.out, "w").write(txt + "\n")
    print(txt)
    return 0


if __name__ == "__main__":
    sys.exit(main())
