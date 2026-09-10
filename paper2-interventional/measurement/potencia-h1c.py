#!/usr/bin/env python3
"""
potencia-h1c.py — H1c como primária tem potência? (opção C da revisão de desenho)

A revisão de 2026-08-30 estabeleceu que H1 incondicional não pode ser testada: o
mecanismo altera 3,14% dos briefs e o desenho pede 30% de redução na densidade global,
o que exigiria efeito de 955% nas oportunidades cobertas — impossível por construção.

A opção C promove a família co-primária H1a–c, **já registrada desde 2026-08-16**, a
primária. H1c é `falhas repetidas / oportunidade` — proporção, binomial logit,
denominador = oportunidades (PREREG §5). Trocar o denominador de *session-hours* para
*oportunidades* remove a diluição da exposição; **não** remove a da cobertura.

⚠️ **O que este script NÃO faz.** Não re-dimensiona o estudo e não escolhe um MDE. Ele
computa qual MDE o `N` já registrado sustenta para H1c, e traduz isso no efeito que
seria necessário **dentro das oportunidades que o mecanismo alcança** — que é a
grandeza que decide se o estudo é possível, e a que ninguém tinha calculado.

⚠️ **Três aproximações, declaradas.** (a) o ICC vem do PREREG e foi estimado para o
desfecho de H1 (densidade por session-hour), não para uma proporção por oportunidade;
(b) `p0` e as oportunidades/dia vêm do archive **vivo**, já que o corpus congelado não
existe mais; (c) `is_error` é proxy do veredito do painel — o painel adjudica com τ=S1
e nem toda ação com erro é falha adjudicada. As três empurram em direções que não se
cancelam, e por isso o resultado é ordem de grandeza, não um número de dimensionamento.
"""
import argparse, json, math, sys

def poder_z(p0, p1, n, z_a):
    pb = (p0 + p1) / 2
    num = abs(p1 - p0) * math.sqrt(n) - z_a * math.sqrt(2 * pb * (1 - pb))
    den = math.sqrt(p1 * (1 - p1) + p0 * (1 - p0))
    return num / den if den else 0.0

def mde(p0, n, z_a, z_b):
    lo, hi = 0.0, p0
    for _ in range(200):
        mid = (lo + hi) / 2
        if poder_z(p0, mid, n, z_a) >= z_b: lo = mid
        else: hi = mid
    return lo

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--p0", type=float, required=True)
    ap.add_argument("--op-dia", type=float, required=True)
    ap.add_argument("--epochs", type=int, default=234)
    ap.add_argument("--epochs-tratamento", type=float,
                    help=("epochs-EQUIVALENTES no braco de tratamento; aceita fracao, "
                          "porque contar um epoch parcial como 1 atribui exposicao que "
                          "nao houve (09-01 entregou 630/672)"))
    ap.add_argument("--epochs-controle", type=float,
                    help="epochs-EQUIVALENTES no braco de controle; aceita fracao")
    ap.add_argument("--icc", type=float, default=0.098459)
    ap.add_argument("--cobertura", type=float, required=True)
    ap.add_argument("--cobertura-informativa", type=float, required=True)
    ap.add_argument("--out")
    a = ap.parse_args()
    z_a, z_b = 1.959964, 0.8416

    DE = 1 + (a.op_dia - 1) * a.icc
    if a.epochs_tratamento is not None or a.epochs_controle is not None:
        if a.epochs_tratamento is None or a.epochs_controle is None:
            sys.exit("RED informe os DOIS bracos ou nenhum")
        nt = a.epochs_tratamento * a.op_dia / DE
        nc = a.epochs_controle * a.op_dia / DE
        n_ef = 2 * nt * nc / (nt + nc)      # media harmonica, nao aritmetica
        bruto = None   # nao existe "por braco" quando os bracos diferem
        desbal = {"epochs_tratamento": a.epochs_tratamento,
                  "epochs_controle": a.epochs_controle,
                  "oportunidades_tratamento": round(a.epochs_tratamento * a.op_dia),
                  "oportunidades_controle": round(a.epochs_controle * a.op_dia),
                  "n_efetivo_tratamento": round(nt, 1), "n_efetivo_controle": round(nc, 1),
                  "criterio": ("media harmonica dos n efetivos (2/n = 1/nt + 1/nc); a "
                               "aritmetica sobrestima o poder. ⚠️ A harmonica tambem "
                               "sobrestima contra o calculo de dois grupos desiguais em "
                               "forma geral (~0,09 de z), logo e' o estimador GENEROSO "
                               "com a hipotese a refutar -- um veredito negativo sob ela "
                               "fica mais firme, nao menos, se refeito pela forma geral.")}
    else:
        bruto = (a.epochs // 2) * a.op_dia
        n_ef = bruto / DE
        desbal = None
    # Perna propria: `mde()` bisseca em [0, p0], logo rel SATURA em 1,0 e "MDE = 100%"
    # fica indistinguivel de "nem eliminar tudo e detectavel". A segunda e' um estado
    # diferente do mundo -- nao ha resultado possivel, nem em principio -- e tem de
    # aparecer, senao le-se como "precisa de efeito enorme" em vez de "impossivel".
    detectavel_no_limite = poder_z(a.p0, 0.0, n_ef, z_a) >= z_b
    # A afirmacao "nao existe efeito detectavel" e' categorica e o veredito e' proximo da
    # fronteira; sem a margem ela nao e' defensavel. Duas quantidades criticas:
    lo, hi = 1.0, 1e6
    for _ in range(300):
        mid = (lo + hi) / 2
        if poder_z(a.p0, 0.0, mid, z_a) >= z_b: hi = mid
        else: lo = mid
    n_ef_critico = hi
    lo_i, hi_i = 0.0, a.icc
    for _ in range(300):
        mid = (lo_i + hi_i) / 2
        DEm = 1 + (a.op_dia - 1) * mid
        if a.epochs_tratamento is not None:
            ntm = a.epochs_tratamento * a.op_dia / DEm
            ncm = a.epochs_controle * a.op_dia / DEm
            nm = 2 * ntm * ncm / (ntm + ncm)
        else:
            nm = (a.epochs // 2) * a.op_dia / DEm
        if poder_z(a.p0, 0.0, nm, z_a) >= z_b: lo_i = mid
        else: hi_i = mid
    icc_critico = lo_i
    p1 = mde(a.p0, n_ef, z_a, z_b)
    rel = (a.p0 - p1) / a.p0

    cenarios = {}
    for nome, cob in (("todas as cobertas", a.cobertura),
                      ("só as informativas", a.cobertura_informativa)):
        nec = rel / cob if cob > 0 else float("inf")
        cenarios[nome] = {
            "cobertura": round(cob, 4),
            "efeito_necessario_nas_cobertas": round(nec, 4),
            "possivel": nec <= 1.0,
        }

    saida = {
        "gerado_por": "measurement/potencia-h1c.py",
        "pergunta": "o N já registrado sustenta H1c como primária?",
        "entradas": {"p0": a.p0, "oportunidades_por_dia": a.op_dia,
                     "epochs": a.epochs, "icc": a.icc},
        "oportunidades_por_braco_bruto": (int(bruto) if bruto is not None else None),
        "nota_bruto": ("nulo quando os bracos diferem: nao existe 'por braco' unico. As "
                       "duas contagens estao em bracos_desbalanceados. O campo ja carregou "
                       "o valor do braco MENOR sob um nome que dizia 'por braco' -- mesma "
                       "classe do `exposto_h`, corrigido 2026-09-10."),
        "design_effect": round(DE, 2),
        "n_efetivo_por_braco": int(n_ef),
        "bracos_desbalanceados": desbal,
        "detectavel_no_limite_p1_igual_zero": detectavel_no_limite,
        "sensibilidade_do_veredito": {
            "n_efetivo_critico_para_p1_zero": round(n_ef_critico, 2),
            "n_efetivo_realizado": round(n_ef, 2),
            "fator_que_falta": round(n_ef_critico / n_ef, 3),
            "icc_critico": round(icc_critico, 6),
            "icc_usado": a.icc,
            "queda_de_icc_que_vira_o_veredito_pct": round(100 * (1 - icc_critico / a.icc), 1),
            "porque_importa": ("o ICC vem do PREREG e foi estimado para DENSIDADE por "
                               "session-hour, nao para proporcao por oportunidade -- uma "
                               "margem estreita num parametro estimado para outra grandeza "
                               "nao sustenta afirmacao categorica"),
        },
        "nota_saturacao": ("rel satura em 1,0 por construcao (bissecao em [0,p0]); se "
                           "detectavel_no_limite for false, NAO existe efeito detectavel "
                           "-- nem a eliminacao total das falhas repetidas"),
        "p1_detectavel": round(p1, 4),
        "mde_relativo_h1c": round(rel, 4),
        "mde_registrado_h1": 0.30,
        "cenarios": cenarios,
        "comparacao_com_h1_incondicional": {
            "fracao_de_briefs_alterada": 0.0314,
            "efeito_necessario": round(0.30 / 0.0314, 2),
            "possivel": False,
        },
        "aproximacoes": [
            "ICC estimado para densidade por session-hour, não para proporção por oportunidade",
            "p0 e oportunidades/dia do archive VIVO — o congelado não existe mais",
            "is_error é proxy do veredito do painel a τ=S1",
        ],
    }

    # ⚠️ O ARTEFATO SAI ANTES DOS GUARDAS (corrigido 2026-09-10). Os guardas abaixo
    # devolvem 1 e, na versão anterior, `return`avam antes do `--out` — logo o veredito
    # MAIS importante ("nem o cenário otimista é alcançável") era o único que não deixava
    # artefato. Em 2026-08-30 o guarda barrava uma decisão de desenho e abortar era certo;
    # com o ensaio a encerrar em 20 epochs o mesmo predicado passou a ser um ACHADO que
    # precisa de lastro. Mesmo conselho, ação oposta.
    #
    # Contrato: o código de saída carrega o veredito, o artefato carrega a evidência.
    if a.out:
        json.dump(saida, open(a.out, "w"), indent=2, ensure_ascii=False)

    # ── guardas ────────────────────────────────────────────────────────────
    # (1) o ponto inteiro da opção C é que H1c é POSSÍVEL onde H1 não é. Se o cenário
    #     otimista também for impossível, C não se sustenta e o script tem de dizer.
    if not cenarios["todas as cobertas"]["possivel"]:
        print(f"⛔ nem no cenário otimista H1c é alcançável: exigiria "
              f"{100*cenarios['todas as cobertas']['efeito_necessario_nas_cobertas']:.0f}% "
              f"de efeito nas cobertas. A opção C não se sustenta.", file=sys.stderr)
        return 1
    # (2) se o cenário pessimista fosse possível, a distinção entre os dois não
    #     informaria nada e o par de cenários seria decoração.
    if cenarios["só as informativas"]["possivel"]:
        print("⛔ os dois cenários dão possível — o par não discrimina, e a "
              "sensibilidade que ele existe para expor não está sendo exposta.",
              file=sys.stderr)
        return 1

    print(f"oportunidades/braço: {int(bruto):,}".replace(",", ".") +
          f"  ·  DE {DE:.1f}  ·  N efetivo {int(n_ef):,}".replace(",", "."))
    print(f"p0 {a.p0:.4f} → p1 detectável {p1:.4f}   MDE relativo H1c: {100*rel:.1f}%\n")
    for nome, c in cenarios.items():
        marca = "✅ possível" if c["possivel"] else "🔴 IMPOSSÍVEL"
        print(f"  {nome:<22} cobertura {100*c['cobertura']:>5.1f}%  ⇒ efeito necessário "
              f"{100*c['efeito_necessario_nas_cobertas']:>7.1f}%  {marca}")
    print(f"\n  {'H1 incondicional':<22} cobertura {100*0.0314:>5.1f}%  ⇒ efeito necessário "
          f"{100*0.30/0.0314:>7.1f}%  🔴 IMPOSSÍVEL")

    if a.out:
        print(f"\n→ {a.out}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
