#!/usr/bin/env python3
"""
censo-de-rotulos-de-populacao.py — cada rótulo nomeia a população que ele mede?

Esta é a classe que produziu **três camadas do mesmo defeito em dois dias**, cada
correção criando a seguinte:

| camada | rótulo escrito | por que era falso | quem achou |
|---|---|---|---|
| 1 | "piso do **próprio sistema**" | é o piso de **um canal**, não do sistema | DeepSeek |
| 2 | "o que o canal **considera elegível**" | o canal aplica **três** condições; o piso é uma | DeepSeek |
| 3 | "passa o **piso de importância** do canal" | ✅ | — |

A distância entre a camada 2 e a verdade é de duas ordens de grandeza: o piso sozinho
seleciona **13.388**, e as três condições juntas selecionam **108**.

O defeito não é ignorância do código — em todas as camadas o número estava certo. É que
o **rótulo** em português e a **definição operacional** no SQL divergem sem que nada
acuse. Revisão adversarial pega isso quando lê o código junto; censo pega sempre, e é
por isso que os dois são necessários.

Este script extrai, de cada script de medição, o predicado SQL que define a população, e
lista o rótulo que o manuscrito usa para o número correspondente. **Ele não decide se o
rótulo está certo** — decide que os dois estão lado a lado, para leitura humana. É a
única forma honesta: nomear população é ato de linguagem, não de cálculo.

Uso:
  censo-de-rotulos-de-populacao.py [--raiz .] [--json] [--out ...]
"""
import argparse
import json
import pathlib
import re
import sys

# Números que nomeiam uma população no manuscrito, com o script que os produz e a
# condição que os define. A coluna `condicoes` é o que o leitor precisa para julgar
# se o rótulo cabe.
POPULACOES = [
    {"valor": "67.187", "script": "superficie-de-exposicao.py",
     "condicoes": ["nenhuma — é o corpus vivo inteiro"]},
    {"valor": "56.288", "script": "superficie-de-exposicao.py",
     "condicoes": ["NOT (id IN brief_log OR access_count > 0)"]},
    {"valor": "13.388", "script": "exposicao-por-coorte.py",
     "condicoes": ["importance >= 0,7 OR pain >= 0,7"]},
    {"valor": "10.008", "script": "composicao-do-piso.py",
     "condicoes": ["importance >= 0,7 OR pain >= 0,7",
                   "NOT (id IN brief_log OR access_count > 0)"]},
    {"valor": "108", "script": "pool-elegivel.py",
     "condicoes": ["importance >= 0,7 OR pain >= 0,7",
                   "source_file LIKE 'memory/entities/%' OR 'memory/lessons.md'",
                   "idade <= 30 dias (sub-pool global) / 7 dias (por agente)"]},
    {"valor": "149", "script": "contrafactual-do-topo.py",
     "condicoes": ["servido na janela 20–27/08", "ainda existente em chunks"]},
    {"valor": "201", "script": "superficie-de-exposicao.py",
     "condicoes": ["servido na janela 20–27/08"]},
]

# Rótulos que já se provaram perigosos: cada um foi escrito errado ao menos uma vez.
ROTULOS_DE_RISCO = [
    (r"piso d[eo] (?:relevância d[eo] )?(?:próprio )?sistema", "atribui ao SISTEMA o que é de um canal"),
    (r"(?:o )?(?:canal|sistema) considera(?:ria)? elegí", "confunde UMA condição com as TRÊS"),
    (r"(?:o )?sistema marcou como relevante", "atribui julgamento global a limiar de canal"),
    (r"elegívei?s? pelo piso", "piso é condição necessária, não suficiente"),
]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raiz", default=str(pathlib.Path(__file__).resolve().parent.parent))
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--out")
    a = ap.parse_args()

    raiz = pathlib.Path(a.raiz)
    doc = (raiz / "MANUSCRIPT.md")
    if not doc.exists():
        print("⛔ MANUSCRIPT.md não encontrado", file=sys.stderr)
        return 1
    texto = doc.read_text(encoding="utf-8")

    # (1) reincidência dos rótulos que já erraram.
    # ⚠️ Um rótulo errado **citado dentro da própria retratação** não é reincidência —
    # é a retratação funcionando. Sem esta distinção o guarda morde o remédio, que é
    # como um guarda perde a confiança de quem o lê. A citação é reconhecida por vir
    # entre aspas ou por estar numa linha de tabela do histórico de correções.
    # ⚠️ A primeira versão usava `^\s*\|` como marca de citação — o que classifica
    # QUALQUER linha de tabela como citação, inclusive a tabela do §4.1, que é
    # afirmação. Mutação de 30/08 provou: repor "piso de relevância do sistema" na
    # tabela passou pelo guarda. Um detector de exceção largo demais desliga o guarda
    # exatamente onde ele mais importa.
    #
    # Agora: citação é (a) trecho entre aspas, (b) precedido de verbo de retratação,
    # ou (c) DENTRO do Apêndice H, que é o único lugar onde o rótulo errado tem
    # direito de aparecer.
    ini_h = texto.find("## Apêndice H")
    CITACAO = [r'"[^"\n]{0,80}$', r"\bdizia\b", r"versão anterior", r"não alcançou"]
    reincidentes, citados = [], []
    for pat, porque in ROTULOS_DE_RISCO:
        for m in re.finditer(pat, texto, re.I):
            ln = texto[:m.start()].count("\n") + 1
            antes = texto[max(0, m.start() - 160):m.start()]
            no_apendice_h = ini_h >= 0 and m.start() > ini_h
            item = {"linha": ln, "trecho": m.group(0), "por_que_e_risco": porque,
                    "em_apendice_h": no_apendice_h}
            if no_apendice_h or any(re.search(c, antes, re.I) for c in CITACAO):
                citados.append(item)
            else:
                reincidentes.append(item)

    # (2) para cada população, os rótulos que a acompanham no texto
    linhas = []
    for p in POPULACOES:
        ctx = []
        for m in re.finditer(re.escape(p["valor"]), texto):
            ini, fim = max(0, m.start() - 110), min(len(texto), m.end() + 60)
            ctx.append({"linha": texto[:m.start()].count("\n") + 1,
                        "trecho": texto[ini:fim].replace("\n", " ").strip()})
        linhas.append({**p, "mencoes": len(ctx), "contextos": ctx,
                       "script_existe": (raiz / "measurement" / p["script"]).exists()})

    ausentes = [l["script"] for l in linhas if not l["script_existe"]]
    sem_mencao = [l["valor"] for l in linhas if l["mencoes"] == 0]

    saida = {
        "populacoes": linhas,
        "rotulos_reincidentes": reincidentes,
        "rotulos_citados_em_retratacao": citados,
        "nao_decide": ("nomear população é ato de linguagem; o script põe rótulo e "
                       "predicado lado a lado e deixa o julgamento para quem lê"),
    }

    # ── guardas ────────────────────────────────────────────────────────────
    # (1) um rótulo já corrigido que reaparece é a assinatura EXATA desta classe:
    #     a correção não alcança onde o defeito também está.
    if reincidentes:
        print(f"⛔ {len(reincidentes)} rótulo(s) de risco reapareceram no texto:",
              file=sys.stderr)
        for r in reincidentes:
            print(f"    L{r['linha']}: «{r['trecho']}» — {r['por_que_e_risco']}",
                  file=sys.stderr)
        return 1
    # (2) script de medição ausente: o predicado da tabela acima deixa de ser
    #     verificável e a tabela vira prosa.
    if ausentes:
        print(f"⛔ script(s) de medição ausente(s): {ausentes} — sem eles o predicado "
              f"declarado aqui não é conferível contra nada.", file=sys.stderr)
        return 1
    # (3) população que o manuscrito não menciona mais: a lista envelheceu.
    if sem_mencao:
        print(f"⛔ {sem_mencao} não aparecem no manuscrito — a lista de populações "
              f"envelheceu junto com o texto.", file=sys.stderr)
        return 1

    if a.json:
        print(json.dumps(saida, indent=2, ensure_ascii=False))
    else:
        print("população   menções  condições que a definem")
        for l in linhas:
            print(f"{l['valor']:>10} {l['mencoes']:>8}   {l['condicoes'][0]}")
            for c in l["condicoes"][1:]:
                print(f"{'':>19}   + {c}")
        print(f"\n✅ nenhum rótulo de risco reincidiu como AFIRMAÇÃO "
              f"({len(ROTULOS_DE_RISCO)} padrões vigiados; {len(citados)} ocorrência(s) "
              f"são citação dentro da própria retratação, que é o uso correto)")
        print("\n⚠️ o par que mais confunde: **13.388** passa o piso; **108** é o pool "
              "elegível de fato. Duas ordens de grandeza, e três redações do rótulo "
              "foram necessárias para dizer isso sem afirmar demais.")

    if a.out:
        json.dump(saida, open(a.out, "w"), indent=2, ensure_ascii=False)
        print(f"→ {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
