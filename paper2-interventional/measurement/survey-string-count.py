#!/usr/bin/env python3
"""survey-string-count.py — recomputa as contagens de string citadas sobre o survey.

O §1 do manuscrito afirma que o survey canônico da área (Huang et al., TMLR 07/2026,
arXiv:2602.06052v4) tem **zero** ocorrências de "pre-registration". Até 2026-08-28 esse
número vinha de nota de leitura de 13/08. Prosa que afirma resultado computado é cache
sem invalidação: a derivação tem de estar em script, e o script tem de ser rodável por
quem lê.

⚠️ Três armadilhas que a contagem ingênua cai, e que este script trata:

1. **Hifenização de fim de linha.** `pdftotext` devolve "pre-\\nregistration" quando a
   palavra quebra; um `grep -c 'pre-registration'` conta zero e a ausência parece
   confirmada pela própria falha do instrumento. Aqui as quebras são costuradas antes
   de contar, e o script reporta quantas costurou.
2. **A grafia não é uma só.** "pre-registration", "preregistration", "pre-registered",
   "preregistered", "pre-register" — contar uma delas e concluir sobre o conceito é
   medir o hífen, não a prática.
3. **Bibliografia não é corpo.** Um título na lista de referências é ocorrência da
   string e NÃO é a área praticando o método. As duas contagens saem separadas; qual
   delas sustenta a afirmação é decisão de quem escreve, não do script.

Uso:
  survey-string-count.py <arquivo.pdf> [--sha256 <hex esperado>] [--json]

O `--sha256` existe porque "o survey" não é um objeto estável: v3 e v4 têm texto
diferente, e uma contagem sem o hash do arquivo contado não é reproduzível.
"""
import hashlib
import json
import re
import subprocess
import sys

TERMOS = [
    "pre-registration", "preregistration", "pre-registered", "preregistered",
    "pre-register", "preregister", "pre-registry", "preregistry",
    "interventional", "counterfactual", "randomized", "randomised",
    "ablation", "ablations",
]

# ⚠️ CONTROLE POSITIVO. A afirmação do paper é um ZERO, e zero é o resultado que uma
# extração quebrada produz de graça: PDF com fonte não-mapeada, `pdftotext` ausente,
# arquivo truncado — todos devolvem "não encontrei" com a mesma cara de achado. Estes
# termos TÊM de aparecer num survey de memória de agentes; se algum vier zero, o
# instrumento está quebrado e nenhuma contagem deste script vale.
#
# ⚠️ `ablation` ESTEVE aqui e foi movido para os termos contados, em 2026-08-28. O
# controle disparou com `ablation=0` e eu fui conferir antes de acreditar em qualquer
# um dos lados: `memory`=1.208 e `benchmark`=126 no mesmo texto ⇒ a extração estava
# íntegra, e o survey realmente não diz "ablation" nenhuma vez. O piso é que estava
# errado: survey CATALOGA, não ablaciona. Controle positivo cujo piso não se sustenta
# transforma dado em falso alarme — e teria transformado, se eu tivesse "consertado" a
# extração em vez de medi-la.
CONTROLE = {"memory": 100, "agent": 100, "benchmark": 10, "evaluation": 10}

# Cabeçalho da bibliografia. Só o ÚLTIMO casamento conta: "References" aparece no
# sumário e em legendas, e cortar no primeiro jogaria o corpo inteiro fora.
REFS = re.compile(r"^\s*(references|bibliography)\s*$", re.I | re.M)


def texto(pdf: str) -> str:
    # `-layout` preserva colunas; sem ele, texto de duas colunas se intercala e
    # palavras de colunas vizinhas se colam, criando casamentos que não existem.
    r = subprocess.run(["pdftotext", "-layout", pdf, "-"],
                       capture_output=True, check=True)
    return r.stdout.decode("utf-8", errors="replace")


def costurar(t: str) -> tuple[str, int]:
    """Junta palavra hifenizada quebrada em duas linhas. Devolve o texto e a contagem."""
    padrao = re.compile(r"(\w)-\s*\n\s*(\w)")
    n = len(padrao.findall(t))
    return padrao.sub(r"\1-\2", t), n


def contar(t: str, termo: str) -> int:
    # `\b` nas duas pontas: "preregistration" não deve contar dentro de outra palavra,
    # e "register" não deve casar "registered".
    return len(re.findall(r"\b" + re.escape(termo) + r"\b", t, re.I))


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__.strip().splitlines()[-4], file=sys.stderr)
        return 2
    pdf = sys.argv[1]
    esperado = None
    if "--sha256" in sys.argv:
        esperado = sys.argv[sys.argv.index("--sha256") + 1].lower()

    sha = hashlib.sha256(open(pdf, "rb").read()).hexdigest()
    if esperado and sha != esperado:
        print(f"ABORTA: sha256 do PDF é {sha}, esperado {esperado}. "
              f"Contagem sobre outro arquivo não sustenta a afirmação.", file=sys.stderr)
        return 1

    bruto = texto(pdf)
    t, costuras = costurar(bruto)

    cortes = list(REFS.finditer(t))
    if cortes:
        corte = cortes[-1].start()
        corpo, refs = t[:corte], t[corte:]
        onde = f"linha {t[:corte].count(chr(10)) + 1}"
    else:
        corpo, refs, onde = t, "", "não encontrada"

    controle = {t_: contar(t, t_) for t_ in CONTROLE}
    quebrados = [f"{k}={v} (mínimo {CONTROLE[k]})" for k, v in controle.items()
                 if v < CONTROLE[k]]
    if quebrados:
        print("ABORTA: controle positivo falhou — a extração está quebrada, e um zero "
              "aqui seria do instrumento, não do survey: " + "; ".join(quebrados),
              file=sys.stderr)
        return 1

    res = {
        "pdf": pdf,
        "controle_positivo": controle,
        "sha256": sha,
        "caracteres": len(t),
        "hifenizacoes_costuradas": costuras,
        "corte_da_bibliografia": onde,
        "contagens": {
            termo: {"corpo": contar(corpo, termo), "bibliografia": contar(refs, termo),
                    "total": contar(t, termo)}
            for termo in TERMOS
        },
    }

    if "--json" in sys.argv:
        print(json.dumps(res, indent=2, ensure_ascii=False))
        return 0

    print(f"PDF      : {pdf}")
    print(f"sha256   : {sha}")
    print(f"texto    : {len(t):,} caracteres · {costuras} hifenizações costuradas")
    print(f"biblio   : corte em {onde}")
    print("controle : " + " · ".join(f"{k}={v}" for k, v in controle.items()) + "  (todos acima do piso)")
    print()
    print(f"{'termo':<20} {'corpo':>6} {'biblio':>7} {'total':>6}")
    for termo, c in res["contagens"].items():
        print(f"{termo:<20} {c['corpo']:>6} {c['bibliografia']:>7} {c['total']:>6}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
