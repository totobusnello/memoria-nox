"""OpenAI (authoring, rubrics) and Gemini (judge, relevance) REST clients, stdlib only.
Keys come from the environment (source /root/.openclaw/.env). The preflight records which model the
provider actually served: a provider can answer with a different model than requested."""
import json
import os
import re
import urllib.request

OPENAI_MODEL = "gpt-5.6-sol"
GEMINI_MODEL = "gemini-2.5-pro"
BRIEF_MARKERS = re.compile(r"\(chk \d+\)|# nox-mem brief|AUTO-GERADO por nox-mem-brief-refresh")


def _post(url, payload, headers, timeout=300):
    req = urllib.request.Request(url, data=json.dumps(payload).encode(), method="POST",
                                 headers={"content-type": "application/json", **headers})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def extract_json(text):
    m = re.search(r"```(?:json)?\s*(.+?)```", text, re.S)
    body = m.group(1) if m else text
    for opener, closer in (("{", "}"), ("[", "]")):
        i, j = body.find(opener), body.rfind(closer)
        if i != -1 and j > i:
            try:
                return json.loads(body[i:j + 1])
            except json.JSONDecodeError:
                continue
    raise ValueError("no JSON object in model output")


def openai_raw(prompt, model=OPENAI_MODEL):
    return _post("https://api.openai.com/v1/chat/completions",
                 {"model": model, "messages": [{"role": "user", "content": prompt}]},
                 {"authorization": f"Bearer {os.environ['OPENAI_API_KEY']}"})


def gemini_raw(prompt, model=GEMINI_MODEL):
    return _post(f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
                 {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": {"temperature": 0}},
                 {"x-goog-api-key": os.environ["GEMINI_API_KEY"]})


def openai_json(prompt, model=OPENAI_MODEL):
    r = openai_raw(prompt, model)
    return extract_json(r["choices"][0]["message"]["content"])


def gemini_json(prompt, model=GEMINI_MODEL):
    r = gemini_raw(prompt, model)
    return extract_json("".join(p.get("text", "") for p in r["candidates"][0]["content"]["parts"]))


def preflight():
    o = openai_raw('Reply with the JSON {"ok": true}')
    g = gemini_raw('Reply with the JSON {"ok": true}')
    served = {"openai": o.get("model"), "gemini": g.get("modelVersion")}
    assert str(served["openai"]).startswith(OPENAI_MODEL), served
    assert str(served["gemini"]).startswith(GEMINI_MODEL), served
    return served


def build_catalog_guard(text):
    assert not BRIEF_MARKERS.search(text), "catalog must not contain brief content (spec §2.1)"
