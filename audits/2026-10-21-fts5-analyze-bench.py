#!/usr/bin/env python3
"""FTS5/ANALYZE bench on a COPY (2026-10-21). Never touches production.

Measures the exact FTS5 query of src/search.ts:410 (bm25 + JOIN chunks + ORDER
BY rank LIMIT 20) before/after ANALYZE and before/after FTS5 'optimize', so the
gain can be compared against the KNN leg that dominates the hybrid search.
Interleaved A/B, warm-up discarded, median over repeats.
"""
import sqlite3, sys, time, statistics as st, json, os

DB = sys.argv[1]
REPS = int(os.environ.get("REPS", "15"))
QUERIES = ["memoria", "brief agente", "vetor embedding", "incidente producao",
           "paper latencia", "chunk salience", "sqlite indice", "decisao roadmap",
           "gemini quota", "worktree branch", "telemetria custo", "kg entidade"]

def connect():
    c = sqlite3.connect(DB)
    c.execute("PRAGMA cache_size=-64000")   # same as src/db.ts
    c.execute("PRAGMA mmap_size=268435456")
    return c

SQL = """
      SELECT c.id, c.source_file, c.chunk_type, c.chunk_text, c.source_date,
             c.tier, c.source_type, c.section, c.section_boost,
             c.pain, c.importance, c.retention_days, c.created_at, c.last_accessed_at,
             c.access_count,
             bm25(chunks_fts, 1.0, 0.5, 0.5) as rank
      FROM chunks_fts
      JOIN chunks c ON c.id = chunks_fts.rowid
      WHERE chunks_fts MATCH ?
      ORDER BY rank LIMIT 20
"""

def bench(label, con):
    for q in QUERIES:               # warm-up, discarded
        con.execute(SQL, (q,)).fetchall()
    per_q = {}
    lat = []
    for r in range(REPS):
        for q in QUERIES:
            t = time.perf_counter()
            rows = con.execute(SQL, (q,)).fetchall()
            ms = (time.perf_counter() - t) * 1000
            lat.append(ms)
            per_q.setdefault(q, []).append((ms, len(rows)))
    med = st.median(lat)
    print(f"  {label:<22} n={len(lat):>4}  mediana={med:7.2f} ms  min={min(lat):6.2f}  max={max(lat):7.2f}  total_por_busca={med:.2f} ms")
    return med, {q: (round(st.median([x[0] for x in v]), 2), v[0][1]) for q, v in per_q.items()}

def fts_state(con):
    idx = con.execute("SELECT COUNT(*) FROM chunks_fts_idx").fetchone()[0]
    data = con.execute("SELECT COUNT(*), SUM(LENGTH(block)) FROM chunks_fts_data").fetchone()
    stat1 = con.execute("SELECT COUNT(*) FROM sqlite_master WHERE name='sqlite_stat1'").fetchone()[0]
    return {"fts_idx_rows": idx, "fts_data_rows": data[0], "fts_data_bytes": data[1], "has_sqlite_stat1": bool(stat1)}

out = {"db": DB, "reps": REPS, "queries": len(QUERIES)}
con = connect()
print("estado inicial:", fts_state(con))
out["estado_inicial"] = fts_state(con)

print("\n== 1. baseline (como esta em producao)")
base, base_q = bench("baseline", con)
out["baseline_ms"] = base

print("\n== 2. ANALYZE")
t = time.perf_counter(); con.execute("ANALYZE"); con.commit()
out["analyze_s"] = round(time.perf_counter() - t, 1)
print(f"  ANALYZE levou {out['analyze_s']} s; sqlite_stat1 agora:",
      con.execute("SELECT COUNT(*) FROM sqlite_stat1").fetchone()[0], "linhas")
con.close(); con = connect()
after_an, _ = bench("depois do ANALYZE", con)
out["after_analyze_ms"] = after_an

print("\n== 3. FTS5 optimize")
t = time.perf_counter()
con.execute("INSERT INTO chunks_fts(chunks_fts) VALUES('optimize')"); con.commit()
out["optimize_s"] = round(time.perf_counter() - t, 1)
print(f"  optimize levou {out['optimize_s']} s; estado:", fts_state(con))
out["estado_final"] = fts_state(con)
con.close(); con = connect()
after_opt, after_q = bench("depois do optimize", con)
out["after_optimize_ms"] = after_opt

out["ganho_analyze_pct"] = round((base - after_an) / base * 100, 1)
out["ganho_total_pct"] = round((base - after_opt) / base * 100, 1)
print(f"\n== RESUMO  baseline={base:.2f} ms -> ANALYZE={after_an:.2f} ms -> +optimize={after_opt:.2f} ms")
print(f"   ganho ANALYZE: {out['ganho_analyze_pct']}%   ganho acumulado: {out['ganho_total_pct']}%   economia absoluta: {base-after_opt:.2f} ms/busca")
# conferir que a resposta nao mudou
same = sum(1 for q in QUERIES if base_q[q][1] == after_q[q][1])
print(f"   sondas com mesmo numero de linhas: {same}/{len(QUERIES)}")
out["sondas_iguais"] = f"{same}/{len(QUERIES)}"
out["tamanho_db_bytes"] = os.path.getsize(DB)
print("\nJSON:", json.dumps(out, ensure_ascii=False))
