#!/usr/bin/env python3
"""Amostra a pressão de memória dos cgroups de serviços escolhidos, em NDJSON.

Por que existe (2026-10-22): o drop-in 50-MemoryHigh.conf pede 1600 MiB e NÃO está
em efeito — quem vence é limits.conf (1000M/1500M), porque drop-in de systemd é
ordenado por NOME DE ARQUIVO entre todos os diretórios, e "limits.conf" vem depois
de "50-MemoryHigh.conf". Antes de mexer no limite é preciso saber se ele chega a
estrangular alguma coisa, e os contadores de memory.events ZERAM a cada restart do
serviço: um restart meu em 21/10 apagou a única evidência que havia. Por isso cada
amostra carrega o instante em que a unidade subiu — "high=0" só quer dizer algo
junto do tempo que o contador acumulou.

Lê e escreve: só lê /sys/fs/cgroup e o systemctl show; escreve uma linha no log.
Não reinicia nada, não altera nenhum limite.
"""
import json, os, subprocess, sys, time

ARGS = [a for a in sys.argv[1:] if not a.startswith("-")]
UNITS = ARGS or ["nox-mem-api", "openclaw-gateway"]
LOG = "/root/.openclaw/logs/cgroup-mem.ndjson"
os.makedirs(os.path.dirname(LOG), exist_ok=True)

def show(unit, *props):
    out = subprocess.run(
        ["systemctl", "show", unit, *[f"-p{p}" for p in props]],
        capture_output=True, text=True, timeout=20).stdout
    d = {}
    for line in out.splitlines():
        if "=" in line:
            k, v = line.split("=", 1)
            d[k] = v
    return d

def read_int(path):
    try:
        with open(path) as f:
            v = f.read().strip()
        return int(v) if v.isdigit() else None
    except OSError:
        return None

def read_events(path):
    try:
        with open(path) as f:
            return {k: int(v) for k, v in (l.split() for l in f if l.strip())}
    except OSError:
        return {}

rows = []
for unit in UNITS:
    p = show(unit, "ControlGroup", "ActiveEnterTimestamp", "MainPID", "NRestarts", "SubState")
    cg = p.get("ControlGroup", "")
    base = "/sys/fs/cgroup" + cg if cg else None
    ev = read_events(f"{base}/memory.events") if base else {}
    row = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "unit": unit,
        "substate": p.get("SubState"),
        "active_since": p.get("ActiveEnterTimestamp") or None,
        "main_pid": p.get("MainPID"),
        "n_restarts": p.get("NRestarts"),
        "current": read_int(f"{base}/memory.current") if base else None,
        "peak": read_int(f"{base}/memory.peak") if base else None,
        "high": read_int(f"{base}/memory.high") if base else None,
        "max": read_int(f"{base}/memory.max") if base else None,
        "ev_high": ev.get("high"), "ev_max": ev.get("max"),
        "ev_oom": ev.get("oom"), "ev_oom_kill": ev.get("oom_kill"),
    }
    # fração do teto, que é o número que interessa ler de relance
    if row["current"] and row["high"]:
        row["pct_high"] = round(100 * row["current"] / row["high"], 1)
    if row["peak"] and row["high"]:
        row["pct_high_peak"] = round(100 * row["peak"] / row["high"], 1)
    rows.append(row)

with open(LOG, "a") as f:
    for r in rows:
        f.write(json.dumps(r, sort_keys=True) + "\n")

if os.isatty(1) or "-v" in sys.argv:
    for r in rows:
        print(json.dumps(r, sort_keys=True))
