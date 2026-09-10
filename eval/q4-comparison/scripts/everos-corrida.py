#!/usr/bin/env python3
"""
Corrida PAGA de ingestao do EverOS — 6.830 documentos, retomavel.

⚠️ PAGA: uma extracao de LLM por documento (create_document) + uma embedding por
topico (cascade sync). Autorizada pelo Toto em 2026-09-10. NAO precisa de reranker
— esse so entra na BUSCA.

Desenho, e cada peca responde a uma falha ja vivida:

  LEDGER  Um `doc_id` por linha, gravado APOS o create bem-sucedido. Nao dependo do
          `doc_id_exists()` do EverOS para retomar porque ele consulta
          `knowledge_documents`, tabela que so e' populada pelo cascade — um resume
          ingenuo recriaria markdown de tudo que foi criado e ainda nao sincronizado.

  PRAZO   Parada por DEADLINE DE PARELHE (--deadline-min), nao por contagem. Loop
          limitado por iteracoes sai `exit 0` e meio-feito, e o meio-feito le-se
          como concluido.

  SYNC    `cascade sync` a cada --sync-cada documentos, nao so no fim. Torna o
          progresso duravel: se a corrida morrer, o que ja foi sincronizado esta'
          buscavel e o ledger diz exatamente onde retomar.

  RECIBO  NDJSON por lote com ts, feitos, restantes, s/doc, ETA e chars. Um recibo
          que omite a entrada decisiva e' ininterpretavel, entao o `sha256` do
          corpus e a contagem entram na primeira linha.

Uso:
    .venv/bin/python scripts/everos-corrida.py \
        --corpus cache/locomo.jsonl --corpus cache/longmemeval.jsonl \
        --raiz /var/tmp/everos-q4 --out out/everos-corrida \
        --deadline-min 600 --sync-cada 500
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path

AQUI = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(AQUI))

BASE = "https://generativelanguage.googleapis.com/v1beta/openai/"


def prepara_env(raiz: Path) -> None:
    chave = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not chave:
        sys.exit("GEMINI_API_KEY ausente")
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
            "EVEROS_EMBEDDING__DIMENSIONS": "3072",
            "EVEROS_ALLOW_PAID_INGEST": "1",
        }
    )


def carrega(caminhos: list[Path]) -> tuple[list[dict], str]:
    h = hashlib.sha256()
    itens: list[dict] = []
    for c in sorted(caminhos):
        dados = c.read_bytes()
        h.update(dados)
        for linha in dados.decode().splitlines():
            linha = linha.strip()
            if not linha:
                continue
            d = json.loads(linha)
            if d.get("id") and d.get("text"):
                itens.append(d)
    return itens, h.hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", action="append", required=True, type=Path)
    ap.add_argument("--raiz", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--deadline-min", type=float, default=600.0)
    ap.add_argument("--sync-cada", type=int, default=500)
    a = ap.parse_args()

    a.out.mkdir(parents=True, exist_ok=True)
    ledger = a.out / "ledger-criados.txt"
    recibo = a.out / "progresso.ndjson"

    prepara_env(a.raiz)
    import adapters.evermind as ad

    v = ad.validate()
    if not v["ok"]:
        sys.exit(f"validate falhou: {v['error']}")

    itens, sha = carrega(a.corpus)
    feitos = set()
    if ledger.exists():
        feitos = {l.strip() for l in ledger.read_text().splitlines() if l.strip()}
    pendentes = [d for d in itens if d["id"] not in feitos]

    fim = time.time() + a.deadline_min * 60
    cab = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "evento": "arranque",
        "corpus": [str(c) for c in a.corpus],
        "corpus_sha256": sha,
        "documentos_total": len(itens),
        "ja_no_ledger": len(feitos),
        "pendentes": len(pendentes),
        "chars_pendentes": sum(len(d["text"]) for d in pendentes),
        "deadline_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime(fim)),
        "raiz": str(a.raiz),
        "everos": v["version"],
    }
    with recibo.open("a") as fh:
        fh.write(json.dumps(cab) + "\n")
    print(json.dumps(cab), flush=True)

    ad.setup()
    from everalgo.types import ParsedContent
    from everos.service.knowledge import create_document

    t0 = time.time()
    ok = falhas = desde_sync = 0
    erros: list[str] = []

    def sincroniza(motivo: str) -> None:
        nonlocal desde_sync
        t = time.time()
        try:
            n = ad._loop.run_until_complete(ad._indexa())
            evt = {"evento": "sync", "motivo": motivo, "linhas": n, "s": round(time.time() - t, 1)}
        except Exception as exc:
            evt = {"evento": "sync_falhou", "motivo": motivo, "erro": f"{type(exc).__name__}: {exc}"}
        evt["ts"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        with recibo.open("a") as fh:
            fh.write(json.dumps(evt) + "\n")
        print(json.dumps(evt), flush=True)
        desde_sync = 0

    for i, d in enumerate(pendentes, 1):
        if time.time() >= fim:
            print(json.dumps({"evento": "deadline", "feitos": ok, "restantes": len(pendentes) - i + 1}), flush=True)
            break
        try:
            ad._loop.run_until_complete(
                create_document(
                    extractor=ad.extractor(),
                    parsed=ParsedContent(text=d["text"]),
                    title=str(d["id"]),
                    knowledge_dir=ad._knowledge_dir,
                    source_name=str(d.get("dataset") or "q4"),
                    source_type="text",
                    doc_id=str(d["id"]),
                )
            )
            ok += 1
            desde_sync += 1
            with ledger.open("a") as fh:  # ledger APOS o sucesso
                fh.write(d["id"] + "\n")
        except Exception as exc:
            falhas += 1
            if len(erros) < 20:
                erros.append(f"{d['id']}: {type(exc).__name__}: {exc}")

        if desde_sync >= a.sync_cada:
            sincroniza(f"lote-{ok}")

        if i % 100 == 0:
            dt = time.time() - t0
            evt = {
                "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "evento": "progresso",
                "tentados": i,
                "ok": ok,
                "falhas": falhas,
                "s_por_doc": round(dt / max(1, i), 2),
                "restantes": len(pendentes) - i,
                "eta_min": round((len(pendentes) - i) * (dt / max(1, i)) / 60, 1),
            }
            with recibo.open("a") as fh:
                fh.write(json.dumps(evt) + "\n")
            print(json.dumps(evt), flush=True)

    if desde_sync:
        sincroniza("final")

    fecho = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "evento": "fecho",
        "ok": ok,
        "falhas": falhas,
        # ⚠️ guarda: se NADA foi criado o ledger nao existe, e um crash aqui apaga
        # justamente a lista de erros que explica por que nada foi criado.
        "no_ledger_agora": (
            len({l.strip() for l in ledger.read_text().splitlines() if l.strip()})
            if ledger.exists()
            else 0
        ),
        "de_um_total_de": len(itens),
        "minutos": round((time.time() - t0) / 60, 1),
        "primeiros_erros": erros,
    }
    with recibo.open("a") as fh:
        fh.write(json.dumps(fecho) + "\n")
    print(json.dumps(fecho), flush=True)
    ad.teardown()
    return 0 if falhas == 0 else 3


if __name__ == "__main__":
    sys.exit(main())
