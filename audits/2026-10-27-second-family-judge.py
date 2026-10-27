"""A second judge from a DIFFERENT model family over the same 99 replay items.

Why, and what it can and cannot settle. The strong form of H2 asked for human
grading by someone who did not build the arms. The Toto chose a different model
family instead (2026-10-27). That buys independence of FAMILY, not of NATURE: it
is still an LLM judge, and the census an hour ago found 4.5% of labels flipping
on a re-read with 47% in the borderline band.

What it does settle is the risk Codex named (finding 7): the identifier prompt
plausibly produces more LITERAL answers, which a judge may reward without an
equal gain in correctness. If that is happening, the D−C gap will differ between
families, and THAT is the number this run exists to produce — not the agreement
rate, which is only the context for reading it.

Judge 1: OpenAI `gpt-6-luna` via the Decisions API (already on disk).
Judge 2: Google `gemini-2.5-flash-lite` — CLAUDE.md rule 3's default; never
         gemini-2.5-flash (3M/d quota) and never 2.0-flash (shut down).

Read-only on the measurement artifacts; writes only its own output.
"""
import json, os, re, sys, time, urllib.error, urllib.request
from collections import Counter
from concurrent.futures import ThreadPoolExecutor

SRC = "/root/medicoes/2026-10-26-memory-tax/armd-judged.json"
OUT = "/root/medicoes/second-family-judge-2026-10-27.json"
KEY = os.environ["GEMINI_API_KEY"]
MODEL = os.environ.get("G_MODEL", "gemini-2.5-flash-lite")
URL = (f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}"
       f":generateContent")
WORKERS = int(os.environ.get("WORKERS", "6"))
SMOKE = int(os.environ.get("SMOKE_N", "0"))
ARMS = ["c_all", "c_visible", "c_iso", "d_full", "d_visible", "d_iso"]

SRC_C = "/root/medicoes/2026-10-26-memory-tax/armc-judged.json"
def load(p):
    o = json.load(open(p))
    return o["rows"] if isinstance(o, dict) and "rows" in o else o
rows, rows_c = load(SRC), load(SRC_C)
# The two artifacts hold DIFFERENT arms' response texts: armc carries
# c_all_text and c_iso_text, armd carries c_visible/d_full/d_visible/d_iso.
# The decisive pair for H2 is c_all vs d_full — both with the full window, only
# the prompt differing — so they must be merged. Verified: the item order and
# questions match across the two files, which is what licenses the merge.
assert len(rows) == len(rows_c), "artifacts differ in length"
assert all(a["question"] == b["question"] for a, b in zip(rows, rows_c)), \
    "item order diverges between artifacts — a positional merge would mismatch"
for r, rc in zip(rows, rows_c):
    for k in ("c_all_text", "c_iso_text"):
        if k in rc and k not in r:
            r[k] = rc[k]
    if "c_all" in rc and "c_all" not in r:
        r["c_all"] = rc["c_all"]
print(f"{len(rows)} items · arms judged by family 2: {ARMS}")

# which arms actually carry a response text here
have = [a for a in ARMS if f"{a}_text" in rows[0]]
print(f"arms with a *_text field in this artifact: {have}")
missing = [a for a in ARMS if a not in have]
if missing:
    print(f"! no text for {missing} — they cannot be re-judged from this file")

PROMPT = """Você é um avaliador. Responda APENAS com um JSON.

PERGUNTA: {q}

RESPOSTA DE REFERÊNCIA (verdade): {gold}

RESPOSTA A AVALIAR: {ans}

Decida se a RESPOSTA A AVALIAR contém a informação da RESPOSTA DE REFERÊNCIA.
Conta como correta se traz o mesmo dado, ainda que com outra redação.
NÃO conta se apenas trata do mesmo assunto, se abstém, ou se contradiz.

Responda exatamente: {{"correta": true}} ou {{"correta": false}}"""

def ask(q, gold, ans):
    body = {"contents": [{"parts": [{"text": PROMPT.format(q=q, gold=gold, ans=ans)}]}],
            "generationConfig": {"temperature": 0, "maxOutputTokens": 2048,
                                 "responseMimeType": "application/json"}}
    req = urllib.request.Request(f"{URL}?key={KEY}", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    last = None
    for a in range(4):
        try:
            with urllib.request.urlopen(req, timeout=120) as r:
                o = json.load(r)
            c = (o.get("candidates") or [{}])[0]
            parts = ((c.get("content") or {}).get("parts") or [{}])
            txt = "".join(p.get("text", "") for p in parts).strip()
            if not txt:
                raise RuntimeError(f"empty response (finishReason="
                                   f"{c.get('finishReason')})")
            m = re.search(r'"correta"\s*:\s*(true|false)', txt)
            if not m:
                raise RuntimeError(f"no verdict in {txt[:90]!r}")
            return m.group(1) == "true"
        except Exception as e:
            last = f"{type(e).__name__}: {str(e)[:110]}"
            time.sleep(2 * (a + 1))
    raise RuntimeError(str(last))

tasks = []
for i, r in enumerate(rows):
    for arm in have:
        t = r.get(f"{arm}_text")
        if t is None:
            continue
        tasks.append({"i": i, "arm": arm, "question": r["question"],
                      "gold": r["answer"], "ans": t,
                      "category": r.get("category"), "stratum": r.get("stratum"),
                      "j1": int((r.get(arm) or {}).get("contem") or 0)})
if SMOKE:
    tasks = tasks[:SMOKE]
print(f"judgements to make: {len(tasks)}", flush=True)

res, t0 = [], time.time()
def work(t):
    try:
        return {**{k: v for k, v in t.items() if k not in ("ans", "gold", "question")},
                "j2": int(ask(t["question"], t["gold"], t["ans"]))}
    except Exception as e:
        return {**{k: v for k, v in t.items() if k not in ("ans", "gold", "question")},
                "erro": str(e)[:110]}
with ThreadPoolExecutor(max_workers=WORKERS) as ex:
    for n, r in enumerate(ex.map(work, tasks), 1):
        res.append(r)
        if n % 60 == 0 or n == len(tasks):
            print(f"  {n}/{len(tasks)}  {time.time()-t0:.0f}s", flush=True)
json.dump(res, open(OUT, "w"), ensure_ascii=False)
ok = [r for r in res if "j2" in r]
print(f"\n{len(ok)} judged · {len(res)-len(ok)} errors · {time.time()-t0:.0f}s")
if len(res) - len(ok):
    print("  first errors:", [r.get("erro") for r in res if "erro" in r][:2])
if not ok:
    sys.exit(3)

print(f"\nAGREEMENT between families, per arm")
print(f"{'arm':12s} {'n':>4s} {'j1 acc':>7s} {'j2 acc':>7s} {'agree':>7s} {'kappa':>7s}")
accs = {}
for arm in have:
    g = [r for r in ok if r["arm"] == arm]
    if not g:
        continue
    a1 = sum(r["j1"] for r in g) / len(g)
    a2 = sum(r["j2"] for r in g) / len(g)
    ag = sum(1 for r in g if r["j1"] == r["j2"]) / len(g)
    p11 = sum(1 for r in g if r["j1"] and r["j2"]) / len(g)
    p00 = sum(1 for r in g if not r["j1"] and not r["j2"]) / len(g)
    pe = a1 * a2 + (1 - a1) * (1 - a2)
    k = (ag - pe) / (1 - pe) if pe < 1 else 0.0
    accs[arm] = (a1, a2, len(g))
    print(f"{arm:12s} {len(g):4d} {a1:7.3f} {a2:7.3f} {ag:7.3f} {k:7.4f}")

print(f"\n🔑 THE NUMBER THIS RUN EXISTS FOR — the D−C gap under each family")
pairs = [("c_all", "d_full"), ("c_visible", "d_visible"), ("c_iso", "d_iso")]
for c, dd in pairs:
    if c in accs and dd in accs:
        g1 = accs[dd][0] - accs[c][0]
        g2 = accs[dd][1] - accs[c][1]
        print(f"  {dd} − {c}:  family1 {g1*100:+6.1f} pp   family2 {g2*100:+6.1f} pp   "
              f"difference {abs(g1-g2)*100:5.1f} pp")
print("\n  If the two families disagree on the GAP, the criterion effect depends on")
print("  who judges, and that is the literalness risk Codex named. If they agree,")
print("  the effect survives a change of judge family — which is what we wanted to")
print("  know and what a single family could not tell us.")
