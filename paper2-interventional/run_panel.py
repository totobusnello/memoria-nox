#!/usr/bin/env python3
"""
Runs the adjudication panel (Sec. 4.1) over a file of episodes.

Each panelist judges each episode **in isolation** — without seeing the other
episodes, without seeing anyone's verdict, without seeing `is_error`, without
seeing the agent. The prompt is identical for all five and comes from
`adjudication_prompt.md`, whose SHA-256 is recorded alongside the results: if
the prompt changes, the hash changes and the reader sees it.

CREDENTIALS
Read from file/env at the moment of use and never printed, never written to the
output, never passed on the command line (where they would appear in `ps`).

[!] REAL CONTENT LEAVES HERE FOR FIVE EXTERNAL APIs. The episodes have already
gone through the redaction in `extract_episodes.py`, which is a net, not a
guarantee.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
import subprocess
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

RAIZ = Path(__file__).resolve().parent


# --- Panelists ---------------------------------------------------------------
#
# Five distinct training families. **Anthropic was left out deliberately**: the
# agents under judgement run on `claude-cli`, so Anthropic on the panel would be
# the family judging its own output (see Sec. 4.1, actor-judge conflict). Since
# five non-Anthropic families are available, we get equal provenance diversity
# and zero conflict — and the panel stays odd, which is what avoids ties.

def _ler(p: str) -> str:
    return Path(p).expanduser().read_text().strip()


PAINEL = [
    # (id, family, model, protocol, base_url, key-fn)
    ("zhipu",    "Zhipu",    "glm-5.2",     "anthropic", "https://api.z.ai/api/anthropic",
     lambda: _ler("~/.config/glm/token")),
    ("xai",      "xAI",      "grok-4.5",    "anthropic", "https://api.x.ai",
     lambda: _ler("~/.config/grok/token")),
    # Added 2026-08-11 for the reduced 3-family design (Sec. 9 window
    # extension). Same protocol family as zhipu/xai (Anthropic-compatible); the
    # credential already existed (~/Claude/scripts/deepseek), it had simply never
    # entered the adjudication panel. Never measured against the others in this
    # role until now — see the kappa/alpha note in the caller.
    ("deepseek", "DeepSeek", "deepseek-v4-pro", "anthropic", "https://api.deepseek.com/anthropic",
     lambda: _ler("~/.config/deepseek/token")),
    # No metered API key: these come in over the CLI connection, which carries
    # the principal's subscription credential. It costs far more tokens (the CLI
    # spins up an agent loop per call — measured: ~22k tokens of overhead on a
    # trivial codex prompt) and is slower. The principal's decision, recorded.
    ("moonshot", "Moonshot", "k3",           "cli", "kimi",   None),
    ("openai",   "OpenAI",   "gpt-5.6-sol",  "cli", "codex",  None),
    ("google",   "Google",   "gemini-2.5-pro", "gemini",   "https://generativelanguage.googleapis.com/v1beta",
     lambda: os.environ["GEMINI_API_KEY"]),
]

# DeepSeek interleaves a "thinking" block before the "text" one in the
# Anthropic-compatible response (confirmed by a raw call on 2026-08-11: a
# trivial prompt spent 57 output tokens on "we are asked..." alone). With
# max_tokens=300 (the floor zhipu/xai/openai/google meet with no missing —
# 1140x5=5700 matched exactly in piece 3), the thinking of a real prompt (longer
# than the smoke test) can consume the whole ceiling and return content=[] with
# only the thinking block — the SAME trap already documented for Gemini (200 OK
# with empty content). Found during integration: 1 smoke test out of 2 already
# gave "missing" with detail="" (empty response, not an error). Fix: a larger
# ceiling ONLY for those who need it.
# 2026-08-14: `zhipu` fell into the SAME trap, and through provider drift. The
# `api.z.ai/api/anthropic` API started serving **glm-5.3** for a `glm-5.2`
# request (confirmed by a raw call: `"model":"glm-5.3"` in the response), and
# 5.3 emits a "thinking" block before the text. With max_tokens=300 the verdict
# JSON comes out truncated mid-string (`{"verdict": "`) or not at all. Measured
# effect in the stratum A census: **27 missing out of 30**, with quota=0 — it
# was not quota.
#
# [!] The `model` field recorded in each row is what the script REQUESTS, not
# what the API SERVES. It says "glm-5.2" in all 3,348 zhipu verdicts already
# collected, which does NOT prove they were judged by 5.2. See
# `docs/INCIDENTS.md#2026-08-14`.
MAX_TOKENS_OVERRIDE = {"deepseek": 1500, "zhipu": 1500}

# [!] ANTHROPIC is OUT by design, not for lack of a credential: the agents under
# judgement run on `claude-cli`, so Anthropic on the panel would be the family
# judging its own output (Sec. 4.1, actor-judge conflict). To include it, add
#   ("anthropic", "Anthropic", "claude-opus-5", "cli", "claude", None)
# and Sec. 4.1 then requires leave-one-family-out as the primary result, not as
# a robustness check.

# How each CLI is invoked. `stdin=True` keeps the episode out of `ps`.
CLIS = {
    "kimi":   {"cmd": [str(Path("~/.kimi-code/bin/kimi").expanduser()), "-p"], "stdin": False},
    "codex":  {"cmd": ["codex", "exec", "--skip-git-repo-check", "-"],        "stdin": True},
    "claude": {"cmd": ["claude", "--bare", "-p"],                             "stdin": True},
}


def chamar_cli(alvo: str, texto: str, timeout: int) -> str:
    """
    Runs the panelist through the CLI. The CLI spins up an agent loop — more
    expensive and slower than the API, and the only route when the credential is
    a subscription one.

    [!] `kimi` does not read stdin (`-p` requires the argument), so the episode
    goes in argv and is visible in `ps` for the duration of the call. Local
    machine, single user, content already redacted — acceptable, and declared
    rather than hidden.
    """
    c = CLIS[alvo]
    if c["stdin"]:
        r = subprocess.run(c["cmd"], input=texto, capture_output=True,
                           text=True, timeout=timeout, cwd="/tmp")
    else:
        r = subprocess.run([*c["cmd"], texto], capture_output=True,
                           text=True, timeout=timeout, cwd="/tmp")
    return r.stdout or r.stderr


def carregar_prompt() -> tuple[str, str]:
    raw = (RAIZ / "adjudication_prompt.md").read_text()
    corpo = raw.split("# Prompt (texto enviado a cada painelista, verbatim)", 1)[1]
    corpo = corpo.split("<!--", 1)[0].strip()
    return corpo, hashlib.sha256(corpo.encode()).hexdigest()


def montar(prompt: str, ep: dict) -> str:
    return (prompt
            .replace("{{tool}}", ep["tool"])
            .replace("{{input_excerpt}}", ep["input_excerpt"])
            .replace("{{result_excerpt}}", ep["result_excerpt"]))


# --- Transport ---------------------------------------------------------------

def _post(url: str, headers: dict, corpo: dict, timeout: int) -> dict:
    req = urllib.request.Request(
        url, data=json.dumps(corpo).encode(), method="POST",
        headers={"Content-Type": "application/json", **headers})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def chamar(protocolo: str, base: str, modelo: str, chave: str, texto: str, timeout: int,
           max_tokens: int = 300) -> tuple[str, dict]:
    """Returns `(raw_text, meta)`. Temperature 0 where the provider accepts it.

    `meta` exists because of two failures on 2026-08-14 that were only
    diagnosable by a raw call outside the harness — which means the harness was
    not recording what it needed to.

    1. `model` SERVED vs REQUESTED. `api.z.ai` began answering **glm-5.3** to
       `glm-5.2` requests. The record stored only the request, so the 3,348
       `zhipu` verdicts already collected assert "glm-5.2" without being able to
       prove it. A panel cannot declare its composition without this.
    2. A 200 response with EMPTY text. When the model spends its budget on
       `thinking` blocks, `content` arrives with no text block at all and the
       concatenation returns `""`. The failure record stored `detail=ultimo`,
       which in that case is the empty string — and that is why 6 episodes were
       left with an unknown cause after 4 attempts. `stop_reason` and the block
       types distinguish "truncated by max_tokens" from "refused" from "empty".
    """
    if protocolo == "anthropic":
        d = _post(f"{base}/v1/messages",
                  {"x-api-key": chave, "anthropic-version": "2023-06-01"},
                  {"model": modelo, "max_tokens": max_tokens, "temperature": 0,
                   "messages": [{"role": "user", "content": texto}]}, timeout)
        blocos = d.get("content", []) or []
        return ("".join(b.get("text", "") for b in blocos),
                {"served": d.get("model"), "stop": d.get("stop_reason"),
                 "blocos": [b.get("type") for b in blocos],
                 "usage": d.get("usage")})
    if protocolo == "openai":
        d = _post(f"{base}/chat/completions",
                  {"Authorization": f"Bearer {chave}"},
                  {"model": modelo, "max_tokens": max_tokens, "temperature": 0,
                   "messages": [{"role": "user", "content": texto}]}, timeout)
        ch = (d.get("choices") or [{}])[0]
        return (ch.get("message", {}).get("content") or "",
                {"served": d.get("model"), "stop": ch.get("finish_reason"),
                 "usage": d.get("usage")})
    if protocolo == "gemini":
        d = _post(f"{base}/models/{modelo}:generateContent",
                  {"x-goog-api-key": chave},
                  {"contents": [{"parts": [{"text": texto}]}],
                   # Gemini 2.5 counts *thinking* tokens against this ceiling
                   # and does not accept thinkingBudget=0 (HTTP 400). Measured:
                   # ~260 tokens of thought before the first word, so 300
                   # returned 200 OK with EMPTY content — a silent failure that
                   # would have become 300 "missing" verdicts with no
                   # explanation.
                   "generationConfig": {"temperature": 0, "maxOutputTokens": 4000}}, timeout)
        cands = d.get("candidates") or [{}]
        partes = cands[0].get("content", {}).get("parts") or []
        return ("".join(p.get("text", "") for p in partes),
                {"served": d.get("modelVersion"),
                 "stop": cands[0].get("finishReason"),
                 "blocos": [("text" if "text" in p else next(iter(p), "?")) for p in partes],
                 "usage": d.get("usageMetadata")})
    if protocolo == "cli":
        # The CLI exposes no response metadata; `served` stays None rather than
        # echoing the request, so as not to invent a confirmation that does not
        # exist.
        return chamar_cli(base, texto, timeout), {"served": None, "stop": None}
    raise ValueError(protocolo)


_JSON = re.compile(r"\{.*?\}", re.S)

def parsear(bruto: str) -> dict | None:
    """
    Tolerant of code fences and surrounding text — but NOT of absent content. A
    response that does not parse becomes an absent verdict (Sec. 4.1), never an
    abstention: abstention is the panelist's decision, a parse failure is the
    pipeline's, and conflating the two contaminates Sec. 5's unadjudicable
    ceiling.
    """
    m = _JSON.search(bruto or "")
    if not m:
        return None
    try:
        d = json.loads(m.group(0))
    except json.JSONDecodeError:
        return None
    v, lvl = d.get("verdict"), d.get("level")
    if v not in {"failure", "not_failure", "abstain"}:
        return None
    if v == "not_failure" and lvl != "S0":     return None
    if v == "failure" and lvl not in {"S1", "S2", "S3", "S4"}: return None
    if v == "abstain" and lvl is not None:     return None
    return {"verdict": v, "level": lvl, "reason": str(d.get("reason", ""))[:300]}


def julgar(pan, ep, prompt, timeout) -> dict:
    pid, familia, modelo, proto, base, get_chave = pan
    texto = montar(prompt, ep)
    base_reg = {"episode_id": ep["episode_id"], "panelist": pid,
                "family": familia, "model": modelo}
    ultimo = ""
    meta: dict = {}
    max_tok = MAX_TOKENS_OVERRIDE.get(pid, 300)
    for tentativa in (1, 2):          # §4.1: um reenvio, depois conta como ausente
        try:
            ultimo, meta = chamar(proto, base, modelo,
                                  get_chave() if get_chave else "", texto, timeout, max_tok)
            p = parsear(ultimo)
            if p:
                return {**base_reg, **p, "attempts": tentativa, "status": "ok",
                        "model_served": meta.get("served"),
                        "stop_reason": meta.get("stop")}
            # -- Reasoning truncation: double the budget and resend ----------
            # Diagnosed on 2026-08-14 in the 6 episodes `zhipu` refused across 4
            # cycles: `stop=max_tokens` with `blocos=['thinking']` and
            # `output_tokens` hitting the ceiling exactly — the model spent
            # everything thinking and had no budget left for the answer. It is
            # not content, nor episode size (`input_tokens` ranged from 384 to
            # 2,336).
            #
            # Doubling is preferable to raising the constant: a larger fixed
            # ceiling pays the cost on EVERY call and is still a guess that the
            # next longer-reasoning model knocks down again. Here only those who
            # need it pay, and the trigger condition is observed, not assumed.
            if (meta.get("stop") == "max_tokens" and not (ultimo or "").strip()
                    and tentativa == 1):
                max_tok *= 2
                continue
        except urllib.error.HTTPError as e:
            ultimo = f"HTTP {e.code}"
            if e.code in (429, 500, 502, 503, 529) and tentativa == 1:
                time.sleep(4)
                continue
            break
        except Exception as e:        # timeout, DNS, TLS…
            ultimo = f"{type(e).__name__}"
            if tentativa == 1:
                time.sleep(2)
                continue
    # -- An exhausted quota is NOT an absent verdict --------------------------
    # `missing` means "we asked and there was no usable answer" — it counts
    # against Sec. 5's unadjudicable ceiling. An exhausted quota means "we have
    # not asked yet": the call is PENDING and must be retried in a later cycle.
    # Recording both as `missing` is what produced 88.6% EVEN panel counts in
    # piece 3 (moonshot 88/1,140) against 8.8% in the calibration, where the
    # panel ran to completion — and parity is what lets an unspecified parameter
    # move the study by 20%.
    #
    # Deliberately conservative: it only classifies as `quota` on an unambiguous
    # signal. Classifying an ordinary error as quota would cause infinite
    # retries.
    baixo = ultimo.lower()
    pendente = ("usage limit" in baixo or "quota" in baixo
                or "rate limit" in baixo or "429" in baixo)
    # `detail` may never again come out empty without saying why. When the call
    # returned 200 with empty text, `ultimo` IS "" — and that is exactly what
    # left 6 episodes without a known cause on 2026-08-14. `meta` fills the gap:
    # `stop=max_tokens` with `blocos=['thinking']` says reasoning truncation;
    # `stop=end_turn` with empty text says silent refusal.
    if ultimo:
        detalhe = ultimo[:200]
    elif meta:
        detalhe = ("resposta 200 sem texto — " +
                   json.dumps({k: meta.get(k) for k in ("served", "stop", "blocos", "usage")},
                              ensure_ascii=False)[:300])
    else:
        detalhe = "sem resposta e sem metadados (falha antes do HTTP)"
    return {**base_reg, "verdict": None, "level": None, "reason": "",
            "attempts": 2, "status": "quota" if pendente else "missing",
            "model_served": meta.get("served"), "stop_reason": meta.get("stop"),
            "detail": detalhe}


def main() -> int:
    ap = argparse.ArgumentParser(description="Roda o painel de adjudicacao")
    ap.add_argument("--episodes", required=True)
    ap.add_argument("--out", required=True, help="JSONL de saida — FORA de repo publico")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--only", default="", help="ids de painelista, virgula (padrao: todos)")
    ap.add_argument("--workers", type=int, default=5)
    ap.add_argument("--timeout", type=int, default=120)
    a = ap.parse_args()

    prompt, phash = carregar_prompt()
    eps = [json.loads(l) for l in Path(a.episodes).read_text().splitlines() if l.strip()]
    if a.limit:
        eps = eps[: a.limit]
    painel = [p for p in PAINEL if not a.only or p[0] in a.only.split(",")]

    # Fail early and cheaply: a missing credential becomes an error now, not
    # after 300 episodes (lesson: preflight must exercise the billing path).
    for pid, _, _, proto, base, get in painel:
        try:
            if proto == "cli":
                # CLI preflight: the binary must exist NOW, not at episode
                # 200.
                subprocess.run([CLIS[base]["cmd"][0], "--version"],
                               capture_output=True, timeout=30, check=True)
            elif not get():
                raise ValueError("vazia")
        except Exception as e:
            print(f"ERRO: credencial de '{pid}' indisponivel ({type(e).__name__})", file=sys.stderr)
            return 2

    print(f"prompt_sha256={phash}  episodios={len(eps)}  painelistas={len(painel)}  "
          f"chamadas={len(eps)*len(painel)}", file=sys.stderr)

    tarefas = [(p, e) for e in eps for p in painel]
    t0 = time.time()
    with ThreadPoolExecutor(max_workers=a.workers) as ex:
        res = list(ex.map(lambda t: julgar(t[0], t[1], prompt, a.timeout), tarefas))

    saida = Path(a.out)
    saida.parent.mkdir(parents=True, exist_ok=True)
    saida.write_text("\n".join(json.dumps(r, ensure_ascii=False, sort_keys=True)
                               for r in sorted(res, key=lambda r: (r["episode_id"], r["panelist"]))) + "\n")

    por_pan: dict[str, dict[str, int]] = {}
    for r in res:
        # `status` can also be "quota" (the provider's quota closed). Counting
        # with a fixed {"ok","missing"} key raised KeyError and brought down the
        # summary AFTER the file had already been written — the work was saved,
        # but the process exited 1 and looked like total failure. It blocked the
        # extension on 2026-08-12 and again in the stability test on 08-14.
        d = por_pan.setdefault(r["panelist"], {"ok": 0, "missing": 0, "quota": 0})
        d[r["status"]] = d.get(r["status"], 0) + 1
    print(json.dumps({
        "prompt_sha256": phash, "chamadas": len(res),
        "pendentes_por_cota": sum(1 for r in res if r.get("status") == "quota"),
        "segundos": round(time.time() - t0, 1),
        "por_painelista": por_pan,
        "out": str(saida),
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
