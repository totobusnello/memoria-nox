#!/usr/bin/env python3
"""
auditoria-da-cadeia.py — script → artefato → alegação: onde a corrente se rompe?

Retrospectiva pedida em 2026-08-30, depois de seis revisões adversariais e três dias de
medição. A pergunta que motiva, e que nenhuma revisão faz, é a terceira abaixo:

1. **alegação sem artefato** — o texto afirma um número que nada produz (envelhece para
   falso em silêncio; já aconteceu duas vezes: os `205` caracteres e o `583.973`);
2. **artefato sem script** — existe um JSON que nada gera, logo irreproduzível;
3. **artefato ÓRFÃO** — medimos, gravamos, e **nunca olhamos**. Este é o mais
   interessante e o mais invisível: nenhum guarda pode acusar a ausência de uma leitura
   que ninguém prometeu fazer. Um resultado medido e não reportado é, do ponto de vista
   do leitor, um resultado que não existe — mas do ponto de vista do método, é seleção
   de evidência, ainda que involuntária.

⚠️ **O item 3 é o que uma retrospectiva por leitura não pega**, porque para notar a
ausência seria preciso lembrar de algo que não está no texto. É censo ou nada.

Uso:
  auditoria-da-cadeia.py [--raiz .] [--json] [--out ...]
"""
import argparse
import json
import pathlib
import re
import sys

# Artefatos que existem por disciplina de processo, não para sustentar alegação no
# manuscrito. Citá-los não é obrigatório, e alarmar sobre eles é ruído.
NAO_PRECISAM_CITACAO = {
    "CLAIM-COVERAGE", "WARNING-DENSITY", "SERVING-VOCAB", "POPULATION-LABELS",
    "CHAIN-AUDIT", "BATCH-CYCLE", "PREDICTION", "DOC-COHERENCE",
    "PARAGRAPH-UNIVERSES",
}


# Órfãos ACEITOS — baseline de 2026-08-30, em TRÊS categorias, e a distinção importa
# porque "aceito" sem razão escrita é indistinguível de "esquecido":
#
#   (a) INTERMEDIÁRIOS deste paper — alimentam artefatos agregados que o texto cita:
#       as 4 granularidades (`gran-*`), as 8 designações (`sens-0*`), as variantes de
#       corte (`c-*`), os esperados de teste;
#   (b) OUTRO ESCOPO, Paper B (o estudo interventivo, que não começou): REACHABILITY,
#       INGRESS-*, SPREAD-SLOTS, CUTS-MEASURED, PILOT-WINDOW, FIXTURE-SERVING,
#       DESIGNATION. Foram medidos para o desenho da intervenção e serão reportados lá;
#   (c) OUTRO ESCOPO, fora dos dois papers: `bench-vec0-2026-08-28.json`, um benchmark
#       de latência do índice vetorial (33,1% de ganho por reempacotamento). Resultado
#       real e verificado, sem relação com a superfície de exposição.
#
# ⚠️ `ancora-sondas.json` e `ancora-sem-exclusao.json` estavam nesta lista por omissão,
# não por decisão — e continham o TERCEIRO eixo de sensibilidade do teto, invisível por
# três dias. Hoje o §5.7.2 os cita, então saíram de órfãos. A categoria inteira existe
# por causa deles.
#
# ⚠️ Órfão FORA desta lista reprova. Acrescentar um item aqui é decisão consciente de
# que aquele artefato não precisa ser lido — que é exatamente a decisão que não foi
# tomada da primeira vez.
ORFAOS_ACEITOS = {
    "CUTS-MEASURED-2026-08-18.json",
    "DESIGNATION-2026-08-26.json",
    "FIXTURE-SERVING-2026-08-18.json",
    "INGRESS-CLEAN-2026-08-18.json",
    "INGRESS-INFLOW-2026-08-18.json",
    "INGRESS-RESTORED-2026-08-20.json",
    "PILOT-WINDOW-2026-08-25.json",
    "REACHABILITY-2026-08-16.json",
    "REACHABILITY-FILA-2026-08-18.json",
    "SPREAD-SLOTS-2026-08-18.json",
    "measurement/out/MANIFESTO.json",
    "measurement/out/bench-vec0-2026-08-28.json",
    "measurement/out/c-27.json",
    "measurement/out/c-incl.json",
    "measurement/out/c-rowid.json",
    "measurement/out/esperado-superficie.json",
    "measurement/out/esperado.json",
    "measurement/out/gran-dia.json",
    "measurement/out/gran-hora.json",
    "measurement/out/gran-min.json",
    "measurement/out/gran-seg.json",
    "measurement/out/gran3-hora.json",
    "measurement/out/gran3-min.json",
    "measurement/out/gran3-seg.json",
    "measurement/out/porque-350-v3.json",
    "measurement/out/sens-01.json",
    "measurement/out/sens-02.json",
    "measurement/out/sens-03.json",
    "measurement/out/sens-04.json",
    "measurement/out/sens-05.json",
    "measurement/out/sens-06.json",
    "measurement/out/sens-07.json",
    "measurement/out/sens-08.json",
}


def rotulo(nome: str) -> str:
    """`CEILING-GRANULARITY-2026-08-28.json` → `CEILING-GRANULARITY`."""
    return re.sub(r"-?\d{4}-\d{2}-\d{2}.*$", "", pathlib.Path(nome).stem)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--raiz", default=str(pathlib.Path(__file__).resolve().parent.parent))
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--out")
    a = ap.parse_args()

    raiz = pathlib.Path(a.raiz)
    doc = raiz / "MANUSCRIPT.md"
    if not doc.exists():
        print("⛔ MANUSCRIPT.md não encontrado", file=sys.stderr)
        return 1
    # ⚠️ O universo de documentos que CITAM artefatos cresceu com o Paper B. Enquanto
    # só existia o manuscrito, "citado" e "citado no manuscrito" eram a mesma coisa; o
    # registro prospectivo do estimando cita artefatos que o manuscrito nunca citará,
    # porque pertencem ao outro estudo. Varrer só o manuscrito passou a produzir órfão
    # falso — e um guarda que acusa o inocente é desligado na terceira vez.
    CITANTES = ["MANUSCRIPT.md", "PROSPECTIVE-ESTIMAND-2026-08-30.md",
                "DEVIATIONS-FOR-PAPER.md"]
    texto = "\n".join((raiz / n).read_text(encoding="utf-8")
                      for n in CITANTES if (raiz / n).exists())
    verificador = (raiz / "claims_check.py").read_text(encoding="utf-8") \
        if (raiz / "claims_check.py").exists() else ""

    scripts = sorted(p.name for p in (raiz / "measurement").glob("*.py"))
    # ⚠️ TRÊS diretórios, não dois. A primeira versão varria só `out/` e
    # `measurement/out/` e perdia os artefatos da RAIZ — que são justamente os que o
    # `claims_check` lê (`DELTA-CUT-MEASUREMENT`, `REMEDIATION`). Uma auditoria cega
    # a um terço do universo reporta "tudo certo" com convicção. Mesma classe do
    # recibo adversarial que eu procurei no `.remember/` errado.
    artefatos = sorted([p for p in (raiz / "out").glob("*.json")] +
                       [p for p in (raiz / "measurement" / "out").glob("*.json")] +
                       [p for p in raiz.glob("*.json")],
                       key=lambda p: p.name)

    linhas = []
    for art in artefatos:
        rel = str(art.relative_to(raiz))
        rot = rotulo(art.name)
        citado_doc = art.name in texto or rel in texto
        lido_verif = art.name in verificador or rel in verificador
        # qual script o gera? procura o nome do artefato (ou seu rótulo) no fonte
        gerado_por = [s for s in scripts
                      if rot in (raiz / "measurement" / s).read_text(encoding="utf-8")
                      or art.name in (raiz / "measurement" / s).read_text(encoding="utf-8")]
        linhas.append({
            "artefato": rel, "rotulo": rot,
            "citado_no_manuscrito": citado_doc,
            "lido_pelo_verificador": lido_verif,
            "gerado_por": gerado_por,
            "bytes": art.stat().st_size,
        })

    orfaos = [l for l in linhas
              if not l["citado_no_manuscrito"] and not l["lido_pelo_verificador"]
              and l["rotulo"] not in NAO_PRECISAM_CITACAO]
    sem_gerador = [l for l in linhas if not l["gerado_por"]]

    # scripts que não produzem artefato nenhum
    sem_saida = []
    for s in scripts:
        fonte = (raiz / "measurement" / s).read_text(encoding="utf-8")
        if "--out" not in fonte and "json.dump" not in fonte:
            sem_saida.append(s)

    # artefatos citados no texto que NÃO existem em disco
    citados = set(re.findall(r"`((?:out|measurement/out)/[A-Za-z0-9._-]+\.json)`", texto))
    existentes = {str(p.relative_to(raiz)) for p in artefatos}
    citados_ausentes = sorted(citados - existentes)

    saida = {
        "scripts": len(scripts),
        "artefatos": len(linhas),
        "artefatos_orfaos": orfaos,
        "artefatos_sem_script_gerador": sem_gerador,
        "scripts_sem_artefato": sem_saida,
        "artefatos_citados_e_ausentes": citados_ausentes,
        "detalhe": linhas,
    }

    # ── guardas ────────────────────────────────────────────────────────────
    # (1) artefato citado e ausente é a falha mais grave: o leitor vai procurar e não
    #     acha, e a alegação fica sem lastro.
    if citados_ausentes:
        print(f"⛔ o manuscrito cita {len(citados_ausentes)} artefato(s) que não existem "
              f"em disco: {citados_ausentes}", file=sys.stderr)
        return 1
    # (2) diretório de medição vazio significa que este script está olhando o lugar
    #     errado — e reportaria "nenhum órfão" por cegueira.
    # (3) todo artefato que o `claims_check` abre tem de estar no universo auditado;
    #     se não estiver, a auditoria é cega justamente onde o verificador confia.
    # ⚠️ `root / "X.json"` aparece no verificador em DOIS papéis diferentes, e tratá-los
    # igual acusa o inocente: um artefato que ele ABRE tem de existir e ser auditável;
    # um arquivo cuja AUSÊNCIA ele testa (`.exists()` como asserção de precedência) não
    # é artefato nenhum — é justamente a inexistência que está sendo afirmada. O guarda
    # do estimando testa se `ASSIGNMENT.json` já existe para detectar que a alegação de
    # precedência envelheceu; exigir que ele exista inverteria o sentido do teste.
    lidos_pelo_verif = {m.group(1) for m in
                        re.finditer(r'root / "([A-Za-z0-9._-]+\.json)"([^\n]*)', verificador)
                        if ".exists()" not in m.group(2)}
    nomes = {p.name for p in artefatos}
    invisiveis = sorted(lidos_pelo_verif - nomes)
    if invisiveis:
        print(f"⛔ o verificador lê {invisiveis}, que esta auditoria não enxerga — "
              f"escopo de diretório incompleto.", file=sys.stderr)
        return 1
    # (4) órfão NOVO: medido, gravado, não citado, não lido, e não declarado como
    #     intermediário aceito. É a categoria que custou três dias de invisibilidade.
    novos = sorted(l["artefato"] for l in orfaos
                   if l["artefato"] not in ORFAOS_ACEITOS)
    if novos:
        print(f"⛔ {len(novos)} artefato(s) órfão(s) NOVO(S) — medidos e nunca lidos, "
              f"e não declarados como intermediários:", file=sys.stderr)
        for n in novos:
            print(f"    {n}", file=sys.stderr)
        print("  Ou o resultado entra no texto, ou o artefato entra em "
              "ORFAOS_ACEITOS com a razão escrita.", file=sys.stderr)
        return 1
    if not scripts or not artefatos:
        print(f"⛔ {len(scripts)} scripts e {len(artefatos)} artefatos — a auditoria "
              f"está olhando o diretório errado e diria 'tudo certo' por cegueira.",
              file=sys.stderr)
        return 1

    if a.json:
        print(json.dumps(saida, indent=2, ensure_ascii=False))
    else:
        print(f"{len(scripts)} scripts · {len(linhas)} artefatos\n")
        if orfaos:
            print(f"🔴 {len(orfaos)} ARTEFATO(S) ÓRFÃO(S) — medidos, gravados, "
                  f"nunca citados nem lidos:")
            for l in orfaos:
                g = l["gerado_por"][0] if l["gerado_por"] else "(sem gerador)"
                print(f"     {l['artefato']:<48} {l['bytes']:>7}B  ← {g}")
        else:
            print("✅ nenhum artefato órfão")
        if sem_gerador:
            print(f"\n⚠️ {len(sem_gerador)} artefato(s) sem script gerador identificado:")
            for l in sem_gerador:
                print(f"     {l['artefato']}")
        if sem_saida:
            print(f"\n📌 {len(sem_saida)} script(s) que não gravam artefato "
                  f"(diagnóstico de tela): {', '.join(sem_saida)}")

    if a.out:
        json.dump(saida, open(a.out, "w"), indent=2, ensure_ascii=False)
        print(f"\n→ {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
