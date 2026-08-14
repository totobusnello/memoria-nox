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
import subprocess
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
    ("zhipu",    "Zhipu",    "glm-5.2",     "anthropic", "https://api.z.ai/api/anthropic",
     lambda: _ler("~/.config/glm/token")),
    ("xai",      "xAI",      "grok-4.5",    "anthropic", "https://api.x.ai",
     lambda: _ler("~/.config/grok/token")),
    # Adicionado 2026-08-11 para o desenho reduzido de 3 (§9 extensao de
    # janela). Mesma familia de protocolo do zhipu/xai (Anthropic-compatible);
    # credencial ja existia (~/Claude/scripts/deepseek), so nunca tinha entrado
    # no painel de adjudicacao. Nunca medida contra as outras nesta funcao ate
    # agora — ver nota de kappa/alpha no chamador.
    ("deepseek", "DeepSeek", "deepseek-v4-pro", "anthropic", "https://api.deepseek.com/anthropic",
     lambda: _ler("~/.config/deepseek/token")),
    # Sem API key medida: entram pela conexao CLI, que carrega a credencial
    # de assinatura do titular. Custa muito mais token (o CLI sobe um agent
    # loop por chamada — medido: ~22k tokens de overhead num prompt trivial
    # do codex) e e mais lento. Decisao do titular, registrada.
    ("moonshot", "Moonshot", "k3",           "cli", "kimi",   None),
    ("openai",   "OpenAI",   "gpt-5.6-sol",  "cli", "codex",  None),
    ("google",   "Google",   "gemini-2.5-pro", "gemini",   "https://generativelanguage.googleapis.com/v1beta",
     lambda: os.environ["GEMINI_API_KEY"]),
]

# DeepSeek intercala um bloco "thinking" antes do "text" na resposta Anthropic-
# compatible (confirmado por chamada crua em 2026-08-11: prompt trivial gastou
# 57 tokens de saida so no "we are asked..."). Com max_tokens=300 (o piso que
# zhipu/xai/openai/google atendem sem missing — 1140x5=5700 bate exato na
# peca3), o thinking de um prompt real (mais longo que o smoke test) pode
# consumir o teto inteiro e devolver content=[] so com o bloco thinking — a
# MESMA armadilha do Gemini ja documentada (200 OK com conteudo vazio). Achado
# na integracao: 1 smoke test de 2 ja deu "missing" com detail="" (resposta
# vazia, nao erro). Fix: teto maior SO para quem precisa.
# 2026-08-14: `zhipu` caiu na MESMA armadilha, e por drift do provider. A API
# `api.z.ai/api/anthropic` passou a servir **glm-5.3** para o pedido `glm-5.2`
# (confirmado por chamada crua: `"model":"glm-5.3"` na resposta), e o 5.3 emite
# bloco "thinking" antes do texto. Com max_tokens=300 o JSON do veredito sai
# truncado no meio (`{"verdict": "`) ou nao sai. Efeito medido no censo do
# estrato A: **27 missing de 30**, com quota=0 — nao era cota.
#
# ⚠️ O campo `model` gravado em cada registro e o que o script PEDE, nao o que a
# API SERVE. Ele diz "glm-5.2" em todos os 3.348 vereditos do zhipu ja
# coletados, o que NAO prova que foram julgados por 5.2. Ver
# `docs/INCIDENTS.md#2026-08-14`.
MAX_TOKENS_OVERRIDE = {"deepseek": 1500, "zhipu": 1500}

# ⚠️ ANTHROPIC ficou FORA por desenho, nao por credencial: os agentes julgados
# rodam em `claude-cli`, entao Anthropic no painel seria a familia julgando a
# propria saida (§4.1, conflito ator-juiz). Para incluir, acrescente
#   ("anthropic", "Anthropic", "claude-opus-5", "cli", "claude", None)
# e o §4.1 passa a exigir o leave-one-family-out como resultado principal,
# nao como robustez.

# Como cada CLI e invocado. `stdin=True` mantem o episodio fora de `ps`.
CLIS = {
    "kimi":   {"cmd": [str(Path("~/.kimi-code/bin/kimi").expanduser()), "-p"], "stdin": False},
    "codex":  {"cmd": ["codex", "exec", "--skip-git-repo-check", "-"],        "stdin": True},
    "claude": {"cmd": ["claude", "--bare", "-p"],                             "stdin": True},
}


def chamar_cli(alvo: str, texto: str, timeout: int) -> str:
    """
    Roda o painelista pelo CLI. O CLI sobe um agent loop — mais caro e mais
    lento que a API, e o unico caminho quando a credencial e de assinatura.

    ⚠️ `kimi` nao le stdin (`-p` exige o argumento), entao o episodio vai em
    argv e fica visivel em `ps` enquanto a chamada dura. Maquina local, usuario
    unico, conteudo ja redigido — aceitavel, e declarado em vez de escondido.
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


# ─── Transporte ──────────────────────────────────────────────────────────────

def _post(url: str, headers: dict, corpo: dict, timeout: int) -> dict:
    req = urllib.request.Request(
        url, data=json.dumps(corpo).encode(), method="POST",
        headers={"Content-Type": "application/json", **headers})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read())


def chamar(protocolo: str, base: str, modelo: str, chave: str, texto: str, timeout: int,
           max_tokens: int = 300) -> tuple[str, dict]:
    """Devolve `(texto_cru, meta)`. Temperatura 0 onde o provedor aceita.

    O `meta` existe por duas falhas de 2026-08-14 que so foram diagnosticaveis
    por chamada crua fora do harness — o que significa que o harness nao estava
    registrando o que precisava.

    1. `model` SERVIDO vs PEDIDO. `api.z.ai` passou a responder **glm-5.3** a
       pedidos de `glm-5.2`. O registro gravava so o pedido, entao os 3.348
       vereditos `zhipu` ja coletados afirmam "glm-5.2" sem poder prova-lo. Um
       painel nao pode declarar sua composicao sem isto.
    2. Resposta 200 com texto VAZIO. Quando o modelo gasta o orcamento em
       blocos `thinking`, `content` vem sem nenhum bloco de texto e a
       concatenacao devolve `""`. O registro de falha gravava `detail=ultimo`,
       que nesse caso e string vazia — e foi por isso que 6 episodios ficaram
       com causa desconhecida depois de 4 tentativas. `stop_reason` e os tipos
       de bloco distinguem "truncou por max_tokens" de "recusou" de "vazio".
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
                   # Gemini 2.5 conta tokens de *thinking* contra este teto e
                   # nao aceita thinkingBudget=0 (HTTP 400). Medido: ~260 de
                   # pensamento antes da primeira palavra, entao 300 devolvia
                   # 200 OK com conteudo VAZIO — falha silenciosa que teria
                   # virado 300 veredictos "missing" sem explicacao.
                   "generationConfig": {"temperature": 0, "maxOutputTokens": 4000}}, timeout)
        cands = d.get("candidates") or [{}]
        partes = cands[0].get("content", {}).get("parts") or []
        return ("".join(p.get("text", "") for p in partes),
                {"served": d.get("modelVersion"),
                 "stop": cands[0].get("finishReason"),
                 "blocos": [("text" if "text" in p else next(iter(p), "?")) for p in partes],
                 "usage": d.get("usageMetadata")})
    if protocolo == "cli":
        # O CLI nao expoe metadados de resposta; `served` fica None em vez de
        # ecoar o pedido, para nao inventar uma confirmacao que nao existe.
        return chamar_cli(base, texto, timeout), {"served": None, "stop": None}
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
            # ── Truncamento por raciocinio: dobra o orcamento e reenvia ──────
            # Diagnosticado em 2026-08-14 nos 6 episodios que o `zhipu` recusou
            # em 4 ciclos: `stop=max_tokens` com `blocos=['thinking']` e
            # `output_tokens` batendo exatamente no teto — o modelo gastou tudo
            # pensando e nao sobrou orcamento para a resposta. Nao e conteudo
            # nem tamanho do episodio (`input_tokens` variava de 384 a 2.336).
            #
            # Dobrar e preferivel a subir a constante: um teto fixo maior paga
            # o custo em TODA chamada e continua sendo um chute que o proximo
            # modelo com raciocinio mais longo derruba de novo. Aqui so paga
            # quem precisa, e a condicao de disparo e observada, nao suposta.
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
    # ── Cota exaurida NAO e ausencia de veredito ────────────────────────────
    # `missing` significa "perguntamos e nao houve resposta utilizavel" — conta
    # contra o teto de nao-adjudicaveis do §5. Cota exaurida significa "ainda
    # nao perguntamos": a chamada esta PENDENTE e tem que ser retentada num
    # ciclo posterior. Registrar as duas como `missing` foi o que produziu
    # 88,6% de contagem PAR na peca 3 (moonshot 88/1.140) contra 8,8% na
    # calibracao, onde o painel rodou ate o fim — e paridade e o que faz um
    # parametro nao especificado mover o estudo em 20%.
    #
    # Deliberadamente conservador: so classifica como `quota` com sinal
    # inequivoco. Classificar erro comum como cota causaria retry infinito.
    baixo = ultimo.lower()
    pendente = ("usage limit" in baixo or "quota" in baixo
                or "rate limit" in baixo or "429" in baixo)
    # `detail` nunca mais pode sair vazio sem dizer por que. Quando a chamada
    # devolveu 200 com texto vazio, `ultimo` E "" — e foi exatamente isso que
    # deixou 6 episodios sem causa conhecida em 2026-08-14. O meta preenche a
    # lacuna: `stop=max_tokens` com `blocos=['thinking']` diz truncamento por
    # raciocinio; `stop=end_turn` com texto vazio diz recusa silenciosa.
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

    # Falha cedo e barato: credencial ausente vira erro agora, não depois de
    # 300 episódios (lição: preflight tem que exercer o caminho de cobrança).
    for pid, _, _, proto, base, get in painel:
        try:
            if proto == "cli":
                # Preflight do CLI: o binario tem que existir AGORA, nao no
                # episodio 200.
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
        # `status` tambem pode ser "quota" (cota do provider fechada). Contar
        # com chave fixa {"ok","missing"} estourava KeyError e derrubava o
        # sumario DEPOIS de o arquivo ja ter sido gravado — o trabalho estava
        # salvo, mas o processo saia com exit 1 e parecia falha total. Bloqueou
        # a extensao em 2026-08-12 e de novo no teste de estabilidade em 08-14.
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
