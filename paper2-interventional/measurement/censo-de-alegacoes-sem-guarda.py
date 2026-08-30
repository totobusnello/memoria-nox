#!/usr/bin/env python3
"""
censo-de-alegacoes-sem-guarda.py — quantos números do manuscrito o verificador protege?

Objeção de revisão adversarial (Codex, 2026-08-29), a de maior alcance das cinco:

> `claims_check.py` limpa números band-dependent mas ignora a maior parte das alegações
> quantitativas. 15 de 18 números principais não têm guarda nenhuma.

A alegação é verificável e não pode ser aceita de terceiro — inclusive porque o revisor
rodava em sandbox *read-only* e afirmou ter "testado mutações", o que ali não é possível.
Este script recomputa o censo do lado de cá.

**Método, e os limites dele.** Um número é "coberto" quando aparece, na forma exata em
que o texto o escreve, dentro de algum literal ou f-string do `claims_check.py`, OU
quando o valor vem de um artefato JSON que o `claims_check` lê e ancora. Isso é
aproximação por dois lados:

- **falso coberto:** o valor pode aparecer no verificador por coincidência (o guarda
  ancora outra coisa que contém o mesmo dígito). Este script marca esses como
  `COBERTURA_FRACA` quando o número tem menos de 4 dígitos significativos;
- **falso descoberto:** um guarda pode proteger o número por caminho que a busca textual
  não vê (recomputando-o de um artefato sem citar o literal). Por isso a coluna
  `artefato` — se o número está num JSON que o `claims_check` lê, ele conta como coberto
  ainda que o literal não apareça.

⚠️ O que este censo **não** decide é se a cobertura é boa. Guarda que existe e não morde
é assunto do teste de mutação, não do censo — as duas coisas pegam classes diferentes.

Uso:
  censo-de-alegacoes-sem-guarda.py [--raiz .] [--json] [--out ...]
"""
import argparse
import json
import pathlib
import re
import sys

# Números que o manuscrito afirma como resultado de medição. Lista curada: um censo
# por regex sobre todos os dígitos do texto devolveria datas, números de linha, seções
# e citações bibliográficas, e a taxa de cobertura resultante seria ficção.
ALEGACOES = [
    ("583.763", "slots acumulados na janela"),
    ("8,7", "capacidade em múltiplos do corpus"),
    ("67.187", "corpus vivo"),
    ("1.787", "distintos servidos no brief"),
    ("2,66%", "cobertura do brief"),
    ("99,98%", "cobertura sob serviço uniforme"),
    ("83,78%", "nunca exposto, agregado"),
    ("56.288", "nunca expostos, absoluto"),
    ("10.899", "união viva de expostos"),
    ("9.755", "expostos pela busca"),
    ("152", "servidos e apagados depois"),
    ("47,16%", "fração dos slots no top-10"),
    ("4.632", "briefs na semana"),
    ("108", "pool elegível do canal de cobertura"),
    ("0,161%", "pool como fração do corpus"),
    ("12,4", "slots por candidato elegível"),
    ("10.008", "elegíveis e nunca expostos"),
    ("74,75%", "taxa condicionada ao piso"),
    ("13.388", "chunks que passam o piso"),
    ("46.280", "nunca expostos ABAIXO do piso"),
    ("82,2%", "fração dos nunca expostos abaixo do piso"),
    ("8.928", "distilled entre os elegíveis"),
    ("232", "comprimento médio do subconjunto"),
    ("85,50%", "coorte madura, nunca exposto"),
    ("1,295", "maior lacuna no eixo, em décadas"),
    ("32,1%", "lacuna como fração da amplitude"),
    ("−0,961", "beta binomial, 15 tipos"),
    ("−0,728", "Pearson, 13 tipos"),
    ("0,471", "erro-padrão por jackknife"),
    ("4,86%", "teto do canal, resolução de segundo"),
    ("36%", "teto sob granularidade de minuto"),
    ("80%", "teto sob granularidade de hora"),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raiz", default=str(pathlib.Path(__file__).resolve().parent.parent))
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--out")
    a = ap.parse_args()

    raiz = pathlib.Path(a.raiz)
    verificador = (raiz / "claims_check.py").read_text(encoding="utf-8")
    doc = (raiz / "MANUSCRIPT.md").read_text(encoding="utf-8")

    # artefatos que o verificador de fato abre — só estes podem cobrir um número
    # ⚠️ Os artefatos são lidos por DOIS caminhos no verificador — `out/` e
    # `out/` — e uma primeira versão desta extração capturava só o nome
    # final, apontando `out/superficie.json` para `out/`. O guarda (2)
    # abaixo mordeu na hora, o que é o comportamento certo: caminho errado faria o
    # censo achar que há menos guarda do que há.
    diretos = set(re.findall(r'"((?:measurement/)?out/[^"]+\.json)"', verificador))
    montados = set()
    for pre, nome in re.findall(r'/ "(measurement|out)"(?: / "out")? / "([^"]+\.json)"',
                                verificador):
        montados.add(f"out/{nome}" if pre == "measurement" else f"out/{nome}")
    lidos = sorted(diretos | montados)
    corpo_artefatos = ""
    faltando = []
    for nome in lidos:
        p = raiz / nome
        if p.exists():
            corpo_artefatos += p.read_text(encoding="utf-8")
        else:
            faltando.append(str(p.relative_to(raiz)))

    linhas = []
    for valor, rotulo in ALEGACOES:
        if valor not in doc:
            linhas.append({"valor": valor, "rotulo": rotulo, "estado": "AUSENTE_DO_TEXTO"})
            continue
        cru = valor.rstrip("%").replace(".", "").replace(",", ".").lstrip("−-")
        # ⚠️ Comparar como STRING dá falso-negativo, e ele aparece de duas formas:
        # o verificador constrói o valor por f-string (`f"{x:.2f}"`), então o literal
        # nunca está no fonte; e o artefato guarda `85.5` onde o texto escreve
        # `85,50%`. Um censo assim reporta "sem guarda" para número protegido, e eu
        # iria "consertar" o que já estava coberto. Comparação por VALOR.
        alvo = float(cru)
        def tem(corpo: str) -> bool:
            return any(abs(float(m) - alvo) < 10 ** -9
                       for m in re.findall(r"-?\d+\.?\d*", corpo.replace(",", "")))
        no_verificador = valor in verificador or tem(verificador)
        no_artefato = tem(corpo_artefatos)
        digitos = len(cru.replace(".", ""))
        if no_verificador or no_artefato:
            estado = "COBERTO" if digitos >= 4 else "COBERTURA_FRACA"
        else:
            estado = "SEM_GUARDA"
        linhas.append({"valor": valor, "rotulo": rotulo, "estado": estado,
                       "no_verificador": no_verificador, "no_artefato_lido": no_artefato})

    conta = {}
    for l in linhas:
        conta[l["estado"]] = conta.get(l["estado"], 0) + 1
    saida = {
        "alegacoes_curadas": len(ALEGACOES),
        "artefatos_lidos_pelo_verificador": lidos,
        "artefatos_citados_mas_ausentes": faltando,
        "contagem": conta,
        "pct_sem_guarda": round(100 * conta.get("SEM_GUARDA", 0) / len(ALEGACOES), 1),
        "detalhe": linhas,
    }

    # ── guardas ────────────────────────────────────────────────────────────
    # (1) número que sumiu do texto: a lista curada envelhece junto com o manuscrito,
    #     e um item que deixou de existir tem de acusar em vez de contar como coberto.
    sumiram = [l["valor"] for l in linhas if l["estado"] == "AUSENTE_DO_TEXTO"]
    if sumiram:
        print(f"⛔ {len(sumiram)} alegação(ões) da lista não estão mais no manuscrito: "
              f"{sumiram} — atualizar a lista curada, não ignorar.", file=sys.stderr)
        return 1
    # (2) artefato citado pelo verificador e ausente do disco: sem ele a cobertura
    #     medida aqui é maior que a real, porque o corpo de busca fica menor.
    if faltando:
        print(f"⛔ o verificador cita artefato(s) que não existem: {faltando} — o censo "
              f"subestimaria a falta de guarda.", file=sys.stderr)
        return 1

    if a.json:
        print(json.dumps(saida, indent=2, ensure_ascii=False))
    else:
        print(f"{len(ALEGACOES)} alegações numéricas curadas do MANUSCRIPT\n")
        for est in ("SEM_GUARDA", "COBERTURA_FRACA", "COBERTO"):
            sel = [l for l in linhas if l["estado"] == est]
            print(f"── {est}: {len(sel)}")
            for l in sel:
                print(f"     {l['valor']:>10}  {l['rotulo']}")
        print(f"\n⇒ {saida['pct_sem_guarda']}% das alegações não têm guarda nenhuma.")
        print(f"⇒ artefatos que o verificador lê: {len(lidos)}")

    if a.out:
        json.dump(saida, open(a.out, "w"), indent=2, ensure_ascii=False)
        print(f"→ {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
