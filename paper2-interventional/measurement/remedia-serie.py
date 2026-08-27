import json, hashlib, collections
from math import sqrt

L = "/root/.openclaw/logs/p2-serving.ndjson"
REGRA = "2026-08-26T20:28:00Z"     # drop-in da designacao
T_FIM = "2026-08-27T09:00:00Z"     # <<< JANELA FECHADA, declarada
GATE  = "2026-08-23"               # epoch minimo p/ base comparavel (regra velha)

raw = open(L, "rb").read()
linhas = [l for l in raw.decode().splitlines() if l.strip()]
rows = [json.loads(l) for l in linhas]
print("=== procedencia da janela ===")
print("arquivo        : %s" % L)
print("sha256         : %s" % hashlib.sha256(raw).hexdigest())
print("bytes / linhas : %d / %d" % (len(raw), len(linhas)))
print("ts min / max   : %s .. %s" % (rows[0]["ts"], rows[-1]["ts"]))
print("janela FECHADA : [%s , %s)" % (REGRA, T_FIM))

def wilson(k, n, z=1.959963985):
    if n == 0: return (0.0, 0.0)
    p = k/n; d = 1 + z*z/n; c = p + z*z/(2*n)
    h = z*sqrt(p*(1-p)/n + z*z/(4*n*n))
    return ((c-h)/d, (c+h)/d)

def eh_sonda(r):
    a = r.get("agent")
    return a is None or a == "" or a == "null"

dep = [r for r in rows if REGRA <= r["ts"] < T_FIM]
ant = [r for r in rows if r["ts"] < REGRA and r.get("epoch", "") >= GATE]

print()
print("=== quem decide, na janela pos-regra (n=%d) ===" % len(dep))
for a, c in collections.Counter(r.get("agent") or "<null/vazio>" for r in dep).most_common():
    sub = [r for r in dep if (r.get("agent") or "<null/vazio>") == a]
    ch = sum(1 for r in sub if r.get("churn", 0) > 0)
    print("  %-16s n=%-5d com_churn=%-4d %6.2f%%" % (a, len(sub), ch, 100*ch/len(sub)))

def bloco(sub, nome):
    n = len(sub); k = sum(1 for r in sub if r.get("churn", 0) > 0)
    if n == 0: print("  %-40s vazio" % nome); return (k, n)
    lo, hi = wilson(k, n)
    print("  %-40s %3d/%-4d = %7.4f%%  Wilson [%.2f; %.2f]" % (nome, k, n, 100*k/n, 100*lo, 100*hi))
    return (k, n)

print()
print("=== REGRA NOVA, janela fechada ===")
tudo   = bloco(dep, "todas as decisoes")
sondas = [r for r in dep if eh_sonda(r)]
limpo  = bloco([r for r in dep if not eh_sonda(r)], "excluindo decisoes sem agent")
bloco(sondas, "so as decisoes sem agent")
print()
print("=== REGRA VELHA (pos-gate, ate a regra), para comparacao ===")
velha = bloco(ant, "velha, todas")
bloco([r for r in ant if not eh_sonda(r)], "velha, excluindo sem agent")

print()
print("=== por hora, regra nova, janela fechada, so agent presente ===")
por = collections.defaultdict(lambda: [0, 0])
for r in dep:
    if eh_sonda(r): continue
    h = r["ts"][:13]; por[h][0] += 1
    if r.get("churn", 0) > 0: por[h][1] += 1
soma_n = soma_k = 0
for h in sorted(por):
    n, k = por[h]; soma_n += n; soma_k += k
    print("  %sZ  n=%-4d churn=%-3d %6.2f%%" % (h, n, k, 100*k/n))
print("  SOMA das horas: %d/%d  (tem de bater com o bloco 'excluindo': %d/%d)  ok=%s"
      % (soma_k, soma_n, limpo[0], limpo[1], (soma_k, soma_n) == limpo))
