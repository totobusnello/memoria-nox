"""As shares são por (episódio, painelista) com veredito failure? Reproduzir n=3812."""
import json, collections, glob
from pathlib import Path
V = Path("/Users/lab/.paper2-verdicts")
ALVO = {"S1": 0.6973, "S2": 0.2962, "S3": 0.0058, "S4": 0.0008}

def carregar(p):
    for ln in p.read_text().splitlines():
        ln = ln.strip()
        if not ln: continue
        try: yield json.loads(ln)
        except: pass

def contar(paths):
    vistos = {}
    for p in paths:
        for r in carregar(p):
            ep = r.get("episode_id") or r.get("episode") or r.get("id")
            pan = r.get("panelist") or r.get("provider") or r.get("model")
            est = (r.get("estado") or r.get("state") or r.get("verdict") or "")
            sev = r.get("severity") or r.get("severidade")
            if not ep or not pan: continue
            if str(est).lower() != "failure": continue
            if not sev or str(sev) not in ("S1","S2","S3","S4"): continue
            vistos[(ep, pan)] = str(sev)          # dedupe por (episode, panelist)
    return vistos

grupos = {
  "combinado-v2":      [V/"verdicts-combinado-v2.jsonl"],
  "combinado":         [V/"verdicts-combinado.jsonl"],
  "extensao-full-v2":  [V/"verdicts-extensao-full-v2.jsonl"],
  "extensao-full":     [V/"verdicts-extensao-full.jsonl"],
  "peca3-pass1":       [V/"peca3-pass1.jsonl"],
  "TODOS os verdicts": sorted(V.glob("verdicts-*.jsonl")),
  "TODOS os jsonl":    sorted(V.glob("*.jsonl")),
}
print(f"{'grupo':22} {'n':>6}  distribuição                                   Δ")
for nome, paths in grupos.items():
    v = contar([p for p in paths if p.exists()])
    n = len(v)
    if not n: print(f"{nome:22} {0:>6}  (vazio)"); continue
    c = collections.Counter(v.values())
    d = {k: round(c[k]/n, 4) for k in ("S1","S2","S3","S4") if c[k]}
    delta = sum(abs(d.get(k,0.0)-x) for k,x in ALVO.items())
    marca = "  <=== BATE" if delta < 0.002 else ("  <-- n=3812!" if n==3812 else "")
    print(f"{nome:22} {n:>6}  {str(d):46} {delta:.4f}{marca}")
