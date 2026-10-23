#!/usr/bin/env python3
"""Apply the four adjudicated principles to all 150 S1 rows and recompute.

On 2026-10-23 four rows of the blind sample were still in dispute between the
first judge (`gemini-2.5-flash-lite` plus a mechanical citation check) and the
second reader. None of the four was a disagreement about what the text says.
All four were policy questions about what counts as "supports", and the owner
settled them:

  P1  a triple that INVERTS the relation does not support it, even when the
      quote is verbatim and the two entities sit side by side
  P2  a predicate that is IMPOVERISHED but not inverted does support it
  P3  a placeholder inside a worked example is not an entity
  P4  formatting does not reject: the citation check drops all punctuation

P4 is mechanical and applies to all 150 at once. P1 and P3 are semantic; this
file ENUMERATES the rows each one reaches, by marker, and the enumeration is
then read. P2 cannot be enumerated that way at all: the judge that rejected a
row returns an empty quote, and an empty quote leaves nothing to check — so the
13 rows the new criterion excludes are read one by one instead.

⚠️  Re-reading only the REJECTED rows is asymmetric: it can only move the
number up. That is why the `substantive` line below is reported as a declared
ceiling, never as the estimate. See the audit for what is left of the
population correction.

Usage: 2026-10-23-kg-s1-quatro-principios.py [rows.json] [nox-mem.db]
The per-triple rows stay on the host: 82.2% of the graph's evidence is vault
material and this repository is public.
"""
import json, math, re, sqlite3, sys, unicodedata

ROWS = sys.argv[1] if len(sys.argv) > 1 else "/root/medicoes/2026-10-22-kg-s1/s1-rows-recheck.json"
DB   = sys.argv[2] if len(sys.argv) > 2 else "/root/.openclaw/workspace/tools/nox-mem/nox-mem.db"
SAMPLE = "/root/medicoes/2026-10-22-kg-s1/meus-vereditos.json"
MIN = 12

def _acc(s):
    s = unicodedata.normalize("NFKD", s or "")
    return "".join(c for c in s if not unicodedata.combining(c))

_Q = dict.fromkeys(map(ord, "“”‘’«»"), '"')
_D = dict.fromkeys(map(ord, "–—−"), "-")

def n_markdown(s):
    """Markup-insensitive. The 2026-10-23 criterion, kept for the mutation."""
    s = _acc(s or "").translate(_Q).translate(_D)
    s = re.sub(r"<[^>\n]{1,24}>", " ", s)
    s = re.sub(r"\\(.)", r"\1", s)
    s = re.sub(r"[*_`#>|~]+", " ", s)
    s = re.sub(r"\s+", " ", s).strip().lower()
    s = re.sub(r'\s+([,.;:!?)\]"])', r"\1", s)
    s = re.sub(r'(["(\[])\s+', r"\1", s)
    return s.strip()

def n_alnum(s):
    """P4: markup-insensitive plus every punctuation mark dropped."""
    return re.sub(r"\s+", " ", re.sub(r"[^0-9a-z ]+", " ", n_markdown(s))).strip()

def casa(norm, quote, text):
    q = norm(quote)
    return len(q) >= MIN and q in norm(text)

def wilson(k, n, z=1.96):
    if n == 0:
        return (0.0, 0.0)
    p, d = k / n, 1 + z * z / n
    c = (p + z * z / (2 * n)) / d
    h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return (max(0.0, c - h), min(1.0, c + h))

# --- the rows each principle reaches, and the MECHANISM that puts it there ---
# Named by structure, not by content: the entity names are vault material.
P1_OUT = {"kg-25584": "the object is the clause the sentence EXCEPTS, so the triple "
                      "asserts the negation of what the text asserts"}
P3_OUT = {"kg-23810": "subject and object are placeholders inside a quoted example "
                      "question, read as entities"}
P2_IN = {
    "kg-27871": "the predicate is the sentence's own verb, applied to the object the "
                "sentence names; the judge's stated reason (the object is absent) is "
                "false against the full chunk",
    "kg-25631": "the triple drops the AGENT of an indemnity and keeps beneficiary, "
                "predicate and subject matter — omission, not inversion",
    "kg-28707": "a passive requirement is attributed to the party it binds, and the "
                "object is the thing the requirement acts on rather than the action "
                "(MARGINAL: the weakest of the four)",
    "kg-28721": "the chunk's tail carries the causative verb twice, governing the "
                "object entity; the predicate is poor, not reversed",
}
P2_OUT = {
    "kg-25874": "the object of the guarantee is a third entity, not the subject - "
                "fabricated object, not an impoverished one",
    "kg-30551": "the text states the conduct did NOT occur - inversion (P1)",
    "kg-33485": "the text states nothing shall be construed as the triple's predicate "
                "- inversion (P1)",
    "kg-39677": "the two entities are alternatives joined by OR; the triple asserts "
                "subsumption",
    "kg-24670": "the text marks the asserted fact as FALSE - inversion (P1)",
    "kg-32180": "the clause defines requirements for a different body than the object",
    "kg-41383": "subject and object sit in two different lists of one sentence - "
                "adjacency, not relation",
    "kg-27774": "sender and recipient are swapped - inversion (P1)",
    "kg-33996": "the predicate is a noun standing in for a verb; it asserts no "
                "checkable relation",
}
EXC = re.compile(r"\b(exceto|salvo|ressalvad\w+|except|unless|other than)\b", re.I)
EX  = re.compile(r"(^|[\s(\[\"'])(ex\.?:|e\.g\.|por exemplo|for example|exemplo:)", re.I)

rows = json.load(open(ROWS))
db = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
texto = {}
for r in rows:
    cid = r.get("evidence_chunk_id")
    if cid and cid not in texto:
        got = db.execute("SELECT chunk_text FROM chunks WHERE id=?", (cid,)).fetchone()
        texto[cid] = got[0] if got else ""

def rid(r): return f"kg-{r['relation_id']}"
byid = {rid(r): r for r in rows}
n = len(rows)

def confere(i, norm=n_alnum):
    r = byid[i]
    return casa(norm, r.get("citacao") or "", texto.get(r.get("evidence_chunk_id"), ""))

def juiz(i): return bool(byid[i].get("sustenta_segundo_juiz"))

aceita_p4 = {i for i in byid if juiz(i) and confere(i)}

print("=" * 76)
print("OS 150 COM OS QUATRO PRINCIPIOS APLICADOS")
print("=" * 76)
passos = [
    ("P4 so (criterio alfanumerico)", len(aceita_p4)),
    ("  - P1 (inversao)", len(aceita_p4 - set(P1_OUT))),
    ("  - P3 (placeholder)   = VERIFICADA", len(aceita_p4 - set(P1_OUT) - set(P3_OUT))),
    ("  + P2 (predicado pobre) = SUBSTANTIVA",
     len(aceita_p4 - set(P1_OUT) - set(P3_OUT)) + len(P2_IN)),
]
for nome, k in passos:
    lo, hi = wilson(k, n)
    print(f"  {nome:<40} {k:>3}/{n} = {k/n:.4f}  IC95 [{lo:.3f}, {hi:.3f}]")
verificada = passos[2][1] / n
print("\n  para comparar: publicado 22/10 = 0.8333 · markdown 23/10 = 0.9067")
print("  VERIFICADA = a tripla sustenta E a citacao do juiz confere.")
print("  SUBSTANTIVA = o chunk sustenta; as 4 de P2 nao tem citacao (o juiz as")
print("  rejeitou e devolveu string vazia), e so as rejeitadas foram relidas.")

print("\n  entram por P2:")
for i, por in P2_IN.items():
    print(f"    {i:<11} {por}")
print("  ficam fora:")
for i, por in P2_OUT.items():
    print(f"    {i:<11} {por}")

print("\n" + "=" * 76)
print("COBERTURA — o filtro de P1/P3 acha o que um leitor acha?")
print("=" * 76)
try:
    meus = {i: v for i, v in json.load(open(SAMPLE)).items() if i.startswith("kg-")}
except OSError:
    print("  amostra cega indisponivel neste host — perna nao exercitada")
    meus = {}
if meus:
    na = [i for i in meus if i in aceita_p4]
    rej = [i for i in na if not meus[i]]
    peg = [i for i in na if EXC.search(_acc(byid[i].get("citacao") or ""))
           or EX.search(_acc(byid[i].get("citacao") or ""))]
    print(f"  das {len(aceita_p4)} aceitas por P4, {len(na)} estao na amostra cega")
    print(f"  o leitor cego rejeita {len(rej)}: {rej}")
    print(f"  o filtro por marcador pega {len(peg)}: {peg}")
    print(f"  -> recall {len([i for i in rej if i in peg])}/{len(rej)} · "
          f"falso positivo {len([i for i in peg if i not in rej])}/{len(peg)}")
    print("  n pequeno. A cobertura do filtro sobre as 118 nao amostradas e desconhecida.")

    print("\n" + "=" * 76)
    print("A AMOSTRA CEGA FOI CONSUMIDA")
    print("=" * 76)
    def novo(i, sem=()):
        if "P1" not in sem and i in P1_OUT: return False
        if "P3" not in sem and i in P3_OUT: return False
        if "P2" not in sem and i in P2_IN:  return True
        if "P4" in sem: return juiz(i) and confere(i, n_markdown)
        return i in aceita_p4
    d = [i for i in meus if novo(i) != bool(meus[i])]
    print(f"  criterio novo vs os {len(meus)} vereditos cegos: {len(d)} discordancias {d}")
    print("  ⚠️  os quatro principios foram decididos A PARTIR destes vereditos.")
    print("      20/20 mede o criterio contra si mesmo; a correcao de populacao que")
    print("      dava 0.913 em 22/10 nao esta mais disponivel. Corrigir de novo exige")
    print("      amostra julgada por quem nao participou de fixar o criterio.")
    print("\n  MUTACAO — desligar um principio reabre a discordancia dele, e so a dele:")
    for p in ("P1", "P2", "P3", "P4"):
        dd = [i for i in meus if novo(i, (p,)) != bool(meus[i])]
        print(f"    sem {p}: {len(dd)} {dd}")
