#!/usr/bin/env python3
"""Data de expiração dos designados do Paper 2, medida contra o corpus SERVIDO.

Por que este instrumento existe
-------------------------------
O predicado de frescor do `serving-brief.ts` (`fetchFreshCandidates`, :640-648) usa
`julianday('now')` LITERAL — não um parâmetro. Não existe forma de perguntar ao harness
"quantos passariam no dia 20"; ele responde sempre pelo relógio de parede. Medir a
expiração exige portanto DESLOCAR A JANELA em vez do relógio, que é a mesma compensação
que o `replay-oportunidade.mjs` faz em `cfgEm(tRefMs)`.

Deslocar a janela é REIMPLEMENTAR o predicado, e monitor que reimplementa predicado
omite caso (CLAUDE.md, e o canary que ignorava `hybrid` em 01/09). A defesa é a perna
`concordancia`: em `tRef == agora` a reimplementação tem de devolver EXATAMENTE o que o
predicado literal devolve. Divergindo, o script sai `RED` e não reporta grade nenhuma —
uma grade construída sobre predicado divergente é pior que nenhuma.

Recibo
------
Todo veredito carrega `corpus_path` E `corpus_sha256`. O §10.17 nasceu de um recibo em
que `GREEN 20/37` e `RED 0/0` tinham `sha256_janela` idêntico porque o campo que
distinguia — o corpus — não existia. Aqui a entrada decisiva está no recibo.

READ-ONLY: abre o corpus em `mode=ro` e não toca no banco vivo.
"""
import argparse, hashlib, json, sqlite3, sys, datetime as dt

# Espelha GLOBAL_FRESH_PATTERNS (serving-brief.ts:135). Mudou lá ⇒ muda aqui, e a
# perna `concordancia` é o que detecta o desalinhamento.
PADROES_GLOBAIS = ["memory/entities/%", "memory/lessons.md"]

def sha256(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", required=True, help="o corpus SERVIDO, não o current.db")
    ap.add_argument("--designacao", required=True)
    ap.add_argument("--designacao-sha256", required=True)
    ap.add_argument("--piso-imp", type=float, default=0.7)
    ap.add_argument("--piso-pain", type=float, default=0.7)
    ap.add_argument("--janela-global-d", type=float, default=30.0)
    ap.add_argument("--grade-de", default=None, help="AAAA-MM-DD; default = hoje UTC")
    ap.add_argument("--grade-dias", type=int, default=18)
    ap.add_argument("--hora-fronteira", default="09:00:00", help="fronteira do epoch, UTC")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()

    rec = {
        "instrumento": "expiracao-designados",
        "versao": 1,
        "ts": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "corpus_path": a.corpus,
        "corpus_sha256": sha256(a.corpus),
        "designacao_path": a.designacao,
        "designacao_sha256": sha256(a.designacao),
        "padroes_globais": PADROES_GLOBAIS,
        "piso_imp": a.piso_imp, "piso_pain": a.piso_pain,
        "janela_global_d": a.janela_global_d,
        "hora_fronteira_utc": a.hora_fronteira,
    }

    if rec["designacao_sha256"] != a.designacao_sha256:
        rec.update(veredito="RED", motivo="designacao-sha256-divergente",
                   esperado=a.designacao_sha256)
        emitir(rec, a.out); return

    ids = json.load(open(a.designacao))["designados_ids"]
    rec["n_designados"] = len(ids)
    marca = ",".join("?" * len(ids))
    like = " OR ".join("source_file LIKE ?" for _ in PADROES_GLOBAIS)

    db = sqlite3.connect(f"file:{a.corpus}?mode=ro", uri=True)

    # ── perna `presenca`: id que não existe no corpus não expira, desaparece ──
    viv = db.execute(f"SELECT COUNT(*) FROM chunks WHERE id IN ({marca})", ids).fetchone()[0]
    rec["vivos_no_corpus"] = viv
    if viv != len(ids):
        rec.update(veredito="RED", motivo="designado-ausente-do-corpus")
        emitir(rec, a.out); return

    # ── perna `concordancia`: literal 'now' vs janela deslocada para agora ──
    lit = {r[0] for r in db.execute(
        f"""SELECT id FROM chunks WHERE id IN ({marca}) AND ({like})
              AND (COALESCE(importance,0) >= ? OR COALESCE(pain,0) >= ?)
              AND julianday('now') - julianday(COALESCE(source_date, created_at)) <= ?""",
        [*ids, *PADROES_GLOBAIS, a.piso_imp, a.piso_pain, a.janela_global_d]).fetchall()}
    agora = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    reimp = {r[0] for r in db.execute(
        f"""SELECT id FROM chunks WHERE id IN ({marca}) AND ({like})
              AND (COALESCE(importance,0) >= ? OR COALESCE(pain,0) >= ?)
              AND julianday(?) - julianday(COALESCE(source_date, created_at)) <= ?""",
        [*ids, *PADROES_GLOBAIS, a.piso_imp, a.piso_pain, agora, a.janela_global_d]).fetchall()}
    rec["concordancia"] = {
        "literal_now": len(lit), "janela_deslocada": len(reimp),
        "so_no_literal": sorted(lit - reimp), "so_na_reimplementacao": sorted(reimp - lit),
    }
    if lit != reimp:
        rec.update(veredito="RED", motivo="reimplementacao-divergente-do-predicado")
        emitir(rec, a.out); return

    # ── censo por id: de que data cada um envelhece, e por qual coluna ──
    cols = db.execute(
        f"""SELECT id, source_file, importance, pain, source_date, created_at,
                   COALESCE(source_date, created_at) AS ancora,
                   CASE WHEN source_date IS NULL THEN 'created_at' ELSE 'source_date' END AS via
              FROM chunks WHERE id IN ({marca}) ORDER BY id""", ids).fetchall()
    rec["por_id"] = [dict(zip(
        ["id","source_file","importance","pain","source_date","created_at","ancora","via"], c))
        for c in cols]
    ancoras = sorted({c[6] for c in cols})
    rec["ancoras_distintas"] = ancoras
    rec["ancora_unica"] = len(ancoras) == 1

    # ── grade: quantos passam a cada fronteira de epoch ──
    d0 = (dt.date.fromisoformat(a.grade_de) if a.grade_de
          else dt.datetime.now(dt.timezone.utc).date())
    grade = []
    for k in range(a.grade_dias):
        dia = d0 + dt.timedelta(days=k)
        t = f"{dia.isoformat()} {a.hora_fronteira}"
        passam = [r[0] for r in db.execute(
            f"""SELECT id FROM chunks WHERE id IN ({marca}) AND ({like})
                  AND (COALESCE(importance,0) >= ? OR COALESCE(pain,0) >= ?)
                  AND julianday(?) - julianday(COALESCE(source_date, created_at)) <= ?""",
            [*ids, *PADROES_GLOBAIS, a.piso_imp, a.piso_pain, t, a.janela_global_d]).fetchall()]
        grade.append({"fronteira_utc": t, "elegiveis": len(passam)})
    rec["grade"] = grade

    # ── último dia elegível e o primeiro zero, lidos DA grade, não deduzidos ──
    ult = [g for g in grade if g["elegiveis"] > 0]
    zer = [g for g in grade if g["elegiveis"] == 0]
    rec["ultima_fronteira_elegivel"] = ult[-1]["fronteira_utc"] if ult else None
    rec["primeira_fronteira_zerada"] = zer[0]["fronteira_utc"] if zer else None
    rec["grade_alcanca_o_zero"] = bool(zer)

    if not zer:
        rec.update(veredito="YELLOW", motivo="grade-curta-nao-alcanca-o-zero")
    elif ult and len(ult[-1:]) and ult[-1]["elegiveis"] == len(ids):
        rec.update(veredito="GREEN", motivo="expiracao-em-bloco-datada")
    else:
        rec.update(veredito="YELLOW", motivo="expiracao-escalonada")
    emitir(rec, a.out)

def emitir(rec, out):
    lin = (f'{rec["veredito"]} p2-expiracao-designados motivo={rec["motivo"]} '
           f'corpus_sha256={rec["corpus_sha256"][:12]} '
           f'ultima={rec.get("ultima_fronteira_elegivel")} '
           f'primeira_zero={rec.get("primeira_fronteira_zerada")}')
    print(lin)
    if out:
        with open(out, "w") as f: json.dump(rec, f, indent=2, ensure_ascii=False)
        print(f"artefato={out}")
    else:
        print(json.dumps(rec, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
