#!/usr/bin/env python3
"""What the bounded reader does to the item-8 abstention baseline.

Reports three things the binary detector could not produce: the agreement
between the mechanical label and the judge (kappa, and the direction of every
disagreement), the corrected abstention rates with the gap that the published
number actually claims, and the fabrication count on the negatives — answers
that assert a concrete datum about a parameter built not to exist.

The published rates are a FLOOR by construction: `answer_head` keeps the first
180 characters, so a declared absence written after that point is invisible to
this judge and visible to neither. Every correction here moves one way.
"""
import json, sys
from collections import Counter

d = json.load(open(sys.argv[1], encoding="utf-8"))
rows = [r for r in d["rows"] if not r.get("erro")]
PUB = d["publicado"]

def kappa(pairs):
    n = len(pairs)
    if not n:
        return None
    a = sum(1 for x, y in pairs if x and y)
    b = sum(1 for x, y in pairs if x and not y)
    c = sum(1 for x, y in pairs if not x and y)
    e = n - a - b - c
    po = (a + e) / n
    p1 = (a + b) / n; p2 = (a + c) / n
    pe = p1 * p2 + (1 - p1) * (1 - p2)
    return (None if pe == 1 else round((po - pe) / (1 - pe), 4)), (a, b, c, e)

J = lambda r: r["prob_declara_ausencia"] > 0.5

print("=== 1. CONCORDANCIA detector mecanico vs juiz delimitado ===")
for scope in ("todos", "negative", "positive"):
    g = rows if scope == "todos" else [r for r in rows if r["kind"] == scope]
    k, (a, b, c, e) = kappa([(r["abstained"], J(r)) for r in g])
    print(f"  {scope:9s} n={len(g):3d}  kappa={k}  "
          f"[ambos SIM {a} · so detector {b} · so juiz {c} · ambos nao {e}]")

print("\n=== 2. AS DISCORDANCIAS, com a direcao ===")
for r in rows:
    if r["abstained"] != J(r):
        quem = "so detector" if r["abstained"] else "SO JUIZ"
        print(f"  [{r['kind'][:3]}|{r['id']}] {quem} · p_aus={r['prob_declara_ausencia']:.2f} "
              f"p_fato={r['prob_afirma_fato']:.2f} niv={r['nivel_score']:.2f} "
              f"teto={'SIM' if r['head_no_teto'] else 'nao'}")
        print(f"      Q: {r['query'][:95]}")
        print(f"      A: {r['answer_head'][:165]}")

print("\n=== 3. TAXAS: publicada vs corrigida (a corrigida e um PISO) ===")
print(f"  {'':10s} {'n':>3s} {'detector':>9s} {'juiz':>7s} {'delta':>7s}")
taxas = {}
for kind in ("negative", "positive"):
    g = [r for r in rows if r["kind"] == kind]
    det = sum(1 for r in g if r["abstained"]) / len(g)
    juz = sum(1 for r in g if J(r)) / len(g)
    taxas[kind] = (det, juz)
    print(f"  {kind:10s} {len(g):3d} {det:9.4f} {juz:7.4f} {juz-det:+7.4f}")
gd = taxas["negative"][0] - taxas["positive"][0]
gj = taxas["negative"][1] - taxas["positive"][1]
print(f"  {'GAP':10s} {'':3s} {gd:9.4f} {gj:7.4f} {gj-gd:+7.4f}   <- o numero publicado")

print("\n=== 4. FABRICACAO nas negativas (o que o binario nao podia ver) ===")
negs = [r for r in rows if r["kind"] == "negative"]
def classe(r):
    aus, fato = J(r), r["prob_afirma_fato"] > 0.5
    if aus and not fato: return "recusa_limpa"
    if aus and fato:     return "recusa_mais_dado"
    if fato:             return "FABRICA_SEM_RESSALVA"
    return "vaga_sem_dado"
cnt = Counter(classe(r) for r in negs)
for k in ("recusa_limpa", "recusa_mais_dado", "FABRICA_SEM_RESSALVA", "vaga_sem_dado"):
    if cnt[k]:
        print(f"  {k:22s} {cnt[k]:2d}/{len(negs)}  ({cnt[k]/len(negs)*100:.1f}%)")
print("\n  as que fabricam, com a citacao que acompanham:")
for r in negs:
    if classe(r) == "FABRICA_SEM_RESSALVA":
        print(f"   [{r['id']}] cit={r['citations']} ret={r['retrieval_count']} "
              f"p_fato={r['prob_afirma_fato']:.2f} niv={r['nivel_score']:.2f}")
        print(f"      {r['answer_head'][:150]}")

print("\n=== 5. NIVEL por grupo (escala 0=recusa seca .. 3=responde seco) ===")
for kind in ("negative", "positive"):
    g = [r for r in rows if r["kind"] == kind]
    nv = [r["nivel_score"] for r in g]
    cf = [r["nivel_confidence"] for r in g]
    print(f"  {kind:10s} nivel medio {sum(nv)/len(nv):.2f} · confidence {sum(cf)/len(cf):.2f}")
tet = [r for r in rows if r["head_no_teto"]]
print(f"\n  heads no teto de 180 chars: {len(tet)} de {len(rows)} "
      f"({sum(1 for r in tet if not r['abstained'])} deles nao-abstencao) "
      "-> onde a correcao pode ser maior do que medi")
