#!/usr/bin/env python3
"""sprint-sham-v2-resumo.py — sprint 2026-10-04, task B-sham-v2.

Recomputes, from artifacts only (no database), every number that
`_sprint-2026-10-04/B-sham-v2/REPORT.md` cites:

  1. which corpus served each state: the `serving_fd_sha256s` that the trial's own trigger
     logged (gatilhos.ndjson), against the sha256 of the preserved copies;
  2. which production states changed (churn > 0) per epoch, and what sonda3's 132 are;
  3. fidelity of the replay on the 22 + 110 states (campo, dose), against production;
  4. the real-code coverage pool (set) on those states, and the sham pools (both modes);
  5. calibration timings and the REAL run's fidelity on the w=4 state set.

Usage:
  python3 sprint-sham-v2-resumo.py --lastro ~/Backups/paper2-ensaio-2026-09-21 \
     --dir _sprint-2026-10-04/B-sham-v2
"""
import argparse, collections, json, os, pathlib, re

ap = argparse.ArgumentParser()
ap.add_argument("--lastro", required=True, help="dir with p2-serving.ndjson and gatilhos.ndjson")
ap.add_argument("--dir", required=True)
ap.add_argument("--corpus-sha256", default="23378a9ea83cd27d0360cfe148207167aee30a376f29ef89d4bcfae415d04131",
                help="sha256 of corpus-SERVING-REAL-e20260903-recuperado.db (p2-bancos-ensaio.sha256)")
ap.add_argument("--preservado-sha256", default="b277bc96d0223a2360ac54ad81f451bf7dea9a05687fceacc6feef194634b47d")
a = ap.parse_args()
L = pathlib.Path(os.path.expanduser(a.lastro)); D = pathlib.Path(a.dir)

# 1. serving fd ---------------------------------------------------------------------------
fd = collections.defaultdict(list); al = collections.Counter()
for line in open(L / "gatilhos.ndjson"):
    try: r = json.loads(line)
    except Exception: continue
    if r.get("serving_fd_sha256s"):
        fd[tuple(r["serving_fd_sha256s"])].append((r["ts"], r.get("serving_fd_n")))
    if r.get("alinhamento_do_serving"):
        al[r["alinhamento_do_serving"].get("motivo")] += 1
for k, v in fd.items():
    print(f"[fd] sha={[x[:16] for x in k]} readings={len(v)} first={min(v)[0]} last={max(v)[0]} "
          f"fd_n={sorted(set(x[1] for x in v))} equals_served_copy={list(k) == [a.corpus_sha256]} "
          f"equals_preservado={list(k) == [a.preservado_sha256]}")
print(f"[fd] alinhamento_do_serving motives: {dict(al)}")

# 2. production states ----------------------------------------------------------------------
prod = {}; churn_ep = collections.Counter(); st_ep = collections.Counter()
for line in open(L / "p2-serving.ndjson"):
    if not line.strip(): continue
    r = json.loads(line)
    if r.get("tag") != "p2_outcome" or len(r.get("ids_controle") or []) != 10: continue
    prod[(r["ts"], r.get("agent"))] = r
    k = (r["epoch"], r["modo"], r["w"]); st_ep[k] += 1
    if (r.get("churn") or 0) > 0: churn_ep[k] += 1
print(f"[prod] states={len(prod)}")
print("[prod] churn>0 per (epoch, modo, w), trial only: " +
      ", ".join(f"{k[0]}/w{k[2]}:{v}" for k, v in sorted(churn_ep.items()) if k[1] == "active"))
w4 = {k: v for k, v in churn_ep.items() if k[1] == "active" and k[2] == 4}
print(f"[prod] churn>0 in w=4 epochs: {sum(w4.values())} (= sonda3's 132 if equal); "
      f"churn>0 in all active epochs: {sum(v for k, v in churn_ep.items() if k[1] == 'active')}")
print(f"[prod] states in w=4 active epochs: {sum(v for k, v in st_ep.items() if k[1]=='active' and k[2]==4)}; "
      f"active states with ts in [2026-09-03T17:23:30Z, 2026-09-21T09:00Z): "
      f"{sum(1 for (ts, _), r in prod.items() if r['modo']=='active' and '2026-09-03T17:23:30Z' <= ts < '2026-09-21T09:00:00Z')}")

# 3. fidelity 22 / 110 ----------------------------------------------------------------------
F = D / "fidelity-110"
for n in ("22", "110"):
    c = json.load(open(F / f"out-campo-{n}.json"))["campo"]
    b = sum(1 for x in c["detalhe"] if x.get("boosts_emitidos") == x.get("producao", {}).get("boosts"))
    print(f"[campo-{n}] replayed={c['replayados']} errors={c['erros']} control={c['bate_controle']} "
          f"churn={c['bate_churn']} enter={c['bate_entra']} boosts==prod={b}")
d = json.load(open(F / "out-dose-110.json"))["dose"]
for w in (2, 4, 100000):
    xs = [x for x in d["detalhe"] if x["w"] == w]
    ctl = sum(1 for x in xs if x["ids_controle_replay"] == prod[(x["ts"], x["agent"])]["ids_controle"])
    eq = sum(1 for x in xs if x["churn"] == prod[(x["ts"], x["agent"])]["churn"]
             and sorted(x["would_enter"]) == sorted(prod[(x["ts"], x["agent"])]["would_enter"]))
    print(f"[dose-110] w={w} states={len(xs)} moved={sum(1 for x in xs if x['churn'] > 0)} "
          f"churn_total={sum(x['churn'] for x in xs)} control==prod={ctl} churn&enter==prod={eq} "
          f"errors={sum(1 for x in xs if x.get('erro'))}")
print(f"[dose-110] positive control: {d['controle_positivo']['veredito']}")

# 4. pools ---------------------------------------------------------------------------------
for n in ("22", "110"):
    p = json.load(open(F / f"pool-{n}.json"))
    print(f"[pool-{n}] states={p['procedencia']['estados']} errors={p['procedencia']['erros']} "
          f"union={len(p['uniao_ids'])} intersection={len(p['intersecao_ids'])} "
          f"sizes={dict(collections.Counter(e['pool'] for e in p['estados']))}")
for modo in ("impulsionavel", "todos"):
    m = json.load(open(D / f"shams-{modo}" / "MANIFESTO-SHAMS-v2.json"))
    print(f"[shams-{modo}] pool={m['pool']} non_designated={m['nao_designados']} "
          f"boostable_non_designated={len(m['impulsionaveis_nao_designados'])} sham_pool={m['sham_pool']} "
          f"real_sev={m['severidades_reais']} real_mass/w={m['massa_de_bonus_real_por_w']} "
          f"boostable_per_sham={sorted(collections.Counter(s['impulsionaveis'] for s in m['shams']).items())} "
          f"mass/w range=[{min(s['massa_de_bonus_por_w'] for s in m['shams'])}, {max(s['massa_de_bonus_por_w'] for s in m['shams'])}] "
          f"pairwise_overlap={m['sobreposicao_par_a_par']}")

# 5. calibration ---------------------------------------------------------------------------
C = D / "calibration"
def tempo(p):
    t = p.read_text()
    g = lambda pat: re.search(pat, t).group(1)
    return dict(user=float(g(r"User time \(seconds\): ([\d.]+)")), sys=float(g(r"System time \(seconds\): ([\d.]+)")),
                wall=g(r"Elapsed \(wall clock\) time \(h:mm:ss or m:ss\): ([\d:.]+)"),
                rss_kb=int(g(r"Maximum resident set size \(kbytes\): (\d+)")))
def secs(s):
    parts = [float(x) for x in s.split(":")]
    return sum(v * 60 ** i for i, v in enumerate(reversed(parts)))
for nome in ("REAL-1", "REAL-amostra200", "REAL-w4"):
    p = C / f"{nome}.time"
    if not p.exists() or not p.read_text().strip():
        print(f"[cal] {nome}: NOT MEASURED (no timing file)"); continue
    tsf = {"REAL-1": "ts-1.txt", "REAL-amostra200": "ts-janela-amostra200.txt", "REAL-w4": "ts-w4.txt"}[nome]
    t = tempo(p); n = len([l for l in open(C / tsf) if l.strip()])
    print(f"[cal] {nome}: states={n} wall={t['wall']} ({secs(t['wall']):.0f}s) cpu={t['user']+t['sys']:.0f}s "
          f"(user {t['user']:.0f} sys {t['sys']:.0f}) rss={t['rss_kb']//1024}MB "
          f"wall/state={secs(t['wall'])/n:.3f}s")
fj = C / "REAL-w4.resumo.json"
if fj.exists():
    r = json.load(open(fj))
    print(f"[cal] REAL-w4 run: {json.dumps(r['run'])}")
    print(f"[cal] REAL-w4 fidelity: {json.dumps({k: v for k, v in r['fidelidade_real'].items() if k != 'primeiras_divergencias'})}")
    print(f"[cal] REAL-w4 first divergences: {r['fidelidade_real']['primeiras_divergencias'][:10]}")
