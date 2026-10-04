#!/usr/bin/env python3
"""sprint-resume-sham-v2.py — reads the output of `sprint-roda-sham-v2.sh` (sprint 2026-10-04,
task B-sham-v2) and computes the specificity test. It REFUSES to compute anything about the
shams unless the job says CONCLUIDO and every promoted output matches the hash the runner
recorded: a partial job is not a negative result, it is no result.

Two modes:
  --job <dir>          the sham job (REAL + K shams). Exit 3 if not CONCLUIDO.
  --real-only <json>   one REAL dose run (the calibration). Reports fidelity against
                       production and dose response; says nothing about specificity.

Statistic (pre-committed shape, SPEC-ANALISE §5 / MANUSCRIPT-B §4.0.1b): for each run, the
number of states the dose moved (`mexeu`, churn > 0) and the total churn, at the
registered w = 4. Randomization p = (1 + #{sham >= real}) / (K + 1); with K = 20 the smallest
attainable p is 1/21 = 0.048. w = 100000 is the positive control, reported, never tested.

Fidelity of the REAL run against production (`p2-serving.ndjson`), per state:
  - control set: replay `ids_controle_replay` == production `ids_controle` (ordered), all states;
  - at production's own w (states where production served w = 4): churn and the sorted
    `would_enter` equal production's.

Usage:
  python3 sprint-resume-sham-v2.py --log p2-serving.ndjson --job <job dir> [--json out.json]
  python3 sprint-resume-sham-v2.py --log p2-serving.ndjson --real-only REAL-w4.json
"""
import argparse, collections, hashlib, json, os, pathlib, sys

ap = argparse.ArgumentParser()
ap.add_argument("--log", required=True)
g = ap.add_mutually_exclusive_group(required=True)
g.add_argument("--job")
g.add_argument("--real-only")
ap.add_argument("--w", type=float, default=4.0)
ap.add_argument("--w-absurdo", type=float, default=100000.0)
ap.add_argument("--json")
a = ap.parse_args()

prod = {}
for line in open(os.path.expanduser(a.log)):
    if line.strip():
        r = json.loads(line)
        if r.get("tag") == "p2_outcome" and len(r.get("ids_controle") or []) == 10:
            prod[(r["ts"], r.get("agent"))] = r

def resumo_run(d):
    det = d["dose"]["detalhe"]
    out = {}
    for w in (a.w, a.w_absurdo):
        xs = [x for x in det if float(x["w"]) == w and not x.get("erro")]
        out[str(w)] = dict(estados=len(xs), mexeu=sum(1 for x in xs if (x.get("churn") or 0) > 0),
                           churn_total=sum(x.get("churn") or 0 for x in xs),
                           boosts=dict(collections.Counter(x.get("boosts_emitidos") for x in xs)))
    out["erros"] = sum(1 for x in det if x.get("erro"))
    return out

def fidelidade(d):
    det = [x for x in d["dose"]["detalhe"] if float(x["w"]) == a.w and not x.get("erro")]
    n = ctl = nw = eq = 0
    por_dia = collections.defaultdict(lambda: [0, 0])
    falhas = []
    for x in det:
        p = prod.get((x["ts"], x.get("agent")))
        if p is None:
            falhas.append((x["ts"], "ausente do log")); continue
        n += 1
        ok_c = x.get("ids_controle_replay") == p["ids_controle"]
        ctl += ok_c
        por_dia[p["epoch"]][0] += 1; por_dia[p["epoch"]][1] += ok_c
        if float(p.get("w") or 0) == a.w and p.get("modo") == "active":
            nw += 1
            ok = (x.get("churn") == p.get("churn")
                  and sorted(x.get("would_enter") or []) == sorted(p.get("would_enter") or []))
            eq += ok
            if not (ok and ok_c) and len(falhas) < 20:
                falhas.append((x["ts"], f"controle={ok_c} churn r/p={x.get('churn')}/{p.get('churn')}"))
        elif not ok_c and len(falhas) < 20:
            falhas.append((x["ts"], "controle diverge"))
    return dict(estados=n, controle_igual=ctl, estados_com_w_de_producao=nw,
                churn_e_entra_iguais=eq, controle_por_epoch={k: f"{v[1]}/{v[0]}" for k, v in sorted(por_dia.items())},
                primeiras_divergencias=falhas)

res = {}
if a.real_only:
    d = json.load(open(a.real_only))
    res = dict(modo="real-only (calibracao; NAO e resultado de especificidade)",
               arquivo=a.real_only, run=resumo_run(d), fidelidade_real=fidelidade(d))
else:
    J = pathlib.Path(a.job)
    status = (J / "STATUS").read_text().split() if (J / "STATUS").exists() else ["AUSENTE"]
    if status[0] != "CONCLUIDO" or not (J / "CONCLUIDO").exists():
        print(f"INCOMPLETO: STATUS={' '.join(status)}; CONCLUIDO={'sim' if (J / 'CONCLUIDO').exists() else 'nao'}. "
              "Corrida incompleta NAO e resultado negativo. Nada calculado.")
        sys.exit(3)
    esperado = {}
    for line in (J / "CONCLUIDO").read_text().splitlines():
        h, nome = line.split(maxsplit=1)
        esperado[nome.strip().lstrip("*")] = h
    runs = {}
    for nome, h in esperado.items():
        p = J / "runs" / nome
        if hashlib.sha256(p.read_bytes()).hexdigest() != h:
            print(f"INCOMPLETO: {nome} nao confere com CONCLUIDO. Nada calculado."); sys.exit(3)
        runs[nome[:-5]] = json.load(open(p))
    if "REAL" not in runs:
        print("INCOMPLETO: sem REAL. Nada calculado."); sys.exit(3)
    shams = sorted(k for k in runs if k.startswith("SHAM-"))
    K = len(shams)
    R = {k: resumo_run(v) for k, v in runs.items()}
    w = str(a.w)
    teste = {}
    for m in ("mexeu", "churn_total"):
        real = R["REAL"][w][m]
        ge = sum(1 for s in shams if R[s][w][m] >= real)
        teste[m] = dict(real=real, shams=sorted(R[s][w][m] for s in shams), shams_ge_real=ge,
                        p=round((1 + ge) / (K + 1), 4))
    res = dict(modo="job", job=str(J), status=" ".join(status), K=K, w=a.w, teste=teste,
               controle_positivo={k: R[k][str(a.w_absurdo)]["mexeu"] for k in ["REAL"] + shams},
               por_run=R, fidelidade_real=fidelidade(runs["REAL"]))

txt = json.dumps(res, indent=1, ensure_ascii=False)
print(txt)
if a.json:
    pathlib.Path(a.json).write_text(txt + "\n")
