#!/usr/bin/env python3
"""
Executa o painel de adjudicação (§4.1) sobre um arquivo de episódios.

Cada painelista julga cada episódio **isolado** — sem ver os outros episódios,
sem ver o veredito de ninguém, sem ver `is_error`, sem ver o agente. O prompt é
idêntico para os cinco e vem de `adjudication_prompt.md`, cujo SHA-256 é
registrado junto com os resultados: se o prompt mudar, o hash muda e o leitor vê.

CREDENCIAIS
Lidas de arquivo/env no momento do uso e nunca impressas, nunca gravadas no
output, nunca passadas em linha de comando (onde apareceriam em `ps`).

⚠️ CONTEÚDO REAL SAI DAQUI PARA CINCO APIs EXTERNAS. Os episódios já passaram
pela redação do `extract_episodes.py`, que é rede e não garantia.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

RAIZ = Path(__file__).resolve().parent


# ─── Painelistas ─────────────────────────────────────────────────────────────
#
# Cinco famílias de treino distintas. **Anthropic ficou de fora de propósito**:
# os agentes julgados rodam em `claude-cli`, então Anthropic no painel seria a
# família julgando a própria saída (ver §4.1, conflito ator-juiz). Como há cinco
# famílias não-Anthropic disponíveis, dá para ter diversidade de procedência
# igual e conflito zero — e o painel segue ímpar, que é o que evita empate.

def _ler(p: str) -> str:
    return Path(p).expanduser().read_text().strip()


PAINEL = [
    # (id, familia, modelo, protocolo, base_url, fn-da-chave)
    ("openai",   "OpenAI",   "gpt-5.6-sol", "openai",    "https://api.openai.com/v1",
     lambda: os.environ["OPENAI_API_KEY"]),
    ("zhipu",    "Zhipu",    "glm-5.2",     "anthropic", "https://api.z.ai/api/anthropic",
     lambda: _ler("~/.config/glm/token")),
    ("xai",      "xAI",      "grok-4.5",    "anthropic", "https://api.x.ai",
     lambda: _ler("~/.config/grok/token")),
    ("moonshot", "Moonshot", "k3",          "openai",    "https://api.kimi.com/coding/v1",
     lambda: re.search(r'api_key\s*=\s*"([^"]+)"',
                       _ler("~/.kimi-code/config.toml")).group(1)),
    ("google",   "Google",   "gemini-2.5-pro", "gemini",   "https://generativelanguage.googleapis.com/v1beta",
     lambda: os.environ["GEMINI_API_KEY"]),
]


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


# ─── Transporte ──────────────────────────────────────────────────────────────

def _post(url: str, headers: dict, corpo: dict, timeout: int) -> dict:
    req = urllib.request.Request(
        url, data=json.dumps(corpo).encode(), method="POST",
        headers={"Content-Type": "application/json", **headers})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def chamar(protocolo: str, base: str, modelo: str, chave: str, texto: str, timeout: int) -> str:
    """Devolve o texto cru da resposta. Temperatura 0 onde o provedor aceita."""
    if protocolo == "anthropic":
        d = _post(f"{base}/v1/messages",
                  {"x-api-key": chave, "anthropic-version": "2023-06-01"},
                  {"model": modelo, "max_tokens": 300, "temperature": 0,
                   "messages": [{"role": "user", "content": texto}]}, timeout)
        return "".join(b.get("text", "") for b in d.get("content", []))
    if protocolo == "openai":
        d = _post(f"{base}/chat/completions",
                  {"Authorization": f"Bearer {chave}"},
                  {"model": modelo, "max_tokens": 300, "temperature": 0,
                   "messages": [{"role": "user", "content": texto}]}, timeout)
        return d["choices"][0]["message"]["content"] or ""
    if protocolo == "gemini":
        d = _post(f"{base}/models/{modelo}:generateContent",
                  {"x-goog-api-key": chave},
                  {"contents": [{"parts": [{"text": texto}]}],
                   # Gemini 2.5 conta tokens de *thinking* contra este teto e
                   # nao aceita thinkingBudget=0 (HTTP 400). Medido: ~260 de
                   # pensamento antes da primeira palavra, entao 300 devolvia
                   # 200 OK com conteudo VAZIO — falha silenciosa que teria
                   # virado 300 veredictos "missing" sem explicacao.
                   "generationConfig": {"temperature": 0, "maxOutputTokens": 4000}}, timeout)
        cands = d.get("candidates") or [{}]
        return "".join(p.get("text", "") for p in
                       (cands[0].get("content", {}).get("parts") or []))
    raise ValueError(protocolo)


_JSON = re.compile(r"\{.*?\}", re.S)

def parsear(bruto: str) -> dict | None:
    """
    Tolerante a cerca de código e a texto ao redor — mas NÃO a conteúdo ausente.
    Resposta que não parseia vira veredito ausente (§4.1), nunca abstenção:
    abstenção é decisão do painelista, falha de parse é do pipeline, e confundir
    as duas contamina o teto de não-adjudicáveis do §5.
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
    for tentativa in (1, 2):          # §4.1: um reenvio, depois conta como ausente
        try:
            ultimo = chamar(proto, base, modelo, get_chave(), texto, timeout)
            p = parsear(ultimo)
            if p:
                return {**base_reg, **p, "attempts": tentativa, "status": "ok"}
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
    return {**base_reg, "verdict": None, "level": None, "reason": "",
            "attempts": 2, "status": "missing", "detail": ultimo[:200]}


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

    # Falha cedo e barato: credencial ausente vira erro agora, não depois de
    # 300 episódios (lição: preflight tem que exercer o caminho de cobrança).
    for pid, _, _, _, _, get in painel:
        try:
            if not get():
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
        d = por_pan.setdefault(r["panelist"], {"ok": 0, "missing": 0})
        d[r["status"]] += 1
    print(json.dumps({
        "prompt_sha256": phash, "chamadas": len(res),
        "segundos": round(time.time() - t0, 1),
        "por_painelista": por_pan,
        "out": str(saida),
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
