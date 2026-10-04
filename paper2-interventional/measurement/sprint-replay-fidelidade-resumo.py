#!/usr/bin/env python3
"""sprint-replay-fidelidade-resumo.py — sprint 2026-10-04, task "B-replay-fidelity".

Recomputes, from artifacts only (no database), every number the report
`_sprint-2026-10-04/B-replay-fidelity.md` cites:

  1. sonda3 (out/NOGO-replay-sonda3-2026-09-23.json) against the production log
     (p2-serving.ndjson): does the replay's CONTROL set equal production's in the
     132 states? Which ids does the replay put where production put others?
  2. the production log alone: was any chunk id above the frozen served corpus'
     MAX(id) = 308752 ever served before the end of the trial?
  3. the 8 replay runs + 2 stratum runs of this sprint (B-replay-fidelity/*.json):
     fidelity (campo) and dose response (dose) per corpus x cut, and whether the
     stand-in serve-state (brief_log of corpus-preservado) reproduces sonda3's
     controls on the 22 states it covers.

Usage:
  python3 sprint-replay-fidelidade-resumo.py \
     --log ~/Backups/paper2-ensaio-2026-09-21/p2-serving.ndjson \
     --sonda3 out/NOGO-replay-sonda3-2026-09-23.json \
     --dir _sprint-2026-10-04/B-replay-fidelity
"""
import argparse, collections, json, os, statistics as st

ap = argparse.ArgumentParser()
ap.add_argument("--log", required=True)
ap.add_argument("--sonda3", required=True)
ap.add_argument("--dir", required=True)
ap.add_argument("--max-id-servido", type=int, default=308752,
                help="MAX(chunks.id) of corpus-SERVING-REAL-e20260903-recuperado.db, measured 2026-10-04")
a = ap.parse_args()

prod = collections.defaultdict(list)
n_lines = 0
served_above = {}
for line in open(os.path.expanduser(a.log)):
    line = line.strip()
    if not line:
        continue
    r = json.loads(line)
    n_lines += 1
    for x in set(r.get("ids_controle") or []) | set(r.get("ids_tratado") or []):
        if x > a.max_id_servido and x not in served_above:
            served_above[x] = r["ts"]
    if r.get("tag") == "p2_outcome" and len(r.get("ids_controle") or []) == 10:
        prod[r["ts"]].append(r)

print(f"[log] lines={n_lines}")
print(f"[log] distinct ids > {a.max_id_servido} ever served: {len(served_above)}; "
      f"earliest serve of any: {min(served_above.values()) if served_above else None}")

s3 = json.load(open(a.sonda3))
det = [d for d in s3["dose"]["detalhe"] if d["w"] == 4]
assert all(len(prod[d["ts"]]) == 1 for d in det), "ambiguous ts in log"
ovl = collections.Counter(); eq = 0; fresh_hit = collections.Counter()
only_rep = collections.Counter(); enter_in = leave_in = 0
for d in det:
    p = prod[d["ts"]][0]
    rep, pc = d["ids_controle_replay"], p["ids_controle"]
    eq += set(rep) == set(pc)
    ovl[len(set(rep) & set(pc))] += 1
    fresh_hit[sum(x in rep for x in p["fresh_added"])] += 1
    only_rep.update(x for x in rep if x not in pc)
    enter_in += any(x in rep for x in p["would_enter"])
    leave_in += any(x in rep for x in p["would_leave"])
print(f"[sonda3] states={len(det)} control==production (as set): {eq}")
print(f"[sonda3] |replay ∩ production| distribution: {dict(sorted(ovl.items()))}")
print(f"[sonda3] production fresh_added ids found in replay control: {dict(sorted(fresh_hit.items()))}")
print(f"[sonda3] ids in replay control but not in production control: {only_rep.most_common()}")
print(f"[sonda3] states where production's would_enter / would_leave id is in replay control: {enter_in} / {leave_in}")
print(f"[sonda3] states by day: {dict(sorted(collections.Counter(d['ts'][:10] for d in det).items()))}")

# stand-in check: campo-preservado-inclusivo must reproduce sonda3's replay controls
s3c = {d["ts"]: d["ids_controle_replay"] for d in det}
c = json.load(open(os.path.join(a.dir, "out-campo-preservado-inclusivo.json")))["campo"]["detalhe"]
same = sum(1 for x in c if x["ids_controle_replay"] == s3c[x["ts"]])
print(f"[stand-in] campo-preservado-inclusivo control == sonda3 control (ordered): {same}/{len(c)}")

for corpus in ("preservado", "servido"):
    for cut in ("inclusivo", "rowid"):
        cf = json.load(open(os.path.join(a.dir, f"out-campo-{corpus}-{cut}.json")))["campo"]
        df = json.load(open(os.path.join(a.dir, f"out-dose-{corpus}-{cut}.json")))["dose"]
        ws = sorted({x["w"] for x in cf["detalhe"]})
        print(f"[run] corpus={corpus:10s} cut={cut:9s} campo(w={ws}): control {cf['bate_controle']}/{cf['replayados']} "
              f"churn {cf['bate_churn']}/{cf['replayados']} enter {cf['bate_entra']}/{cf['replayados']} | dose: "
              + "; ".join(f"w={t['w']}: moved {t['mexeu']}/{t['estados']} (churn {t['churn_total']}, boosts {t['boosts']})"
                          for t in df["tabela"]))

for corpus in ("servido", "preservado"):
    e = json.load(open(os.path.join(a.dir, f"estratos-{corpus}.json")))
    for cut in ("rowid", "estrito", "inclusivo"):
        xs = [x["por_corte"][cut] for x in e["detalhe"] if "erro" not in x["por_corte"][cut]]
        med = lambda k: (min(x[k] for x in xs), st.median(x[k] for x in xs), max(x[k] for x in xs))
        fr = [x["estrato_fronteira"]["tamanho"] for x in xs]
        hist = collections.Counter()
        for x in xs:
            for k, v in x["histograma_tamanho_estrato"].items():
                hist[int(k)] += v
        print(f"[strata] corpus={corpus:10s} cut={cut:9s} n={len(xs)} pool={med('pool')} never_served={med('nunca_servidos')} "
              f"strata={med('estratos')} singletons={med('estratos_singleton')} boundary_size(min,med,max)=({min(fr)},{st.median(fr)},{max(fr)}) "
              f"boundary_NULL={sum(x['estrato_fronteira']['last_served'] is None for x in xs)} "
              f"states_with_designated_in_boundary={sum(x['designados_no_estrato_fronteira'] > 0 for x in xs)} "
              f"first_designated_pos={med('posicao_primeiro_designado')} enter_ties_leave={sum(x['entra_empata_com_sai'] for x in xs)} "
              f"stratum_size_hist={dict(sorted(hist.items()))}")
