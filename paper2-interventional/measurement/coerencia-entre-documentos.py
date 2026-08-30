#!/usr/bin/env python3
"""
coerencia-entre-documentos.py — o mesmo rótulo carrega o mesmo número em todo lugar?

Terceira perna da retrospectiva de 2026-08-30. As duas primeiras olharam o manuscrito
contra os artefatos (`claims_check`) e os artefatos contra as leituras
(`auditoria-da-cadeia`). Falta o eixo que nenhuma delas cobre: **os 60 documentos do
pacote entre si**.

O risco é concreto e já se materializou duas vezes neste repositório:

- o `583.973` viveu cinco lugares do manuscrito enquanto o artefato dizia `583.763`;
- a contagem do catálogo de defeitos dizia "16, sete deles" em cinco pontos enquanto a
  tabela já tinha oito linhas.

Nos dois casos o erro sobreviveu porque **nada comparava as ocorrências entre si**. Entre
documentos o risco é maior: uma decisão registrada em 25/08 e um resultado escrito em
30/08 não se olham, e o leitor que abrir os dois vê a contradição que nós não vimos.

Este script procura, para cada rótulo canônico, o número que o acompanha em **cada**
documento, e reporta divergência.

⚠️ **O que ele NÃO decide.** Divergência pode ser legítima: um documento de 18/08 que
registra um valor *depois retratado* está certo em preservá-lo — a retratação é o
histórico. Por isso a saída separa `DIVERGE` de `DIVERGE_EM_DOC_HISTORICO`, e a segunda
categoria é informativa, não falha. O julgamento é humano; o script garante que a
comparação foi feita.

Uso:
  coerencia-entre-documentos.py [--raiz .] [--json] [--out ...]
"""
import argparse
import json
import pathlib
import re
import sys

# Rótulo canônico → (padrão que o localiza, valor vigente no manuscrito).
# Só entram números que o manuscrito AFIRMA hoje; um número que só existe no
# histórico não tem valor canônico contra o qual divergir.
CANONICOS = [
    ("corpus vivo", r"67\.187", "67.187"),
    ("nunca expostos", r"56\.288", "56.288"),
    ("taxa de não-exposição", r"83,78\s*%", "83,78%"),
    ("slots acumulados", r"583\.\d{3}", "583.763"),
    ("distintos no brief", r"1\.787", "1.787"),
    ("pool elegível do canal", r"\b108\b(?!\d)", "108"),
    ("teto do canal", r"4,86\s*%", "4,86%"),
    ("teto sob outro sorteio", r"7,43\s*%", "7,43%"),
    ("elegíveis nunca expostos", r"10\.008", "10.008"),
    ("chunks que passam o piso", r"13\.388", "13.388"),
    ("estados do replay", r"350 de 350|350 estados", "350"),
]

# Documentos que registram estado ANTERIOR por desenho: divergência neles é o
# histórico funcionando, não defeito.
HISTORICOS = re.compile(
    r"(RETRACTION|AMENDMENT|REMEDIATION|DEVIATIONS|DECISION-|PREREG|"
    r"-DRAFT|DEFECT|_archive|HANDOFF|SPLIT|SEED)", re.I)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raiz", default=str(pathlib.Path(__file__).resolve().parent.parent))
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--out")
    a = ap.parse_args()

    raiz = pathlib.Path(a.raiz)
    docs = sorted(p for p in raiz.glob("*.md") if p.name != "MANUSCRIPT.md")
    manu = raiz / "MANUSCRIPT.md"
    if not manu.exists():
        print("⛔ MANUSCRIPT.md não encontrado", file=sys.stderr)
        return 1
    texto_manu = manu.read_text(encoding="utf-8")

    # (0) o canônico tem de estar no manuscrito; se não estiver, a lista envelheceu
    fora = [rot for rot, pat, val in CANONICOS if val not in texto_manu]
    if fora:
        print(f"⛔ valor(es) canônico(s) ausente(s) do manuscrito: {fora} — a lista "
              f"deste script envelheceu junto com o texto.", file=sys.stderr)
        return 1

    achados, historicos = [], []
    examinadas = 0  # ⚠️ sem esta contagem, "zero divergências" é indistinguível de
                    # "zero ocorrências examinadas" — o guarda (3) abaixo separa.
    for doc in docs:
        try:
            t = doc.read_text(encoding="utf-8")
        except Exception:
            continue
        for rot, pat, canon in CANONICOS:
            for m in re.finditer(pat, t):
                # ⚠️ Comparar a FRASE casada com o valor canônico dá falso positivo:
                # "350 de 350" normalizado vira "350de350", que difere de "350". O que
                # se compara é o NÚMERO, extraído do match — a frase é só o localizador.
                num = re.search(r"\d[\d.,]*", m.group(0))
                if not num:
                    continue
                visto = num.group(0).rstrip(".,")
                examinadas += 1
                if visto == canon.rstrip("%").strip():
                    continue
                item = {
                    "documento": doc.name, "rotulo": rot,
                    "canonico": canon, "encontrado": visto,
                    "linha": t[:m.start()].count("\n") + 1,
                    "contexto": t[max(0, m.start() - 80):m.end() + 60]
                                 .replace("\n", " ").strip(),
                }
                (historicos if HISTORICOS.search(doc.name) else achados).append(item)

    saida = {
        "documentos_varridos": len(docs),
        "ocorrencias_examinadas": examinadas,
        "rotulos_canonicos": len(CANONICOS),
        "divergencias": achados,
        "divergencias_em_documento_historico": historicos,
    }

    # ── guardas ────────────────────────────────────────────────────────────
    # (1) divergência em documento NÃO-histórico: dois textos vigentes afirmam
    #     números diferentes para a mesma grandeza, e o leitor que abrir os dois vê.
    if achados:
        print(f"⛔ {len(achados)} divergência(s) entre documentos vigentes:",
              file=sys.stderr)
        for x in achados:
            print(f"    {x['documento']}:{x['linha']} — {x['rotulo']}: canônico "
                  f"{x['canonico']}, encontrado {x['encontrado']}", file=sys.stderr)
            print(f"      …{x['contexto'][:120]}…", file=sys.stderr)
        return 1
    # (2) zero documentos varridos = escopo errado, e o script diria "coerente" por
    #     cegueira — a mesma falha que a auditoria da cadeia cometeu com a raiz.
    if not docs:
        print("⛔ nenhum documento varrido — escopo errado.", file=sys.stderr)
        return 1
    # (3) ZERO ocorrências examinadas com 11 rótulos e 59 documentos significa que os
    #     padrões não casam mais — e o veredito "coerente" viria de cegueira, não de
    #     coerência. É a mesma classe do guarda cujo predicado exige o dado que falta.
    if examinadas < len(CANONICOS):
        print(f"⛔ só {examinadas} ocorrência(s) examinada(s) em {len(docs)} documentos "
              f"com {len(CANONICOS)} rótulos — os padrões não estão casando, e "
              f"'nenhuma divergência' seria cegueira e não coerência.", file=sys.stderr)
        return 1

    if a.json:
        print(json.dumps(saida, indent=2, ensure_ascii=False))
    else:
        print(f"{len(docs)} documentos · {len(CANONICOS)} rótulos canônicos\n")
        print("✅ nenhuma divergência entre documentos vigentes")
        if historicos:
            print(f"\n📌 {len(historicos)} divergência(s) em documento HISTÓRICO "
                  f"(esperado — é o registro preservando o valor retratado):")
            por_doc = {}
            for x in historicos:
                por_doc.setdefault(x["documento"], []).append(x)
            for d, xs in sorted(por_doc.items()):
                rots = sorted({f"{x['rotulo']} {x['encontrado']}≠{x['canonico']}"
                               for x in xs})
                print(f"     {d}: {'; '.join(rots[:3])}")

    if a.out:
        json.dump(saida, open(a.out, "w"), indent=2, ensure_ascii=False)
        print(f"\n→ {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
