#!/usr/bin/env python3
"""ROADMAP item 4, step S1: sampled precision of the knowledge graph.

Each relation carries `evidence_chunk_id`, so precision here is FAITHFULNESS:
does the cited evidence actually support the triple as stated? That is the
question that decides whether it is worth paying an LLM to extract over the
~93% of the corpus the graph does not cover — extracting more of something
unfaithful buys more unfaithfulness.

Sampling: uniform over relations whose evidence chunk still exists, with a fixed
seed recorded in the output so the draw is reproducible. Relations whose
evidence is gone are counted and excluded rather than silently dropped.

The judge must copy the FIRST EIGHT WORDS of the supporting sentence and the
span is verified by substring against the chunk. Measured on 2026-10-22 on this
same corpus: a judge asked for a free-length "verbatim" span produced one that
was not in the source 34.5% of the time, so an unverified claim of support is
not evidence of support.

Read-only: mode=ro, writes only its own output file.
"""
import json, os, random, re, sqlite3, sys, time, unicodedata, urllib.request
from concurrent.futures import ThreadPoolExecutor

DB    = os.environ.get("KG_DB", "/root/.openclaw/workspace/tools/nox-mem/nox-mem.db")
OUT   = sys.argv[1]
N     = int(os.environ.get("KG_N", "150"))
SEED  = int(os.environ.get("KG_SEED", "20261022"))
KEY   = os.environ["GEMINI_API_KEY"]
MODEL = os.environ.get("KG_MODEL", "gemini-2.5-flash-lite")
API   = "https://generativelanguage.googleapis.com/v1beta"
WORKERS = int(os.environ.get("KG_WORKERS", "6"))

def call(prompt):
    body = {"contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.0, "maxOutputTokens": 700,
                                 "responseMimeType": "application/json"}}
    req = urllib.request.Request(f"{API}/models/{MODEL}:generateContent?key={KEY}",
                                 data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    last = None
    for a in range(5):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                d = json.load(r)
            t = "".join(p.get("text", "") for p in d["candidates"][0]["content"]["parts"]).strip()
            if t:
                return t
            raise RuntimeError("vazio")
        except Exception as e:
            last = e
            time.sleep(1.5 * (a + 1))
    raise RuntimeError(str(last))

def jload(txt):
    def fix(o):
        if isinstance(o, list):
            return next((x for x in o if isinstance(x, dict)), None)
        return o if isinstance(o, dict) else None
    for att in (txt, re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", txt)):
        for f in (lambda s: json.loads(s, strict=False),
                  lambda s: json.JSONDecoder(strict=False).raw_decode(s.lstrip())[0]):
            try:
                return fix(f(att))
            except Exception:
                pass
        m = re.search(r"[\{\[].*[\}\]]", att, re.S)
        if m:
            try:
                return fix(json.loads(m.group(0), strict=False))
            except Exception:
                pass
    return None

def norm(s):
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s).strip().lower()

con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True, check_same_thread=False)
total  = con.execute("SELECT COUNT(*) FROM kg_relations").fetchone()[0]
sem_ev = con.execute("SELECT COUNT(*) FROM kg_relations WHERE evidence_chunk_id IS NULL").fetchone()[0]
morta  = con.execute("SELECT COUNT(*) FROM kg_relations r LEFT JOIN chunks c ON c.id=r.evidence_chunk_id "
                     "WHERE r.evidence_chunk_id IS NOT NULL AND c.id IS NULL").fetchone()[0]
elig = con.execute(
    "SELECT r.id, se.name, se.entity_type, r.relation_type, te.name, te.entity_type, "
    "       r.evidence_chunk_id, r.relation_reason, r.confidence, r.created_at, c.source_file, c.chunk_text "
    "FROM kg_relations r "
    "JOIN kg_entities se ON se.id = r.source_entity_id "
    "JOIN kg_entities te ON te.id = r.target_entity_id "
    "JOIN chunks c ON c.id = r.evidence_chunk_id").fetchall()
print(f"populacao: {total} relacoes · sem evidence_chunk_id {sem_ev} · evidencia morta {morta} "
      f"· elegiveis {len(elig)}", flush=True)

random.seed(SEED)
amostra = random.sample(elig, min(N, len(elig)))
print(f"amostra: {len(amostra)} (seed {SEED})", flush=True)

P = """Abaixo há uma TRIPLA extraída de um grafo de conhecimento e o TRECHO que foi registrado
como sua evidência. Decida se o trecho sustenta a tripla **como ela está escrita**.

TRIPLA:  ({s}) --[{p}]--> ({o})

TRECHO (a evidência registrada):
---
{t}
---

Regras:
- Os dois lados têm de aparecer no trecho, ou ser inequívocos a partir dele.
- A relação `{p}` tem de ser a que o trecho afirma. "Aparecem na mesma frase" NÃO é relação,
  a menos que a relação declarada seja exatamente de menção conjunta.
- Se sustenta, copie as **8 primeiras palavras** da frase do trecho que sustenta, exatamente
  como aparecem, sem reescrever e sem juntar pedaços de lugares diferentes.

Devolva JSON:
{{"sustenta": true|false,
  "oito_palavras": "<... ou vazio>",
  "erro": "nenhum"|"entidade_ausente"|"relacao_errada"|"so_co_ocorrencia"|"vago_demais"|"invertida",
  "motivo": "<uma frase>"}}"""

def do(row):
    (rid, sname, stype, rtype, tname, ttype, cid, reason, conf, created, sfile, ctext) = row
    rec = {"relation_id": rid, "source": sname, "source_type": stype, "relation": rtype,
           "target": tname, "target_type": ttype, "evidence_chunk_id": cid,
           "relation_reason": reason, "confidence": conf, "created_at": created,
           "source_file": sfile}
    try:
        j = jload(call(P.format(s=sname, p=rtype, o=tname, t=(ctext or "")[:6000]))) or {}
    except Exception as e:
        rec.update({"erro_exec": str(e)[:150], "sustenta": None})
        return rec
    q8 = (j.get("oito_palavras") or "").strip()
    ok = bool(q8) and len(norm(q8)) >= 12 and norm(q8) in norm(ctext or "")
    rec.update({"sustenta_segundo_juiz": bool(j.get("sustenta")),
                "citacao": q8[:200], "citacao_confere": ok,
                "sustenta": bool(j.get("sustenta")) and ok,
                "erro": j.get("erro") or "", "motivo": (j.get("motivo") or "")[:220]})
    return rec

res = []
with ThreadPoolExecutor(max_workers=WORKERS) as ex:
    for i, r in enumerate(ex.map(do, amostra), 1):
        res.append(r)
        if i % 25 == 0:
            print(f"  {i}/{len(amostra)}", flush=True)

ok   = [r for r in res if r.get("sustenta")]
claim= [r for r in res if r.get("sustenta_segundo_juiz")]
bad  = [r for r in res if r.get("sustenta_segundo_juiz") and not r.get("citacao_confere")]
err  = [r for r in res if r.get("erro_exec")]
n = len([r for r in res if r.get("sustenta") is not None])
p = len(ok) / n if n else 0
se = (p * (1 - p) / n) ** 0.5 if n else 0
out = {"population": {"relations": total, "no_evidence_id": sem_ev, "dead_evidence": morta,
                      "eligible": len(elig)},
       "sample": {"n": len(amostra), "seed": SEED, "judged": n, "exec_errors": len(err)},
       "precision": {"verified": len(ok), "p": round(p, 4),
                     "ci95": [round(max(0, p - 1.96 * se), 4), round(min(1, p + 1.96 * se), 4)],
                     "judge_claimed": len(claim),
                     "claimed_but_quote_failed": len(bad)},
       "rows": res}
json.dump(out, open(OUT, "w"), ensure_ascii=False, indent=1)
print(f"\nprecisao verificada: {len(ok)}/{n} = {p:.3f}  IC95 [{out['precision']['ci95'][0]:.3f}, "
      f"{out['precision']['ci95'][1]:.3f}]")
print(f"juiz afirmou sustentar: {len(claim)}  ·  destes, citacao nao conferiu: {len(bad)}")
