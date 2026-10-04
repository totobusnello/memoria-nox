#!/usr/bin/env python3
"""sprint-gera-shams-v2.py — K SHAM designations for the specificity test (SPEC-ANALISE §5),
version 2 (sprint 2026-10-04, task B-sham-v2). Does NOT replace `gera-shams.py`; that file is
kept as the record of what was configured on 2026-09-21.

What changed against v1, each item closing a defect measured in
`_sprint-2026-10-04/B-replay-fidelity.md`:

1. CORPUS. v1 read `corpus-preservado-20260908.db`, which holds 60 `memory/lessons.md` chunks
   re-ingested on 2026-09-07 that production never served. v2 reads the corpus that SERVED
   the trial: `corpus-SERVING-REAL-e20260903-recuperado.db` (sha256 23378a9e…, equal to the
   `serving_fd_sha256s` the trial's own trigger logged daily from 09-10 to 09-21).
2. POOL = THE SET THE MECHANISM SEES, CHECKED AS A SET. v1 checked only a COUNT
   (SQL 115 = replay 115). v2 takes the pool ids that the REAL `fetchFreshCandidates`
   returned (`sprint-pool-ids-v2.mjs`) and asserts SET equality with its own SQL
   predicate (same predicate as `src/api/brief.ts`, incl. COALESCE(source_date, created_at)).
   Two routes, one set. On the served corpus that set has 108 chunks (v1: 115).
3. BOOSTABILITY (new; v1 did not check it). `boostsParaCandidatos`
   (`src/paper2/brief-outcome.ts`) gives a bonus ONLY to designated ids that have a
   `p2_verdict` row with severity S1-S4 and `written_at <= epoch_start - 1 day`; the bonus is
   `w * 0.043 * pain(severity)`. A sham chunk with no such row gets bonus 0, so it
   "does not move" BY CONSTRUCTION — the same trap v1's docstring warns about for
   ineligible chunks, one gate further down. Drawing from all 89 non-designated pool
   members would give each sham ~19*36/89 = 7.7 boostable members against the real 19,
   biasing the test toward "real > sham" (the comfortable direction).
   Default mode `impulsionavel`: draw from (pool - real) ∩ boostable, stratified so each
   sham has the SAME severity counts as the real 19 (same total bonus mass at every w).
   Mode `todos` reproduces the literal "89 of the 108-pool" draw, for comparison only;
   its manifest reports the boostable count of every sham.

Nothing is written outside --out. Databases are opened read-only (URI mode=ro) and must be
COPIES (the caller's job; never the /var/backups originals).

Usage (research VPS):
  python3 sprint-gera-shams-v2.py --designacao DESIGNATION-2026-08-26.json \
     --corpus <copy of served corpus> --vivo <copy holding p2_verdict> \
     --pool-json pool-22.json --k 20 --out <dir> [--modo-pool impulsionavel|todos]
"""
import argparse, collections, datetime as dt, hashlib, json, pathlib, random, sqlite3, sys

ap = argparse.ArgumentParser()
ap.add_argument("--designacao", required=True)
ap.add_argument("--corpus", required=True, help="COPY of corpus-SERVING-REAL-e20260903-recuperado.db")
ap.add_argument("--corpus-sha256", required=True, help="expected sha256 of --corpus (full file)")
ap.add_argument("--vivo", required=True, help="COPY of a DB holding p2_verdict")
ap.add_argument("--pool-json", required=True, help="output of sprint-pool-ids-v2.mjs (real-code pool)")
ap.add_argument("--k", type=int, default=20)
ap.add_argument("--out", required=True)
ap.add_argument("--modo-pool", choices=["impulsionavel", "todos"], default="impulsionavel")
ap.add_argument("--pool-esperado", type=int, default=108,
                help="pool size the replay observed on the served corpus (B-replay-fidelity 2.4)")
ap.add_argument("--epoch-inicio-mais-cedo", default="2026-09-01T09:00:00Z",
                help="earliest epoch start of the states the sham will replay (maturity gate)")
ap.add_argument("--seed-prefix", default="p2-sham-v2-2026-10-04")
a = ap.parse_args()

def die(msg):
    print(f"ABORTA: {msg}", file=sys.stderr); sys.exit(2)

def sha_file(p):
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for b in iter(lambda: f.read(1 << 20), b""):
            h.update(b)
    return h.hexdigest()

# --- corpus identity: the whole file, not the first MB ---------------------------------
sc = sha_file(a.corpus)
if sc != a.corpus_sha256:
    die(f"corpus sha256 {sc[:16]}… != expected {a.corpus_sha256[:16]}…")

real = json.loads(pathlib.Path(a.designacao).read_text())
ids_reais = set(real["designados"].values())
chaves = list(real["designados"].keys())
if len(ids_reais) != 19:
    die(f"real designation has {len(ids_reais)} ids, expected 19")

# --- route 1: the real code's pool (set), over the states in --pool-json ---------------
pj = json.loads(pathlib.Path(a.pool_json).read_text())
if pj["procedencia"]["erros"]:
    die(f"pool-json has {pj['procedencia']['erros']} states with error")
estados_pool = [e for e in pj["estados"] if "pool_ids" in e]
uniao, inter = set(pj["uniao_ids"]), set(pj["intersecao_ids"])
if uniao != inter:
    die(f"real-code pool is not constant across the {len(estados_pool)} states "
        f"(union {len(uniao)} vs intersection {len(inter)}): pick states with one pool")
pool_real = inter
ts_ref = min(e["ts"] for e in estados_pool)
ts_ref_max = max(e["ts"] for e in estados_pool)

# --- route 2: SQL predicate, the one src/api/brief.ts:637-646 builds --------------------
con = sqlite3.connect(f"file:{a.corpus}?mode=ro", uri=True)
def pool_sql(ts_iso):
    t = ts_iso.replace("T", " ").replace("Z", "")[:19]
    return {r[0] for r in con.execute("""
        SELECT id FROM chunks
         WHERE (source_file LIKE 'memory/entities/%' ESCAPE '\\' OR source_file LIKE 'memory/lessons.md' ESCAPE '\\')
           AND (COALESCE(importance, 0) >= 0.7 OR COALESCE(pain, 0) >= 0.7)
           AND julianday(?) - julianday(COALESCE(source_date, created_at)) <= 30""", (t,))}
p_sql_min, p_sql_max = pool_sql(ts_ref), pool_sql(ts_ref_max)
con.close()
if not (p_sql_min == p_sql_max == pool_real):
    die(f"SQL predicate != real-code pool: sql@min={len(p_sql_min)} sql@max={len(p_sql_max)} "
        f"real={len(pool_real)}; sql-real={sorted(p_sql_min - pool_real)[:10]} real-sql={sorted(pool_real - p_sql_min)[:10]}")
if len(pool_real) != a.pool_esperado:
    die(f"pool has {len(pool_real)} chunks, expected {a.pool_esperado}")
if not ids_reais <= pool_real:
    die(f"{len(ids_reais - pool_real)} real designated are outside the pool: {sorted(ids_reais - pool_real)}")

# --- boostability: the gate of boostsParaCandidatos, read from p2_verdict ---------------
inicio = dt.datetime.fromisoformat(a.epoch_inicio_mais_cedo.replace("Z", "+00:00"))
corte = (inicio - dt.timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
SEV_PAIN = {"S1": 0.25, "S2": 0.5, "S3": 0.75, "S4": 1.0}
vc = sqlite3.connect(f"file:{a.vivo}?mode=ro", uri=True)
sev = collections.defaultdict(set)
for cid, s in vc.execute("""SELECT chunk_id, severity FROM p2_verdict
                             WHERE chunk_id IS NOT NULL AND severity IN ('S1','S2','S3','S4')
                               AND written_at <= ?""", (corte,)):
    sev[cid].add(s)
p2v_sha = hashlib.sha256("\n".join("|".join("" if x is None else str(x) for x in r) for r in
          vc.execute("SELECT * FROM p2_verdict ORDER BY rowid")).encode()).hexdigest()
vc.close()
multi = {c: s for c, s in sev.items() if len(s) > 1}
if multi:
    # the code applies `set` per row, so the LAST row wins; refuse rather than guess
    die(f"{len(multi)} chunks carry more than one severity in p2_verdict: {list(multi)[:5]}")
sev1 = {c: next(iter(s)) for c, s in sev.items()}
if not all(i in sev1 for i in ids_reais):
    die(f"real designated without a gate-passing p2_verdict row: {sorted(i for i in ids_reais if i not in sev1)}")
sev_real = collections.Counter(sev1[i] for i in ids_reais)

nao_desig = sorted(pool_real - ids_reais)
impuls = [c for c in nao_desig if c in sev1]
if a.modo_pool == "impulsionavel":
    base = impuls
    por_sev = collections.defaultdict(list)
    for c in base:
        por_sev[sev1[c]].append(c)
    for s, n in sev_real.items():
        if len(por_sev[s]) < n:
            die(f"stratum {s}: real has {n}, only {len(por_sev[s])} boostable non-designated available")
else:
    base = nao_desig
if len(base) < 19:
    die(f"sham pool has {len(base)} < 19")

print(f"pool real-code = SQL = {len(pool_real)} | real designated in pool {len(ids_reais & pool_real)} | "
      f"non-designated {len(nao_desig)} | boostable non-designated {len(impuls)} "
      f"{dict(collections.Counter(sev1[c] for c in impuls))} | real severities {dict(sev_real)} | "
      f"mode {a.modo_pool} -> sham pool {len(base)}")

OUT = pathlib.Path(a.out); OUT.mkdir(parents=True, exist_ok=True)
manifesto = []
for i in range(a.k):
    rng = random.Random(int(hashlib.sha256(f"{a.seed_prefix}|{i}".encode()).hexdigest()[:16], 16))
    if a.modo_pool == "impulsionavel":
        escolhidos = []
        for s in sorted(sev_real):                       # deterministic stratum order
            escolhidos += rng.sample(sorted(por_sev[s]), sev_real[s])
    else:
        escolhidos = rng.sample(base, 19)
    if set(escolhidos) & ids_reais or len(set(escolhidos)) != 19:
        die(f"sham {i} overlaps the real designation or repeats ids")
    d = dict(real)
    d["designados"] = {k: v for k, v in zip(chaves, escolhidos)}
    d["designados_ids"] = sorted(escolhidos)
    d["declaracao"] = (f"SHAM v2 {i} — 19 non-designated chunks of the served pool "
                       f"({a.modo_pool}). NOT the trial's designation.")
    d["sha256_do_conjunto"] = hashlib.sha256(",".join(str(x) for x in sorted(escolhidos)).encode()).hexdigest()
    p = OUT / f"SHAM-{i:03d}.json"
    p.write_text(json.dumps(d, indent=2, ensure_ascii=False))
    manifesto.append(dict(i=i, path=p.name, sha_ficheiro=sha_file(p), ids=sorted(escolhidos),
                          impulsionaveis=sum(1 for c in escolhidos if c in sev1),
                          severidades=dict(collections.Counter(sev1.get(c, "sem-p2_verdict") for c in escolhidos)),
                          massa_de_bonus_por_w=round(sum(0.043 * SEV_PAIN.get(sev1.get(c), 0) for c in escolhidos), 6)))

massa_real = round(sum(0.043 * SEV_PAIN[sev1[c]] for c in ids_reais), 6)
over = [len(set(x["ids"]) & set(y["ids"])) for j, x in enumerate(manifesto) for y in manifesto[j + 1:]]
(OUT / "MANIFESTO-SHAMS-v2.json").write_text(json.dumps(dict(
    k=a.k, seed_prefix=a.seed_prefix, modo_pool=a.modo_pool,
    corpus=a.corpus, corpus_sha256=sc, vivo=a.vivo, p2_verdict_sha256_linhas=p2v_sha,
    gate_maturidade_corte=corte,
    pool_json=a.pool_json, pool_estados=len(estados_pool), pool_ts_min=ts_ref, pool_ts_max=ts_ref_max,
    pool=len(pool_real), pool_ids=sorted(pool_real),
    nao_designados=len(nao_desig), impulsionaveis_nao_designados=sorted(impuls),
    severidades_reais=dict(sev_real), massa_de_bonus_real_por_w=massa_real,
    sham_pool=len(base), ids_reais=sorted(ids_reais),
    sobreposicao_par_a_par=dict(min=min(over), max=max(over), media=round(sum(over) / len(over), 3)) if over else None,
    shams=manifesto), indent=2))
print(f"wrote {a.k} shams to {OUT} | overlap with real: 0 | boostable per sham: "
      f"{sorted(collections.Counter(m['impulsionaveis'] for m in manifesto).items())} | "
      f"bonus mass/w real {massa_real} vs shams {sorted(set(m['massa_de_bonus_por_w'] for m in manifesto))}")
