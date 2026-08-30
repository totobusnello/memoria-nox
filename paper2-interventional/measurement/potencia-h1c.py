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
    ap.add_argument("--icc", type=float, default=0.098459)
    ap.add_argument("--cobertura", type=float, required=True)
    ap.add_argument("--cobertura-informativa", type=float, required=True)
    ap.add_argument("--out")
    a = ap.parse_args()
    z_a, z_b = 1.959964, 0.8416

    bruto = (a.epochs // 2) * a.op_dia
    DE = 1 + (a.op_dia - 1) * a.icc
    n_ef = bruto / DE
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
        "oportunidades_por_braco_bruto": int(bruto),
        "design_effect": round(DE, 2),
        "n_efetivo_por_braco": int(n_ef),
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
        json.dump(saida, open(a.out, "w"), indent=2, ensure_ascii=False)
        print(f"\n→ {a.out}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
