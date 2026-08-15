#!/usr/bin/env python3
"""Distribuição de task regret — insumo para o `[TO LOCK: p95]` do §4.2.

O §4.2 define o desfecho secundário como *"excess time-to-resolution + token
cost vs. best known resolution of the same signature, winsorized at [TO LOCK:
p95]"*. Este script mede a distribuição de onde esse p95 sai.

⚠️ NÃO TOCA no `extract_episodes.py`. Aquele arquivo está LOCKED — commit
`c0abe143`, SHA-256 registrado em `CORPUS-FREEZE.md` — e a taxonomia de
assinaturas depende dele byte a byte. Este script **importa** as funções de
assinatura de lá e re-percorre o corpus por conta própria para colher as duas
quantidades que o extractor não emite (duração e tokens), sem alterar uma
linha do original.

O PAREAMENTO É O MESMO, DE PROPÓSITO
`tool_use` → `tool_result` por `tool_use_id`, na ordem do arquivo, com
`pendentes` descartando resultado sem uso pareado. Reproduzir a lógica em vez
de reusá-la seria arriscar divergir do corpus congelado; ela é copiada
deliberadamente, e o `episode_id` é derivado pela mesma fórmula para que as
linhas possam ser unidas ao corpus oficial.

⚠️ AMBIGUIDADE REAL NA DEFINIÇÃO, e ela não é resolvida aqui
"excess time-to-resolution **+** token cost" soma segundos com tokens, que não
têm dimensão comum. Somá-los exigiria uma taxa de conversão que o pré-registro
nunca declarou, e inventá-la agora — depois de ver os dados — seria escolher o
estimador com o resultado à vista. Este script portanto reporta os **dois
componentes separadamente**, cada um com seu p95, e deixa a escolha entre
(a) dois desfechos secundários, (b) uma soma com taxa declarada, ou (c) a
retirada do desfecho, para quem trava.

    python3 task_regret.py --raiz /var/lib/nox-mem/action-archive
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from extract_episodes import assinaturas  # LOCKED — importado, nunca modificado


def parse_ts(s: str) -> datetime | None:
    try:
        return datetime.fromisoformat((s or "").replace("Z", "+00:00"))
    except ValueError:
        return None


def tokens_da_mensagem(ev: dict) -> int | None:
    """Tokens billados da mensagem que emitiu o `tool_use`.

    Conta input + output + cache_creation, e **exclui `cache_read`**: token
    lido de cache é cobrado a fração do preço e contá-lo cheio inflaria o
    custo de sessões longas — que são exatamente as que acumulam cache. A
    escolha é conservadora para o regret (subestima o custo de sessões longas)
    e está declarada por isso.
    """
    u = (ev.get("message") or {}).get("usage")
    if not isinstance(u, dict):
        return None
    return (int(u.get("input_tokens") or 0)
            + int(u.get("output_tokens") or 0)
            + int(u.get("cache_creation_input_tokens") or 0))


def percentil(xs: list[float], p: float) -> float:
    if not xs:
        return float("nan")
    s = sorted(xs)
    if len(s) == 1:
        return s[0]
    pos = p * (len(s) - 1)
    lo = int(pos)
    return s[lo] + (pos - lo) * (s[min(lo + 1, len(s) - 1)] - s[lo])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--raiz", default="/var/lib/nox-mem/action-archive")
    ap.add_argument("--min-por-assinatura", type=int, default=5,
                    help="assinaturas com menos episodios que isto nao definem "
                         "um 'best known' confiavel e sao excluidas do regret")
    a = ap.parse_args()

    linhas: list[dict] = []
    sem_ts = sem_tokens = pares = 0
    for arq in sorted(Path(a.raiz).rglob("*.jsonl")):
        agente = arq.parent.name.replace("-root--openclaw-workspace-", "") or "workspace"
        pendentes: dict[str, dict] = {}
        try:
            conteudo_arq = arq.read_text(errors="replace").splitlines()
        except OSError:
            continue
        for linha in conteudo_arq:
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
                        "tokens": tokens_da_mensagem(ev),
                    }
                elif b.get("type") == "tool_result":
                    orig = pendentes.pop(b.get("tool_use_id"), None)
                    if orig is None:
                        continue
                    pares += 1
                    t0, t1 = parse_ts(orig["ts"]), parse_ts(ev.get("timestamp") or "")
                    if t0 is None or t1 is None:
                        sem_ts += 1
                        continue
                    dur = (t1 - t0).total_seconds()
                    if orig["tokens"] is None:
                        sem_tokens += 1
                    sig = assinaturas(orig["tool"], orig["input"])
                    bruto = (f"{agente}|{orig['session']}|{orig['ts']}|"
                             f"{orig['tool']}|{b.get('tool_use_id')}")
                    linhas.append({
                        "episode_id": hashlib.sha256(bruto.encode()).hexdigest()[:16],
                        "sig": sig["primary"],
                        "dur_s": dur,
                        "tokens": orig["tokens"],
                        "is_error": bool(b.get("is_error")),
                    })

    por_sig: dict[str, list[dict]] = collections.defaultdict(list)
    for r in linhas:
        por_sig[r["sig"]].append(r)

    # "best known resolution": o minimo observado entre episodios BEM-SUCEDIDOS
    # da mesma assinatura. Usar o minimo global (incluindo erros) daria um piso
    # artificialmente baixo — uma falha instantanea e barata, e nao e resolucao.
    regret_t: list[float] = []
    regret_k: list[float] = []
    sigs_usadas = sigs_descartadas = 0
    for sig, rs in por_sig.items():
        ok = [r for r in rs if not r["is_error"]]
        if len(ok) < a.min_por_assinatura:
            sigs_descartadas += 1
            continue
        sigs_usadas += 1
        base_t = min(r["dur_s"] for r in ok)
        com_tok = [r for r in ok if r["tokens"] is not None]
        base_k = min(r["tokens"] for r in com_tok) if com_tok else None
        for r in rs:
            regret_t.append(max(0.0, r["dur_s"] - base_t))
            if base_k is not None and r["tokens"] is not None:
                regret_k.append(max(0.0, r["tokens"] - base_k))

    def resumo(xs: list[float], nome: str) -> dict:
        return {
            "componente": nome, "n": len(xs),
            "min": round(min(xs), 3) if xs else None,
            "p50": round(percentil(xs, 0.50), 3),
            "p90": round(percentil(xs, 0.90), 3),
            "p95": round(percentil(xs, 0.95), 3),
            "p99": round(percentil(xs, 0.99), 3),
            "max": round(max(xs), 3) if xs else None,
            "razao_p99_p95": round(percentil(xs, 0.99) / percentil(xs, 0.95), 2)
            if percentil(xs, 0.95) else None,
        }

    print(json.dumps({
        "pares_tool_use_result": pares,
        "descartados_sem_timestamp": sem_ts,
        "episodios_sem_usage": sem_tokens,
        "assinaturas_usadas": sigs_usadas,
        "assinaturas_descartadas_por_n_baixo": sigs_descartadas,
        "min_por_assinatura": a.min_por_assinatura,
        "componentes": [resumo(regret_t, "excess_time_to_resolution_s"),
                        resumo(regret_k, "excess_token_cost")],
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
