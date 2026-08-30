#!/usr/bin/env python3
"""
concentracao-de-oportunidades.py — as oportunidades caem onde a dose alcança?

Pré-condição do Epoch 1, declarada em `PROSPECTIVE-ESTIMAND-2026-08-30.md` §2 **antes**
de qualquer dado de braço existir. A pergunta que ela responde decide se o estudo é
capaz de detectar o que se propõe a detectar.

**O problema.** O dimensionamento fixa N=234 contra um MDE de 30% na densidade global,
derivado da variância e do ICC — e contra o *reach*, a fração dos episódios escritos que
**pode** alcançar um slot de cobertura. O Paper A mediu outra coisa: o **teto do canal**,
a fração dos briefs que **muda de composição**. Sob a dose que testa H1 (`w = 2,0`), essa
fração é **11/350 = 3,14%**.

Se o efeito só pode operar através de briefs alterados, então

    efeito global ≤ (fração de briefs alterados) × (efeito condicional)

e, sob distribuição uniforme das oportunidades, o teto é 3,14% — uma ordem de grandeza
abaixo do MDE. Para 30% ser alcançável é preciso concentração de ~10×.

⚠️ **Mas a uniformidade é justamente o que não se deve supor.** O mecanismo não sorteia
qual brief altera: altera aquele cujo grupo de assinatura tem uma lição designada. Os
briefs alterados são, por construção, os mais próximos das oportunidades. A concentração
pode ser favorável, e é isso que este script mede.

## O que ele computa, e por que é um LIMITE SUPERIOR

`brief_log` não tem `session_id` — só `agent` e `served_at` — então ligar cada brief à
sessão que o recebeu exigiria casar por (agente, janela temporal), o que introduz erro de
atribuição num número que decide o desenho. Em vez disso, mede-se no nível da
**assinatura**, onde o mecanismo de fato opera:

    cobertura = (oportunidades cuja assinatura o mecanismo consegue promover sob w)
                ÷ (todas as oportunidades)

    concentração ≤ cobertura ÷ (fração de briefs alterados)

Isto é um **teto** porque supõe que promover a assinatura certa sempre acerta a sessão
certa — o melhor caso possível de acoplamento entre a promoção e a oportunidade. Se nem
o teto chega a 10×, a conclusão é robusta ao acoplamento, que é a quantidade que não
temos como medir sem `session_id`.

⚠️ **Um teto que reprova é conclusivo; um teto que aprova não é.** Se o resultado passar
de 10×, isso não estabelece que o desenho tem potência — estabelece apenas que o
acoplamento passa a ser o fator decisivo e precisa ser medido por outro caminho.

## O corpus, e o que se perdeu

`CORPUS-FREEZE.md` declara que a reprodução roda contra
`action-archive-20260729T094609Z.tar.gz` (5.547 episódios) em
`/var/backups/nox-mem/paper2-corpus/`. 🔴 **Esse arquivo não existe** — procurado em
2026-08-30 por nome, por tamanho (~107 MB) e por `sha256` em toda a máquina. O diretório
não existe. Esta medição corre sobre o archive **vivo**, que a retenção reduziu a 1.843
episódios, e isso é declarado no artefato.

O que sobreviveu é a `sig()`: `extract_episodes.py` na árvore tem `sha256`
`e860357bd9f1fc06…`, idêntico ao congelado no pré-registro. A taxonomia é reproduzível;
o corpus sobre o qual foi derivada, não.

Uso:
  concentracao-de-oportunidades.py --episodios eps.jsonl --promovidas sigs.txt [--out ...]
"""
import argparse
import json
import pathlib
import sys

# Fração dos briefs que a dose w=2,0 altera — 11/350, de `out/dose-350-v3.json`.
# ⚠️ Não é constante de conveniência: é o denominador da concentração, e o script a
# recomputa do artefato quando ele está disponível em vez de confiar neste valor.
FRACAO_ALTERADA_PADRAO = 11 / 350
MDE = 0.30


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--episodios", required=True, help="JSONL do extrator congelado")
    ap.add_argument("--promovidas", required=True,
                    help="arquivo com uma sig_primary por linha — as que a dose alcança")
    ap.add_argument("--dose-artefato", default="", help="dose-350-v3.json, para recomputar")
    ap.add_argument("--out")
    a = ap.parse_args()

    eps = []
    with open(a.episodios) as f:
        for ln in f:
            ln = ln.strip()
            if ln:
                eps.append(json.loads(ln))
    if not eps:
        print("⛔ nenhum episódio lido — corpus vazio ou caminho errado", file=sys.stderr)
        return 1
    eps.sort(key=lambda e: e.get("ts", ""))

    promovidas = {l.strip() for l in open(a.promovidas) if l.strip()
                  and not l.startswith("#")}
    if not promovidas:
        print("⛔ nenhuma assinatura promovida — sem elas a cobertura é zero por "
              "construção e o número não significa nada", file=sys.stderr)
        return 1

    # fração alterada: do artefato se houver, senão a constante declarada
    frac = FRACAO_ALTERADA_PADRAO
    fonte_frac = "constante declarada (11/350)"
    if a.dose_artefato and pathlib.Path(a.dose_artefato).exists():
        d = json.load(open(a.dose_artefato))
        for r in d["dose"]["tabela"]:
            if str(r["w"]) == "2":
                frac = r["mexeu"] / r["estados"]
                fonte_frac = f"artefato: {r['mexeu']}/{r['estados']}"

    # ── oportunidades ───────────────────────────────────────────────────────
    # Uma ação é OPORTUNIDADE se a sua assinatura já produziu falha ANTES dela.
    # ⚠️ "Antes" é ordem temporal no corpus, não o "≥ 1 epoch antes" do §4.1 do
    # pré-registro: aplicar a defasagem de um epoch exigiria o snapshot de serving de
    # cada instante, que não existe para o archive vivo. A diferença ALARGA o conjunto
    # de oportunidades (toda oportunidade do §4.1 é oportunidade aqui, e não o
    # inverso), o que empurra a cobertura na direção de... depende de onde as
    # assinaturas caem, e por isso é declarado e não presumido inofensivo.
    ja_falhou = set()
    oportunidades, cobertas = [], []
    for e in eps:
        sig = e.get("sig_primary")
        if sig in ja_falhou:
            oportunidades.append(e)
            if sig in promovidas:
                cobertas.append(e)
        if e.get("is_error"):
            ja_falhou.add(sig)

    n_op = len(oportunidades)
    if n_op == 0:
        print("⛔ zero oportunidades no corpus — ou o corpus não tem repetição de "
              "assinatura com falha prévia, ou o campo `is_error` não está sendo lido. "
              "Nos dois casos a concentração é indefinida, não zero.", file=sys.stderr)
        return 1

    cobertura = len(cobertas) / n_op
    concentracao = cobertura / frac if frac > 0 else float("inf")
    mde_implicado = frac * cobertura / frac if frac else 0  # = cobertura
    faixa = ("≥10x — o desenho segue" if concentracao >= 10 else
             "3x-10x — roda com MDE declarado inalcançável" if concentracao >= 3 else
             "<3x — REVISAR o desenho antes de começar")

    por_sig = {}
    for e in oportunidades:
        s = e["sig_primary"]
        por_sig.setdefault(s, {"total": 0, "coberta": s in promovidas})
        por_sig[s]["total"] += 1

    # ── 🔴 leave-one-signature-out ──────────────────────────────────────────
    # Um agregado que passa a faixa pode repousar sobre UM estrato, e este projeto já
    # perdeu tempo com exatamente isso: o estrato S2 do painel de severidade depende de
    # uma única família de raters. A pergunta não é "qual é a cobertura" — é "a
    # cobertura sobrevive à remoção da maior contribuinte".
    #
    # ⚠️ E aqui há uma razão a mais para desconfiar da maior. `Bash|shell:outro` é a
    # assinatura de MENOR especificidade do esquema: é o balde de tudo que a taxonomia
    # não classifica, e o próprio pré-registro observa que ela sozinha é ~27% do corpus
    # e que uma amostra ingênua seria dominada por ela. Uma lição de falha rotulada
    # "Bash, shell, outro" é fraca justamente onde a intervenção precisa ser forte:
    # prevenir uma repetição ESPECÍFICA. Concentração carregada por ela é concentração
    # sobre a assinatura menos informativa que existe.
    cob = {k: v for k, v in por_sig.items() if v["coberta"]}
    lou = None
    if cob:
        maior_sig = max(cob, key=lambda k: cob[k]["total"])
        maior_n = cob[maior_sig]["total"]
        cob_sem = (len(cobertas) - maior_n) / n_op
        lou = {
            "maior_contribuinte": maior_sig,
            "oportunidades_dela": maior_n,
            "share_das_cobertas": round(maior_n / len(cobertas), 4) if cobertas else 0,
            "cobertura_sem_ela": round(cob_sem, 4),
            "concentracao_sem_ela": round(cob_sem / frac, 2) if frac else None,
            "assinaturas_promovidas_com_zero_oportunidades":
                sorted(promovidas - set(por_sig)),
        }

    saida = {
        "gerado_por": "measurement/concentracao-de-oportunidades.py",
        "pergunta": "as oportunidades de falha repetida caem nas assinaturas que a dose "
                    "w=2,0 consegue promover?",
        "corpus": {
            "episodios": len(eps),
            "com_is_error": sum(1 for e in eps if e.get("is_error")),
            "assinaturas_distintas": len({e.get("sig_primary") for e in eps}),
            "ATENCAO": "archive VIVO, não o congelado do CORPUS-FREEZE.md — aquele "
                       "(5.547 episódios) não existe mais na máquina, procurado por "
                       "nome, tamanho e sha256 em 2026-08-30",
        },
        "assinaturas_promovidas_sob_w2": sorted(promovidas),
        "oportunidades": n_op,
        "oportunidades_cobertas": len(cobertas),
        "cobertura": round(cobertura, 4),
        "fracao_de_briefs_alterada": round(frac, 6),
        "fonte_da_fracao": fonte_frac,
        "concentracao_LIMITE_SUPERIOR": round(concentracao, 2),
        "faixa_pre_registrada": faixa,
        "mde_alcancavel_no_melhor_caso": round(mde_implicado, 4),
        "mde_registrado": MDE,
        "por_assinatura": dict(sorted(por_sig.items(),
                                      key=lambda kv: -kv[1]["total"])),
        "leave_one_signature_out": lou,
        "e_limite_superior_porque": (
            "supõe acoplamento perfeito entre promover a assinatura e acertar a sessão; "
            "brief_log não tem session_id, então o acoplamento real não é medível por "
            "este caminho"),
    }

    # ── guardas ────────────────────────────────────────────────────────────
    # (1) cobertura de 100% com poucas assinaturas promovidas é sinal de que o
    #     conjunto `promovidas` foi montado errado (ex.: contém a assinatura dominante
    #     por engano de parsing), não de mecanismo perfeito.
    if cobertura == 1.0:
        print("⛔ cobertura de 100% — toda oportunidade cai numa assinatura promovida. "
              "Isso é implausível e sugere que o conjunto de promovidas foi montado "
              "errado; conferir antes de acreditar.", file=sys.stderr)
        return 1
    # (2) o denominador tem de vir do artefato quando ele existe; uma constante
    #     memorizada é como o `583.973` sobreviveu.
    if a.dose_artefato and fonte_frac.startswith("constante"):
        print(f"⛔ --dose-artefato foi passado ({a.dose_artefato}) e a fração continua "
              f"vindo da constante — o artefato não tem a dose w=2.", file=sys.stderr)
        return 1

    # (3) 🔴 O agregado passa a faixa apoiado numa única assinatura. Reprovar seria
    #     errado — o número é o número — mas deixar passar em silêncio reproduz o
    #     defeito de ler um agregado sem olhar a composição. O script FALHA para que o
    #     operador seja obrigado a ver a decomposição antes de usar o resultado.
    if lou and lou["share_das_cobertas"] > 0.80 and concentracao >= 3:
        print(f"⛔ a concentração de {concentracao:.2f}× passa a faixa, mas "
              f"{100*lou['share_das_cobertas']:.1f}% dela vem de UMA assinatura "
              f"({lou['maior_contribuinte']}). Sem ela: {lou['concentracao_sem_ela']}×. "
              f"Um agregado que repousa num estrato não é o agregado que a faixa "
              f"pré-registrada supunha — a decisão exige olhar a composição.",
              file=sys.stderr)
        if a.out:
            json.dump(saida, open(a.out, "w"), indent=2, ensure_ascii=False)
            print(f"→ {a.out} (gravado mesmo com a falha)", file=sys.stderr)
        return 1

    print(f"corpus: {len(eps)} episódios · {saida['corpus']['com_is_error']} com erro · "
          f"{saida['corpus']['assinaturas_distintas']} assinaturas")
    print(f"promovidas sob w=2,0: {len(promovidas)}")
    print(f"\noportunidades: {n_op}")
    print(f"  cobertas por assinatura promovida: {len(cobertas)}  "
          f"({100*cobertura:.1f}%)")
    print(f"\nfração de briefs alterada: {100*frac:.2f}%  [{fonte_frac}]")
    print(f"CONCENTRAÇÃO (limite superior): {concentracao:.2f}×")
    print(f"faixa pré-registrada: {faixa}")
    if lou:
        print(f"\n🔴 leave-one-signature-out:")
        print(f"   maior contribuinte: {lou['maior_contribuinte']} "
              f"({100*lou['share_das_cobertas']:.1f}% das cobertas)")
        print(f"   sem ela: cobertura {100*lou['cobertura_sem_ela']:.1f}%, "
              f"concentração {lou['concentracao_sem_ela']}×")
        if lou["assinaturas_promovidas_com_zero_oportunidades"]:
            print(f"   promovidas que NÃO aparecem em oportunidade nenhuma: "
                  f"{len(lou['assinaturas_promovidas_com_zero_oportunidades'])} de "
                  f"{len(promovidas)}")
    print(f"\n⚠️ teto do efeito global no melhor caso: {100*cobertura:.1f}% "
          f"contra um MDE registrado de {100*MDE:.0f}%")

    if a.out:
        json.dump(saida, open(a.out, "w"), indent=2, ensure_ascii=False)
        print(f"\n→ {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
