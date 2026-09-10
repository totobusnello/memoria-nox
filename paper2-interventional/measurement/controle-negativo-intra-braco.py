#!/usr/bin/env python3
"""controle-negativo-intra-braco.py — especificidade sem sair do braço de tratamento.

O PROBLEMA QUE ISTO RESOLVE
---------------------------
O controle negativo óbvio — "epoch de controle tem `mexeu == 0`" — é INVÁLIDO. Nos
epochs de controle os campos `ids_controle`/`ids_tratado` não existem (`sem_ids == n`
em 09-03, 09-07 e 09-10), logo `mexeu == 0` é indistinguível de "o campo nunca foi
escrito". É a regra 9 do CLAUDE.md no próprio instrumento que se ia usar como controle.

O ENUNCIADO VÁLIDO
------------------
Briefs de epoch de TRATAMENTO em que nenhum id designado aparece no conjunto servido:
a dose não tem onde agir, logo `set(ids_controle) == set(ids_tratado)` por construção.
Se algum mexer, o instrumento está errado. Isto corre DENTRO do braço onde o
dual-compute existe, então não depende de campo ausente — e não depende do replay,
que o §7 da spec de análise proíbe para o estimador.

SEMÂNTICA (declarada, à moda do `semantica=` que a sessão par adotou)
--------------------------------------------------------------------
  mexeu        := set(ids_controle) != set(ids_tratado)   -- PERTENCIMENTO, não ordem
  tem_alcance  := set(designated_ids) & (set(ids_controle) | set(ids_tratado)) != {}
  Filtra `modo == "active"`: em modo shadow a dose servida não é a designada.

EFEITO COLATERAL ÚTIL: o estimando condicional
----------------------------------------------
A taxa condicionada a `tem_alcance` é muito menos diluída que a incondicional — 72 a
79% dos briefs não têm alcance. ⚠️ Mas o denominador NÃO é intercambiável entre
epochs (medido 2026-09-10: 144 em 09-06 contra 184-193 nos outros, 23% menor), então
condicionar pode trocar um viés por outro. O script emite os dois e não escolhe.
"""
import argparse, collections, json, os, sys, hashlib

SEMANTICA = ("mexeu=pertencimento(set!=set), NAO ordem; tem_alcance=designated_ids "
             "intersecta o servido; filtra modo=active. NAO e replay nem contrafactual "
             "recomputado — le o que foi REGISTRADO no log de serving.")

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", default="/root/.openclaw/logs/p2-serving.ndjson")
    ap.add_argument("--desde", default="2026-09-01", help="epoch inicial (chave epoch, nao ts)")
    ap.add_argument("--out")
    a = ap.parse_args()

    if not os.path.isfile(a.log):
        print(f"ERRO: log inexistente: {a.log}", file=sys.stderr)
        return 2

    h = hashlib.sha256()
    with open(a.log, "rb") as fh:
        for blk in iter(lambda: fh.read(1 << 20), b""):
            h.update(blk)

    por = collections.defaultdict(collections.Counter)
    sem_designated = malformadas = 0
    for ln in open(a.log, encoding="utf-8", errors="replace"):
        ln = ln.strip()
        if not ln:
            continue
        try:
            d = json.loads(ln)
        except Exception:
            malformadas += 1
            continue
        if d.get("modo") != "active":
            continue
        ep = str(d.get("epoch"))[:10]
        if ep < a.desde:
            continue
        c, t = d.get("ids_controle"), d.get("ids_tratado")
        if c is None or t is None:      # epoch de controle: dual-compute nao corre
            continue
        dg = d.get("designated_ids")
        if dg is None:
            sem_designated += 1
            continue
        servidos = set(c) | set(t)
        mexeu = set(c) != set(t)
        k = por[ep]
        k["n"] += 1
        k["w"] = d.get("w")
        if set(dg) & servidos:
            k["com_alcance"] += 1
            k["com_alcance_mexeu"] += mexeu
        else:
            k["sem_alcance"] += 1
            k["sem_alcance_mexeu"] += mexeu

    # `sem_designated > 0` invalida a leitura: sem o campo nao se sabe se ha alcance.
    if sem_designated:
        print(f"ERRO: {sem_designated} registros sem `designated_ids` — alcance "
              f"indeterminavel, controle NAO avaliavel", file=sys.stderr)
        return 2
    if not por:
        print("ERRO: nenhum epoch de tratamento na janela — controle NAO avaliavel "
              "(ausencia de dado, nao ausencia de defeito)", file=sys.stderr)
        return 2

    epochs = []
    for ep in sorted(por):
        k = por[ep]
        sa, ca = k["sem_alcance"], k["com_alcance"]
        epochs.append({
            "epoch": ep, "w": k["w"], "n": k["n"],
            "sem_alcance": sa, "sem_alcance_mexeu": k["sem_alcance_mexeu"],
            "com_alcance": ca, "com_alcance_mexeu": k["com_alcance_mexeu"],
            "taxa_incondicional": round(k["com_alcance_mexeu"] / k["n"], 6) if k["n"] else None,
            "taxa_condicional": round(k["com_alcance_mexeu"] / ca, 6) if ca else None,
        })

    viola = sum(e["sem_alcance_mexeu"] for e in epochs)
    total_sem = sum(e["sem_alcance"] for e in epochs)
    den = [e["com_alcance"] for e in epochs]
    art = {
        "gerado_por": "measurement/controle-negativo-intra-braco.py",
        "semantica": SEMANTICA,
        "procedencia": {"log": a.log, "sha256": h.hexdigest(),
                        "linhas_malformadas": malformadas, "desde": a.desde},
        "controle_negativo": {
            "enunciado": "brief de tratamento sem designado no servido nao pode mexer",
            "briefs_sem_alcance": total_sem,
            "violacoes": viola,
            "passa": viola == 0,
        },
        "aviso_condicionamento": (
            "o denominador de `com_alcance` NAO e intercambiavel entre epochs "
            f"(min {min(den)}, max {max(den)}, razao {max(den)/min(den):.2f}x); "
            "condicionar pode introduzir selecao propria"
        ) if den else None,
        "epochs": epochs,
    }

    # Artefato ANTES do veredito: o exit code carrega o veredito, o artefato a evidencia
    # (contrato adotado da sessao par, 2026-09-10 — o guarda dela retornava antes do --out
    # e o veredito mais importante era o unico que nao deixava evidencia).
    if a.out:
        with open(a.out, "w", encoding="utf-8") as fh:
            json.dump(art, fh, ensure_ascii=False, indent=2)
        print(f"artefato: {a.out}")
    else:
        json.dump(art, sys.stdout, ensure_ascii=False, indent=2)
        print()

    if viola:
        print(f"FALHA: {viola} de {total_sem} briefs mexeram sem a dose ter alcance",
              file=sys.stderr)
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
