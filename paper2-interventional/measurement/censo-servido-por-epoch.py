#!/usr/bin/env python3
"""Censo de briefs SERVIDOS por epoch, com procedência, lido do log de produção.

Existe porque o `janela-elegivel.py` classificava epochs por SOBREPOSIÇÃO DE RELÓGIO e
chamava o resultado de `fracao_exposta`/`exposto_h`, com um docstring que dizia "fração do
epoch em que a dose foi servida". Ele não lia serving nenhum. Consequência medida em
2026-09-10: `2026-09-02` saiu `classe=inteiro, exposto_h=24.0` e serviu **0 briefs**;
`2026-09-03` saiu `inteiro` e serviu **441 de 672**.

⚠️ Três vias de contagem dão três respostas sobre o MESMO arquivo, e a diferença é de
desenho, não defeito:

  * por dia-calendário  -> 2026-09-02 = 252 registros (são as 00:00–09:00Z que pertencem
                           ao epoch de 09-01, porque a fronteira é 09:00Z)
  * pelo campo `epoch`  -> 2026-09-02 AUSENTE
  * derivado do `ts`-9h -> 2026-09-02 AUSENTE

Este censo usa o **campo `epoch`** e confere contra a derivação do `ts`; divergência é
reportada, nunca silenciada (medido 2026-09-10: 0 de 12.173).

Procedência vai no artefato: host, caminho, sha256 e nº de linhas do log. Sem isso o censo
é transcrição — e transcrição não se recomputa.
"""
import argparse, collections, datetime, json, os, shlex, subprocess, sys

ESPERADO_POR_EPOCH = 672      # 4 rajadas/h x 24 h x 7 briefs/rajada (6 agentes, nox 2x)
FRONTEIRA_H = 9

REMOTO = r'''
import collections, datetime, hashlib, json, os, sys
p = sys.argv[1]
h = hashlib.sha256()
with open(p, "rb") as f:
    for b in iter(lambda: f.read(1 << 20), b""):
        h.update(b)
porcampo = collections.Counter(); ports = collections.Counter(); cal = collections.Counter()
pormodo = collections.defaultdict(collections.Counter)
wpor = collections.defaultdict(set)
n = 0; malformadas = 0; div = 0; semts = 0; semmodo = 0
for ln in open(p):
    ln = ln.strip()
    if not ln:
        continue
    try:
        r = json.loads(ln)
    except Exception:
        malformadas += 1
        continue
    n += 1
    ts = r.get("ts")
    if not ts:
        semts += 1
        continue
    t = datetime.datetime.fromisoformat(ts.replace("Z", "+00:00"))
    der = (t - datetime.timedelta(hours=9)).date().isoformat()
    ep = r.get("epoch")
    ports[der] += 1
    cal[t.date().isoformat()] += 1
    if ep is not None:
        porcampo[str(ep)] += 1
        m = r.get("modo")
        if m is None:
            semmodo += 1
        else:
            pormodo[str(ep)][str(m)] += 1
            wpor[str(ep) + "|" + str(m)].add(str(r.get("w")))
        if str(ep) != der:
            div += 1
print(json.dumps({
    "host": os.uname().nodename,
    "log": p,
    "log_sha256": h.hexdigest(),
    "log_bytes": os.path.getsize(p),
    "linhas": n, "malformadas": malformadas, "sem_ts": semts,
    "divergencia_campo_vs_ts": div,
    "sem_modo": semmodo,
    "por_campo_epoch": dict(porcampo),
    "por_epoch_e_modo": {k: dict(v) for k, v in pormodo.items()},
    "w_por_epoch_e_modo": {k: sorted(v) for k, v in wpor.items()},
    "por_ts_menos_9h": dict(ports),
    "por_dia_calendario": dict(cal),
}))
'''


def colhe(host: str, log: str) -> dict:
    cmd = ["ssh", "-o", "BatchMode=yes", "-o", "ConnectTimeout=12", host,
           f"python3 - {shlex.quote(log)}"]
    r = subprocess.run(cmd, input=REMOTO, capture_output=True, text=True, timeout=180)
    if r.returncode != 0:
        raise SystemExit(f"RED censo-remoto-falhou rc={r.returncode} err={r.stderr[:400]}")
    return json.loads(r.stdout)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--host", default=os.environ.get("NOX_VPS_HOST", ""),
                    help="alvo SSH da VPS de produção; sem default no git — vem de $NOX_VPS_HOST. Identidade prova-se por artefato datado, nunca por nome")
    ap.add_argument("--log", default="/root/.openclaw/logs/p2-serving.ndjson")
    ap.add_argument("--local", help="ler NDJSON local em vez de ssh (para teste)")

    a = ap.parse_args()
    if not a.local and not a.host:
        sys.exit("RED sem-alvo: defina $NOX_VPS_HOST (o nome do host nao vive no git) "
                 "ou passe --host/--local. Sem isso o ssh falha com 'Host key "
                 "verification failed', que nao nomeia a pre-condicao que faltou.")

    if a.local:
        import hashlib  # `os` vem do import do módulo (linha 24);
        # reimportá-lo aqui tornava o nome LOCAL e quebrava o default do --host
        h = hashlib.sha256()
        with open(a.local, "rb") as f:
            for b in iter(lambda: f.read(1 << 20), b""):
                h.update(b)
        porcampo = collections.Counter(); ports = collections.Counter()
        cal = collections.Counter(); n = mal = div = semts = semmodo = 0
        pormodo = collections.defaultdict(collections.Counter)
        wpor = collections.defaultdict(set)
        for ln in open(a.local):
            ln = ln.strip()
            if not ln:
                continue
            try:
                r = json.loads(ln)
            except Exception:
                mal += 1
                continue
            n += 1
            ts = r.get("ts")
            if not ts:
                semts += 1
                continue
            t = datetime.datetime.fromisoformat(ts.replace("Z", "+00:00"))
            der = (t - datetime.timedelta(hours=FRONTEIRA_H)).date().isoformat()
            ep = r.get("epoch")
            ports[der] += 1
            cal[t.date().isoformat()] += 1
            if ep is not None:
                porcampo[str(ep)] += 1
                m = r.get("modo")
                if m is None:
                    semmodo += 1
                else:
                    pormodo[str(ep)][str(m)] += 1
                    wpor[str(ep) + "|" + str(m)].add(str(r.get("w")))
                if str(ep) != der:
                    div += 1
        bruto = {"host": "local", "log": a.local, "log_sha256": h.hexdigest(),
                 "log_bytes": os.path.getsize(a.local), "linhas": n, "malformadas": mal,
                 "sem_ts": semts, "divergencia_campo_vs_ts": div,
                 "sem_modo": semmodo,
                 "por_campo_epoch": dict(porcampo),
                 "por_epoch_e_modo": {k: dict(v) for k, v in pormodo.items()},
                 "w_por_epoch_e_modo": {k: sorted(v) for k, v in wpor.items()},
                 "por_ts_menos_9h": dict(ports), "por_dia_calendario": dict(cal)}
    else:
        bruto = colhe(a.host, a.log)

    # A concordância entre as duas vias é PERNA PRÓPRIA, antes de qualquer conclusão:
    # se elas divergirem, a chave de agrupamento não é confiável e o censo não vale.
    estado = "GREEN" if bruto["divergencia_campo_vs_ts"] == 0 else "RED"
    bruto["semantica"] = (
        "briefs-REGISTRADOS-no-log-de-serving-por-chave-epoch; "
        "NAO e' sobreposicao de relogio nem contrafactual recomputado. "
        "`por_campo_epoch` e' o TOTAL e inclui `shadow`; a exposicao SOB A DESIGNACAO "
        "esta em `por_epoch_e_modo[epoch]['active']`. Medido 2026-09-10: 2026-09-01 e' o "
        "UNICO epoch de modo misto da janela (630 active w=4,0 + 42 shadow w=2,0), logo "
        "o total 672 sobrestima a entrega designada em 42.")
    bruto["esperado_por_epoch"] = ESPERADO_POR_EPOCH
    bruto["estado"] = estado
    bruto["ts_censo"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
    print(json.dumps(bruto, indent=2, ensure_ascii=False))
    sys.exit(0 if estado == "GREEN" else 1)


if __name__ == "__main__":
    main()
