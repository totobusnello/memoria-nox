#!/usr/bin/env python3
"""
granularidade-do-teto.py — o teto de 4,86% é do comparador ou do FORMATO de `served_at`?

O comparador de cobertura é lexicográfico em `(last_served ASC, salience DESC)`, e a
Proposição 1 (§5, verificada pelo modo `porque` do replay) diz que o bônus aditivo age
**só dentro** de um empate da coordenada dominante. Segue disso, dedutivamente, que o
teto de alcançabilidade não é propriedade do comparador sozinho: é propriedade de
**quantos empates o formato de `served_at` produz**.

E a resolução de `served_at` é herdada do `datetime('now')` do SQLite. Ninguém a
escolheu como parâmetro de desenho.

Este script consolida o contrafactual que separa as duas coisas: o MESMO replay, o
MESMO corpus, a MESMA designação, os MESMOS 350 estados, a MESMA dose absurda — variando
só a granularidade da chave de estrato (`--granularidade` de `replay-oportunidade.mjs`,
que trunca-e-repõe `served_at` no serve-state derivado, depois do corte).

⚠️ **A truncação é cirúrgica por um fato verificado no fonte, não por suposição.**
`served_at` tem UM consumidor vivo no serving: a chave de estrato. O outro
(`serveCounts`, a janela do novelty-penalty) está exportado e testado, mas **nenhum
caminho de produção o chama** — é o resto do mecanismo A, que o tune de 06-26 substituiu
por cobertura (`src/api/brief.ts:588`). Fosse chamado, truncar contaminaria a contagem
de janela e o contrafactual mediria duas coisas ao mesmo tempo.

⚠️ **Uma predição minha morreu aqui, e ela fica registrada.** A nota de desenho do
`--granularidade` dizia: "coarsening só funde estratos, nunca divide ⇒ o teto é monótono
não-decrescente, e essa monotonia é o autoteste do instrumento". A contagem de fato sobe
(17 → 127 → 281 → 348), mas os **conjuntos não são aninhados**: 1 estado sai de
`seg`→`min` e 2 de `min`→`hora`. O erro do raciocínio é que fundir estrato mexe também
no braço de **controle**, não só no tratado — e o churn é a diferença entre os dois.
Medidos, os três estados perdidos se dividem em dois mecanismos OPOSTOS:

  - **redundância** (`2026-08-26T20:52:04`): o designado estava fora do controle sob
    `seg` e passa a estar DENTRO sob `min`. A fusão o promoveu sozinho; a intervenção
    ficou sem o que fazer.
  - **inalcançabilidade** (`05:37` e `07:37`): o designado continua fora do controle sob
    `hora` e ainda assim o churn some. O estrato inteiro dele desceu para baixo do corte
    de seleção, e bônus não atravessa estrato — que é a própria Proposição 1 mordendo na
    direção contrária.

Logo a monotonia da contagem é **empírica, não estrutural**, e este script a reporta em
vez de a exigir. Um guarda que afirmasse aninhamento estaria errado e teria escondido o
achado mais interessante.

⚠️ E o efeito não é só de quantidade: em `07:37` o id que ENTRA muda de 308284 (`seg`)
para 308296 (`min`). A resolução do timestamp decide também **qual** chunk é beneficiado.

O guarda que este script de fato precisa é outro: provar que **só** a granularidade
variou. Ele compara, entre os quatro artefatos, o sha256 do corpus, o sha256 da
designação, o número de designados, o corte do serve-state, a dose e o conjunto de
estados replayados. Qualquer divergência aborta — sem isso, a tabela compararia braços
que diferem em mais de uma coisa, que é o defeito de composição já cometido neste
projeto.

Uso:
  granularidade-do-teto.py --gran seg=out/gran-seg.json --gran min=out/gran-min.json \
      --gran hora=out/gran-hora.json --gran dia=out/gran-dia.json \
      [--diag seg=out/gran3-seg.json ...] [--out CEILING-GRANULARITY-2026-08-28.json]
"""
import argparse
import json
import sys

# A âncora publicada (REPLAY-OPORTUNIDADE-2026-08-27.md, §5 do manuscrito). A
# granularidade nativa TEM de a reproduzir; se não reproduzir, o caminho novo de
# reescrita de `served_at` mudou alguma coisa que devia ser no-op, e nenhuma linha
# grosseira desta tabela vale nada.
ANCORA_NATIVA = {"estados": 350, "mexeu": 17}
ORDEM = ["seg", "min", "hora", "dia"]


def carrega(spec):
    rot, _, caminho = spec.partition("=")
    if not caminho:
        raise SystemExit(f"--gran espera rotulo=caminho, recebi {spec!r}")
    return rot, caminho, json.load(open(caminho))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--gran", action="append", required=True)
    ap.add_argument("--diag", action="append", default=[])
    ap.add_argument("--out")
    a = ap.parse_args()

    art = {}
    for spec in a.gran:
        rot, caminho, d = carrega(spec)
        art[rot] = {"caminho": caminho, "d": d}

    faltam = [g for g in ORDEM if g not in art]
    if faltam:
        raise SystemExit(f"faltam granularidades: {faltam}")

    # ── guarda: só a granularidade variou ──────────────────────────────────
    invar = {}
    for rot in ORDEM:
        p = art[rot]["d"]["procedencia"]
        dose = art[rot]["d"]["dose"]
        estados = tuple(sorted(x["ts"] for x in dose["detalhe"]))
        invar[rot] = {
            "corpus_sha256_primeiros_1MB": p["corpus_sha256_primeiros_1MB"],
            "designacao_sha256": p["designacao_sha256"],
            "designados": p["designados"],
            "corte_serve_state": p["corte_serve_state"],
            "fonte_brief_ts_sha256": p["fonte_brief_ts_sha256"],
            "doses": tuple(t["w"] for t in dose["tabela"]),
            "n_estados": len(estados),
            "hash_estados": hash(estados),
        }
        # e o rótulo tem de bater com o que o artefato diz de si mesmo
        declarada = p.get("granularidade_last_served")
        if declarada != rot:
            raise SystemExit(
                f"{art[rot]['caminho']}: rotulado {rot!r} mas a procedência diz "
                f"{declarada!r}. Artefato trocado — a tabela seria uma mentira ordenada.")

    base = invar["seg"]
    divs = {}
    for rot in ORDEM[1:]:
        d = {k: (base[k], invar[rot][k]) for k in base if base[k] != invar[rot][k]}
        if d:
            divs[rot] = d
    if divs:
        for rot, d in divs.items():
            print(f"⛔ {rot} difere de seg em mais que a granularidade:", file=sys.stderr)
            for k, (x, y) in d.items():
                print(f"     {k}: seg={x} {rot}={y}", file=sys.stderr)
        raise SystemExit("contrafactual inválido: mais de uma coisa mudou entre os braços.")

    # ── guarda: a granularidade nativa reproduz a âncora publicada ─────────
    t0 = art["seg"]["d"]["dose"]["tabela"][0]
    obs = {"estados": art["seg"]["d"]["dose"]["estados"], "mexeu": t0["mexeu"]}
    if obs != ANCORA_NATIVA:
        raise SystemExit(
            f"âncora nativa NÃO reproduzida: publicada {ANCORA_NATIVA}, observada {obs}. "
            f"O caminho de reescrita de `served_at` devia ser no-op em `seg` e não é.")

    # ── tabela ─────────────────────────────────────────────────────────────
    linhas, conjuntos = [], {}
    for rot in ORDEM:
        dose = art[rot]["d"]["dose"]
        t = dose["tabela"][0]
        det = dose["detalhe"]
        erros = [x for x in det if "erro" in x]
        conjuntos[rot] = {x["ts"] for x in det if not x.get("erro") and (x.get("churn") or 0) > 0}
        linhas.append({
            "granularidade": rot,
            "estados": dose["estados"],
            "mexeu": t["mexeu"],
            "teto_pct": round(100 * t["mexeu"] / dose["estados"], 2),
            "churn_total": t["churn_total"],
            "boosts_emitidos": t["boosts"],
            "erros": len(erros),
        })

    # aninhamento: reportado, nunca exigido — ver o cabeçalho
    aninh = []
    for i in range(len(ORDEM) - 1):
        a_, b_ = ORDEM[i], ORDEM[i + 1]
        perdidos = sorted(conjuntos[a_] - conjuntos[b_])
        aninh.append({
            "de": a_, "para": b_,
            "ganhos": len(conjuntos[b_] - conjuntos[a_]),
            "perdas": len(perdidos),
            "estados_perdidos": perdidos,
            "aninhado": not perdidos,
        })

    mono = all(linhas[i]["mexeu"] <= linhas[i + 1]["mexeu"] for i in range(len(linhas) - 1))

    # ── diagnóstico dos estados perdidos, se fornecido ─────────────────────
    diag = {}
    if a.diag:
        dd = {}
        for spec in a.diag:
            rot, caminho, d = carrega(spec)
            dd[rot] = {x["ts"]: x for x in d["dose"]["detalhe"]}
        # ⚠️ Esta classificação já esteve ERRADA, e o erro é instrutivo: a versão
        # anterior juntava `would_enter` de TODAS as granularidades e testava contra o
        # controle da granularidade corrente (`for g in ORDEM for c in ...`). Isso
        # cruza braços que não se comparam e transforma a taxonomia numa heurística
        # com cara de medição. Achado por revisão adversarial em 2026-08-29.
        #
        # A pergunta correta é por TRANSIÇÃO, não por granularidade: o estado deixou
        # de mexer indo de `a` (fina) para `b` (grossa). O id que entrava em `a` está
        # no CONTROLE de `b`? Se está, a fusão o promoveu sozinho ⇒ redundância. Se
        # não está e mesmo assim o churn zerou, o estrato dele saiu de alcance ⇒
        # inalcançabilidade. Só `a` e `b` entram na conta.
        for par in aninh:
            a_, b_ = par["de"], par["para"]
            for ts in par["estados_perdidos"]:
                xa, xb = dd.get(a_, {}).get(ts), dd.get(b_, {}).get(ts)
                if xa is None or xb is None:
                    diag[ts] = {"transicao": f"{a_}→{b_}",
                                "mecanismo": "NAO CLASSIFICADO — falta o estado "
                                             "replayado em uma das duas granularidades"}
                    continue
                entrou_em_a = list(xa.get("would_enter") or [])
                ctl_b = set(xb.get("ids_controle_replay") or [])
                promovidos = sorted(c for c in entrou_em_a if c in ctl_b)
                if not ctl_b:
                    mec = ("NAO CLASSIFICADO — o controle de %s não foi registrado, "
                           "e sem ele redundância e inalcançabilidade são "
                           "indistinguíveis" % b_)
                elif promovidos:
                    mec = ("redundancia — o designado que entrava em %s já está no "
                           "CONTROLE de %s" % (a_, b_))
                else:
                    mec = ("inalcancabilidade — o designado que entrava em %s NÃO está "
                           "no controle de %s e ainda assim o churn zerou: o estrato "
                           "saiu de alcance (Proposição 1)" % (a_, b_))
                diag[ts] = {
                    "transicao": f"{a_}→{b_}",
                    a_: {"churn": xa.get("churn"), "would_enter": entrou_em_a,
                         "would_leave": xa.get("would_leave")},
                    b_: {"churn": xb.get("churn"),
                         "controle_registrado": bool(ctl_b)},
                    "entrou_em_%s_e_esta_no_controle_de_%s" % (a_, b_): promovidos,
                    "mecanismo": mec,
                }

    saida = {
        "gerado_por": "measurement/granularidade-do-teto.py",
        "pergunta": "o teto de alcançabilidade é do comparador ou da resolução de served_at?",
        "ancora_nativa_reproduzida": ANCORA_NATIVA,
        "invariantes_conferidos": sorted(k for k in base if k != "hash_estados"),
        "tabela": linhas,
        "monotonia_da_contagem": mono,
        "aninhamento_dos_conjuntos": aninh,
        "conjuntos_aninhados": all(p["aninhado"] for p in aninh),
        "diagnostico_dos_perdidos": diag,
        "artefatos": {rot: art[rot]["caminho"] for rot in ORDEM},
    }

    print(f"{'gran':6}{'estados':>9}{'mexeu':>7}{'teto':>9}{'churn':>7}{'erros':>7}")
    for l in linhas:
        print(f"{l['granularidade']:6}{l['estados']:>9}{l['mexeu']:>7}"
              f"{l['teto_pct']:>8.2f}%{l['churn_total']:>7}{l['erros']:>7}")
    print(f"\ncontagem monótona: {mono} · conjuntos aninhados: {saida['conjuntos_aninhados']}")
    for p in aninh:
        print(f"  {p['de']:>4} → {p['para']:<5} +{p['ganhos']:<4} −{p['perdas']}"
              + (f"  {p['estados_perdidos']}" if p["perdas"] else ""))
    for ts, v in diag.items():
        print(f"\n  {ts} [{v.get('transicao','?')}]: {v['mecanismo']}")

    if a.out:
        json.dump(saida, open(a.out, "w"), indent=2, ensure_ascii=False)
        print(f"\n→ {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
