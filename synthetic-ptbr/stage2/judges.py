"""Step 2 instruments: request bodies, response parsing and the citation checks.

No network here. `run.py` sends what these functions build and hands back what the API returned.
The prompt strings live in `prompts.py` (extracted by code from the sources); `jload` and `norm` are
copied from `audits/2026-10-22-gold-oracle.py` at `582a8cee`, and `test-stage2.py` compares their
text with the source.
"""
import json
import re
import unicodedata

import prompts as P

GEMINI_MODEL = "gemini-2.5-flash-lite"
DECISIONS_MODEL = "gpt-6-luna"
CUT = 6000
THRESHOLD = 0.5

# New for this step (PREREGISTRATION.md §3, J-premise): Paper A's premise-check prompt was never
# committed. This text is not a copy of anything.
PREMISE = """PERGUNTA: {q}

TRECHO:
---
{t}
---

A PERGUNTA pressupõe um fato: por exemplo, que existe uma data marcada, um preço definido ou um contrato assinado.
1. Diga, em uma frase, qual é esse fato pressuposto (a premissa).
2. Em relação à premissa, o TRECHO:
   "sustenta" — traz o dado que a PERGUNTA pressupõe existir;
   "contradiz" — diz que esse dado não existe, foi cancelado ou nunca foi definido;
   "nada_diz" — não permite decidir.

Devolva JSON: {{"premissa": "<uma frase>", "relacao": "sustenta"|"contradiz"|"nada_diz", "motivo": "<uma frase>"}}"""


def jload(txt):
    """Tolerante de proposito. Os 6 erros da primeira passagem foram TODOS de parsing,
    nao do modelo recusar: caractere de controle cru dentro de string, um segundo
    objeto JSON colado depois do primeiro ("Extra data"), escape invalido, e uma
    lista no lugar de um objeto. Nenhum deles e resposta ruim, sao formas que o
    json.loads estrito nao aceita."""
    def fix(o):
        if isinstance(o, list):
            for x in o:
                if isinstance(x, dict):
                    return x
            return None
        return o if isinstance(o, dict) else None
    for attempt in (txt, re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", txt)):
        try:
            return fix(json.loads(attempt, strict=False))
        except Exception:
            pass
        try:                                   # primeiro objeto, ignora o que vier depois
            return fix(json.JSONDecoder(strict=False).raw_decode(attempt.lstrip())[0])
        except Exception:
            pass
        m = re.search(r"[\{\[].*[\}\]]", attempt, re.S)
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


# ------------------------------------------------------------------ citation checks (§3)
def oracle_quote_ok(quote, chunk):
    """The source's check: non-empty, first 160 normalised characters are a substring."""
    return bool(quote) and norm(quote)[:160] in norm(chunk)


def whole_quote_ok(quote, chunk):
    """Added beside the source's check: the whole normalised quote is a substring."""
    return bool(quote) and norm(quote) in norm(chunk)


def eight_words_ok(q8, chunk):
    """The source's 8-word leg: 12 normalised characters and a substring (no word count)."""
    return bool(q8) and len(norm(q8)) >= 12 and norm(q8) in norm(chunk)


# ------------------------------------------------------------------ request bodies
def gemini_body(prompt, max_tokens):
    return {"contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"temperature": 0.0, "maxOutputTokens": max_tokens,
                                 "responseMimeType": "application/json"}}


MAX_TOKENS = {"closed": 1200, "oracle": 1200, "repass": 900, "pool": 700, "premise": 700}


def body(instrument, q, chunk=None, closed_answer=None):
    t = (chunk or "")[:CUT]
    if instrument == "closed":
        return gemini_body(P.CLOSED.format(q=q), MAX_TOKENS["closed"])
    if instrument == "oracle":
        return gemini_body(P.ORACLE.format(q=q, texto=t, sem=closed_answer or "NAO SEI"),
                           MAX_TOKENS["oracle"])
    if instrument == "repass":
        return gemini_body(P.REPASS.format(q=q, t=t, sem=closed_answer or "NAO SEI"),
                           MAX_TOKENS["repass"])
    if instrument == "pool":
        return gemini_body(P.POOL.format(q=q, t=t), MAX_TOKENS["pool"])
    if instrument == "premise":
        return gemini_body(PREMISE.format(q=q, t=t), MAX_TOKENS["premise"])
    if instrument in ("reg", "reg2"):
        return {"model": DECISIONS_MODEL, "input": t, "questions": [
            {"type": "predicate", "name": "contem_resposta",
             "instructions": P.REG_PREDICATE.format(q=q)},
            {"type": "score", "name": "nivel", "instructions": P.REG_LEVEL_Q.format(q=q),
             "levels": P.REG_LEVELS}]}
    if instrument == "envelope":
        return {"model": DECISIONS_MODEL, "input": f"TRECHO:\n---\n{t}\n---",
                "questions": [{"type": "predicate", "name": "relevante",
                               "instructions": P.ENVELOPE_PRED.format(q=q)}]}
    if instrument == "gold":
        return {"model": DECISIONS_MODEL, "input": f"TRECHO:\n---\n{t}\n---",
                "questions": [{"type": "predicate", "name": "responde",
                               "instructions": P.GOLD_RESPONDE.format(q=q)}]}
    raise ValueError(instrument)


GEMINI = {"closed", "oracle", "repass", "pool", "premise"}
DECISIONS_ANSWER = {"reg": "contem_resposta", "reg2": "contem_resposta",
                    "envelope": "relevante", "gold": "responde"}


# ------------------------------------------------------------------ parsing (§3, Labels)
def gemini_text(resp):
    cands = resp.get("candidates") or []
    if not cands:
        return None
    parts = cands[0].get("content", {}).get("parts") or []
    return "".join(p.get("text", "") for p in parts).strip() or None


def _bool(o, k):
    v = o.get(k)
    return v if isinstance(v, bool) else None


def parse(instrument, resp, chunk=None):
    """Return a dict with `valid` and the fields read; an invalid response is a missing label."""
    if instrument in DECISIONS_ANSWER:
        ans = {a.get("name"): a for a in resp.get("answers", []) if isinstance(a, dict)}
        a = ans.get(DECISIONS_ANSWER[instrument])
        p = a.get("probability") if a else None
        if not isinstance(p, (int, float)) or isinstance(p, bool):
            return {"valid": False}
        out = {"valid": True, "p": float(p), "label": p > THRESHOLD}
        if instrument in ("reg", "reg2"):
            s = ans.get("nivel") or {}
            out["nivel"] = s.get("score")
        return out
    txt = gemini_text(resp)
    o = jload(txt) if txt else None
    if not isinstance(o, dict):
        return {"valid": False}
    if instrument == "closed":
        r = o.get("resposta")
        return {"valid": isinstance(r, str), "resposta": r if isinstance(r, str) else None}
    if instrument == "oracle":
        # Amendment 1: a null or absent quote is an empty quote, as in the source
        # (`(j.get("citacao_verbatim") or "")`), not a missing label.
        tr, sf, q = _bool(o, "trecho_responde"), _bool(o, "sem_fonte_ja_responde"), o.get("citacao_verbatim")
        q = "" if q is None else q
        if tr is None or sf is None or not isinstance(q, str):
            return {"valid": False}
        q = q.strip()
        return {"valid": True, "label": tr, "sem_fonte_ja_responde": sf, "quote": q,
                "quote_ok": oracle_quote_ok(q, chunk), "whole_quote_ok": whole_quote_ok(q, chunk),
                "label_source_rule": tr and not sf and oracle_quote_ok(q, chunk),
                "motivo": o.get("motivo") if isinstance(o.get("motivo"), str) else None}
    if instrument in ("repass", "pool"):
        # Amendment 1: a null or absent `oito_palavras` is an empty string, as in the source
        # (`(j.get("oito_palavras") or "")`), not a missing label.
        tr, q8 = _bool(o, "trecho_responde"), o.get("oito_palavras")
        q8 = "" if q8 is None else q8
        if tr is None or not isinstance(q8, str):
            return {"valid": False}
        q8 = q8.strip()
        ok = eight_words_ok(q8, chunk)
        return {"valid": True, "label": tr, "q8": q8, "citacao_confere": ok,
                "label_with_leg": tr and ok}
    if instrument == "premise":
        rel = o.get("relacao")
        if rel not in ("sustenta", "contradiz", "nada_diz"):
            return {"valid": False}
        return {"valid": True, "relacao": rel,
                "premissa": o.get("premissa") if isinstance(o.get("premissa"), str) else None,
                "motivo": o.get("motivo") if isinstance(o.get("motivo"), str) else None}
    raise ValueError(instrument)
