#!/usr/bin/env python3
"""
Extrator de episódios — a implementação canônica do `sig()` (§4.1 / §9 item 5).

Lê o arquivo de transcripts dos agentes e emite episódios candidatos: um
`tool_use` pareado com seu `tool_result`. É esta a definição de "ação
executada" sobre a qual o §4.1 constrói repeated failure.

POR QUE ISTO E NAO OUTRA COISA
O OpenClaw sobe `claude-cli` como subprocess e é o CLI que persiste
tool_use/tool_result. O store do OpenClaw não tem ação nenhuma (verificado).
Ver §9 item 0.

DETERMINISMO
Nenhum `random` sem seed, nenhum timestamp de execução no output. Rodar duas
vezes sobre o mesmo arquivo dá byte a byte o mesmo resultado — condição para
o corpus de episódios ser hasheável e o pré-registro ser checável.

⚠️ O QUE SAI DAQUI NÃO VAI PARA REPO PÚBLICO
Os episódios carregam conteúdo real de trabalho. Escreva sempre fora do repo.
Há redação de padrões óbvios de segredo, que é uma rede, não uma garantia.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from dataclasses import dataclass, asdict
from pathlib import Path

# ─── Taxonomia do sig() — três granularidades ────────────────────────────────
#
# O §5 pré-compromete robustez "um nível mais grosso e um mais fino". Isso só
# é verificável se os três níveis estiverem definidos ANTES de ver desfecho.
# As classes abaixo saíram da distribuição medida em 2026-07-26 (4.492 ações,
# 71 assinaturas no nível primário), não de introspecção.

_FAMILIA_FERRAMENTA = {
    "Read": "leitura", "Glob": "leitura", "Grep": "leitura", "NotebookRead": "leitura",
    "Write": "escrita", "Edit": "escrita", "NotebookEdit": "escrita",
    "Bash": "execucao", "BashOutput": "execucao", "KillShell": "execucao",
    "Task": "delegacao", "ToolSearch": "busca", "WebSearch": "busca", "WebFetch": "busca",
}

def familia_ferramenta(tool: str) -> str:
    if tool in _FAMILIA_FERRAMENTA:
        return _FAMILIA_FERRAMENTA[tool]
    if tool.startswith("mcp__"):
        return "mcp"
    return "outro"


def classe_alvo(inp: dict | None) -> str:
    """Classe do ALVO, nunca o valor literal — o literal é ilimitado e não agrega."""
    if not isinstance(inp, dict):
        return "sem-alvo"
    g = lambda k: inp[k] if isinstance(inp.get(k), str) else ""
    caminho = g("file_path") or g("path") or g("notebook_path")
    if caminho:
        if re.search(r"\.(test|spec)\.[jt]sx?$", caminho):      return "arquivo:teste"
        if re.search(r"/(src|lib)/", caminho):                   return "arquivo:fonte"
        if re.search(r"\.(md|txt|rst)$", caminho, re.I):         return "arquivo:doc"
        if re.search(r"\.(json|ya?ml|toml|conf|env)$", caminho, re.I): return "arquivo:config"
        if re.search(r"\.(db|sqlite3?)$", caminho, re.I):        return "arquivo:banco"
        if re.search(r"\.(sh|bash|zsh)$", caminho, re.I):        return "arquivo:script"
        return "arquivo:outro"
    cmd = g("command")
    if cmd:
        c = cmd.strip().split()[0].split("/")[-1] if cmd.strip() else ""
        if c == "git":
            partes = cmd.strip().split()
            sub = partes[1] if len(partes) > 1 else ""
            return "git:mutacao" if sub in {
                "push", "commit", "merge", "rebase", "reset", "checkout", "cherry-pick", "tag"
            } else "git:leitura"
        if c in {"npm", "pnpm", "yarn", "npx", "tsc", "node", "python", "python3", "pytest"}: return "build/run"
        if c in {"systemctl", "service", "journalctl"}:                                        return "servico"
        if c in {"sqlite3", "psql", "redis-cli"}:                                              return "banco"
        if c in {"rm", "mv", "cp", "chmod", "chown", "mkdir", "ln", "truncate"}:               return "fs:mutacao"
        if c in {"ls", "cat", "grep", "rg", "find", "head", "tail", "wc", "jq", "awk", "sed",
                 "du", "df", "stat"}:                                                          return "fs:leitura"
        if c in {"ssh", "scp", "curl", "wget", "gh"}:                                          return "rede"
        if c in {"crontab", "at"}:                                                             return "agendamento"
        return "shell:outro"
    if inp.get("query") or inp.get("pattern"): return "consulta"
    if inp.get("prompt"):                      return "delegacao"
    if inp.get("url"):                         return "rede"
    return "sem-alvo"


_FAMILIA_ALVO = {
    "arquivo:teste": "arquivo", "arquivo:fonte": "arquivo", "arquivo:doc": "arquivo",
    "arquivo:config": "arquivo", "arquivo:banco": "arquivo", "arquivo:script": "arquivo",
    "arquivo:outro": "arquivo", "fs:mutacao": "arquivo", "fs:leitura": "arquivo",
    "git:mutacao": "vcs", "git:leitura": "vcs",
    "build/run": "processo", "servico": "processo", "shell:outro": "processo",
    "banco": "estado", "agendamento": "estado",
    "rede": "externo", "consulta": "externo", "delegacao": "externo",
}

def sub_comando(inp: dict | None) -> str:
    """Refinamento do nível fino: o verbo real, quando existe."""
    if not isinstance(inp, dict):
        return ""
    cmd = inp.get("command")
    if isinstance(cmd, str) and cmd.strip():
        partes = cmd.strip().split()
        base = partes[0].split("/")[-1]
        return f"{base}:{partes[1]}" if base == "git" and len(partes) > 1 else base
    return ""


def assinaturas(tool: str, inp: dict | None) -> dict[str, str]:
    """Os três níveis. `primary` é o que o §4.1 usa; os outros são a robustez."""
    alvo = classe_alvo(inp)
    fam_alvo = _FAMILIA_ALVO.get(alvo, "outro")
    fino = sub_comando(inp)
    return {
        "coarse":  f"{familia_ferramenta(tool)}|{fam_alvo}",
        "primary": f"{tool}|{alvo}",
        "fine":    f"{tool}|{alvo}|{fino}" if fino else f"{tool}|{alvo}",
    }


# ─── Redação ─────────────────────────────────────────────────────────────────
# Rede, não garantia. O corpus vai para um painel de LLM externo; um token que
# escapar daqui escapou de vez.
_SEGREDOS = [
    (re.compile(r"\b(sk-[A-Za-z0-9_\-]{16,})"), "[REDACTED:api-key]"),
    (re.compile(r"\b(AQ\.[A-Za-z0-9_\-]{16,})"), "[REDACTED:gemini-key]"),
    (re.compile(r"\b(gh[pousr]_[A-Za-z0-9]{16,})"), "[REDACTED:gh-token]"),
    (re.compile(r"\b(eyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,})"), "[REDACTED:jwt]"),
    (re.compile(r"(?i)\b((?:api[_-]?key|token|secret|password|passwd)\s*[=:]\s*)\S+"), r"\1[REDACTED]"),
    (re.compile(r"\b(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})\b"), "[REDACTED:ip]"),
    (re.compile(r"\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b"), "[REDACTED:email]"),
]

def redigir(s: str) -> str:
    for padrao, sub in _SEGREDOS:
        s = padrao.sub(sub, s)
    return s


def truncar(v, limite: int) -> str:
    s = v if isinstance(v, str) else json.dumps(v, ensure_ascii=False, sort_keys=True)
    s = redigir(s)
    return s if len(s) <= limite else s[:limite] + f"…[+{len(s)-limite} chars]"


@dataclass(frozen=True)
class Episodio:
    episode_id: str      # hash estavel: mesmo episodio => mesmo id, sempre
    agent: str
    session: str
    ts: str
    tool: str
    sig_coarse: str
    sig_primary: str
    sig_fine: str
    is_error: bool
    input_excerpt: str
    result_excerpt: str


def extrair(raiz: Path, max_chars: int) -> list[Episodio]:
    saida: list[Episodio] = []
    for arq in sorted(raiz.rglob("*.jsonl")):       # sorted => determinismo
        agente = arq.parent.name.replace("-root--openclaw-workspace-", "") or "workspace"
        pendentes: dict[str, dict] = {}
        try:
            linhas = arq.read_text(errors="replace").splitlines()
        except OSError:
            continue
        for linha in linhas:
            if "tool_use" not in linha and "tool_result" not in linha:
                continue
            try:
                ev = json.loads(linha)
            except json.JSONDecodeError:
                continue
            conteudo = (ev.get("message") or {}).get("content")
            if not isinstance(conteudo, list):
                continue
            for b in conteudo:
                if not isinstance(b, dict):
                    continue
                if b.get("type") == "tool_use" and b.get("id"):
                    pendentes[b["id"]] = {
                        "tool": b.get("name") or "?", "input": b.get("input"),
                        "ts": ev.get("timestamp") or "", "session": arq.stem,
                    }
                elif b.get("type") == "tool_result":
                    orig = pendentes.pop(b.get("tool_use_id"), None)
                    if orig is None:
                        continue     # resultado sem uso pareado: sessao truncada pelo prune
                    sig = assinaturas(orig["tool"], orig["input"])
                    bruto = f"{agente}|{orig['session']}|{orig['ts']}|{orig['tool']}|{b.get('tool_use_id')}"
                    saida.append(Episodio(
                        episode_id=hashlib.sha256(bruto.encode()).hexdigest()[:16],
                        agent=agente, session=orig["session"], ts=orig["ts"],
                        tool=orig["tool"], sig_coarse=sig["coarse"],
                        sig_primary=sig["primary"], sig_fine=sig["fine"],
                        is_error=bool(b.get("is_error")),
                        input_excerpt=truncar(orig["input"], max_chars),
                        result_excerpt=truncar(b.get("content"), max_chars),
                    ))
    # Ordenacao canonica: o corpus tem que hashear igual em qualquer maquina.
    saida.sort(key=lambda e: (e.ts, e.episode_id))
    return saida


def amostrar(eps: list[Episodio], n: int, seed: str) -> list[Episodio]:
    """
    Amostra por hash, não por PRNG: reprodutível sem depender da implementação
    de `random` de nenhuma versão de Python. Estratificada por assinatura, para
    que o calibration set cubra a cauda em vez de só o `Bash` mais comum — é a
    cauda que decide se a rubrica é usável.
    """
    por_sig: dict[str, list[Episodio]] = {}
    for e in eps:
        por_sig.setdefault(e.sig_primary, []).append(e)
    for lista in por_sig.values():
        lista.sort(key=lambda e: hashlib.sha256((seed + e.episode_id).encode()).hexdigest())

    escolhidos: list[Episodio] = []
    i = 0
    while len(escolhidos) < n:
        rodada = [l[i] for l in (por_sig[k] for k in sorted(por_sig)) if len(l) > i]
        if not rodada:
            break                                   # esgotou o corpus
        escolhidos.extend(rodada[: n - len(escolhidos)])
        i += 1
    return escolhidos


def main() -> int:
    ap = argparse.ArgumentParser(description="Extrai episodios candidatos para adjudicacao")
    ap.add_argument("--raiz", default="/var/lib/nox-mem/action-archive")
    ap.add_argument("--out", required=True, help="JSONL de saida — FORA de repo publico")
    ap.add_argument("--sample", type=int, default=0, help="0 = tudo; N = calibration set de N")
    ap.add_argument("--seed", default="", help="obrigatorio com --sample; derive do beacon")
    ap.add_argument("--only-errors", action="store_true", help="so is_error (candidatos a falha)")
    ap.add_argument("--max-chars", type=int, default=4000)
    a = ap.parse_args()

    if a.sample and not a.seed:
        print("ERRO: --sample exige --seed. Amostra sem seed declarada nao e pre-registravel.",
              file=sys.stderr)
        return 2

    eps = extrair(Path(a.raiz), a.max_chars)
    if a.only_errors:
        eps = [e for e in eps if e.is_error]
    total = len(eps)
    if a.sample:
        eps = amostrar(eps, a.sample, a.seed)

    saida = Path(a.out)
    saida.parent.mkdir(parents=True, exist_ok=True)
    corpo = "\n".join(json.dumps(asdict(e), ensure_ascii=False, sort_keys=True) for e in eps)
    saida.write_text(corpo + ("\n" if corpo else ""))

    h = hashlib.sha256(corpo.encode()).hexdigest()
    sigs = {e.sig_primary for e in eps}
    erros = sum(1 for e in eps if e.is_error)
    print(json.dumps({
        "corpus_total": total, "emitidos": len(eps), "is_error": erros,
        "assinaturas_primary": len(sigs),
        "assinaturas_coarse": len({e.sig_coarse for e in eps}),
        "assinaturas_fine": len({e.sig_fine for e in eps}),
        "sha256": h, "out": str(saida),
    }, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
