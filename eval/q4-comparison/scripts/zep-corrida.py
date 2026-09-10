#!/usr/bin/env python3
"""
Ingestão do corpus inteiro no Zep — retomável, com recibo e prazo de parede.

⚠️ POR QUE UM LEDGER E NÃO `doc_id_exists()`: o Zep 0.27 **não deduplica no nível
da mensagem**. Reenviar a mesma conversa MULTIPLICA os dados, e a documentação do
próprio adapter diz que a única limpeza é `docker compose down -v` — que apaga
tudo. Logo a retomada tem de ser responsabilidade nossa: o ledger guarda os
`conversation_id` JÁ ENVIADOS e a corrida salta-os.

⚠️ PRAZO DE PAREDE, não contagem de iterações: laço limitado por contagem sai
`exit 0` e meio-feito, e "terminou" fica indistinguível de "acabaram as voltas".

⚠️ O EMBEDDING DO ZEP É ASSÍNCRONO. Terminar a ingestão NÃO significa que o
índice está pronto. Esta corrida reporta a contagem de mensagens gravadas; a
prontidão do vetor é uma segunda pergunta, medida depois (ver `--espera-final`).

Uso:
  python scripts/zep-corrida.py --corpus cache/locomo.jsonl \
      --corpus cache/longmemeval.jsonl --out out/zep --deadline-min 240
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def _censo_zep() -> tuple[int, int]:
    """(mensagens, vetores) no Postgres do Zep. (0,0) quando não se consegue medir."""
    import subprocess

    try:
        out = subprocess.run(
            ["docker", "exec", "q4-postgres", "psql", "-U", "zep", "-d", "zep", "-t", "-A",
             "-c", "SELECT (SELECT count(*) FROM message)||' '||(SELECT count(*) FROM message_embedding);"],
            capture_output=True, text=True, timeout=15,
        )
        a, b = out.stdout.strip().split()
        return int(a), int(b)
    except Exception:
        return 0, 0


def agora() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", action="append", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--deadline-min", type=int, default=240)
    ap.add_argument("--espera-final", type=int, default=120,
                    help="segundos de espera antes de medir a prontidao do indice")
    a = ap.parse_args()

    saida = Path(a.out); saida.mkdir(parents=True, exist_ok=True)
    recibo = saida / "recibo.ndjson"
    ledger = saida / "ledger-conversas.txt"

    from adapters import zep as ad

    v = ad.validate()
    if not v.get("ok"):
        recibo.open("a").write(json.dumps({"ts": agora(), "evento": "validate_falhou", "v": v}) + "\n")
        print(f"🔴 validate() falhou: {v.get('error')}")
        return 2

    # ⚠️ DOIS hashes, e a razão importa. A corrida do EverOS emite
    # `corpus_sha256` sobre os BYTES DOS ARQUIVOS em ordem de caminho ordenada.
    # A minha primeira versão daqui hasheava LINHA A LINHA sem newline — também
    # válido, e **incomparável**: dois recibos que dizem medir o mesmo corpus com
    # `corpus_sha256` diferente leem-se como corpora diferentes, que é o pior tipo
    # de recibo (o que parece informar e desinforma).
    #
    # `corpus_sha256` passa a ser o CANÔNICO (bytes/arquivo, ordem ordenada),
    # verificado igual ao do EverOS: d150c703e3dd… O de linhas fica ao lado, com
    # nome próprio, porque é o que este script realmente serviu ao adapter.
    h_canon = hashlib.sha256()
    for c in sorted(Path(x) for x in a.corpus):
        h_canon.update(c.read_bytes())
    h = hashlib.sha256()
    grupos: dict[str, list[dict]] = defaultdict(list)
    total = 0
    for c in a.corpus:
        p = Path(c)
        for linha in p.read_text().splitlines():
            if not linha.strip():
                continue
            h.update(linha.encode())
            d = json.loads(linha)
            grupos[d.get("conversation_id") or d["id"].split("::")[0]].append(
                {"id": d["id"], "text": d.get("text", ""),
                 "conv_id": d.get("conversation_id"), "metadata": d.get("metadata") or {}}
            )
            total += 1

    feitas = set()
    if ledger.exists():
        feitas = {l.strip() for l in ledger.read_text().splitlines() if l.strip()}

    pendentes = [k for k in sorted(grupos) if k not in feitas]
    arranque = {
        "ts": agora(), "evento": "arranque", "documentos": total,
        "conversas": len(grupos), "ja_feitas": len(feitas), "pendentes": len(pendentes),
        "corpus_sha256": h_canon.hexdigest(),
        "corpus_sha256_linhas": h.hexdigest(),
        "corpus": [str(x) for x in a.corpus],
        "deadline_min": a.deadline_min,
        "versao_cliente": v.get("version"),
    }
    with recibo.open("a") as f:
        f.write(json.dumps(arranque, ensure_ascii=False) + "\n")
    print(json.dumps(arranque, ensure_ascii=False))

    ad.setup()
    limite = time.time() + a.deadline_min * 60
    ok_msgs = 0
    erros = 0
    t0 = time.time()

    for i, conv in enumerate(pendentes, 1):
        if time.time() > limite:
            with recibo.open("a") as f:
                f.write(json.dumps({"ts": agora(), "evento": "deadline",
                                    "conversas_feitas": i - 1, "restantes": len(pendentes) - i + 1},
                                   ensure_ascii=False) + "\n")
            print("⏱️ prazo de parede atingido — parando com o ledger íntegro")
            break
        try:
            r = ad.ingest_corpus(grupos[conv])
            if r.get("errors"):
                erros += int(r["errors"])
                with recibo.open("a") as f:
                    f.write(json.dumps({"ts": agora(), "evento": "falha_conversa",
                                        "conv": conv, "r": r}, ensure_ascii=False) + "\n")
            else:
                ok_msgs += int(r.get("messages_added") or 0)
                # Só entra no ledger quem foi INTEIRO. Meia conversa no ledger
                # seria pior que ausência: a retomada saltaria o que falta.
                with ledger.open("a") as f:
                    f.write(conv + "\n")
        except Exception as exc:
            erros += 1
            with recibo.open("a") as f:
                f.write(json.dumps({"ts": agora(), "evento": "excecao", "conv": conv,
                                    "erro": f"{type(exc).__name__}: {exc}"}, ensure_ascii=False) + "\n")

        if i % 25 == 0 or i == len(pendentes):
            dt = time.time() - t0
            ev = {"ts": agora(), "evento": "progresso", "conversas": i,
                  "de": len(pendentes), "mensagens_ok": ok_msgs, "erros": erros,
                  "s_por_conversa": round(dt / i, 2),
                  "eta_min": round((len(pendentes) - i) * dt / i / 60, 1)}
            with recibo.open("a") as f:
                f.write(json.dumps(ev, ensure_ascii=False) + "\n")
            print(json.dumps(ev, ensure_ascii=False), flush=True)

    ad.teardown()

    # ⚠️ A ESPERA PERTENCE À FRONTEIRA, e é por ESTADO, não por relógio.
    #
    # Duas correções aqui. (i) `time.sleep(N)` mede o relógio, não o índice: se N
    # for curto o `fecho` afirma prontidão que não existe, e se for longo paga-se
    # tempo sem saber por quê. (ii) A espera do adapter é POR CHAMADA, e este
    # script chama `ingest_corpus` uma vez por conversa — 510 arredondamentos de
    # granularidade, medidos em ~2,7 h. Logo desligamos a espera por chamada
    # (`ZEP_EMBED_WAIT_SECS=0`, feito no envelope) e esperamos UMA vez, aqui, que
    # é a fronteira real: depois deste ponto alguém vai buscar.
    print("⏳ prontidão do índice, medida no banco (não no relógio)...", flush=True)
    limite_prontidao = time.time() + a.espera_final
    while time.time() < limite_prontidao:
        msg, emb = _censo_zep()
        if msg > 0 and emb >= msg:
            print(f"✅ índice pronto: EMB={emb} >= MSG={msg}", flush=True)
            break
        print(f"   EMB={emb} de MSG={msg}", flush=True)
        time.sleep(5)
    else:
        msg, emb = _censo_zep()
        print(f"⚠️ prazo de prontidão esgotado com EMB={emb} de MSG={msg} — "
              f"o `fecho` vai DIZER isso em vez de afirmar prontidão", flush=True)

    msg_fim, emb_fim = _censo_zep()
    fecho = {"ts": agora(), "evento": "fecho", "mensagens_ok": ok_msgs, "erros": erros,
             # Prontidão é campo do recibo, não suposição de quem o lê.
             "mensagens_no_banco": msg_fim, "vetores_no_banco": emb_fim,
             "indice_pronto": bool(msg_fim > 0 and emb_fim >= msg_fim),
             "conversas_no_ledger": len({l.strip() for l in ledger.read_text().splitlines() if l.strip()})
             if ledger.exists() else 0,
             "documentos_no_corpus": total, "conversas_no_corpus": len(grupos)}
    with recibo.open("a") as f:
        f.write(json.dumps(fecho, ensure_ascii=False) + "\n")
    print(json.dumps(fecho, ensure_ascii=False))
    return 0 if erros == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
