#!/usr/bin/env python3
"""Gera K designacoes SHAM para o teste de especificidade (SPEC-ANALISE §5).

19 chunks NAO designados, sorteados do MESMO predicado de elegibilidade de que
sairam os 19 reais. Estrutura identica ao DESIGNATION real, porque o replay
carrega o ficheiro por essa forma.

⚠️ O sorteio e' do POOL ELEGIVEL, nao do corpus: um sham tirado do corpus
inteiro nunca entraria no candidato list e o replay nao mediria nada -- o teste
diria 'sham nao move' por construcao, que e' a armadilha simetrica a' do
candidato tautologico que a SPEC §5 ja' rejeita.
"""
import json, hashlib, random, sqlite3, sys, pathlib

DES  = "/root/.openclaw/paper2/DESIGNATION-2026-08-26.json"
CORP = "/var/lib/nox-mem/p2/corpus-preservado-20260908.db"
K    = int(sys.argv[1]) if len(sys.argv) > 1 else 20
OUT  = pathlib.Path("/tmp/shams"); OUT.mkdir(exist_ok=True)

real = json.loads(pathlib.Path(DES).read_text())
ids_reais = set(real["designados"].values())
chaves = list(real["designados"].keys())

# o predicado de elegibilidade, o mesmo que POOL-ELEGIVEL declara
con = sqlite3.connect(f"file:{CORP}?mode=ro", uri=True)
# ⚠️ A JANELA DE IDADE tambem entra. Sem ela o predicado da 305 e o pool real e
# 115: um sham com chunk velho nao entra no candidate list e 'nao move' por
# construcao — o teste diria especificidade onde havia so' inelegibilidade.
# Controle do predicado: com a idade, este SQL da' 115, e o replay OBSERVA
# pool=115 no mesmo t-ref. Duas vias independentes, mesmo numero.
import datetime as _dt
TREF = _dt.datetime(2026, 9, 8, 12, 0, 0)
rows = con.execute("""
    SELECT id, created_at FROM chunks
     WHERE (source_file LIKE 'memory/entities/%' OR source_file = 'memory/lessons.md')
       AND (importance >= 0.7 OR pain >= 0.7)
""").fetchall()
con.close()
cand = [r[0] for r in rows
        if r[1] and (TREF - _dt.datetime.fromisoformat(r[1])).days <= 30]
pool = sorted(set(cand) - ids_reais)
assert len(cand) == 115, f"predicado deu {len(cand)}, esperado 115 (o replay observa 115)"
print(f"candidatos no predicado: {len(cand)}  |  nao-designados: {len(pool)}  |  reais: {len(ids_reais)}")
if len(pool) < 19:
    print(f"🔴 ABORTA: pool de nao-designados tem {len(pool)} < 19 — sham impossivel"); sys.exit(2)

manifesto = []
for i in range(K):
    rng = random.Random(int(hashlib.sha256(f"p2-sham-2026-09-21|{i}".encode()).hexdigest()[:16], 16))
    escolhidos = rng.sample(pool, 19)
    d = dict(real)                       # mesma forma; so' os ids mudam
    d["designados"] = {k: v for k, v in zip(chaves, escolhidos)}
    d["designados_ids"] = sorted(escolhidos)
    d["declaracao"] = f"SHAM {i} — 19 nao-designados do mesmo predicado. NAO e' a designacao do ensaio."
    d["sha256_do_conjunto"] = hashlib.sha256(
        ",".join(str(x) for x in sorted(escolhidos)).encode()).hexdigest()
    p = OUT / f"SHAM-{i:03d}.json"
    p.write_text(json.dumps(d, indent=2, ensure_ascii=False))
    manifesto.append(dict(i=i, path=str(p),
                          sha_ficheiro=hashlib.sha256(p.read_bytes()).hexdigest(),
                          ids=sorted(escolhidos)))
(OUT / "MANIFESTO-SHAMS.json").write_text(json.dumps(
    dict(k=K, seed_prefix="p2-sham-2026-09-21", pool_nao_designados=len(pool),
         ids_reais=sorted(ids_reais), shams=manifesto), indent=2))
print(f"gerados {K} shams em {OUT}  |  sobreposicao com os reais: "
      f"{max(len(set(m['ids']) & ids_reais) for m in manifesto)} (tem de ser 0)")
