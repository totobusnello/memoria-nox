#!/usr/bin/env python3
"""Runner of the public-corpus leg (§11, as amended in v1.1 §12). Standard library only.

Every component is the deployed one or the one the production arms used, copied verbatim:
  extractor   DISTILL_SYSTEM v1 / DISTILL_SYSTEM_V2  (audits/2026-10-27-arm-{c,d}-*-build.py)
  blocking    BLOCK_SIZE 2000, never splits a line, per SESSION (session-distill works per session)
  noise       is_noise_static, verbatim
  filter      importance >= 0.5, at most 10 items per block (the prompt's own ceiling)
  answerer    ANSWER_SYSTEM verbatim, gemini-2.5-flash-lite, temperature 0, 200 output tokens
  judge       gpt-6-luna, Decisions API, the CONTEM / CONTRADIZ predicates and 4-level scale;
              correct  <=>  P(contem) > 0.5
  judge 2     gemini-2.5-flash-lite, the family-2 prompt of audits/2026-10-27-second-family-
              judge.py; both families judge every row (§11.5 item 9: the bracket)

What v1.1 §12 pins and this file implements (nothing here is chosen after seeing outcomes):
  §12.3 serving   all units of the cell's sessions, importance descending, ties by more recent
                  session, then block, then position; each line "[<session date>] [<category>] text"
  §12.3 question  "PERGUNTA (feita em <question_date>): <question>"
  §12.4 reuse     a block is distilled ONCE per criterion; every window containing it reuses it
  §12.5 controls  positive = full window minus every answer session, C1
                  negative = W 0.240 cut applied to non-answer sessions + ALL answer sessions, C1
  §12.6 counterf. answer sessions rewritten by the manifest's rule, four primary cells
  §11.5 item 8    length-matched arm: cell 00's units, padded with the haystack's NON-answer prose
                  (most recent first) to cell 11's served length

  python3 -I lme-run.py --phase smoke  --out <dir>            prints the estimate, spends nothing
  python3 -I lme-run.py --phase smoke  --out <dir> --yes      runs
  python3 -I lme-run.py --phase stage1 --out <dir> --yes --cap-usd 140

  python3 -I lme-run.py --phase confirm --reader <R> --out <dir> --yes --cap-usd <usd>   (v1.2 §13)
  python3 -I lme-run.py --phase confirm --reader R3 --repair C2 --out <dir> --yes ...      (v1.3 §14)

v1.2 §13 adds READERS: the reader is the only component v1.2 changes. R0 is the v1.1 reader and
keeps its exact cache key, so smoke and stage 1 replay byte for byte; R1-R3 are the calibration
candidates of §13.5. Phase `confirm` reads v12-manifest.json and requires --reader.

Resumable: every call is cached in <out>/cache.sqlite under the hash of its exact input.
"""
import argparse
import hashlib
import json
import os
import pathlib
import re
import sqlite3
import subprocess
import sys
import threading
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor

HERE = pathlib.Path(__file__).resolve().parent
GMODEL = "gemini-2.5-flash-lite"
JMODEL = "gpt-6-luna"
BLOCK_SIZE = 2000
THR = 0.5
G_IN, G_OUT = 0.10 / 1e6, 0.40 / 1e6          # flash-lite list price, USD per token
J_CALL = 6.4e-5                                 # measured per judge call (§11.4)

DISTILL_SYSTEM = """Você é um extrator de memória de conversas de IA.
Analise a conversa e extraia APENAS informações que merecem ser lembradas a longo prazo:
- Decisões tomadas pelo usuário ou pelo agente
- Preferências do usuário (como ele quer as coisas feitas)
- Lições aprendidas (erros, fixes, insights técnicos)
- Contexto de projetos relevantes (nomes, status, detalhes)

Ignore: cumprimentos, confirmações (ok, feito, obrigado), listas de tarefas genéricas, conteúdo repetido.

Responda APENAS com JSON válido:
{"memories": [{"text": "...", "category": "decision|preference|lesson|context|project", "importance": 0.0-1.0}]}

Importância: 0.9+ = crítico, 0.7-0.9 = importante, 0.5-0.7 = útil, <0.5 = ignorar.
Retorne [] se não houver nada relevante. Máximo 10 itens."""

IDENT_PARAGRAPH = """OBRIGATÓRIO: todo identificador que aparecer na conversa tem de ser copiado LETRA POR LETRA no texto da memória — nome de arquivo, caminho, comando, nome de tabela ou de coluna, chave de configuração, número de porta, URL, nome de canal, versão, valor numérico. Nunca trocar por descrição ("o arquivo de tarefas"), nunca abreviar, nunca traduzir. Uma memória que diz o que foi decidido mas não diz sobre qual arquivo, comando ou valor não serve para nada: ou carrega o identificador, ou não vale ser extraída.

"""
_ANCHOR = "Responda APENAS com JSON válido:"
assert DISTILL_SYSTEM.count(_ANCHOR) == 1
DISTILL_SYSTEM_V2 = DISTILL_SYSTEM.replace(_ANCHOR, IDENT_PARAGRAPH + _ANCHOR)
# v1.3 §14.3 — criterion C2, fixed before any C2 call. It is C1 plus one paragraph, inserted at
# the same anchor, aimed at the three losses READER-CEILING.md / §14.1 measured on the spent 200:
# incidental facts about the user dropped or turned into lessons, the time of an event replaced
# by the date of the conversation, and what the assistant said that the user may ask back.
EVENT_PARAGRAPH = """TAMBÉM OBRIGATÓRIO: fatos concretos sobre a vida do usuário merecem memória mesmo quando ditos de passagem, no meio de outro assunto — rotina, quantidades, valores gastos, durações, idades, lugares, pessoas, compras, viagens, eventos. Extraia cada um como fato (categoria context), com os números e nomes copiados, sem transformá-lo em lição ou preferência, e com importância de pelo menos 0.5.
Quando a conversa disser quando algo aconteceu ("há três semanas", "ontem", "no sábado passado", "em 15 de abril"), copie a expressão de tempo para a memória junto com o evento: a data da conversa não é a data do evento.
Quando o assistente der uma informação específica que o usuário pode pedir de volta depois — uma lista, um nome, uma recomendação, um número — guarde-a como memória, com os itens na ordem em que foram dados.

"""
DISTILL_SYSTEM_V3 = DISTILL_SYSTEM_V2.replace(_ANCHOR, EVENT_PARAGRAPH + _ANCHOR)
PROMPTS = {"C0": DISTILL_SYSTEM, "C1": DISTILL_SYSTEM_V2, "C2": DISTILL_SYSTEM_V3}
# the repaired level of factor C. v1.1/v1.2: C1. v1.3 (§14): C2, set only by --phase confirm --repair C2
REPAIR = "C1"

ANSWER_SYSTEM = """Você responde perguntas usando APENAS o material fornecido.

Regras:
- Se o material contém a resposta, responda em no máximo 25 palavras.
- Se o material NÃO contém a resposta, responda exatamente: NAO SEI
- Nunca use conhecimento próprio. Nunca especule. Nunca complete lacuna.
- Se o material trouxer duas informações conflitantes, responda com a que o
  material indicar como final e diga que houve mudança. Se não houver como
  saber qual é a final, responda as duas e diga que o material não resolve."""

# v1.2 §13.5 — prompt B, fixed before any calibration call. It changes three things against
# ANSWER_SYSTEM and nothing else: it says what the material is (dated memories), it asks for the
# combining LongMemEval questions need (count, compare, date arithmetic from the memories' dates
# and the question's date), and it reserves NAO SEI for material with NOTHING relevant.
ANSWER_SYSTEM_B = """Você responde perguntas sobre o usuário usando APENAS o material fornecido: memórias datadas, extraídas de conversas antigas dele, uma por linha no formato [data] [categoria] texto.

Regras:
- Leia todas as memórias relevantes para a pergunta. A resposta pode exigir juntar várias delas, contar itens, comparar ou ordenar eventos, ou calcular intervalos a partir das datas das memórias e da data em que a pergunta é feita. Faça esse raciocínio.
- Responda em no máximo 25 palavras.
- Responda exatamente NAO SEI somente se nenhuma memória do material for relevante para a pergunta.
- Tudo o que você afirmar sobre o usuário tem de estar no material. Não use conhecimento próprio sobre ele.
- Se o material trouxer informações conflitantes, use a mais recente e diga que houve mudança."""

# id -> (model, system prompt, generationConfig, USD per input token, USD per output token).
# Prices: Gemini Developer API list price, standard tier, read 2026-11-03 (ai.google.dev pricing);
# output price includes thinking tokens. R0 is the v1.1 reader, untouched.
READERS = {
    "R0": ("gemini-2.5-flash-lite", "A", {"temperature": 0.0, "maxOutputTokens": 200},
           0.10e-6, 0.40e-6),
    "R1": ("gemini-2.5-flash-lite", "B", {"temperature": 0.0, "maxOutputTokens": 200},
           0.10e-6, 0.40e-6),
    "R2": ("gemini-3.8-flash", "A", {"temperature": 0.0, "maxOutputTokens": 2048,
                                     "thinkingConfig": {"thinkingLevel": "low"}},
           0.75e-6, 3.75e-6),
    "R3": ("gemini-3.8-flash", "B", {"temperature": 0.0, "maxOutputTokens": 2048,
                                     "thinkingConfig": {"thinkingLevel": "low"}},
           0.75e-6, 3.75e-6),
}

CANON = "i have no memory matches for this question"


def abstained(t):
    s = (t or "").lower()
    return (CANON in s or "nao sei" in s or "não sei" in s or "não tenho" in s
            or "nao tenho" in s or "não há informação" in s or "nao ha informacao" in s)


CONTEM = ("A RESPOSTA DO CANDIDATO transmite o mesmo fato que a RESPOSTA DE REFERENCIA, "
          "para esta pergunta: {q}\nRedacao diferente, mais detalhe ou caminho completo em "
          "vez de nome de arquivo contam como o mesmo fato. Omitir o fato pedido ou dizer "
          "que nao sabe NAO conta.")
CONTRADIZ = ("A RESPOSTA DO CANDIDATO afirma algo INCOMPATIVEL com a RESPOSTA DE REFERENCIA "
             "para esta pergunta: {q}\nConta como incompativel: valor, nome, numero, horario "
             "ou decisao diferente apresentado como correto. NAO conta: dizer que nao sabe, "
             "nem omitir parte do fato, nem dar menos detalhe.")
LEVELS = [
    {"label": "nao_responde", "description": "O CANDIDATO nao apresenta resposta: diz que nao "
                                             "sabe, que a informacao nao esta disponivel, ou "
                                             "nada diz sobre o que foi perguntado."},
    {"label": "responde_errado", "description": "O CANDIDATO apresenta uma resposta, e ela "
                                                "afirma um valor, nome ou decisao diferente do "
                                                "da REFERENCIA."},
    {"label": "responde_parcial", "description": "O CANDIDATO apresenta parte do fato da "
                                                 "REFERENCIA e deixa faltar outra parte, sem "
                                                 "afirmar nada que a contradiga."},
    {"label": "responde_certo", "description": "O CANDIDATO apresenta o fato da REFERENCIA por "
                                               "inteiro, com qualquer redacao."},
]

NOISE_PATTERNS = [
    re.compile(r"^\s*[\U0001F44D\U0001F44C✅\U0001F64F❤️\U0001F44F\U0001F60A\U0001F91D\U0001F4AA\U0001F525]+\s*$"),
    re.compile(r"^\s*[\.\-_,;:!?]+\s*$"),
    re.compile(r"^\s*\d+\s*$"),
    re.compile(r"^(ok|sim|não|nao|yes|no|yep|nope)\.?\s*$", re.I),
]


def is_noise_static(text):
    t = text.strip()
    if len(t) <= 10:
        return True
    if len(t) >= 500:
        return False
    return any(rx.match(t) for rx in NOISE_PATTERNS)


def blocks_of(lines):
    out, cur = [], ""
    for line in lines:
        if len(cur) + len(line) > BLOCK_SIZE and cur:
            out.append(cur.strip())
            cur = line + "\n"
        else:
            cur += line + "\n"
    if cur.strip():
        out.append(cur.strip())
    return out


def session_blocks(sess):
    lines = [f"[{(t.get('role') or 'unknown').upper()}]: {t.get('content') or ''}"
             for t in sess if not is_noise_static(t.get("content") or "")]
    return blocks_of(lines)


def h(*parts):
    return hashlib.sha256("\x1f".join(parts).encode()).hexdigest()


# ------------------------------------------------------------------ the cut rule (§11.2)
def prose(sess):
    return sum(len(t.get("content") or "") for t in sess)


def recency_order(r):
    return sorted(range(len(r["haystack_sessions"])),
                  key=lambda i: (r["haystack_dates"][i], i), reverse=True)


def cut(r, frac, among=None):
    """most-recent-first, cumulative prose chars over the WHOLE haystack's prose, crossing
    session included whole. `among` restricts which sessions may be taken (negative control)."""
    total = sum(prose(s) for s in r["haystack_sessions"])
    kept, run = [], 0
    for i in recency_order(r):
        if among is not None and i not in among:
            continue
        if run >= frac * total:
            break
        kept.append(i)
        run += prose(r["haystack_sessions"][i])
    return kept


def evidence(r):
    return {i for i, sid in enumerate(r["haystack_session_ids"]) if sid in r["answer_session_ids"]}


NUM = re.compile(r"\d+(?:\.\d+)?")


def rewrite(r, original, altered):
    """§12.6: inside the answer sessions, every case-insensitive occurrence of the original
    answer string becomes the altered one. Nothing else in the haystack changes."""
    rx = re.compile(re.escape(original), re.I)
    ev = evidence(r)
    out = dict(r)
    out["haystack_sessions"] = [
        [dict(t, content=rx.sub(altered, t.get("content") or "")) for t in s] if i in ev else s
        for i, s in enumerate(r["haystack_sessions"])]
    return out


# ------------------------------------------------------------------ calls, cached
class Cache:
    def __init__(self, path):
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.lock = threading.Lock()
        with self.lock:
            self.db.execute("CREATE TABLE IF NOT EXISTS c (k TEXT PRIMARY KEY, kind TEXT, v TEXT)")
            self.db.commit()

    def get(self, k):
        with self.lock:
            row = self.db.execute("SELECT v FROM c WHERE k=?", (k,)).fetchone()
        return json.loads(row[0]) if row else None

    def put(self, k, kind, v):
        with self.lock:
            self.db.execute("INSERT OR REPLACE INTO c VALUES (?,?,?)", (k, kind, json.dumps(v)))
            self.db.commit()


class Ledger:
    def __init__(self, cap):
        self.cap, self.usd, self.lock = cap, 0.0, threading.Lock()
        self.n = {"distill": 0, "answer": 0, "judge": 0, "cached": 0, "failed": 0}

    def add(self, kind, usd):
        with self.lock:
            self.usd += usd
            self.n[kind] += 1
            if self.cap and self.usd > self.cap:
                raise SystemExit(f"CAP REACHED: US$ {self.usd:.2f} > {self.cap}")


def post(url, body, hdr, timeout=180):
    req = urllib.request.Request(url, data=json.dumps(body).encode(), headers=hdr)
    last = None
    for a in range(6):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return json.load(r)
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}: {e.read().decode()[:200]}"
            if e.code in (400, 401, 403, 404):
                break
            time.sleep(3 * (a + 1))
        except Exception as e:
            last = f"{type(e).__name__}: {str(e)[:160]}"
            time.sleep(3 * (a + 1))
    raise RuntimeError(str(last))


def gurl(model=None):
    return (f"https://generativelanguage.googleapis.com/v1beta/models/{model or GMODEL}"
            f":generateContent?key={os.environ['GEMINI_API_KEY']}")


def g_usage(d):
    u = d.get("usageMetadata") or {}
    return (u.get("promptTokenCount", 0) or 0,
            (u.get("candidatesTokenCount", 0) or 0) + (u.get("thoughtsTokenCount", 0) or 0))


def distill(cache, led, crit, block):
    k = h("distill", crit, PROMPTS[crit], block)
    hit = cache.get(k)
    if hit is not None:
        led.n["cached"] += 1
        return hit
    body = {"contents": [{"role": "user",
                          "parts": [{"text": PROMPTS[crit] + "\n\nConversa:\n" + block}]}],
            "generationConfig": {"responseMimeType": "application/json", "temperature": 0.1}}
    try:
        d = post(gurl(), body, {"Content-Type": "application/json"})
        txt = "".join(p.get("text", "") for p in
                      ((d.get("candidates") or [{}])[0].get("content") or {}).get("parts") or [])
        mem = (json.loads(txt).get("memories") or []) if txt else []
        units = [{"text": m.get("text", ""), "category": m.get("category"),
                  "importance": m.get("importance")} for m in mem
                 if isinstance(m, dict) and (m.get("importance") or 0) >= 0.5]
        ti, to = g_usage(d)
        v = {"units": units, "failed": not txt, "model_version": d.get("modelVersion"),
             "tin": ti, "tout": to}
    except Exception as e:
        v = {"units": [], "failed": True, "error": str(e)[:200], "tin": 0, "tout": 0}
        led.n["failed"] += 1
    led.add("distill", v["tin"] * G_IN + v["tout"] * G_OUT)
    if not v.get("error"):
        cache.put(k, "distill", v)
    return v


def answer(cache, led, material, question, reader="R0"):
    model, pid, gen, p_in, p_out = READERS[reader]
    system = ANSWER_SYSTEM if pid == "A" else ANSWER_SYSTEM_B
    if reader == "R0":   # the v1.1 key, so stage 1 and the smoke replay from their caches
        k = h("answer", GMODEL, ANSWER_SYSTEM, material, question)
    else:
        k = h("answer", model, system, json.dumps(gen, sort_keys=True), material, question)
    hit = cache.get(k)
    if hit is not None:
        led.n["cached"] += 1
        return hit
    d = post(gurl(model), {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [{"parts": [{"text": f"MATERIAL:\n{material}\n\n{question}"}]}],
        "generationConfig": gen},
        {"Content-Type": "application/json"})
    c = (d.get("candidates") or [{}])[0]
    txt = "".join(p.get("text", "") for p in (c.get("content") or {}).get("parts") or []).strip()
    ti, to = g_usage(d)
    v = {"text": txt, "finish": c.get("finishReason"), "model_version": d.get("modelVersion"),
         "tin": ti, "tout": to}
    led.add("answer", ti * p_in + to * p_out)
    cache.put(k, "answer", v)
    return v


def judge(cache, led, ref, cand, q):
    k = h("judge", JMODEL, CONTEM, CONTRADIZ, json.dumps(LEVELS), ref, cand, q)
    hit = cache.get(k)
    if hit is not None:
        led.n["cached"] += 1
        return hit
    d = post("https://api.openai.com/v1/decisions", {
        "model": JMODEL,
        "input": f"RESPOSTA DE REFERENCIA:\n---\n{ref}\n---\n\n"
                 f"RESPOSTA DO CANDIDATO:\n---\n{cand}\n---",
        "questions": [
            {"type": "predicate", "name": "contem", "instructions": CONTEM.format(q=q)},
            {"type": "predicate", "name": "contradiz", "instructions": CONTRADIZ.format(q=q)},
            {"type": "score", "name": "nivel",
             "instructions": f"Qual destes descreve melhor a RESPOSTA DO CANDIDATO, "
                             f"dada a pergunta: {q}", "levels": LEVELS}]},
        {"Content-Type": "application/json",
         "Authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"})
    ans = {a["name"]: a for a in d.get("answers", [])}
    if "contem" not in ans or "contradiz" not in ans:
        raise RuntimeError(f"judge envelope without the predicates: keys={list(d)[:6]}")
    s_ = ans.get("nivel", {})
    v = {"contem": ans["contem"].get("probability"),
         "contradiz": ans["contradiz"].get("probability"),
         "nivel": s_.get("score"),
         "nivel_probs": {x["label"]: x["probability"] for x in s_.get("probabilities", [])},
         "model": d.get("model")}
    led.add("judge", J_CALL)
    cache.put(k, "judge", v)
    return v


# Family-2 judge, verbatim from audits/2026-10-27-second-family-judge.py. §11.5 item 9 makes the
# criterion effect a bracket ACROSS judge families, so both families judge every row.
J2_PROMPT = """Você é um avaliador. Responda APENAS com um JSON.

PERGUNTA: {q}
RESPOSTA DE REFERÊNCIA (verdade): {gold}
RESPOSTA A AVALIAR: {ans}

Decida se a RESPOSTA A AVALIAR contém a informação da RESPOSTA DE REFERÊNCIA.
Conta como correta se traz o mesmo dado, ainda que com outra redação.
NÃO conta se apenas trata do mesmo assunto, se abstém, ou se contradiz.

Responda exatamente: {{"correta": true}} ou {{"correta": false}}"""


def judge2(cache, led, ref, cand, q):
    k = h("judge2", GMODEL, J2_PROMPT, ref, cand, q)
    hit = cache.get(k)
    if hit is not None:
        led.n["cached"] += 1
        return hit
    body = {"contents": [{"parts": [{"text": J2_PROMPT.format(q=q, gold=ref, ans=cand)}]}],
            "generationConfig": {"temperature": 0, "maxOutputTokens": 2048,
                                 "responseMimeType": "application/json"}}
    d = post(gurl(), body, {"Content-Type": "application/json"})
    c = (d.get("candidates") or [{}])[0]
    txt = "".join(p.get("text", "") for p in (c.get("content") or {}).get("parts") or []).strip()
    m = re.search(r'"correta"\s*:\s*(true|false)', txt)
    if not m:
        raise RuntimeError(f"family-2 judge gave no verdict: {txt[:90]!r}")
    ti, to = g_usage(d)
    v = {"correta": m.group(1) == "true", "model_version": d.get("modelVersion")}
    led.add("judge", ti * G_IN + to * G_OUT)
    cache.put(k, "judge2", v)
    return v


# ------------------------------------------------------------------ cells
def cells_for(qid, man, phase):
    prim = ["00", "01", "10", "11"]
    cs = list(prim)
    if phase == "smoke":
        cs += ["pos", "neg", "lenmatch"]
        return cs
    if qid in man["dose_subsample"]:
        cs += ["d020_C0", f"d020_{REPAIR}", "d894_C0", f"d894_{REPAIR}"]
    if qid in man["control_subsample"]:
        cs += ["pos", "neg"]
    cs += ["lenmatch"]
    return cs


def cell_spec(cell, r):
    """-> (criterion, list of session indices)"""
    n = len(r["haystack_sessions"])
    allv = list(range(n))
    ev = evidence(r)
    if cell in ("00", "01"):
        return ("C0" if cell == "00" else REPAIR), cut(r, 0.240)
    if cell in ("10", "11"):
        return ("C0" if cell == "10" else REPAIR), allv
    if cell.startswith("d"):
        frac = {"d020": 0.020, "d894": 0.894}[cell[:4]]
        return cell[5:], cut(r, frac)
    if cell == "pos":
        return REPAIR, [i for i in allv if i not in ev]
    if cell == "neg":
        non = set(allv) - ev
        return REPAIR, sorted(set(cut(r, 0.240, among=non)) | ev)
    raise ValueError(cell)


def serve(units_by_session, sessions, r):
    rank = {i: p for p, i in enumerate(recency_order(r))}
    items = []
    for i in sessions:
        for b, us in enumerate(units_by_session[i]):
            for pos, u in enumerate(us):
                items.append((-(u.get("importance") or 0), rank[i], b, pos, i, u))
    items.sort(key=lambda x: x[:4])
    return "\n".join(f"[{r['haystack_dates'][x[4]]}] [{x[5].get('category')}] {x[5].get('text')}"
                     for x in items)


def pad_to(material, target, r):
    """length-matched arm: append the haystack's NON-answer prose, most recent first."""
    ev = evidence(r)
    out = material
    for i in recency_order(r):
        if len(out) >= target:
            break
        if i in ev:
            continue
        for t in r["haystack_sessions"][i]:
            if len(out) >= target:
                break
            out += f"\n[{r['haystack_dates'][i]}] [{(t.get('role') or '').upper()}]: {t.get('content') or ''}"
    return out[:max(target, len(material))]


def question_text(r):
    return f"PERGUNTA (feita em {r['question_date']}): {r['question']}"


# ------------------------------------------------------------------ main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--phase", choices=["smoke", "stage1", "confirm"], required=True)
    ap.add_argument("--reader", choices=sorted(READERS), default=None,
                    help="v1.2 §13: required for --phase confirm; smoke and stage 1 are R0")
    ap.add_argument("--repair", choices=["C1", "C2"], default="C1",
                    help="v1.3 §14: the repaired criterion level; C2 only with --phase confirm")
    ap.add_argument("--out", required=True)
    ap.add_argument("--data", default=os.path.expanduser(
        "~/datasets/longmemeval/longmemeval_s_cleaned.json"))
    ap.add_argument("--workers", type=int, default=8)
    ap.add_argument("--cap-usd", type=float, default=0)
    ap.add_argument("--yes", action="store_true")
    a = ap.parse_args()
    if a.phase == "confirm" and not a.reader:
        sys.exit("--phase confirm needs --reader (the one §13.10 records as selected)")
    if a.phase != "confirm" and a.reader not in (None, "R0"):
        sys.exit("smoke and stage 1 ran with R0; another reader there would not be a replay")
    reader = a.reader or "R0"
    if a.repair != "C1" and a.phase != "confirm":
        sys.exit("smoke and stage 1 ran with C1 as the repaired level; C2 is v1.3's, confirm only")
    global REPAIR
    REPAIR = a.repair

    chk = subprocess.run([sys.executable, "-I", str(HERE / "stage1-manifest.py"), a.data, "--check"],
                         capture_output=True, text=True)
    if chk.returncode != 0:
        sys.exit(f"manifest check failed: {chk.stdout}{chk.stderr}")
    man = json.load(open(HERE / "stage1-manifest.json"))
    man_path = HERE / "stage1-manifest.json"
    if a.phase == "confirm":
        chk = subprocess.run([sys.executable, "-I", str(HERE / "v12-manifest.py"), a.data, "--check"],
                             capture_output=True, text=True)
        if chk.returncode != 0:
            sys.exit(f"v1.2 manifest check failed: {chk.stdout}{chk.stderr}")
        man_path = HERE / "v12-manifest.json"
        if REPAIR == "C2":
            # v1.3 §14.9: the confirmatory sample is v13-manifest.json (by provenance, 242)
            chk = subprocess.run([sys.executable, "-I", str(HERE / "v13-manifest.py"), a.data,
                                  "--check"], capture_output=True, text=True)
            if chk.returncode != 0:
                sys.exit(f"v1.3 manifest check failed: {chk.stdout}{chk.stderr}")
            man_path = HERE / "v13-manifest.json"
        man = json.load(open(man_path))
    data = {r["question_id"]: r for r in json.load(open(a.data))}

    if a.phase == "smoke":
        qids, cf_ids = list(man["smoke"]), []
    elif a.phase == "stage1":
        qids, cf_ids = list(man["stage1"]), list(man["counterfactual"])
    else:
        qids, cf_ids = list(man["confirm"]), list(man["counterfactual"])
    if a.phase == "confirm":
        overlap = set(qids) & (set(man["smoke"]) | set(man["stage1"]))
        assert not overlap, f"confirmatory sample touches spent instances: {overlap}"
        if REPAIR == "C2":   # §14.9: nor any instance whose question or evidence already ran
            spent_ev = set().union(*(set(data[q]["answer_session_ids"])
                                     for q in set(man["smoke"]) | set(man["stage1"])))
            bad = [q for q in qids if q in man["counterfactual"]
                   or set(data[q]["answer_session_ids"]) & spent_ev]
            assert not bad, f"confirmatory sample holds exposed instances: {bad[:5]}"
    else:
        overlap = set(qids) & (set(man["smoke"]) if a.phase == "stage1" else set(man["stage1"]))
        assert not overlap, f"smoke and stage 1 overlap: {overlap}"

    # every (instance-variant, criterion, session, block) the run needs
    variants = {q: data[q] for q in qids}
    for q in cf_ids:
        cf = man["counterfactual_rewrite"][q]
        variants[q + "#cf"] = rewrite(data[q], cf["original"], cf["altered"])
    blocks = {}
    for vk, r in variants.items():
        crits = ("C0", REPAIR)
        for i, s in enumerate(r["haystack_sessions"]):
            if vk.endswith("#cf") and i not in evidence(r):
                pass  # unchanged session: same text as the original, same cache key
            for b, txt in enumerate(session_blocks(s)):
                for c in crits:
                    blocks[(vk, c, i, b)] = txt
    uniq = {(c, t) for (vk, c, i, b), t in blocks.items()}
    if a.yes:
        pathlib.Path(a.out).mkdir(parents=True, exist_ok=True)
    cache = Cache(str(pathlib.Path(a.out) / "cache.sqlite")) if a.yes else None
    est_d = len(uniq) * 6.22e-4
    print(f"phase {a.phase}: {len(qids)} instances + {len(cf_ids)} counterfactual variants")
    print(f"distinct (criterion, block) to distill: {len(uniq)} of {len(blocks)} referenced "
          f"-> ~US$ {est_d:.2f} at the measured US$ 6.22e-4/block")
    if not a.yes:
        print("estimate only; pass --yes to run")
        return
    led = Ledger(a.cap_usd)
    if a.phase == "confirm":
        # §14.9 / §14.10: the cap is CUMULATIVE across restarts, and only one process may own <out>.
        #  - lock: an exclusive flock on <out>/run.lock; a second process on the same out exits.
        #  - spend: each process keeps its own <out>/spend/<start>-<pid>.json, rewritten every 20
        #    ledger entries, when the cap trips, and at exit. The next process starts from the sum
        #    of all of them, so a kill -9 loses at most the last 19 entries (< US$ 1 here).
        import atexit
        import fcntl
        outp = pathlib.Path(a.out)
        lockf = open(outp / "run.lock", "w")
        try:
            fcntl.flock(lockf, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            sys.exit(f"another process holds {outp}/run.lock; one process per out dir")
        sdir = outp / "spend"
        sdir.mkdir(exist_ok=True)
        prior = sum(json.loads(f.read_text())["usd"] for f in sorted(sdir.glob("*.json")))
        mine = sdir / f"{time.strftime('%Y%m%dT%H%M%SZ', time.gmtime())}-{os.getpid()}.json"
        led.usd = prior
        print(f"cumulative spend before this process: US$ {prior:.2f} (cap {a.cap_usd})")
        wlock, nadd = threading.Lock(), [0]

        def _save():
            with wlock:
                tmp = mine.with_suffix(".tmp")
                tmp.write_text(json.dumps({"usd": round(led.usd - prior, 6), "calls": dict(led.n),
                                           "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}))
                tmp.replace(mine)
        base_add = led.add

        def _add(kind, usd):
            try:
                base_add(kind, usd)
            finally:
                nadd[0] += 1
                if nadd[0] % 20 == 0 or (led.cap and led.usd > led.cap):
                    _save()
        led.add = _add
        atexit.register(_save)
    t0 = time.time()

    # 1. distill
    todo = sorted(uniq)
    res = {}
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        for n, ((c, t), v) in enumerate(zip(todo, ex.map(lambda ct: distill(cache, led, *ct), todo))):
            res[(c, t)] = v
            if (n + 1) % 500 == 0 or n + 1 == len(todo):
                print(f"  distill {n+1}/{len(todo)} · US$ {led.usd:.2f} · {time.time()-t0:.0f}s",
                      flush=True)
    failed_blocks = sum(1 for v in res.values() if v.get("failed"))

    def units(vk, c):
        r = variants[vk]
        return [[res[(c, blocks[(vk, c, i, b)])]["units"]
                 for b in range(len(session_blocks(s)))]
                for i, s in enumerate(r["haystack_sessions"])]

    # 2. cells -> material
    jobs = []
    for vk, r in variants.items():
        q = vk.split("#")[0]
        if vk.endswith("#cf"):
            cells = ["00", "01", "10", "11"]
            ref = man["counterfactual_rewrite"][q]["altered"]
        else:
            cells = cells_for(q, man, a.phase)
            ref = str(r["answer"])
        ub = {c: units(vk, c) for c in ("C0", REPAIR)}
        mats = {}
        for cell in cells:
            if cell == "lenmatch":
                continue
            crit, sess = cell_spec(cell, r)
            mats[cell] = (crit, sess, serve(ub[crit], sess, r))
        if "lenmatch" in cells:
            mats["lenmatch"] = ("C0", mats["00"][1], pad_to(mats["00"][2], len(mats["11"][2]), r))
        ev = evidence(r)
        for cell, (crit, sess, mat) in mats.items():
            jobs.append({"variant": vk, "qid": q, "cell": cell, "criterion": crit,
                         "question_type": r["question_type"], "reference": ref,
                         "question": question_text(r), "q_plain": r["question"],
                         "sessions": len(sess), "evidence_kept": len(ev & set(sess)),
                         "evidence_total": len(ev),
                         "realised": round(sum(prose(r["haystack_sessions"][i]) for i in sess)
                                           / sum(prose(s) for s in r["haystack_sessions"]), 4),
                         "served_chars": len(mat), "material": mat})

    # 3. answer + 4. judge
    def run(j):
        av = answer(cache, led, j["material"] or "(vazio)", j["question"], reader)
        jv = judge(cache, led, j["reference"], av["text"], j["q_plain"])
        j2 = judge2(cache, led, j["reference"], av["text"], j["q_plain"])
        out = {k: v for k, v in j.items() if k != "material"}
        out.update({"answer": av["text"], "finish": av.get("finish"),
                    "answer_model_version": av.get("model_version"),
                    "abstained": abstained(av["text"]), "judge": jv,
                    "correct": (jv.get("contem") or 0) > THR,
                    "judge2": j2, "correct_j2": bool(j2.get("correta")),
                    "material_sha256": hashlib.sha256(j["material"].encode()).hexdigest()})
        return out

    rows = []
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        for n, row in enumerate(ex.map(run, jobs)):
            rows.append(row)
            if (n + 1) % 100 == 0 or n + 1 == len(jobs):
                print(f"  answer+judge {n+1}/{len(jobs)} · US$ {led.usd:.2f} · "
                      f"{time.time()-t0:.0f}s", flush=True)

    # judge preflight (§12.7): abstentions on answerable questions must be rejected
    pre = []
    if a.phase == "smoke":
        for q in qids:
            for cand in ("NAO SEI",
                         "The information is not available in the retrieved sessions; I don't know."):
                jv = judge(cache, led, str(data[q]["answer"]), cand, data[q]["question"])
                j2 = judge2(cache, led, str(data[q]["answer"]), cand, data[q]["question"])
                pre.append({"qid": q, "candidate": cand, "contem": jv.get("contem"),
                            "accepted": (jv.get("contem") or 0) > THR,
                            "accepted_j2": bool(j2.get("correta"))})

    out = pathlib.Path(a.out)
    with open(out / "rows.ndjson", "w") as f:
        for row in sorted(rows, key=lambda x: (x["variant"], x["cell"])):
            f.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
    receipt = {"phase": a.phase, "finished_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
               "seconds": round(time.time() - t0), "spend_usd_estimated": round(led.usd, 4),
               "calls": led.n, "distinct_blocks": len(uniq), "failed_blocks": failed_blocks,
               "rows": len(rows), "judge_preflight": pre,
               "manifest_sha256": hashlib.sha256(man_path.read_bytes()).hexdigest(),
               "runner_sha256": hashlib.sha256(pathlib.Path(__file__).read_bytes()).hexdigest(),
               **({"reader": reader, "reader_spec": READERS[reader][:3], "repair": REPAIR,
                   "repair_prompt_sha256": hashlib.sha256(PROMPTS[REPAIR].encode()).hexdigest()}
                  if a.phase == "confirm" else {}),
               "models": {"extractor_answerer": GMODEL, "judge": JMODEL,
                          "answer_versions": sorted({r.get("answer_model_version") or "?" for r in rows})}}
    (out / "receipt.json").write_text(json.dumps(receipt, indent=1) + "\n")
    print(json.dumps({k: receipt[k] for k in ("spend_usd_estimated", "calls", "failed_blocks", "rows")}))


if __name__ == "__main__":
    main()
