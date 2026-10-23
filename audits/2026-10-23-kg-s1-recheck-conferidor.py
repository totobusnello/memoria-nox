"""Re-derive the S1 citation check, versioned this time, and measure its power.

Why this exists. The S1 audit (2026-10-22) reported faithfulness 0.833 under a
"loose, calibrated, markdown-insensitive" predicate. The number is in
DECISIONS.md and in the audit — but the code that produced it was never
committed. Only the per-row boolean `confere_solto` survives, in
`s1-rows-recheck.json`. A number whose predicate cannot be re-run is not
reproducible, so this file rebuilds the predicate in the open.

It calls no LLM. It re-runs a mechanical check over judgements already made.

The harder question it answers. Relaxing a check until it stops rejecting is
not calibration, it is surrender: a check that never disagrees with the judge
adds nothing to the judge. A negative control against a RANDOM chunk does not
settle this — chunks from different documents share little vocabulary, so even
a hopeless predicate scores 0 there. So the control here perturbs the quote
itself, against its OWN chunk:

  word   — one content word replaced by another drawn from the corpus
  digit  — one digit changed ("R$ 50.000" -> "R$ 60.000"), the failure mode
           that matters most in contracts
  order  — the quote's words shuffled

A predicate with power rejects all three while still accepting the untouched
quote. One that accepts them is measuring vocabulary, not citation.
"""
import json, random, re, sqlite3, sys, unicodedata

ROWS = sys.argv[1] if len(sys.argv) > 1 else "/root/medicoes/2026-10-22-kg-s1/s1-rows-recheck.json"
DB   = sys.argv[2] if len(sys.argv) > 2 else "/root/.openclaw/workspace/tools/nox-mem/nox-mem.db"
SEED = 20261023
MIN  = 12  # a normalised quote shorter than this is not evidence of anything

def _acc(s):
    s = unicodedata.normalize("NFKD", s or "")
    return "".join(c for c in s if not unicodedata.combining(c))

_Q = dict.fromkeys(map(ord, "“”‘’«»"), '"')
_D = dict.fromkeys(map(ord, "–—−"), "-")

def n_strict(s):
    """Accent- and whitespace-insensitive. The first predicate, 2026-10-22."""
    return re.sub(r"\s+", " ", _acc(s)).strip().lower()

def n_markdown(s):
    """Strict plus the markup that contract and filing chunks carry.

    Dropping a marker leaves the space it occupied, so `**"Term"**` and `"Term"`
    normalise to `" term "` and `"term"` — equal content, unequal string. The
    two spacing rules below close that, and they are the reason this predicate
    recovers quotes the 2026-10-22 one did not.
    """
    s = _acc(s or "").translate(_Q).translate(_D)
    s = re.sub(r"<[^>\n]{1,24}>", " ", s)   # <u>, </u>, <br>
    s = re.sub(r"\\(.)", r"\1", s)          # R\$ -> R$
    s = re.sub(r"[*_`#>|~]+", " ", s)       # emphasis, strikethrough, headings, pipe tables
    s = re.sub(r"\s+", " ", s).strip().lower()
    s = re.sub(r'\s+([,.;:!?)\]"])', r"\1", s)   # space left by a dropped marker
    s = re.sub(r'(["(\[])\s+', r"\1", s)
    return s.strip()

def n_alnum(s):
    """Markdown-insensitive plus EVERY punctuation mark dropped."""
    return re.sub(r"\s+", " ", re.sub(r"[^0-9a-z ]+", " ", n_markdown(s))).strip()

CRITERIOS = [("estrito", n_strict), ("markdown", n_markdown), ("so alfanumerico", n_alnum)]

def casa(norm, quote, text):
    q = norm(quote)
    return len(q) >= MIN and q in norm(text)

rows = json.load(open(ROWS))
db = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
texto, _cache = {}, {}
for r in rows:
    cid = r.get("evidence_chunk_id")
    if cid and cid not in texto:
        got = db.execute("SELECT chunk_text FROM chunks WHERE id=?", (cid,)).fetchone()
        texto[cid] = got[0] if got else ""

claimed = [r for r in rows if r.get("sustenta_segundo_juiz")]
rnd = random.Random(SEED)
vocab = sorted({w for t in texto.values() for w in re.findall(r"[A-Za-zÀ-ÿ]{4,}", t)})

def perturba_palavra(q):
    ws = q.split()
    idx = [i for i, w in enumerate(ws) if len(re.sub(r"\W", "", w)) >= 4]
    if not idx:
        return None
    i = rnd.choice(idx)
    ws[i] = rnd.choice(vocab)
    return " ".join(ws)

def perturba_digito(q):
    pos = [i for i, c in enumerate(q) if c.isdigit()]
    if not pos:
        return None
    i = rnd.choice(pos)
    novo = rnd.choice([d for d in "0123456789" if d != q[i]])
    return q[:i] + novo + q[i + 1:]

def perturba_ordem(q):
    ws = q.split()
    if len(ws) < 4:
        return None
    for _ in range(8):
        emb = ws[:]
        rnd.shuffle(emb)
        if emb != ws:
            return " ".join(emb)
    return None

print(f"linhas: {len(rows)} · juiz afirma sustentar: {len(claimed)}\n")

print("precisao sobre TODAS as 150 (recomputada, nao aplicada so as falhas):")
res = {}
for nome, f in CRITERIOS:
    k = sum(1 for r in rows if r.get("sustenta_segundo_juiz")
            and casa(f, r.get("citacao") or "", texto.get(r.get("evidence_chunk_id"), "")))
    res[nome] = k
    print(f"  {nome:<18} {k:>3}/{len(rows)} = {k/len(rows):.3f}")
juiz = len(claimed)
print(f"  {'juiz puro':<18} {juiz:>3}/{len(rows)} = {juiz/len(rows):.3f}   (nenhuma conferencia)")
gravado = sum(1 for r in rows if r.get("sustenta_segundo_juiz") and r.get("confere_solto"))
print(f"  {'[gravado 22/10]':<18} {gravado:>3}/{len(rows)} = {gravado/len(rows):.3f}   "
      f"(booleano do arquivo; o codigo nao foi versionado)")

print("\nPODER: a citacao PERTURBADA contra o PROPRIO chunk deve ser REJEITADA.")
print("      'aceita' aqui = o criterio nao distingue a citacao do vocabulario.\n")
print(f"{'criterio':<18}" + "".join(f"{p:>22}" for p in ("1 palavra trocada", "1 digito trocado", "ordem embaralhada")))
for nome, f in CRITERIOS:
    linha = f"{nome:<18}"
    for pert in (perturba_palavra, perturba_digito, perturba_ordem):
        n = aceita = 0
        for r in claimed:
            q = r.get("citacao") or ""
            t = texto.get(r.get("evidence_chunk_id"), "")
            if not casa(f, q, t):
                continue           # só perturba o que o critério aceitava
            pq = pert(q)
            if pq is None:
                continue
            n += 1
            if casa(f, pq, t):
                aceita += 1
        linha += f"{f'{aceita}/{n} aceita':>22}"
    print(linha)

print("\nCONTROLE FRACO (citacao vs chunk ALEATORIO de outro documento):")
for nome, f in CRITERIOS:
    fp = 0
    ids = [r["evidence_chunk_id"] for r in rows if r.get("evidence_chunk_id")]
    for r in claimed:
        outro = rnd.choice([i for i in ids if i != r["evidence_chunk_id"]])
        if casa(f, r.get("citacao") or "", texto.get(outro, "")):
            fp += 1
    print(f"  {nome:<18} {fp}/{len(claimed)} falsos positivos")
