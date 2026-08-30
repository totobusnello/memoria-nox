#!/usr/bin/env python3
"""
censo-vocabulario-de-serving.py — o texto diz "servido" sobre o quê?

Esta é a classe de defeito mais cara do paper, e ela reincidiu **três vezes em um dia**:

| onde | o que dizia | por que era falso |
|---|---|---|
| abstract | "testamos com dose crescente **em produção**" | o serving nunca saiu de *shadow*; nada foi servido tratado |
| §1 | idem | idem |
| §4.4 | "a dose **servida** reproduz a taxa publicada" | corrigido no abstract uma hora antes e vivo aqui |

O paper corre em modo *shadow*: a composição tratada é **computada e registrada**, e o
que o agente recebe é sempre o controle. Os **estados** são de produção; a **intervenção**
não foi servida. Um verbo de entrega aplicado à intervenção é overclaim, e ele sobreviveu
a cinco revisões adversariais — porque revisão verifica o que está escrito, e este defeito
está no que o arco *sugere*.

Censo mecânico pega o que revisão não pega, e vice-versa: as duas classes são disjuntas.
Este script varre todo verbo de entrega e classifica pelo **objeto gramatical** a que se
aplica, por vizinhança léxica.

⚠️ **Poder de detecção, medido por mutação (30/08), não estimado.** De três mutações que
repõem o overclaim, **duas são pegas**:

| mutação | pega? | por quê |
|---|---|---|
| "a dose **servida em produção** reproduz a taxa" | ✅ | objeto da oração é `dose`, sem termo legítimo |
| repor "piso de relevância do sistema" na tabela | ✅ | (censo irmão, de rótulos) |
| "**Experimento** com dose crescente sobre 350 **estados**" | ❌ | genuinamente ambíguo: o experimento *é* sobre estados |

O terceiro caso não é falha de implementação — é ambiguidade real da frase, e refinar o
classificador até pegá-lo seria sobreajustá-lo aos meus próprios testes. Fica declarado
como limite: **este censo pega o overclaim quando o objeto da oração é a intervenção, e
não pega quando a oração menciona ambos.**

⚠️ **O que ele NÃO decide.** A classificação é heurística: "servido" perto de "estado" é
provavelmente legítimo, perto de "dose"/"intervenção"/"tratamento" é provavelmente
overclaim. As bordas precisam de leitura humana, e é por isso que a saída lista cada
ocorrência em vez de devolver só uma contagem. O valor do script é a **exaustividade** —
ele não esquece nenhuma ocorrência, que é exatamente o que aconteceu três vezes hoje.

Uso:
  censo-vocabulario-de-serving.py [--doc MANUSCRIPT.md] [--json] [--out ...]
"""
import argparse
import json
import pathlib
import re
import sys

# Verbos e locuções que afirmam entrega ao agente.
ENTREGA = [
    r"\bservid[oa]s?\b", r"\bserviu\b", r"\bservir\b", r"\bentregue?s?\b",
    r"\bentregou\b", r"\bem produção\b", r"\bimplantad[oa]s?\b", r"\bimplantar\b",
    r"\bexperimento\b", r"\bteste em produção\b", r"\brodou em produção\b",
]

# Vizinhança que indica o OBJETO. A intervenção é o que não pode ser dito servido.
INTERVENCAO = [
    r"\bdose\b", r"\bintervenção\b", r"\btratament\w+", r"\btratad[oa]s?\b",
    r"\bbônus\b", r"\bboost\b", r"\bbraço\b", r"\bw\s*=", r"\bdesignaç\w+",
]
# Objetos para os quais o verbo é legítimo: os estados, o brief, o corpus, o sistema.
LEGITIMO = [
    r"\bestados?\b", r"\bbrief\w*\b", r"\bchunks?\b", r"\bcorpus\b", r"\bslots?\b",
    r"\bsistema\b", r"\bagente\b", r"\bpool\b", r"\bcanal\b", r"\bcobertura\b",
    r"\bitens?\b", r"\bmemória\b",
]
JANELA = 90  # caracteres de cada lado


# ⚠️ Sem isto o script marca as PRÓPRIAS ressalvas como overclaim: "nada foi servido
# tratado" e "a intervenção não foi servida" têm vizinhança idêntica à da afirmação que
# elas negam. Um censo que alarma sobre a correção não distingue o defeito do remédio,
# e o operador aprende a ignorá-lo — que é o modo como um guarda morre.
NEGACAO = [
    r"\bn[ãa]o\s+(?:foi|foram|é|são|havia|chegou)\b", r"\bnada\s+(?:foi|ainda)\b",
    r"\bnunca\b", r"\bantes de\b", r"\bsem que\b", r"\bjamais\b",
    r"\bnenhum[ao]?\b", r"\bdeixa de\b",
]


# ⚠️ Classe descoberta em 30/08 por leitura de arco, e que este censo NÃO pegava.
# A tabela de dose do §4.4 trazia a coluna `w = 2` rotulada `(servido)`, com a
# ressalva — "significa a dose em vigor no shadow" — no parágrafo imediatamente acima.
# O censo classificou como legítima porque a vizinhança tinha "estados", e um revisor
# humano leu "Testamos … (servido) … Resultado" como estudo interventivo entregue.
#
# O que torna a célula de tabela diferente de prosa: **ela é lida sem o parágrafo que a
# precede.** Um leitor varre a tabela, e a defesa que mora fora dela não o alcança.
# Logo um verbo de entrega dentro de célula precisa ser autossuficiente — não pode
# depender de contexto externo para não afirmar demais.
#
# Isto é ESTREITO de propósito: só reprova o verbo de entrega SOZINHO numa célula
# (entre `|`), sem termo legítimo dentro da própria célula. `| estados servidos |`
# passa, `| **2** (servido) |` não.
def em_celula_isolada(texto: str, ini: int, fim: int) -> bool:
    lin0 = texto.rfind("\n", 0, ini) + 1
    lin1 = texto.find("\n", fim)
    linha = texto[lin0:lin1 if lin1 > 0 else len(texto)]
    if linha.count("|") < 2:
        return False
    # ⚠️ A primeira versão exigia só que a CÉLULA não repetisse o objeto, e mordeu o
    # inocente: `| servidos no dia |` é rótulo de contagem de chunks, legítimo, e não
    # repete "chunks" porque a tabela já o diz. O que separa esse caso de
    # `| **2** (servido) |` não é a célula — é a LINHA: no overclaim, o verbo qualifica
    # um valor da dose, e a linha inteira é sobre `w`. Exigir a intervenção na linha
    # distingue os dois sem desligar o guarda.
    if not any(re.search(p, linha, re.I) for p in INTERVENCAO + [r"`w`"]):
        return False
    p_ini = texto.rfind("|", lin0, ini)
    p_fim = texto.find("|", fim)
    if p_ini < 0 or p_fim < 0:
        return False
    celula = texto[p_ini + 1:p_fim]
    if len(celula) > 60:
        return False
    return not any(re.search(p, celula, re.I) for p in LEGITIMO + NEGACAO)


def classifica(ctx: str, termo_citado: bool = False) -> str:
    # ⚠️ Um verbo ENTRE ASPAS é citação do rótulo, não afirmação de entrega — o texto
    # está explicando o que a palavra significa naquela coluna, que é o oposto de
    # afirmá-la. Sem isto o censo reprova a própria explicação, e um guarda que morde
    # o remédio é desligado pelo operador na terceira vez.
    if termo_citado:
        return "CITADO"
    if any(re.search(p, ctx, re.I) for p in NEGACAO):
        return "NEGADO"
    tem_i = any(re.search(p, ctx, re.I) for p in INTERVENCAO)
    tem_l = any(re.search(p, ctx, re.I) for p in LEGITIMO)
    if tem_i and not tem_l:
        return "OVERCLAIM_PROVAVEL"
    if tem_i and tem_l:
        return "AMBIGUO"
    return "LEGITIMO_PROVAVEL"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--doc", default="MANUSCRIPT.md")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--out")
    a = ap.parse_args()

    doc = pathlib.Path(a.doc)
    if not doc.exists():
        print(f"⛔ {doc} não existe", file=sys.stderr)
        return 1
    texto = doc.read_text(encoding="utf-8")

    achados = []
    vistos = set()
    for pat in ENTREGA:
        for m in re.finditer(pat, texto, re.I):
            if m.start() in vistos:
                continue
            vistos.add(m.start())
            ini, fim = max(0, m.start() - JANELA), min(len(texto), m.end() + JANELA)
            ctx = texto[ini:fim].replace("\n", " ")
            # ⚠️ A janela fixa cruza fronteira de frase e captura o objeto ERRADO.
            # Mutação de 30/08: "a dose servida em produção" foi classificada como
            # AMBÍGUA porque o item anterior da lista dizia "0 estados não monótonos",
            # e "estados" é objeto legítimo — a 50 caracteres de distância, noutra
            # oração. O objeto de um verbo está na mesma oração; recortar por
            # proximidade sintática é mais fiel que por contagem de bytes.
            antes = texto[ini:m.start()].replace("\n", " ")
            corte = max(antes.rfind("; "), antes.rfind(". "), antes.rfind("— "),
                        antes.rfind("- "), antes.rfind("| "))
            if corte >= 0:
                ctx = antes[corte + 2:] + texto[m.start():fim].replace("\n", " ")
            # ⚠️ Aspas E crase. O Apêndice H descreve a correção escrevendo o rótulo
            # errado — `(servido)` — entre crases, que é como se cita um rótulo de
            # código. Sem incluir a crase, o censo reprova a própria retratação, que é
            # o modo como um guarda perde a confiança de quem o lê. Isto NÃO desliga a
            # detecção do caso real: na tabela o rótulo vinha entre parênteses, sem
            # crase, e a mutação continua mordendo.
            aspas = ('"', '`')
            citado = (texto[max(0, m.start() - 1)] in aspas
                      and texto[m.end():m.end() + 1] in aspas)
            if not citado:
                viz_a, viz_d = texto[max(0, m.start() - 3):m.start()], texto[m.end():m.end() + 3]
                citado = any(c in viz_a for c in aspas) and any(c in viz_d for c in aspas)
            classe = classifica(ctx, termo_citado=citado)
            # célula de tabela isolada: a defesa fora dela não alcança quem varre a
            # tabela, então o rótulo tem de bastar por si.
            if not citado and em_celula_isolada(texto, m.start(), m.end()):
                classe = "ROTULO_DE_CELULA_SEM_DEFESA"
            achados.append({
                "linha": texto[:m.start()].count("\n") + 1,
                "termo": m.group(0),
                "classe": classe,
                "contexto": ctx.strip(),
            })
    achados.sort(key=lambda d: d["linha"])

    conta = {}
    for x in achados:
        conta[x["classe"]] = conta.get(x["classe"], 0) + 1
    suspeitos = [x for x in achados
                 if x["classe"] in ("OVERCLAIM_PROVAVEL", "AMBIGUO")]
    # ⚠️ "NEGADO" é o estado saudável deste paper — a frase diz que a intervenção NÃO
    # foi servida. Se ele zerar, as ressalvas sumiram do texto.
    negados = [x for x in achados if x["classe"] == "NEGADO"]

    saida = {
        "ocorrencias": len(achados),
        "por_classe": conta,
        "para_leitura_humana": suspeitos,
        "nao_decide": ("a classificação é por vizinhança léxica; as bordas exigem "
                       "leitura. O valor do script é não esquecer nenhuma ocorrência."),
    }

    # ── guardas ────────────────────────────────────────────────────────────
    # (1) zero ocorrências num paper cujo objeto é uma superfície de serving só pode
    #     ser padrão quebrado, não texto limpo.
    if not achados:
        print("⛔ nenhuma ocorrência de verbo de entrega — num paper sobre uma "
              "superfície que serve memória, isso é padrão quebrado, não texto limpo.",
              file=sys.stderr)
        return 1
    # (2) se TODAS caírem numa classe só, a classificação não está discriminando.
    if not negados:
        print("⛔ nenhuma ocorrência NEGADA — este paper corre em shadow, então as "
              "frases que dizem que a intervenção NÃO foi servida têm de existir. "
              "Zero delas significa que as ressalvas saíram do texto.", file=sys.stderr)
        return 1
    if len(conta) == 1:
        print(f"⛔ todas as {len(achados)} ocorrências na mesma classe "
              f"({list(conta)[0]}) — o classificador não está discriminando.",
              file=sys.stderr)
        return 1
    # (3) ⚠️ O GUARDA QUE FALTAVA. A primeira versão deste script LISTAVA os overclaims
    #     e saía 0 — um censo que reporta sem reprovar não propaga nada, e o
    #     `censos_check` do verificador ficava verde com o defeito na tela. Mutação de
    #     30/08: repor "a dose servida em produção" passou incólume.
    #     Reprova só `OVERCLAIM_PROVAVEL`; `AMBIGUO` exige leitura humana e não pode
    #     travar o verificador, senão o guarda vira ruído e é desligado.
    overclaims = [x for x in achados
                  if x["classe"] in ("OVERCLAIM_PROVAVEL", "ROTULO_DE_CELULA_SEM_DEFESA")]
    if overclaims:
        print(f"⛔ {len(overclaims)} verbo(s) de entrega aplicado(s) à INTERVENÇÃO, "
              f"que nunca foi servida (o paper corre em shadow):", file=sys.stderr)
        for x in overclaims:
            print(f"    L{x['linha']}: «{x['termo']}» — …{x['contexto'][:110]}…",
                  file=sys.stderr)
        return 1

    if a.json:
        print(json.dumps(saida, indent=2, ensure_ascii=False))
    else:
        print(f"{len(achados)} ocorrências de verbo de entrega\n")
        for c, n in sorted(conta.items(), key=lambda kv: -kv[1]):
            print(f"  {n:>3}  {c}")
        if suspeitos:
            print(f"\n── {len(suspeitos)} para leitura humana:")
            for x in suspeitos:
                print(f"\n  L{x['linha']} [{x['classe']}] «{x['termo']}»")
                print(f"     …{x['contexto'][:150]}…")

    if a.out:
        json.dump(saida, open(a.out, "w"), indent=2, ensure_ascii=False)
        print(f"\n→ {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
