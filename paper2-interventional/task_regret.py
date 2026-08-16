#!/usr/bin/env python3
"""Task-regret distribution — input for the `[TO LOCK: p95]` of Sec. 4.2.

Sec. 4.2 defines the secondary outcome as *"excess time-to-resolution + token
cost vs. best known resolution of the same signature, winsorized at [TO LOCK:
p95]"*. This script measures the distribution that p95 comes from.

[!] IT DOES NOT TOUCH `extract_episodes.py`. That file is LOCKED — commit
`c0abe143`, SHA-256 registered in `CORPUS-FREEZE.md` — and the signature
taxonomy depends on it byte for byte. This script **imports** the signature
functions from there and re-walks the corpus on its own to collect the two
quantities the extractor does not emit (duration and tokens), without changing
a line of the original.

THE PAIRING IS THE SAME, DELIBERATELY
`tool_use` -> `tool_result` by `tool_use_id`, in file order, with `pendentes`
discarding any result without a paired use. Reimplementing the logic rather
than reusing it would risk diverging from the frozen corpus; it is copied
deliberately, and `episode_id` is derived by the same formula so that rows can
be joined to the official corpus.

[!] A REAL AMBIGUITY IN THE DEFINITION, and it is not resolved here
"excess time-to-resolution **+** token cost" adds seconds to tokens, which have
no common dimension. Summing them would require a conversion rate the
pre-registration never declared, and inventing one now — after seeing the data
— would mean choosing the estimator with the result in view. This script
therefore reports the **two components separately**, each with its own p95, and
leaves the choice between (a) two secondary outcomes, (b) a sum with a declared
rate, or (c) dropping the outcome, to whoever locks it.

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
    """Billed tokens of the message that emitted the `tool_use`.

    Counts input + output + cache_creation, and **excludes `cache_read`**: a
    cached-read token is billed at a fraction of the price and counting it at
    full rate would inflate the cost of long sessions — which are exactly the
    ones that accumulate cache. The choice is conservative for regret (it
    understates the cost of long sessions) and is declared for that reason.
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
                    help="signatures with fewer episodes than this do not define "
                         "a reliable 'best known' and are excluded from the regret")
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

    # "best known resolution": the minimum observed among SUCCESSFUL episodes of
    # the same signature. Using the global minimum (errors included) would give
    # an artificially low floor — a failure is instant and cheap, and a failure
    # is not a resolution.
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
