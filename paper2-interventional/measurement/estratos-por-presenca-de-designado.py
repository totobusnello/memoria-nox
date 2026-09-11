#!/usr/bin/env python3
"""estratos-por-presenca-de-designado.py — caracterização, NÃO controle.

⛔ ESTE SCRIPT SUBSTITUI UM QUE ESTAVA ERRADO
---------------------------------------------
A versão anterior — `controle-negativo-intra-braco.py`, PR #501, mergeada e agora
retirada — afirmava um controle negativo: *"brief de tratamento em que nenhum
designado aparece no conjunto SERVIDO não pode mexer"*, com 2.908 briefs e 0
violações. **Era tautológico.**

"Servido" estava definido como `set(ids_controle) | set(ids_tratado)`, e `ids_tratado`
é **pós-dose**. Se a dose promove um designado, ele entra em `ids_tratado`, logo entra
em "servido", logo o brief cai no estrato "presente". O estrato "ausente" não pode
conter movimento **por construção**, não por medição.

Indício que o prova, e está na própria saída: `presença em (controle ∪ tratado)` é
**numericamente idêntica** a `presença em tratado` em todos os epochs — 189, 185, 184,
144, 187, 193. O critério nunca dependeu do controle.

E a premissa estava **invertida**. Pelo critério dose-independente (presença no
conjunto de **controle**), o estrato "ausente" tem **118 movimentos**, não 0 — porque a
dose age promovendo chunk que **não estava** no baseline. Ausência do controle é onde a
dose tem MAIS o que fazer.

⇒ **Não existe controle negativo intra-braço neste log**, por três vias: (1) epoch de
controle não tem os campos (`sem_ids == n`); (2) presença pós-dose é tautológica;
(3) `boost_by_id` vazio é estrato vazio (`sem_boost == 0` em 3.990 briefs — o boost
sempre aplica a algo). O buraco fica aberto e declarado.

O QUE ESTE SCRIPT FAZ
---------------------
Estratifica por presença de designado no conjunto de **controle** — dose-independente,
logo não seleciona sobre o desfecho. Emite os dois estratos e a taxa de movimento em
cada. É **caracterização do mecanismo**, não teste de especificidade: o estrato
"ausente" ter movimento é o esperado, não uma falha.

⚠️ NÃO usar a taxa condicional como estimando primário: o denominador `presC` não é
intercambiável entre epochs (124 em 09-06 contra 158-174 nos outros) e a anomalia
existe também nesta variável dose-independente, logo não é causada pela dose — e
continua sem explicação.

SEMÂNTICA
---------
  mexeu   := set(ids_controle) != set(ids_tratado)   -- PERTENCIMENTO, não ordem
  presC   := set(designated_ids) & set(ids_controle) != {}   -- POS-controle, dose-indep.
  Filtra `modo == "active"`: em shadow a dose servida não é a designada.
  Lê o REGISTRADO no log; não é replay nem contrafactual recomputado.
"""
import argparse, collections, hashlib, json, os, sys

SEMANTICA = ("estratifica por presenca de designado no conjunto de CONTROLE "
             "(dose-independente); mexeu=pertencimento(set!=set); filtra modo=active; "
             "NAO e controle negativo — o estrato ausente TEM movimento por mecanismo")

def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--log", default="/root/.openclaw/logs/p2-serving.ndjson")
    ap.add_argument("--desde", default="2026-09-01")
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
        if c is None or t is None:
            continue
        dg = d.get("designated_ids")
        if dg is None:
            sem_designated += 1
            continue
        sc, st, sd = set(c), set(t), set(dg)
        mexeu = sc != st
        k = por[ep]
        k["n"] += 1
        k["w"] = d.get("w")
        if sd & sc:
            k["presC"] += 1; k["presC_mexeu"] += mexeu
        else:
            k["ausC"] += 1;  k["ausC_mexeu"] += mexeu
        # medido só para expor a tautologia da versão anterior
        if sd & st:
            k["presT"] += 1
        if sd & (sc | st):
            k["presUniao"] += 1

    if sem_designated:
        print(f"ERRO: {sem_designated} registros sem `designated_ids` — estrato "
              f"indeterminavel", file=sys.stderr)
        return 2
    if not por:
        print("ERRO: nenhum epoch de tratamento na janela — nada a estratificar "
              "(ausencia de dado, nao ausencia de efeito)", file=sys.stderr)
        return 2

    epochs, tautologico = [], True
    for ep in sorted(por):
        k = por[ep]
        if k["presUniao"] != k["presT"]:
            tautologico = False
        epochs.append({
            "epoch": ep, "w": k["w"], "n": k["n"],
            "presC": k["presC"], "presC_mexeu": k["presC_mexeu"],
            "ausC": k["ausC"], "ausC_mexeu": k["ausC_mexeu"],
            "presT": k["presT"], "presUniao": k["presUniao"],
            "taxa_em_presC": round(k["presC_mexeu"] / k["presC"], 6) if k["presC"] else None,
            "taxa_em_ausC": round(k["ausC_mexeu"] / k["ausC"], 6) if k["ausC"] else None,
        })

    den = [e["presC"] for e in epochs]
    art = {
        "gerado_por": "measurement/estratos-por-presenca-de-designado.py",
        "semantica": SEMANTICA,
        "nao_e_controle_negativo": (
            "o estrato ausC TEM movimento (%d total) porque a dose promove chunk que nao "
            "estava no baseline; ausencia do controle e onde ela tem MAIS o que fazer"
            % sum(e["ausC_mexeu"] for e in epochs)),
        "tautologia_da_versao_anterior": {
            "afirmava": "presenca em (controle uniao tratado) => estrato sem movimento",
            "prova_de_que_era_tautologia": "presUniao == presT em todos os epochs",
            "confirmado": tautologico,
        },
        "procedencia": {"log": a.log, "sha256": h.hexdigest(),
                        "linhas_malformadas": malformadas, "desde": a.desde},
        "aviso_denominador": (
            "presC NAO e intercambiavel entre epochs (min %d, max %d, razao %.2fx) e a "
            "anomalia existe nesta variavel DOSE-INDEPENDENTE, logo nao e causada pela "
            "dose — e segue sem explicacao" % (min(den), max(den), max(den)/min(den))
        ) if den else None,
        "epochs": epochs,
    }

    if a.out:
        with open(a.out, "w", encoding="utf-8") as fh:
            json.dump(art, fh, ensure_ascii=False, indent=2)
        print(f"artefato: {a.out}")
    else:
        json.dump(art, sys.stdout, ensure_ascii=False, indent=2)
        print()

    # Exit 1 se a tautologia NAO se confirmar: significaria que presUniao != presT e a
    # explicacao da retirada estaria errada — o que exige revisao, nao silencio.
    if not tautologico:
        print("ATENCAO: presUniao != presT em algum epoch — a explicacao da retirada do "
              "controle anterior precisa de revisao", file=sys.stderr)
        return 1
    return 0

if __name__ == "__main__":
    sys.exit(main())
