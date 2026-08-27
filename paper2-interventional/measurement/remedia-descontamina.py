import sqlite3, collections
DB = "file:/root/.openclaw/workspace/tools/nox-mem/nox-mem.db?mode=ro"
T_REF = "2026-08-27 09:00:00"        # <<< instante de referencia FIXADO (era julianday('now'))
CORTE_ANTIGO = "2026-08-26 19:58:00" # o rollback temporal que o script errado usava
SONDAS = ("473f85e8-43ae-4883-baa2-2d76407af941","c48e8353-cd95-4bd5-997b-dc921e2a0cac",
          "6ff2d9c4-79f2-4526-8eb5-c42d60bbeea6","90a105f5-ef33-4135-8e54-b4e978bbb1ee",
          "66977ec1-2809-44df-91b8-c158ce0e68e8")
db = sqlite3.connect(DB, uri=True)

n_sonda = db.execute("SELECT COUNT(*) FROM brief_log WHERE brief_id IN (%s)"
                     % ",".join("?"*len(SONDAS)), SONDAS).fetchone()[0]
print("linhas de sonda a excluir: %d em %d briefs" % (n_sonda, len(SONDAS)))
n_corte = db.execute("SELECT COUNT(*) FROM brief_log WHERE served_at >= ?", (CORTE_ANTIGO,)).fetchone()[0]
print("linhas que o CORTE TEMPORAL antigo removia: %d  <- inclui trafego organico" % n_corte)
print("instante de referencia fixado: %s (antes: julianday('now'))" % T_REF)

estudo = {r[0] for r in db.execute(
    "SELECT DISTINCT chunk_id FROM p2_verdict WHERE chunk_id IS NOT NULL AND severity IN ('S1','S2')")}
eleg = {r[0] for r in db.execute("""SELECT id FROM chunks
   WHERE (source_file LIKE 'memory/entities/%' OR source_file LIKE 'memory/lessons.md')
     AND (COALESCE(importance,0) >= 0.7 OR COALESCE(pain,0) >= 0.7)
     AND julianday(?) - julianday(COALESCE(source_date, created_at)) <= 30""", (T_REF,))}
print("elegiveis=%d  estudo=%d  estudo∩elegiveis=%d" % (len(eleg), len(estudo), len(estudo & eleg)))

def estado(modo):
    if modo == "observado":       cond, par = "", ()
    elif modo == "corte_temporal": cond, par = "AND served_at < ?", (CORTE_ANTIGO,)
    elif modo == "sem_sondas":     cond, par = "AND brief_id NOT IN (%s)" % ",".join("?"*len(SONDAS)), SONDAS
    ls = {}
    for cid, m in db.execute(
            "SELECT chunk_id, MAX(served_at) FROM brief_log WHERE 1=1 %s GROUP BY chunk_id" % cond, par):
        if cid in eleg: ls[cid] = m
    g = collections.defaultdict(list)
    for cid, m in ls.items(): g[m].append(cid)
    ordem = sorted(ls.items(), key=lambda kv: kv[1])
    pos_1o = next((i for i, (cid, _) in enumerate(ordem) if cid in estudo), None)
    quali = []; puro = mist = 0
    for m, v in g.items():
        e = [c for c in v if c in estudo]; n = [c for c in v if c not in estudo]
        if len(v) > 1:
            if e and n: mist += 1
            elif e: puro += 1
        if e and n and len(v) > 2:
            quali.append(min(i for i, (cid, _) in enumerate(ordem) if ls[cid] == m))
    return dict(chunks=len(ls), grupos=len(g), pos_1o_estudo=pos_1o, qualificaveis=len(quali),
                menor_pos_qualif=min(quali) if quali else None, puros=puro, mistos=mist)

o = estado("observado"); c = estado("corte_temporal"); s = estado("sem_sondas")
print()
print("%-20s %>12s %>16s %>14s" % ("metrica", "observado", "corte_temporal", "sem_sondas") if False else
      "%-20s %12s %16s %14s" % ("metrica", "observado", "corte_temporal", "sem_sondas"))
print("-"*66)
for k in o:
    print("%-20s %12s %16s %14s" % (k, o[k], c[k], s[k]))
print()
print("=== leitura: 'corte_temporal' == 'sem_sondas'? %s" % ("SIM" if c == s else "NAO — o corte nao era descontaminacao"))
