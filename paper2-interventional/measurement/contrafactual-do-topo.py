#!/usr/bin/env python3
"""
contrafactual-do-topo.py — o topo do brief é MESMO determinado por tráfego antigo?

Objeção de revisão adversarial (DeepSeek, 2026-08-29), e ela mira uma palavra que este
paper trocou no mesmo dia:

> "o topo do brief é **determinado** pelo tráfego de busca de meses atrás" é inferência
> da fórmula, não contrafactual. Os 3 chunks exibidos têm `pain = 1,00` e
> `importance = 0,80`; sem zerar `access_count` é plausível que ficassem no topo do
> mesmo jeito.

⚠️ **A objeção existe por causa de uma correção anterior.** A frase dizia "o topo do
brief é um **fóssil** do tráfego de busca de meses atrás", e a metáfora foi trocada por
"determinado por" numa passagem de neutralização lexical — para tirar o juízo de valor.
Só que "determinado" é uma afirmação **causal mais forte** que a metáfora que substituiu.
Neutralizar o tom endureceu a alegação, que é o oposto do pretendido.

Este script mede o contrafactual: recomputa a salience dos candidatos com o componente
de acesso **zerado** e verifica se os 3 chunks onipresentes continuam no topo. Fórmula
verbatim de `serving-salience.ts:220-233`.

Uso:
  contrafactual-do-topo.py --db nox-mem.db [--top 10] [--json] [--out ...]
"""
import argparse
import json
import math
import sqlite3
import sys

# Verbatim de `serving-salience.ts:220-223`.
W_IMPORTANCE, W_RECENCY, W_PAIN, W_ACCESS = 0.55, 0.15, 0.10, 0.20
# `serving-salience.ts:228-233`: zero quando access_count <= 0, senão
# log1p(n)/log(1000), saturado em 1.
LOG1000 = math.log(1000)


def acesso(n):
    if not n or n <= 0:
        return 0.0
    return min(1.0, math.log1p(n) / LOG1000)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--db", required=True)
    ap.add_argument("--top", type=int, default=10)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--out")
    a = ap.parse_args()

    c = sqlite3.connect(f"file:{a.db}?mode=ro", uri=True)

    # os chunks que aparecem em 100% dos briefs da janela — o "topo" em questão
    janela = ("SELECT chunk_id, COUNT(DISTINCT brief_id) n FROM brief_log "
              "WHERE served_at >= '2026-08-20' AND served_at < '2026-08-27' "
              "GROUP BY chunk_id")
    briefs = c.execute("SELECT COUNT(DISTINCT brief_id) FROM brief_log WHERE "
                       "served_at >= '2026-08-20' AND served_at < '2026-08-27'").fetchone()[0]
    onipresentes = [r[0] for r in c.execute(
        f"SELECT chunk_id FROM ({janela}) WHERE n = ?", (briefs,))]

    # população de comparação: todo chunk que foi servido na janela. É o conjunto
    # dentro do qual o topo é disputado — comparar com o corpus inteiro responderia
    # outra pergunta.
    cands = c.execute(f"""
        SELECT c.id, COALESCE(c.importance,0.5), COALESCE(c.pain,0.2),
               COALESCE(c.access_count,0),
               julianday('now') - julianday(COALESCE(c.source_date, c.created_at))
          FROM chunks c WHERE c.id IN (SELECT chunk_id FROM ({janela}))""").fetchall()

    def score(imp, pain, acc, idade, com_acesso: bool):
        rec = max(0.0, min(1.0, 1.0 - (idade or 0) / 365.0))
        return (W_IMPORTANCE * imp + W_RECENCY * rec + W_PAIN * pain
                + W_ACCESS * (acesso(acc) if com_acesso else 0.0))

    com = sorted(((score(i, p, ac, id_, True), cid) for cid, i, p, ac, id_ in cands),
                 reverse=True)
    sem = sorted(((score(i, p, ac, id_, False), cid) for cid, i, p, ac, id_ in cands),
                 reverse=True)
    pos_com = {cid: k for k, (_, cid) in enumerate(com, 1)}
    pos_sem = {cid: k for k, (_, cid) in enumerate(sem, 1)}

    linhas = []
    for cid, imp, pain, acc, idade in cands:
        if cid not in onipresentes:
            continue
        linhas.append({
            "chunk_id": cid, "importance": imp, "pain": pain, "access_count": acc,
            "posicao_com_acesso": pos_com[cid], "posicao_sem_acesso": pos_sem[cid],
            "sai_do_top": pos_sem[cid] > a.top,
        })
    linhas.sort(key=lambda d: d["posicao_com_acesso"])

    saem = [l for l in linhas if l["sai_do_top"]]
    saida = {
        "briefs_na_janela": briefs,
        "candidatos_servidos_na_janela": len(cands),
        "top_considerado": a.top,
        "onipresentes": len(linhas),
        "saem_do_top_sem_acesso": len(saem),
        "detalhe": linhas,
        "veredito": None,
    }
    if not linhas:
        print("⛔ nenhum chunk onipresente na janela — 'o topo' não existe para medir, "
              "e reportar 'o acesso não decide' aqui seria ausência de dado lida como "
              "resultado.", file=sys.stderr)
        return 1
    saida["veredito"] = (
        "DETERMINA" if len(saem) == len(linhas) else
        "NAO_DETERMINA" if not saem else "PARCIAL")

    if a.json:
        print(json.dumps(saida, indent=2, ensure_ascii=False))
    else:
        print(f"janela: {briefs} briefs · {len(cands)} chunks servidos · "
              f"{len(linhas)} onipresentes\n")
        print(f"{'chunk':>9}{'imp':>6}{'pain':>6}{'acessos':>9}"
              f"{'pos c/':>8}{'pos s/':>8}  sai do top-%d?" % a.top)
        for l in linhas:
            print(f"{l['chunk_id']:>9}{l['importance']:>6.2f}{l['pain']:>6.2f}"
                  f"{l['access_count']:>9}{l['posicao_com_acesso']:>8}"
                  f"{l['posicao_sem_acesso']:>8}  {'SIM' if l['sai_do_top'] else 'não'}")
        print()
        if saida["veredito"] == "NAO_DETERMINA":
            print("⇒ NENHUM sai do topo com o componente de acesso zerado: o tráfego "
                  "antigo NÃO determina a posição — importance e pain bastam. A palavra "
                  "'determinado' não se sustenta.")
        elif saida["veredito"] == "DETERMINA":
            print("⇒ TODOS saem do topo sem o componente de acesso: o tráfego antigo é "
                  "o que os põe lá.")
        else:
            print(f"⇒ PARCIAL: {len(saem)} de {len(linhas)} saem. A alegação vale para "
                  f"alguns e não para todos, e tem de ser escrita assim.")

    if a.out:
        json.dump(saida, open(a.out, "w"), indent=2, ensure_ascii=False)
        print(f"→ {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
