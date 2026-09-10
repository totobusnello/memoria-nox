#!/usr/bin/env python3
"""
Preflight PAGO do Zep — 5 documentos, e responde o que assinatura não responde.

Existe pela mesma razão do `everos-preflight.py`: antes de gastar o corpus
inteiro, provar as quatro coisas que só uma chamada real revela.

  1. A chave OpenAI embeda de verdade pelo caminho do Zep (não só direto na API).
  2. O `gold_id` faz ROUND-TRIP — entra no `metadata` da mensagem e volta na busca.
     Sem isto o nDCG@10 por `gold_chunk_ids` é indefinido e a coluna não existe.
  3. A busca devolve DISTÂNCIA real (não zero, não vazio) — prova de que o vetor
     foi gravado, e não só a mensagem.
  4. Quantas sessões o agrupamento cria, porque a busca do Zep é POR SESSÃO e o
     adapter faz fan-out: o custo e a latência da fase de busca dependem disso.

⚠️ Ele ESCREVE em Zep. Roda num prefixo de sessão próprio (`pf-`) para não
contaminar a corrida real; não há wipe seletivo em Zep 0.27 e `down -v` apaga
tudo, logo separar por nome é o que existe.
"""
from __future__ import annotations

import json
import os
import sys
import time
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from adapters import zep as ad  # noqa: E402

MARCA = uuid.uuid4().hex[:6]

DOCS = [
    {"id": f"pf-{MARCA}-conv-A::D1:1", "conv_id": f"pf-{MARCA}-A",
     "text": "Maria comprou um guarda-chuva vermelho na feira de Pinheiros no sabado."},
    {"id": f"pf-{MARCA}-conv-A::D1:2", "conv_id": f"pf-{MARCA}-A",
     "text": "O guarda-chuva quebrou na primeira chuva forte e ela pediu reembolso."},
    {"id": f"pf-{MARCA}-conv-A::D1:3", "conv_id": f"pf-{MARCA}-A",
     "text": "A feira de Pinheiros funciona todo sabado das seis as treze horas."},
    {"id": f"pf-{MARCA}-conv-B::D2:1", "conv_id": f"pf-{MARCA}-B",
     "text": "Joao adotou um gato preto chamado Zinco em marco do ano passado."},
    {"id": f"pf-{MARCA}-conv-B::D2:2", "conv_id": f"pf-{MARCA}-B",
     "text": "O gato Zinco dorme no telhado quando o sol esquenta as telhas."},
]

CONSULTAS = [
    ("guarda-chuva quebrado reembolso", f"pf-{MARCA}-conv-A::D1:2"),
    ("gato que dorme no telhado", f"pf-{MARCA}-conv-B::D2:2"),
    ("horario da feira", f"pf-{MARCA}-conv-A::D1:3"),
]


def main() -> int:
    v = ad.validate()
    print(json.dumps({"validate": v}, ensure_ascii=False))
    if not v.get("ok"):
        print("VEREDITO: validate() falhou — nada foi gasto.")
        return 2

    ad.setup()
    t0 = time.time()
    res = ad.ingest_corpus(DOCS)
    dt = time.time() - t0
    print(json.dumps({"ingest": res, "s": round(dt, 2)}, ensure_ascii=False))

    if res.get("errors"):
        print("VEREDITO: a ingestao acusou erro — NAO seguir para o corpus.")
        ad.teardown()
        return 2

    # O embedding do Zep e' ASSINCRONO: sem espera, "0 hits" mede a espera, nao a busca.
    time.sleep(15)

    acertos = 0
    relatorio = []
    for q, esperado in CONSULTAS:
        hits = ad.search(q, k=5)
        ids = [h.get("id") for h in hits]
        dists = [h.get("score") for h in hits]
        ok = esperado in ids
        acertos += int(ok)
        relatorio.append({"q": q, "esperado": esperado, "achou": ok,
                          "ids": ids[:5], "scores": [round(float(d or 0), 4) for d in dists[:5]]})
    print(json.dumps({"busca": relatorio}, ensure_ascii=False, indent=2))

    zeros = all(not any(float(s or 0) for s in r["scores"]) for r in relatorio if r["scores"])
    ad.teardown()

    print("\n=== VEREDITO ===")
    print(f"round-trip do gold_id: {acertos}/{len(CONSULTAS)}")
    print(f"sessoes criadas: {res.get('sessions_created')} para 2 conv_id distintos")
    print(f"mensagens: {res.get('messages_added')} de {len(DOCS)} documentos")
    if acertos == 0:
        print("🔴 nenhum gold_id voltou — a coluna do Zep no nDCG@10 seria INDEFINIDA.")
        return 2
    if zeros:
        print("🔴 todas as distancias sao zero — a mensagem gravou, o VETOR provavelmente nao.")
        return 2
    if acertos < len(CONSULTAS):
        print(f"⚠️ {len(CONSULTAS) - acertos} consulta(s) nao trouxe(ram) o alvo no top-5 — "
              "aceitavel num n=5, mas anotar; nao e' falha estrutural.")
    print("✅ round-trip provado, distancias reais. O corpus inteiro pode correr.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
