#!/usr/bin/env python3
"""Posta falhas adjudicadas na rota do componente 1 do Paper 2.

Peça que faltava: a rota `POST /internal/paper2/adjudicated-failure` está viva em
produção desde 2026-08-19 e **ninguém a chama**. Isto chama.

Desenho, e cada linha tem razão registrada:

* **`sig()` tem UMA implementação, em Python.** Este script NÃO recomputa
  assinatura: lê `sig_primary`/`sig_coarse` do output de `extract_episodes.py`
  (pipeline congelado `c0abe143`). Duas implementações escreveriam a população
  errada em silêncio.
* **A consolidação de severidade também tem uma só.** Importa
  `severidade_consolidada` de `reachable_share.py` — a mesma função que produziu
  todo número publicado. Reimplementar a mediana inferior do painel aqui seria o
  mesmo defeito de classe.
* **Texto do chunk é o template travado do §2(b)**, três linhas, sem prosa gerada.
  Vai na seção `compiled`, que é a única que passa o gate de cobertura
  (`importance` 0,90 via `Math.max`; frontmatter e timeline nascem em 0,40).
  Timeline é **omitida** de propósito: só criaria chunks inertes.
* **`S0` não escreve chunk.** O veredito é gravado (mantém o denominador de §5
  auditável) e `chunk_id` fica NULL — escrever poria não-falha na população tratada.
* **Arm-blind por construção:** este script não lê, não recebe e não pode resolver
  braço. Verificável por inspeção — nenhum import de artefato de atribuição.

O token NUNCA vem de argv (`ps` vaza) nem de repo público: só de arquivo com
permissão restrita, fora do repo.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import urllib.error
import urllib.request
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from reachable_share import severidade_consolidada  # única implementação

TEMPLATE = "Failure recorded: {sig}\nSeverity {sev}, adjudicated {data}.\nEpisode {ep}."


def carregar_episodios(p: Path) -> dict[str, dict]:
    """episode_id -> registro. Fonte de `sig_primary`/`sig_coarse`."""
    out: dict[str, dict] = {}
    for ln in p.read_text().splitlines():
        ln = ln.strip()
        if not ln:
            continue
        try:
            r = json.loads(ln)
        except json.JSONDecodeError:
            continue
        if r.get("episode_id"):
            out[r["episode_id"]] = r
    return out


def panel_hashes(p: Path) -> dict[str, str]:
    """sha256 do conjunto BRUTO de vereditos por episódio.

    Ordenado por (panelist, level, verdict) para ser estável entre execuções —
    a ordem de linha no JSONL depende de concorrência e não pode entrar no hash.
    """
    bruto: dict[str, list[tuple]] = defaultdict(list)
    for ln in p.read_text().splitlines():
        ln = ln.strip()
        if not ln:
            continue
        try:
            r = json.loads(ln)
        except json.JSONDecodeError:
            continue
        ep = r.get("episode_id")
        if not ep:
            continue
        bruto[ep].append((r.get("panelist"), r.get("level"), r.get("verdict"), r.get("status")))
    return {
        ep: hashlib.sha256(json.dumps(sorted(v), ensure_ascii=False).encode()).hexdigest()
        for ep, v in bruto.items()
    }


def conteudo(ep: str, sig: str, sev: str, data: str, nome: str) -> str:
    """Entity file de 2 seções: frontmatter + compiled. Timeline omitida.

    O `compiled` carrega EXATAMENTE o template do §2(b) — três linhas.
    """
    corpo = TEMPLATE.format(sig=sig, sev=sev, data=data, ep=ep)
    return f"---\nname: {nome}\ntype: lesson\n---\n\n{corpo}\n"


def ler_token(caminho: Path) -> str:
    if not caminho.exists():
        sys.exit(f"token não encontrado: {caminho}")
    modo = caminho.stat().st_mode & 0o777
    if modo & 0o077:
        sys.exit(f"token com permissão frouxa ({oct(modo)}) em {caminho} — use chmod 600")
    tok = caminho.read_text().strip()
    if not tok:
        sys.exit(f"token vazio em {caminho}")
    return tok


def postar(url: str, token: str, corpo: dict, timeout: float) -> tuple[int, dict]:
    req = urllib.request.Request(
        url,
        data=json.dumps(corpo, ensure_ascii=False).encode(),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, json.loads(r.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        try:
            return e.code, json.loads(e.read().decode() or "{}")
        except Exception:
            return e.code, {}
    except Exception as e:  # rede, DNS, timeout
        return 0, {"error": str(e)}


def main() -> int:
    ap = argparse.ArgumentParser(description="Posta falhas adjudicadas (Paper 2, componente 1)")
    ap.add_argument("--episodes", required=True, help="JSONL do extract_episodes.py")
    ap.add_argument("--verdicts", required=True, help="JSONL do run_panel.py")
    ap.add_argument("--endpoint", default="http://127.0.0.1:18802/internal/paper2/adjudicated-failure")
    ap.add_argument("--token-file", default=str(Path.home() / ".paper2-verdicts/.nox-api-token"))
    ap.add_argument("--log", default=str(Path.home() / ".paper2-verdicts/post-adjudicated.ndjson"),
                    help="NDJSON append-only — FORA de repo público")
    ap.add_argument("--limit", type=int, default=0, help="0 = todos")
    ap.add_argument("--timeout", type=float, default=30.0)
    ap.add_argument("--dry-run", action="store_true", help="não posta; imprime o que faria")
    ap.add_argument("--confirm", action="store_true",
                    help="obrigatório para postar de verdade (escreve em produção)")
    a = ap.parse_args()

    if not a.dry_run and not a.confirm:
        sys.exit("escrita em produção exige --confirm (ou use --dry-run)")

    eps = carregar_episodios(Path(a.episodes))
    sev_por_ep = severidade_consolidada(Path(a.verdicts), frozenset())
    hashes = panel_hashes(Path(a.verdicts))
    token = "" if a.dry_run else ler_token(Path(a.token_file))
    log = Path(a.log)

    alvos = [e for e in sev_por_ep if e in eps]
    alvos.sort()  # determinístico
    if a.limit:
        alvos = alvos[: a.limit]

    cont = {"enviados": 0, "duplicados": 0, "s0": 0, "erros": 0, "sem_sig": 0, "sem_hash": 0}
    for ep in alvos:
        sev = sev_por_ep[ep]
        reg = eps[ep]
        sig = reg.get("sig_primary")
        if not sig:
            cont["sem_sig"] += 1
            continue
        ph = hashes.get(ep)
        if not ph:
            cont["sem_hash"] += 1
            continue
        # `adjudicated_at` vem do registro do episódio; §2(c) exige o instante da
        # consolidação, não um horário de lote.
        data = (reg.get("ts") or "")[:10] or "0000-00-00"
        corpo = {
            "episode_id": ep,
            "severity": sev,
            "sig_primary": sig,
            "sig_coarse": reg.get("sig_coarse"),
            "panel_hash": ph,
            "adjudicated_at": reg.get("ts") or data,
            "content": conteudo(ep, sig, sev, data, f"failure-{ep}"),
        }
        if a.dry_run:
            print(f"  [dry-run] {ep} sev={sev} sig={sig[:28]}… "
                  f"chunk={'não (S0)' if sev == 'S0' else 'sim'}")
            cont["s0" if sev == "S0" else "enviados"] += 1
            continue

        status, resp = postar(a.endpoint, token, corpo, a.timeout)
        linha = {"episode_id": ep, "severity": sev, "status": status, "resp": resp}
        with log.open("a") as fh:
            fh.write(json.dumps(linha, ensure_ascii=False) + "\n")
        if status == 200 and resp.get("duplicate"):
            cont["duplicados"] += 1
        elif status == 200:
            cont["s0" if sev == "S0" else "enviados"] += 1
        else:
            cont["erros"] += 1
            print(f"  ERRO {ep}: HTTP {status} {resp}", file=sys.stderr)

    print(json.dumps({"alvos": len(alvos), **cont,
                      "log": None if a.dry_run else str(log)}, indent=1))
    return 1 if cont["erros"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
