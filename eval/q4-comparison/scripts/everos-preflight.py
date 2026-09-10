#!/usr/bin/env python3
"""
Preflight PAGO do EverOS — decide se a corrida completa vale o gasto.

Verifica com ~5 documentos aquilo que a assinatura NÃO prova:
  1. a chave `AQ.` do Gemini atende o endpoint OpenAI-compatível do everos;
  2. `create_document(doc_id=X)` devolve `doc_id == X` (não sobrescreve);
  3. `search_knowledge()` devolve `SearchHit.document.doc_id` igual ao id do chunk;
  4. quantos TÓPICOS um documento gera (o fator de colapso real, não o suposto).

Se (2) ou (3) falharem, as 6.830 extrações da corrida completa saem inúteis.

Uso:
    .venv/bin/python scripts/everos-preflight.py [--n 5]
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path

AQUI = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AQUI))

BASE = "https://generativelanguage.googleapis.com/v1beta/openai/"


def env_gemini(raiz: Path) -> None:
    chave = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not chave:
        sys.exit("GEMINI_API_KEY ausente no env")
    os.environ.update(
        {
            "EVEROS_ROOT": str(raiz),
            "EVEROS_EVAL_ROOT": str(raiz),
            "EVEROS_LLM__MODEL": os.environ.get("EVEROS_LLM__MODEL", "gemini-2.5-flash-lite"),
            "EVEROS_LLM__API_KEY": chave,
            "EVEROS_LLM__BASE_URL": BASE,
            "EVEROS_EMBEDDING__MODEL": "gemini-embedding-001",
            "EVEROS_EMBEDDING__API_KEY": chave,
            "EVEROS_EMBEDDING__BASE_URL": BASE,
            # 3072d: o que o gemini-embedding-001 devolve sem output_dimensionality,
            # e o que o nox-mem roda em produção — não baixar, reintroduz confound.
            "EVEROS_EMBEDDING__DIMENSIONS": "3072",
            "EVEROS_ALLOW_PAID_INGEST": "1",
        }
    )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=5)
    ap.add_argument("--raiz", default="/private/var/tmp/everos-preflight")
    a = ap.parse_args()

    raiz = Path(a.raiz)
    env_gemini(raiz)

    import adapters.evermind as ad

    v = ad.validate()
    print(f"[1] validate: ok={v['ok']} version={v['version']} erro={v.get('error')}")
    if not v["ok"]:
        return 1

    # Documentos curtos e com id RECONHECÍVEL, do corpus real.
    chunks = []
    with (AQUI / "cache" / "locomo.jsonl").open() as fh:
        for linha in fh:
            linha = linha.strip()
            if not linha:
                continue
            d = json.loads(linha)
            if 80 <= len(d.get("text", "")) <= 400:
                chunks.append(d)
            if len(chunks) >= a.n:
                break
    print(f"[2] {len(chunks)} documentos do corpus real, ids: {[c['id'] for c in chunks]}")

    t0 = time.perf_counter()
    r = ad.ingest_corpus(chunks)
    dt = time.perf_counter() - t0
    print(f"[3] ingest em {dt:.1f}s: {json.dumps({k: v for k, v in r.items() if k != 'estimate'})}")
    if r["ingested"] == 0:
        print("    ABORTA: nada ingerido")
        return 1

    # A pergunta que decide o gasto: o id do chunk voltou?
    consulta = chunks[0]["text"][:120]
    hits = ad.search(consulta, k=5)
    print(f"[4] search({consulta[:48]!r}…) -> {len(hits)} doc_ids distintos")
    for h in hits:
        print(f"      id={h['id']!r} score={h['score']:.4f} topics_seen={h['topics_seen']} topic={h.get('topic_name')!r}")

    ids_ingeridos = {c["id"] for c in chunks}
    ids_devolvidos = {h["id"] for h in hits}
    intersecao = ids_ingeridos & ids_devolvidos

    print()
    print("=== VEREDITO ===")
    print(f"  ids ingeridos     : {sorted(ids_ingeridos)}")
    print(f"  ids devolvidos    : {sorted(ids_devolvidos)}")
    print(f"  round-trip do id  : {'SIM' if intersecao else 'NAO'} ({len(intersecao)}/{len(ids_ingeridos)})")
    print(f"  topicos/documento : {r.get('topics_per_doc')}")
    print(f"  s/documento       : {dt / max(1, r['ingested']):.2f}")
    est = r["estimate"]
    print(f"  extrapolacao 6830 : {dt / max(1, r['ingested']) * 6830 / 60:.0f} min de ingestao")
    ad.teardown()

    if not intersecao:
        print()
        print("  🔴 O id do chunk NAO volta. A corrida completa seria dinheiro perdido:")
        print("     sem essa volta, o nDCG@10 sobre gold_chunk_ids e' indefinido.")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
