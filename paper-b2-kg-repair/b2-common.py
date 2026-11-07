"""Shared pieces of Paper B2 (PREREGISTRATION.md): the repair prompt, the call to the repairer
through `claude -p`, its cache and ledger. Paper B's own module is loaded for the citation check,
the judges, the draw helpers and the public-history checks, so B2 never reimplements them.

Stdlib only; run with `python3 -I`.
"""
import importlib.util
import json
import os
import pathlib
import subprocess
import tempfile

HERE = pathlib.Path(__file__).resolve().parent
ROOT = HERE.parent
D = "paper-b2-kg-repair"
TAG = "paper-b2-prereg-v1.0"
CAP_USD = 20.0                  # §6: repair and rewrite judging together
REPAIRER = {"name": "repairer", "family": "anthropic", "model": "claude-opus-5-5",
            "effort": "medium"}


def _load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


B = _load("b_common", ROOT / "paper-b-kg" / "b-common.py")

SYSTEM = """Você mantém um grafo de conhecimento. Agentes recuperam as relações dele como fatos, então
uma relação deve afirmar só o que o trecho de evidência sustenta. Você recebe UMA relação (tripla)
e o TRECHO registrado como sua evidência, e decide uma ação:

- "keep": o trecho sustenta a tripla como está escrita.
- "rewrite": o trecho não sustenta a tripla como está, mas sustenta uma relação entre as mesmas
  duas entidades, ou entre entidades nomeadas no trecho; devolva essa tripla corrigida.
- "delete": o trecho não sustenta a tripla e não há reescrita que ele sustente.

O que conta como sustentado:
- Os dois lados têm de aparecer no trecho, ou ser inequívocos a partir dele.
- A relação tem de ser a que o trecho afirma. "Aparecem na mesma frase" NÃO é relação, a menos
  que a relação declarada seja exatamente de menção conjunta.
- Se a tripla INVERTE a relação (troca quem faz e quem sofre, ou afirma o que o trecho exclui),
  ela NÃO é sustentada, mesmo com as duas entidades lado a lado e uma frase literal.
- Se o predicado é mais pobre ou mais genérico que o trecho, mas não o contradiz nem o inverte,
  a tripla É sustentada.
- Um nome de exemplo dentro de um exemplo ilustrativo (um modelo, um marcador de lugar como
  "Fulano", "X" ou "<nome>") não é uma entidade: a tripla que o usa NÃO é sustentada.
- Formatação (negrito, tabelas, pontuação, quebras de linha) nunca é motivo para rejeitar.

Para "keep" e "rewrite", copie em "oito_palavras" as 8 primeiras palavras da frase do trecho que
sustenta a tripla final, exatamente como aparecem. Para "rewrite", preencha "nova_origem",
"novo_predicado" e "novo_destino". Para "delete", deixe esses campos e "oito_palavras" vazios.
Em "motivo", uma frase."""

SCHEMA = {
    "type": "object",
    "properties": {
        "acao": {"type": "string", "enum": ["keep", "rewrite", "delete"]},
        "oito_palavras": {"type": "string"},
        "nova_origem": {"type": "string"},
        "novo_predicado": {"type": "string"},
        "novo_destino": {"type": "string"},
        "motivo": {"type": "string"},
    },
    "required": ["acao", "oito_palavras", "nova_origem", "novo_predicado", "novo_destino",
                 "motivo"],
    "additionalProperties": False,
}


def user_message(item, text):
    return ("TRIPLA:  ({s}) --[{p}]--> ({o})\n\nTRECHO (a evidência registrada):\n---\n{t}\n---"
            .format(s=item["source"], p=item["predicate"], o=item["target"],
                    t=(text or "")[:B.CHUNK_CHARS]))


def claude_cmd(model=REPAIRER["model"], effort=REPAIRER["effort"]):
    """`claude -p` on the author's subscription (decision 2026-11-07, «Via claude -p»): our system
    prompt replaces Claude Code's, no tools, no MCP server, no setting source (so no hook and no
    CLAUDE.md), no session kept, structured output against SCHEMA."""
    return ["claude", "-p", "--model", model, "--effort", effort,
            "--system-prompt", SYSTEM, "--tools", "", "--strict-mcp-config",
            "--mcp-config", '{"mcpServers":{}}', "--setting-sources", "",
            "--no-session-persistence", "--output-format", "json",
            "--json-schema", json.dumps(SCHEMA)]


def call_claude(msg, timeout=600, runner=subprocess.run):
    """One call. Returns (answer dict or None, record). The record keeps what the CLI reports:
    served model, tokens (thinking included) and the list-price cost it computes."""
    with tempfile.TemporaryDirectory(prefix="b2-") as cwd:   # empty cwd: nothing to discover
        p = runner(claude_cmd(), input=msg, capture_output=True, text=True, timeout=timeout,
                   cwd=cwd)
    if p.returncode != 0:
        raise RuntimeError(f"claude -p rc={p.returncode}: {p.stderr[-300:]}")
    d = json.loads(p.stdout)
    mu = d.get("modelUsage") or {}
    served = sorted(mu)
    u = d.get("usage") or {}
    rec = {"served": served, "usd": float(d.get("total_cost_usd") or 0.0),
           "tin": int(u.get("input_tokens") or 0) + int(u.get("cache_creation_input_tokens") or 0)
           + int(u.get("cache_read_input_tokens") or 0),
           "tout": int(u.get("output_tokens") or 0),
           "thinking": int((u.get("output_tokens_details") or {}).get("thinking_tokens") or 0),
           "is_error": bool(d.get("is_error")), "subtype": d.get("subtype"),
           "stop": d.get("stop_reason")}
    ans = d.get("structured_output")
    if not isinstance(ans, dict) or ans.get("acao") not in ("keep", "rewrite", "delete"):
        ans = None
    return ans, rec


def repair_one(cache, led, item, text, caller=call_claude):
    """§3: one action per relation, asked once and cached; a refusal or an unreadable answer is
    counted and the relation is kept unchanged."""
    msg = user_message(item, text)
    k = B.sha_bytes(json.dumps([REPAIRER["model"], REPAIRER["effort"], SYSTEM, msg]).encode())
    hit = cache.get(k)
    if hit is not None:
        led.cached += 1
        return hit
    ans, rec = caller(msg)
    led.add(rec["usd"])
    if ans is None:
        v = {"action": "keep", "no_answer": True, "quote": "", "quote_ok": False}
    else:
        q = (ans.get("oito_palavras") or "").strip()
        v = {"action": ans["acao"], "no_answer": False, "quote": q[:300],
             "quote_ok": B.quote_ok(q, text) if ans["acao"] != "delete" else False,
             "new": ({"source": ans["nova_origem"][:300], "predicate": ans["novo_predicado"][:200],
                      "target": ans["novo_destino"][:300]} if ans["acao"] == "rewrite" else None),
             "reason": str(ans.get("motivo") or "")[:300]}
    v.update({k2: rec[k2] for k2 in ("served", "usd", "tin", "tout", "thinking", "stop")})
    cache.put(k, v)
    return v
